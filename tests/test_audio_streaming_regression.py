"""The Studio status API must never interrupt an HTTP upload body read."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests

from io import BytesIO

from src.module.audio_module import AudioUpdateError, UpdateAudioModule, _AudioUploadBody, _AudioUploadFile
from src.task_runtime import TaskStopped
from test_audio_upload_confirmation import track
from test_tv_audio_upload import RecordingAdapter, response


class AudioStreamingRegressionTests(unittest.TestCase):
    def upload(self, kind, *, interim="PENDING", final="PENDING"):
        module = UpdateAudioModule()
        clock = [100.0]
        received = bytearray()
        self.body_polls = 0
        self.progress = {}
        self.calls = []
        reading = False
        registered = False
        finalized = False
        channel = SimpleNamespace(id="channel", role="OWNER", delegated_session_id="owner", cookies=[])

        def snapshot(*_args):
            if reading:
                self.body_polls += 1
            if not registered:
                return {}
            return {"ours": track(kind, final if finalized else interim, "ours")}

        def send(request):
            nonlocal reading, registered, finalized
            self.calls.append(request)
            if len(self.calls) == 1:
                return response({"X-Goog-Upload-Status": "active", "X-Goog-Upload-URL": "https://upload.youtube.com/session",
                                 "X-Goog-Upload-Header-Scotty-Resource-Id": "resource"})
            if len(self.calls) == 2:
                registered = True
                return response(body={"videoId": "video", "audioTrackId": "ours"})
            reading = True
            try:
                received.extend(request.body.read(3))
                clock[0] = 106.0
                received.extend(request.body.read())
            finally:
                reading = False
            finalized = True
            return response({"X-Goog-Upload-Status": "final"})

        self.received = received
        with tempfile.TemporaryDirectory() as folder, requests.Session() as session:
            music = Path(folder) / "music.mp3"
            music.write_bytes(b"abcdefghij")
            session.mount("https://", RecordingAdapter(send))
            with (
                patch("src.module.audio_module.requests.Session", return_value=session),
                patch("src.module.audio_module.get_channels_info", return_value=channel),
                patch("src.module.audio_module.studio_authorization_header", return_value="test-auth"),
                patch("src.module.audio_module.time.monotonic", side_effect=lambda: clock[0]),
                patch.object(module, "_get_session_token", return_value="token"),
                patch.object(module, "_audio_upload_snapshot", side_effect=snapshot),
                patch("src.module.audio_module.wait_interruptibly"),
            ):
                return module.add("video", "channel", str(music), "en", progress=self.progress, audio_content_type=kind)

    def test_status_requests_do_not_block_sending_file_bytes(self):
        for kind in ("dubbed", "descriptive"):
            with self.subTest(kind=kind):
                self.assertEqual(self.upload(kind), 200)
                self.assertEqual(self.body_polls, 0)
                self.assertEqual(bytes(self.received), b"abcdefghij")

    def test_unfinalized_track_status_does_not_abort_the_file(self):
        for kind in ("dubbed", "descriptive"):
            with self.subTest(kind=kind):
                self.assertEqual(self.upload(kind, interim="FAILED", final="PROCESSED"), 200)
                self.assertEqual(bytes(self.received), b"abcdefghij")
                self.assertTrue(self.progress["file_finalized"])
                self.assertEqual(self.progress["studio_state"], "published")

    def test_real_failure_after_finalization_still_fails(self):
        for kind in ("dubbed", "descriptive"):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(AudioUpdateError, "AUDIO_TRACK_STATUS_FAILED"):
                    self.upload(kind, final="FAILED")
                self.assertEqual(bytes(self.received), b"abcdefghij")
                self.assertTrue(self.progress["file_finalized"])
                self.assertTrue(self.progress["server_rejected"])

    def test_cancellation_still_stops_each_body_read_without_studio_polling(self):
        for body in (_AudioUploadBody(b"audio", 0, None), _AudioUploadFile(BytesIO(b"audio"), 5, None)):
            with self.subTest(body=type(body)), patch("src.module.audio_module.check_stopped", side_effect=TaskStopped()):
                with self.assertRaises(TaskStopped):
                    body.read(1)
