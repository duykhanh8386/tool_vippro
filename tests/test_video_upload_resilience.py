from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.module.upload_video_module import UploadVideoModule


class VideoUploadResilienceTests(unittest.TestCase):
    def test_uses_smaller_chunks_and_extended_timeout(self):
        module = UploadVideoModule()
        response = Mock(status_code=200, headers={"X-Goog-Upload-Status": "final"})

        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"x" * (module._CHUNK_TARGET + 1))

            with patch(
                "src.module.upload_video_module.post_with_stop",
                side_effect=[response, response],
            ) as post:
                module._upload_bytes(
                    "https://upload.example/session",
                    "cookie",
                    "video.mp4",
                    str(video),
                    granularity=1,
                )

        self.assertEqual(module._CHUNK_TARGET, 4 * 1024 * 1024)
        self.assertEqual(post.call_count, 2)
        self.assertTrue(
            all(call.kwargs["timeout"] == (30, 180) for call in post.call_args_list)
        )

    def test_timeout_queries_offset_and_uses_exponential_backoff(self):
        module = UploadVideoModule()
        response = Mock(status_code=200, headers={"X-Goog-Upload-Status": "final"})

        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"content")

            with (
                patch(
                    "src.module.upload_video_module.post_with_stop",
                    side_effect=[TimeoutError("write timed out"), response],
                ) as post,
                patch.object(module, "_query_offset", return_value=0) as query,
                patch("src.module.upload_video_module.wait_interruptibly") as wait,
            ):
                module._upload_bytes(
                    "https://upload.example/session",
                    "cookie",
                    "video.mp4",
                    str(video),
                    granularity=1,
                )

        self.assertEqual(post.call_count, 2)
        self.assertTrue(
            all(call.kwargs["timeout"] == (30, 180) for call in post.call_args_list)
        )
        query.assert_called_once()
        wait.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
