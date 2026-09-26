import unittest
import tempfile
from pathlib import Path
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
    def test_audio_upload_uses_sixteen_megabyte_chunks(self):
        self.assertEqual(UpdateAudioModule._CHUNK_SIZE, 16 * 1024 * 1024)

    def test_file_upload_streams_chunks_and_reports_progress(self):
        module = UpdateAudioModule()
        module._CHUNK_SIZE = 4
        progress = {}
        session = Mock()

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "audio.mp3"
            audio_path.write_bytes(b"abcdefghij")
            with patch(
                "src.module.audio_module.post_with_stop",
                return_value=Response(200),
            ) as post:
                result = module._next_upload_http(
                    "https://session",
                    "audio.mp3",
                    "cookie",
                    data=None,
                    file_path=str(audio_path),
                    progress=progress,
                    session=session,
                )

        self.assertEqual(result, "final")
        self.assertEqual(
            [call.kwargs["data"] for call in post.call_args_list],
            [b"abcd", b"efgh", b"ij"],
        )
        self.assertTrue(
            all(call.kwargs["session"] is session for call in post.call_args_list)
        )
        self.assertEqual(progress["sent"], 10)
        self.assertEqual(progress["total"], 10)
        self.assertEqual(progress["status"], "complete")

    def test_add_reuses_one_http_session_for_start_register_and_upload(self):
        module = UpdateAudioModule()
        channel = SimpleNamespace(cookies=[], sapisidhash="hash")
        session = Mock()
        session_context = Mock()
        session_context.__enter__ = Mock(return_value=session)
        session_context.__exit__ = Mock(return_value=False)

        with (
            patch("src.module.audio_module.get_channels_info", return_value=channel),
            patch.object(module, "_get_session_token", return_value="token"),
            patch("src.module.audio_module.requests.Session", return_value=session_context),
            patch.object(
                module,
                "_upload_http",
                return_value=("https://session", "resource"),
            ) as start,
            patch.object(module, "_update", return_value=200) as register,
            patch.object(module, "_next_upload_http", return_value="final") as upload,
        ):
            self.assertEqual(
                module.add(
                    "video",
                    "channel",
                    "audio.mp3",
                    "vi",
                    data=None,
                    upload_path="rendered.mp3",
                ),
                200,
            )

        self.assertIs(start.call_args.kwargs["session"], session)
        self.assertIs(register.call_args.kwargs["session"], session)
        self.assertIs(upload.call_args.kwargs["session"], session)
        self.assertIsNone(upload.call_args.kwargs["data"])
        self.assertEqual(upload.call_args.kwargs["file_path"], "rendered.mp3")

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

    def test_collects_only_languages_with_an_audio_track(self):
        module = UpdateAudioModule()
        items = [
            {"languageCode": "EN", "audioTranslation": {"audioTrackId": "one"}},
            {"translationLanguage": {"code": "vi"}, "audioTranslation": {"audioTrackId": "two"}},
            {"languageCode": "ja", "audioTranslation": {}},
        ]
        with patch.object(module, "_get_audio_translation_items", return_value=items):
            self.assertEqual(
                module.get_existing_audio_languages("video", "channel"),
                {"en", "vi"},
            )

    def test_audio_scan_selects_all_four_requested_studio_states(self):
        module = UpdateAudioModule()
        groups = [
            {
                "videoId": "failed-video",
                "translations": [
                    {
                        "languageCode": "en",
                        "audioTranslation": {
                            "audioTrackProcessingStatus": "AUDIO_TRACK_PROCESSING_STATUS_FAILED"
                        },
                    }
                ],
            },
            {
                "videoId": "ineligible-video",
                "translations": [
                    {
                        "languageCode": "fr",
                        "audioTranslation": {
                            "status": "AUDIO_TRACK_STATUS_INELIGIBLE"
                        },
                    }
                ],
            },
            {
                "videoId": "ready-video",
                "translations": [
                    {
                        "languageCode": "ja",
                        "audioTranslation": {
                            "audioTrackId": "track",
                            "status": "AUDIO_TRACK_STATUS_READY",
                            "errorCode": "AUDIO_TRACK_ERROR_NONE",
                        },
                    }
                ],
            },
            {
                "videoId": "processing-video",
                "translations": [
                    {
                        "languageCode": "de",
                        "audioTranslation": {
                            "audioTrackProcessingStatus": "AUDIO_TRACK_PROCESSING_STATUS_PROCESSING"
                        },
                    }
                ],
            },
            {
                "videoId": "deleted-video",
                "translations": [
                    {
                        "languageCode": "es",
                        "audioTranslation": {
                            "status": "AUDIO_TRACK_STATUS_DELETED"
                        },
                    }
                ],
            },
            {
                "videoId": "no-speech-video",
                "translations": [
                    {
                        "captionsTranslations": [
                            {
                                "status": "TRANSLATION_STATUS_PROCESSING",
                                "processingEta": {
                                    "status": "PROCESSING_ETA_STATUS_SPEECH_NOT_DETECTED"
                                },
                            }
                        ]
                    }
                ],
            },
        ]
        with patch.object(module, "_get_video_translation_groups", return_value=groups) as fetch:
            failed = module.get_failed_audio_video_ids(
                [
                    "failed-video",
                    "ineligible-video",
                    "ready-video",
                    "processing-video",
                    "deleted-video",
                    "no-speech-video",
                ],
                "channel",
            )

        self.assertEqual(
            failed,
            {
                "failed-video",
                "ineligible-video",
                "processing-video",
                "deleted-video",
                "no-speech-video",
            },
        )
        fetch.assert_called_once_with(
            [
                "failed-video",
                "ineligible-video",
                "ready-video",
                "processing-video",
                "deleted-video",
                "no-speech-video",
            ],
            "channel",
        )

    def test_processing_enum_namespace_does_not_select_completed_audio(self):
        module = UpdateAudioModule()

        self.assertFalse(
            module._audio_translation_needs_attention(
                {
                    "audioTranslation": {
                        "audioTrackProcessingStatus": "AUDIO_TRACK_PROCESSING_STATUS_COMPLETED"
                    }
                }
            )
        )

    def test_failed_audio_scan_recognizes_nested_error_reason(self):
        module = UpdateAudioModule()
        item = {
            "title": "A failed experiment",
            "audioTranslation": {
                "processingError": {"reasonCode": "MEDIA_COULD_NOT_PROCESS"}
            },
        }

        self.assertTrue(module._audio_translation_has_processing_failure(item))

    def test_failed_word_outside_audio_status_is_ignored(self):
        module = UpdateAudioModule()
        item = {
            "title": "Failed sleep music",
            "audioTranslation": {"status": "AUDIO_TRACK_STATUS_READY"},
        }

        self.assertFalse(module._audio_translation_has_processing_failure(item))

    def test_failed_audio_scan_splits_precondition_batch_and_reports_unreadable(self):
        module = UpdateAudioModule()

        def fetch(video_ids, _channel):
            if len(video_ids) > 1:
                raise AudioUpdateError("Precondition check failed", status_code=400)
            if video_ids[0] == "unreadable":
                raise AudioUpdateError("Precondition check failed", status_code=400)
            return [
                {
                    "videoId": video_ids[0],
                    "translations": [
                        {
                            "audioTranslation": {
                                "status": "AUDIO_TRACK_PROCESSING_STATUS_FAILED"
                            }
                        }
                    ],
                }
            ]

        unreadable = []
        with patch.object(module, "_get_video_translation_groups", side_effect=fetch):
            failed = module.get_failed_audio_video_ids(
                ["failed", "unreadable"], "channel", unreadable
            )

        self.assertEqual(failed, {"failed"})
        self.assertEqual(unreadable, ["unreadable"])


class AudioDeleteTests(unittest.TestCase):
    def _channel(self):
        return SimpleNamespace(
            cookies=[],
            sapisidhash="hash",
            id="channel",
            delegated_session_id="delegated",
            role="OWNER",
        )

    def test_delete_returns_only_after_all_tracks_succeed(self):
        module = UpdateAudioModule()
        with (
            patch("src.module.audio_module.get_channels_info", return_value=self._channel()),
            patch.object(module, "_get_session_token", return_value="token"),
            patch.object(module, "_get_all_audio_track_ids", return_value=["a", "b"]),
            patch("src.module.audio_module.post_with_stop", return_value=Response(200)) as post,
        ):
            self.assertEqual(module.delete("video", "channel"), 200)
        self.assertEqual(post.call_count, 2)

    def test_delete_propagates_youtube_failure(self):
        module = UpdateAudioModule()
        with (
            patch("src.module.audio_module.get_channels_info", return_value=self._channel()),
            patch.object(module, "_get_session_token", return_value="token"),
            patch.object(module, "_get_all_audio_track_ids", return_value=["a"]),
            patch("src.module.audio_module.post_with_stop", return_value=Response(503)),
        ):
            with self.assertRaises(AudioUpdateError) as raised:
                module.delete("video", "channel")
        self.assertEqual(raised.exception.status_code, 503)
        self.assertTrue(raised.exception.retryable)


if __name__ == "__main__":
    unittest.main()
