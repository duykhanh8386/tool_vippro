import unittest

from src.utils import (
    DEFAULT_VIDEO_BITRATE,
    DEFAULT_VIDEO_BUFSIZE,
    DEFAULT_VIDEO_MAXRATE,
    _video_quality_args,
)


class VideoQualityTests(unittest.TestCase):
    def _default_args(self):
        return [
            "-b:v", DEFAULT_VIDEO_BITRATE,
            "-maxrate", DEFAULT_VIDEO_MAXRATE,
            "-bufsize", DEFAULT_VIDEO_BUFSIZE,
        ]

    def test_cpu_uses_balanced_bitrate_by_default(self):
        self.assertEqual(
            _video_quality_args(qsv=False, video_bitrate=None), self._default_args()
        )

    def test_qsv_uses_balanced_bitrate_by_default(self):
        self.assertEqual(
            _video_quality_args(qsv=True, video_bitrate=None), self._default_args()
        )

    def test_explicit_bitrate_override_is_preserved(self):
        self.assertEqual(
            _video_quality_args(qsv=False, video_bitrate="8M"),
            ["-b:v", "8M"],
        )


if __name__ == "__main__":
    unittest.main()
