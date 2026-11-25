"""Check that downloaded thumbnail bytes become a JPEG before chat upload."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.publishing_browser import PublishingBrowserError, download_reference_image
from src.task_runtime import TaskStopped


class ReferenceImageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.destination = Path(self.folder.name) / "reference.jpg"
        self.response = Mock(status_code=200, headers={"Content-Type": "image/avif"})
        self.response.iter_content.return_value = [b"\x00\x00\x00 ftypavif", b"image bytes"]
        self.request = patch("requests.get").start()
        self.request.return_value.__enter__.return_value = self.response
        self.addCleanup(patch.stopall)

    def test_avif_response_is_decoded_instead_of_renamed_to_jpg(self):
        sources = []
        def convert(source, destination):
            sources.append(source)
            self.assertEqual(source.read_bytes(), b"\x00\x00\x00 ftypavifimage bytes")
            self.assertNotEqual(source, destination)
            destination.write_bytes(b"\xff\xd8\xffJPEG")
            return str(destination)
        with patch("src.publishing_browser.normalize_thumbnail", side_effect=convert):
            result = download_reference_image("https://i.ytimg.com/vi/Abc123_-XYZ/hqdefault.jpg", self.destination)
        self.assertEqual(result, str(self.destination))
        self.assertTrue(self.destination.read_bytes().startswith(b"\xff\xd8\xff"))
        self.assertFalse(sources[0].exists())

    def test_conversion_failure_removes_raw_download_and_stops_before_upload(self):
        with patch("src.publishing_browser.normalize_thumbnail", side_effect=PublishingBrowserError("Invalid image")), \
                self.assertRaises(PublishingBrowserError):
            download_reference_image("https://i.ytimg.com/vi/Abc123_-XYZ/hqdefault.jpg", self.destination)
        self.assertEqual(list(self.destination.parent.iterdir()), [])

    def test_stop_during_download_removes_partial_file(self):
        self.response.iter_content.side_effect = TaskStopped()
        with self.assertRaises(TaskStopped):
            download_reference_image("https://i.ytimg.com/vi/Abc123_-XYZ/hqdefault.jpg", self.destination)
        self.assertEqual(list(self.destination.parent.iterdir()), [])

    def test_oversized_image_is_rejected_before_conversion(self):
        self.response.iter_content.return_value = [b"x" * (20 * 1024 * 1024 + 1)]
        with patch("src.publishing_browser.normalize_thumbnail") as convert, self.assertRaises(PublishingBrowserError):
            download_reference_image("https://i.ytimg.com/vi/Abc123_-XYZ/hqdefault.jpg", self.destination)
        convert.assert_not_called()
        self.assertEqual(list(self.destination.parent.iterdir()), [])

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is unavailable")
    def test_real_avif_at_jpg_url_is_converted_to_a_real_jpeg(self):
        source = self.destination.with_suffix(".avif")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=blue:s=640x360",
                        "-frames:v", "1", "-c:v", "libaom-av1", "-cpu-used", "8", "-still-picture", "1", str(source)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        content = source.read_bytes()
        self.assertIn(b"ftypavif", content[:24])
        self.response.iter_content.return_value = [content]
        download_reference_image("https://i.ytimg.com/vi/Abc123_-XYZ/hqdefault.jpg", self.destination)
        self.assertTrue(self.destination.read_bytes().startswith(b"\xff\xd8\xff"))
        self.assertLess(self.destination.stat().st_size, 2 * 1024 * 1024)
        self.assertEqual(sorted(path.suffix for path in self.destination.parent.iterdir()), [".avif", ".jpg"])


if __name__ == "__main__":
    unittest.main()
