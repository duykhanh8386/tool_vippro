"""HTTP checks for the TV Automation upload shape, without running its EXE."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests

from src.module.audio_module import AudioUpdateError, UpdateAudioModule


class RecordingAdapter(requests.adapters.BaseAdapter):
    def __init__(self, callback):
        self.callback = callback

    def send(self, request, **kwargs):
        return self.callback(request)

    def close(self):
        pass


def response(headers=None, body=None):
    result = requests.Response()
    result.status_code = 200
    result.headers.update(headers or {})
    result._content = b"{}"
    if body is not None:
        result.json = lambda: body
    return result


class TvAudioUploadTests(unittest.TestCase):
    def test_file_is_one_finalize_request_with_exact_length_and_byte_progress(self):
        module = UpdateAudioModule()
        module._CHUNK_SIZE = 4
        progress, received, calls = {}, [], []

        def receive(request):
            calls.append(request)
            self.assertEqual(request.headers["Content-Length"], "10")
            self.assertNotIn("Transfer-Encoding", request.headers)
            self.assertEqual(request.headers["X-Goog-Upload-Command"], "upload, finalize")
            self.assertEqual(request.headers["X-Goog-Upload-Offset"], "0")
            while block := request.body.read(3):
                received.append(block)
                self.assertEqual(progress["sent"], len(b"".join(received)))
            return response({"X-Goog-Upload-Status": "final"})

        with tempfile.TemporaryDirectory() as folder, requests.Session() as session:
            path = Path(folder) / "song.mp3"
            path.write_bytes(b"abcdefghij")
            session.mount("https://", RecordingAdapter(receive))
            self.assertEqual(module._next_upload_http(
                "https://upload.example.test/session", "song.mp3", "cookie", file_path=str(path),
                progress=progress, session=session, single_request=True,
            ), "final")
        self.assertEqual(len(calls), 1)
        self.assertEqual(b"".join(received), b"abcdefghij")
        self.assertEqual(progress["status"], "complete")
        self.assertEqual(progress["confirmed"], 10)

    def test_single_request_timeout_resumes_remaining_bytes_with_correct_content_length(self):
        module = UpdateAudioModule()
        received, calls = [], []

        def receive(request):
            calls.append(request)
            if request.headers["X-Goog-Upload-Command"] == "query":
                return response({"X-Goog-Upload-Size-Received": "4", "X-Goog-Upload-Status": "active"})
            if len(calls) == 1:
                self.assertEqual(request.headers["Content-Length"], "10")
                self.assertEqual(request.body.read(4), b"abcd")
                raise requests.exceptions.Timeout("response lost")
            self.assertEqual(request.headers["X-Goog-Upload-Offset"], "4")
            self.assertEqual(request.headers["Content-Length"], "6")
            self.assertNotIn("Transfer-Encoding", request.headers)
            received.append(request.body.read())
            return response({"X-Goog-Upload-Status": "final"})

        with tempfile.TemporaryDirectory() as folder, requests.Session() as session:
            path = Path(folder) / "song.mp3"
            path.write_bytes(b"abcdefghij")
            session.mount("https://", RecordingAdapter(receive))
            with patch("src.module.audio_module.wait_interruptibly"):
                module._next_upload_http("https://upload.example.test/session", "song.mp3", "cookie",
                                         file_path=str(path), session=session, single_request=True)
        self.assertEqual(len(calls), 3)
        self.assertEqual(received, [b"efghij"])

    def test_empty_finalize_has_no_chunked_transfer_encoding(self):
        module = UpdateAudioModule()
        calls = []

        def receive(request):
            calls.append(request)
            self.assertNotIn("Transfer-Encoding", request.headers)
            if len(calls) == 1:
                self.assertEqual(request.body.read(), b"abc")
                return response({"X-Goog-Upload-Status": "active"})
            self.assertEqual(request.headers["Content-Length"], "0")
            self.assertEqual(request.headers["X-Goog-Upload-Offset"], "3")
            return response({"X-Goog-Upload-Status": "final"})

        with requests.Session() as session, patch("src.module.audio_module.wait_interruptibly"):
            session.mount("https://", RecordingAdapter(receive))
            module._next_upload_http("https://upload.example.test/session", "song.mp3", "cookie",
                                     data=b"abc", session=session, single_request=True)
        self.assertEqual(len(calls), 2)

    def test_audio_rpcs_keep_the_captured_serialized_channel_context(self):
        module = UpdateAudioModule()
        channel = SimpleNamespace(
            id="channel", role="OWNER", delegated_session_id="owner", cookies=[],
            studio_context={"user": {"delegationContext": {"externalChannelId": "channel"},
                                     "serializedDelegationContext": "captured-channel-context"}},
        )
        with (
            patch("src.module.audio_module.get_channels_info", return_value=channel),
            patch("src.module.audio_module.studio_authorization_header", return_value="test-auth"),
            patch.object(module, "_get_session_token", return_value="token"),
            patch("src.module.audio_module.post_with_stop", return_value=response(body={
                "videoTranslations": [{"videoId": "video", "translations": []}], "audioTracks": [],
            })) as post,
        ):
            module._update("video", "resource", channel, "cookie", "token", "en", audio_content_type="descriptive")
            module.delete_track_ids("video", "channel", ["failed-description"])
            module._get_video_translation_payload(["video"], "channel")
        self.assertEqual(post.call_count, 4)
        for call in post.call_args_list:
            self.assertEqual(call.kwargs["json"]["context"]["user"]["serializedDelegationContext"],
                             "captured-channel-context")

    def test_foreign_channel_context_stops_before_registering_audio(self):
        module = UpdateAudioModule()
        channel = SimpleNamespace(id="channel", role="OWNER", delegated_session_id="owner", cookies=[],
                                  studio_context={"user": {"delegationContext": {"externalChannelId": "other"},
                                                           "serializedDelegationContext": "other-context"}})
        with (
            patch("src.module.audio_module.studio_authorization_header", return_value="test-auth"),
            patch("src.module.audio_module.post_with_stop") as post,
        ):
            with self.assertRaises(AudioUpdateError):
                module._update("video", "resource", channel, "cookie", "token", "en", audio_content_type="descriptive")
        post.assert_not_called()

    def test_legacy_channel_context_is_preserved(self):
        channel = SimpleNamespace(id="channel", serialized_delegation_context="legacy-context")
        self.assertEqual(UpdateAudioModule._serialized_delegation_context(channel), "legacy-context")


if __name__ == "__main__":
    unittest.main()
