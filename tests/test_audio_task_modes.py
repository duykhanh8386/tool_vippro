import asyncio
import copy
import inspect
import tempfile
import unittest
from contextlib import ExitStack
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from nicegui import Client, ui
from nicegui.page import page

from src.audio_recovery import get_audio_mutation_guard
from src.module.model import Video
from web.components import audio, remove_audio


class MemoryStateManager:
    def __init__(self):
        self.states = {}

    def save_state(self, key, state):
        self.states[key] = copy.deepcopy(state)
        return True

    def load_state(self, key):
        return copy.deepcopy(self.states.get(key))


class AudioTaskModeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.music = Path(folder.name) / "music.mp3"
        self.music.write_bytes(b"test audio")
        self.state = MemoryStateManager()
        self.channel = SimpleNamespace(
            id="mode-test-channel", name="Test channel", img_src="", owner_email="test@example.test",
        )
        self.events = []
        self.timers = []

        def timer(_interval, callback, **kwargs):
            if kwargs.get("once"):
                self.timers.append(callback)
            return Mock()

        for module in (audio, remove_audio):
            self.patches.enter_context(patch.object(module, "state_manager", self.state))
            self.patches.enter_context(patch.object(
                module, "get_channels_info",
                side_effect=lambda channel_id=None: self.channel if channel_id else [self.channel],
            ))
        self.patches.enter_context(patch.object(audio.ui, "timer", side_effect=timer))
        self.patches.enter_context(patch.object(audio.ui, "notify"))
        self.patches.enter_context(patch.object(audio, "find_caption_oauth_client", return_value=None))

        def delete(**_kwargs):
            self.events.append("delete")
            return 200

        def delete_tracks(*_args):
            self.events.append("delete_tracks")
            return 200

        self.delete = self.patches.enter_context(patch.object(
            audio.update_audio_module, "delete", side_effect=delete,
        ))
        self.delete_tracks = self.patches.enter_context(patch.object(
            audio.update_audio_module, "delete_track_ids", side_effect=delete_tracks,
        ))

        def add(**kwargs):
            self.events.append("add:" + kwargs["language"])
            return 200

        self.add = self.patches.enter_context(patch.object(audio.update_audio_module, "add", side_effect=add))
        self.patches.enter_context(patch.object(
            audio.update_audio_module, "_get_video_info", return_value=Video(
                id="video", channel_id=self.channel.id, title="", description="", thumbnail="", duration_ms=60000,
            ),
        ))
        self.patches.enter_context(patch.object(audio, "multiply_audio"))
        self.recovery = self.patches.enter_context(patch.object(audio, "register_audio_recovery", return_value=True))

    def saved_add_state(self):
        return {
            "selected_channel": self.channel.id,
            "video_ids": ["video"],
            "id_to_path": {"video": str(self.music)},
            "selected_languages": ["en", "vi"],
            "performance_settings": {
                "mode": audio._AUDIO_UPLOAD_CONCURRENCY_MODE,
                "max_concurrency": audio.DEFAULT_AUDIO_UPLOAD_CONCURRENCY,
            },
            "video_source_state": {"mode": "manual", "scan_scope": "all", "recent_limit": 50},
        }

    def render(self, *, delete_existing=True, remove_only=False):
        route = "/audio/remove" if remove_only else ("/audio/add" if delete_existing else "/audio/add-only")
        client = Client(page(route), request=None)
        self.addCleanup(client.delete)
        self.timers.clear()
        with client:
            if remove_only:
                remove_audio.create_remove_audio_page()
            else:
                audio.create_add_audio_page(delete_existing=delete_existing)
            for callback in list(self.timers):
                callback()
        return client

    def button_callback(self, client, text):
        button = next(element for element in client.elements.values()
                      if isinstance(element, ui.button) and element.text == text)
        listener = next(listener for listener in button._event_listeners.values() if listener.type == "click")
        return inspect.getclosurevars(listener.handler).nonlocals["callback"]

    def scan_scope_controls(self, client):
        toggle = next(element for element in client.elements.values()
                      if isinstance(element, ui.toggle) and set(element.options) == audio.VIDEO_SCAN_SCOPES)
        number = next(element for element in client.elements.values()
                      if isinstance(element, ui.number) and element._props.get("label") == "Số video muốn quét")
        return toggle, number

    async def test_combined_workflow_still_deletes_before_adding_every_language(self):
        self.state.states["audio_add"] = self.saved_add_state()
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.events, ["delete", "add:en", "add:vi"])
        self.assertEqual(self.state.states["audio_add"]["video_cleanup_status"]["video"], "successful")
        self.assertNotIn("audio_add_only", self.state.states)
        self.assertFalse(get_audio_mutation_guard(self.channel.id).locked())

    async def test_add_only_never_deletes_and_keeps_combined_checkpoint(self):
        combined = {"keep": "combined task checkpoint"}
        self.state.states["audio_add"] = copy.deepcopy(combined)
        self.state.states["audio_add_only"] = self.saved_add_state()
        client = self.render(delete_existing=False)
        with client:
            await self.button_callback(client, "Bắt đầu thêm audio")()
        self.assertEqual(self.events, ["add:en", "add:vi"])
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.assertEqual(self.state.states["audio_add"], combined)
        self.assertEqual(self.state.states["audio_add_only"]["video_processing_status"]["video"],
                         {"en": "successful", "vi": "successful"})
        self.assertEqual(self.state.states["audio_add_only"]["video_cleanup_status"], {})
        self.assertTrue(self.recovery.call_args.kwargs["merge_languages"])
        labels = [element.text for element in client.elements.values() if isinstance(element, ui.label)]
        self.assertIn("Thành công", labels)
        self.assertNotIn("Chờ xóa audio cũ", labels)

    async def test_add_only_error_scan_never_deletes_failed_track_ids(self):
        saved = self.saved_add_state()
        saved["video_source_state"].update({
            "mode": "failed", "failed_channel": self.channel.id,
            "failed_targets": {"video": [{"language": "en", "track_ids": ["failed-track"]}]},
        })
        self.state.states["audio_add_only"] = saved
        client = self.render(delete_existing=False)
        with patch.object(audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={
            "video": [{"language": "en", "track_ids": ["failed-track"]}],
        }), client:
            await self.button_callback(client, "Bắt đầu thêm audio")()
        self.assertEqual(self.events, ["add:en"])
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()

    async def test_remove_only_requires_no_audio_file_or_languages_and_never_adds(self):
        self.state.states["audio_remove"] = {"selected_channel": self.channel.id, "ids": ["video"]}
        self.state.states["audio_add"] = {"keep": "combined"}
        self.state.states["audio_add_only"] = {"keep": "add only"}
        client = self.render(remove_only=True)
        with client:
            await self.button_callback(client, "Bắt đầu xóa")()
        self.assertEqual(self.events, ["delete"])
        self.add.assert_not_called()
        self.assertEqual(self.state.states["audio_remove"]["video_processing_status"]["video"], "successful")
        self.assertEqual(self.state.states["audio_add"], {"keep": "combined"})
        self.assertEqual(self.state.states["audio_add_only"], {"keep": "add only"})
        self.assertFalse(get_audio_mutation_guard(self.channel.id).locked())

    async def test_combined_error_scan_keeps_targeted_delete_before_add(self):
        saved = self.saved_add_state()
        saved["video_source_state"].update({
            "mode": "failed", "failed_channel": self.channel.id,
            "failed_targets": {"video": [{"language": "en", "track_ids": ["failed-track"]}]},
        })
        self.state.states["audio_add"] = saved
        client = self.render()
        with patch.object(audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={
            "video": [{"language": "en", "track_ids": ["failed-track"]}],
        }), client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.events, ["delete_tracks", "add:en"])
        self.delete.assert_not_called()
        self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed-track"])

    async def test_completed_add_only_checkpoint_skips_upload_when_run_again(self):
        self.state.states["audio_add_only"] = self.saved_add_state()
        for _ in range(2):
            client = self.render(delete_existing=False)
            with client:
                await self.button_callback(client, "Bắt đầu thêm audio")()
        self.assertEqual(self.events, ["add:en", "add:vi"])
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()

    async def test_remove_only_is_blocked_by_other_audio_mutations_on_the_same_channel(self):
        self.state.states["audio_remove"] = {"selected_channel": self.channel.id, "ids": ["video"]}
        client = self.render(remove_only=True)
        guard = get_audio_mutation_guard(self.channel.id)
        guard.acquire()
        try:
            with client:
                await self.button_callback(client, "Bắt đầu xóa")()
            self.assertTrue(guard.locked())
            self.delete.assert_not_called()
            self.add.assert_not_called()
        finally:
            guard.release()

    async def test_draft_limit_is_editable_saved_and_applied_before_checking_audio(self):
        saved = self.saved_add_state()
        saved["video_source_state"].update(mode="failed", scan_scope="draft", recent_limit=2)
        self.state.states["audio_add"] = saved
        client = self.render()
        number = next(element for element in client.elements.values()
                      if isinstance(element, ui.number) and element._props.get("label") == "Số video muốn quét")
        self.assertFalse(number._props.get("disable"))
        with client:
            number.value = 3
        self.assertEqual(self.state.states["audio_add"]["video_source_state"]["recent_limit"], 3)
        with (
            patch.object(audio.list_videos_module, "list_all_videos", return_value=(
                [Video(id=f"draft-{i}", channel_id=self.channel.id, title="", description="",
                       thumbnail="", duration_ms=60000) for i in range(5)], "unused"),
            ) as list_videos,
            patch.object(audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={
                "draft-0": [{"language": "en", "track_ids": ["failed-track"]}],
            }) as targets,
            client,
        ):
            await self.button_callback(client, "Quét ID audio cần xử lý")()
        list_videos.assert_called_once_with(self.channel.id, limit=3, page_token=None, draft_only=True)
        self.assertEqual(targets.call_args.args[0], ["draft-0", "draft-1", "draft-2"])
        source = self.state.states["audio_add"]["video_source_state"]
        self.assertEqual(source["scan_total"], 3)
        self.assertEqual(source["last_scan_limit"], 3)
        self.assertEqual(self.state.states["audio_add"]["video_ids"], ["draft-0"])
        self.assertFalse(number._props.get("disable"))

    async def test_clearing_add_only_does_not_clear_other_tasks(self):
        self.state.states["audio_add"] = {"keep": "combined"}
        self.state.states["audio_remove"] = {"keep": "remove"}
        self.state.states["audio_add_only"] = self.saved_add_state()
        client = self.render(delete_existing=False)
        with client:
            self.button_callback(client, "Xóa dữ liệu")()
        self.assertEqual(self.state.states["audio_add_only"]["video_ids"], [])
        self.assertEqual(self.state.states["audio_add"], {"keep": "combined"})
        self.assertEqual(self.state.states["audio_remove"], {"keep": "remove"})

    async def test_remove_scan_caps_drafts_before_reading_audio_and_saves_actual_result_scope(self):
        self.state.states["audio_remove"] = {
            "selected_channel": self.channel.id,
            "scan_settings": {"scan_scope": "draft", "recent_limit": 2},
        }
        client = self.render(remove_only=True)
        scope, number = self.scan_scope_controls(client)
        self.assertEqual(scope.options, audio.VIDEO_SCAN_SCOPE_OPTIONS)
        self.assertFalse(number._props.get("disable"))
        with client:
            number.value = 3

        def find_attention(video_ids, channel_id, unreadable):
            unreadable.append("draft-1")
            return {"draft-0", "draft-2"}

        with (
            patch.object(remove_audio.list_videos_module, "list_all_videos", return_value=(
                [SimpleNamespace(id=f"draft-{i}") for i in range(5)], "unused"),
            ) as fetch,
            patch.object(remove_audio.update_audio_module, "get_audio_attention_video_ids", side_effect=find_attention) as scan,
            client,
        ):
            await self.button_callback(client, "Quét video cần xử lý")()

        fetch.assert_called_once_with(self.channel.id, limit=3, page_token=None, draft_only=True)
        self.assertEqual(scan.call_args.args[0], ["draft-0", "draft-1", "draft-2"])
        saved = self.state.states["audio_remove"]
        self.assertEqual(saved["ids"], ["draft-0", "draft-2"])
        self.assertEqual(saved["scan_settings"], {"scan_scope": "draft", "recent_limit": 3, "scan_start_date": "", "scan_date_type": "auto"})
        self.assertEqual(saved["scan_state"]["total"], 3)
        self.assertEqual(saved["scan_state"]["matched"], 2)
        self.assertEqual(saved["scan_state"]["skipped"], 1)
        self.assertEqual(saved["scan_state"]["last_scan_scope"], "draft")
        self.assertEqual(saved["scan_state"]["last_scan_limit"], 3)
        self.delete.assert_not_called()
        self.add.assert_not_called()
        self.assertFalse(scope._props.get("disable"))
        self.assertFalse(number._props.get("disable"))

    async def test_remove_scan_applies_every_scope_to_the_ids_sent_for_audio_checks(self):
        videos = [
            SimpleNamespace(id="public", privacy="VIDEO_PRIVACY_PUBLIC"),
            SimpleNamespace(id="scheduled", privacy="VIDEO_PRIVACY_PRIVATE", scheduled_publishing_details={"time": "later"}),
            SimpleNamespace(id="draft", privacy="VIDEO_PRIVACY_PRIVATE", draft_status="DRAFT"),
            SimpleNamespace(id="private", privacy="VIDEO_PRIVACY_PRIVATE"),
        ]
        expected_by_scope = {
            "all": ["public", "scheduled", "draft", "private"],
            "public": ["public"],
            "scheduled": ["scheduled"],
            "draft": ["draft"],
            "recent": ["public", "scheduled"],
        }
        for scope, expected in expected_by_scope.items():
            with self.subTest(scope=scope):
                self.state.states["audio_remove"] = {
                    "selected_channel": self.channel.id,
                    "scan_settings": {"scan_scope": scope, "recent_limit": 2},
                }
                client = self.render(remove_only=True)
                _, number = self.scan_scope_controls(client)
                self.assertEqual(bool(number._props.get("disable")), scope not in {"draft", "recent"})
                with (
                    patch.object(remove_audio.list_videos_module, "list_all_videos", return_value=(
                        [videos[2]] if scope == "draft" else videos, None,
                    )) as fetch,
                    patch.object(remove_audio.update_audio_module, "get_audio_attention_video_ids", return_value=set(expected)) as scan,
                    client,
                ):
                    await self.button_callback(client, "Quét video cần xử lý")()

                self.assertEqual(scan.call_args.args[0], expected)
                self.assertEqual(self.state.states["audio_remove"]["ids"], expected)
                self.assertEqual(fetch.call_args.kwargs["limit"], 2 if scope in {"draft", "recent"} else 50)
                self.assertEqual(fetch.call_args.kwargs.get("draft_only", False), scope == "draft")
                self.assertEqual(self.state.states["audio_remove"]["scan_state"]["last_scan_scope"], scope)

    async def test_remove_scan_preferences_restore_and_clear_independently_of_add_tasks(self):
        self.state.states["audio_add"] = {"keep": "combined"}
        self.state.states["audio_add_only"] = {"keep": "add only"}
        self.state.states["audio_remove"] = {"selected_channel": self.channel.id, "ids": ["video"]}
        client = self.render(remove_only=True)
        scope, number = self.scan_scope_controls(client)
        self.assertEqual(scope.value, "all")
        self.assertEqual(number.value, 50)
        self.assertTrue(number._props.get("disable"))
        with client:
            scope.value = "recent"
            number.value = 0
            self.assertEqual(number.value, 1)
            number.value = 10001
            self.assertEqual(number.value, 10000)
            number.value = 17

        reopened = self.render(remove_only=True)
        restored_scope, restored_number = self.scan_scope_controls(reopened)
        self.assertEqual(restored_scope.value, "recent")
        self.assertEqual(restored_number.value, 17)
        self.assertFalse(restored_number._props.get("disable"))
        self.assertEqual(self.state.states["audio_remove"]["ids"], ["video"])
        with reopened:
            self.button_callback(reopened, "Xóa dữ liệu")()
        self.assertEqual(self.state.states["audio_remove"]["scan_settings"], {"scan_scope": "all", "recent_limit": 50, "scan_start_date": "", "scan_date_type": "auto"})
        self.assertEqual(restored_scope.value, "all")
        self.assertTrue(restored_number._props.get("disable"))
        self.assertEqual(self.state.states["audio_add"], {"keep": "combined"})
        self.assertEqual(self.state.states["audio_add_only"], {"keep": "add only"})

    async def test_remove_scan_blocks_scope_and_count_changes_until_scan_finishes(self):
        self.state.states["audio_remove"] = {
            "selected_channel": self.channel.id,
            "scan_settings": {"scan_scope": "draft", "recent_limit": 3},
        }
        client = self.render(remove_only=True)
        scope, number = self.scan_scope_controls(client)
        calendar = next(element for element in client.elements.values()
                        if isinstance(element, ui.input) and element._props.get("label") == "Quét từ ngày")
        basis = next(element for element in client.elements.values()
                     if isinstance(element, ui.select) and element._props.get("label") == "Tính theo ngày")
        started, release = asyncio.Event(), asyncio.Event()

        async def dispatch(function, *args, **kwargs):
            if function is remove_audio._fetch_channel_videos:
                started.set()
                await release.wait()
                return []
            return function(*args, **kwargs)

        with (
            patch.object(remove_audio.asyncio, "to_thread", new=AsyncMock(side_effect=dispatch)),
            patch.object(remove_audio.update_audio_module, "get_audio_attention_video_ids", return_value=set()),
            client,
        ):
            task = asyncio.create_task(self.button_callback(client, "Quét video cần xử lý")())
            try:
                await asyncio.wait_for(started.wait(), timeout=2)
                self.assertTrue(scope._props.get("disable"))
                self.assertTrue(number._props.get("disable"))
                self.assertTrue(calendar._props.get("disable"))
                self.assertTrue(basis._props.get("disable"))
                scope.value = "public"
                number.value = 20
                calendar.value = "2026-10-20"
                basis.value = "published"
                self.assertEqual(scope.value, "draft")
                self.assertEqual(number.value, 3)
                self.assertEqual(calendar.value, "")
                self.assertEqual(basis.value, "auto")
            finally:
                release.set()
                await task

        self.assertFalse(scope._props.get("disable"))
        self.assertFalse(number._props.get("disable"))
        self.assertFalse(calendar._props.get("disable"))
        self.assertFalse(basis._props.get("disable"))
        self.assertEqual(self.state.states["audio_remove"]["scan_settings"], {"scan_scope": "draft", "recent_limit": 3, "scan_start_date": "", "scan_date_type": "auto"})

    async def test_failed_remove_scan_preserves_previous_ids_and_reenables_scan_controls(self):
        self.state.states["audio_remove"] = {
            "selected_channel": self.channel.id, "ids": ["previous-video"],
            "scan_settings": {"scan_scope": "recent", "recent_limit": 4},
        }
        client = self.render(remove_only=True)
        scope, number = self.scan_scope_controls(client)
        with patch.object(remove_audio, "_fetch_channel_videos", side_effect=RuntimeError("scan failed")), client:
            await self.button_callback(client, "Quét video cần xử lý")()

        self.assertEqual(self.state.states["audio_remove"]["ids"], ["previous-video"])
        self.assertFalse(scope._props.get("disable"))
        self.assertFalse(number._props.get("disable"))
        self.delete.assert_not_called()

    async def test_calendar_is_saved_restored_and_applied_in_all_three_audio_tasks(self):
        today = date(2026, 10, 22)
        zone = timezone(timedelta(hours=7))
        rows = [Video(
            id=video_id, channel_id=self.channel.id, title=video_id, description="",
            thumbnail="", duration_ms=60000,
            time_created_seconds=datetime(2026, 10, day, 12, tzinfo=zone).timestamp(),
        ) for video_id, day in (("too-old", 20), ("eligible", 21), ("future", 23))]
        for state_key, delete_existing, remove_only in (
            ("audio_add", True, False), ("audio_add_only", False, False), ("audio_remove", True, True),
        ):
            with self.subTest(task=state_key):
                settings_key = "scan_settings" if remove_only else "video_source_state"
                saved = {"selected_channel": self.channel.id} if remove_only else self.saved_add_state()
                saved[settings_key] = {
                    "mode": "failed", "scan_scope": "all", "recent_limit": 50, "scan_start_date": "2026-10-20",
                }
                self.state.states[state_key] = saved
                client = self.render(delete_existing=delete_existing, remove_only=remove_only)
                calendar = next(element for element in client.elements.values()
                                if isinstance(element, ui.input) and element._props.get("label") == "Quét từ ngày")
                self.assertEqual(calendar._props["type"], "date")
                self.assertEqual(calendar.value, "2026-10-20")
                self.assertFalse(calendar._props.get("disable"))
                with client:
                    calendar.value = "2026-10-21"
                self.assertEqual(self.state.states[state_key][settings_key]["scan_start_date"], "2026-10-21")

                client = self.render(delete_existing=delete_existing, remove_only=remove_only)
                calendar = next(element for element in client.elements.values()
                                if isinstance(element, ui.input) and element._props.get("label") == "Quét từ ngày")
                self.assertEqual(calendar.value, "2026-10-21")
                module = remove_audio if remove_only else audio
                method = "get_audio_attention_video_ids" if remove_only else "get_terminal_audio_repair_targets"
                targets = {"eligible"} if remove_only else {"eligible": [{"language": "en", "track_ids": ["failed"]}]}
                with (
                    patch("src.video_scan_dates.scan_today", return_value=today),
                    patch.object(module, "scan_today", return_value=today),
                    patch.object(module.list_videos_module, "list_all_videos", return_value=(rows, None)),
                    patch.object(module.update_audio_module, method, return_value=targets) as query,
                    client,
                ):
                    await self.button_callback(client, "Quét video cần xử lý" if remove_only else "Quét ID audio cần xử lý")()
                self.assertEqual(query.call_args.args[0], ["eligible"])
                result_key = "scan_state" if remove_only else "video_source_state"
                result = self.state.states[state_key][result_key]
                self.assertEqual(result["last_scan_start_date"], "2026-10-21")
                self.assertEqual(result["last_scan_end_date"], "2026-10-22")
                with client:
                    calendar.value = "9999-01-01"
                self.assertEqual(calendar.value, "2026-10-21")
                self.assertEqual(self.state.states[state_key][settings_key]["scan_start_date"], "2026-10-21")
                with client:
                    calendar.value = None
                self.assertEqual(self.state.states[state_key][settings_key]["scan_start_date"], "")

        self.delete.assert_not_called()
        self.add.assert_not_called()

    async def test_date_type_select_scans_and_restores_each_audio_task(self):
        today = date(2026, 10, 22)
        zone = timezone(timedelta(hours=7))
        stamp = lambda day: datetime(2026, 10, day, 12, tzinfo=zone).timestamp()
        rows = [
            Video(id="upload", channel_id=self.channel.id, title="upload", description="", thumbnail="", duration_ms=60000,
                  privacy="VIDEO_PRIVACY_PUBLIC", time_created_seconds=stamp(21), time_published_seconds=stamp(19)),
            Video(id="publication", channel_id=self.channel.id, title="publication", description="", thumbnail="", duration_ms=60000,
                  privacy="VIDEO_PRIVACY_PUBLIC", time_created_seconds=stamp(10), time_published_seconds=stamp(21)),
            Video(id="schedule", channel_id=self.channel.id, title="schedule", description="", thumbnail="", duration_ms=60000,
                  privacy="VIDEO_PRIVACY_PRIVATE", time_created_seconds=stamp(10), scheduled_publishing_details={"time": stamp(22)}),
        ]
        for state_key, delete_existing, remove_only in (
            ("audio_add", True, False), ("audio_add_only", False, False), ("audio_remove", True, True),
        ):
            with self.subTest(task=state_key):
                settings_key = "scan_settings" if remove_only else "video_source_state"
                saved = {"selected_channel": self.channel.id} if remove_only else self.saved_add_state()
                saved[settings_key] = {
                    "mode": "failed", "scan_scope": "all", "recent_limit": 50, "scan_start_date": "2026-10-20",
                }
                self.state.states[state_key] = saved
                client = self.render(delete_existing=delete_existing, remove_only=remove_only)
                basis = next(element for element in client.elements.values()
                             if isinstance(element, ui.select) and element._props.get("label") == "Tính theo ngày")
                self.assertEqual(basis.value, "auto")
                module = remove_audio if remove_only else audio
                method = "get_audio_attention_video_ids" if remove_only else "get_terminal_audio_repair_targets"
                for date_type, expected in (("auto", ["publication", "schedule"]), ("uploaded", ["upload"]),
                                            ("published", ["publication"]), ("scheduled", ["schedule"])):
                    with client:
                        basis.value = date_type
                    targets = set(expected) if remove_only else {
                        video_id: [{"language": "en", "track_ids": ["failed"]}] for video_id in expected
                    }
                    with (
                        self.subTest(date_type=date_type),
                        patch("src.video_scan_dates.scan_today", return_value=today),
                        patch.object(module.list_videos_module, "list_all_videos", return_value=(rows, None)),
                        patch.object(module.update_audio_module, method, return_value=targets) as query,
                        client,
                    ):
                        await self.button_callback(client, "Quét video cần xử lý" if remove_only else "Quét ID audio cần xử lý")()
                    self.assertEqual(query.call_args.args[0], expected)
                    self.assertEqual(self.state.states[state_key][settings_key]["scan_date_type"], date_type)
                    result_key = "scan_state" if remove_only else "video_source_state"
                    self.assertEqual(self.state.states[state_key][result_key]["last_scan_date_type"], date_type)
                reopened = self.render(delete_existing=delete_existing, remove_only=remove_only)
                restored = next(element for element in reopened.elements.values()
                                if isinstance(element, ui.select) and element._props.get("label") == "Tính theo ngày")
                self.assertEqual(restored.value, "scheduled")


class AudioTaskRouteTests(unittest.TestCase):
    def test_all_three_task_routes_remain_available(self):
        from web.views import audio as views

        with (
            patch.object(views, "create_drawer"),
            patch.object(views.nav_state, "set_active_route"),
            patch.object(views, "create_add_audio_page") as render_add,
            patch.object(views, "create_remove_audio_page") as render_remove,
        ):
            views.add_audio_page()
            render_add.assert_called_once_with()
            render_add.reset_mock()
            views.add_only_audio_page()
            render_add.assert_called_once_with(delete_existing=False)
            views.remove_audio_page()
            render_remove.assert_called_once_with()
        self.assertTrue({"/audio/add", "/audio/remove", "/audio/add-only"}.issubset(views.router.routes))


if __name__ == "__main__":
    unittest.main()
