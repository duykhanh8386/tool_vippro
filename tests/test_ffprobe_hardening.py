import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.utils import (
    FFprobeError,
    FFprobeErrorCategory,
    get_video_duration,
)
from web.components.add_audio_flow import _run_supervised_queue


def completed_duration(duration: float) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        ["ffprobe"],
        0,
        stdout=f'{{"format": {{"duration": "{duration}"}}}}'.encode(),
        stderr=b"",
    )


def failed_probe(stderr: str) -> subprocess.CalledProcessError:
    return subprocess.CalledProcessError(
        1,
        ["ffprobe"],
        output=b"",
        stderr=stderr.encode(),
    )


class FFprobeHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def media_file(self, name: str = "video.mp4", content: bytes = b"media") -> Path:
        path = Path(self.temp_dir.name) / name
        path.write_bytes(content)
        return path

    def test_valid_video_returns_float_without_retry(self):
        path = self.media_file()
        sleeps = []
        with patch(
            "src.utils.run_owned_process",
            return_value=completed_duration(12.5),
        ) as probe:
            duration = get_video_duration(path, sleep=sleeps.append)

        self.assertEqual(duration, 12.5)
        self.assertEqual(probe.call_count, 1)
        self.assertEqual(sleeps, [])

    def test_missing_file_fails_without_calling_ffprobe(self):
        path = Path(self.temp_dir.name) / "missing.mp4"
        with patch("src.utils.run_owned_process") as probe:
            with self.assertRaises(FFprobeError) as raised:
                get_video_duration(path, sleep=lambda _: None)

        self.assertEqual(raised.exception.category, FFprobeErrorCategory.FILE_NOT_FOUND)
        probe.assert_not_called()

    def test_zero_size_file_is_not_ready_and_never_probed(self):
        path = self.media_file(content=b"")
        sleeps = []
        with patch("src.utils.run_owned_process") as probe:
            with self.assertRaises(FFprobeError) as raised:
                get_video_duration(
                    path,
                    max_attempts=3,
                    retry_delay=0.1,
                    sleep=sleeps.append,
                )

        self.assertEqual(raised.exception.category, FFprobeErrorCategory.FILE_NOT_READY)
        self.assertEqual(raised.exception.attempt, 3)
        self.assertEqual(sleeps, [0.1, 0.1])
        probe.assert_not_called()

    def test_invalid_media_fails_without_retry(self):
        path = self.media_file()
        with patch(
            "src.utils.run_owned_process",
            side_effect=failed_probe("Invalid data found when processing input"),
        ) as probe:
            with self.assertRaises(FFprobeError) as raised:
                get_video_duration(path, sleep=lambda _: None)

        self.assertEqual(raised.exception.category, FFprobeErrorCategory.INVALID_MEDIA)
        self.assertIn("Invalid data found", str(raised.exception))
        self.assertEqual(probe.call_count, 1)

    def test_moov_atom_not_found_is_invalid_media(self):
        path = self.media_file()
        with patch(
            "src.utils.run_owned_process",
            side_effect=failed_probe("moov atom not found"),
        ) as probe:
            with self.assertRaises(FFprobeError) as raised:
                get_video_duration(path, sleep=lambda _: None)

        self.assertEqual(raised.exception.category, FFprobeErrorCategory.INVALID_MEDIA)
        self.assertIn("moov atom not found", raised.exception.stderr)
        self.assertEqual(probe.call_count, 1)

    def test_transient_failure_retries_then_succeeds(self):
        path = self.media_file()
        sleeps = []
        with patch(
            "src.utils.run_owned_process",
            side_effect=[
                failed_probe("Resource temporarily unavailable"),
                completed_duration(9.75),
            ],
        ) as probe:
            duration = get_video_duration(
                path,
                retry_delay=0.2,
                sleep=sleeps.append,
            )

        self.assertEqual(duration, 9.75)
        self.assertEqual(probe.call_count, 2)
        self.assertEqual(sleeps, [0.2])

    def test_transient_retry_exhaustion_has_clear_diagnostic(self):
        path = self.media_file()
        with patch(
            "src.utils.run_owned_process",
            side_effect=failed_probe("sharing violation"),
        ) as probe:
            with self.assertRaises(FFprobeError) as raised:
                get_video_duration(
                    path,
                    max_attempts=3,
                    retry_delay=0,
                    sleep=lambda _: None,
                )

        error = raised.exception
        self.assertEqual(error.category, FFprobeErrorCategory.TRANSIENT)
        self.assertEqual(error.attempt, 3)
        self.assertEqual(probe.call_count, 3)
        self.assertIn("ffprobe_exit=1", str(error))
        self.assertIn("sharing violation", str(error))

    def test_stderr_is_preserved_but_sensitive_assignment_is_redacted(self):
        path = self.media_file()
        stderr = (
            "Invalid data found when processing input\n"
            "authorization=must-not-leak"
        )
        with patch(
            "src.utils.run_owned_process",
            side_effect=failed_probe(stderr),
        ):
            with self.assertRaises(FFprobeError) as raised:
                get_video_duration(path, sleep=lambda _: None)

        diagnostic = str(raised.exception)
        self.assertIn("Invalid data found when processing input", diagnostic)
        self.assertIn("authorization=<redacted>", diagnostic)
        self.assertNotIn("must-not-leak", diagnostic)


class FFprobeBatchIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_invalid_video_does_not_stop_batch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = []
            for name in ("A.mp4", "B.mp4", "C.mp4"):
                path = Path(temp_dir) / name
                path.write_bytes(b"media")
                paths.append(path)

            states = {path.name: "pending" for path in paths}

            def probe(command, **_kwargs):
                if Path(command[-1]).name == "B.mp4":
                    raise failed_probe("moov atom not found")
                return completed_duration(5.0)

            async def process_item(path):
                get_video_duration(path, sleep=lambda _: None)
                states[path.name] = "successful"

            def record_error(path, _exc):
                states[path.name] = "unsuccessful"

            with patch("src.utils.run_owned_process", side_effect=probe):
                errors, remaining = await _run_supervised_queue(
                    paths,
                    2,
                    process_item,
                    lambda: False,
                    record_error,
                )

        self.assertEqual(
            states,
            {
                "A.mp4": "successful",
                "B.mp4": "unsuccessful",
                "C.mp4": "successful",
            },
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
