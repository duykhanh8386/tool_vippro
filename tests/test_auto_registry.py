import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from src.audio_recovery import (
    RECOVERY_SCAN_MODE_ALL,
    RECOVERY_SCAN_MODE_SELECTED,
    _monitor_failed_caption_tracks,
    get_audio_recovery_registry_items,
    get_audio_recovery_scan_preferences,
    get_audio_recovery_state,
    is_audio_recovery_channel_enabled,
    is_audio_recovery_video_enabled,
    register_audio_recovery,
    run_audio_recovery_cycle,
    set_audio_recovery_items_enabled,
    set_audio_recovery_scan_preferences,
)
from src.state_manager import StateManager


class RegistryStorage:
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path_patch = patch(
            "src.state_manager.get_data_dir", return_value=Path(self.folder.name)
        )
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.manager = StateManager()
        self.state_patch = patch("src.audio_recovery.state_manager", self.manager)
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)
        self.addCleanup(lambda: self.manager._conn.close())
        self.original_entries = {
            "channel-a": {
                "video-shared": {
                    "audio_path": "source.mp3",
                    "languages": ["en", "es"],
                    "attempts": {"en": {"attempted_at": 1, "succeeded": True}},
                    "caption_monitor": {"languages": ["en"]},
                },
                "video-other": {"audio_path": "source.mp3", "languages": ["en"]},
            },
            "channel-b": {
                "video-shared": {"audio_path": "source.mp3", "languages": ["fr"]},
            },
        }
        self.manager.save_state("audio_recovery", {
            "entries": copy.deepcopy(self.original_entries),
            "last_cycle_result": {"repaired": 3},
        })


class AutoRegistryPersistenceTests(RegistryStorage, unittest.TestCase):
    def test_disabled_channels_survive_restart_scope_changes_and_registration(self):
        self.assertTrue(set_audio_recovery_items_enabled(
            enabled=False, channel_ids=[" channel-a ", "channel-a", ""]
        ))
        self.manager._conn.close()
        self.manager._conn = None
        self.assertFalse(is_audio_recovery_channel_enabled("channel-a"))
        self.assertTrue(is_audio_recovery_channel_enabled("channel-b"))
        self.assertEqual(get_audio_recovery_state()["entries"], self.original_entries)
        self.assertEqual(get_audio_recovery_state()["last_cycle_result"], {"repaired": 3})
        set_audio_recovery_scan_preferences(
            scan_mode=RECOVERY_SCAN_MODE_SELECTED, selected_channel_ids=["channel-a"]
        )
        self.assertFalse(is_audio_recovery_channel_enabled("channel-a"))
        set_audio_recovery_scan_preferences(scan_mode=RECOVERY_SCAN_MODE_ALL)
        register_audio_recovery(
            channel_id="channel-a", video_id="new-video", audio_path="new.mp3",
            languages=["en"], repeat_times=1, extra_minutes=0,
        )
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "new-video"))

    def test_video_opt_out_is_scoped_to_channel_and_survives_reregistration(self):
        self.assertTrue(set_audio_recovery_items_enabled(
            enabled=False, video_ids_by_channel={"channel-a": ["video-shared"]}
        ))
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-shared"))
        self.assertTrue(is_audio_recovery_video_enabled("channel-a", "video-other"))
        self.assertTrue(is_audio_recovery_video_enabled("channel-b", "video-shared"))
        register_audio_recovery(
            channel_id="channel-a", video_id="video-shared", audio_path="new.mp3",
            languages=["de"], repeat_times=1, extra_minutes=0,
        )
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-shared"))

    def test_reenabling_channel_preserves_individual_video_opt_outs(self):
        set_audio_recovery_items_enabled(
            enabled=False, channel_ids=["channel-a"],
            video_ids_by_channel={"channel-a": ["video-shared"]},
        )
        set_audio_recovery_scan_preferences(
            scan_mode=RECOVERY_SCAN_MODE_SELECTED, selected_channel_ids=[]
        )
        self.assertTrue(set_audio_recovery_items_enabled(
            enabled=True, channel_ids=["channel-a"]
        ))
        self.assertTrue(is_audio_recovery_channel_enabled("channel-a"))
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-shared"))
        self.assertTrue(is_audio_recovery_video_enabled("channel-a", "video-other"))
        self.assertTrue(set_audio_recovery_items_enabled(
            enabled=True, video_ids_by_channel={"channel-a": ["video-shared"]}
        ))
        self.assertTrue(is_audio_recovery_video_enabled("channel-a", "video-shared"))
        self.assertEqual(get_audio_recovery_state()["disabled_video_ids"], {})

    def test_enabling_video_keeps_parent_channel_disabled(self):
        set_audio_recovery_items_enabled(
            enabled=False, channel_ids=["channel-a"],
            video_ids_by_channel={"channel-a": ["video-shared"]},
        )
        set_audio_recovery_items_enabled(
            enabled=True, video_ids_by_channel={"channel-a": ["video-shared"]}
        )
        self.assertFalse(is_audio_recovery_channel_enabled("channel-a"))
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-shared"))
        channels, videos = get_audio_recovery_registry_items()
        self.assertEqual([row["channel_id"] for row in channels], ["channel-a", "channel-b"])
        self.assertEqual(len(videos), 3)
        video = next(row for row in videos if row["channel_id"] == "channel-a")
        self.assertTrue(video["video_enabled"])
        self.assertFalse(video["channel_enabled"])

    def test_failed_save_leaves_existing_scan_preferences_intact(self):
        with patch.object(self.manager, "save_state", return_value=False):
            self.assertFalse(set_audio_recovery_items_enabled(
                enabled=False, channel_ids=["channel-a"]
            ))
        self.assertTrue(is_audio_recovery_channel_enabled("channel-a"))


class AutoRegistryCycleTests(RegistryStorage, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        caption_patch = patch(
            "src.audio_recovery._monitor_failed_caption_tracks",
            new=AsyncMock(return_value={}),
        )
        caption_patch.start()
        self.addCleanup(caption_patch.stop)

    async def test_cycle_never_scans_disabled_channels_or_videos(self):
        set_audio_recovery_items_enabled(
            enabled=False, channel_ids=["channel-b"],
            video_ids_by_channel={"channel-a": ["video-shared"]},
        )
        visibility = Mock(return_value=({"video-other": True}, set()))
        translations = Mock(return_value={"videoTranslations": [], "audioTracks": []})
        captions = AsyncMock(return_value={})
        with (
            patch("src.audio_recovery._get_registered_video_public_statuses", visibility),
            patch("src.audio_recovery.update_audio_module._get_video_translation_payload", translations),
            patch("src.audio_recovery._monitor_failed_caption_tracks", captions),
        ):
            result = await run_audio_recovery_cycle(now=2000)
        visibility.assert_called_once_with("channel-a", ["video-other"])
        translations.assert_called_once_with(["video-other"], "channel-a")
        self.assertEqual(list(captions.call_args.kwargs["entries"]), ["video-other"])
        self.assertEqual(result["scope_skipped_channel_ids"], ["channel-b"])
        self.assertEqual(get_audio_recovery_state()["entries"], self.original_entries)

    async def test_all_disabled_videos_skip_youtube_calls(self):
        set_audio_recovery_items_enabled(
            enabled=False,
            video_ids_by_channel={
                "channel-a": ["video-shared", "video-other"],
                "channel-b": ["video-shared"],
            },
        )
        with (
            patch("src.audio_recovery._get_registered_video_public_statuses") as visibility,
            patch("src.audio_recovery.update_audio_module._get_video_translation_payload") as translations,
            patch("src.audio_recovery._monitor_failed_caption_tracks", new=AsyncMock()) as captions,
        ):
            result = await run_audio_recovery_cycle(now=2000)
        visibility.assert_not_called()
        translations.assert_not_called()
        captions.assert_not_called()
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["deferred_initial_grace"], 0)

    async def test_disabling_video_during_scan_prevents_upload(self):
        source = Path(self.folder.name) / "source.mp3"
        source.write_bytes(b"source")
        register_audio_recovery(
            channel_id="channel-a", video_id="video-shared", audio_path=str(source),
            languages=["en"], repeat_times=1, extra_minutes=0, registered_at=0,
        )
        set_audio_recovery_items_enabled(
            enabled=False, channel_ids=["channel-b"],
            video_ids_by_channel={"channel-a": ["video-other"]},
        )

        def scan(video_ids, channel_id):
            set_audio_recovery_items_enabled(
                enabled=False, video_ids_by_channel={channel_id: video_ids}
            )
            return {"videoTranslations": [{
                "videoId": "video-shared",
                "translations": [{"languageCode": "en", "audioTranslation": {
                    "status": "AUDIO_TRACK_STATUS_FAILED",
                }}],
            }], "audioTracks": []}

        with (
            patch("src.audio_recovery._get_registered_video_public_statuses", return_value=({"video-shared": True}, set())),
            patch("src.audio_recovery.update_audio_module._get_video_translation_payload", side_effect=scan),
            patch("src.audio_recovery.update_audio_module._get_video_info") as video_info,
            patch("src.audio_recovery.update_audio_module.add") as add,
        ):
            result = await run_audio_recovery_cycle(now=2000)
        video_info.assert_not_called()
        add.assert_not_called()
        self.assertEqual(result["repaired"], 0)

    async def test_disabling_video_during_upload_stops_next_language(self):
        source = Path(self.folder.name) / "source.mp3"
        source.write_bytes(b"source")
        register_audio_recovery(
            channel_id="channel-a", video_id="video-shared", audio_path=str(source),
            languages=["en", "es"], repeat_times=1, extra_minutes=0, registered_at=0,
        )
        set_audio_recovery_items_enabled(
            enabled=False, channel_ids=["channel-b"],
            video_ids_by_channel={"channel-a": ["video-other"]},
        )
        payload = {"videoTranslations": [{
            "videoId": "video-shared",
            "translations": [
                {"languageCode": language, "audioTranslation": {"status": "AUDIO_TRACK_STATUS_FAILED"}}
                for language in ("en", "es")
            ],
        }], "audioTracks": []}

        def render(**kwargs):
            Path(kwargs["output_file"]).write_bytes(b"rendered")

        def upload(**kwargs):
            set_audio_recovery_items_enabled(
                enabled=False, video_ids_by_channel={"channel-a": ["video-shared"]}
            )
            return 200

        async def retry(operation, **kwargs):
            return operation()

        with (
            patch("src.audio_recovery._get_registered_video_public_statuses", return_value=({"video-shared": True}, set())),
            patch("src.audio_recovery.update_audio_module._get_video_translation_payload", return_value=payload),
            patch("src.audio_recovery.update_audio_module._get_video_info", return_value=SimpleNamespace(duration_ms=60000)),
            patch("src.audio_recovery.multiply_audio", side_effect=render),
            patch("src.audio_recovery.call_audio_update_with_retry", new=AsyncMock(side_effect=retry)),
            patch("src.audio_recovery.update_audio_module.add", side_effect=upload) as add,
        ):
            result = await run_audio_recovery_cycle(now=2000)
        self.assertEqual(add.call_count, 1)
        self.assertEqual(add.call_args.kwargs["language"], "en")
        self.assertEqual(result["repaired"], 1)


    async def test_disabling_video_during_caption_translation_prevents_update(self):
        source = Path(self.folder.name) / "source.srt"
        source.write_text("source", encoding="utf-8")
        entry = {"caption_monitor": {
            "source_srt_path": str(source), "source_language": "en",
            "languages": ["fr"], "next_check_at": 0,
        }}
        tracks = [
            {"id": "source", "snippet": {"language": "en", "status": "serving"}},
            {"id": "failed", "snippet": {"language": "fr", "status": "failed"}},
        ]

        def translate(*args):
            set_audio_recovery_items_enabled(
                enabled=False, video_ids_by_channel={"channel-a": ["video-shared"]}
            )
            return b"translated"

        client = SimpleNamespace(
            list_tracks=Mock(return_value=tracks),
            track_language=lambda track: track["snippet"]["language"],
            download_translation=Mock(side_effect=translate),
            upsert_track=Mock(),
        )
        with (
            patch("src.audio_recovery.YouTubeCaptionClient", return_value=client),
            patch("src.audio_recovery.get_caption_quota_status", return_value={}),
        ):
            result = await _monitor_failed_caption_tracks(
                channel_id="channel-a", entries={"video-shared": entry}, cycle_time=2000,
                video_continue_allowed=lambda video_id: is_audio_recovery_video_enabled(
                    "channel-a", video_id
                ),
            )
        client.download_translation.assert_called_once()
        client.upsert_track.assert_not_called()
        self.assertEqual(result["repaired"], 0)


class AutoRegistryUiTests(RegistryStorage, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from nicegui import Client, ui
        from nicegui.page import page
        from web.components.auto_registry import create_auto_registry_content

        self.ui = ui
        self.client = Client(page("/test-auto-registry"), request=None)
        self.addCleanup(self.client.delete)
        names_patch = patch(
            "web.components.auto_registry.get_channels_info", return_value=[]
        )
        names_patch.start()
        self.addCleanup(names_patch.stop)
        notify_patch = patch("web.components.auto_registry.ui.notify")
        self.notify = notify_patch.start()
        self.addCleanup(notify_patch.stop)
        with self.client:
            self.refresh = create_auto_registry_content()
        self.tables = [
            element for element in self.client.elements.values()
            if isinstance(element, ui.table)
        ]

    def click_action(self, text, index=0):
        buttons = [
            element for element in self.client.elements.values()
            if isinstance(element, self.ui.button) and element.text == text
        ]
        button = buttons[index]
        listener = next(
            listener for listener in button._event_listeners.values()
            if listener.type == "click"
        )
        with self.client:
            listener.handler(None)

    def test_channel_action_updates_both_lists_and_preserves_unlisted_channels(self):
        channels, videos = self.tables
        self.assertEqual(len(channels.rows), 2)
        self.assertEqual(len(videos.rows), 3)
        channels.selected = [channels.rows[0]]
        self.click_action("Deactive")
        self.assertFalse(is_audio_recovery_channel_enabled("channel-a"))
        self.assertFalse(channels.rows[0]["enabled"])
        self.assertTrue(channels.rows[1]["enabled"])
        self.assertEqual(channels.selected, [])
        self.assertTrue(all(
            row["status"] == "Deactive"
            and row["inactive_reason"] == "Kênh chưa được phép tự động quét"
            for row in videos.rows if row["channel_id"] == "channel-a"
        ))

    def test_default_scans_all_channels_and_new_channels_start_active(self):
        self.assertEqual(
            get_audio_recovery_scan_preferences()["scan_mode"], RECOVERY_SCAN_MODE_ALL
        )
        self.assertTrue(all(row["status"] == "Active" for row in self.tables[0].rows))
        register_audio_recovery(
            channel_id="channel-new", video_id="video-new", audio_path="new.mp3",
            languages=["en"], repeat_times=1, extra_minutes=0,
        )
        with self.client:
            self.refresh()
        new_channel = next(
            row for row in self.tables[0].rows if row["channel_id"] == "channel-new"
        )
        self.assertEqual(new_channel["status"], "Active")
        self.assertTrue(is_audio_recovery_channel_enabled("channel-new"))

    def test_row_button_keeps_deactive_channel_listed_and_activates_it_again(self):
        channels, videos = self.tables
        original_channel_ids = [row["id"] for row in channels.rows]
        original_video_ids = [row["id"] for row in videos.rows]
        listener = next(
            listener for listener in channels._event_listeners.values()
            if listener.type == "toggleActive"
        )
        with self.client:
            listener.handler(SimpleNamespace(args={"id": "channel-a"}))
        self.assertEqual([row["id"] for row in channels.rows], original_channel_ids)
        self.assertEqual([row["id"] for row in videos.rows], original_video_ids)
        self.assertEqual(channels.rows[0]["status"], "Deactive")
        self.assertFalse(is_audio_recovery_channel_enabled("channel-a"))
        with self.client:
            self.refresh()
            listener.handler(SimpleNamespace(args={"id": "channel-a"}))
        self.assertEqual(channels.rows[0]["status"], "Active")
        self.assertTrue(is_audio_recovery_channel_enabled("channel-a"))
        self.assertEqual(get_audio_recovery_state()["entries"], self.original_entries)

    def test_video_action_uses_channel_and_video_id_and_can_enable_again(self):
        videos = self.tables[1]
        chosen = next(row for row in videos.rows if row["id"] == "channel-a:video-shared")
        videos.selected = [chosen]
        self.click_action("Deactive", index=1)
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-shared"))
        self.assertTrue(is_audio_recovery_video_enabled("channel-b", "video-shared"))
        videos.selected = [next(row for row in videos.rows if row["id"] == chosen["id"])]
        self.click_action("Active", index=1)
        self.assertTrue(is_audio_recovery_video_enabled("channel-a", "video-shared"))

    def test_refresh_preserves_selection_and_failed_save_keeps_checkboxes(self):
        channels = self.tables[0]
        channels.selected = [channels.rows[0]]
        set_audio_recovery_items_enabled(
            enabled=False, video_ids_by_channel={"channel-a": ["video-shared"]}
        )
        with self.client:
            self.refresh()
        self.assertEqual(len(channels.selected), 1)
        self.assertEqual(channels.selected[0]["active_video_count"], 1)
        with patch("web.components.auto_registry.set_audio_recovery_items_enabled", return_value=False):
            self.click_action("Deactive")
        self.assertEqual(len(channels.selected), 1)
        self.assertTrue(is_audio_recovery_channel_enabled("channel-a"))
        self.assertEqual(self.notify.call_args.kwargs["type"], "negative")


if __name__ == "__main__":
    unittest.main()
