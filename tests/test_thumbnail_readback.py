import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.publishing_thumbnails import ThumbnailReadback, same_thumbnail


class ThumbnailReadbackTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "expected.jpg"
        self.path.write_bytes(b"image")
        self.reader = Mock(return_value=SimpleNamespace(id="Abc123_-XYZ", channel_id="channel", thumbnail="https://i.ytimg.com/old.jpg",
                          thumbnail_details={"thumbnails": [{"url":"https://i.ytimg.com/small.jpg","width":120},
                                                              {"url":"https://i.ytimg.com/large.jpg","width":1280}]}))
        self.pixels = patch("src.publishing_thumbnails.thumbnail_pixels", return_value=bytes([100] * 43200)).start()
        self.request = patch("requests.get").start()
        self.addCleanup(patch.stopall)
        self.response = Mock(status_code=200, headers={"Content-Type":"image/jpeg"})
        self.response.iter_content.return_value = [b"saved image"]
        self.request.return_value.__enter__.return_value = self.response

    def verifier(self):
        return ThumbnailReadback("channel", "Abc123_-XYZ", self.path, reader=self.reader)

    def test_saved_image_is_read_from_owned_video_at_best_resolution(self):
        self.assertTrue(self.verifier()())
        self.reader.assert_called_once_with("channel", "Abc123_-XYZ")
        self.assertEqual(self.request.call_args.args[0], "https://i.ytimg.com/large.jpg")

    def test_foreign_video_cannot_confirm_upload(self):
        self.reader.return_value.id = "Def123_-XYZ"
        with self.assertRaises(ValueError):
            self.verifier()()
        self.request.assert_not_called()

    def test_other_image_and_non_image_response_do_not_confirm(self):
        self.pixels.side_effect = [bytes([100] * 43200), bytes([200] * 43200)]
        self.assertFalse(self.verifier()())
        self.pixels.side_effect = None
        self.response.headers = {"Content-Type":"text/html"}
        self.assertFalse(self.verifier()())

    def test_invalid_image_host_is_not_downloaded(self):
        self.reader.return_value.thumbnail_details = {}
        self.reader.return_value.thumbnail = "https://example.com/image.jpg"
        self.assertFalse(self.verifier()())
        self.request.assert_not_called()

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg unavailable")
    def test_real_jpeg_recompression_matches_but_a_different_image_does_not(self):
        self.pixels.stop()
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","testsrc2=s=640x360",
                        "-frames:v","1","-q:v","2",str(self.path)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       )
        compressed = self.path.with_name("compressed.jpg")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",str(self.path),"-q:v","10",str(compressed)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.response.iter_content.return_value = [compressed.read_bytes()]
        verifier = self.verifier()
        self.assertTrue(verifier())
        from src.publishing_thumbnails import thumbnail_pixels
        self.assertFalse(same_thumbnail(thumbnail_pixels(self.path), bytes([0] * 43200)))


if __name__ == "__main__":
    unittest.main()
