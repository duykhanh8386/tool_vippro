import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from src.audio_recovery import (
    DEFAULT_RECOVERY_INTERVAL_SECONDS,
    acknowledge_channel_refresh,
    build_audio_recovery_plan,
    clear_audio_recovery_registry,
    get_channel_refresh_alerts,
    mark_channel_refresh_required,
    register_audio_recovery,
    run_audio_recovery_cycle,
)


class AudioRecoveryPlanTests(unittest.TestCase):
    def test_default_monitor_interval_is_six_hours(self):
        self.assertEqual(DEFAULT_RECOVERY_INTERVAL_SECONDS, 6 * 60 * 60)

    def test_plan_ignores_source_lock_and_healthy_or_processing_dubs(self):
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
        self.assertEqual(
            actions,
            [
                {
                    "video_id": "video",
                    "language": "es",
                    "track_ids": ["failed-es"],
                    "reason": "terminal",
                },
                {
                    "video_id": "video",
                    "language": "fr",
                    "track_ids": [],
                    "reason": "missing",
                },
            ],
        )

    def test_omitted_video_is_unreadable_not_treated_as_missing_audio(self):
        actions, unreadable = build_audio_recovery_plan(
            {"videoTranslations": [], "audioTracks": []},
            {"video": {"languages": ["en"]}},
            ["video"],
        )

        self.assertEqual(actions, [])
        self.assertEqual(unreadable, {"video"})


class AudioRecoveryRegistryTests(unittest.TestCase):
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


class AudioRecoveryCycleTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_cycle_repairs_only_failed_and_missing_languages(self):
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
                result = await run_audio_recovery_cycle(now=1000)

        self.assertEqual(result["repaired"], 2)
        self.assertEqual(result["failed"], 0)
        deleted.assert_called_once_with("video", "channel", ["failed-es"])
        self.assertEqual(
            [call.kwargs["language"] for call in added.call_args_list],
            ["es", "fr"],
        )


if __name__ == "__main__":
    unittest.main()
