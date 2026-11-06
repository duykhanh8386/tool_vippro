import copy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import requests

from src import audio_recovery as recovery
from src.module.audio_module import AudioUpdateError, UpdateAudioModule
from web.components.drawer import _recovery_studio_text, _recovery_transfer_text
from test_audio_upload_confirmation import track
from test_tv_audio_upload import RecordingAdapter, response


class UploadWatchdogTests(unittest.TestCase):
    def run_transfer(self, kind, observed, *, wrapped_error=False, data_bytes=False):
        module = UpdateAudioModule()
        clock = [100.0]
        progress, received, calls = {}, bytearray(), []
        initial = {"videoTranslations": [{"videoId": "video", "translations": []}], "audioTracks": []}
        live = {**initial, "audioTracks": observed}
        self.final_progress, self.received, self.calls = progress, received, calls

        def fetch(*_):
            return copy.deepcopy(initial if len(calls) < 2 else live)

        def send(request):
            calls.append(request)
            if len(calls) == 1:
                return response({"X-Goog-Upload-Status": "active", "X-Goog-Upload-URL": "https://upload.youtube.com/session",
                                 "X-Goog-Upload-Header-Scotty-Resource-Id": "resource"})
            if len(calls) == 2:
                return response(body={"videoId": "video", "audioTrackId": "ours"})
            received.extend(request.body.read(3))
            clock[0] = 106.0
            try:
                received.extend(request.body.read())
            except AudioUpdateError as exc:
                if wrapped_error:
                    raise requests.exceptions.ConnectionError("body reader failed") from exc
                raise
            return response({"X-Goog-Upload-Status": "final"})

        channel = SimpleNamespace(id="channel", role="OWNER", delegated_session_id="owner", cookies=[])
        with tempfile.TemporaryDirectory() as folder, requests.Session() as session:
            path = Path(folder) / "music.mp3"
            path.write_bytes(b"abcdefghij")
            session.mount("https://", RecordingAdapter(send))
            with (
                patch("src.module.audio_module.requests.Session", return_value=session),
                patch("src.module.audio_module.get_channels_info", return_value=channel),
                patch("src.module.audio_module.studio_authorization_header", return_value="test-auth"),
                patch("src.module.audio_module.time.monotonic", side_effect=lambda: clock[0]),
                patch.object(module, "_get_session_token", return_value="token"),
                patch.object(module, "_get_video_translation_payload", side_effect=fetch),
                patch("src.module.audio_module.wait_interruptibly") as wait,
            ):
                try:
                    return module.add("video", "channel", str(path), "en", progress=progress, audio_content_type=kind,
                                      data=path.read_bytes() if data_bytes else None)
                finally:
                    wait.assert_not_called()

    def test_server_failure_is_reported_only_after_file_finalization(self):
        for kind in ("dubbed", "descriptive"):
            for wrapped in (False, True):
                for data_bytes in (False, True):
                    with self.subTest(kind=kind, wrapped=wrapped, data_bytes=data_bytes):
                        with self.assertRaisesRegex(AudioUpdateError, "AUDIO_TRACK_STATUS_FAILED"):
                            self.run_transfer(kind, [track(kind, "FAILED", "ours")], wrapped_error=wrapped, data_bytes=data_bytes)
                        self.assertEqual(bytes(self.received), b"abcdefghij")
                        self.assertEqual(len(self.calls), 3)
                        self.assertTrue(self.final_progress["registered"])
                        self.assertTrue(self.final_progress["server_rejected"])
                        self.assertTrue(self.final_progress["file_finalized"])
                        self.assertEqual(self.final_progress["track_id"], "ours")
                        self.assertEqual(self.final_progress["studio_state"], "failed")
                        self.assertEqual(self.final_progress["status"], "error")

    def test_other_failed_track_does_not_abort_our_pending_upload(self):
        self.assertEqual(self.run_transfer("descriptive", [track(track_id="ours"), track(status="FAILED", track_id="other")]), 200)
        self.assertEqual(bytes(self.received), b"abcdefghij")
        self.assertEqual(self.final_progress["track_id"], "ours")
        self.assertEqual(self.final_progress["studio_state"], "processing")



    def test_verification_cannot_accept_a_different_new_track(self):
        module = UpdateAudioModule()
        with patch.object(module, "_audio_upload_snapshot", return_value={"other": track(track_id="other")}), patch(
            "src.module.audio_module.wait_interruptibly",
        ):
            with self.assertRaises(AudioUpdateError):
                module._verify_audio_upload("video", "channel", "en", "descriptive", {}, progress={"track_id": "ours"})

    def test_registration_for_a_different_video_is_rejected(self):
        module = UpdateAudioModule()
        channel = SimpleNamespace(id="channel", role="OWNER", delegated_session_id="owner", cookies=[])
        with patch("src.module.audio_module.post_with_stop", return_value=response(body={"videoId": "other", "audioTrackId": "foreign"})), patch(
            "src.module.audio_module.studio_authorization_header", return_value="auth",
        ):
            with self.assertRaises(AudioUpdateError):
                module._update("video", "resource", channel, "cookie", "token", "en", progress={})

    def test_registry_shows_server_failure_separately_from_sent_bytes(self):
        job = recovery._with_upload_progress({"phase": "uploading", "_upload_progress": {
            "sent": 52, "total": 100, "status": "error", "studio_state": "failed",
            "track_id": "ours", "track_status": "AUDIO_TRACK_STATUS_FAILED", "studio_checked_at": 123,
        }})
        self.assertEqual(job["upload_track_id"], "ours")
        self.assertEqual(job["upload_studio_checked_at"], 123)
        self.assertIn("không xử lý được", _recovery_transfer_text(job))
        self.assertEqual(_recovery_studio_text(job), "Không xử lý được")
        self.assertEqual(_recovery_studio_text({**job, "upload_studio_state": ""}), "Chưa xác nhận trạng thái")


if __name__ == "__main__":
    unittest.main()
