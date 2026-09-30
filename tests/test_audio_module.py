import unittest
import tempfile
from concurrent.futures import ThreadPoolExecutor
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

    def test_parallel_workers_share_short_lived_session_token(self):
        module = UpdateAudioModule()
        channel = SimpleNamespace(
            id="cache-test-channel",
            role="CREATOR_CHANNEL_ROLE_TYPE_OWNER",
            delegated_session_id="delegated",
            challenge="challenge",
            botguardResponse="botguard",
            sapisidhash="hash",
            cookie_string=lambda: "cookie=value",
        )
        cache_key = module._session_token_cache_key(channel)
        with module._SESSION_TOKEN_CACHE_LOCK:
            module._SESSION_TOKEN_CACHE.pop(cache_key, None)
            module._SESSION_TOKEN_FETCH_LOCKS.pop(cache_key, None)

        def fake_post(url, **_kwargs):
            if "/att/esr" in url:
                return Response(200, body={"ctx": "attestation"})
            if "get_web_reauth_url" in url:
                return Response(
                    200,
                    body={
                        "encodedReauthProofToken": "proof",
                        "sessionRiskCtx": "risk",
                    },
                )
            if "/ars/grst" in url:
                return Response(200, body={"sessionToken": "shared-token"})
            raise AssertionError(url)

        try:
            with patch(
                "src.module.base.post_with_stop", side_effect=fake_post
            ) as post:
                with ThreadPoolExecutor(max_workers=5) as executor:
                    tokens = list(
                        executor.map(
                            lambda _index: module._get_session_token(channel),
                            range(5),
                        )
                    )
            self.assertEqual(tokens, ["shared-token"] * 5)
            self.assertEqual(post.call_count, 3)
        finally:
            with module._SESSION_TOKEN_CACHE_LOCK:
                module._SESSION_TOKEN_CACHE.pop(cache_key, None)
                module._SESSION_TOKEN_FETCH_LOCKS.pop(cache_key, None)

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

    def test_translation_request_matches_studio_audio_table_request(self):
        module = UpdateAudioModule()
        channel = SimpleNamespace(
            cookies=[],
            sapisidhash="hash",
            id="channel",
            delegated_session_id="delegated",
            role="OWNER",
        )
        with (
            patch("src.module.audio_module.get_channels_info", return_value=channel),
            patch.object(module, "_get_session_token", return_value="token"),
            patch(
                "src.module.audio_module.post_with_stop",
                return_value=Response(200, body={"videoTranslations": []}),
            ) as post,
        ):
            module._get_video_translation_payload(["video"], "channel")

        payload = post.call_args.kwargs["json"]
        self.assertFalse(payload["fetchAloudData"])
        self.assertFalse(payload["fetchAutoDubbingData"])
        self.assertFalse(payload["fetchAutoDubbingAsrData"])
        self.assertFalse(payload["fetchBulkActionsStatus"])
        self.assertFalse(payload["fetchDataFromInternalService"])
        self.assertEqual(
            payload["filters"],
            ["TRANSLATION_FILTER_DRAFT", "TRANSLATION_FILTER_PUBLISHED"],
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
                            "audioTrackId": "track-ineligible",
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
                        "audioTranslation": {
                            "processingError": {
                                "reasonCode": "SPEECH_NOT_DETECTED"
                            }
                        }
                    }
                ],
            },
        ]
        with patch.object(
            module,
            "_get_video_translation_payload",
            return_value={"videoTranslations": groups, "audioTracks": []},
        ) as fetch:
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

    def test_audio_scan_uses_root_audio_tracks_status_from_real_studio_shape(self):
        module = UpdateAudioModule()
        payload = {
            "videoTranslations": [
                {
                    "videoId": "failed-video",
                    "translations": [
                        {
                            "languageCode": "en",
                            "audioTranslation": {
                                "videoId": "failed-video",
                                "audioTrackId": "track-failed",
                            },
                        }
                    ],
                    "status": "VIDEO_TRANSLATIONS_STATUS_OK",
                },
                {
                    "videoId": "ready-video",
                    "translations": [
                        {
                            "languageCode": "es",
                            "audioTranslation": {
                                "videoId": "ready-video",
                                "audioTrackId": "track-ready",
                            },
                        }
                    ],
                    "status": "VIDEO_TRANSLATIONS_STATUS_OK",
                },
            ],
            "audioTracks": [
                {
                    "videoId": "failed-video",
                    "audioTrackId": "track-failed",
                    "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed",
                    "status": "AUDIO_TRACK_STATUS_FAILED",
                    "rejectedReason": "AUDIO_TRACK_REJECTED_REASON_CLAIM_COMPATIBILITY_MISMATCH",
                },
                {
                    "videoId": "ready-video",
                    "audioTrackId": "track-ready",
                    "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed",
                    "status": "AUDIO_TRACK_STATUS_READY",
                },
            ],
        }

        with patch.object(
            module, "_get_video_translation_payload", return_value=payload
        ):
            selected = module.get_audio_attention_video_ids(
                ["failed-video", "ready-video"], "channel"
            )

        self.assertEqual(selected, {"failed-video"})

    def test_source_audio_black_ineligible_lock_is_not_selected(self):
        module = UpdateAudioModule()
        payload = {
            "videoTranslations": [
                {
                    "videoId": "healthy-video",
                    "translations": [
                        {
                            "languageCode": "pcm",
                            "audioTranslation": {
                                "audioTrackId": "source-original",
                                "status": "AUDIO_TRACK_STATUS_INELIGIBLE",
                            },
                        },
                        {
                            "languageCode": "en",
                            "audioTranslation": {
                                "videoId": "healthy-video",
                                "audioTrackId": "creator-ready",
                            },
                        },
                    ],
                }
            ],
            "audioTracks": [
                {
                    "videoId": "healthy-video",
                    "audioTrackId": "source-original",
                    "source": "AUDIO_TRACK_SOURCE_UPLOAD",
                    "audioContentTypeString": "original",
                    "status": "AUDIO_TRACK_STATUS_INELIGIBLE",
                },
                {
                    "videoId": "healthy-video",
                    "audioTrackId": "creator-ready",
                    "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed",
                    "status": "AUDIO_TRACK_STATUS_READY",
                },
            ],
        }

        with patch.object(
            module, "_get_video_translation_payload", return_value=payload
        ):
            selected = module.get_audio_attention_video_ids(
                ["healthy-video"], "channel"
            )

        self.assertEqual(selected, set())

    def test_red_creator_dub_ineligible_is_selected(self):
        module = UpdateAudioModule()
        payload = {
            "videoTranslations": [],
            "audioTracks": [
                {
                    "videoId": "rejected-video",
                    "audioTrackId": "creator-failed",
                    "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed",
                    "status": "AUDIO_TRACK_STATUS_FAILED",
                    "rejectedReason": (
                        "AUDIO_TRACK_REJECTED_REASON_CLAIM_COMPATIBILITY_MISMATCH"
                    ),
                }
            ],
        }

        with patch.object(
            module, "_get_video_translation_payload", return_value=payload
        ):
            selected = module.get_audio_attention_video_ids(
                ["rejected-video"], "channel"
            )

        self.assertEqual(selected, {"rejected-video"})

    def test_source_black_lock_does_not_hide_another_failed_creator_dub(self):
        module = UpdateAudioModule()
        payload = {
            "videoTranslations": [
                {
                    "videoId": "mixed-video",
                    "translations": [
                        {
                            "languageCode": "pcm",
                            "audioTranslation": {
                                "videoId": "mixed-video",
                                "audioTrackId": "source-original",
                                "status": "AUDIO_TRACK_STATUS_INELIGIBLE",
                            },
                        },
                        {
                            "languageCode": "es",
                            "audioTranslation": {
                                "videoId": "mixed-video",
                                "audioTrackId": "failed-es",
                            },
                        },
                    ],
                }
            ],
            "audioTracks": [
                {
                    "videoId": "mixed-video",
                    "audioTrackId": "source-original",
                    "language": "pcm",
                    "source": "AUDIO_TRACK_SOURCE_UPLOAD",
                    "audioContentTypeString": "original",
                    "status": "AUDIO_TRACK_STATUS_INELIGIBLE",
                },
                {
                    "videoId": "mixed-video",
                    "audioTrackId": "failed-es",
                    "language": "es",
                    "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed",
                    "status": "AUDIO_TRACK_STATUS_FAILED",
                },
            ],
        }

        with patch.object(
            module, "_get_video_translation_payload", return_value=payload
        ):
            selected = module.get_audio_attention_video_ids(
                ["mixed-video"], "channel"
            )

        self.assertEqual(selected, {"mixed-video"})

    def test_trackless_translation_ineligible_is_source_row_and_is_ignored(self):
        module = UpdateAudioModule()

        self.assertFalse(
            module._audio_translation_needs_attention(
                {
                    "languageCode": "pcm",
                    "audioTranslation": {
                        "status": "AUDIO_TRACK_STATUS_INELIGIBLE"
                    },
                }
            )
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

    def test_group_level_auto_dubbing_eligibility_without_audio_rows_is_ignored(self):
        module = UpdateAudioModule()
        groups = [
            {
                "videoId": "caption-editor-only",
                "translations": [
                    {
                        "languageCode": "en",
                        "captionsTranslations": [
                            {
                                "status": "TRANSLATION_STATUS_PROCESSING",
                                "processingEta": {
                                    "status": "PROCESSING_ETA_STATUS_SPEECH_NOT_DETECTED"
                                },
                            }
                        ],
                    }
                ],
                "autoDubbingData": {
                    "languageDubbings": [
                        {
                            "languageCode": "en",
                            "availabilityStatus": "DUBBING_AVAILABILITY_STATUS_INELIGIBLE",
                        }
                    ]
                },
            }
        ]

        with patch.object(
            module,
            "_get_video_translation_payload",
            return_value={"videoTranslations": groups, "audioTracks": []},
        ):
            selected = module.get_audio_attention_video_ids(
                ["caption-editor-only"], "channel"
            )

        self.assertEqual(selected, set())

    def test_translation_row_auto_dubbing_status_is_selected(self):
        module = UpdateAudioModule()
        groups = [
            {
                "videoId": "auto-dub-failed",
                "translations": [
                    {
                        "languageCode": "es",
                        "autoDubbingData": {
                            "status": "AUTO_DUBBING_STATUS_FAILED"
                        },
                    }
                ],
            }
        ]

        with patch.object(
            module,
            "_get_video_translation_payload",
            return_value={"videoTranslations": groups, "audioTracks": []},
        ):
            selected = module.get_audio_attention_video_ids(
                ["auto-dub-failed"], "channel"
            )

        self.assertEqual(selected, {"auto-dub-failed"})

    def test_audio_scan_recognizes_localized_audio_status_labels(self):
        module = UpdateAudioModule()

        for label in (
            "Đang xử lý",
            "Không xử lý được",
            "Không đủ điều kiện",
            "Đã xoá",
        ):
            with self.subTest(label=label):
                self.assertTrue(
                    module._audio_payload_needs_attention(
                        {"autoDubbingData": {"statusLabel": label}}
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
            return {
                "videoTranslations": [
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
                ],
                "audioTracks": [],
            }

        unreadable = []
        with patch.object(module, "_get_video_translation_payload", side_effect=fetch):
            failed = module.get_failed_audio_video_ids(
                ["failed", "unreadable"], "channel", unreadable
            )

        self.assertEqual(failed, {"failed"})
        self.assertEqual(unreadable, ["unreadable"])

    def test_partial_success_response_retries_missing_videos_individually(self):
        module = UpdateAudioModule()

        def fetch(video_ids, _channel):
            if len(video_ids) > 1:
                return {
                    "videoTranslations": [
                        {
                            "videoId": "clean",
                            "translations": [
                                {
                                    "audioTranslation": {
                                        "status": "AUDIO_TRACK_STATUS_READY"
                                    }
                                }
                            ],
                        }
                    ],
                    "audioTracks": [],
                }
            if video_ids == ["failed"]:
                return {
                    "videoTranslations": [
                        {
                            "videoId": "failed",
                            "translations": [
                                {
                                    "autoDubbingData": {
                                        "status": "AUTO_DUBBING_STATUS_FAILED"
                                    }
                                }
                            ],
                        }
                    ],
                    "audioTracks": [],
                }
            return {"videoTranslations": [], "audioTracks": []}

        unreadable = []
        with patch.object(
            module, "_get_video_translation_payload", side_effect=fetch
        ) as request:
            selected = module.get_audio_attention_video_ids(
                ["clean", "failed", "missing"], "channel", unreadable
            )

        self.assertEqual(selected, {"failed"})
        self.assertEqual(unreadable, ["missing"])
        self.assertEqual(
            [call.args[0] for call in request.call_args_list],
            [["clean", "failed", "missing"], ["failed"], ["missing"]],
        )

    def test_terminal_repair_scan_returns_only_exact_failed_language(self):
        module = UpdateAudioModule()
        payload = {
            "videoTranslations": [
                {
                    "videoId": "video",
                    "translations": [
                        {
                            "languageCode": "en",
                            "audioTranslation": {
                                "audioTrackId": "ready-en",
                                "status": "AUDIO_TRACK_STATUS_READY",
                            },
                        },
                        {
                            "languageCode": "es",
                            "audioTranslation": {"audioTrackId": "failed-es"},
                        },
                        {
                            "languageCode": "de",
                            "audioTranslation": {
                                "audioTrackId": "processing-de",
                                "status": "AUDIO_TRACK_STATUS_PROCESSING",
                            },
                        },
                        {
                            "languageCode": "pt-PT",
                            "audioTranslation": {
                                "audioTrackId": "published-pt",
                                "publishStatus": "PUBLISHED",
                            },
                        },
                    ],
                }
            ],
            "audioTracks": [
                {
                    "videoId": "video",
                    "audioTrackId": "ready-en",
                    "language": "en",
                    "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed",
                    "status": "AUDIO_TRACK_STATUS_READY",
                },
                {
                    "videoId": "video",
                    "audioTrackId": "failed-es",
                    # Real responses can require the translation row to supply
                    # the language for a root audioTracks item.
                    "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed",
                    "status": "AUDIO_TRACK_STATUS_FAILED",
                },
                {
                    "videoId": "video",
                    "audioTrackId": "processing-de",
                    "language": "de",
                    "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed",
                    "status": "AUDIO_TRACK_STATUS_PROCESSING",
                },
            ],
        }

        with patch.object(
            module, "_get_video_translation_payload", return_value=payload
        ):
            targets = module.get_terminal_audio_repair_targets(
                ["video"], "channel"
            )

        self.assertEqual(
            targets,
            {
                "video": [
                    {
                        "language": "es",
                        "track_ids": ["failed-es"],
                        "reason": "terminal",
                    }
                ]
            },
        )

    def test_terminal_repair_scan_ignores_processing_and_published_rows(self):
        module = UpdateAudioModule()
        payload = {
            "videoTranslations": [
                {
                    "videoId": "video",
                    "translations": [
                        {
                            "languageCode": "fr",
                            "audioTranslation": {
                                "audioTrackId": "published-fr",
                                "statusLabel": "Đã xuất bản",
                            },
                        },
                        {
                            "languageCode": "it",
                            "audioTranslation": {
                                "audioTrackId": "processing-it",
                                "statusLabel": "Đang xử lý... 95%",
                            },
                        },
                    ],
                }
            ],
            "audioTracks": [],
        }

        with patch.object(
            module, "_get_video_translation_payload", return_value=payload
        ):
            targets = module.get_terminal_audio_repair_targets(
                ["video"], "channel"
            )

        self.assertEqual(targets, {})


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

    def test_delete_track_ids_does_not_discover_or_delete_healthy_tracks(self):
        module = UpdateAudioModule()
        with (
            patch("src.module.audio_module.get_channels_info", return_value=self._channel()),
            patch.object(module, "_get_session_token", return_value="token"),
            patch.object(module, "_get_all_audio_track_ids") as discover,
            patch("src.module.audio_module.post_with_stop", return_value=Response(200)) as post,
        ):
            self.assertEqual(
                module.delete_track_ids("video", "channel", ["failed-track"]),
                200,
            )

        discover.assert_not_called()
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["json"]["audioTrackId"], "failed-track")

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
