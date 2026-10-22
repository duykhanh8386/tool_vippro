import asyncio
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.audio_recovery import (
    RECOVERY_VIDEO_SCOPE_BOTH, RECOVERY_VIDEO_SCOPE_PUBLIC, RECOVERY_VIDEO_SCOPE_SCHEDULED,
    _get_registered_video_scan_statuses,
)
from src.audio_video_scan import _fetch_channel_videos
from src.module.list_videos_module import ListVideosModule
from src.module.model import Video
from src.video_scan_dates import (
    VIETNAM_TIMEZONE, normalize_scan_date_type, normalize_scan_start_date, scan_date_bounds,
    validate_scan_start_date, video_matches_scan_dates,
)
from web.components.audio import _video_from_snapshot, _video_snapshot
from web.components.delete_video_controller import COPYRIGHT_STARTED, DeleteVideoController


TODAY = date(2026, 10, 22)


def uploaded(day, *, hour=12, minute=0, second=0):
    return datetime(2026, 10, day, hour, minute, second, tzinfo=VIETNAM_TIMEZONE).timestamp()


def video(video_id, day=None, **kwargs):
    return Video(
        id=video_id, channel_id="channel", title=video_id, description="", thumbnail="",
        duration_ms=60000, time_created_seconds=uploaded(day) if day else "",
        **kwargs,
    )


class VideoScanDateTests(unittest.TestCase):
    def test_range_includes_start_and_today_in_vietnam_timezone(self):
        bounds = scan_date_bounds("2026-10-20", end_date=TODAY)
        for timestamp, expected in (
            (uploaded(19, hour=23, minute=59, second=59), False),
            (uploaded(20, hour=0), True),
            (uploaded(22, hour=23, minute=59, second=59), True),
            (uploaded(23, hour=0), False),
        ):
            with self.subTest(timestamp=timestamp):
                self.assertEqual(video_matches_scan_dates(SimpleNamespace(time_created_seconds=str(timestamp)), bounds), expected)
        self.assertEqual(bounds[0], datetime(2026, 10, 19, 17, tzinfo=timezone.utc).timestamp())

    def test_empty_date_preserves_existing_scans_and_unknown_dates_are_excluded_only_when_filtered(self):
        self.assertIsNone(scan_date_bounds(""))
        for timestamp in (None, "", "invalid", "NaN", "inf", 0, -1):
            row = SimpleNamespace(time_created_seconds=timestamp)
            with self.subTest(timestamp=timestamp):
                self.assertTrue(video_matches_scan_dates(row, None))
                self.assertFalse(video_matches_scan_dates(row, scan_date_bounds("2026-10-20", end_date=TODAY)))

    def test_invalid_or_future_start_date_is_rejected(self):
        with patch("src.video_scan_dates.scan_today", return_value=TODAY):
            self.assertEqual(validate_scan_start_date("2026-10-22"), "2026-10-22")
            self.assertEqual(normalize_scan_start_date(None), "")
            for invalid in ("2026-02-30", "20/10/2026", "2026-10-23"):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    validate_scan_start_date(invalid)

    def test_date_filter_combines_with_all_five_scopes(self):
        rows = [
            video("old", 19, privacy="VIDEO_PRIVACY_PUBLIC", time_published_seconds=uploaded(21)),
            video("public", 20, privacy="VIDEO_PRIVACY_PUBLIC"),
            video("scheduled", 21, privacy="VIDEO_PRIVACY_PRIVATE", scheduled_publishing_details={"time": "later"}, time_published_seconds=uploaded(25)),
            video("draft", 22, privacy="VIDEO_PRIVACY_PRIVATE", draft_status="DRAFT"),
            video("future", 23, privacy="VIDEO_PRIVACY_PUBLIC"),
            video("unknown", privacy="VIDEO_PRIVACY_PUBLIC"),
        ]
        for scope, expected in (
            ("all", ["public", "scheduled", "draft"]),
            ("public", ["public"]),
            ("scheduled", ["scheduled"]),
            ("draft", ["draft"]),
            ("recent", ["public", "scheduled"]),
        ):
            with (
                self.subTest(scope=scope),
                patch("src.video_scan_dates.scan_today", return_value=TODAY),
                patch("src.audio_video_scan.list_videos_module.list_all_videos", return_value=(
                    [rows[3]] if scope == "draft" else rows, None,
                )) as fetch,
            ):
                selected = _fetch_channel_videos("channel", scope=scope, recent_limit=2, start_date="2026-10-20", date_type="uploaded")
                self.assertEqual([row.id for row in selected], expected)
                self.assertEqual(fetch.call_args.kwargs.get("draft_only", False), scope == "draft")

    def test_limited_scan_counts_matching_dates_across_pages_and_does_not_stop_on_old_display_dates(self):
        for scope in ("recent", "draft"):
            pages = [([video("old", 19)], "next"),
                     ([video("first", 20), video("second", 21), video("extra", 22)], "unused")]
            with (
                self.subTest(scope=scope),
                patch("src.video_scan_dates.scan_today", return_value=TODAY),
                patch("src.audio_video_scan.list_videos_module.list_all_videos", side_effect=pages) as fetch,
            ):
                selected = _fetch_channel_videos("channel", scope=scope, recent_limit=2, start_date="2026-10-20")
                self.assertEqual([row.id for row in selected], ["first", "second"])
                self.assertEqual(fetch.call_count, 2)
                self.assertTrue(all(call.kwargs["limit"] == 2 for call in fetch.call_args_list))

    def test_future_date_fails_before_querying_channel(self):
        with patch("src.video_scan_dates.scan_today", return_value=TODAY), patch(
            "src.audio_video_scan.list_videos_module.list_all_videos"
        ) as fetch:
            with self.assertRaises(ValueError):
                _fetch_channel_videos("channel", start_date="2026-10-23")
            fetch.assert_not_called()

    def test_scan_dates_survive_video_listing_and_saved_video_snapshots(self):
        module = ListVideosModule()
        channel = SimpleNamespace(
            id="channel", delegated_session_id="delegate", role="OWNER",
            cookies=[{"name": "SAPISID", "value": "test-value"}], cookie_string=lambda: "SAPISID=test-value",
        )
        payload = {"videos": [{"videoId": "video", "channelId": "channel", "title": "test",
                               "timeCreatedSeconds": str(uploaded(20)), "timePublishedSeconds": str(uploaded(25))}]}
        with (
            patch("src.module.list_videos_module.get_channels_info", return_value=channel),
            patch.object(module, "_get_session_token", return_value="test-token"),
            patch("src.module.list_videos_module.post_with_stop", return_value=SimpleNamespace(status_code=200, json=lambda: payload)),
        ):
            rows, _ = module.list_all_videos("channel")
        restored = _video_from_snapshot(_video_snapshot(rows[0]))
        self.assertEqual(restored.time_created_seconds, str(uploaded(20)))
        self.assertEqual(restored.time_published_seconds, str(uploaded(25)))

    def test_auto_registry_applies_upload_dates_in_every_supported_video_scope(self):
        rows = [video("old", 19, privacy="VIDEO_PRIVACY_PUBLIC"),
                video("public", 20, privacy="VIDEO_PRIVACY_PUBLIC"),
                video("scheduled", 21, privacy="VIDEO_PRIVACY_PRIVATE", scheduled_publishing_details={"time": "later"}),
                video("unknown", privacy="VIDEO_PRIVACY_PUBLIC")]
        for scope, selected in ((RECOVERY_VIDEO_SCOPE_PUBLIC, {"public"}),
                                (RECOVERY_VIDEO_SCOPE_SCHEDULED, {"scheduled"}),
                                (RECOVERY_VIDEO_SCOPE_BOTH, {"public", "scheduled"})):
            with (
                self.subTest(scope=scope), patch("src.video_scan_dates.scan_today", return_value=TODAY),
                patch("src.audio_recovery.list_videos_module.list_all_videos", return_value=(rows, None)),
            ):
                statuses, unknown = _get_registered_video_scan_statuses(
                    "channel", [row.id for row in rows], video_scan_scope=scope,
                    scan_start_date="2026-10-20", scan_date_type="uploaded",
                )
                self.assertEqual({key for key, matches in statuses.items() if matches}, selected)
                self.assertEqual(unknown, set())

    def test_publication_date_is_independent_of_upload_date(self):
        bounds = scan_date_bounds("2026-10-20", end_date=TODAY)
        recent_publication = video("published", 10, privacy="VIDEO_PRIVACY_PUBLIC", time_published_seconds=uploaded(21))
        old_publication = video("old-publication", 21, privacy="VIDEO_PRIVACY_PUBLIC", time_published_seconds=uploaded(19))
        missing_publication = video("unknown-publication", 21, privacy="VIDEO_PRIVACY_PUBLIC")
        self.assertTrue(video_matches_scan_dates(recent_publication, bounds, date_type="published"))
        self.assertFalse(video_matches_scan_dates(recent_publication, bounds, date_type="uploaded"))
        self.assertFalse(video_matches_scan_dates(old_publication, bounds, date_type="published"))
        self.assertTrue(video_matches_scan_dates(old_publication, bounds, date_type="uploaded"))
        self.assertFalse(video_matches_scan_dates(missing_publication, bounds, date_type="auto"))

    def test_schedule_dates_accept_seconds_milliseconds_iso_and_nested_timestamps(self):
        bounds = scan_date_bounds("2026-10-20", end_date=TODAY)
        for schedule in (
            {"publishTime": str(uploaded(21))},
            {"scheduledPublishTimeSeconds": str(uploaded(21))},
            {"time": {"seconds": str(uploaded(21))}},
            {"publishAt": "2026-10-21T12:00:00+07:00"},
            {"scheduledPublishingTime": "2026-10-21T05:00:00Z"},
            {"publishTime": uploaded(21) * 1000},
        ):
            row = video("scheduled", 10, privacy="VIDEO_PRIVACY_PRIVATE", scheduled_publishing_details=schedule)
            with self.subTest(schedule=schedule):
                self.assertTrue(video_matches_scan_dates(row, bounds, date_type="scheduled"))
                self.assertTrue(video_matches_scan_dates(row, bounds, date_type="auto"))
                self.assertFalse(video_matches_scan_dates(row, bounds, date_type="uploaded"))
                self.assertFalse(video_matches_scan_dates(row, bounds, date_type="published"))

    def test_future_schedule_is_not_selected_by_recent_upload_or_old_publication_dates(self):
        bounds = scan_date_bounds("2026-10-20", end_date=TODAY)
        row = video("future-schedule", 21, privacy="VIDEO_PRIVACY_PRIVATE",
                    scheduled_publishing_details={"publishTime": uploaded(25)}, time_published_seconds=uploaded(21))
        self.assertFalse(video_matches_scan_dates(row, bounds, date_type="scheduled"))
        self.assertFalse(video_matches_scan_dates(row, bounds, date_type="auto"))
        self.assertTrue(video_matches_scan_dates(row, bounds, date_type="uploaded"))
        row.scheduled_publishing_details = {"unknownField": True}
        row.time_published_seconds = uploaded(22)
        self.assertTrue(video_matches_scan_dates(row, bounds, date_type="scheduled"))
        row.time_published_seconds = ""
        self.assertFalse(video_matches_scan_dates(row, bounds, date_type="scheduled"))

    def test_auto_date_type_combines_with_every_video_scope(self):
        rows = [
            video("old-publication", 21, privacy="VIDEO_PRIVACY_PUBLIC", time_published_seconds=uploaded(19)),
            video("recent-publication", 10, privacy="VIDEO_PRIVACY_PUBLIC", time_published_seconds=uploaded(21)),
            video("scheduled", 10, privacy="VIDEO_PRIVACY_PRIVATE", scheduled_publishing_details={"time": uploaded(22)}),
            video("draft", 21, privacy="VIDEO_PRIVACY_PRIVATE", draft_status="DRAFT"),
        ]
        for scope, expected in (
            ("all", ["recent-publication", "scheduled", "draft"]),
            ("public", ["recent-publication"]), ("scheduled", ["scheduled"]),
            ("draft", ["draft"]), ("recent", ["recent-publication", "scheduled"]),
        ):
            with (
                self.subTest(scope=scope), patch("src.video_scan_dates.scan_today", return_value=TODAY),
                patch("src.audio_video_scan.list_videos_module.list_all_videos", return_value=(
                    [rows[3]] if scope == "draft" else rows, None,
                )),
            ):
                selected = _fetch_channel_videos("channel", scope=scope, recent_limit=2, start_date="2026-10-20")
                self.assertEqual([row.id for row in selected], expected)

    def test_unknown_date_type_defaults_to_auto_and_empty_date_keeps_all_types(self):
        self.assertEqual(normalize_scan_date_type("invalid"), "auto")
        self.assertEqual(normalize_scan_date_type(None), "auto")
        for date_type in ("auto", "uploaded", "published", "scheduled"):
            self.assertTrue(video_matches_scan_dates(video("undated"), None, date_type=date_type))


class DeleteVideoDateTests(unittest.IsolatedAsyncioTestCase):
    async def test_delete_video_calendar_persists_and_blocks_edits_while_running(self):
        from nicegui import Client, ui
        from nicegui.page import page
        from web.components import delete_video as screen

        with (
            tempfile.TemporaryDirectory() as folder,
            patch("web.components.delete_video_controller._load_output_dir", return_value=Path(folder)),
            patch("web.components.delete_video_controller.state_manager.load_state", return_value={}),
            patch("web.components.delete_video_controller.state_manager.save_state", return_value=True) as save,
        ):
            controller = DeleteVideoController()
            client = Client(page("/test-delete-date"), request=None)
            self.addCleanup(client.delete)
            with (
                patch.object(screen, "delete_controller", controller),
                patch.object(screen, "get_channels_info", return_value=[]),
                patch.object(screen.ui, "timer"), patch.object(screen.ui, "notify"),
                client,
            ):
                screen.create_delete_video_page()
                calendar = next(element for element in client.elements.values()
                                if isinstance(element, ui.input) and element._props.get("label") == "Quét từ ngày")
                calendar.value = "2026-10-20"
                self.assertEqual(controller.scan_start_date, "2026-10-20")
                self.assertEqual(save.call_args.args[1]["scan_start_date"], "2026-10-20")
                basis = next(element for element in client.elements.values()
                             if isinstance(element, ui.select) and element._props.get("label") == "Tính theo ngày")
                basis.value = "published"
                self.assertEqual(controller.scan_date_type, "published")
                self.assertEqual(save.call_args.args[1]["scan_date_type"], "published")
                with patch.object(controller, "is_running", return_value=True):
                    calendar.value = "2026-10-21"
                    basis.value = "scheduled"
                self.assertEqual(calendar.value, "2026-10-20")
                self.assertEqual(basis.value, "published")
                calendar.value = "9999-01-01"
                self.assertEqual(calendar.value, "2026-10-20")

    async def test_delete_scan_only_processes_uploads_in_date_range_and_keeps_future_scheduling_independent(self):
        rows = [video("old", 19, copyright_check_status=COPYRIGHT_STARTED),
                video("in-range", 21, copyright_check_status=COPYRIGHT_STARTED, time_published_seconds=uploaded(25)),
                video("unknown", copyright_check_status=COPYRIGHT_STARTED)]
        with (
            tempfile.TemporaryDirectory() as folder,
            patch("web.components.delete_video_controller._load_output_dir", return_value=Path(folder)),
            patch("web.components.delete_video_controller.state_manager.load_state", return_value={"scan_start_date": "2026-10-20"}),
            patch("web.components.delete_video_controller.state_manager.save_state", return_value=True) as save,
            patch("src.video_scan_dates.scan_today", return_value=TODAY),
            patch("web.components.delete_video_controller.list_videos_module.list_all_videos", return_value=(rows, None)),
            patch("web.components.delete_video_controller.delete_video_module.delete", return_value=200) as delete,
        ):
            controller = DeleteVideoController()
            self.assertEqual(controller.scan_start_date, "2026-10-20")
            controller.running = True
            await controller._process_channel("channel", asyncio.Semaphore(1))
            self.assertEqual([row["id"] for row in controller.all_videos], ["in-range"])
            delete.assert_called_once_with("in-range", "channel")
            self.assertEqual(save.call_args.args[1]["scan_start_date"], "2026-10-20")

    async def test_delete_date_type_controls_which_videos_are_processed(self):
        rows = [
            video("new-upload", 21, privacy="VIDEO_PRIVACY_PUBLIC", time_published_seconds=uploaded(19), copyright_check_status=COPYRIGHT_STARTED),
            video("new-publication", 10, privacy="VIDEO_PRIVACY_PUBLIC", time_published_seconds=uploaded(21), copyright_check_status=COPYRIGHT_STARTED),
            video("schedule", 10, privacy="VIDEO_PRIVACY_PRIVATE", scheduled_publishing_details={"time": uploaded(22)}, copyright_check_status=COPYRIGHT_STARTED),
        ]
        for date_type, expected in (
            ("uploaded", ["new-upload"]), ("published", ["new-publication"]),
            ("scheduled", ["schedule"]), ("auto", ["new-publication", "schedule"]),
        ):
            with (
                self.subTest(date_type=date_type), tempfile.TemporaryDirectory() as folder,
                patch("web.components.delete_video_controller._load_output_dir", return_value=Path(folder)),
                patch("web.components.delete_video_controller.state_manager.load_state", return_value={
                    "scan_start_date": "2026-10-20", "scan_date_type": date_type,
                }),
                patch("web.components.delete_video_controller.state_manager.save_state", return_value=True),
                patch("src.video_scan_dates.scan_today", return_value=TODAY),
                patch("web.components.delete_video_controller.list_videos_module.list_all_videos", return_value=(rows, None)),
                patch("web.components.delete_video_controller.delete_video_module.delete", return_value=200) as delete,
            ):
                controller = DeleteVideoController()
                controller.running = True
                await controller._process_channel("channel", asyncio.Semaphore(1))
                self.assertEqual([call.args[0] for call in delete.call_args_list], expected)
