import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.audio_batch_matcher import (
    build_audio_rename_plan,
    execute_audio_rename_plan,
    match_audio_files,
    match_audio_files_by_title,
    match_audio_files_sequentially,
    normalize_title,
)


def video(video_id: str, title: str, duration_seconds: float = 60):
    return SimpleNamespace(id=video_id, title=title, duration_ms=duration_seconds * 1000)


class AudioBatchMatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def touch(self, relative_path: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        return path.resolve()

    def test_duration_match_accepts_two_second_delta(self):
        expected = self.touch("random-name.m4a")

        result = match_audio_files(
            [video("RQ1sE4Oo-8Y", "Tên video", 120)],
            self.root,
            duration_reader=lambda _path: 121.9,
        )

        self.assertEqual(result.matched[0].path, str(expected))
        self.assertEqual(result.matched[0].status, "duration")
        self.assertIn("lệch 1.9s", result.matched[0].detail)

    def test_duration_match_rejects_file_outside_tolerance(self):
        extra = self.touch("random-name.m4a")

        result = match_audio_files(
            [video("abcdefghijk", "Video", 120)],
            self.root,
            duration_reader=lambda _path: 122.1,
        )

        self.assertEqual(len(result.matched), 0)
        self.assertEqual(result.unmatched[0].video_id, "abcdefghijk")
        self.assertEqual(result.extra_files, (str(extra),))

    def test_equal_duration_candidates_use_title_to_disambiguate(self):
        expected = self.touch("prefix Nhạc Thư Giãn bản mới.flac")
        self.touch("other.wav")

        result = match_audio_files(
            [video("abcdefghijk", "Nhạc thư giãn", 60)],
            self.root,
            duration_reader=lambda _path: 60,
        )

        self.assertEqual(result.matched[0].path, str(expected))
        self.assertEqual(result.matched[0].status, "duration")

    def test_equal_duration_candidates_use_stable_filename_order(self):
        first = self.touch("first.mp3")
        second = self.touch("second.wav")

        result = match_audio_files(
            [video("abcdefghijk", "Unrelated", 60)],
            self.root,
            duration_reader=lambda _path: 60,
        )

        self.assertEqual(result.matched[0].path, str(first))
        self.assertEqual(result.extra_files, (str(second),))

    def test_one_audio_is_assigned_to_the_closest_of_similar_videos(self):
        audio = self.touch("shared.mp3")

        result = match_audio_files(
            [
                video("video000001", "First", 100),
                video("video000002", "Second", 101),
            ],
            self.root,
            duration_reader=lambda _path: 100.8,
        )

        self.assertEqual(
            [(item.video_id, item.path) for item in result.matched],
            [("video000002", str(audio))],
        )
        self.assertIn("gần hơn", result.unmatched[0].detail)

    def test_equal_video_durations_use_title_then_channel_order(self):
        audio = self.touch("Second official audio.mp3")

        result = match_audio_files(
            [
                video("video000001", "First", 100),
                video("video000002", "Second", 100),
            ],
            self.root,
            duration_reader=lambda _path: 100,
        )

        self.assertEqual(result.matched[0].video_id, "video000002")
        self.assertEqual(result.matched[0].path, str(audio))

    def test_youtube_title_only_needs_to_be_contained_in_filename(self):
        expected = self.touch("001 - nhac dem thu gian - final mix.flac")

        result = match_audio_files_by_title(
            [video("abcdefghijk", "Nhạc Đêm Thư Giãn")], self.root
        )

        self.assertEqual(normalize_title("Nhạc thư giãn"), "nhacthugian")
        self.assertEqual(result.matched[0].path, str(expected))
        self.assertEqual(result.matched[0].status, "title")

    def test_duplicate_channel_titles_are_not_auto_matched(self):
        self.touch("Same title.mp3")

        result = match_audio_files_by_title(
            [video("abcdefghijk", "Same title"), video("lmnopqrstuv", "Same title")],
            self.root,
        )

        self.assertEqual(len(result.matched), 0)
        self.assertEqual(len(result.ambiguous), 2)

    def test_mapping_csv_can_use_relative_audio_path(self):
        expected = self.touch("custom/audio.ogg")
        with (self.root / "mapping.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["video_id", "audio_file"])
            writer.writeheader()
            writer.writerow({"video_id": "abcdefghijk", "audio_file": "custom/audio.ogg"})

        result = match_audio_files(
            [video("abcdefghijk", "Video")],
            self.root,
            duration_reader=lambda _path: 999,
        )

        self.assertEqual(result.matched[0].path, str(expected))
        self.assertEqual(result.matched[0].status, "mapping")

    def test_unmatched_video_and_extra_audio_are_reported(self):
        extra = self.touch("other.mp3")

        result = match_audio_files(
            [video("abcdefghijk", "No match", 60)],
            self.root,
            duration_reader=lambda _path: 90,
        )

        self.assertEqual(result.unmatched[0].video_id, "abcdefghijk")
        self.assertEqual(result.extra_files, (str(extra),))

    def test_sequential_match_uses_channel_order_and_natural_filename_order(self):
        first = self.touch("track1.mp3")
        second = self.touch("track2.m4a")
        extra = self.touch("track10.wav")

        result = match_audio_files_sequentially(
            [video("video000001", "Newest"), video("video000002", "Older")],
            self.root,
        )

        self.assertEqual(
            [(item.video_id, item.path) for item in result.matched],
            [("video000001", str(first)), ("video000002", str(second))],
        )
        self.assertEqual(result.extra_files, (str(extra),))

    def test_rename_plan_preserves_extension_and_renames_file(self):
        source = self.touch("track 01.M4A")
        plan = build_audio_rename_plan([("RQ1sE4Oo-8Y", source)])

        changed = execute_audio_rename_plan(plan)

        expected = source.with_name("RQ1sE4Oo-8Y.m4a")
        self.assertEqual(changed, {"RQ1sE4Oo-8Y": str(expected)})
        self.assertTrue(expected.is_file())
        self.assertFalse(source.exists())

    def test_rename_plan_rejects_existing_target_without_mutating_files(self):
        source = self.touch("track.mp3")
        target = self.touch("RQ1sE4Oo-8Y.mp3")

        with self.assertRaisesRegex(ValueError, "đã tồn tại"):
            build_audio_rename_plan([("RQ1sE4Oo-8Y", source)])

        self.assertTrue(source.is_file())
        self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
