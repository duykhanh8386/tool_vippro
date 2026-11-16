import copy
import unittest
from datetime import datetime
from unittest.mock import patch

from src import audio_recovery as recovery
from src.registry_lifecycle import (
    AUTO_RECOVERY_SECONDS, DAY_SECONDS, filter_registry_videos,
    newest_registry_video_ids, registry_expired, sync_registry_metadata,
)
import test_auto_registry as fixtures
import test_registry_descriptions as audio_fixtures

NOW = 1_800_000_000.0


class RegistryLifecycleTests(fixtures.RegistryStorage, unittest.TestCase):
    def setUp(self):
        super().setUp()
        clock = patch("src.audio_recovery.time.time", return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)

    def enroll(self, video="new", *, age=0):
        self.assertTrue(recovery.register_audio_recovery(
            channel_id="channel-a", video_id=video, audio_path=f"{video}.mp3",
            languages=["en"], repeat_times=1, extra_minutes=0,
            registered_at=NOW-age*DAY_SECONDS,
        ))

    def test_expiry_boundary_disables_without_losing_data_and_survives_restart(self):
        self.enroll(age=20)
        state = recovery.get_audio_recovery_state()
        self.assertFalse(recovery.is_audio_recovery_video_enabled("channel-a", "new"))
        row = next(row for row in recovery.get_audio_recovery_registry_items()[1] if row["video_id"] == "new")
        self.assertTrue(row["expired"])
        self.assertFalse(row["enabled"])
        self.assertEqual(row["age_days"], 20)
        self.assertEqual(row["title"], "new")
        self.manager._conn.close()
        self.manager._conn = None
        restored = recovery.get_audio_recovery_state()
        self.assertEqual(restored["entries"], state["entries"])
        self.assertEqual(restored["registry_metadata"]["channel-a"]["new"]["expired_at"], NOW)

    def test_under_twenty_days_stays_active_and_re_registration_never_renews(self):
        self.enroll(age=19.999)
        self.assertTrue(recovery.is_audio_recovery_video_enabled("channel-a", "new"))
        original = recovery.get_audio_recovery_state()["registry_metadata"]["channel-a"]["new"]["added_at"]
        self.enroll(age=0)
        self.assertEqual(recovery.get_audio_recovery_state()["registry_metadata"]["channel-a"]["new"]["added_at"], original)
        with patch("src.audio_recovery.time.time", return_value=original + AUTO_RECOVERY_SECONDS):
            self.assertFalse(recovery.is_audio_recovery_video_enabled("channel-a", "new"))
            self.assertFalse(recovery.set_audio_recovery_items_enabled(enabled=True, video_ids_by_channel={"channel-a": ["new"]}))

    def test_legacy_unknown_dates_start_one_persisted_window_and_keep_entries_intact(self):
        first = recovery.get_audio_recovery_state()
        self.assertEqual(first["entries"], self.original_entries)
        self.assertTrue(first["registry_metadata"]["channel-a"]["video-shared"]["date_estimated"])
        with patch("src.audio_recovery.time.time", return_value=NOW + DAY_SECONDS):
            second = recovery.get_audio_recovery_state()
        self.assertEqual(first["registry_metadata"], second["registry_metadata"])

    def test_deleted_video_can_start_a_new_window_only_after_explicit_reenrollment(self):
        self.enroll(age=30)
        self.assertTrue(recovery.remove_audio_recovery_items(video_ids_by_channel={"channel-a": ["new"]}))
        self.assertNotIn("new", recovery.get_audio_recovery_state()["registry_metadata"]["channel-a"])
        self.enroll()
        self.assertTrue(recovery.is_audio_recovery_video_enabled("channel-a", "new"))

    def test_newest_first_uses_first_enrollment_dates_and_reverse_insertion_for_ties(self):
        self.enroll("newest", age=1)
        self.enroll("oldest", age=5)
        self.enroll("middle", age=3)
        state = recovery.get_audio_recovery_state()
        entries = {key: state["entries"]["channel-a"][key] for key in ("newest", "oldest", "middle")}
        self.assertEqual(newest_registry_video_ids(state, "channel-a", entries), ["newest", "middle", "oldest"])
        self.assertEqual(newest_registry_video_ids({}, "a", {"one": {}, "two": {}}), ["two", "one"])

    def test_visibility_titles_are_cached_without_changing_audio_history(self):
        before = recovery.get_audio_recovery_state()
        recovery._cache_registry_titles("channel-a", {"video-shared": "Tên video gốc", "removed": "Ignore"})
        after = recovery.get_audio_recovery_state()
        self.assertEqual(after["entries"], before["entries"])
        self.assertNotIn("removed", after["registry_metadata"]["channel-a"])
        row = next(row for row in recovery.get_audio_recovery_registry_items()[1]
                   if row["channel_id"] == "channel-a" and row["video_id"] == "video-shared")
        self.assertEqual(row["title"], "Tên video gốc")


class RegistryDateFilterTests(unittest.TestCase):
    def test_name_and_age_filters_intersect_and_keep_boundary_values_precise(self):
        rows = [dict(id=str(age), title="เพลง ｜ Live", added_at=NOW-age*DAY_SECONDS)
                for age in (0, 6.9, 7, 19.9, 20, 28, 30)]
        chosen = filter_registry_videos(rows, query="เพลง | live", min_days=7, max_days=28, now=NOW)
        self.assertEqual([row["id"] for row in chosen], ["7", "19.9", "20"])
        self.assertEqual(len(filter_registry_videos(rows, min_days=20, now=NOW)), 3)
        self.assertEqual(filter_registry_videos(rows, query="missing", now=NOW), [])

    def test_custom_local_dates_include_last_day_and_leave_unknown_dates_in_all(self):
        stamp = lambda text: datetime.fromisoformat(text).timestamp()
        rows = [dict(id="first", added_at=stamp("2026-10-01T00:00:00")),
                dict(id="last", added_at=stamp("2026-10-31T23:59:59")),
                dict(id="next", added_at=stamp("2026-11-01T00:00:00")), dict(id="unknown")]
        result = filter_registry_videos(rows, start_date="2026-10-01", end_date="2026-10-31", now=NOW)
        self.assertEqual([row["id"] for row in result], ["first", "last"])
        self.assertEqual(len(filter_registry_videos(rows, now=NOW)), 4)

    def test_migration_ignores_invalid_dates_and_keeps_valid_registered_dates(self):
        state = {"entries": {"c": {"a": {"registered_at": "nan"}, "b": {"registered_at": NOW-DAY_SECONDS}}}}
        self.assertTrue(sync_registry_metadata(state, NOW))
        self.assertEqual(state["registry_metadata"]["c"]["a"]["added_at"], NOW)
        self.assertFalse(sync_registry_metadata(state, NOW))
        self.assertFalse(registry_expired(state, "c", "b", NOW))


class RegistryLifecycleCycleTests(audio_fixtures.RegistryAudioFixture, unittest.IsolatedAsyncioTestCase):
    async def test_expired_videos_do_not_reach_youtube_even_with_master_disabled_then_enabled(self):
        state = recovery.get_audio_recovery_state()
        state["registry_metadata"]["channel"]["video"]["added_at"] = NOW - AUTO_RECOVERY_SECONDS
        self.manager.save_state("audio_recovery", state)
        with patch("src.audio_recovery.time.time", return_value=NOW):
            recovery.set_audio_recovery_enabled(False)
            recovery.set_audio_recovery_enabled(True)
            result = await recovery.run_audio_recovery_cycle(now=NOW)
        self.visibility.assert_not_called()
        self.fetch.assert_not_called()
        self.add.assert_not_called()
        self.assertEqual(result["repaired"], 0)
        self.assertIn("video", recovery.get_audio_recovery_state()["entries"]["channel"])

    async def test_real_sequential_repair_queue_processes_newest_video_first(self):
        state = {"audio_content_types": ["descriptive"], "entries": {"channel": {
            "middle": {**copy.deepcopy(self.entry), "registered_at": NOW-3*DAY_SECONDS},
            "newest": {**copy.deepcopy(self.entry), "registered_at": NOW-DAY_SECONDS},
            "oldest": {**copy.deepcopy(self.entry), "registered_at": NOW-5*DAY_SECONDS},
        }}}
        self.manager.save_state("audio_recovery", state)
        self.fetch.side_effect = lambda ids, _channel: {"videoTranslations": [{"videoId": video} for video in ids], "audioTracks": []}
        with patch("src.audio_recovery.time.time", return_value=NOW):
            await recovery.run_audio_recovery_cycle(now=NOW)
        self.assertEqual(self.visibility.call_args.args[1], ["newest", "middle", "oldest"])
        self.assertEqual([call.kwargs["id_video"] for call in self.add.call_args_list],
                         ["newest", "newest", "middle", "middle", "oldest", "oldest"])


class RegistryFilterUiTests(fixtures.RegistryStorage, unittest.TestCase):
    click_action = fixtures.AutoRegistryUiTests.click_action

    def setUp(self):
        super().setUp()
        fixtures.AutoRegistryUiTests.create_registry_ui(self)

    def control(self, label):
        return next(element for element in self.client.elements.values()
                    if element._props.get("label") == label)

    def set_dates(self):
        state = recovery.get_audio_recovery_state()
        ages = {"channel-a": {"video-shared": 2, "video-other": 25}, "channel-b": {"video-shared": 40}}
        for channel, entries in ages.items():
            for video, age in entries.items():
                state["registry_metadata"][channel][video]["added_at"] = NOW-age*DAY_SECONDS
                state["registry_metadata"][channel][video]["date_estimated"] = False
        self.manager.save_state("audio_recovery", state)

    def test_filters_select_all_across_pages_and_deactivate_only_visible_matches(self):
        self.set_dates()
        with patch("src.audio_recovery.time.time", return_value=NOW), self.client:
            self.control("Thời gian từ lúc thêm âm").value = "expired"
            videos = self.tables[1]
            self.assertEqual(len(videos.rows), 2)
            self.click_action("Chọn tất cả kết quả lọc")
            self.assertEqual(len(videos.selected), 2)
            self.click_action("Deactive", index=1)
            state = recovery.get_audio_recovery_state()
            self.assertEqual(state["disabled_video_ids"], {"channel-a": ["video-other"], "channel-b": ["video-shared"]})
            self.assertTrue(recovery.is_audio_recovery_video_enabled("channel-a", "video-shared"))

    def test_changing_name_filter_clears_hidden_selection_and_searches_titles(self):
        self.set_dates()
        state = recovery.get_audio_recovery_state()
        state["registry_metadata"]["channel-a"]["video-other"]["title"] = "เพลงไทย"
        self.manager.save_state("audio_recovery", state)
        with self.client:
            self.click_action("Chọn tất cả kết quả lọc")
            self.control("Tìm tên video, nhạc, ID hoặc tên kênh").value = "เพลงไทย"
        self.assertEqual([row["video_id"] for row in self.tables[1].rows], ["video-other"])
        self.assertEqual(self.tables[1].selected, [])

    def test_filtered_delete_keeps_unmatched_rows_and_expired_rows_stay_listed(self):
        self.set_dates()
        with patch("src.audio_recovery.time.time", return_value=NOW), self.client:
            self.control("Thời gian từ lúc thêm âm").value = "expired"
            self.assertTrue(all(row["inactive_reason"] == "Đã hết hạn tự động 20 ngày" for row in self.tables[1].rows))
            self.click_action("Chọn tất cả kết quả lọc")
            self.click_action("Xóa khỏi danh sách", index=1)
            self.assertEqual(len(recovery.get_audio_recovery_registry_items()[1]), 3)
            self.click_action("Xóa")
        rows = recovery.get_audio_recovery_registry_items()[1]
        self.assertEqual([(row["channel_id"], row["video_id"]) for row in rows], [("channel-a", "video-shared")])

    def test_custom_age_filter_and_invalid_range_leave_last_valid_filter(self):
        self.set_dates()
        with patch("src.audio_recovery.time.time", return_value=NOW), self.client:
            self.control("Thời gian từ lúc thêm âm").value = "custom"
            self.control("Từ (ngày)").value = 20
            self.control("Ít hơn (ngày)").value = 30
            self.assertEqual([row["video_id"] for row in self.tables[1].rows], ["video-other"])
            self.control("Ít hơn (ngày)").value = 10
            self.refresh()
        self.assertEqual([row["video_id"] for row in self.tables[1].rows], ["video-other"])
        self.assertEqual(self.notify.call_args.kwargs["type"], "warning")

    def test_select_all_applies_to_more_than_one_page_without_touching_new_videos(self):
        state = {"entries": {"channel-a": {
            f"video-{index}": {"audio_path": f"Song {index}.mp3", "languages": ["en"],
                "registered_at": NOW - (25 if index < 30 else 2)*DAY_SECONDS}
            for index in range(45)
        }}}
        self.manager.save_state("audio_recovery", state)
        with patch("src.audio_recovery.time.time", return_value=NOW), self.client:
            self.control("Thời gian từ lúc thêm âm").value = "expired"
            self.click_action("Chọn tất cả kết quả lọc")
            self.assertEqual(len(self.tables[1].selected), 30)
            self.click_action("Deactive", index=1)
            saved = recovery.get_audio_recovery_state()
            self.assertEqual(len(saved["disabled_video_ids"]["channel-a"]), 30)
            self.assertEqual(len(saved["entries"]["channel-a"]), 45)
            self.assertTrue(all(recovery.is_audio_recovery_video_enabled("channel-a", f"video-{index}")
                                for index in range(30, 45)))

    def test_month_and_calendar_filters_survive_refresh_without_changing_scan_preferences(self):
        period = self.control("Thời gian từ lúc thêm âm")
        month_key = next(key for key in period.options if key.startswith("month:"))
        year, month = map(int, month_key.split(":")[1].split("-"))
        state = recovery.get_audio_recovery_state()
        for channel in state["registry_metadata"].values():
            for entry in channel.values():
                entry["added_at"] = datetime(year-1, month, 15).timestamp()
        state["registry_metadata"]["channel-a"]["video-other"]["added_at"] = datetime(year, month, 15).timestamp()
        self.manager.save_state("audio_recovery", state)
        before = recovery.get_audio_recovery_scan_preferences()
        with self.client:
            period.value = month_key
            self.refresh()
            self.assertEqual([row["video_id"] for row in self.tables[1].rows], ["video-other"])
            period.value = "custom"
            self.control("Thêm âm từ ngày").value = f"{year:04d}-{month:02d}-01"
            self.control("Thêm âm đến ngày").value = f"{year:04d}-{month:02d}-28"
            self.refresh()
        self.assertEqual([row["video_id"] for row in self.tables[1].rows], ["video-other"])
        self.assertEqual(recovery.get_audio_recovery_scan_preferences(), before)
