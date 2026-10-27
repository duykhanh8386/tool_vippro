import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from src.audio_recovery import (
    DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS,
    DEFAULT_RECOVERY_INTERVAL_SECONDS,
    DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS,
    DEFAULT_STALE_PROCESSING_SECONDS,
    MONITOR_IDLE_POLL_SECONDS,
    PROCESSING_WARNING_REASON,
    RECOVERY_SCAN_MODE_ALL,
    RECOVERY_SCAN_MODE_SELECTED,
    RECOVERY_VIDEO_SCOPE_BOTH,
    RECOVERY_VIDEO_SCOPE_PUBLIC,
    RECOVERY_VIDEO_SCOPE_SCHEDULED,
    _get_registered_video_scan_statuses,
    _monitor_failed_caption_tracks,
    _monitor_loop,
    _record_processing_observations,
    acknowledge_channel_refresh,
    build_audio_recovery_plan,
    clear_audio_recovery_registry,
    get_audio_recovery_runtime_status,
    get_audio_recovery_scan_preferences,
    get_channel_refresh_alerts,
    get_audio_mutation_guard,
    import_add_audio_flow_recovery_state,
    mark_channel_refresh_required,
    register_audio_recovery,
    register_caption_monitor,
    run_audio_recovery_cycle,
    set_audio_recovery_scan_preferences,
)


class AudioRecoveryPlanTests(unittest.TestCase):
    def test_default_monitor_scans_and_repairs_without_time_delays(self):
        self.assertEqual(DEFAULT_RECOVERY_INTERVAL_SECONDS, 0)
        self.assertEqual(DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS, 0)
        self.assertEqual(DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS, 0)
        self.assertEqual(DEFAULT_STALE_PROCESSING_SECONDS, 2 * 60 * 60)

    def test_plan_skips_entire_video_with_any_healthy_dub(self):
        entries = {
            "video": {
                "languages": ["en", "es", "fr", "de"],
            }
        }
        payload = {
            "videoTranslations": [{"videoId": "video", "translations": []}],
            "audioTracks": [
                {
                    "videoId": "video",
                    "audioTrackId": "original",
                    "language": "pcm",
                    "source": "AUDIO_TRACK_SOURCE_UPLOAD",
                    "audioContentTypeString": "original",
                    "status": "AUDIO_TRACK_STATUS_INELIGIBLE",
                },
                {
                    "videoId": "video",
                    "audioTrackId": "healthy-en",
                    "language": "en",
                    "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed",
                    "status": "AUDIO_TRACK_STATUS_READY",
                },
                {
                    "videoId": "video",
                    "audioTrackId": "failed-es",
                    "language": "es",
                    "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed",
                    "status": "AUDIO_TRACK_STATUS_FAILED",
                    "rejectedReason": "AUDIO_TRACK_REJECTED_REASON_CLAIM_COMPATIBILITY_MISMATCH",
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

        actions, unreadable = build_audio_recovery_plan(payload, entries, ["video"])

        self.assertEqual(unreadable, set())
        self.assertEqual(actions, [])

    def test_absent_registered_languages_are_added_without_deleting_tracks(self):
        actions, unreadable = build_audio_recovery_plan(
            {
                "videoTranslations": [
                    {"videoId": "video", "translations": []}
                ],
                "audioTracks": [],
            },
            {"video": {"languages": ["fr", "es"]}},
            ["video"],
        )

        self.assertEqual(unreadable, set())
        self.assertEqual(actions, [
            {"video_id": "video", "language": "fr", "track_ids": [], "reason": "missing"},
            {"video_id": "video", "language": "es", "track_ids": [], "reason": "missing"},
        ])

    def test_all_dash_audio_rows_are_added_even_with_published_subtitles(self):
        for empty_audio in (None, {}, {"statusLabel": "-"}):
            with self.subTest(empty_audio=empty_audio):
                payload = {
                    "videoTranslations": [{"videoId": "video", "translations": [
                        {"languageCode": language, "audioTranslation": empty_audio,
                         "captionTranslation": {"publishStatus": "PUBLISHED"}}
                        for language in ("en", "fr")
                    ]}],
                    "audioTracks": [],
                }

                actions, unreadable = build_audio_recovery_plan(
                    payload, {"video": {"languages": ["en", "fr"]}}, ["video"]
                )

                self.assertEqual(unreadable, set())
                self.assertEqual([(a["language"], a["reason"], a["track_ids"]) for a in actions],
                                 [("en", "missing", []), ("fr", "missing", [])])

    def test_missing_and_failed_languages_are_both_recovered_without_any_healthy_audio(self):
        payload = {
            "videoTranslations": [{"videoId": "video", "translations": [
                {"languageCode": "fr", "audioTranslation": {}},
                {"languageCode": "es", "audioTranslation": {
                    "audioTrackId": "deleted-es", "statusLabel": "Đã xoá"}},
            ]}], "audioTracks": [],
        }

        actions, unreadable = build_audio_recovery_plan(
            payload, {"video": {"languages": ["fr", "es"]}}, ["video"]
        )

        self.assertEqual(unreadable, set())
        self.assertEqual([(a["language"], a["reason"], a["track_ids"]) for a in actions],
                         [("fr", "missing", []), ("es", "terminal", ["deleted-es"])])

    def test_missing_audio_is_added_while_existing_processing_track_is_left_to_finish(self):
        payload = {
            "videoTranslations": [{"videoId": "video", "translations": [
                {"languageCode": "it", "audioTranslation": {
                    "audioTrackId": "processing-it", "statusLabel": "Đang xử lý... 95%"}},
            ]}], "audioTracks": [],
        }

        actions, unreadable = build_audio_recovery_plan(
            payload, {"video": {"languages": ["it", "es"]}}, ["video"]
        )

        self.assertEqual(unreadable, set())
        self.assertEqual(actions, [
            {"video_id": "video", "language": "es", "track_ids": [], "reason": "missing"}
        ])

    def test_healthy_track_without_readable_language_still_protects_entire_video(self):
        payload = {
            "videoTranslations": [{"videoId": "video", "translations": []}],
            "audioTracks": [{
                "videoId": "video", "audioTrackId": "healthy-unknown-language",
                "source": "AUDIO_TRACK_SOURCE_CREATOR", "audioContentTypeString": "dubbed",
                "status": "AUDIO_TRACK_STATUS_READY",
            }],
        }

        actions, unreadable = build_audio_recovery_plan(
            payload, {"video": {"languages": ["es"]}}, ["video"]
        )

        self.assertEqual(actions, [])
        self.assertEqual(unreadable, set())

    def test_malformed_response_is_not_treated_as_all_audio_missing(self):
        for payload in (
            {"videoTranslations": "invalid", "audioTracks": []},
            {"videoTranslations": [{"videoId": "video", "translations": "invalid"}], "audioTracks": []},
            {"videoTranslations": [{"videoId": "video", "translations": []}], "audioTracks": "invalid"},
        ):
            with self.subTest(payload=payload):
                actions, unreadable = build_audio_recovery_plan(
                    payload, {"video": {"languages": ["es"]}}, ["video"]
                )

                self.assertEqual(actions, [])
                self.assertEqual(unreadable, {"video"})

    def test_omitted_video_is_unreadable_not_treated_as_missing_audio(self):
        actions, unreadable = build_audio_recovery_plan(
            {"videoTranslations": [], "audioTracks": []},
            {"video": {"languages": ["en"]}},
            ["video"],
        )

        self.assertEqual(actions, [])
        self.assertEqual(unreadable, {"video"})

    def test_published_translation_protects_video_when_omitted_from_root_tracks(self):
        entries = {"video": {"languages": ["fr", "es"]}}
        payload = {
            "videoTranslations": [
                {
                    "videoId": "video",
                    "translations": [
                        {
                            "languageCode": "fr",
                            "audioTranslation": {
                                "audioTrackId": "published-fr",
                                "publishStatus": "PUBLISHED",
                            },
                        },
                        {
                            "languageCode": "es",
                            "audioTranslation": {
                                "audioTrackId": "failed-es",
                                "status": "AUDIO_TRACK_STATUS_FAILED",
                            },
                        },
                    ],
                }
            ],
            # Studio sometimes omits published rows from this root collection.
            "audioTracks": [],
        }

        actions, unreadable = build_audio_recovery_plan(
            payload, entries, ["video"]
        )

        self.assertEqual(unreadable, set())
        self.assertEqual(actions, [])

    def test_published_languages_outside_registry_also_protect_entire_video(self):
        for healthy_count in (1, 2, 3):
            with self.subTest(healthy_count=healthy_count):
                payload = {
                    "videoTranslations": [{"videoId": "video", "translations": []}],
                    "audioTracks": [
                        {"videoId": "video", "audioTrackId": f"healthy-{language}",
                         "language": language, "source": "AUDIO_TRACK_SOURCE_CREATOR",
                         "audioContentTypeString": "dubbed", "status": "AUDIO_TRACK_STATUS_READY"}
                        for language in ("en", "fr", "de")[:healthy_count]
                    ] + [
                        {"videoId": "video", "audioTrackId": "deleted-es", "language": "es",
                         "source": "AUDIO_TRACK_SOURCE_CREATOR", "audioContentTypeString": "dubbed",
                         "status": "AUDIO_TRACK_STATUS_DELETED"}
                    ],
                }

                actions, unreadable = build_audio_recovery_plan(
                    payload, {"video": {"languages": ["es"]}}, ["video"]
                )

                self.assertEqual(actions, [])
                self.assertEqual(unreadable, set())

    def test_all_failed_video_is_repaired_despite_source_audio_and_published_subtitles(self):
        payload = {
            "videoTranslations": [{"videoId": "video", "translations": [
                {"languageCode": "en", "captionTranslation": {"publishStatus": "PUBLISHED"}},
                {"languageCode": "es", "audioTranslation": {
                    "audioTrackId": "deleted-es", "statusLabel": "Đã xoá"}},
                {"languageCode": "fr", "audioTranslation": {
                    "audioTrackId": "failed-fr", "status": "AUDIO_TRACK_STATUS_FAILED"}},
            ]}],
            "audioTracks": [
                {"videoId": "video", "audioTrackId": "original", "language": "ak",
                 "source": "AUDIO_TRACK_SOURCE_UPLOAD", "audioContentTypeString": "original",
                 "status": "AUDIO_TRACK_STATUS_READY"}
            ],
        }

        actions, unreadable = build_audio_recovery_plan(
            payload, {"video": {"languages": ["es", "fr"]}}, ["video"]
        )

        self.assertEqual(unreadable, set())
        self.assertEqual([(action["language"], action["track_ids"]) for action in actions],
                         [("es", ["deleted-es"]), ("fr", ["failed-fr"])])

    def test_batch_only_skips_video_with_published_audio(self):
        payload = {
            "videoTranslations": [{"videoId": video_id, "translations": []}
                                  for video_id in ("partial", "all-failed")],
            "audioTracks": [
                {"videoId": "partial", "audioTrackId": "healthy-en", "language": "en",
                 "source": "AUDIO_TRACK_SOURCE_CREATOR", "audioContentTypeString": "dubbed",
                 "status": "AUDIO_TRACK_STATUS_READY"},
            ] + [
                {"videoId": video_id, "audioTrackId": f"failed-{video_id}", "language": "es",
                 "source": "AUDIO_TRACK_SOURCE_CREATOR", "audioContentTypeString": "dubbed",
                 "status": "AUDIO_TRACK_STATUS_FAILED"}
                for video_id in ("partial", "all-failed")
            ],
        }

        actions, unreadable = build_audio_recovery_plan(
            payload, {video_id: {"languages": ["es"]} for video_id in ("partial", "all-failed")}
        )

        self.assertEqual(unreadable, set())
        self.assertEqual([action["video_id"] for action in actions], ["all-failed"])

    def test_other_published_language_does_not_prevent_repairing_stale_processing(self):
        entries = {"video": {"languages": ["it"], "processing_observations": {
            "it": {"track_ids": ["processing-it"], "first_seen_at": 1000,
                   "last_seen_at": 1000, "scan_count": 10}
        }}}
        payload = {
            "videoTranslations": [{"videoId": "video", "translations": [
                {"languageCode": "en", "audioTranslation": {
                    "audioTrackId": "published-en", "publishStatus": "PUBLISHED"}},
                {"languageCode": "it", "audioTranslation": {
                    "audioTrackId": "processing-it", "statusLabel": "Đang xử lý... 95%"}},
            ]}], "audioTracks": [],
        }
        observations = {}
        actions, unreadable = build_audio_recovery_plan(
            payload, entries, ["video"], observation_sink=observations
        )
        state = {"entries": {"channel": entries}}
        with patch("src.audio_recovery._load_state", return_value=state), patch(
            "src.audio_recovery.state_manager.save_state", return_value=True
        ):
            stale_actions = _record_processing_observations(
                channel_id="channel", requested_entries=entries, observations=observations,
                observed_at=1000 + DEFAULT_STALE_PROCESSING_SECONDS,
            )

        self.assertEqual(actions, [])
        self.assertEqual(unreadable, set())
        self.assertEqual([action["track_ids"] for action in stale_actions], [["processing-it"]])
        self.assertEqual(entries["video"]["processing_observations"]["it"]["first_seen_at"], 1000)

    def test_same_processing_track_is_eligible_only_after_two_hours(self):
        entries = {"video": {"languages": ["it"]}}
        payload = {
            "videoTranslations": [
                {
                    "videoId": "video",
                    "translations": [
                        {
                            "languageCode": "it",
                            "audioTranslation": {
                                "audioTrackId": "processing-it",
                                "statusLabel": "Đang xử lý... 95%",
                            },
                        }
                    ],
                }
            ],
            "audioTracks": [],
        }
        observations = {}
        actions, unreadable = build_audio_recovery_plan(
            payload,
            entries,
            ["video"],
            observation_sink=observations,
        )
        self.assertEqual(actions, [])
        self.assertEqual(unreadable, set())

        state = {
            "entries": {
                "channel": {
                    "video": {
                        "languages": ["it"],
                    }
                }
            },
            "channel_refresh_alerts": {},
        }
        with (
            patch("src.audio_recovery._load_state", return_value=state),
            patch(
                "src.audio_recovery.state_manager.save_state",
                return_value=True,
            ) as save,
            patch("src.audio_recovery.logger.warning") as warn,
        ):
            first = _record_processing_observations(
                channel_id="channel",
                requested_entries=entries,
                observations=observations,
                observed_at=1000,
            )
            before = _record_processing_observations(
                channel_id="channel", requested_entries=entries,
                observations=observations,
                observed_at=1000 + DEFAULT_STALE_PROCESSING_SECONDS - 1,
            )
            warning = _record_processing_observations(
                channel_id="channel",
                requested_entries=entries,
                observations=observations,
                observed_at=1000 + DEFAULT_STALE_PROCESSING_SECONDS,
            )
            repeated = _record_processing_observations(
                channel_id="channel",
                requested_entries=entries,
                observations=observations,
                observed_at=1000 + 2 * DEFAULT_STALE_PROCESSING_SECONDS,
            )

        self.assertEqual(first, [])
        self.assertEqual(before, [])
        self.assertEqual(
            warning,
            [
                {
                    "channel_id": "channel",
                    "video_id": "video",
                    "language": "it",
                    "track_ids": ["processing-it"],
                    "reason": PROCESSING_WARNING_REASON,
                    "age_seconds": DEFAULT_STALE_PROCESSING_SECONDS,
                }
            ],
        )
        tracker = state["entries"]["channel"]["video"][
            "processing_observations"
        ]["it"]
        self.assertEqual(tracker["first_seen_at"], 1000)
        self.assertEqual(tracker["scan_count"], 4)
        self.assertEqual(tracker["warning_reason"], PROCESSING_WARNING_REASON)
        self.assertEqual(tracker["warned_at"], 1000 + DEFAULT_STALE_PROCESSING_SECONDS)
        self.assertEqual(repeated[0]["reason"], PROCESSING_WARNING_REASON)
        self.assertEqual(repeated[0]["age_seconds"], 2 * DEFAULT_STALE_PROCESSING_SECONDS)
        self.assertEqual(save.call_count, 4)
        warn.assert_called_once()

    def test_changed_processing_track_restarts_stale_clock(self):
        entries = {"video": {"languages": ["it"]}}
        state = {
            "entries": {
                "channel": {
                    "video": {
                        "languages": ["it"],
                        "processing_observations": {
                            "it": {
                                "language": "it",
                                "track_ids": ["old-track"],
                                "first_seen_at": 1000,
                                "last_seen_at": 1000,
                                "scan_count": 10,
                                "warning_reason": PROCESSING_WARNING_REASON,
                                "warned_at": 1000,
                            }
                        },
                    }
                }
            },
            "channel_refresh_alerts": {},
        }
        observations = {
            "video": {
                "it": {
                    "states": ["inflight"],
                    "inflight_track_ids": ["new-track"],
                }
            }
        }
        with (
            patch("src.audio_recovery._load_state", return_value=state),
            patch(
                "src.audio_recovery.state_manager.save_state",
                return_value=True,
            ),
        ):
            stale = _record_processing_observations(
                channel_id="channel",
                requested_entries=entries,
                observations=observations,
                observed_at=1000 + DEFAULT_STALE_PROCESSING_SECONDS,
            )

        self.assertEqual(stale, [])
        tracker = state["entries"]["channel"]["video"][
            "processing_observations"
        ]["it"]
        self.assertEqual(tracker["track_ids"], ["new-track"])
        self.assertEqual(tracker["first_seen_at"], 1000 + DEFAULT_STALE_PROCESSING_SECONDS)
        self.assertEqual(tracker["scan_count"], 1)
        self.assertNotIn("warning_reason", tracker)
        self.assertNotIn("warned_at", tracker)


class AudioRecoveryRegistryTests(unittest.TestCase):
    def test_scan_scope_defaults_to_all_for_existing_installations(self):
        with patch("src.audio_recovery.state_manager.load_state", return_value=None):
            preferences = get_audio_recovery_scan_preferences()

        self.assertEqual(preferences["scan_mode"], RECOVERY_SCAN_MODE_ALL)
        self.assertEqual(preferences["selected_channel_ids"], [])
        self.assertEqual(preferences["video_scan_scope"], RECOVERY_VIDEO_SCOPE_PUBLIC)

    def test_selected_scan_scope_is_persisted_without_changing_registry(self):
        stored = {
            "enabled": True,
            "entries": {"channel-a": {"video": {"languages": ["en"]}}},
        }

        def load(_name):
            return stored.copy()

        def save(_name, state):
            stored.clear()
            stored.update(state)
            return True

        with (
            patch("src.audio_recovery.state_manager.load_state", side_effect=load),
            patch("src.audio_recovery.state_manager.save_state", side_effect=save),
        ):
            saved = set_audio_recovery_scan_preferences(
                scan_mode=RECOVERY_SCAN_MODE_SELECTED,
                selected_channel_ids=["channel-b", "channel-a", "channel-b", ""],
            )
            preferences = get_audio_recovery_scan_preferences()

        self.assertTrue(saved)
        self.assertEqual(preferences["scan_mode"], RECOVERY_SCAN_MODE_SELECTED)
        self.assertEqual(
            preferences["selected_channel_ids"],
            ["channel-b", "channel-a"],
        )
        self.assertIn("channel-a", stored["entries"])

    def test_imports_completed_legacy_add_audio_flow_items(self):
        flow_state = {
            "selected_channel": "channel",
            "statuses": {
                "source.mp4": {
                    "video_id": "video",
                    "music_path": r"D:\\music\\source.mp3",
                    "audio_language_results": {
                        "en": {"status": "successful"},
                        "es": {"status": "already_added"},
                        "fr": {"status": "unsuccessful"},
                    },
                }
            },
        }
        recovery_state = {"entries": {}, "channel_refresh_alerts": {}}

        with (
            patch(
                "src.audio_recovery.state_manager.load_state",
                return_value=flow_state,
            ),
            patch("src.audio_recovery._load_state", return_value=recovery_state),
            patch(
                "src.audio_recovery.register_audio_recovery",
                return_value=True,
            ) as register,
        ):
            imported = import_add_audio_flow_recovery_state()

        self.assertEqual(imported, 1)
        register.assert_called_once_with(
            channel_id="channel",
            video_id="video",
            audio_path=r"D:\\music\\source.mp3",
            languages=["en", "es"],
            repeat_times=1,
            extra_minutes=0,
            registered_at=0,
        )

    def test_registration_persists_mapping_and_language_configuration(self):
        stored = {}

        def load(name):
            self.assertEqual(name, "audio_recovery")
            return stored.copy() if stored else None

        def save(name, state):
            self.assertEqual(name, "audio_recovery")
            stored.clear()
            stored.update(state)
            return True

        with (
            patch("src.audio_recovery.state_manager.load_state", side_effect=load),
            patch("src.audio_recovery.state_manager.save_state", side_effect=save),
        ):
            saved = register_audio_recovery(
                channel_id="channel",
                video_id="video",
                audio_path=r"D:\\music\\track.mp3",
                languages=["en", "es", "en"],
                repeat_times=2,
                extra_minutes=1.5,
            )

        self.assertTrue(saved)
        entry = stored["entries"]["channel"]["video"]
        self.assertEqual(entry["languages"], ["en", "es"])
        self.assertEqual(entry["repeat_times"], 2)
        self.assertEqual(entry["extra_minutes"], 1.5)

    def test_caption_monitor_is_attached_to_registered_audio_entry(self):
        state = {
            "enabled": True,
            "entries": {
                "channel": {
                    "video": {
                        "audio_path": "track.mp3",
                        "languages": ["en"],
                    }
                }
            },
            "channel_refresh_alerts": {},
        }

        with (
            patch("src.audio_recovery._load_state", return_value=state),
            patch(
                "src.audio_recovery.state_manager.save_state",
                return_value=True,
            ) as save,
        ):
            saved = register_caption_monitor(
                channel_id="channel",
                video_id="video",
                source_srt_path="source.en.srt",
                source_language="en",
                languages=["en", "fr", "fr"],
                now=1000,
            )

        self.assertTrue(saved)
        save.assert_called_once()
        monitor = state["entries"]["channel"]["video"]["caption_monitor"]
        self.assertEqual(monitor["languages"], ["en", "fr"])
        self.assertEqual(monitor["next_check_at"], 1000 + 15 * 60)

    def test_reregistering_audio_preserves_pending_caption_monitor(self):
        monitor = {
            "source_srt_path": "source.en.srt",
            "source_language": "en",
            "languages": ["fr"],
            "next_check_at": 1900,
        }
        state = {
            "enabled": True,
            "entries": {
                "channel": {
                    "video": {
                        "audio_path": "track.mp3",
                        "languages": ["en"],
                        "repeat_times": 1,
                        "extra_minutes": 0,
                        "attempts": {},
                        "caption_monitor": monitor,
                    }
                }
            },
            "channel_refresh_alerts": {},
        }

        with (
            patch("src.audio_recovery._load_state", return_value=state),
            patch("src.audio_recovery.state_manager.save_state", return_value=True),
        ):
            saved = register_audio_recovery(
                channel_id="channel",
                video_id="video",
                audio_path="track.mp3",
                languages=["en"],
                repeat_times=1,
                extra_minutes=0,
            )

        self.assertTrue(saved)
        self.assertEqual(
            state["entries"]["channel"]["video"]["caption_monitor"],
            monitor,
        )


    def test_clear_registry_stops_future_automatic_recovery(self):
        stored = {
            "enabled": True,
            "entries": {"channel": {"video": {"languages": ["en"]}}},
        }

        def load(_name):
            return stored.copy()

        def save(_name, state):
            stored.clear()
            stored.update(state)
            return True

        with (
            patch("src.audio_recovery.state_manager.load_state", side_effect=load),
            patch("src.audio_recovery.state_manager.save_state", side_effect=save),
        ):
            self.assertTrue(clear_audio_recovery_registry())

        self.assertEqual(stored["entries"], {})

    def test_only_token_failure_persists_channel_refresh_alert(self):
        stored = {
            "enabled": True,
            "entries": {},
            "channel_refresh_alerts": {},
        }

        def load(_name):
            return stored.copy()

        def save(_name, state):
            stored.clear()
            stored.update(state)
            return True

        with (
            patch("src.audio_recovery.state_manager.load_state", side_effect=load),
            patch("src.audio_recovery.state_manager.save_state", side_effect=save),
        ):
            self.assertTrue(
                mark_channel_refresh_required(
                    "channel-a",
                    "Retry failed: encodedReauthProofToken vẫn không có",
                    now=1234,
                )
            )
            alerts = get_channel_refresh_alerts()
            self.assertEqual(set(alerts), {"channel-a"})
            self.assertEqual(
                alerts["channel-a"]["reason"],
                "encoded_reauth_proof_token_missing",
            )
            self.assertEqual(acknowledge_channel_refresh(["channel-a"]), 1)

        self.assertEqual(stored["channel_refresh_alerts"], {})

    def test_failed_post_reload_validation_records_red_channel_details(self):
        stored = {
            "enabled": True,
            "entries": {},
            "channel_refresh_alerts": {},
        }

        def load(_name):
            return stored.copy()

        def save(_name, state):
            stored.clear()
            stored.update(state)
            return True

        with (
            patch("src.audio_recovery.state_manager.load_state", side_effect=load),
            patch("src.audio_recovery.state_manager.save_state", side_effect=save),
        ):
            self.assertTrue(
                mark_channel_refresh_required(
                    "channel-a",
                    "sessionToken=secret rejected",
                    now=1234,
                    channel_name="Channel A",
                    validation_failed=True,
                )
            )

        alert = stored["channel_refresh_alerts"]["channel-a"]
        self.assertEqual(alert["channel_name"], "Channel A")
        self.assertEqual(alert["requested_at"], 1234)
        self.assertEqual(alert["severity"], "error")
        self.assertTrue(alert["validation_failed"])
        self.assertNotIn("secret", alert["error"])


class AudioRecoveryVisibilityTests(unittest.TestCase):
    def test_video_scope_distinguishes_scheduled_private_from_unscheduled_and_draft(self):
        videos = [
            SimpleNamespace(id="public", privacy="VIDEO_PRIVACY_PUBLIC"),
            SimpleNamespace(id="scheduled-private", privacy="VIDEO_PRIVACY_PRIVATE", scheduled_publishing_details={"time": "later"}),
            SimpleNamespace(id="scheduled-public", privacy="VIDEO_PRIVACY_PUBLIC", scheduled_publishing_details={"time": "later"}),
            SimpleNamespace(id="private", privacy="VIDEO_PRIVACY_PRIVATE"),
            SimpleNamespace(id="unlisted", privacy="VIDEO_PRIVACY_UNLISTED"),
            SimpleNamespace(id="draft", privacy="VIDEO_PRIVACY_PUBLIC", draft_status={"isDraft": True}, scheduled_publishing_details={"time": "later"}),
        ]
        requested = [video.id for video in videos] + ["missing"]
        for scope, expected in (
            (RECOVERY_VIDEO_SCOPE_PUBLIC, {"public"}),
            (RECOVERY_VIDEO_SCOPE_SCHEDULED, {"scheduled-private", "scheduled-public"}),
            (RECOVERY_VIDEO_SCOPE_BOTH, {"public", "scheduled-private", "scheduled-public"}),
        ):
            with self.subTest(scope=scope), patch(
                "src.audio_recovery.list_videos_module.list_all_videos",
                return_value=(videos, None),
            ):
                matches, unresolved = _get_registered_video_scan_statuses(
                    "channel", requested, video_scan_scope=scope
                )
            self.assertEqual({vid for vid, matches_scope in matches.items() if matches_scope}, expected)
            self.assertEqual(unresolved, {"missing"})

    def test_scheduled_scope_stops_matching_after_video_goes_public(self):
        for scope, expected in (
            (RECOVERY_VIDEO_SCOPE_PUBLIC, [False, True]),
            (RECOVERY_VIDEO_SCOPE_SCHEDULED, [True, False]),
            (RECOVERY_VIDEO_SCOPE_BOTH, [True, True]),
        ):
            with self.subTest(scope=scope), patch(
                "src.audio_recovery.list_videos_module.list_all_videos",
                side_effect=[
                    ([SimpleNamespace(id="video", privacy="VIDEO_PRIVACY_PRIVATE", scheduled_publishing_details={"time": "later"})], None),
                    ([SimpleNamespace(id="video", privacy="VIDEO_PRIVACY_PUBLIC", scheduled_publishing_details={})], None),
                ],
            ):
                actual = [
                    _get_registered_video_scan_statuses("channel", ["video"], video_scan_scope=scope)[0]["video"]
                    for _ in range(2)
                ]
            self.assertEqual(actual, expected)

    def test_visibility_lookup_pages_and_rejects_draft_or_scheduled_public(self):
        with patch(
            "src.audio_recovery.list_videos_module.list_all_videos",
            side_effect=[
                (
                    [
                        SimpleNamespace(
                            id="private-video",
                            privacy="VIDEO_PRIVACY_PRIVATE",
                        ),
                        SimpleNamespace(
                            id="draft-video",
                            privacy="VIDEO_PRIVACY_PUBLIC",
                            draft_status="VIDEO_DRAFT_STATUS_DRAFT",
                        ),
                        SimpleNamespace(
                            id="scheduled-video",
                            privacy="VIDEO_PRIVACY_PUBLIC",
                            scheduled_publishing_details={"time": "later"},
                        ),
                    ],
                    "next-page",
                ),
                (
                    [
                        SimpleNamespace(
                            id="public-video",
                            privacy="VIDEO_PRIVACY_PUBLIC",
                        )
                    ],
                    None,
                ),
            ],
        ) as list_videos:
            public_statuses, unresolved = _get_registered_video_scan_statuses(
                "channel",
                [
                    "public-video",
                    "private-video",
                    "draft-video",
                    "scheduled-video",
                    "missing-video",
                ],
            )

        self.assertEqual(
            public_statuses,
            {
                "private-video": False,
                "draft-video": False,
                "scheduled-video": False,
                "public-video": True,
            },
        )
        self.assertEqual(unresolved, {"missing-video"})
        self.assertEqual(list_videos.call_count, 2)


class AudioRecoveryCycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.visibility_patch = patch(
            "src.audio_recovery._get_registered_video_scan_statuses",
            side_effect=lambda _channel_id, video_ids, **_kwargs: (
                {video_id: True for video_id in video_ids},
                set(),
            ),
        )
        self.visibility_patch.start()
        self.addCleanup(self.visibility_patch.stop)

    async def test_each_video_scope_repairs_only_matching_active_registry_videos(self):
        from src.audio_recovery import update_audio_module

        videos = [
            SimpleNamespace(id="public", privacy="VIDEO_PRIVACY_PUBLIC"),
            SimpleNamespace(id="scheduled", privacy="VIDEO_PRIVACY_PRIVATE", scheduled_publishing_details={"time": "later"}),
            SimpleNamespace(id="private", privacy="VIDEO_PRIVACY_PRIVATE"),
            SimpleNamespace(id="draft", privacy="VIDEO_PRIVACY_PUBLIC", draft_status="DRAFT"),
            SimpleNamespace(id="disabled-scheduled", privacy="VIDEO_PRIVACY_PRIVATE", scheduled_publishing_details={"time": "later"}),
        ]

        def fetch(video_ids, _channel_id):
            return {
                "videoTranslations": [{"videoId": vid} for vid in video_ids],
                "audioTracks": [
                    {"videoId": vid, "audioTrackId": f"failed-{vid}", "language": "en",
                     "source": "AUDIO_TRACK_SOURCE_CREATOR", "audioContentTypeString": "dubbed",
                     "status": "AUDIO_TRACK_STATUS_FAILED"}
                    for vid in video_ids
                ],
            }

        def render_audio(*, output_file, **_kwargs):
            Path(output_file).write_bytes(b"rendered")

        async def run_retry(operation, **_kwargs):
            return operation()

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.write_bytes(b"source")
            for scope, expected in (
                (RECOVERY_VIDEO_SCOPE_PUBLIC, ["public"]),
                (RECOVERY_VIDEO_SCOPE_SCHEDULED, ["scheduled"]),
                (RECOVERY_VIDEO_SCOPE_BOTH, ["public", "scheduled"]),
            ):
                state = {
                    "enabled": True, "video_scan_scope": scope, "initial_grace_seconds": 0,
                    "retry_cooldown_seconds": 0, "disabled_video_ids": {"channel": ["disabled-scheduled"]},
                    "entries": {"channel": {
                        vid: {"audio_path": str(source), "languages": ["en"], "repeat_times": 1}
                        for vid in [video.id for video in videos] + ["missing"]
                    }},
                }
                caption_monitor = AsyncMock(return_value={"repaired": 0, "failed": 0, "quota_message": ""})
                with (
                    self.subTest(scope=scope),
                    patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
                    patch("src.audio_recovery._load_state", return_value=state),
                    patch("src.audio_recovery.state_manager.save_state", return_value=True),
                    patch("src.audio_recovery._get_registered_video_scan_statuses", side_effect=_get_registered_video_scan_statuses),
                    patch("src.audio_recovery.list_videos_module.list_all_videos", return_value=(videos, None)),
                    patch.object(update_audio_module, "_get_video_translation_payload", side_effect=fetch) as query,
                    patch.object(update_audio_module, "_get_video_info", return_value=SimpleNamespace(duration_ms=60_000)),
                    patch.object(update_audio_module, "delete_track_ids", return_value=200) as delete,
                    patch.object(update_audio_module, "add", return_value=200) as add,
                    patch("src.audio_recovery.multiply_audio", side_effect=render_audio),
                    patch("src.audio_recovery.call_audio_update_with_retry", new=AsyncMock(side_effect=run_retry)),
                    patch("src.audio_recovery._monitor_failed_caption_tracks", caption_monitor),
                ):
                    result = await run_audio_recovery_cycle(now=2000)
                    query.assert_called_once_with(expected, "channel")
                    self.assertEqual([call.kwargs["id_video"] for call in add.call_args_list], expected)
                    self.assertEqual([call.args[0] for call in delete.call_args_list], expected)
                    self.assertEqual(set(caption_monitor.await_args.kwargs["entries"]), set(expected))
                    self.assertEqual(result["repaired"], len(expected))
                    self.assertEqual(result["failed"], 0)
                    self.assertEqual(result["video_scan_scope"], scope)
                    self.assertEqual(result["deferred_video_scope"], 4 - len(expected))
                    self.assertEqual(result["deferred_visibility_unknown"], 1)
                    self.assertEqual(len(state["entries"]["channel"]), 6)

    async def test_selected_scope_scans_only_selected_registry_channels(self):
        state = {
            "enabled": True,
            "scan_mode": RECOVERY_SCAN_MODE_SELECTED,
            "selected_channel_ids": ["channel-a"],
            "retry_cooldown_seconds": 0,
            "initial_grace_seconds": 0,
            "entries": {
                "channel-a": {
                    "video-a": {"audio_path": "unused-a.mp3", "languages": ["en"]}
                },
                "channel-b": {
                    "video-b": {"audio_path": "unused-b.mp3", "languages": ["en"]}
                },
            },
            "channel_refresh_alerts": {},
        }
        scanned_channels = []

        def fetch(video_ids, channel_id):
            scanned_channels.append(channel_id)
            return {
                "videoTranslations": [
                    {"videoId": video_id} for video_id in video_ids
                ],
                "audioTracks": [
                    {
                        "videoId": video_id,
                        "audioTrackId": f"healthy-{video_id}",
                        "language": "en",
                        "source": "AUDIO_TRACK_SOURCE_CREATOR",
                        "audioContentTypeString": "dubbed",
                        "status": "AUDIO_TRACK_STATUS_READY",
                    }
                    for video_id in video_ids
                ],
            }

        with (
            patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
            patch("src.audio_recovery._load_state", return_value=state),
            patch("src.audio_recovery.state_manager.save_state", return_value=True),
            patch.object(
                __import__(
                    "src.audio_recovery", fromlist=["update_audio_module"]
                ).update_audio_module,
                "_get_video_translation_payload",
                side_effect=fetch,
            ),
        ):
            result = await run_audio_recovery_cycle(now=2000)

        self.assertEqual(scanned_channels, ["channel-a"])
        self.assertEqual(result["scan_mode"], RECOVERY_SCAN_MODE_SELECTED)
        self.assertEqual(result["scope_skipped_channel_ids"], ["channel-b"])

    async def test_deselecting_channel_finishes_current_track_then_stops_scheduling(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.write_bytes(b"source")
            state = {
                "enabled": True,
                "scan_mode": RECOVERY_SCAN_MODE_SELECTED,
                "selected_channel_ids": ["channel"],
                "retry_cooldown_seconds": 0,
                "initial_grace_seconds": 0,
                "entries": {
                    "channel": {
                        "video": {
                            "audio_path": str(source),
                            "languages": ["en", "es"],
                            "repeat_times": 1,
                            "extra_minutes": 0,
                            "attempts": {},
                        }
                    }
                },
                "channel_refresh_alerts": {},
            }
            payload = {
                "videoTranslations": [
                    {
                        "videoId": "video",
                        "translations": [
                            {
                                "languageCode": language,
                                "audioTranslation": {
                                    "status": "AUDIO_TRACK_STATUS_FAILED"
                                },
                            }
                            for language in ("en", "es")
                        ],
                    }
                ],
                "audioTracks": [],
            }

            def render_audio(*, output_file, **_kwargs):
                Path(output_file).write_bytes(b"rendered")

            def add_track(**kwargs):
                state["selected_channel_ids"] = []
                return 200

            async def run_retry(operation, **_kwargs):
                return operation()

            added = Mock(side_effect=add_track)
            with (
                patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
                patch("src.audio_recovery._load_state", return_value=state),
                patch("src.audio_recovery.state_manager.save_state", return_value=True),
                patch("src.audio_recovery._record_recovery_attempt"),
                patch.object(
                    __import__(
                        "src.audio_recovery", fromlist=["update_audio_module"]
                    ).update_audio_module,
                    "_get_video_translation_payload",
                    return_value=payload,
                ),
                patch.object(
                    __import__(
                        "src.audio_recovery", fromlist=["update_audio_module"]
                    ).update_audio_module,
                    "_get_video_info",
                    return_value=SimpleNamespace(duration_ms=60_000),
                ),
                patch.object(
                    __import__(
                        "src.audio_recovery", fromlist=["update_audio_module"]
                    ).update_audio_module,
                    "add",
                    added,
                ),
                patch("src.audio_recovery.multiply_audio", side_effect=render_audio),
                patch(
                    "src.audio_recovery.call_audio_update_with_retry",
                    new=AsyncMock(side_effect=run_retry),
                ),
            ):
                result = await run_audio_recovery_cycle(now=2000)

        self.assertEqual(result["repaired"], 1)
        self.assertEqual(added.call_count, 1)
        self.assertEqual(added.call_args.kwargs["language"], "en")
        self.assertEqual(result["scope_skipped_channel_ids"], ["channel"])

    async def test_cycle_replaces_processing_after_two_hours_and_restarts_the_new_track_timer(self):
        from src.audio_recovery import update_audio_module
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.write_bytes(b"source")
            entry = {"audio_path": str(source), "languages": ["it"], "attempts": {}}
            state = {"enabled": True, "entries": {"channel": {"video": entry}}}
            audio = {"audioTrackId": "processing-it", "statusLabel": "Dang xu ly"}
            # Enum is authoritative; captions and titles cannot trigger repair.
            audio["status"] = "AUDIO_TRACK_STATUS_PROCESSING"
            payload = {"videoTranslations": [{"videoId": "video", "translations": [
                {"languageCode": "it", "audioTranslation": audio},
            ]}], "audioTracks": []}
            events = []

            def delete(*args):
                events.append(("delete", args))
                return 200

            def add(**kwargs):
                events.append(("add", kwargs["language"]))
                return 200

            def render_audio(*, output_file, **_kwargs):
                Path(output_file).write_bytes(b"rendered")

            with (
                patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
                patch("src.audio_recovery._load_state", return_value=state),
                patch("src.audio_recovery.state_manager.save_state", return_value=True),
                patch.object(update_audio_module, "_get_video_translation_payload", return_value=payload) as fetch,
                patch.object(update_audio_module, "_get_video_info", return_value=SimpleNamespace(duration_ms=60000)),
                patch.object(update_audio_module, "delete_track_ids", side_effect=delete),
                patch.object(update_audio_module, "add", side_effect=add),
                patch("src.audio_recovery.multiply_audio", side_effect=render_audio),
            ):
                first = await run_audio_recovery_cycle(now=1000)
                before = await run_audio_recovery_cycle(now=1000 + DEFAULT_STALE_PROCESSING_SECONDS - 1)
                self.assertEqual(events, [])
                overdue = await run_audio_recovery_cycle(now=1000 + DEFAULT_STALE_PROCESSING_SECONDS)
                self.assertEqual(events, [("delete", ("video", "channel", ["processing-it"])), ("add", "it")])
                self.assertNotIn("processing_observations", entry)
                self.assertTrue(entry["attempts"]["it"]["succeeded"])
                self.assertEqual(entry["attempts"]["it"]["message"], PROCESSING_WARNING_REASON)
                self.assertEqual(fetch.call_count, 4)  # scan, scan, scan, pre-delete check
                audio["audioTrackId"] = "replacement-it"
                next_scan = await run_audio_recovery_cycle(now=1000 + DEFAULT_STALE_PROCESSING_SECONDS + 1)
                self.assertEqual(entry["processing_observations"]["it"]["first_seen_at"], 1000 + DEFAULT_STALE_PROCESSING_SECONDS + 1)
                audio.clear()
                audio.update(audioTrackId="replacement-it", publishStatus="PUBLISHED")
                healthy = await run_audio_recovery_cycle(now=1000 + DEFAULT_STALE_PROCESSING_SECONDS + 2)

            self.assertEqual([first["repaired"], before["repaired"], overdue["repaired"], next_scan["repaired"]], [0, 0, 1, 0])
            self.assertEqual(overdue["failed"], 0)
            self.assertEqual(overdue["processing_warnings"][0]["track_ids"], ["processing-it"])
            self.assertEqual(healthy["processing_warnings"], [])
            self.assertNotIn("processing_observations", entry)
            self.assertEqual(len(events), 2)

    async def test_caption_monitor_repairs_only_explicit_failed_tracks(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.en.srt"
            source.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
            entries = {
                "video": {
                    "caption_monitor": {
                        "source_srt_path": str(source),
                        "source_language": "en",
                        "languages": ["en", "fr", "es", "de"],
                        "next_check_at": 0,
                    }
                }
            }
            tracks = [
                {"id": "source", "snippet": {"language": "en", "status": "serving"}},
                {"id": "failed-fr", "snippet": {"language": "fr", "status": "failed"}},
                {"id": "serving-es", "snippet": {"language": "es", "status": "serving"}},
            ]
            client = SimpleNamespace(
                list_tracks=Mock(return_value=tracks),
                track_language=lambda track: str((track.get("snippet") or {}).get("language") or ""),
                download_translation=Mock(return_value=b"translated srt"),
                upsert_track=Mock(return_value=("failed-fr", "successful")),
            )

            with (
                patch("src.audio_recovery.YouTubeCaptionClient", return_value=client),
                patch(
                    "src.audio_recovery.get_caption_quota_status",
                    return_value={"blocked": False},
                ),
                patch("src.audio_recovery._save_caption_monitor_state") as save,
            ):
                result = await _monitor_failed_caption_tracks(
                    channel_id="channel",
                    entries=entries,
                    cycle_time=1000,
                )

        self.assertEqual(result["repaired"], 1)
        self.assertEqual(result["failed"], 0)
        client.download_translation.assert_called_once_with("source", "fr")
        client.upsert_track.assert_called_once()
        self.assertEqual(client.upsert_track.call_args.kwargs["language"], "fr")
        save.assert_called_once_with(
            "channel",
            "video",
            languages=["fr"],
            next_check_at=1000 + 15 * 60,
        )

    async def test_caption_monitor_waits_for_syncing_track_without_upload(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.en.srt"
            source.write_text("source", encoding="utf-8")
            entries = {
                "video": {
                    "caption_monitor": {
                        "source_srt_path": str(source),
                        "source_language": "en",
                        "languages": ["fr"],
                        "next_check_at": 0,
                    }
                }
            }
            client = SimpleNamespace(
                list_tracks=Mock(
                    return_value=[
                        {"id": "fr", "snippet": {"language": "fr", "status": "syncing"}}
                    ]
                ),
                track_language=lambda track: str((track.get("snippet") or {}).get("language") or ""),
                download_translation=Mock(),
                upsert_track=Mock(),
            )

            with (
                patch("src.audio_recovery.YouTubeCaptionClient", return_value=client),
                patch(
                    "src.audio_recovery.get_caption_quota_status",
                    return_value={"blocked": False},
                ),
                patch("src.audio_recovery._save_caption_monitor_state") as save,
            ):
                result = await _monitor_failed_caption_tracks(
                    channel_id="channel",
                    entries=entries,
                    cycle_time=1000,
                )

        self.assertEqual(result["repaired"], 0)
        client.download_translation.assert_not_called()
        client.upsert_track.assert_not_called()
        save.assert_called_once_with(
            "channel",
            "video",
            languages=["fr"],
            next_check_at=1000 + 6 * 60 * 60,
        )

    async def test_caption_monitor_receives_only_public_video_entries(self):
        state = {
            "enabled": True,
            "retry_cooldown_seconds": 0,
            "entries": {
                "channel": {
                    video_id: {
                        "audio_path": "unused.mp3",
                        "languages": ["en"],
                    }
                    for video_id in ("public-video", "private-video")
                }
            },
            "channel_refresh_alerts": {},
        }
        caption_monitor = AsyncMock(
            return_value={"repaired": 0, "failed": 0, "quota_message": ""}
        )
        fetch = Mock(
            return_value={
                "videoTranslations": [{"videoId": "public-video"}],
                "audioTracks": [
                    {
                        "videoId": "public-video",
                        "audioTrackId": "healthy-en",
                        "language": "en",
                        "source": "AUDIO_TRACK_SOURCE_CREATOR",
                        "audioContentTypeString": "dubbed",
                        "status": "AUDIO_TRACK_STATUS_READY",
                    }
                ],
            }
        )

        with (
            patch(
                "src.audio_recovery._get_registered_video_scan_statuses",
                return_value=(
                    {"public-video": True, "private-video": False},
                    set(),
                ),
            ),
            patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
            patch("src.audio_recovery._load_state", return_value=state),
            patch("src.audio_recovery.state_manager.save_state", return_value=True),
            patch(
                "src.audio_recovery._monitor_failed_caption_tracks",
                caption_monitor,
            ),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "_get_video_translation_payload",
                fetch,
            ),
        ):
            result = await run_audio_recovery_cycle(now=2000)

        self.assertEqual(result["deferred_video_scope"], 1)
        caption_monitor.assert_awaited_once()
        self.assertEqual(
            set(caption_monitor.await_args.kwargs["entries"]),
            {"public-video"},
        )

    async def test_monitor_runs_immediately_after_restart_despite_recent_cycle(self):
        stop_event = asyncio.Event()
        state = {
            "enabled": True,
            "interval_seconds": 15 * 60,
            "last_cycle_at": 10**12,
            "last_cycle_result": {},
        }

        async def run_once(**_kwargs):
            stop_event.set()
            return {"repaired": 0, "failed": 0}

        cycle = AsyncMock(side_effect=run_once)
        with (
            patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
            patch("src.audio_recovery.run_audio_recovery_cycle", cycle),
        ):
            await asyncio.wait_for(_monitor_loop(stop_event), timeout=0.2)

        cycle.assert_awaited_once_with(stop_event=stop_event)

    async def test_monitor_repeats_as_soon_as_previous_scan_finishes_without_overlap(self):
        for deferred_busy in (0, 1):
            with self.subTest(deferred_busy=deferred_busy):
                stop_event = asyncio.Event()
                first_started = asyncio.Event()
                finish_first = asyncio.Event()
                calls = 0

                async def scan(**_kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == 1:
                        first_started.set()
                        await finish_first.wait()
                    else:
                        stop_event.set()
                    return {"scanned_channels": 1, "deferred_busy": deferred_busy}

                cycle = AsyncMock(side_effect=scan)
                with (
                    patch("src.audio_recovery.run_audio_recovery_cycle", cycle),
                    patch("src.audio_recovery.get_audio_recovery_state", return_value={
                        "interval_seconds": 15 * 60,
                    }),
                ):
                    task = asyncio.create_task(_monitor_loop(stop_event))
                    try:
                        await asyncio.wait_for(first_started.wait(), timeout=0.5)
                        await asyncio.sleep(0)
                        self.assertEqual(cycle.await_count, 1)
                        finish_first.set()
                        await asyncio.wait_for(task, timeout=0.5)
                    finally:
                        if not task.done():
                            task.cancel()
                            with self.assertRaises(asyncio.CancelledError):
                                await task
                self.assertEqual(cycle.await_count, 2)

    async def test_monitor_waits_briefly_when_no_scan_can_run_or_response_is_unreadable(self):
        results = [
            {"skipped": "disabled"}, {"skipped": "empty"},
            {"skipped": "no_selected_channels"},
            {"scanned_channels": 0, "deferred_busy": 1},
            {"scanned_channels": 0, "reauth_required": ["channel"]},
            {"scanned_channels": 1, "unreadable": ["video"]},
        ]
        for result in results:
            with self.subTest(result=result):
                stop_event = asyncio.Event()

                async def stop_when_idle(awaitable, *, timeout):
                    stop_event.set()
                    return await awaitable

                with (
                    patch("src.audio_recovery.run_audio_recovery_cycle", new=AsyncMock(return_value=result)) as cycle,
                    patch("src.audio_recovery.asyncio.wait_for", new=AsyncMock(side_effect=stop_when_idle)) as wait,
                ):
                    await _monitor_loop(stop_event)
                cycle.assert_awaited_once_with(stop_event=stop_event)
                self.assertEqual(wait.await_args.kwargs["timeout"], MONITOR_IDLE_POLL_SECONDS)

    async def test_monitor_waits_after_unexpected_error_and_stops_during_idle_wait(self):
        stop_event = asyncio.Event()
        wait_for = asyncio.wait_for
        with patch("src.audio_recovery.run_audio_recovery_cycle", new=AsyncMock(side_effect=RuntimeError("offline"))) as cycle:
            task = asyncio.create_task(_monitor_loop(stop_event))
            try:
                await asyncio.sleep(0)
                self.assertEqual(cycle.await_count, 1)
                stop_event.set()
                await wait_for(task, timeout=0.5)
            finally:
                if not task.done():
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
        cycle.assert_awaited_once_with(stop_event=stop_event)

    async def test_monitor_propagates_cancellation_without_starting_another_scan(self):
        stop_event = asyncio.Event()
        with (
            patch("src.audio_recovery.run_audio_recovery_cycle", new=AsyncMock(side_effect=asyncio.CancelledError)) as cycle,
            patch("src.audio_recovery.asyncio.wait_for", new=AsyncMock()) as wait,
        ):
            with self.assertRaises(asyncio.CancelledError):
                await _monitor_loop(stop_event)
        cycle.assert_awaited_once_with(stop_event=stop_event)
        wait.assert_not_awaited()

    async def test_non_public_video_stays_registered_until_it_becomes_public(self):
        state = {
            "enabled": True,
            "retry_cooldown_seconds": 0,
            "entries": {
                "channel": {
                    "video": {
                        "audio_path": "unused.mp3",
                        "languages": ["en"],
                    }
                }
            },
            "channel_refresh_alerts": {},
        }
        visibility = Mock(
            side_effect=[
                ({"video": False}, set()),
                ({"video": True}, set()),
            ]
        )
        fetch = Mock(
            return_value={
                "videoTranslations": [
                    {"videoId": "video", "translations": []}
                ],
                "audioTracks": [],
            }
        )

        with (
            patch(
                "src.audio_recovery._get_registered_video_scan_statuses",
                visibility,
            ),
            patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
            patch("src.audio_recovery._load_state", return_value=state),
            patch("src.audio_recovery.state_manager.save_state", return_value=True),
            patch.object(
                __import__(
                    "src.audio_recovery", fromlist=["update_audio_module"]
                ).update_audio_module,
                "_get_video_translation_payload",
                fetch,
            ),
        ):
            private_result = await run_audio_recovery_cycle(now=1000)
            public_result = await run_audio_recovery_cycle(now=2000)

        fetch.assert_called_once_with(["video"], "channel")
        self.assertEqual(private_result["deferred_video_scope"], 1)
        self.assertEqual(public_result["deferred_video_scope"], 0)
        self.assertIn("video", state["entries"]["channel"])


    async def test_new_registration_scans_immediately_despite_legacy_grace_setting(self):
        state = {
            "enabled": True,
            "retry_cooldown_seconds": 0,
            "initial_grace_seconds": 15 * 60,
            "entries": {
                "channel": {
                    "video": {
                        "audio_path": "unused.mp3",
                        "languages": ["en"],
                        "registered_at": 1000,
                    }
                }
            },
            "channel_refresh_alerts": {},
        }
        fetch = Mock(
            return_value={
                "videoTranslations": [{"videoId": "video"}],
                "audioTracks": [
                    {
                        "videoId": "video",
                        "audioTrackId": "healthy-en",
                        "language": "en",
                        "source": "AUDIO_TRACK_SOURCE_CREATOR",
                        "audioContentTypeString": "dubbed",
                        "status": "AUDIO_TRACK_STATUS_READY",
                    }
                ],
            }
        )
        with (
            patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
            patch("src.audio_recovery._load_state", return_value=state),
            patch("src.audio_recovery.state_manager.save_state", return_value=True),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "_get_video_translation_payload",
                fetch,
            ),
        ):
            result = await run_audio_recovery_cycle(now=1000)
            due_result = await run_audio_recovery_cycle(now=1001)

        self.assertEqual(fetch.call_count, 2)
        self.assertTrue(all(call.args == (["video"], "channel") for call in fetch.call_args_list))
        self.assertEqual(result["deferred_initial_grace"], 0)
        self.assertEqual(result["repaired"], 0)
        self.assertEqual(due_result["deferred_initial_grace"], 0)
        self.assertEqual(due_result["repaired"], 0)

    async def test_read_only_recovery_scan_does_not_hold_mutation_guard(self):
        state = {
            "enabled": True,
            "retry_cooldown_seconds": 0,
            "entries": {
                "channel": {
                    "video": {
                        "audio_path": "unused.mp3",
                        "languages": ["en"],
                    }
                }
            },
            "channel_refresh_alerts": {},
        }

        def fetch(_video_ids, _channel_id):
            self.assertFalse(get_audio_mutation_guard("channel").locked())
            return {
                "videoTranslations": [{"videoId": "video"}],
                "audioTracks": [
                    {
                        "videoId": "video",
                        "audioTrackId": "healthy-en",
                        "language": "en",
                        "source": "AUDIO_TRACK_SOURCE_CREATOR",
                        "audioContentTypeString": "dubbed",
                        "status": "AUDIO_TRACK_STATUS_READY",
                    }
                ],
            }

        with (
            patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
            patch("src.audio_recovery._load_state", return_value=state),
            patch("src.audio_recovery.state_manager.save_state", return_value=True),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "_get_video_translation_payload",
                side_effect=fetch,
            ),
        ):
            result = await run_audio_recovery_cycle(now=2000)

        self.assertEqual(result["repaired"], 0)
        self.assertFalse(get_audio_mutation_guard("channel").locked())

    async def test_recovery_on_one_channel_continues_while_another_is_busy(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.write_bytes(b"source")
            state = {
                "enabled": True,
                "retry_cooldown_seconds": 0,
                "entries": {
                    channel_id: {
                        video_id: {
                            "audio_path": str(source),
                            "languages": ["en"],
                            "repeat_times": 1,
                            "extra_minutes": 0,
                            "attempts": {},
                        }
                    }
                    for channel_id, video_id in (
                        ("channel-a", "video-a"),
                        ("channel-b", "video-b"),
                    )
                },
                "channel_refresh_alerts": {},
            }

            def fetch(video_ids, _channel_id):
                return {
                    "videoTranslations": [
                        {
                            "videoId": video_id,
                            "translations": [
                                {
                                    "languageCode": "en",
                                    "audioTranslation": {
                                        "status": "AUDIO_TRACK_STATUS_FAILED"
                                    },
                                }
                            ],
                        }
                        for video_id in video_ids
                    ],
                    "audioTracks": [],
                }

            def render_audio(*, output_file, **_kwargs):
                Path(output_file).write_bytes(b"rendered")

            async def run_retry(operation, **_kwargs):
                return operation()

            added = Mock(return_value=200)
            scanned_channels = []
            original_fetch = fetch

            def record_fetch(video_ids, channel_id):
                scanned_channels.append(channel_id)
                return original_fetch(video_ids, channel_id)

            busy_guard = get_audio_mutation_guard("channel-b")
            busy_guard.acquire()
            try:
                with (
                    patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
                    patch("src.audio_recovery._load_state", return_value=state),
                    patch("src.audio_recovery.state_manager.save_state", return_value=True),
                    patch("src.audio_recovery._record_recovery_attempt"),
                    patch.object(
                        __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                        "_get_video_translation_payload",
                        side_effect=record_fetch,
                    ),
                    patch.object(
                        __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                        "_get_video_info",
                        return_value=SimpleNamespace(duration_ms=60_000),
                    ),
                    patch.object(
                        __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                        "add",
                        added,
                    ),
                    patch("src.audio_recovery.multiply_audio", side_effect=render_audio),
                    patch(
                        "src.audio_recovery.call_audio_update_with_retry",
                        new=AsyncMock(side_effect=run_retry),
                    ),
                ):
                    result = await run_audio_recovery_cycle(now=2000)
            finally:
                busy_guard.release()

        self.assertEqual(result["repaired"], 1)
        self.assertEqual(result["deferred_busy"], 1)
        self.assertEqual(scanned_channels, ["channel-a"])
        self.assertEqual(added.call_args.kwargs["id_video"], "video-a")

    async def test_clearing_registry_cancels_running_recovery_snapshot(self):
        stored = {
            "enabled": True,
            "retry_cooldown_seconds": 0,
            "entries": {
                "channel": {
                    "video": {
                        "audio_path": "unused.mp3",
                        "languages": ["en"],
                    }
                }
            },
            "channel_refresh_alerts": {},
        }

        def load(_name):
            return stored.copy()

        def save(_name, state):
            stored.clear()
            stored.update(state)
            return True

        def fetch(_video_ids, _channel_id):
            clear_audio_recovery_registry()
            return {
                "videoTranslations": [
                    {
                        "videoId": "video",
                        "translations": [
                            {
                                "languageCode": "en",
                                "audioTranslation": {
                                    "status": "AUDIO_TRACK_STATUS_FAILED"
                                },
                            }
                        ],
                    }
                ],
                "audioTracks": [],
            }

        added = Mock()
        deleted = Mock()
        with (
            patch("src.audio_recovery.state_manager.load_state", side_effect=load),
            patch("src.audio_recovery.state_manager.save_state", side_effect=save),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "_get_video_translation_payload",
                side_effect=fetch,
            ),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "delete_track_ids",
                deleted,
            ),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "add",
                added,
            ),
        ):
            result = await run_audio_recovery_cycle(now=2000)

        self.assertTrue(result["cancelled_by_clear"])
        self.assertEqual(stored["entries"], {})
        deleted.assert_not_called()
        added.assert_not_called()

    async def test_non_token_scan_error_does_not_request_login(self):
        stored = {
            "enabled": True,
            "retry_cooldown_seconds": 0,
            "entries": {
                "channel": {
                    "video": {
                        "audio_path": "unused.mp3",
                        "languages": ["en"],
                    }
                }
            },
            "channel_refresh_alerts": {},
        }

        def load(_name):
            return stored.copy()

        def save(_name, state):
            stored.clear()
            stored.update(state)
            return True

        with (
            patch("src.audio_recovery.state_manager.load_state", side_effect=load),
            patch("src.audio_recovery.state_manager.save_state", side_effect=save),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "_get_video_translation_payload",
                side_effect=TimeoutError("temporary network timeout"),
            ),
        ):
            result = await run_audio_recovery_cycle(now=2000)

        self.assertEqual(stored["channel_refresh_alerts"], {})
        self.assertEqual(result["reauth_required"], [])

    async def test_token_failure_creates_alert_without_mutating_audio(self):
        stored = {
            "enabled": True,
            "retry_cooldown_seconds": 0,
            "entries": {
                "channel": {
                    "video": {
                        "audio_path": "unused.mp3",
                        "languages": ["en"],
                    }
                }
            },
            "channel_refresh_alerts": {},
        }

        def load(_name):
            return stored.copy()

        def save(_name, state):
            stored.clear()
            stored.update(state)
            return True

        deleted = Mock()
        added = Mock()
        with (
            patch("src.audio_recovery.state_manager.load_state", side_effect=load),
            patch("src.audio_recovery.state_manager.save_state", side_effect=save),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "_get_video_translation_payload",
                side_effect=Exception(
                    "Retry failed: encodedReauthProofToken vẫn không có"
                ),
            ),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "delete_track_ids",
                deleted,
            ),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "add",
                added,
            ),
        ):
            result = await run_audio_recovery_cycle(now=2000)

        self.assertEqual(set(stored["channel_refresh_alerts"]), {"channel"})
        self.assertEqual(result["reauth_required"], ["channel"])
        deleted.assert_not_called()
        added.assert_not_called()

    async def test_cycle_never_contacts_youtube_while_refresh_alert_is_pending(self):
        state = {
            "enabled": True,
            "retry_cooldown_seconds": 0,
            "entries": {
                "channel": {
                    "video": {
                        "audio_path": "unused.mp3",
                        "languages": ["en"],
                    }
                }
            },
            "channel_refresh_alerts": {
                "channel": {"requested_at": 1000}
            },
        }
        fetch = Mock()
        with (
            patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
            patch("src.audio_recovery._load_state", return_value=state),
            patch("src.audio_recovery.state_manager.save_state", return_value=True),
            patch.object(
                __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                "_get_video_translation_payload",
                fetch,
            ),
        ):
            result = await run_audio_recovery_cycle(now=2000)

        fetch.assert_not_called()
        self.assertEqual(result["repaired"], 0)
        self.assertEqual(result["failed"], 0)

    async def test_cycle_skips_partial_failure_then_repairs_when_all_dubs_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.mp3"
            source.write_bytes(b"source")
            state = {
                "enabled": True,
                "retry_cooldown_seconds": 0,
                "entries": {
                    "channel": {
                        "video": {
                            "audio_path": str(source),
                            "languages": ["en", "es", "fr"],
                            "repeat_times": 1,
                            "extra_minutes": 0,
                            "attempts": {},
                        }
                    }
                },
            }
            payload = {
                "videoTranslations": [{"videoId": "video", "translations": []}],
                "audioTracks": [
                    {
                        "videoId": "video",
                        "audioTrackId": "audio-en",
                        "language": "en",
                        "source": "AUDIO_TRACK_SOURCE_CREATOR",
                        "audioContentTypeString": "dubbed",
                        "status": "AUDIO_TRACK_STATUS_READY",
                    },
                    {
                        "videoId": "video",
                        "audioTrackId": "failed-es",
                        "language": "es",
                        "source": "AUDIO_TRACK_SOURCE_CREATOR",
                        "audioContentTypeString": "dubbed",
                        "status": "AUDIO_TRACK_STATUS_FAILED",
                    },
                ],
            }
            deleted = Mock(return_value=200)
            added = Mock(return_value=200)

            async def run_retry(operation, **_kwargs):
                return operation()

            def render_audio(*, output_file, **_kwargs):
                Path(output_file).write_bytes(b"rendered")

            with (
                patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
                patch("src.audio_recovery._load_state", return_value=state),
                patch("src.audio_recovery.state_manager.save_state", return_value=True),
                patch("src.audio_recovery._record_recovery_attempt"),
                patch.object(
                    __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                    "_get_video_translation_payload",
                    return_value=payload,
                ),
                patch.object(
                    __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                    "_get_video_info",
                    return_value=SimpleNamespace(duration_ms=60_000),
                ),
                patch.object(
                    __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                    "delete_track_ids",
                    deleted,
                ),
                patch.object(
                    __import__("src.audio_recovery", fromlist=["update_audio_module"]).update_audio_module,
                    "add",
                    added,
                ),
                patch("src.audio_recovery.multiply_audio", side_effect=render_audio),
                patch("src.audio_recovery.call_audio_update_with_retry", new=AsyncMock(side_effect=run_retry)),
            ):
                partial = await run_audio_recovery_cycle(now=1000)
                self.assertEqual(partial["repaired"], 0)
                self.assertEqual(partial["failed"], 0)
                deleted.assert_not_called()
                added.assert_not_called()
                self.assertIn("video", state["entries"]["channel"])

                payload["audioTracks"][0]["status"] = "AUDIO_TRACK_STATUS_FAILED"
                result = await run_audio_recovery_cycle(now=2000)

        self.assertEqual(result["repaired"], 3)
        self.assertEqual(result["failed"], 0)
        self.assertEqual([call.args for call in deleted.call_args_list], [
            ("video", "channel", ["audio-en"]),
            ("video", "channel", ["failed-es"]),
        ])
        self.assertEqual(
            [call.kwargs["language"] for call in added.call_args_list],
            ["en", "es", "fr"],
        )
        for call in added.call_args_list:
            progress = call.kwargs["progress"]
            self.assertEqual(progress["sent"], 0)
            self.assertGreater(progress["total"], 0)
            self.assertEqual(progress["status"], "starting" if call.kwargs["language"] == "fr" else "deleting")

        runtime_status = get_audio_recovery_runtime_status()
        self.assertFalse(runtime_status["active"])
        self.assertEqual(runtime_status["phase"], "idle")
        self.assertEqual(runtime_status["repaired"], 3)
        self.assertEqual(runtime_status["failed"], 0)
        self.assertEqual(runtime_status["upload_sent"], 0)
        self.assertEqual(runtime_status["upload_total"], 0)

    async def test_stale_processing_is_rechecked_after_preparing_file_and_good_audio_is_preserved(self):
        from src.audio_recovery import update_audio_module
        for fresh_state in ("processing", "ready", "healthy-duplicate", "new-track", "unreadable"):
            with self.subTest(fresh_state=fresh_state), tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "source.mp3"
                source.write_bytes(b"source")
                entry = {"audio_path": str(source), "languages": ["es", "it"],
                         "processing_observations": {"it": {
                             "track_ids": ["stuck-it"], "first_seen_at": 1000,
                             "last_seen_at": 1000, "scan_count": 10,
                         }}}
                state = {"enabled": True, "entries": {"channel": {"video": entry}}}

                def payload(status="PROCESSING", track_id="stuck-it"):
                    return {"videoTranslations": [{"videoId": "video", "translations": [
                        {"languageCode": "en", "audioTranslation": {
                            "audioTrackId": "published-en", "publishStatus": "PUBLISHED"}},
                        {"languageCode": "es", "audioTranslation": {
                            "audioTrackId": "deleted-es", "statusLabel": "Deleted"}},
                        {"languageCode": "it", "audioTranslation": {
                            "audioTrackId": track_id, "status": "AUDIO_TRACK_STATUS_" + status}},
                    ]}], "audioTracks": []}

                fresh = (payload() if fresh_state == "processing" else
                         payload("READY") if fresh_state == "ready" else
                         payload(track_id="new-it") if fresh_state == "new-track" else {})
                if fresh_state == "healthy-duplicate":
                    fresh = payload()
                    fresh["videoTranslations"][0]["translations"].append({
                        "languageCode": "it", "audioTranslation": {
                            "audioTrackId": "ready-it", "publishStatus": "PUBLISHED"},
                    })

                def render_audio(*, output_file, **_kwargs):
                    Path(output_file).write_bytes(b"rendered")

                with (
                    patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
                    patch("src.audio_recovery._load_state", return_value=state),
                    patch("src.audio_recovery.state_manager.save_state", return_value=True),
                    patch.object(update_audio_module, "_get_video_translation_payload", side_effect=[payload(), fresh]) as fetch,
                    patch.object(update_audio_module, "_get_video_info", return_value=SimpleNamespace(duration_ms=60000)),
                    patch.object(update_audio_module, "delete_track_ids", return_value=200) as delete,
                    patch.object(update_audio_module, "add", return_value=200) as add,
                    patch("src.audio_recovery.multiply_audio", side_effect=render_audio),
                ):
                    result = await run_audio_recovery_cycle(now=1000 + DEFAULT_STALE_PROCESSING_SECONDS)

                self.assertEqual(fetch.call_count, 2)
                if fresh_state == "processing":
                    self.assertEqual(result["repaired"], 1)
                    delete.assert_called_once_with("video", "channel", ["stuck-it"])
                    self.assertEqual(add.call_args.kwargs["language"], "it")
                    self.assertEqual(result["channel_results"][0]["healthy_skipped"], 0)
                else:
                    self.assertEqual(result["repaired"], 0)
                    delete.assert_not_called()
                    add.assert_not_called()
                self.assertEqual(result["failed"], int(fresh_state == "unreadable"))

    async def test_cycle_immediately_retries_missing_or_deleted_audio_but_preserves_processing(self):
        from src.audio_recovery import update_audio_module

        for failed_es in (False, True):
            with self.subTest(failed_es=failed_es), tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "source.mp3"
                source.write_bytes(b"source")
                state = {
                    "enabled": True, "initial_grace_seconds": 0,
                    "retry_cooldown_seconds": 15 * 60,
                    "entries": {"channel": {"video": {
                        "audio_path": str(source), "languages": ["en", "es"],
                        "repeat_times": 1, "attempts": {},
                    }}},
                }
                payload = {
                    "videoTranslations": [{"videoId": "video", "translations": [
                        {"languageCode": language, "audioTranslation": {"statusLabel": "-"}}
                        for language in ("en", "es", "fr")
                    ]}],
                    "audioTracks": [{
                        "videoId": "video", "audioTrackId": "original", "language": "ak",
                        "source": "AUDIO_TRACK_SOURCE_UPLOAD", "audioContentTypeString": "original",
                        "status": "AUDIO_TRACK_STATUS_READY",
                    }],
                }
                if failed_es:
                    payload["videoTranslations"][0]["translations"][1]["audioTranslation"] = {
                        "audioTrackId": "deleted-es", "statusLabel": "Đã xoá",
                    }

                def render_audio(*, output_file, **_kwargs):
                    Path(output_file).write_bytes(b"rendered")

                async def run_retry(operation, **_kwargs):
                    return operation()

                with (
                    patch("src.audio_recovery.get_audio_recovery_state", return_value=state),
                    patch("src.audio_recovery._load_state", return_value=state),
                    patch("src.audio_recovery.state_manager.save_state", return_value=True),
                    patch.object(update_audio_module, "_get_video_translation_payload", return_value=payload),
                    patch.object(update_audio_module, "_get_video_info", return_value=SimpleNamespace(duration_ms=60000)) as info,
                    patch.object(update_audio_module, "delete_track_ids", return_value=200) as delete,
                    patch.object(update_audio_module, "add", return_value=200) as add,
                    patch("src.audio_recovery.multiply_audio", side_effect=render_audio) as render,
                    patch("src.audio_recovery.call_audio_update_with_retry", new=AsyncMock(side_effect=run_retry)),
                ):
                    result = await run_audio_recovery_cycle(now=2000)
                    # Re-read Studio on each cycle; missing/deleted audio can
                    # be repaired immediately even after a recent submission.
                    repeated = await run_audio_recovery_cycle(now=2000)
                    for item in payload["videoTranslations"][0]["translations"]:
                        if item["languageCode"] in ("en", "es"):
                            item["audioTranslation"] = {
                                "audioTrackId": f"processing-{item['languageCode']}",
                                "status": "AUDIO_TRACK_STATUS_PROCESSING",
                            }
                    processing = await run_audio_recovery_cycle(now=2001)

                self.assertEqual(result["repaired"], 2)
                self.assertEqual(result["failed"], 0)
                self.assertEqual(result["unreadable"], [])
                self.assertEqual(repeated["repaired"], 2)
                self.assertEqual(repeated["failed"], 0)
                self.assertEqual(processing["repaired"], 0)
                self.assertEqual(processing["failed"], 0)
                self.assertEqual([call.kwargs["language"] for call in add.call_args_list], ["en", "es", "en", "es"])
                self.assertEqual(info.call_count, 2)
                self.assertEqual(render.call_count, 2)
                if failed_es:
                    self.assertEqual(delete.call_count, 2)
                    self.assertTrue(all(call.args == ("video", "channel", ["deleted-es"]) for call in delete.call_args_list))
                else:
                    delete.assert_not_called()
                attempts = state["entries"]["channel"]["video"]["attempts"]
                self.assertEqual(set(attempts), {"en", "es"})
                self.assertTrue(all(attempt["succeeded"] for attempt in attempts.values()))


if __name__ == "__main__":
    unittest.main()
