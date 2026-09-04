import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

from src.module.base import YouTubeRequestError, _response_json_or_error
from src.module.upload_video_module import (
    UploadVideoModule,
    VideoProcessingResult,
    VideoProcessingState,
)
from web.components.add_audio_flow import (
    YouTubeProcessingTimeoutError,
    YouTubeProcessingWaitError,
    _run_supervised_queue,
    _wait_for_youtube_processing,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds
        await asyncio.sleep(0)


def result(state, message="", **kwargs):
    return VideoProcessingResult(state, message=message, **kwargs)


class YouTubeProcessingWaitTests(unittest.IsolatedAsyncioTestCase):
    async def run_sequence(self, sequence, **kwargs):
        clock = kwargs.pop("clock", FakeClock())
        values = iter(sequence)
        calls = []

        async def check():
            value = next(values)
            calls.append(value)
            return value

        resolved = await _wait_for_youtube_processing(
            check,
            video_id="video-1",
            timeout_seconds=kwargs.pop("timeout_seconds", 120),
            poll_interval_seconds=kwargs.pop("poll_interval_seconds", 15),
            monotonic=clock.monotonic,
            sleep=clock.sleep,
            **kwargs,
        )
        return resolved, calls, clock

    async def test_processing_then_processed(self):
        resolved, calls, _ = await self.run_sequence(
            [
                result(VideoProcessingState.PROCESSING),
                result(VideoProcessingState.PROCESSING),
                result(VideoProcessingState.PROCESSED),
            ]
        )

        self.assertEqual(resolved.state, VideoProcessingState.PROCESSED)
        self.assertEqual(len(calls), 3)

    async def test_processing_timeout_is_not_reported_as_network_or_auth(self):
        clock = FakeClock()

        async def processing():
            return result(VideoProcessingState.PROCESSING)

        with self.assertRaises(YouTubeProcessingTimeoutError) as raised:
            await _wait_for_youtube_processing(
                processing,
                video_id="video-timeout",
                timeout_seconds=30,
                poll_interval_seconds=15,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )

        self.assertIn("processing timeout", str(raised.exception))
        self.assertNotIn("authentication", str(raised.exception))
        self.assertNotIn("status check failed", str(raised.exception))

    async def test_transient_errors_recover_and_counter_resets(self):
        transient = result(
            VideoProcessingState.TRANSIENT_ERROR,
            "network timeout",
            error_type="Timeout",
        )
        resolved, calls, _ = await self.run_sequence(
            [
                transient,
                transient,
                result(VideoProcessingState.PROCESSING),
                result(VideoProcessingState.PROCESSED),
            ],
            max_consecutive_transient_errors=3,
        )

        self.assertEqual(resolved.state, VideoProcessingState.PROCESSED)
        self.assertEqual(len(calls), 4)

    async def test_too_many_consecutive_transient_errors_fail_early(self):
        clock = FakeClock()
        calls = 0

        async def failing_check():
            nonlocal calls
            calls += 1
            return result(
                VideoProcessingState.TRANSIENT_ERROR,
                "connection reset",
                error_type="ConnectionError",
            )

        with self.assertRaises(YouTubeProcessingWaitError) as raised:
            await _wait_for_youtube_processing(
                failing_check,
                video_id="video-network",
                timeout_seconds=1200,
                poll_interval_seconds=15,
                max_consecutive_transient_errors=3,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )

        self.assertEqual(calls, 3)
        self.assertEqual(
            raised.exception.state,
            VideoProcessingState.TRANSIENT_ERROR,
        )
        self.assertLess(clock.now, 1200)

    async def test_auth_error_fails_immediately(self):
        clock = FakeClock()
        calls = 0

        async def auth_error():
            nonlocal calls
            calls += 1
            return result(
                VideoProcessingState.AUTH_ERROR,
                "YouTube authentication/session failed (HTTP 401)",
                http_status=401,
            )

        with self.assertRaises(YouTubeProcessingWaitError) as raised:
            await _wait_for_youtube_processing(
                auth_error,
                video_id="video-auth",
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )

        self.assertEqual(calls, 1)
        self.assertEqual(raised.exception.state, VideoProcessingState.AUTH_ERROR)
        self.assertEqual(clock.now, 0)

    async def test_unknown_response_fails_instead_of_becoming_processing(self):
        async def unknown():
            return result(
                VideoProcessingState.UNKNOWN_ERROR,
                "YouTube trả trạng thái video không xác định: <empty>",
                error_type="UnknownYouTubeVideoStatus",
            )

        with self.assertRaises(YouTubeProcessingWaitError) as raised:
            await _wait_for_youtube_processing(unknown, video_id="video-unknown")

        self.assertEqual(raised.exception.state, VideoProcessingState.UNKNOWN_ERROR)

    async def test_deadline_includes_time_spent_inside_status_request(self):
        clock = FakeClock()
        calls = 0

        async def slow_processing_check():
            nonlocal calls
            calls += 1
            clock.now += 7
            return result(VideoProcessingState.PROCESSING)

        with self.assertRaises(YouTubeProcessingTimeoutError):
            await _wait_for_youtube_processing(
                slow_processing_check,
                video_id="video-slow-request",
                timeout_seconds=10,
                poll_interval_seconds=5,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )

        self.assertEqual(calls, 1)
        self.assertEqual(clock.now, 10)

    async def test_transient_request_crossing_deadline_is_not_processing_timeout(self):
        clock = FakeClock()

        async def slow_transient_check():
            clock.now += 12
            return result(
                VideoProcessingState.TRANSIENT_ERROR,
                "read timed out",
                error_type="Timeout",
            )

        with self.assertRaises(YouTubeProcessingWaitError) as raised:
            await _wait_for_youtube_processing(
                slow_transient_check,
                video_id="video-slow-network",
                timeout_seconds=10,
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )

        self.assertNotIsInstance(
            raised.exception,
            YouTubeProcessingTimeoutError,
        )
        self.assertEqual(
            raised.exception.state,
            VideoProcessingState.TRANSIENT_ERROR,
        )

    async def test_one_auth_failure_does_not_stop_other_queue_items(self):
        states = {"A": "pending", "B": "pending", "C": "pending"}

        async def process_item(item):
            async def check():
                if item == "B":
                    return result(
                        VideoProcessingState.AUTH_ERROR,
                        "YouTube authentication/session failed",
                    )
                return result(VideoProcessingState.PROCESSED)

            try:
                await _wait_for_youtube_processing(check, video_id=item)
            except YouTubeProcessingWaitError:
                states[item] = "unsuccessful"
            else:
                states[item] = "successful"

        errors, remaining = await _run_supervised_queue(
            list(states),
            2,
            process_item,
            lambda: False,
            lambda item, exc: self.fail(f"unexpected error for {item}: {exc}"),
        )

        self.assertEqual(
            states,
            {"A": "successful", "B": "unsuccessful", "C": "successful"},
        )
        self.assertEqual(errors, [])
        self.assertEqual(remaining, [])


class VideoProcessingClassificationTests(unittest.TestCase):
    def setUp(self):
        self.module = UploadVideoModule()
        self.channel_patch = patch(
            "src.module.upload_video_module.get_channels_info",
            return_value=object(),
        )
        self.channel_patch.start()
        self.addCleanup(self.channel_patch.stop)

    def test_request_timeout_is_transient(self):
        with patch.object(
            self.module,
            "_get_video_info",
            side_effect=requests.Timeout("read timed out"),
        ):
            resolved = self.module.get_processing_status("channel", "video")

        self.assertEqual(resolved.state, VideoProcessingState.TRANSIENT_ERROR)
        self.assertEqual(resolved.error_type, "Timeout")

    def test_http_401_and_403_are_auth_errors(self):
        for status_code in (401, 403):
            with self.subTest(status_code=status_code), patch.object(
                self.module,
                "_get_video_info",
                side_effect=YouTubeRequestError(
                    "request failed",
                    status_code=status_code,
                ),
            ):
                resolved = self.module.get_processing_status("channel", "video")
                self.assertEqual(resolved.state, VideoProcessingState.AUTH_ERROR)
                self.assertEqual(resolved.http_status, status_code)

    def test_http_404_is_permanent(self):
        with patch.object(
            self.module,
            "_get_video_info",
            side_effect=YouTubeRequestError("not found", status_code=404),
        ):
            resolved = self.module.get_processing_status("channel", "video")

        self.assertEqual(resolved.state, VideoProcessingState.PERMANENT_ERROR)

    def test_invalid_response_and_unknown_status_are_unknown_errors(self):
        with patch.object(
            self.module,
            "_get_video_info",
            side_effect=YouTubeRequestError("invalid JSON", status_code=200),
        ):
            invalid = self.module.get_processing_status("channel", "video")
        with patch.object(
            self.module,
            "_get_video_info",
            return_value=SimpleNamespace(video_status="VIDEO_STATUS_NEW_VALUE"),
        ):
            unknown = self.module.get_processing_status("channel", "video")

        self.assertEqual(invalid.state, VideoProcessingState.UNKNOWN_ERROR)
        self.assertEqual(unknown.state, VideoProcessingState.UNKNOWN_ERROR)

    def test_bool_compatibility_api_does_not_hide_errors_as_false(self):
        with patch.object(
            self.module,
            "get_processing_status",
            return_value=result(
                VideoProcessingState.AUTH_ERROR,
                "authentication failed",
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.module.is_processed("channel", "video")


class YouTubeResponseErrorTests(unittest.TestCase):
    def test_http_status_is_preserved_without_copying_raw_response_body(self):
        class Response:
            status_code = 401
            text = "sessionToken=must-not-appear"

            @staticmethod
            def json():
                raise ValueError("not JSON")

        with self.assertRaises(YouTubeRequestError) as raised:
            _response_json_or_error(Response(), "video status check")

        self.assertEqual(raised.exception.status_code, 401)
        self.assertNotIn("must-not-appear", str(raised.exception))
        self.assertEqual(raised.exception.response_excerpt, "")


if __name__ == "__main__":
    unittest.main()
