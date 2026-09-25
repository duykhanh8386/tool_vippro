import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.audio_batch_matcher import match_audio_files, normalize_title


def video(video_id: str, title: str):
    return SimpleNamespace(id=video_id, title=title)


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

    def test_video_id_filename_has_priority_and_supports_m4a(self):
        expected = self.touch("RQ1sE4Oo-8Y__vi.m4a")
        self.touch("Tên video.mp3")

        result = match_audio_files([video("RQ1sE4Oo-8Y", "Tên video")], self.root)

        self.assertEqual(result.matched[0].path, str(expected))
        self.assertEqual(result.matched[0].status, "video_id")

    def test_exact_normalized_title_is_a_fallback(self):
        expected = self.touch("Nhạc Thư Giãn!.flac")

        result = match_audio_files([video("abcdefghijk", "Nhạc thư giãn")], self.root)

        self.assertEqual(normalize_title("Nhạc thư giãn"), "nhacthugian")
        self.assertEqual(result.matched[0].path, str(expected))
        self.assertEqual(result.matched[0].status, "title")

    def test_ambiguous_video_id_is_not_auto_selected(self):
        self.touch("abcdefghijk.mp3")
        self.touch("abcdefghijk__vi.wav")

        result = match_audio_files([video("abcdefghijk", "Video")], self.root)

        self.assertEqual(len(result.matched), 0)
        self.assertEqual(result.ambiguous[0].status, "ambiguous")
        self.assertEqual(len(result.ambiguous[0].candidates), 2)

    def test_duplicate_channel_titles_are_not_auto_matched(self):
        self.touch("Same title.mp3")

        result = match_audio_files(
            [video("abcdefghijk", "Same title"), video("lmnopqrstuv", "Same title")],
            self.root,
        )

        self.assertEqual(len(result.matched), 0)
        self.assertEqual(len(result.unmatched), 2)

    def test_mapping_csv_can_use_relative_audio_path(self):
        expected = self.touch("custom/audio.ogg")
        with (self.root / "mapping.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["video_id", "audio_file"])
            writer.writeheader()
            writer.writerow({"video_id": "abcdefghijk", "audio_file": "custom/audio.ogg"})

        result = match_audio_files([video("abcdefghijk", "Video")], self.root)

        self.assertEqual(result.matched[0].path, str(expected))
        self.assertEqual(result.matched[0].status, "mapping")

    def test_unmatched_video_and_extra_audio_are_reported(self):
        extra = self.touch("other.mp3")

        result = match_audio_files([video("abcdefghijk", "No match")], self.root)

        self.assertEqual(result.unmatched[0].video_id, "abcdefghijk")
        self.assertEqual(result.extra_files, (str(extra),))


if __name__ == "__main__":
    unittest.main()
