import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import audio_recovery as recovery
from src.task_runtime import TaskStopped
from src.utils import multiply_audio
from web.components.drawer import _recovery_transfer_text


class AudioPreparationTests(unittest.TestCase):
    def test_stop_during_copy_does_not_start_encoding(self):
        with patch("src.utils.get_video_duration", return_value=10), patch(
            "src.utils.run_owned_process", side_effect=TaskStopped("stopped"),
        ) as run:
            with self.assertRaises(TaskStopped):
                multiply_audio("input.mp3", "output.mp3", times=1)
        run.assert_called_once()

    def test_registry_verification_is_distinct_from_sending_a_file(self):
        text = _recovery_transfer_text({"phase": "uploading", "upload_status": "verifying"})
        self.assertIn("kiểm tra track", text)

    def test_registry_distinguishes_confirmed_processing_from_published(self):
        for state, expected in [("processing", "đang xử lý"), ("published", "Đã xuất bản")]:
            snapshot = recovery._with_upload_progress({"phase": "uploading", "_upload_progress": {
                "status": "complete", "studio_state": state, "sent": 10, "total": 10, "confirmed": 10,
            }})
            self.assertIn(expected, _recovery_transfer_text(snapshot))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools are unavailable")
class RealAudioPreparationTests(unittest.TestCase):
    def probe(self, path, *args):
        result = subprocess.run(["ffprobe", "-v", "error", *args, "-of", "json", str(path)],
                                check=True, capture_output=True, text=True, timeout=20)
        return json.loads(result.stdout)

    def generate(self, path, codec):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=2", "-c:a", codec, str(path)],
                       check=True, capture_output=True, timeout=20)

    def test_mp3_copy_preserves_audio_packets_and_trims_duration(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "source.mp3", Path(folder) / "output.mp3"
            self.generate(source, "libmp3lame")
            multiply_audio(str(source), str(output), times=1, video_duration_seconds=1.2)
            def hashes(path):
                return [packet["data_hash"] for packet in self.probe(
                    path, "-select_streams", "a:0", "-show_packets", "-show_data_hash", "sha256",
                    "-show_entries", "packet=data_hash",
                )["packets"]]
            copied, original = hashes(output), hashes(source)
            self.assertGreater(len(copied), 10)
            self.assertEqual(copied, original[:len(copied)])
            info = self.probe(output, "-show_entries", "format=duration:stream=codec_name,codec_type")
            self.assertAlmostEqual(float(info["format"]["duration"]), 1.2, delta=0.1)
            self.assertEqual(info["streams"][0]["codec_name"], "mp3")

    def test_aac_input_falls_back_to_a_valid_mp3_with_video_duration(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "source.m4a", Path(folder) / "output.mp3"
            self.generate(source, "aac")
            multiply_audio(str(source), str(output), times=1, video_duration_seconds=2.7)
            info = self.probe(output, "-show_entries", "format=duration:stream=codec_name,codec_type")
            self.assertEqual([item["codec_name"] for item in info["streams"]], ["mp3"])
            self.assertAlmostEqual(float(info["format"]["duration"]), 2.7, delta=0.1)


if __name__ == "__main__":
    unittest.main()
