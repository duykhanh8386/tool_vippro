import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.youtube_mp3_download import (
    STATE_KEY,
    YoutubeMp3DownloadController,
    parse_youtube_urls,
    resolve_js_runtime,
)


class MemoryStateManager:
    def __init__(self):
        self.states = {}

    def load_state(self, key):
        return self.states.get(key)

    def save_state(self, key, value):
        self.states[key] = value
        return True


class YoutubeMp3DownloadTests(unittest.TestCase):
    def test_parses_only_youtube_video_urls_and_deduplicates(self):
        urls, invalid = parse_youtube_urls(
            "https://youtu.be/abc\nhttps://www.youtube.com/watch?v=def\n"
            "https://youtu.be/abc\nhttps://example.com/not-youtube"
        )

        self.assertEqual(
            urls,
            ["https://youtu.be/abc", "https://www.youtube.com/watch?v=def"],
        )
        self.assertEqual(invalid, ["https://example.com/not-youtube"])

    def test_restart_keeps_completed_items_and_retries_interrupted_item(self):
        state = MemoryStateManager()
        with tempfile.TemporaryDirectory() as temporary_dir:
            state.states[STATE_KEY] = {
                "urls": ["https://youtu.be/complete", "https://youtu.be/live"],
                "output_dir": temporary_dir,
                "items": {
                    "https://youtu.be/complete": {"status": "successful", "progress": 100},
                    "https://youtu.be/live": {"status": "downloading", "progress": 42},
                },
            }
            with patch("src.youtube_mp3_download.state_manager", state):
                controller = YoutubeMp3DownloadController()

        self.assertEqual(controller.items["https://youtu.be/complete"]["status"], "successful")
        self.assertEqual(controller.items["https://youtu.be/live"]["status"], "pending")
        self.assertEqual(controller.items["https://youtu.be/live"]["progress"], 0)
        self.assertEqual(state.states[STATE_KEY]["items"]["https://youtu.be/live"]["status"], "pending")

    def test_replacing_queue_preserves_completed_url(self):
        state = MemoryStateManager()
        with patch("src.youtube_mp3_download.state_manager", state):
            controller = YoutubeMp3DownloadController()
            controller.update_urls(["https://youtu.be/a", "https://youtu.be/b"])
            controller.items["https://youtu.be/a"].update(
                status="successful", progress=100, output_path="a.mp3"
            )
            controller.update_urls(["https://youtu.be/a", "https://youtu.be/c"])

        self.assertEqual(controller.items["https://youtu.be/a"]["status"], "successful")
        self.assertEqual(controller.items["https://youtu.be/a"]["output_path"], "a.mp3")
        self.assertEqual(controller.items["https://youtu.be/c"]["status"], "pending")

    def test_download_uses_audio_only_mp3_postprocessor(self):
        state = MemoryStateManager()
        captured = {}

        class FakeYoutubeDL:
            def __init__(self, options):
                captured.update(options)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def extract_info(self, _url, download):
                self_options = captured
                self_options["progress_hooks"][0](
                    {"status": "downloading", "downloaded_bytes": 1, "total_bytes": 2}
                )
                if not download:
                    raise AssertionError("download must be enabled")
                return {"title": "Song", "id": "video"}

            def prepare_filename(self, _info):
                return captured["outtmpl"].replace(
                    "%(title).180B [%(id)s].%(ext)s", "Song [video].webm"
                )

        with tempfile.TemporaryDirectory() as temporary_dir:
            with (
                patch("src.youtube_mp3_download.state_manager", state),
                patch("src.youtube_mp3_download.YoutubeDL", FakeYoutubeDL),
            ):
                controller = YoutubeMp3DownloadController()
                controller.set_output_dir(temporary_dir)
                result = controller._download_one("https://youtu.be/video", temporary_dir)

        self.assertEqual(result["title"], "Song")
        self.assertTrue(result["output_path"].endswith("Song [video].mp3"))
        self.assertEqual(captured["format"], "bestaudio/best")
        self.assertTrue(captured["noplaylist"])
        self.assertTrue(captured["continuedl"])
        self.assertEqual(captured["postprocessors"][0]["preferredcodec"], "mp3")

    def test_prefers_available_javascript_runtime(self):
        with patch("src.youtube_mp3_download.shutil.which", side_effect=[None, "C:/node.exe"]):
            self.assertEqual(resolve_js_runtime(), ("node", "C:/node.exe"))


if __name__ == "__main__":
    unittest.main()
