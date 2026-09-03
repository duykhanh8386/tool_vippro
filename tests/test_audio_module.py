import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from src.module.audio_module import AudioUpdateError, UpdateAudioModule


class Response:
    def __init__(self, status_code=200, headers=None, body=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = ""
        self._body = body or {}

    def json(self):
        return self._body


class AudioUploadTests(unittest.TestCase):
    def test_timeout_queries_offset_and_resumes_same_session(self):
        module = UpdateAudioModule()
        data = b"x" * (10 * 1024 * 1024)
        calls = []
        first_upload = True

        def fake_post(url, **kwargs):
            nonlocal first_upload
            calls.append((url, kwargs))
            command = kwargs["headers"]["X-Goog-Upload-Command"]
            if command == "query":
                return Response(headers={"X-Goog-Upload-Size-Received": str(4 * 1024 * 1024)})
            if first_upload:
                first_upload = False
                raise requests.exceptions.Timeout("write timed out")
            return Response()

        with (
            patch("src.module.audio_module.post_with_stop", side_effect=fake_post),
            patch("src.module.audio_module.wait_interruptibly"),
        ):
            self.assertEqual(
                module._next_upload_http("https://same-session", "audio.mp3", "cookie", data),
                "final",
            )

        self.assertTrue(all(url == "https://same-session" for url, _ in calls))
        upload_calls = [kw for _, kw in calls if kw["headers"]["X-Goog-Upload-Command"] != "query"]
        self.assertEqual(upload_calls[1]["headers"]["X-Goog-Upload-Offset"], str(4 * 1024 * 1024))
        self.assertEqual(upload_calls[1]["timeout"], (30, 900))

    def test_non_retryable_upload_error_stops_immediately(self):
        module = UpdateAudioModule()
        with patch("src.module.audio_module.post_with_stop", return_value=Response(403)) as post:
            with self.assertRaises(AudioUpdateError) as raised:
                module._next_upload_http("https://session", "audio.mp3", "cookie", b"abc")
        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(post.call_count, 1)

    def test_verified_409_skips_byte_upload(self):
        module = UpdateAudioModule()
        channel = SimpleNamespace(cookies=[], sapisidhash="hash")
        with (
            patch("src.module.audio_module.get_channels_info", return_value=channel),
            patch.object(module, "_get_session_token", return_value="token"),
            patch.object(module, "_upload_http", return_value=("https://session", "resource")),
            patch.object(module, "_update", return_value=409),
            patch.object(module, "_has_audio_track", return_value=True),
            patch.object(module, "_next_upload_http") as upload,
        ):
            status = module.add("video", "channel", "audio.mp3", "pt", b"abc")
        self.assertEqual(status, 409)
        upload.assert_not_called()

    def test_unverified_409_is_not_success(self):
        module = UpdateAudioModule()
        channel = SimpleNamespace(cookies=[], sapisidhash="hash")
        with (
            patch("src.module.audio_module.get_channels_info", return_value=channel),
            patch.object(module, "_get_session_token", return_value="token"),
            patch.object(module, "_upload_http", return_value=("https://session", "resource")),
            patch.object(module, "_update", return_value=409),
            patch.object(module, "_has_audio_track", return_value=False),
            patch.object(module, "_next_upload_http") as upload,
        ):
            with self.assertRaises(AudioUpdateError) as raised:
                module.add("video", "channel", "audio.mp3", "pt", b"abc")
        self.assertEqual(raised.exception.status_code, 409)
        upload.assert_not_called()

    def test_extracts_language_from_translation_response(self):
        module = UpdateAudioModule()
        self.assertEqual(
            module._translation_language(
                {
                    "translationLanguage": {"languageCode": "nl-BE"},
                    "audioTranslation": {"audioTrackId": "track"},
                }
            ),
            "nl-BE",
        )


if __name__ == "__main__":
    unittest.main()
