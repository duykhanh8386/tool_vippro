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
from src.module.audio_module import AudioUpdateError
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
        self.description_events = []
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
            if kwargs.get("audio_content_type") == "descriptive":
                self.description_events.append("description:" + kwargs["language"])
            else:
                self.events.append("add:" + kwargs["language"])
            return 200

        self.add = self.patches.enter_context(patch.object(audio.update_audio_module, "add", side_effect=add))
        self.patches.enter_context(patch.object(
            audio.update_audio_module, "_get_video_info", return_value=Video(
                id="video", channel_id=self.channel.id, title="", description="", thumbnail="", duration_ms=60000,
            ),
        ))
        self.patches.enter_context(patch.object(audio, "multiply_audio"))
        self.track_states = self.patches.enter_context(patch.object(
            audio.update_audio_module, "get_audio_track_states",
            side_effect=lambda video_id, channel_id, languages: {
                language: {"dubbed": "missing", "descriptive": "missing", "descriptive_track_ids": []}
                for language in languages
            },
        ))
        self.recovery = self.patches.enter_context(patch.object(audio, "register_audio_recovery", return_value=True))
        self.invalidate_description = self.patches.enter_context(patch.object(
            audio, "invalidate_description_completion", return_value=True,
        ))

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

    def audio_type_switches(self, client):
        return {
            element.text: element for element in client.elements.values()
            if isinstance(element, ui.switch) and element.text in {"Audio ngôn ngữ", "Âm thanh mô tả"}
        }

    async def test_upload_errors_stay_compact_and_details_are_collapsed_in_both_add_modes(self):
        for delete_existing, key, button in (
            (True, "audio_add", "Bắt đầu xóa & thêm audio"),
            (False, "audio_add_only", "Bắt đầu thêm audio"),
        ):
            with self.subTest(delete_existing=delete_existing):
                self.state.states[key] = self.saved_add_state()

                def reject(**kwargs):
                    kwargs["progress"].update(registered=True, file_finalized=True)
                    raise AudioUpdateError("AUDIO_TRACK_STATUS_FAILED " + "details " * 1000)

                self.add.side_effect = reject
                client = self.render(delete_existing=delete_existing)
                await self.button_callback(client, button)()
                saved = self.state.states[key]
                self.assertLessEqual(len(saved["video_processing_errors"]["video"]["en"]), 280)
                self.assertLessEqual(len(saved["video_description_errors"]["video"]["en"]), 280)
                details = [element for element in client.elements.values()
                           if isinstance(element, ui.expansion) and "xem chi tiết" in element.text]
                self.assertEqual(len(details), 2)
                self.assertTrue(all(not element.value for element in details))
                message = audio.ui.notify.call_args.args[0]
                self.assertLess(len(message), 200)
                self.assertNotIn("details", message)

    async def test_manual_audio_type_switches_restore_save_and_do_not_change_registry_preferences(self):
        self.state.states["audio_add"] = self.saved_add_state()
        self.state.states["audio_recovery"] = {"audio_content_types": ["dubbed"]}
        client = self.render()
        switches = self.audio_type_switches(client)
        self.assertEqual(set(switches), {"Audio ngôn ngữ", "Âm thanh mô tả"})
        self.assertTrue(all(control.value for control in switches.values()))
        with client:
            switches["Audio ngôn ngữ"].set_value(False)
        self.assertEqual(self.state.states["audio_add"]["audio_content_types"], ["descriptive"])
        reopened = self.render()
        restored = self.audio_type_switches(reopened)
        self.assertFalse(restored["Audio ngôn ngữ"].value)
        self.assertTrue(restored["Âm thanh mô tả"].value)
        self.assertEqual(self.state.states["audio_recovery"], {"audio_content_types": ["dubbed"]})
        with reopened:
            self.button_callback(reopened, "Xóa dữ liệu")()
        self.assertTrue(all(control.value for control in restored.values()))
        self.assertEqual(self.state.states["audio_add"]["audio_content_types"], ["dubbed", "descriptive"])
        self.assertEqual(self.state.states["audio_recovery"], {"audio_content_types": ["dubbed"]})

    async def test_language_only_deletes_and_replaces_failed_dubs_without_touching_descriptions(self):
        saved = self.saved_add_state()
        saved["audio_content_types"] = ["dubbed"]
        self.state.states["audio_add"] = saved
        self.track_states.side_effect = lambda _vid, _channel, languages: {
            lang: {"dubbed": "terminal", "dubbed_track_ids": ["failed-dub-" + lang],
                   "descriptive": "terminal", "descriptive_track_ids": ["failed-desc-" + lang]}
            for lang in languages
        }
        client = self.render()
        await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.events, ["delete_tracks", "add:en", "add:vi"])
        self.assertEqual(self.description_events, [])
        self.assertEqual(self.delete_tracks.call_args.args[2], ["failed-dub-en", "failed-dub-vi"])
        self.invalidate_description.assert_not_called()
        self.assertTrue(all(call.kwargs.get("audio_content_type", "dubbed") == "dubbed"
                            for call in self.add.call_args_list))

    async def test_description_only_replaces_failed_descriptions_without_touching_failed_dubs(self):
        saved = self.saved_add_state()
        saved["audio_content_types"] = ["descriptive"]
        saved["video_processing_errors"] = {"video": {"en": "old dubbed error"}}
        self.state.states["audio_add"] = saved
        self.track_states.side_effect = lambda _vid, _channel, languages: {
            lang: {"dubbed": "terminal", "dubbed_track_ids": ["failed-dub-" + lang],
                   "descriptive": "terminal", "descriptive_track_ids": ["failed-desc-" + lang]}
            for lang in languages
        }
        client = self.render()
        await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.description_events, ["description:en", "description:vi"])
        self.assertEqual(self.events, ["delete_tracks", "delete_tracks"])
        self.assertEqual([call.args[2] for call in self.delete_tracks.call_args_list],
                         [["failed-desc-en"], ["failed-desc-vi"]])
        self.assertTrue(all(call.kwargs["audio_content_type"] == "descriptive" for call in self.add.call_args_list))
        self.assertEqual(audio.ui.notify.call_args.kwargs["type"], "positive")
        self.assertIn("1/1 video thành công", audio.ui.notify.call_args.args[0])

    async def test_description_only_can_add_missing_descriptions_when_normal_audio_is_missing(self):
        saved = self.saved_add_state()
        saved["audio_content_types"] = ["descriptive"]
        self.state.states["audio_add"] = saved
        client = self.render()
        await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.events, [])
        self.assertEqual(self.description_events, ["description:en", "description:vi"])
        self.delete_tracks.assert_not_called()

    async def test_manual_audio_types_both_off_prevents_any_delete_or_upload(self):
        saved = self.saved_add_state()
        saved["audio_content_types"] = []
        self.state.states["audio_add"] = saved
        client = self.render()
        await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.track_states.assert_not_called()
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.add.assert_not_called()
        self.assertFalse(audio._ADD_AUDIO_RUN_GUARD.locked())
        self.assertIn("Hãy bật", audio.ui.notify.call_args.args[0])

    async def test_single_audio_type_preserves_published_and_processing_tracks_without_rendering(self):
        for kind in ("dubbed", "descriptive"):
            for track_state in ("healthy", "inflight"):
                with self.subTest(kind=kind, track_state=track_state):
                    saved = self.saved_add_state()
                    saved["audio_content_types"] = [kind]
                    self.state.states["audio_add"] = saved
                    self.track_states.side_effect = lambda _vid, _channel, languages: {
                        lang: {"dubbed": track_state, "descriptive": track_state} for lang in languages
                    }
                    client = self.render()
                    with patch.object(audio, "multiply_audio") as render:
                        await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
                    render.assert_not_called()
        self.add.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.delete.assert_not_called()

    async def test_single_audio_type_keeps_scanned_language_scope_and_deletes_only_selected_track_type(self):
        targets = {"video": [{"language": "en", "reason": "terminal", "track_ids": ["failed-dub-en"]}]}
        for kind in ("dubbed", "descriptive"):
            with self.subTest(kind=kind):
                saved = self.saved_add_state()
                saved["audio_content_types"] = [kind]
                saved["video_source_state"].update({
                    "mode": "failed", "failed_channel": self.channel.id, "failed_targets": targets,
                })
                self.state.states["audio_add"] = saved
                self.track_states.side_effect = lambda _vid, _channel, languages: {
                    lang: {"dubbed": "terminal", "dubbed_track_ids": ["failed-dub-" + lang],
                           "descriptive": "terminal", "descriptive_track_ids": ["failed-desc-" + lang]}
                    for lang in languages
                }
                self.add.reset_mock()
                self.delete_tracks.reset_mock()
                client = self.render()
                with patch.object(audio.update_audio_module, "get_terminal_audio_repair_targets", return_value=targets):
                    await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
                self.add.assert_called_once()
                self.assertEqual(self.add.call_args.kwargs["language"], "en")
                self.assertEqual(self.add.call_args.kwargs.get("audio_content_type", "dubbed"), kind)
                self.delete_tracks.assert_called_once()
                self.assertEqual(self.delete_tracks.call_args.args[2],
                                 ["failed-dub-en" if kind == "dubbed" else "failed-desc-en"])

    async def test_switching_to_description_only_after_language_only_adds_just_missing_descriptions(self):
        saved = self.saved_add_state()
        saved["audio_content_types"] = ["dubbed"]
        self.state.states["audio_add"] = saved
        client = self.render()
        await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.events, ["add:en", "add:vi"])
        self.assertEqual(self.description_events, [])
        switches = self.audio_type_switches(client)
        with client:
            switches["Audio ngôn ngữ"].set_value(False)
            switches["Âm thanh mô tả"].set_value(True)
        await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.events, ["add:en", "add:vi"])
        self.assertEqual(self.description_events, ["description:en", "description:vi"])
        self.assertEqual(self.add.call_count, 4)
        self.assertEqual(self.state.states["audio_add"]["video_processing_status"]["video"],
                         {"en": "successful", "vi": "successful"})

    async def test_audio_type_change_is_rejected_while_a_manual_audio_run_owns_configuration(self):
        self.state.states["audio_add"] = self.saved_add_state()
        client = self.render()
        switch = self.audio_type_switches(client)["Audio ngôn ngữ"]
        self.assertTrue(audio._ADD_AUDIO_RUN_GUARD.acquire(blocking=False))
        try:
            with client:
                switch.set_value(False)
            self.assertTrue(switch.value)
            self.assertEqual(self.state.states["audio_add"].get("audio_content_types", ["dubbed", "descriptive"]),
                             ["dubbed", "descriptive"])
        finally:
            audio._ADD_AUDIO_RUN_GUARD.release()

    async def test_combined_workflow_deletes_only_failed_dubs_before_uploading_replacements(self):
        self.state.states["audio_add"] = self.saved_add_state()
        self.track_states.side_effect = lambda _vid, _channel, languages: {
            lang: {"dubbed": "terminal", "dubbed_track_ids": ["failed-" + lang], "descriptive": "missing"}
            for lang in languages
        }
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.events, ["delete_tracks", "add:en", "add:vi"])
        self.delete.assert_not_called()
        self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed-en", "failed-vi"])
        self.assertEqual(self.description_events, ["description:en", "description:vi"])
        self.assertEqual([
            (call.kwargs["language"], call.kwargs.get("audio_content_type", "dubbed"))
            for call in self.add.call_args_list
        ], [("en", "dubbed"), ("en", "descriptive"), ("vi", "dubbed"), ("vi", "descriptive")])
        self.assertEqual(self.state.states["audio_add"]["video_description_status"]["video"], {
            "en": "successful", "vi": "successful",
        })
        self.assertEqual(self.state.states["audio_add"]["video_cleanup_status"]["video"], "successful")
        self.assertNotIn("audio_add_only", self.state.states)
        self.assertFalse(get_audio_mutation_guard(self.channel.id).locked())

    async def test_description_checkpoint_exists_before_the_next_language_starts_in_both_add_modes(self):
        for delete_existing, state_key, button in (
            (True, "audio_add", "Bắt đầu xóa & thêm audio"),
            (False, "audio_add_only", "Bắt đầu thêm audio"),
        ):
            with self.subTest(delete_existing=delete_existing):
                self.state.states[state_key] = self.saved_add_state()
                self.add.reset_mock()

                def upload(**kwargs):
                    if kwargs["language"] == "vi" and kwargs.get("audio_content_type") != "descriptive":
                        saved = self.state.states[state_key]
                        self.assertEqual(saved["video_description_status"]["video"]["en"], "successful")
                    return 200

                self.add.side_effect = upload
                client = self.render(delete_existing=delete_existing)
                with client:
                    await self.button_callback(client, button)()
                self.assertEqual([
                    (call.kwargs["language"], call.kwargs.get("audio_content_type", "dubbed"))
                    for call in self.add.call_args_list
                ], [("en", "dubbed"), ("en", "descriptive"), ("vi", "dubbed"), ("vi", "descriptive")])

    async def test_resume_twelve_normal_tracks_fills_descriptions_before_the_seven_remaining_language_pairs(self):
        languages = "en-AU en-CA en-US pt de de-CH ru ru-Latn es es-US nl nl-BE nl-NL it ja fr th km my".split()
        saved = self.saved_add_state()
        saved.update({"selected_languages": languages,
                      "video_processing_status": {"video": {lang: "successful" for lang in languages[:12]}}})
        self.state.states["audio_add"] = saved
        self.track_states.side_effect = lambda _vid, _channel, requested: {
            lang: {"dubbed": "inflight" if lang in languages[:12] else "missing", "descriptive": "missing"}
            for lang in requested
        }

        def upload(**kwargs):
            if kwargs.get("audio_content_type") != "descriptive":
                descriptions = self.state.states["audio_add"]["video_description_status"]["video"]
                for lang in languages[:languages.index(kwargs["language"])]:
                    self.assertEqual(descriptions[lang], "successful")
            return 200

        self.add.side_effect = upload
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        expected = [(lang, "descriptive") for lang in languages[:12]]
        expected += [(lang, kind) for lang in languages[12:] for kind in ("dubbed", "descriptive")]
        self.assertEqual([
            (call.kwargs["language"], call.kwargs.get("audio_content_type", "dubbed"))
            for call in self.add.call_args_list
        ], expected)
        self.assertEqual(set(self.state.states["audio_add"]["video_description_status"]["video"]), set(languages))
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()

    async def test_combined_manual_keeps_published_dub_and_repairs_only_failed_language(self):
        self.state.states["audio_add"] = self.saved_add_state()
        states = {
            "en": {"dubbed": "healthy", "descriptive": "missing"},
            "vi": {"dubbed": "terminal", "dubbed_track_ids": ["failed-vi"], "descriptive": "missing"},
        }
        self.track_states.side_effect = lambda _vid, _channel, languages: {lang: states[lang] for lang in languages}
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.delete.assert_not_called()
        self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed-vi"])
        self.assertEqual(self.events, ["delete_tracks", "add:vi"])
        self.assertEqual(self.description_events, ["description:en", "description:vi"])
        self.assertEqual(self.state.states["audio_add"]["video_processing_status"]["video"]["en"], "already_added")

    async def test_combined_keeps_all_processed_or_published_dubs_and_adds_missing_descriptions(self):
        self.state.states["audio_add"] = self.saved_add_state()
        payload = {"videoTranslations": [{"videoId": "video", "translations": []}], "audioTracks": [
            {"videoId": "video", "audioTrackId": "processed-en", "language": "en",
             "source": "AUDIO_TRACK_SOURCE_CREATOR", "audioContentTypeString": "dubbed",
             "status": "AUDIO_TRACK_STATUS_PROCESSED", "failureReason": "AUDIO_TRACK_FAILURE_REASON_UNSPECIFIED"},
            {"videoId": "video", "audioTrackId": "published-vi", "language": "vi",
             "source": "AUDIO_TRACK_SOURCE_CREATOR", "audioContentTypeString": "dubbed", "publishStatus": "PUBLISHED"},
        ]}
        self.track_states.side_effect = lambda vid, _channel, languages: (
            audio.update_audio_module._audio_track_states_from_payload(payload, vid, languages)
        )
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.assertEqual(self.events, [])
        self.assertEqual(self.description_events, ["description:en", "description:vi"])
        self.assertTrue(all(call.kwargs.get("audio_content_type") == "descriptive" for call in self.add.call_args_list))

    async def test_language_published_during_render_is_not_uploaded_again(self):
        self.state.states["audio_add"] = self.saved_add_state()
        states = {lang: {"dubbed": "missing", "descriptive": "missing"} for lang in ("en", "vi")}
        self.track_states.side_effect = lambda _vid, _channel, languages: {lang: states[lang] for lang in languages}

        def render(**_kwargs):
            for state in states.values():
                state["dubbed"] = "healthy"

        client = self.render()
        with patch.object(audio, "multiply_audio", side_effect=render), client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.assertEqual(self.events, [])
        self.assertEqual(self.description_events, ["description:en", "description:vi"])

    async def test_failed_delete_retry_rechecks_and_keeps_a_newly_published_track(self):
        from src.audio_language import call_audio_update_with_retry as retry
        self.state.states["audio_add"] = self.saved_add_state()
        states = {lang: {"dubbed": "terminal", "dubbed_track_ids": ["failed-" + lang], "descriptive": "missing"}
                  for lang in ("en", "vi")}
        self.track_states.side_effect = lambda _vid, _channel, languages: {lang: states[lang] for lang in languages}

        def fail_delete(*_args):
            for state in states.values():
                state["dubbed"] = "healthy"
            raise AudioUpdateError("retry later", status_code=503, retryable=True)

        async def fast_retry(operation, **kwargs):
            return await retry(operation, sleep=AsyncMock(), **kwargs)

        self.delete_tracks.side_effect = fail_delete
        client = self.render()
        with patch.object(audio, "call_audio_update_with_retry", side_effect=fast_retry), client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.delete_tracks.assert_called_once()
        self.delete.assert_not_called()
        self.assertEqual(self.events, [])
        self.assertEqual(self.description_events, ["description:en", "description:vi"])

    async def test_unreadable_live_audio_state_does_not_delete_or_upload_anything(self):
        self.state.states["audio_add"] = self.saved_add_state()
        self.track_states.side_effect = AudioUpdateError("video state unavailable", status_code=400)
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.add.assert_not_called()

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

    async def test_combined_retry_preserves_published_dubs_and_successful_descriptions(self):
        self.state.states["audio_add"] = self.saved_add_state()
        client = self.render()
        original_add = self.add.side_effect
        failed_once = False

        def add(**kwargs):
            nonlocal failed_once
            if kwargs.get("audio_content_type") == "descriptive" and kwargs["language"] == "en" and not failed_once:
                failed_once = True
                raise AudioUpdateError("description rejected")
            return original_add(**kwargs)

        self.add.side_effect = add
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        saved = self.state.states["audio_add"]
        self.assertEqual(saved["video_processing_status"]["video"], {"en": "successful", "vi": "successful"})
        self.assertEqual(saved["video_description_status"]["video"], {"en": "unsuccessful", "vi": "successful"})
        self.assertEqual(saved["video_description_errors"]["video"]["en"], "description rejected")
        self.track_states.side_effect = lambda _vid, _channel, languages: {
            lang: {"dubbed": "healthy", "descriptive": "missing" if lang == "en" else "healthy"}
            for lang in languages
        }
        reopened = self.render()
        with reopened:
            await self.button_callback(reopened, "Bắt đầu xóa & thêm audio")()
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.assertEqual(self.events, ["add:en", "add:vi"])
        self.assertEqual(self.description_events, ["description:vi", "description:en"])
        self.assertEqual(self.state.states["audio_add"]["video_description_status"]["video"], {"en": "successful", "vi": "already_added"})
        self.assertEqual(self.state.states["audio_add"]["video_description_errors"]["video"], {})

    async def test_normal_processing_failure_is_recorded_and_missing_description_is_still_attempted(self):
        self.state.states["audio_add"] = self.saved_add_state()
        client = self.render()
        original_add = self.add.side_effect

        def add(**kwargs):
            if kwargs.get("audio_content_type") != "descriptive" and kwargs["language"] == "en":
                kwargs["progress"].update(file_finalized=True, registered=True, track_status="AUDIO_TRACK_STATUS_FAILED")
                raise AudioUpdateError("AUDIO_TRACK_STATUS_FAILED")
            return original_add(**kwargs)

        self.add.side_effect = add
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        saved = self.state.states["audio_add"]
        self.assertEqual(saved["video_processing_status"]["video"]["en"], "unsuccessful")
        self.assertEqual(saved["video_description_status"]["video"]["en"], "successful")
        self.assertEqual(self.description_events, ["description:en", "description:vi"])

    async def test_existing_description_is_kept_and_only_the_missing_language_is_uploaded(self):
        self.state.states["audio_add"] = self.saved_add_state()
        self.track_states.side_effect = None
        self.track_states.return_value = {
            "en": {"descriptive": "healthy"}, "vi": {"descriptive": "missing"},
        }
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.description_events, ["description:vi"])
        self.assertEqual(self.state.states["audio_add"]["video_description_status"]["video"]["en"], "already_added")

    async def test_server_rejection_during_normal_transfer_still_allows_its_description(self):
        self.state.states["audio_add"] = self.saved_add_state()
        client = self.render()
        original_add = self.add.side_effect

        def add(**kwargs):
            if kwargs.get("audio_content_type") != "descriptive" and kwargs["language"] == "en":
                kwargs["progress"].update(registered=True, file_finalized=False, server_rejected=True,
                                          studio_state="failed", track_status="AUDIO_TRACK_STATUS_FAILED")
                raise AudioUpdateError("YouTube rejected track during transfer")
            return original_add(**kwargs)

        self.add.side_effect = add
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        saved = self.state.states["audio_add"]
        self.assertEqual(saved["video_processing_status"]["video"]["en"], "unsuccessful")
        self.assertEqual(saved["video_description_status"]["video"]["en"], "successful")
        self.assertEqual(self.description_events, ["description:en", "description:vi"])

    async def test_failed_description_is_deleted_before_reupload_and_healthy_description_is_kept(self):
        self.state.states["audio_add"] = self.saved_add_state()
        self.track_states.side_effect = None
        self.track_states.return_value = {
            "en": {"descriptive": "terminal", "descriptive_track_ids": ["failed-en-description"]},
            "vi": {"descriptive": "healthy", "descriptive_track_ids": []},
        }
        events = []
        original_add = self.add.side_effect

        def delete_failed(video_id, channel_id, track_ids):
            self.assertTrue(get_audio_mutation_guard(self.channel.id).locked())
            self.assertEqual((video_id, channel_id, track_ids), ("video", self.channel.id, ["failed-en-description"]))
            self.assertEqual(self.state.states["audio_add"]["video_description_status"]["video"]["en"], "processing")
            events.append("delete-description")
            return 200

        def add(**kwargs):
            if kwargs.get("audio_content_type") == "descriptive":
                events.append("add-description:" + kwargs["language"])
            return original_add(**kwargs)

        self.delete_tracks.side_effect = delete_failed
        self.add.side_effect = add
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(events, ["delete-description", "add-description:en"])
        self.invalidate_description.assert_called_once_with(self.channel.id, "video", ["en"])
        self.assertEqual(self.description_events, ["description:en"])
        self.assertEqual(self.state.states["audio_add"]["video_description_status"]["video"], {
            "en": "successful", "vi": "already_added",
        })

    async def test_successful_checkpoint_is_rechecked_and_failed_description_is_replaced(self):
        self.state.states["audio_add"] = self.saved_add_state()
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.description_events.clear()
        self.track_states.side_effect = None
        self.track_states.return_value = {
            "en": {"dubbed": "healthy", "descriptive": "terminal", "descriptive_track_ids": ["failed-after-upload"]},
            "vi": {"dubbed": "healthy", "descriptive": "healthy"},
        }
        reopened = self.render()
        with reopened:
            await self.button_callback(reopened, "Bắt đầu xóa & thêm audio")()
        self.delete.assert_not_called()
        self.assertEqual(self.events, ["add:en", "add:vi", "delete_tracks"])
        self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed-after-upload"])
        self.assertEqual(self.description_events, ["description:en"])

    async def test_description_delete_failure_does_not_upload_that_language_and_other_languages_continue(self):
        self.state.states["audio_add"] = self.saved_add_state()
        self.track_states.side_effect = None
        self.track_states.return_value = {
            "en": {"descriptive": "terminal", "descriptive_track_ids": ["failed-en-description"]},
            "vi": {"descriptive": "missing"},
        }
        self.delete_tracks.side_effect = RuntimeError("delete description failed")
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.description_events, ["description:vi"])
        saved = self.state.states["audio_add"]
        self.assertEqual(saved["video_description_status"]["video"], {"en": "unsuccessful", "vi": "successful"})
        self.assertEqual(saved["video_description_errors"]["video"]["en"], "delete description failed")

    async def test_failed_description_is_replaced_even_when_the_dub_upload_fails(self):
        self.state.states["audio_add"] = self.saved_add_state()
        self.track_states.side_effect = None
        self.track_states.return_value = {
            "en": {"descriptive": "terminal", "descriptive_track_ids": ["failed-en-description"]},
            "vi": {"descriptive": "inflight"},
        }
        original_add = self.add.side_effect

        def add(**kwargs):
            if kwargs["language"] == "en" and kwargs.get("audio_content_type") != "descriptive":
                raise RuntimeError("dub upload failed")
            return original_add(**kwargs)

        self.add.side_effect = add
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed-en-description"])
        self.assertEqual(self.description_events, ["description:en"])
        self.assertEqual(self.state.states["audio_add"]["video_description_status"]["video"]["en"], "successful")

    async def test_failed_registry_checkpoint_prevents_description_delete_and_upload(self):
        self.state.states["audio_add"] = self.saved_add_state()
        self.track_states.side_effect = None
        self.track_states.return_value = {
            "en": {"descriptive": "terminal", "descriptive_track_ids": ["failed-en-description"]},
            "vi": {"descriptive": "healthy"},
        }
        self.invalidate_description.return_value = False
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.delete_tracks.assert_not_called()
        self.assertEqual(self.description_events, [])
        self.assertEqual(self.state.states["audio_add"]["video_description_status"]["video"]["en"], "unsuccessful")

    async def test_failed_description_checkpoint_prevents_delete_and_upload(self):
        self.state.states["audio_add"] = self.saved_add_state()
        self.track_states.side_effect = None
        self.track_states.return_value = {
            "en": {"descriptive": "terminal", "descriptive_track_ids": ["failed-en-description"]},
            "vi": {"descriptive": "healthy"},
        }
        save = self.state.save_state

        def fail_delete_checkpoint(name, state):
            if state.get("video_description_status", {}).get("video", {}).get("en") == "processing":
                return False
            return save(name, state)

        client = self.render()
        with patch.object(self.state, "save_state", side_effect=fail_delete_checkpoint), client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.delete_tracks.assert_not_called()
        self.assertEqual(self.description_events, [])
        self.assertEqual(self.state.states["audio_add"]["video_description_status"]["video"]["en"], "unsuccessful")

    async def test_combined_missing_description_scan_preserves_published_dubs_and_adds_description(self):
        saved = self.saved_add_state()
        saved["selected_languages"] = ["en-AU", "es-419"]
        saved["audio_path_history"] = {self.channel.id: {"video": str(self.music)}}
        saved["video_source_state"].update({"mode": "failed", "audio_filter": "missing_description", "scan_scope": "public"})
        self.state.states["audio_add"] = saved
        self.track_states.side_effect = lambda _vid, _channel, languages: {
            lang: {"dubbed": "healthy", "descriptive": "missing"} for lang in languages
        }
        client = self.render()
        targets = {"video": [{"language": "en-AU", "reason": "missing_description", "track_ids": [], "audio_present": True}]}
        with (
            patch.object(audio, "_fetch_channel_videos", return_value=[Video(
                id="video", channel_id=self.channel.id, title="Video", description="", thumbnail="", duration_ms=60000,
            )]),
            patch.object(audio.update_audio_module, "get_missing_audio_description_targets", return_value=targets) as scan,
            client,
        ):
            await self.button_callback(client, "Quét ID audio cần xử lý")()
            self.assertEqual(scan.call_args.args[2], ["en-AU", "es-419"])
            self.assertEqual(self.state.states["audio_add"]["video_ids"], ["video"])
            self.assertEqual(self.state.states["audio_add"]["video_source_state"]["audio_filter"], "missing_description")
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.events, [])
        self.assertEqual(self.description_events, ["description:en-AU"])
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.assertEqual(scan.call_count, 2)
        reopened = self.render()
        control = next(element for element in reopened.elements.values()
                       if isinstance(element, ui.toggle) and "missing_description" in element.options)
        self.assertEqual(control.value, "missing_description")

    async def test_combined_failed_description_scan_preserves_healthy_dubs_and_replaces_only_descriptions(self):
        saved = self.saved_add_state()
        languages = ["en-AU", "es-MX"]
        saved["selected_languages"] = languages
        targets = {"video": [
            {"language": lang, "reason": "missing_description", "track_ids": [], "audio_present": True}
            for lang in languages
        ]}
        saved["video_source_state"].update({
            "mode": "failed", "audio_filter": "missing_description", "failed_channel": self.channel.id,
            "last_scan_languages": languages, "failed_targets": targets,
        })
        self.state.states["audio_add"] = saved
        self.track_states.side_effect = lambda _vid, _channel, requested: {
            lang: {"dubbed": "healthy", "descriptive": "terminal", "descriptive_track_ids": ["failed-desc-" + lang]}
            for lang in requested
        }
        operations = Mock()
        operations.attach_mock(self.delete, "delete_dubs")
        operations.attach_mock(self.delete_tracks, "delete_description")
        operations.attach_mock(self.add, "add")
        client = self.render()
        with patch.object(audio.update_audio_module, "get_missing_audio_description_targets", return_value=targets), client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.delete.assert_not_called()
        self.assertEqual([
            (call.kwargs["language"], call.kwargs.get("audio_content_type", "dubbed"))
            for call in self.add.call_args_list
        ], [("en-AU", "descriptive"), ("es-MX", "descriptive")])
        self.assertEqual([call[0] for call in operations.mock_calls], [
            "delete_description", "add", "delete_description", "add",
        ])
        self.assertEqual([call.args[2] for call in self.delete_tracks.call_args_list], [
            ["failed-desc-en-AU"], ["failed-desc-es-MX"],
        ])

    async def test_add_only_description_scan_still_preserves_existing_language_audio(self):
        saved = self.saved_add_state()
        targets = {"video": [{"language": "en", "reason": "missing_description", "track_ids": [], "audio_present": True}]}
        saved["video_source_state"].update({
            "mode": "failed", "audio_filter": "missing_description", "failed_channel": self.channel.id,
            "last_scan_languages": ["en", "vi"], "failed_targets": targets,
        })
        self.state.states["audio_add_only"] = saved
        client = self.render(delete_existing=False)
        with patch.object(audio.update_audio_module, "get_missing_audio_description_targets", return_value=targets), client:
            await self.button_callback(client, "Bắt đầu thêm audio")()
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.assertEqual(self.events, [])
        self.assertEqual(self.description_events, ["description:en"])

    async def test_combined_cleanup_failure_prevents_both_dub_and_description_uploads(self):
        self.state.states["audio_add"] = self.saved_add_state()
        self.track_states.side_effect = lambda _vid, _channel, languages: {
            lang: {"dubbed": "terminal", "dubbed_track_ids": ["failed-" + lang], "descriptive": "missing"}
            for lang in languages
        }
        self.delete_tracks.side_effect = RuntimeError("cannot delete language audio")
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.add.assert_not_called()
        self.delete_tracks.assert_called_once()
        self.assertEqual(self.state.states["audio_add"]["video_cleanup_status"]["video"], "unsuccessful")

    async def test_completed_combined_checkpoint_preserves_published_audio_on_the_next_click(self):
        self.state.states["audio_add"] = self.saved_add_state()
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.track_states.side_effect = lambda _vid, _channel, requested: {
            lang: {"dubbed": "healthy", "descriptive": "healthy"} for lang in requested
        }
        reopened = self.render()
        with reopened:
            await self.button_callback(reopened, "Bắt đầu xóa & thêm audio")()
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.assertEqual(self.events, ["add:en", "add:vi"])
        self.assertEqual(self.description_events, ["description:en", "description:vi"])

    async def test_cached_success_does_not_skip_missing_descriptions_on_published_languages(self):
        self.state.states["audio_add"] = self.saved_add_state()
        client = self.render()
        with client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.events.clear()
        self.description_events.clear()
        self.track_states.side_effect = lambda _vid, _channel, languages: {
            lang: {"dubbed": "healthy", "descriptive": "missing"} for lang in languages
        }
        reopened = self.render()
        with reopened:
            await self.button_callback(reopened, "Bắt đầu xóa & thêm audio")()
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.assertEqual(self.events, [])
        self.assertEqual(self.description_events, ["description:en", "description:vi"])

    async def test_description_published_between_scan_and_start_is_not_uploaded_again(self):
        saved = self.saved_add_state()
        saved["video_source_state"].update({
            "mode": "failed", "audio_filter": "missing_description", "failed_channel": self.channel.id,
            "last_scan_languages": ["en", "vi"], "failed_targets": {"video": [{
                "language": "en", "reason": "missing_description", "track_ids": [], "audio_present": True,
            }]},
        })
        self.state.states["audio_add"] = saved
        self.track_states.side_effect = lambda _vid, _channel, languages: {
            lang: {"dubbed": "healthy", "descriptive": "healthy"} for lang in languages
        }
        client = self.render()
        with patch.object(audio.update_audio_module, "get_missing_audio_description_targets", return_value={}), client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.add.assert_not_called()
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()
        self.assertEqual(self.state.states["audio_add"]["video_description_status"]["video"]["en"], "already_added")

    async def test_description_scan_requires_languages_and_never_calls_youtube_for_empty_input(self):
        saved = self.saved_add_state()
        saved["selected_languages"] = []
        saved["video_source_state"].update({"mode": "failed", "audio_filter": "missing_description"})
        self.state.states["audio_add"] = saved
        client = self.render()
        with patch.object(audio, "_fetch_channel_videos") as fetch, client:
            await self.button_callback(client, "Quét ID audio cần xử lý")()
        fetch.assert_not_called()

    async def test_both_videos_use_their_own_full_audio_for_all_fifteen_input_languages(self):
        languages = (
            "en-AU en-CA en-IN en-IE en-GB en-US pt pt-BR pt-PT "
            "es es-419 es-MX es-ES es-US fr"
        ).split()
        other_music = self.music.with_name("other.mp3")
        other_music.write_bytes(b"other full music")
        expected = {"first": self.music.read_bytes(), "second": other_music.read_bytes()}
        saved = self.saved_add_state()
        saved.update({
            "video_ids": ["first", "second"], "selected_languages": languages,
            "id_to_path": {"first": str(self.music), "second": str(other_music)},
        })
        self.state.states["audio_add"] = saved

        def prepare(**kwargs):
            Path(kwargs["output_file"]).write_bytes(Path(kwargs["input_file"]).read_bytes())

        def upload(**kwargs):
            self.assertEqual(Path(kwargs["file_name"]).read_bytes(), expected[kwargs["id_video"]])
            return 200

        self.add.side_effect = upload
        client = self.render()
        with patch.object(audio, "multiply_audio", side_effect=prepare), client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.add.call_count, 60)
        for video_id in expected:
            calls = [call for call in self.add.call_args_list if call.kwargs["id_video"] == video_id]
            self.assertEqual([
                (call.kwargs["language"], call.kwargs.get("audio_content_type", "dubbed"))
                for call in calls
            ], [(language, kind) for language in languages for kind in ("dubbed", "descriptive")])
            self.assertEqual(set(self.state.states["audio_add"]["video_description_status"][video_id]), set(languages))
        self.assertTrue(all(not Path(call.kwargs["file_name"]).exists() for call in self.add.call_args_list))

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
        with patch.object(remove_audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={
            "video": [{"language": "en", "track_ids": ["failed-en"]}],
        }), client:
            await self.button_callback(client, "Bắt đầu xóa")()
        self.assertEqual(self.events, ["delete_tracks"])
        self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed-en"])
        self.delete.assert_not_called()
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
        self.track_states.side_effect = lambda _vid, _channel, languages: {
            lang: {"dubbed": "terminal", "dubbed_track_ids": ["failed-track"], "descriptive": "missing"}
            for lang in languages
        }
        client = self.render()
        with patch.object(audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={
            "video": [{"language": "en", "track_ids": ["failed-track"]}],
        }), client:
            await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
        self.assertEqual(self.events, ["delete_tracks", "add:en"])
        self.delete.assert_not_called()
        self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed-track"])

    async def test_combined_scan_keeps_processing_and_published_language_audio(self):
        for fresh_status in ("PROCESSING", "READY"):
            with self.subTest(fresh_status=fresh_status):
                self.events.clear()
                self.delete_tracks.reset_mock()
                saved = self.saved_add_state()
                saved["video_source_state"]["mode"] = "failed"
                self.state.states["audio_add"] = saved
                client = self.render()

                def payload(status):
                    return {"videoTranslations": [{"videoId": "video", "translations": [
                        {"languageCode": "en", "audioTranslation": {
                            "audioTrackId": "processing-en", "status": "AUDIO_TRACK_STATUS_" + status}},
                        {"languageCode": "vi", "audioTranslation": {
                            "audioTrackId": "published-vi", "publishStatus": "PUBLISHED"}},
                    ]}], "audioTracks": []}

                self.track_states.side_effect = lambda vid, _channel, languages: (
                    audio.update_audio_module._audio_track_states_from_payload(payload(fresh_status), vid, languages)
                )
                with (
                    patch.object(audio, "_fetch_channel_videos", return_value=[Video(
                        id="video", channel_id=self.channel.id, title="Test", description="",
                        thumbnail="", duration_ms=60000,
                    )]),
                    patch.object(audio.update_audio_module, "_get_video_translation_payload",
                                 side_effect=[payload("PROCESSING"), payload(fresh_status)]),
                    client,
                ):
                    await self.button_callback(client, "Quét ID audio cần xử lý")()
                    self.assertEqual(self.state.states["audio_add"]["video_ids"], ["video"])
                    await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
                self.delete_tracks.assert_not_called()
                self.assertEqual(self.events, [])
                self.delete.assert_not_called()

    async def test_single_language_dash_audio_scan_can_add_selected_languages_after_reload(self):
        for delete_existing, state_key in ((True, "audio_add"), (False, "audio_add_only")):
            with self.subTest(delete_existing=delete_existing):
                self.events.clear()
                self.delete.reset_mock()
                self.delete_tracks.reset_mock()
                saved = self.saved_add_state()
                saved["video_source_state"]["mode"] = "failed"
                self.state.states[state_key] = saved
                client = self.render(delete_existing=delete_existing)
                payload = {"videoTranslations": [{"videoId": "video", "translations": [{
                    "languageCode": "es", "audioTranslation": {"statusLabel": "–"},
                    "captionsTranslations": [{"publishStatus": "PUBLISHED"}],
                }]}], "audioTracks": []}
                with (
                    patch.object(audio, "_fetch_channel_videos", return_value=[Video(
                        id="video", channel_id=self.channel.id, title="Single language", description="",
                        thumbnail="", duration_ms=60000,
                    )]),
                    patch.object(audio.update_audio_module, "_get_video_translation_payload", return_value=payload) as fetch,
                ):
                    with client:
                        await self.button_callback(client, "Quét ID audio cần xử lý")()
                    self.assertEqual(self.state.states[state_key]["video_ids"], ["video"])
                    self.assertEqual(self.state.states[state_key]["video_source_state"]["scan_skipped"], 0)
                    # The language selection may change after the channel scan.
                    language_input = next(element for element in client.elements.values()
                                          if isinstance(element, ui.input) and element._props.get("label")
                                          == "Mã ngôn ngữ, cách nhau bởi khoảng trắng")
                    with client:
                        language_input.value = "en fr"
                        listener = next(listener for listener in language_input._event_listeners.values()
                                        if listener.type == "change")
                        listener.handler()
                    self.assertEqual(self.state.states[state_key]["selected_languages"], ["en", "fr"])
                    self.assertTrue(any(
                        isinstance(element, ui.label) and "2 audio cần sửa hoặc thêm" in element.text
                        for element in client.elements.values()
                    ))
                    client = self.render(delete_existing=delete_existing)
                    with client:
                        await self.button_callback(
                            client, "Bắt đầu xóa & thêm audio" if delete_existing else "Bắt đầu thêm audio",
                        )()
                self.assertEqual(self.events, ["add:en", "add:fr"])
                self.assertEqual(fetch.call_count, 2)
                self.delete.assert_not_called()
                self.delete_tracks.assert_not_called()
                self.assertEqual(self.state.states[state_key]["video_processing_status"]["video"], {
                    "en": "successful", "fr": "successful",
                })

    async def test_completely_empty_translations_table_is_excluded_from_add_modes(self):
        empty_translations_cases = [
            [],
            [{"languageCode": "sdp", "audioTranslation": {"statusLabel": "–"}}],
            [{"languageCode": "sdp"}],
        ]
        for translations in empty_translations_cases:
            for delete_existing, state_key in ((True, "audio_add"), (False, "audio_add_only")):
                with self.subTest(translations=translations, delete_existing=delete_existing):
                    self.events.clear()
                    self.delete.reset_mock()
                    self.delete_tracks.reset_mock()
                    saved = self.saved_add_state()
                    saved["video_source_state"]["mode"] = "failed"
                    self.state.states[state_key] = saved
                    client = self.render(delete_existing=delete_existing)
                    payload = {"videoTranslations": [{"videoId": "video", "translations": translations}], "audioTracks": []}
                    with (
                        patch.object(audio, "_fetch_channel_videos", return_value=[Video(
                            id="video", channel_id=self.channel.id, title="Completely empty table", description="",
                            thumbnail="", duration_ms=60000,
                        )]),
                        patch.object(audio.update_audio_module, "_get_video_translation_payload", return_value=payload),
                        client,
                    ):
                        await self.button_callback(client, "Quét ID audio cần xử lý")()
                    self.assertEqual(self.state.states[state_key]["video_ids"], [])
                    self.assertEqual(self.state.states[state_key]["video_source_state"]["scan_skipped"], 0)

    async def test_scans_and_repairs_only_languages_present_in_video(self):
        for delete_existing, state_key in ((True, "audio_add"), (False, "audio_add_only")):
            with self.subTest(delete_existing=delete_existing):
                self.events.clear()
                self.delete.reset_mock()
                self.delete_tracks.reset_mock()
                saved = self.saved_add_state()
                saved["video_source_state"]["mode"] = "failed"
                self.state.states[state_key] = saved
                client = self.render(delete_existing=delete_existing)
                payload = {"videoTranslations": [{"videoId": "video", "translations": [
                    {"languageCode": "es", "audioTranslation": {
                        "audioTrackId": "failed-es", "status": "AUDIO_TRACK_STATUS_FAILED",
                    }},
                    {"languageCode": "en", "audioTranslation": {
                        "audioTrackId": "ready-en", "status": "AUDIO_TRACK_STATUS_READY",
                    }},
                ]}], "audioTracks": []}
                self.track_states.side_effect = lambda vid, _channel, languages: (
                    audio.update_audio_module._audio_track_states_from_payload(payload, vid, languages)
                )
                with (
                    patch.object(audio, "_fetch_channel_videos", return_value=[Video(
                        id="video", channel_id=self.channel.id, title="Video with error", description="",
                        thumbnail="", duration_ms=60000,
                    )]),
                    patch.object(audio.update_audio_module, "_get_video_translation_payload", return_value=payload) as fetch,
                    client,
                ):
                    await self.button_callback(client, "Quét ID audio cần xử lý")()
                    self.assertEqual(self.state.states[state_key]["video_ids"], ["video"])
                    language_input = next(element for element in client.elements.values()
                                          if isinstance(element, ui.input) and element._props.get("label")
                                          == "Mã ngôn ngữ, cách nhau bởi khoảng trắng")
                    with client:
                        language_input.value = "en es fr"
                        listener = next(listener for listener in language_input._event_listeners.values()
                                        if listener.type == "change")
                        listener.handler()
                    self.assertEqual(self.state.states[state_key]["selected_languages"], ["en", "es", "fr"])
                    self.assertTrue(any(
                        isinstance(element, ui.label) and "1 audio cần sửa" in element.text
                        for element in client.elements.values()
                    ))
                    client = self.render(delete_existing=delete_existing)
                    with client:
                        await self.button_callback(
                            client, "Bắt đầu xóa & thêm audio" if delete_existing else "Bắt đầu thêm audio",
                        )()
                if delete_existing:
                    self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed-es"])
                    self.assertEqual(self.events, ["delete_tracks", "add:es"])
                else:
                    self.delete_tracks.assert_not_called()
                    self.assertEqual(self.events, ["add:es"])
                self.assertEqual(fetch.call_count, 2)
                self.delete.assert_not_called()
                self.assertEqual(self.state.states[state_key]["video_processing_status"]["video"], {
                    "es": "successful",
                })

    async def test_dash_audio_scan_rechecks_and_skips_video_when_audio_appears(self):
        for status in ("READY", "PROCESSING"):
            with self.subTest(status=status):
                self.events.clear()
                saved = self.saved_add_state()
                saved["video_source_state"].update({
                    "mode": "failed", "failed_channel": self.channel.id,
                    "failed_targets": {"video": [{"language": "es", "track_ids": ["failed-es"], "reason": "terminal"}]},
                })
                self.state.states["audio_add"] = saved
                client = self.render()
                payload = {"videoTranslations": [{"videoId": "video", "translations": [{
                    "languageCode": "es", "audioTranslation": {},
                }]}], "audioTracks": [{
                    "videoId": "video", "audioTrackId": "new-es", "language": "es",
                    "source": "AUDIO_TRACK_SOURCE_CREATOR", "audioContentTypeString": "dubbed",
                    "status": f"AUDIO_TRACK_STATUS_{status}",
                }]}
                with patch.object(audio.update_audio_module, "_get_video_translation_payload", return_value=payload), client:
                    await self.button_callback(client, "Bắt đầu xóa & thêm audio")()
                self.assertEqual(self.events, [])
                self.delete.assert_not_called()
                self.delete_tracks.assert_not_called()

    async def test_completed_add_only_checkpoint_skips_upload_when_run_again(self):
        self.state.states["audio_add_only"] = self.saved_add_state()
        for _ in range(2):
            client = self.render(delete_existing=False)
            with client:
                await self.button_callback(client, "Bắt đầu thêm audio")()
        self.assertEqual(self.events, ["add:en", "add:vi"])
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()

    async def test_remove_only_waits_for_other_audio_mutations_on_the_same_video(self):
        self.state.states["audio_remove"] = {"selected_channel": self.channel.id, "ids": ["video"]}
        client = self.render(remove_only=True)
        guard = get_audio_mutation_guard(self.channel.id, "video")
        guard.acquire()
        released = False
        try:
            with patch.object(remove_audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={
                "video": [{"track_ids": ["failed"]}],
            }), client:
                async def run_remove():
                    with client:
                        await self.button_callback(client, "Bắt đầu xóa")()

                task = asyncio.create_task(run_remove())
                await asyncio.sleep(0.03)
                self.assertFalse(task.done())
                self.delete_tracks.assert_not_called()
                guard.release()
                released = True
                await asyncio.wait_for(task, 2)
            self.assertFalse(guard.locked())
        finally:
            if not released:
                guard.release()
        self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed"])
        self.delete.assert_not_called()
        self.add.assert_not_called()

    async def test_manual_add_modes_run_beside_auto_upload_on_another_video_in_same_channel(self):
        from src import audio_recovery as recovery
        guard = get_audio_mutation_guard(self.channel.id, "auto-video")
        token = recovery._RUNTIME_CHANNEL_CONTEXT.set((999, self.channel.id))
        try:
            self.assertTrue(guard.acquire(blocking=False))
        finally:
            recovery._RUNTIME_CHANNEL_CONTEXT.reset(token)
        try:
            for delete_existing in (True, False):
                with self.subTest(delete_existing=delete_existing):
                    key = "audio_add" if delete_existing else "audio_add_only"
                    self.state.states[key] = self.saved_add_state()
                    self.events.clear()
                    self.description_events.clear()
                    client = self.render(delete_existing=delete_existing)
                    label = "Bắt đầu xóa & thêm audio" if delete_existing else "Bắt đầu thêm audio"
                    with client:
                        await asyncio.wait_for(self.button_callback(client, label)(), 2)
                    self.assertEqual(self.events, ["add:en", "add:vi"])
                    self.assertEqual(self.description_events, ["description:en", "description:vi"])
                    self.assertTrue(guard.locked())
                    self.assertFalse(get_audio_mutation_guard(self.channel.id, "video").locked())
        finally:
            guard.release()

    async def test_remove_only_runs_while_other_video_on_same_channel_is_busy(self):
        self.state.states["audio_remove"] = {"selected_channel": self.channel.id, "ids": ["video"]}
        client = self.render(remove_only=True)
        guard = get_audio_mutation_guard(self.channel.id, "auto-video")
        self.assertTrue(guard.acquire(blocking=False))
        try:
            with patch.object(remove_audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={
                "video": [{"track_ids": ["failed"]}],
            }), client:
                async def run_remove():
                    with client:
                        await self.button_callback(client, "Bắt đầu xóa")()

                await asyncio.wait_for(run_remove(), 2)
            self.assertTrue(guard.locked())
            self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed"])
            self.assertFalse(get_audio_mutation_guard(self.channel.id, "video").locked())
        finally:
            guard.release()

    async def test_busy_videos_do_not_occupy_all_manual_upload_workers(self):
        from src import audio_recovery as recovery
        videos = ["busy-0", "busy-1", "busy-2", "free"]
        saved = self.saved_add_state()
        saved.update(video_ids=videos, id_to_path=dict.fromkeys(videos, str(self.music)))
        self.state.states["audio_add"] = saved
        guards = [get_audio_mutation_guard(self.channel.id, vid) for vid in videos[:3]]
        token = recovery._RUNTIME_CHANNEL_CONTEXT.set((999, self.channel.id))
        try:
            for guard in guards:
                self.assertTrue(guard.acquire(blocking=False))
        finally:
            recovery._RUNTIME_CHANNEL_CONTEXT.reset(token)
        free_done = asyncio.Event()
        loop = asyncio.get_running_loop()
        seen = []
        original_add = self.add.side_effect

        def add(**kwargs):
            vid = kwargs["id_video"]
            seen.append(vid)
            self.assertTrue(get_audio_mutation_guard(self.channel.id, vid).locked())
            if vid == "free" and kwargs.get("audio_content_type") == "descriptive" and kwargs["language"] == "vi":
                loop.call_soon_threadsafe(free_done.set)
            return original_add(**kwargs)

        self.add.side_effect = add
        client = self.render()
        with client:
            task = asyncio.create_task(self.button_callback(client, "Bắt đầu xóa & thêm audio")())
        try:
            await asyncio.wait_for(free_done.wait(), 2)
            self.assertEqual(set(seen), {"free"})
            self.assertFalse(task.done())
        finally:
            for guard in guards:
                guard.release()
            await asyncio.wait_for(task, 3)
        self.assertEqual(set(seen), set(videos))
        self.assertTrue(all(not guard.locked() for guard in guards))

    async def test_stop_while_waiting_for_video_keeps_auto_lock(self):
        self.state.states["audio_add"] = self.saved_add_state()
        guard = get_audio_mutation_guard(self.channel.id, "video")
        self.assertTrue(guard.acquire(blocking=False))
        client = self.render()
        with client:
            task = asyncio.create_task(self.button_callback(client, "Bắt đầu xóa & thêm audio")())
        try:
            await asyncio.sleep(0.03)
            self.assertFalse(task.done())
            await audio._stop_active_audio_runs()
            await asyncio.wait_for(task, 2)
            self.assertTrue(guard.locked())
            self.add.assert_not_called()
            self.delete_tracks.assert_not_called()
            self.assertFalse(audio._ADD_AUDIO_RUN_GUARD.locked())
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

    async def test_remove_scan_matches_combined_failure_filter_and_skips_videos_without_audio(self):
        rows = [
            ("mixed", [
                {"languageCode": "en", "audioTranslation": {
                    "audioTrackId": "failed-en", "status": "AUDIO_TRACK_STATUS_FAILED",
                }},
                {"languageCode": "vi", "audioTranslation": {
                    "audioTrackId": "ready-vi", "status": "AUDIO_TRACK_STATUS_READY",
                }},
            ]),
            ("processing", [{"languageCode": "en", "audioTranslation": {
                "audioTrackId": "processing-en", "status": "AUDIO_TRACK_STATUS_PROCESSING",
            }}]),
            ("published", [{"languageCode": "en", "audioTranslation": {
                "audioTrackId": "published-en", "publishStatus": "PUBLISHED",
            }}]),
            ("source-ineligible", [{"languageCode": "es", "audioTranslation": {
                "status": "AUDIO_TRACK_STATUS_INELIGIBLE",
            }}]),
            ("no-audio", [{"languageCode": "es", "audioTranslation": {"statusLabel": "–"}}]),
        ]
        videos = [Video(id=video_id, channel_id=self.channel.id, title="", description="",
                        thumbnail="", duration_ms=60000) for video_id, _translations in rows]
        payload = {"videoTranslations": [
            {"videoId": video_id, "translations": translations} for video_id, translations in rows
        ], "audioTracks": []}
        for remove_only, state_key in ((False, "audio_add"), (True, "audio_remove")):
            with self.subTest(remove_only=remove_only):
                if remove_only:
                    self.state.states[state_key] = {"selected_channel": self.channel.id}
                else:
                    saved = self.saved_add_state()
                    saved["video_source_state"]["mode"] = "failed"
                    self.state.states[state_key] = saved
                client = self.render(remove_only=remove_only)
                module = remove_audio if remove_only else audio
                with (
                    patch.object(module, "_fetch_channel_videos", return_value=videos),
                    patch.object(module.update_audio_module, "_get_video_translation_payload", return_value=payload),
                    client,
                ):
                    await self.button_callback(
                        client, "Quét video cần xử lý" if remove_only else "Quét ID audio cần xử lý",
                    )()
                self.assertEqual(self.state.states[state_key]["ids" if remove_only else "video_ids"],
                                 ["mixed", "processing"])
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()

    async def test_remove_scanned_video_deletes_failed_and_processing_tracks_and_preserves_good_audio(self):
        self.state.states["audio_remove"] = {"selected_channel": self.channel.id}
        client = self.render(remove_only=True)
        payload = {"videoTranslations": [{"videoId": "video", "translations": [
            {"languageCode": "en", "audioTranslation": {
                "audioTrackId": "failed-en", "status": "AUDIO_TRACK_STATUS_FAILED",
            }},
            {"languageCode": "vi", "audioTranslation": {
                "audioTrackId": "ready-vi", "status": "AUDIO_TRACK_STATUS_READY",
            }},
            {"languageCode": "fr", "audioTranslation": {
                "audioTrackId": "processing-fr", "status": "AUDIO_TRACK_STATUS_PROCESSING",
            }},
        ]}], "audioTracks": []}
        with (
            patch.object(remove_audio, "_fetch_channel_videos", return_value=[SimpleNamespace(id="video")]),
            patch.object(remove_audio.update_audio_module, "_get_video_translation_payload", return_value=payload) as fetch,
        ):
            with client:
                await self.button_callback(client, "Quét video cần xử lý")()
            # Reopening the page must still recheck the current audio state.
            client = self.render(remove_only=True)
            with client:
                await self.button_callback(client, "Bắt đầu xóa")()
        self.assertEqual(fetch.call_count, 2)
        self.delete.assert_not_called()
        self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed-en", "processing-fr"])
        self.add.assert_not_called()
        self.assertEqual(self.state.states["audio_remove"]["video_processing_status"]["video"], "successful")

    async def test_remove_recheck_skips_videos_without_deletable_failed_tracks(self):
        for audio_translation in (
            {"audioTrackId": "ready-en", "status": "AUDIO_TRACK_STATUS_READY"},
            {"status": "AUDIO_TRACK_STATUS_PROCESSING"},
            {"statusLabel": "–"},
            {"status": "AUDIO_TRACK_STATUS_FAILED"},
        ):
            with self.subTest(audio_translation=audio_translation):
                self.state.states["audio_remove"] = {
                    "selected_channel": self.channel.id, "ids": ["video"],
                }
                client = self.render(remove_only=True)
                payload = {"videoTranslations": [{"videoId": "video", "translations": [
                    {"languageCode": "en", "audioTranslation": audio_translation},
                ]}], "audioTracks": []}
                with patch.object(remove_audio.update_audio_module, "_get_video_translation_payload", return_value=payload), client:
                    await self.button_callback(client, "Bắt đầu xóa")()
                saved = self.state.states["audio_remove"]
                self.assertEqual(saved["video_processing_status"]["video"], "skipped")
                self.assertEqual(saved["delete_requested"], {})
                self.delete.assert_not_called()
                self.delete_tracks.assert_not_called()

    async def test_remove_recheck_omitted_video_is_an_error_and_is_not_deleted(self):
        self.state.states["audio_remove"] = {"selected_channel": self.channel.id, "ids": ["video"]}
        client = self.render(remove_only=True)
        with patch.object(remove_audio.update_audio_module, "_get_video_translation_payload", return_value={
            "videoTranslations": [], "audioTracks": [],
        }), client:
            await self.button_callback(client, "Bắt đầu xóa")()
        self.assertEqual(self.state.states["audio_remove"]["video_processing_status"]["video"], "unsuccessful")
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()

    async def test_remove_resume_preserves_remaining_healthy_audio(self):
        self.state.states["audio_remove"] = {
            "selected_channel": self.channel.id, "ids": ["video"],
            "delete_requested": {"video": True}, "video_processing_status": {"video": "processing"},
        }
        client = self.render(remove_only=True)
        with (
            patch.object(remove_audio.update_audio_module, "_get_all_audio_track_ids") as discover,
            patch.object(remove_audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={}),
            client,
        ):
            await self.button_callback(client, "Bắt đầu xóa")()
        self.assertEqual(self.state.states["audio_remove"]["video_processing_status"]["video"], "skipped")
        discover.assert_not_called()
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()

    async def test_remove_recheck_excludes_track_that_became_ready_since_scan(self):
        self.state.states["audio_remove"] = {"selected_channel": self.channel.id}
        client = self.render(remove_only=True)

        def payload(en_status):
            return {"videoTranslations": [{"videoId": "video", "translations": [
                {"languageCode": "en", "audioTranslation": {
                    "audioTrackId": "track-en", "status": f"AUDIO_TRACK_STATUS_{en_status}",
                }},
                {"languageCode": "vi", "audioTranslation": {
                    "audioTrackId": "failed-vi", "status": "AUDIO_TRACK_STATUS_FAILED",
                }},
            ]}], "audioTracks": []}

        with (
            patch.object(remove_audio, "_fetch_channel_videos", return_value=[SimpleNamespace(id="video")]),
            patch.object(remove_audio.update_audio_module, "_get_video_translation_payload",
                         side_effect=[payload("FAILED"), payload("READY")]),
            client,
        ):
            await self.button_callback(client, "Quét video cần xử lý")()
            await self.button_callback(client, "Bắt đầu xóa")()
        self.delete_tracks.assert_called_once_with("video", self.channel.id, ["failed-vi"])
        self.delete.assert_not_called()

    async def test_remove_retry_rechecks_remaining_failed_tracks_after_uncertain_delete(self):
        self.state.states["audio_remove"] = {"selected_channel": self.channel.id, "ids": ["video"]}
        client = self.render(remove_only=True)

        def payload(en_status):
            return {"videoTranslations": [{"videoId": "video", "translations": [
                {"languageCode": "en", "audioTranslation": {
                    "audioTrackId": "track-en", "status": f"AUDIO_TRACK_STATUS_{en_status}",
                }},
                {"languageCode": "vi", "audioTranslation": {
                    "audioTrackId": "failed-vi", "status": "AUDIO_TRACK_STATUS_FAILED",
                }},
            ]}], "audioTracks": []}

        with (
            patch.object(remove_audio.update_audio_module, "_get_video_translation_payload",
                         side_effect=[payload("FAILED"), payload("READY")]),
            patch.object(remove_audio.update_audio_module, "delete_track_ids", side_effect=[
                TimeoutError("response lost after partial deletion"), 200,
            ]) as delete_tracks,
        ):
            with client:
                await self.button_callback(client, "Bắt đầu xóa")()
            saved = self.state.states["audio_remove"]
            self.assertEqual(saved["video_processing_status"]["video"], "unsuccessful")
            self.assertEqual(saved["delete_requested"]["video"], ["track-en", "failed-vi"])
            client = self.render(remove_only=True)
            with client:
                await self.button_callback(client, "Bắt đầu xóa")()
        self.assertEqual([call.args for call in delete_tracks.call_args_list], [
            ("video", self.channel.id, ["track-en", "failed-vi"]),
            ("video", self.channel.id, ["failed-vi"]),
        ])
        self.assertEqual(self.state.states["audio_remove"]["video_processing_status"]["video"], "successful")
        self.assertEqual(self.state.states["audio_remove"]["delete_requested"], {})
        self.delete.assert_not_called()

    async def test_remove_resume_completes_exact_delete_when_only_healthy_tracks_remain(self):
        self.state.states["audio_remove"] = {
            "selected_channel": self.channel.id, "ids": ["video"],
            "delete_requested": {"video": ["removed-en"]},
            "video_processing_status": {"video": "processing"},
        }
        client = self.render(remove_only=True)
        with patch.object(remove_audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={}), client:
            await self.button_callback(client, "Bắt đầu xóa")()
        self.assertEqual(self.state.states["audio_remove"]["video_processing_status"]["video"], "successful")
        self.assertEqual(self.state.states["audio_remove"]["delete_requested"], {})
        self.delete.assert_not_called()
        self.delete_tracks.assert_not_called()

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

        def find_failures(video_ids, channel_id, unreadable, *, include_processing=False):
            self.assertTrue(include_processing)
            unreadable.append("draft-1")
            return {
                video_id: [{"language": "en", "track_ids": ["failed-" + video_id]}]
                for video_id in ("draft-0", "draft-2")
            }

        with (
            patch.object(remove_audio.list_videos_module, "list_all_videos", return_value=(
                [SimpleNamespace(id=f"draft-{i}") for i in range(5)], "unused"),
            ) as fetch,
            patch.object(remove_audio.update_audio_module, "get_terminal_audio_repair_targets", side_effect=find_failures) as scan,
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
                    patch.object(remove_audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={
                        video_id: [{"language": "en", "track_ids": ["failed-" + video_id]}]
                        for video_id in expected
                    }) as scan,
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
            patch.object(remove_audio.update_audio_module, "get_terminal_audio_repair_targets", return_value={}),
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
                method = "get_terminal_audio_repair_targets"
                targets = {"eligible": [{"language": "en", "track_ids": ["failed"]}]}
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
                method = "get_terminal_audio_repair_targets"
                for date_type, expected in (("auto", ["publication", "schedule"]), ("uploaded", ["upload"]),
                                            ("published", ["publication"]), ("scheduled", ["schedule"])):
                    with client:
                        basis.value = date_type
                    targets = {
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
