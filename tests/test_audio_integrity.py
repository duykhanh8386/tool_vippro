"""Tests for detecting intermittent 3s-on / 7s-silent original video audio."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import requests

from src.audio_integrity import (
    AudioIntegrityResult,
    SAMPLE_RATE,
    _build_channel_media_session,
    _is_allowed_youtube_media_url,
    analyze_pcm_audio,
    decode_audio_sample_from_stream,
    inspect_channel_videos_audio,
)


def _make_pcm_segments(segments, *, sample_rate=SAMPLE_RATE, freq=440.0, amplitude=12000):
    chunks = bytearray()
    t_index = 0
    for duration_sec, audible in segments:
        count = int(round(duration_sec * sample_rate))
        if not audible:
            chunks.extend(b"\x00\x00" * count)
            t_index += count
            continue
        samples = [
            int(amplitude * math.sin(2.0 * math.pi * freq * ((t_index + offset) / sample_rate)))
            for offset in range(count)
        ]
        chunks.extend(struct.pack(f"<{count}h", *samples))
        t_index += count
    return bytes(chunks)


class AudioIntegrityAnalysisTests(unittest.TestCase):
    def test_continuous_audio_is_complete(self):
        pcm = _make_pcm_segments([(25.0, True)])
        result = analyze_pcm_audio(pcm, total_duration_seconds=120.0)
        self.assertEqual(result.status, "complete")
        self.assertGreater(result.audible_ratio, 0.95)

    def test_intermittent_3s_on_7s_off_audio_is_detected(self):
        pcm = _make_pcm_segments([
            (3.0, True),
            (7.0, False),
            (3.0, True),
            (7.0, False),
            (3.0, True),
            (2.0, False),
        ])
        result = analyze_pcm_audio(pcm, total_duration_seconds=600.0)
        self.assertEqual(result.status, "intermittent")
        self.assertGreaterEqual(len(result.silent_gaps), 2)

    def test_intermittent_with_initial_long_silence_is_detected(self):
        pcm = _make_pcm_segments([
            (10.0, False),
            (4.0, True),
            (6.0, False),
            (5.0, True),
        ])
        result = analyze_pcm_audio(pcm, total_duration_seconds=5400.0)
        self.assertEqual(result.status, "intermittent")

    def test_short_14s_intermittent_audio_is_detected(self):
        pcm = _make_pcm_segments([
            (3.0, True),
            (7.0, False),
            (4.0, True),
        ])
        result = analyze_pcm_audio(pcm, total_duration_seconds=14.0)
        self.assertEqual(result.status, "intermittent")

    def test_normal_audio_with_silent_intro_stays_complete(self):
        short_intro = analyze_pcm_audio(_make_pcm_segments([(1.5, False), (23.5, True)]), total_duration_seconds=300.0)
        long_intro = analyze_pcm_audio(_make_pcm_segments([(6.0, False), (19.0, True)]), total_duration_seconds=300.0)
        self.assertEqual(short_intro.status, "complete")
        self.assertEqual(long_intro.status, "complete")

    def test_completely_silent_audio_is_silent(self):
        pcm = _make_pcm_segments([(25.0, False)])
        result = analyze_pcm_audio(pcm, total_duration_seconds=300.0)
        self.assertEqual(result.status, "silent")

    def test_empty_or_truncated_audio_is_unreadable(self):
        self.assertEqual(analyze_pcm_audio(b"", total_duration_seconds=300.0).status, "unreadable")
        short_pcm = _make_pcm_segments([(1.0, True)])
        self.assertEqual(analyze_pcm_audio(short_pcm, total_duration_seconds=300.0).status, "unreadable")

    def test_allowed_youtube_media_urls_and_cookie_domain_filtering(self):
        self.assertTrue(_is_allowed_youtube_media_url("https://rr4---sn-abc.c.youtube.com/videoplayback?id=1"))
        self.assertTrue(_is_allowed_youtube_media_url("https://rr1---sn-xyz.googlevideo.com/videoplayback"))
        self.assertFalse(_is_allowed_youtube_media_url("http://rr4---sn-abc.c.youtube.com/videoplayback"))
        self.assertFalse(_is_allowed_youtube_media_url("https://evil.example.com/video.mp4"))
        self.assertFalse(_is_allowed_youtube_media_url("file:///c:/test.mp4"))

        channel = SimpleNamespace(
            id="UC" + "a" * 22,
            cookies=[
                {"name": "SID", "value": "yt-sid", "domain": ".youtube.com"},
                {"name": "BAD", "value": "leak", "domain": ".evil.com"},
            ],
            studio_context={"client": {"userAgent": "CustomUA/1.0"}},
        )
        session, headers = _build_channel_media_session(channel)
        try:
            self.assertEqual(session.cookies.get("SID"), "yt-sid")
            self.assertIsNone(session.cookies.get("BAD"))
            self.assertEqual(headers["User-Agent"], "CustomUA/1.0")
        finally:
            session.close()

    def test_inspect_channel_videos_audio_handles_missing_url_and_sanitizes_errors(self):
        channel = SimpleNamespace(id="UC" + "a" * 22, cookies=[], studio_context={})
        videos = [
            SimpleNamespace(id="NoUrl______", video_stream_url="", duration_ms=60000),
            SimpleNamespace(id="Fail_______", video_stream_url="https://rr1.c.youtube.com/videoplayback", duration_ms=60000),
            SimpleNamespace(id="Good_______", video_stream_url="https://rr2.c.youtube.com/videoplayback", duration_ms=60000),
        ]
        good_pcm = _make_pcm_segments([(25.0, True)])

        def fake_decode(url, **_kwargs):
            if "rr1" in url:
                raise RuntimeError("secret-cookie-leak")
            return good_pcm

        with patch("src.audio_integrity.shutil.which", return_value="ffmpeg"), \
                patch("src.audio_integrity.get_channels_info", return_value=channel), \
                patch("src.audio_integrity.decode_audio_sample_from_stream", side_effect=fake_decode), \
                patch("src.audio_integrity.logger.warning") as log:
            results = inspect_channel_videos_audio(channel.id, videos)

        self.assertEqual(results["NoUrl______"].status, "unreadable")
        self.assertEqual(results["Fail_______"].status, "unreadable")
        self.assertEqual(results["Good_______"].status, "complete")
        self.assertNotIn("secret-cookie-leak", results["Fail_______"].reason)
        self.assertNotIn("secret-cookie-leak", str(log.call_args))


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg unavailable")
class AudioIntegrityStreamingTests(unittest.TestCase):
    def test_real_ffmpeg_streaming_classifies_continuous_and_gated_mp4(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            continuous = root / "continuous.mp4"
            intermittent = root / "intermittent.mp4"
            common_video = ["-f", "lavfi", "-i", "color=c=black:s=64x64:r=2:d=25"]
            common_audio = ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=25"]
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    *common_video, *common_audio,
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
                    str(continuous),
                ],
                check=True,
            )
            volume_expr = "if(lt(mod(t,10),3),1,if(gte(t,22),1,0))"
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    *common_video, *common_audio,
                    "-af", f"volume=volume='{volume_expr}':eval=frame",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
                    str(intermittent),
                ],
                check=True,
            )

            class QuietHandler(SimpleHTTPRequestHandler):
                def log_message(self, *args):
                    pass

            handler = partial(QuietHandler, directory=str(root))
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            session = requests.Session()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                pcm_ok = decode_audio_sample_from_stream(
                    f"{base}/continuous.mp4",
                    session=session,
                    headers={},
                    allow_local_http=True,
                )
                pcm_gated = decode_audio_sample_from_stream(
                    f"{base}/intermittent.mp4",
                    session=session,
                    headers={},
                    allow_local_http=True,
                )
                res_ok = analyze_pcm_audio(pcm_ok, total_duration_seconds=25.0)
                res_gated = analyze_pcm_audio(pcm_gated, total_duration_seconds=25.0)
                self.assertIsInstance(res_ok, AudioIntegrityResult)
                self.assertEqual(res_ok.status, "complete")
                self.assertEqual(res_gated.status, "intermittent")
            finally:
                session.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
