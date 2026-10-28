"""Synthetic channels and mocked Studio requests; never edit real YouTube videos."""
import copy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
import tempfile
import inspect
import shutil
import subprocess
import unittest
from unittest.mock import Mock, patch

import requests

from src.module.base import YouTubeRequestError
from src.module.model import Video
from src.module.video_title_module import VideoTitleModule
from src.task_runtime import TaskStopped, bind_run_context, create_run_context
from src.video_title_matching import build_title_matches, clean_video_title, parse_manual_title_ids, scan_title_videos
from src.video_title_tasks import STATE_KEY, VideoTitleController

CHANNEL = "UC" + "a" * 22
VIDEO = "Abc123_-XYZ"
OTHER = "Def123_-XYZ"


def video(identifier=VIDEO, **changes):
    fields = dict(id=identifier, channel_id=CHANNEL, title="1026(1)_part40", description="keep-description",
                  thumbnail="", duration_ms=60000, privacy="PUBLIC")
    fields.update(changes)
    return Video(**fields)


def row(identifier=VIDEO, **changes):
    fields = dict(video_id=identifier, channel_id=CHANNEL, old_title="1026(1)_part40", duration_seconds=60,
                  status="scanned", new_title="", audio_path="", selected=False, detail="")
    fields.update(changes)
    return fields


class MemoryState:
    def __init__(self):
        self.values = {}
        self.fail = False

    def load_state(self, key):
        return copy.deepcopy(self.values.get(key))

    def save_state(self, key, value):
        if self.fail:
            return False
        self.values[key] = copy.deepcopy(value)
        return True


class TitleScanTests(unittest.TestCase):
    def test_part_scan_counts_matching_titles_across_pages_and_ignores_case(self):
        pages = [([video(title="Song without the keyword"), video(OTHER, title="1026(1)_PART40")], "next"),
                 ([video(OTHER, title="Repeated part"), video("Ghi123_-XYZ", title="Mix Part 2"),
                   video("Jkl123_-XYZ", title="Part 3")], None)]
        with patch("src.video_title_matching.list_videos_module.list_all_videos", side_effect=pages) as listing:
            result = scan_title_videos(CHANNEL, limit=2, title_contains="part")
        self.assertEqual([item.id for item in result], [OTHER, "Ghi123_-XYZ"])
        self.assertEqual(listing.call_count, 2)
        self.assertEqual(listing.call_args.kwargs["limit"], 50)

    def test_part_scan_keeps_date_and_scope_filters(self):
        stamp = lambda day: datetime(2026, 10, day, 12, tzinfo=timezone.utc).timestamp()
        pages = [([video(title="Part 1", privacy="PRIVATE", time_created_seconds=stamp(28)),
                   video(OTHER, title="Part 2", time_created_seconds=stamp(27))], "next"),
                 ([video("Ghi123_-XYZ", title="A part30", time_created_seconds=stamp(28)),
                   video("Jkl123_-XYZ", title="Normal title", time_created_seconds=stamp(28))], None)]
        with patch("src.video_title_matching.list_videos_module.list_all_videos", side_effect=pages):
            result = scan_title_videos(CHANNEL, mode="dates", scope="public", title_contains="part", limit=1,
                                       start_date="2026-10-28", end_date="2026-10-28", date_type="uploaded")
        self.assertEqual([item.id for item in result], ["Ghi123_-XYZ"])

    def test_count_filters_scope_before_counting_and_deduplicates_pages(self):
        pages = [([video(privacy="PRIVATE"), video(OTHER)], "next"), ([video(OTHER), video("Ghi123_-XYZ")], None)]
        with patch("src.video_title_matching.list_videos_module.list_all_videos", side_effect=pages) as listing:
            result = scan_title_videos(CHANNEL, mode="count", scope="public", limit=2)
        self.assertEqual([v.id for v in result], [OTHER, "Ghi123_-XYZ"])
        self.assertEqual(listing.call_count, 2)
        self.assertTrue(listing.call_args.kwargs["include_all_origins"])

    def test_dates_include_end_of_day_in_vietnam_and_scan_every_page(self):
        vn = timezone(timedelta(hours=7))
        stamp = lambda day, hour=0: datetime(2026, 10, day, hour, tzinfo=vn).timestamp()
        pages = [([video(time_created_seconds=stamp(13)), video(OTHER, time_created_seconds=stamp(14))], "next"),
                 ([video("Ghi123_-XYZ", time_created_seconds=stamp(28, 23)), video("Jkl123_-XYZ", time_created_seconds=stamp(29))], None)]
        with patch("src.video_title_matching.list_videos_module.list_all_videos", side_effect=pages):
            result = scan_title_videos(CHANNEL, mode="dates", limit=1, start_date="2026-10-14", end_date="2026-10-28", date_type="uploaded")
        self.assertEqual([v.id for v in result], [OTHER, "Ghi123_-XYZ"])

    def test_scheduled_scope_uses_schedule_date_and_count_scan_ignores_dates(self):
        schedule = datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp()
        scheduled = video(scheduled_publishing_details={"publishTimeSeconds": schedule}, privacy="PRIVATE")
        with patch("src.video_title_matching.list_videos_module.list_all_videos", return_value=([scheduled], None)):
            result = scan_title_videos(CHANNEL, mode="dates", scope="scheduled", start_date="2026-11-01", end_date="2026-11-01", date_type="auto")
            self.assertEqual(len(result), 1)
            result = scan_title_videos(CHANNEL, mode="count", start_date="invalid", end_date="invalid")
            self.assertEqual(len(result), 1)

    def test_drafts_request_explicit_draft_filter(self):
        with patch("src.video_title_matching.list_videos_module.list_all_videos", return_value=([video()], None)) as listing:
            scan_title_videos(CHANNEL, scope="draft")
        self.assertTrue(listing.call_args.kwargs["draft_only"])

    def test_invalid_range_repeated_tokens_and_foreign_channel_fail_explicitly(self):
        with self.assertRaises(ValueError):
            scan_title_videos(CHANNEL, mode="dates", start_date="2026-10-28", end_date="2026-10-14")
        with patch("src.video_title_matching.list_videos_module.list_all_videos", return_value=([], "repeat")):
            with self.assertRaisesRegex(RuntimeError, "phân trang"):
                scan_title_videos(CHANNEL, mode="dates", start_date="2026-10-14", end_date="2026-10-28")
        with patch("src.video_title_matching.list_videos_module.list_all_videos", return_value=([video(channel_id="foreign")], None)):
            with self.assertRaisesRegex(ValueError, "không thuộc"):
                scan_title_videos(CHANNEL)


class ManualTitleIdsTests(unittest.TestCase):
    def test_ids_and_youtube_links_are_deduplicated_in_input_order(self):
        text = (f"{VIDEO}\nhttps://youtu.be/{OTHER}?t=20; https://www.youtube.com/watch?v={VIDEO}&list=fixture\n"
                f"https://studio.youtube.com/video/Ghi123_-XYZ/edit, youtube.com/shorts/Jkl123_-XYZ\n"
                f"https://www.youtube.com/live/{OTHER}\nhttps://www.youtube.com/embed/{VIDEO}")
        self.assertEqual(parse_manual_title_ids(text), [VIDEO, OTHER, "Ghi123_-XYZ", "Jkl123_-XYZ"])

    def test_invalid_entries_are_not_silently_ignored_or_extracted_from_other_sites(self):
        for text in ("", "   ", VIDEO + "\nwrong", "https://example.com/watch?v=" + VIDEO,
                     "https://youtube.com.evil.test/watch?v=" + VIDEO, "https://youtube.com/@channel",
                     "ftp://youtube.com/watch?v=" + VIDEO, "http://[", VIDEO + "extra"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_manual_title_ids(text)


class TitleMatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name).resolve()

    def match(self, rows, files, **options):
        for name in files:
            path = self.folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic-audio")
        return build_title_matches(rows, self.folder, duration_reader=lambda path: files[str(Path(path).relative_to(self.folder))], **options)

    def test_match_uses_song_name_not_original_video_name_and_reuses_song(self):
        result, counts = self.match([row(), row(OTHER)], {"Bài nhạc gốc.mp3": 60.2})
        self.assertEqual(counts["files"], 1)
        self.assertTrue(all(item["new_title"] == "Bài nhạc gốc" and item["selected"] for item in result))
        self.assertAlmostEqual(result[0]["delta"], .2)

    def test_nearest_duration_wins_and_equal_ties_require_explicit_choice(self):
        result, _ = self.match([row()], {"Song A.mp3": 60, "Song B.m4a": 60})
        self.assertEqual(result[0]["status"], "ambiguous")
        self.assertFalse(result[0]["selected"])
        self.assertEqual(len(result[0]["candidates"]), 2)
        result, _ = build_title_matches([row()], self.folder, duration_reader=lambda path: 60 if Path(path).name == "Song B.m4a" else 61)
        self.assertEqual(result[0]["new_title"], "Song B")

    def test_title_hint_resolves_duration_tie_and_already_correct_is_not_selected(self):
        result, _ = self.match([row(old_title="Song A")], {"Song A.mp3": 60, "Song B.mp3": 60})
        self.assertEqual(result[0]["status"], "unchanged")
        self.assertFalse(result[0]["selected"])

    def test_invalid_audio_and_unknown_video_duration_stay_unmatched(self):
        result, counts = self.match([row(), row(OTHER, duration_seconds=0)], {"broken.mp3": float("nan")})
        self.assertEqual(counts["unreadable"], 1)
        self.assertTrue(all(item["status"] == "unmatched" for item in result))
        with self.assertRaises(ValueError):
            build_title_matches([], self.folder, tolerance=float("nan"))

    def test_subfolders_and_no_filesystem_renames(self):
        relative = str(Path("sub") / "Tên bài.mp3")
        result, _ = self.match([row()], {relative: 60}, recursive=False)
        self.assertEqual(result[0]["status"], "unmatched")
        result, _ = build_title_matches([row()], self.folder, recursive=True, duration_reader=lambda _: 60)
        self.assertEqual(result[0]["new_title"], "Tên bài")
        self.assertEqual((self.folder / relative).read_bytes(), b"synthetic-audio")

    def test_title_normalization_keeps_unicode_and_whole_emoji(self):
        self.assertEqual(clean_video_title("  Bài <nhạc>\n đẹp  "), "Bài nhạc đẹp")
        title = clean_video_title("a" * 99 + "🎵")
        self.assertEqual(title, "a" * 99)
        self.assertLessEqual(len(clean_video_title("🎵" * 60).encode("utf-16-le")), 200)


class TitleModuleTests(unittest.TestCase):
    def setUp(self):
        self.module = VideoTitleModule()
        self.channel = SimpleNamespace(id=CHANNEL, role="OWNER", delegated_session_id="fixture-delegation", cookies=[], cookie_string=lambda: "fixture-cookie")
        self.patches = [patch("src.module.video_title_module.get_channels_info", return_value=self.channel),
                        patch("src.module.video_title_module.studio_authorization_header", return_value="fixture-hash"),
                        patch.object(self.module, "_get_session_token", return_value="fixture-token"), patch("time.sleep")]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def call(self):
        return self.module.update_title(CHANNEL, VIDEO, "Tên bài nhạc", expected_title="1026(1)_part40", audio_duration=60, tolerance=2)

    def test_manual_read_checks_exact_video_and_channel_without_mutation(self):
        with patch.object(self.module, "_get_video_info", return_value=video()) as read, \
             patch("src.module.video_title_module.post_with_stop") as post:
            self.assertEqual(self.module.read_video(CHANNEL, VIDEO).title, "1026(1)_part40")
            read.assert_called_once_with(VIDEO, CHANNEL)
            post.assert_not_called()
        for current in (video(channel_id="foreign"), video(OTHER)):
            with self.subTest(current=current), patch.object(self.module, "_get_video_info", return_value=current):
                with self.assertRaises(ValueError):
                    self.module.read_video(CHANNEL, VIDEO)

    def test_mutation_contains_only_title_and_success_requires_readback(self):
        with patch.object(self.module, "_get_video_info", side_effect=[video(), video(title="Tên bài nhạc")]), \
             patch("src.module.video_title_module.post_with_stop", return_value=Mock(status_code=200, json=lambda: {})) as post:
            self.assertTrue(self.call()["changed"])
        payload = post.call_args.kwargs["json"]
        self.assertEqual(set(payload), {"encryptedVideoId", "title", "context", "delegationContext", "videoReadMask"})
        self.assertEqual(payload["title"], {"newTitle": "Tên bài nhạc"})

    def test_already_applied_update_does_not_post_again(self):
        with patch.object(self.module, "_get_video_info", return_value=video(title="Tên bài nhạc")), \
             patch("src.module.video_title_module.post_with_stop") as post:
            self.assertFalse(self.call()["changed"])
        post.assert_not_called()

    def test_wrong_owner_changed_title_and_changed_duration_never_mutate(self):
        for current in (video(channel_id="foreign"), video(title="Manual edit"), video(duration_ms=90000), video(OTHER)):
            with self.subTest(current=current), patch.object(self.module, "_get_video_info", return_value=current), \
                 patch("src.module.video_title_module.post_with_stop") as post:
                with self.assertRaises(ValueError):
                    self.call()
                post.assert_not_called()

    def test_lost_response_after_success_is_verified_without_duplicate_post(self):
        with patch.object(self.module, "_get_video_info", side_effect=[video(), video(title="Tên bài nhạc")]), \
             patch("src.module.video_title_module.post_with_stop", side_effect=requests.Timeout) as post:
            self.assertTrue(self.call()["changed"])
        post.assert_called_once()

    def test_server_rejection_or_unchanged_readback_is_not_success(self):
        for body in ({"success": False}, {"error": {"code": 403}}, {}):
            with self.subTest(body=body), patch.object(self.module, "_get_video_info", return_value=video()), \
                 patch("src.module.video_title_module.post_with_stop", return_value=Mock(status_code=200, json=lambda: body)):
                with self.assertRaises((ValueError, YouTubeRequestError)):
                    self.call()

    def test_all_origins_is_opt_in_and_does_not_change_existing_audio_scans(self):
        from src.module.list_videos_module import ListVideosModule
        listing = ListVideosModule()
        response = Mock(status_code=200, json=lambda: {"videos": []})
        with patch("src.module.list_videos_module.get_channels_info", return_value=self.channel), \
             patch.object(listing, "_get_session_token", return_value="fixture-token"), \
             patch("src.module.list_videos_module.studio_authorization_header", return_value="fixture-hash"), \
             patch("src.module.list_videos_module.post_with_stop", return_value=response) as post:
            listing.list_all_videos(CHANNEL)
            operands = post.call_args.kwargs["json"]["filter"]["and"]["operands"]
            self.assertTrue(any("videoOriginIs" in item for item in operands))
            listing.list_all_videos(CHANNEL, include_all_origins=True)
            operands = post.call_args.kwargs["json"]["filter"]["and"]["operands"]
            self.assertFalse(any("videoOriginIs" in item for item in operands))


class TitleControllerTests(unittest.TestCase):
    def setUp(self):
        self.state = MemoryState()
        self.module = Mock()
        self.module.update_title.return_value = {"title": "Song", "changed": True}
        self.controller = VideoTitleController(storage=self.state, module=self.module)
        self.controller.change_settings(channel_id=CHANNEL)
        self.controller.rows = [row(status="ready", new_title="Song", selected=True, audio_path="fixture.mp3", audio_duration=60)]

    def run_update(self):
        self.controller.start("update")
        self.controller.thread.join(timeout=5)
        self.assertFalse(self.controller.thread.is_alive())

    def test_manual_scan_reads_only_explicit_ids_and_does_not_apply_channel_scan_filters(self):
        self.controller.change_settings(manual_ids=f"{OTHER}\n{VIDEO}\n{OTHER}", mode="dates", scope="draft",
                                        start_date="invalid", end_date="invalid", limit=1)
        self.module.read_video.side_effect = [video(OTHER, title="Chosen song", duration_ms=80000), video()]
        with patch("src.video_title_tasks.scan_title_videos") as scan:
            self.controller.start("scan_manual")
            self.controller.thread.join(5)
        self.assertFalse(self.controller.busy)
        scan.assert_not_called()
        self.assertEqual([call.args for call in self.module.read_video.call_args_list], [(CHANNEL, OTHER), (CHANNEL, VIDEO)])
        self.assertEqual([item["video_id"] for item in self.controller.rows], [OTHER, VIDEO])
        self.assertEqual(self.controller.rows[0]["duration_seconds"], 80)
        self.assertEqual(self.controller.rows[0]["old_title"], "Chosen song")
        self.assertTrue(all(item["status"] == "scanned" for item in self.controller.rows))
        self.module.update_title.assert_not_called()
        restored = VideoTitleController(storage=self.state, module=self.module)
        self.assertEqual(restored.settings["manual_ids"], f"{OTHER}\n{VIDEO}\n{OTHER}")
        self.assertEqual(restored.rows, self.controller.rows)

    def test_manual_input_is_draft_and_failed_or_stopped_reads_keep_existing_preview(self):
        original = copy.deepcopy(self.controller.rows)
        self.controller.change_settings(manual_ids=f"{VIDEO}\n{OTHER}")
        self.assertEqual(self.controller.rows, original)
        self.module.read_video.side_effect = [video(), ValueError("Không thuộc kênh đã chọn")]
        self.controller.start("scan_manual")
        self.controller.thread.join(5)
        self.assertEqual(self.controller.rows, original)
        self.assertIn(OTHER, self.controller.message)
        self.module.update_title.assert_not_called()

        def read(*args):
            self.controller.stop()
            return video()

        self.module.read_video.reset_mock(side_effect=True)
        self.module.read_video.side_effect = read
        self.controller.start("scan_manual")
        self.controller.thread.join(5)
        self.module.read_video.assert_called_once()
        self.assertEqual(self.controller.rows, original)

    def test_invalid_manual_input_does_not_start_background_job(self):
        self.controller.change_settings(manual_ids=VIDEO + "\ninvalid")
        with self.assertRaises(ValueError):
            self.controller.start("scan_manual")
        self.assertFalse(self.controller.busy)
        self.module.read_video.assert_not_called()

    def test_part_button_starts_filtered_scan_and_normal_scan_stays_unfiltered(self):
        for action, criterion in (("scan_part", "part"), ("scan", "")):
            with self.subTest(action=action), patch("src.video_title_tasks.scan_title_videos", return_value=[video()]) as scan:
                self.controller.start(action)
                self.controller.thread.join(5)
                self.assertFalse(self.controller.busy)
                self.assertEqual(scan.call_args.kwargs["title_contains"], criterion)
                self.assertEqual(scan.call_args.args, (CHANNEL,))
                self.assertEqual(self.controller.rows[0]["old_title"], "1026(1)_part40")
        self.module.update_title.assert_not_called()

    def test_confirmed_changes_are_saved_and_reload_does_not_select_successes(self):
        self.run_update()
        snapshot = self.controller.snapshot()
        self.assertEqual(snapshot["rows"][0]["status"], "successful")
        restored = VideoTitleController(storage=self.state, module=self.module)
        self.assertFalse(restored.rows[0]["selected"])
        with self.assertRaises(ValueError):
            restored.start("update")

    def test_folder_change_preserves_scan_but_invalidates_old_preview(self):
        self.controller.change_settings(folder="another-folder")
        self.assertEqual(len(self.controller.rows), 1)
        self.assertEqual(self.controller.rows[0]["status"], "scanned")
        self.assertEqual(self.controller.rows[0]["new_title"], "")
        self.controller.change_settings(channel_id="another-channel")
        self.assertEqual(self.controller.rows, [])

    def test_checkpoint_failure_stops_before_any_mutation(self):
        self.state.fail = True
        self.run_update()
        self.module.update_title.assert_not_called()
        self.assertFalse(self.controller.busy)

    def test_stopping_first_row_keeps_second_for_next_pass(self):
        self.controller.rows.append(row(OTHER, status="ready", new_title="Song", selected=True))

        def update(*args, **kwargs):
            self.controller.stop()
            return {"title": "Song", "changed": True}

        self.module.update_title.side_effect = update
        self.run_update()
        self.assertEqual(self.module.update_title.call_count, 1)
        self.assertEqual(self.controller.rows[1]["status"], "ready")
        self.assertTrue(self.controller.rows[1]["selected"])

    def test_interrupted_row_is_retryable_and_uses_original_expected_title(self):
        self.controller.rows[0]["status"] = "processing"
        self.controller._save()
        restored = VideoTitleController(storage=self.state, module=self.module)
        self.assertEqual(restored.rows[0]["status"], "ready")
        restored.start("update")
        restored.thread.join(5)
        self.assertEqual(self.module.update_title.call_args.kwargs["expected_title"], "1026(1)_part40")

    def test_manual_candidate_must_be_one_of_the_duration_matches(self):
        target = self.controller.rows[0]
        target.update(status="ambiguous", selected=False, new_title="", candidates=[{"path":"matched.mp3", "seconds":60, "title":"Chosen song", "delta":0}])
        with self.assertRaises(ValueError):
            self.controller.select_candidate(VIDEO, "not-a-match.mp3")
        self.controller.select_candidate(VIDEO, "matched.mp3")
        self.assertEqual(target["new_title"], "Chosen song")
        self.assertTrue(target["selected"])


class TitlePageTests(unittest.TestCase):
    def test_action_button_uses_selected_controller_rows_and_refresh_reattaches(self):
        from nicegui import Client, ui
        from nicegui.page import page
        from web.components import video_titles
        state = MemoryState()
        module = Mock()
        module.update_title.return_value = {"title": "Song", "changed": True}
        controller = VideoTitleController(storage=state, module=module)
        controller.settings["channel_id"] = CHANNEL
        controller.rows = [row(status="ready", new_title="Song", selected=True, audio_duration=60), row(OTHER)]
        channel = SimpleNamespace(id=CHANNEL, name="Fixture channel", owner_email="fixture@example.test", img_src="")
        timers = []
        clients = []
        with patch.object(video_titles, "get_video_title_controller", return_value=controller), \
             patch.object(video_titles, "get_channels_info", return_value=[channel]), \
             patch.object(video_titles.ui, "timer", side_effect=lambda interval, callback, **kwargs: timers.append(callback)), \
             patch.object(video_titles.ui, "notify"):
            try:
                for iteration in range(2):
                    client = Client(page("/titles-ui-test"), request=None)
                    clients.append(client)
                    with client:
                        video_titles.create_video_titles_page()
                        table = next(item for item in client.elements.values() if isinstance(item, ui.table))
                        self.assertEqual(len(table.rows), 2)
                        if iteration == 0:
                            button = next(item for item in client.elements.values() if isinstance(item, ui.button) and item.text == "Đổi tiêu đề đã chọn")
                            listener = next(item for item in button._event_listeners.values() if item.type == "click")
                            inspect.getclosurevars(listener.handler).nonlocals["callback"]()
                            controller.thread.join(5)
                            timers[-1]()
                            self.assertEqual(table.rows[0]["status_label"], "Thành công")
                        else:
                            self.assertEqual(table.rows[0]["status_label"], "Thành công")
                            self.assertEqual(table.selected, [])
                module.update_title.assert_called_once()
                self.assertEqual(module.update_title.call_args.args[1], VIDEO)
            finally:
                for client in clients:
                    client.delete()

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "Requires FFmpeg")
    def test_real_audio_duration_is_read_before_preview(self):
        with tempfile.TemporaryDirectory() as folder:
            audio = Path(folder) / "Bài nhạc mẫu.mp3"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                            "-c:a", "libmp3lame", str(audio)], check=True, capture_output=True, timeout=20)
            matches, counts = build_title_matches([row(duration_seconds=2)], folder, tolerance=.2)
            self.assertEqual(matches[0]["new_title"], "Bài nhạc mẫu")
            self.assertEqual(matches[0]["status"], "ready")
            self.assertEqual(counts["unreadable"], 0)


if __name__ == "__main__":
    unittest.main()
