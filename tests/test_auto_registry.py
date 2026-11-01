import copy
from datetime import date, datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from src.audio_recovery import (
    DEFAULT_RECOVERY_CONCURRENCY_MODE,
    PROCESSING_WARNING_REASON,
    RECOVERY_CONCURRENCY_MODE_CHANNELS,
    RECOVERY_CONCURRENCY_MODE_VIDEOS,
    RECOVERY_SCAN_MODE_ALL,
    RECOVERY_SCAN_MODE_SELECTED,
    RECOVERY_VIDEO_SCOPE_BOTH,
    RECOVERY_VIDEO_SCOPE_PUBLIC,
    RECOVERY_VIDEO_SCOPE_SCHEDULED,
    _monitor_failed_caption_tracks,
    get_audio_recovery_registry_items,
    get_audio_recovery_scan_preferences,
    get_audio_recovery_state,
    get_audio_recovery_runtime_status,
    import_add_audio_flow_recovery_state,
    is_audio_recovery_channel_enabled,
    is_audio_recovery_video_enabled,
    is_audio_recovery_enabled,
    register_audio_recovery,
    remove_audio_recovery_items,
    run_audio_recovery_cycle,
    set_audio_recovery_items_enabled,
    set_audio_recovery_scan_preferences,
    set_audio_recovery_enabled,
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
    def test_master_switch_survives_restart_and_preserves_registry_and_opt_outs(self):
        set_audio_recovery_items_enabled(
            enabled=False, video_ids_by_channel={"channel-a": ["video-other"]},
        )
        before = get_audio_recovery_state()
        self.assertTrue(set_audio_recovery_enabled(False))
        self.manager._conn.close()
        self.manager._conn = None
        saved = get_audio_recovery_state()
        self.assertFalse(saved["enabled"])
        self.assertFalse(is_audio_recovery_enabled())
        self.assertFalse(is_audio_recovery_channel_enabled("channel-a"))
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-shared"))
        self.assertEqual(saved["entries"], before["entries"])
        self.assertEqual(saved["disabled_video_ids"], before["disabled_video_ids"])
        self.assertEqual(saved["last_cycle_result"], before["last_cycle_result"])
        self.assertTrue(set_audio_recovery_enabled(True))
        self.assertTrue(is_audio_recovery_video_enabled("channel-a", "video-shared"))
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-other"))

    def test_registering_more_audio_does_not_enable_the_master_switch(self):
        self.assertTrue(set_audio_recovery_enabled(False))
        self.assertTrue(register_audio_recovery(
            channel_id="channel-new", video_id="video-new", audio_path="music.mp3",
            languages=["en"], repeat_times=1, extra_minutes=0,
        ))
        self.assertFalse(is_audio_recovery_enabled())
        self.assertFalse(get_audio_recovery_runtime_status()["enabled"])
        self.assertIn("video-new", get_audio_recovery_state()["entries"]["channel-new"])

    def test_master_switch_failed_save_does_not_change_saved_or_runtime_state(self):
        self.assertTrue(set_audio_recovery_enabled(True))
        with patch.object(self.manager, "save_state", return_value=False):
            self.assertFalse(set_audio_recovery_enabled(False))
        self.assertTrue(is_audio_recovery_enabled())
        self.assertTrue(get_audio_recovery_runtime_status()["enabled"])

    def test_legacy_scan_and_repair_delays_are_removed_without_changing_entries(self):
        for interval in (15 * 60, 6 * 60 * 60):
            with self.subTest(interval=interval):
                self.manager.save_state("audio_recovery", {
                    "entries": self.original_entries, "interval_seconds": interval,
                    "initial_grace_seconds": interval, "retry_cooldown_seconds": interval,
                    "stale_processing_seconds": 6 * 60 * 60,
                })
                state = get_audio_recovery_state()
                self.assertEqual(state["interval_seconds"], 0)
                self.assertEqual(state["initial_grace_seconds"], 0)
                self.assertEqual(state["retry_cooldown_seconds"], 0)
                self.assertEqual(state["stale_processing_seconds"], 2 * 60 * 60)
                self.assertEqual(state["entries"], self.original_entries)

    def test_processing_warning_survives_restart_and_is_available_in_registry(self):
        state = get_audio_recovery_state()
        tracker = {
            "language": "en", "track_ids": ["processing-en"],
            "first_seen_at": 1000, "last_seen_at": 22600, "scan_count": 2,
            "warning_reason": PROCESSING_WARNING_REASON, "warned_at": 22600,
        }
        state["entries"]["channel-a"]["video-shared"]["description_processing_observations"] = {"en": tracker}
        self.assertTrue(self.manager.save_state("audio_recovery", state))
        self.manager._conn.close()
        self.manager._conn = None

        channels, videos = get_audio_recovery_registry_items()
        channel = next(item for item in channels if item["channel_id"] == "channel-a")
        video = next(item for item in videos if item["channel_id"] == "channel-a"
                     and item["video_id"] == "video-shared")
        self.assertEqual(channel["processing_warning_count"], 1)
        self.assertEqual(video["processing_warnings"], [{
            "language": "en", "track_ids": ["processing-en"],
            "reason": PROCESSING_WARNING_REASON,
            "first_seen_at": 1000, "last_seen_at": 22600, "warned_at": 22600,
        }])

    def test_video_scope_survives_restart_without_changing_channel_preferences(self):
        set_audio_recovery_scan_preferences(
            scan_mode=RECOVERY_SCAN_MODE_SELECTED, selected_channel_ids=["channel-a"]
        )
        set_audio_recovery_items_enabled(
            enabled=False, video_ids_by_channel={"channel-a": ["video-other"]}
        )
        for scope in (RECOVERY_VIDEO_SCOPE_SCHEDULED, RECOVERY_VIDEO_SCOPE_BOTH):
            with self.subTest(scope=scope):
                self.assertTrue(set_audio_recovery_scan_preferences(video_scan_scope=scope))
                self.manager._conn.close()
                self.manager._conn = None
                preferences = get_audio_recovery_scan_preferences()
                self.assertEqual(preferences["video_scan_scope"], scope)
                self.assertEqual(preferences["scan_mode"], RECOVERY_SCAN_MODE_SELECTED)
                self.assertEqual(preferences["selected_channel_ids"], ["channel-a"])
                self.assertEqual(get_audio_recovery_state()["entries"], self.original_entries)
                self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-other"))
        set_audio_recovery_scan_preferences(scan_mode=RECOVERY_SCAN_MODE_ALL)
        self.assertEqual(
            get_audio_recovery_scan_preferences()["video_scan_scope"], RECOVERY_VIDEO_SCOPE_BOTH
        )

    def test_missing_or_invalid_video_scope_defaults_to_public(self):
        self.assertEqual(
            get_audio_recovery_scan_preferences()["video_scan_scope"], RECOVERY_VIDEO_SCOPE_PUBLIC
        )
        for invalid in ("unknown", None, []):
            with self.subTest(scope=invalid):
                self.manager.save_state("audio_recovery", {
                    "entries": self.original_entries, "video_scan_scope": invalid,
                })
                self.assertEqual(
                    get_audio_recovery_scan_preferences()["video_scan_scope"],
                    RECOVERY_VIDEO_SCOPE_PUBLIC,
                )

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

    def test_removing_channel_removes_all_its_videos_and_scope_settings(self):
        set_audio_recovery_scan_preferences(
            scan_mode=RECOVERY_SCAN_MODE_SELECTED,
            selected_channel_ids=["channel-a", "channel-b"],
        )
        set_audio_recovery_items_enabled(
            enabled=False, channel_ids=["channel-a"],
            video_ids_by_channel={"channel-a": ["video-shared"]},
        )
        self.assertTrue(remove_audio_recovery_items(channel_ids=[" channel-a "]))
        state = get_audio_recovery_state()
        self.assertEqual(state["entries"], {"channel-b": self.original_entries["channel-b"]})
        self.assertEqual(state["selected_channel_ids"], ["channel-b"])
        self.assertEqual(state["disabled_channel_ids"], [])
        self.assertEqual(state["disabled_video_ids"], {})
        self.assertEqual(state["last_cycle_result"], {"repaired": 3})
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-shared"))
        channels, videos = get_audio_recovery_registry_items()
        self.assertEqual([row["channel_id"] for row in channels], ["channel-b"])
        self.assertEqual(len(videos), 1)

    def test_removing_video_keeps_other_videos_and_prunes_empty_channel(self):
        self.assertTrue(remove_audio_recovery_items(
            video_ids_by_channel={"channel-a": ["video-shared"]}
        ))
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-shared"))
        self.assertTrue(is_audio_recovery_video_enabled("channel-b", "video-shared"))
        self.assertTrue(is_audio_recovery_video_enabled("channel-a", "video-other"))
        self.assertTrue(remove_audio_recovery_items(
            video_ids_by_channel={"channel-a": ["video-other"]}
        ))
        self.assertNotIn("channel-a", get_audio_recovery_state()["entries"])
        self.assertIn("channel-b", get_audio_recovery_state()["entries"])

    def test_removed_videos_stay_removed_after_restart_and_legacy_import(self):
        self.manager.save_state("add_audio_flow", {
            "selected_channel": "channel-a",
            "statuses": {
                video_id: {
                    "video_id": video_id, "music_path": "source.mp3",
                    "audio_language_results": {"en": {"status": "successful"}},
                }
                for video_id in ("video-shared", "video-other")
            },
        })
        checkpoint = self.manager.load_state("add_audio_flow")
        remove_audio_recovery_items(channel_ids=["channel-a"])
        self.manager._conn.close()
        self.manager._conn = None
        self.assertEqual(import_add_audio_flow_recovery_state(), 0)
        self.assertNotIn("channel-a", get_audio_recovery_state()["entries"])
        self.assertEqual(self.manager.load_state("add_audio_flow"), checkpoint)

    def test_explicit_registration_can_reenroll_removed_video(self):
        remove_audio_recovery_items(video_ids_by_channel={"channel-a": ["video-shared"]})
        self.assertTrue(register_audio_recovery(
            channel_id="channel-a", video_id="video-shared", audio_path="new.mp3",
            languages=["en"], repeat_times=1, extra_minutes=0,
        ))
        self.assertTrue(is_audio_recovery_video_enabled("channel-a", "video-shared"))
        self.assertNotIn("video-shared", get_audio_recovery_state()["removed_video_ids"].get("channel-a", []))

    def test_failed_remove_leaves_registry_and_preferences_intact(self):
        before = get_audio_recovery_state()
        with patch.object(self.manager, "save_state", return_value=False):
            self.assertFalse(remove_audio_recovery_items(channel_ids=["channel-a"]))
        self.assertEqual(get_audio_recovery_state(), before)


class AutoRegistryCycleTests(RegistryStorage, unittest.IsolatedAsyncioTestCase):
    async def test_disabling_during_upload_finishes_it_without_starting_the_next_track(self):
        from src.audio_recovery import get_audio_mutation_guard

        source = Path(self.folder.name) / "source.mp3"
        source.write_bytes(b"full music")
        register_audio_recovery(
            channel_id="channel-a", video_id="video-shared", audio_path=str(source),
            languages=["en", "es"], repeat_times=1, extra_minutes=0,
        )
        set_audio_recovery_items_enabled(
            enabled=False, channel_ids=["channel-b"],
            video_ids_by_channel={"channel-a": ["video-other"]},
        )
        payload = {"videoTranslations": [], "audioTracks": [
            {
                "videoId": "video-shared", "audioTrackId": "failed-" + language,
                "language": language, "source": "AUDIO_TRACK_SOURCE_CREATOR",
                "audioContentTypeString": "dubbed", "status": "AUDIO_TRACK_STATUS_FAILED",
            } for language in ("en", "es")
        ]}
        temporary_paths = []

        def prepare(**kwargs):
            path = Path(kwargs["output_file"])
            temporary_paths.append(path)
            path.write_bytes(b"full music")

        def upload(**kwargs):
            self.assertTrue(Path(kwargs["file_name"]).exists())
            self.assertTrue(set_audio_recovery_enabled(False))
            return 200

        with (
            patch("src.audio_recovery._get_registered_video_scan_statuses", return_value=({"video-shared": True}, set())),
            patch("src.audio_recovery.update_audio_module._get_video_translation_payload", return_value=payload),
            patch("src.audio_recovery.update_audio_module._get_video_info", return_value=SimpleNamespace(duration_ms=60000)),
            patch("src.audio_recovery.multiply_audio", side_effect=prepare),
            patch("src.audio_recovery.update_audio_module.delete_track_ids", return_value=200) as delete,
            patch("src.audio_recovery.update_audio_module.add", side_effect=upload) as add,
        ):
            result = await run_audio_recovery_cycle(now=2000)
            self.assertEqual(result["repaired"], 1)
            add.assert_called_once()
            self.assertEqual(add.call_args.kwargs["language"], "en")
            delete.assert_not_called()
            self.assertEqual(add.call_args.kwargs["audio_content_type"], "descriptive")
            self.assertFalse(get_audio_recovery_runtime_status()["enabled"])
            self.assertEqual((await run_audio_recovery_cycle())["skipped"], "disabled")
            add.assert_called_once()
        self.assertFalse(is_audio_recovery_enabled())
        self.assertFalse(get_audio_mutation_guard("channel-a").locked())
        self.assertTrue(temporary_paths)
        self.assertTrue(all(not path.exists() for path in temporary_paths))

    async def test_master_switch_off_prevents_audio_and_caption_requests(self):
        self.assertTrue(set_audio_recovery_enabled(False))
        with (
            patch("src.audio_recovery._get_registered_video_scan_statuses") as visibility,
            patch("src.audio_recovery.update_audio_module._get_video_translation_payload") as scan,
            patch("src.audio_recovery.update_audio_module.delete_track_ids") as delete,
            patch("src.audio_recovery.update_audio_module.add") as add,
            patch("src.audio_recovery._monitor_failed_caption_tracks", new=AsyncMock()) as captions,
        ):
            result = await run_audio_recovery_cycle()
        self.assertEqual(result["skipped"], "disabled")
        for operation in (visibility, scan, delete, add):
            operation.assert_not_called()
        captions.assert_not_awaited()
        self.assertEqual(get_audio_recovery_runtime_status()["phase"], "disabled")
        self.assertFalse(get_audio_recovery_runtime_status()["active"])

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
            patch("src.audio_recovery._get_registered_video_scan_statuses", visibility),
            patch("src.audio_recovery.update_audio_module._get_video_translation_payload", translations),
            patch("src.audio_recovery._monitor_failed_caption_tracks", captions),
        ):
            result = await run_audio_recovery_cycle(now=2000)
        visibility.assert_called_once_with("channel-a", ["video-other"], video_scan_scope="public")
        translations.assert_called_once_with(["video-other"], "channel-a")
        self.assertEqual(list(captions.call_args.kwargs["entries"]), ["video-other"])
        self.assertEqual(result["scope_skipped_channel_ids"], ["channel-b"])
        self.assertEqual(get_audio_recovery_state()["entries"], self.original_entries)

    async def test_date_filter_is_applied_before_audio_and_caption_checks(self):
        from src.audio_recovery import _get_registered_video_scan_statuses

        set_audio_recovery_items_enabled(enabled=False, channel_ids=["channel-b"])
        set_audio_recovery_scan_preferences(scan_start_date="2026-10-20", scan_date_type="uploaded")
        zone = timezone(timedelta(hours=7))
        rows = [SimpleNamespace(id=video_id, privacy="VIDEO_PRIVACY_PUBLIC",
                                time_created_seconds=datetime(2026, 10, day, 12, tzinfo=zone).timestamp())
                for video_id, day in (("video-shared", 19), ("video-other", 21))]
        captions = AsyncMock(return_value={})
        payload = {"videoTranslations": [{"videoId": "video-other", "translations": []}],
                   "audioTracks": [{"videoId": "video-other", "audioTrackId": "healthy-en", "language": "en",
                                    "source": "AUDIO_TRACK_SOURCE_CREATOR", "audioContentTypeString": "descriptive",
                                    "status": "AUDIO_TRACK_STATUS_READY"}]}
        with (
            patch("src.video_scan_dates.scan_today", return_value=date(2026, 10, 22)),
            patch("src.audio_recovery._get_registered_video_scan_statuses", side_effect=_get_registered_video_scan_statuses),
            patch("src.audio_recovery.list_videos_module.list_all_videos", return_value=(rows, None)),
            patch("src.audio_recovery.update_audio_module._get_video_translation_payload", return_value=payload) as query,
            patch("src.audio_recovery._monitor_failed_caption_tracks", captions),
        ):
            result = await run_audio_recovery_cycle(now=2000)

        query.assert_called_once_with(["video-other"], "channel-a")
        self.assertEqual(set(captions.await_args.kwargs["entries"]), {"video-other"})
        self.assertEqual(result["deferred_video_scope"], 1)
        self.assertEqual(result["scan_start_date"], "2026-10-20")
        self.assertEqual(get_audio_recovery_state()["entries"]["channel-a"]["video-other"]["audio_path"], "source.mp3")

    async def test_date_type_filters_publication_and_schedules_before_recovery(self):
        from src.audio_recovery import _get_registered_video_scan_statuses

        zone = timezone(timedelta(hours=7))
        stamp = lambda day: datetime(2026, 10, day, 12, tzinfo=zone).timestamp()
        set_audio_recovery_items_enabled(enabled=False, channel_ids=["channel-b"])
        register_audio_recovery(channel_id="channel-a", video_id="scheduled-video", audio_path="source.mp3",
                                languages=["en"], repeat_times=1, extra_minutes=0, registered_at=0)
        rows = [
            SimpleNamespace(id="video-shared", privacy="VIDEO_PRIVACY_PUBLIC", time_created_seconds=stamp(10), time_published_seconds=stamp(21)),
            SimpleNamespace(id="video-other", privacy="VIDEO_PRIVACY_PUBLIC", time_created_seconds=stamp(21), time_published_seconds=stamp(19)),
            SimpleNamespace(id="scheduled-video", privacy="VIDEO_PRIVACY_PRIVATE", time_created_seconds=stamp(10), scheduled_publishing_details={"time": stamp(22)}),
        ]

        def healthy(video_ids, _channel):
            return {"videoTranslations": [{"videoId": vid, "translations": []} for vid in video_ids],
                    "audioTracks": [{"videoId": vid, "audioTrackId": f"healthy-{vid}-{language}", "language": language,
                                     "source": "AUDIO_TRACK_SOURCE_CREATOR", "audioContentTypeString": "descriptive",
                                     "status": "AUDIO_TRACK_STATUS_READY"} for vid in video_ids for language in ("en", "es")]}

        for date_type, expected in (("auto", ["video-shared", "scheduled-video"]),
                                    ("uploaded", ["video-other"]), ("published", ["video-shared"]),
                                    ("scheduled", ["scheduled-video"])):
            fresh = get_audio_recovery_state()
            for entries in fresh["entries"].values():
                for entry in entries.values():
                    for key in list(entry):
                        if key.startswith("description_"):
                            entry.pop(key)
            self.manager.save_state("audio_recovery", fresh)
            set_audio_recovery_scan_preferences(video_scan_scope=RECOVERY_VIDEO_SCOPE_BOTH,
                                                scan_start_date="2026-10-20", scan_date_type=date_type)
            with (
                self.subTest(date_type=date_type), patch("src.video_scan_dates.scan_today", return_value=date(2026, 10, 22)),
                patch("src.audio_recovery._get_registered_video_scan_statuses", side_effect=_get_registered_video_scan_statuses),
                patch("src.audio_recovery.list_videos_module.list_all_videos", return_value=(rows, None)),
                patch("src.audio_recovery.update_audio_module._get_video_translation_payload", side_effect=healthy) as query,
                patch("src.audio_recovery._monitor_failed_caption_tracks", new=AsyncMock(return_value={})) as captions,
            ):
                result = await run_audio_recovery_cycle(now=2000)
            self.assertEqual(query.call_args.args[0], expected)
            self.assertEqual(set(captions.await_args.kwargs["entries"]), set(expected))
            self.assertEqual(result["scan_date_type"], date_type)
            self.assertEqual(result["repaired"], 0)

    async def test_all_disabled_videos_skip_youtube_calls(self):
        set_audio_recovery_items_enabled(
            enabled=False,
            video_ids_by_channel={
                "channel-a": ["video-shared", "video-other"],
                "channel-b": ["video-shared"],
            },
        )
        with (
            patch("src.audio_recovery._get_registered_video_scan_statuses") as visibility,
            patch("src.audio_recovery.update_audio_module._get_video_translation_payload") as translations,
            patch("src.audio_recovery._monitor_failed_caption_tracks", new=AsyncMock()) as captions,
        ):
            result = await run_audio_recovery_cycle(now=2000)
        visibility.assert_not_called()
        translations.assert_not_called()
        captions.assert_not_called()
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["deferred_initial_grace"], 0)

    async def test_removing_video_during_visibility_check_stops_snapshot_scan(self):
        seen = []

        def visibility(channel_id, video_ids, **_kwargs):
            seen.append((channel_id, video_ids))
            if channel_id == "channel-a":
                remove_audio_recovery_items(
                    video_ids_by_channel={"channel-a": ["video-shared"]}
                )
            return {video_id: True for video_id in video_ids}, set()

        with (
            patch("src.audio_recovery._get_registered_video_scan_statuses", side_effect=visibility),
            patch("src.audio_recovery.update_audio_module._get_video_translation_payload", return_value={}) as scan,
        ):
            await run_audio_recovery_cycle(now=2000)
        self.assertIn(("channel-a", ["video-shared", "video-other"]), seen)
        self.assertEqual(
            [(call.args[1], call.args[0]) for call in scan.call_args_list],
            [("channel-a", ["video-other"]), ("channel-b", ["video-shared"])],
        )
        self.assertFalse(is_audio_recovery_video_enabled("channel-a", "video-shared"))

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
            patch("src.audio_recovery._get_registered_video_scan_statuses", return_value=({"video-shared": True}, set())),
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
            patch("src.audio_recovery._get_registered_video_scan_statuses", return_value=({"video-shared": True}, set())),
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
    def test_processing_warning_is_displayed_and_clears_when_resolved(self):
        state = get_audio_recovery_state()
        entry = state["entries"]["channel-a"]["video-shared"]
        entry["description_processing_observations"] = {"en": {
            "language": "en", "track_ids": ["processing-en"],
            "warning_reason": PROCESSING_WARNING_REASON,
        }}
        self.manager.save_state("audio_recovery", state)
        with self.client:
            self.refresh()
        channels, videos = self.tables
        channel = next(item for item in channels.rows if item["channel_id"] == "channel-a")
        video = next(item for item in videos.rows if item["channel_id"] == "channel-a"
                     and item["video_id"] == "video-shared")
        self.assertEqual(channel["processing_warning_count"], 1)
        self.assertEqual(video["processing_warning"], "Đang xử lý lâu: en · Chờ thêm lại mô tả")

        entry.pop("description_processing_observations")
        self.manager.save_state("audio_recovery", state)
        with self.client:
            self.refresh()
        self.assertTrue(all(item["processing_warning_count"] == 0 for item in channels.rows))
        self.assertTrue(all(item["processing_warning"] == "" for item in videos.rows))

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

    def video_scope_control(self):
        return next(
            element for element in self.client.elements.values()
            if isinstance(element, self.ui.toggle)
            and RECOVERY_VIDEO_SCOPE_PUBLIC in element.options
        )

    def concurrency_mode_control(self):
        return next(
            element for element in self.client.elements.values()
            if isinstance(element, self.ui.toggle)
            and RECOVERY_CONCURRENCY_MODE_CHANNELS in element.options
        )

    def test_master_button_toggles_and_refresh_restores_the_saved_choice(self):
        self.click_action("Tắt Auto Registry")
        self.assertFalse(is_audio_recovery_enabled())
        self.assertEqual(get_audio_recovery_state()["entries"], self.original_entries)
        self.assertTrue(all(not row["enabled"] for table in self.tables for row in table.rows))
        with self.client:
            self.refresh()
        self.assertTrue(any(
            isinstance(element, self.ui.button) and element.text == "Bật Auto Registry"
            for element in self.client.elements.values()
        ))
        self.click_action("Bật Auto Registry")
        self.assertTrue(is_audio_recovery_enabled())
        self.assertTrue(all(row["enabled"] for table in self.tables for row in table.rows))

    def test_master_button_reports_failed_save_without_disabling(self):
        with patch("web.components.auto_registry.set_audio_recovery_enabled", return_value=False):
            self.click_action("Tắt Auto Registry")
        self.assertTrue(is_audio_recovery_enabled())
        self.assertEqual(self.notify.call_args.kwargs["type"], "negative")
        self.assertTrue(any(
            isinstance(element, self.ui.button) and element.text == "Tắt Auto Registry"
            for element in self.client.elements.values()
        ))

    def test_calendar_saves_reloads_and_clears_without_changing_registered_videos(self):
        calendar = next(element for element in self.client.elements.values()
                        if isinstance(element, self.ui.input) and element._props.get("label") == "Quét từ ngày")
        self.assertEqual(calendar._props["type"], "date")
        with self.client:
            calendar.value = "2026-10-20"
        self.assertEqual(get_audio_recovery_scan_preferences()["scan_start_date"], "2026-10-20")
        self.assertEqual(get_audio_recovery_state()["entries"], self.original_entries)
        self.manager._conn.close()
        self.manager._conn = None
        self.assertEqual(get_audio_recovery_scan_preferences()["scan_start_date"], "2026-10-20")
        with self.client:
            calendar.value = "9999-01-01"
        self.assertEqual(calendar.value, "2026-10-20")
        with self.client:
            calendar.value = None
        self.assertEqual(get_audio_recovery_scan_preferences()["scan_start_date"], "")

    def test_calendar_reverts_when_save_fails_and_refresh_does_not_save_again(self):
        calendar = next(element for element in self.client.elements.values()
                        if isinstance(element, self.ui.input) and element._props.get("label") == "Quét từ ngày")
        set_audio_recovery_scan_preferences(scan_start_date="2026-10-20")
        with patch("web.components.auto_registry.set_audio_recovery_scan_preferences") as save, self.client:
            self.refresh()
        self.assertEqual(calendar.value, "2026-10-20")
        save.assert_not_called()
        with patch("web.components.auto_registry.set_audio_recovery_scan_preferences", return_value=False), self.client:
            calendar.value = "2026-10-21"
        self.assertEqual(calendar.value, "2026-10-20")

    def test_date_type_is_saved_and_restored_without_changing_registry_entries(self):
        basis = next(element for element in self.client.elements.values()
                     if isinstance(element, self.ui.select) and element._props.get("label") == "Tính theo ngày")
        self.assertEqual(basis.value, "auto")
        for date_type in ("uploaded", "published", "scheduled", "auto"):
            with self.subTest(date_type=date_type), self.client:
                basis.value = date_type
            self.assertEqual(get_audio_recovery_scan_preferences()["scan_date_type"], date_type)
            self.assertEqual(get_audio_recovery_state()["entries"], self.original_entries)
        set_audio_recovery_scan_preferences(scan_date_type="published")
        with patch("web.components.auto_registry.set_audio_recovery_scan_preferences") as save, self.client:
            self.refresh()
        self.assertEqual(basis.value, "published")
        save.assert_not_called()
        with patch("web.components.auto_registry.set_audio_recovery_scan_preferences", return_value=False), self.client:
            basis.value = "scheduled"
        self.assertEqual(basis.value, "published")
        self.manager._conn.close()
        self.manager._conn = None
        self.assertEqual(get_audio_recovery_scan_preferences()["scan_date_type"], "published")

    def test_video_scope_control_saves_all_choices(self):
        control = self.video_scope_control()
        self.assertEqual(control.value, RECOVERY_VIDEO_SCOPE_PUBLIC)
        for scope in (RECOVERY_VIDEO_SCOPE_SCHEDULED, RECOVERY_VIDEO_SCOPE_BOTH, RECOVERY_VIDEO_SCOPE_PUBLIC):
            with self.subTest(scope=scope), self.client:
                control.set_value(scope)
                self.assertEqual(get_audio_recovery_scan_preferences()["video_scan_scope"], scope)
                self.assertEqual(get_audio_recovery_state()["entries"], self.original_entries)

    def test_video_scope_control_restores_selection_when_save_fails(self):
        control = self.video_scope_control()
        with patch("web.components.auto_registry.set_audio_recovery_scan_preferences", return_value=False), self.client:
            control.set_value(RECOVERY_VIDEO_SCOPE_SCHEDULED)
        self.assertEqual(control.value, RECOVERY_VIDEO_SCOPE_PUBLIC)
        self.assertEqual(
            get_audio_recovery_scan_preferences()["video_scan_scope"], RECOVERY_VIDEO_SCOPE_PUBLIC
        )
        self.notify.assert_called_with("Không thể lưu loại video tự động quét.", type="negative")

    def test_refresh_syncs_video_scope_without_saving_again(self):
        set_audio_recovery_scan_preferences(video_scan_scope=RECOVERY_VIDEO_SCOPE_BOTH)
        with patch("web.components.auto_registry.set_audio_recovery_scan_preferences") as save, self.client:
            self.refresh()
        self.assertEqual(self.video_scope_control().value, RECOVERY_VIDEO_SCOPE_BOTH)
        save.assert_not_called()

    def test_concurrency_mode_control_saves_all_choices(self):
        control = self.concurrency_mode_control()
        self.assertEqual(control.value, DEFAULT_RECOVERY_CONCURRENCY_MODE)
        for mode in (RECOVERY_CONCURRENCY_MODE_VIDEOS, RECOVERY_CONCURRENCY_MODE_CHANNELS):
            with self.subTest(mode=mode), self.client:
                control.set_value(mode)
                self.assertEqual(get_audio_recovery_scan_preferences()["concurrency_mode"], mode)
                self.assertEqual(get_audio_recovery_state()["entries"], self.original_entries)

    def test_concurrency_mode_control_restores_selection_when_save_fails(self):
        control = self.concurrency_mode_control()
        with patch("web.components.auto_registry.set_audio_recovery_scan_preferences", return_value=False), self.client:
            control.set_value(RECOVERY_CONCURRENCY_MODE_VIDEOS)
        self.assertEqual(control.value, DEFAULT_RECOVERY_CONCURRENCY_MODE)
        self.assertEqual(
            get_audio_recovery_scan_preferences()["concurrency_mode"], DEFAULT_RECOVERY_CONCURRENCY_MODE
        )
        self.notify.assert_called_with("Không thể lưu chế độ luồng tự động quét.", type="negative")

    def test_refresh_syncs_concurrency_mode_without_saving_again(self):
        set_audio_recovery_scan_preferences(concurrency_mode=RECOVERY_CONCURRENCY_MODE_VIDEOS)
        with patch("web.components.auto_registry.set_audio_recovery_scan_preferences") as save, self.client:
            self.refresh()
        self.assertEqual(self.concurrency_mode_control().value, RECOVERY_CONCURRENCY_MODE_VIDEOS)
        save.assert_not_called()

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

    def test_bulk_remove_waits_for_confirmation_and_updates_both_lists(self):
        channels, videos = self.tables
        channels.selected = [channels.rows[0]]
        self.click_action("Xóa khỏi danh sách")
        self.assertEqual(len(channels.rows), 2)
        self.click_action("Xóa")
        self.assertEqual([row["id"] for row in channels.rows], ["channel-b"])
        self.assertEqual([row["id"] for row in videos.rows], ["channel-b:video-shared"])
        self.assertEqual(channels.selected, [])

    def test_row_remove_video_only_removes_that_row(self):
        channels, videos = self.tables
        listener = next(
            listener for listener in videos._event_listeners.values()
            if listener.type == "removeItem"
        )
        with self.client:
            listener.handler(SimpleNamespace(args={"id": "channel-a:video-shared"}))
        self.click_action("Xóa")
        self.assertEqual(len(channels.rows), 2)
        self.assertEqual(
            [row["id"] for row in videos.rows],
            ["channel-a:video-other", "channel-b:video-shared"],
        )

    def test_cancel_remove_preserves_data_and_failed_save_keeps_selection(self):
        channels = self.tables[0]
        channels.selected = [channels.rows[0]]
        before = get_audio_recovery_state()
        self.click_action("Xóa khỏi danh sách")
        self.click_action("Hủy")
        self.assertEqual(get_audio_recovery_state(), before)
        self.assertEqual(len(channels.selected), 1)
        self.click_action("Xóa khỏi danh sách")
        with patch("web.components.auto_registry.remove_audio_recovery_items", return_value=False):
            self.click_action("Xóa", index=1)
        self.assertEqual(get_audio_recovery_state(), before)
        self.assertEqual(len(channels.selected), 1)
        self.assertEqual(self.notify.call_args.kwargs["type"], "negative")


if __name__ == "__main__":
    unittest.main()
