import unittest

from src import audio_recovery as recovery
from src.audio_description_recovery import registry_entry_complete, registry_work_due, track_state_prefix
from src.module.audio_module import AudioUpdateError
from test_registry_descriptions import RegistryAudioFixture, audio_track, response


class RegistryProcessingSuccessTests(RegistryAudioFixture, unittest.IsolatedAsyncioTestCase):
    def prepare(self, kind):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        recovery.set_audio_recovery_audio_types([kind])
        self.payload = response([audio_track("en", kind, "PROCESSING")])
        self.add.reset_mock()
        self.delete_ids.reset_mock()

    async def test_processing_counts_as_success_and_is_never_replaced_for_its_age(self):
        for kind in ("dubbed", "descriptive"):
            with self.subTest(kind=kind):
                self.prepare(kind)
                for now in (2000, 2031, 9201, 20000):
                    result = await recovery.run_audio_recovery_cycle(now=now)
                    self.assertTrue(registry_entry_complete(self.saved_entry(), [kind]))
                    self.assertEqual(result["failed"], 0)
                    self.assertEqual(result["processing_warnings"], [])
                self.add.assert_not_called()
                self.delete_ids.assert_not_called()
                self.assertTrue(registry_work_due(self.saved_entry(), 20031, [kind]))

    async def test_later_youtube_failure_reopens_success_and_reports_the_real_error(self):
        for kind in ("dubbed", "descriptive"):
            with self.subTest(kind=kind):
                self.prepare(kind)
                await recovery.run_audio_recovery_cycle(now=2000)
                self.assertTrue(registry_entry_complete(self.saved_entry(), [kind]))
                self.payload = response([audio_track("en", kind, "FAILED")])
                self.delete_ids.side_effect = None
                self.delete_ids.return_value = 200
                self.add.side_effect = AudioUpdateError("YouTube rejected audio", status_code=403)
                result = await recovery.run_audio_recovery_cycle(now=2031)
                self.assertEqual(result["failed"], 1)
                self.assertFalse(registry_entry_complete(self.saved_entry(), [kind]))
                attempt = self.saved_entry()[track_state_prefix(kind) + "_attempts"]["en"]
                self.assertFalse(attempt["succeeded"])
                self.assertIn("YouTube rejected", attempt["message"])

    async def test_ready_after_processing_finishes_monitoring_without_another_upload(self):
        self.prepare("descriptive")
        await recovery.run_audio_recovery_cycle(now=2000)
        self.payload = response([audio_track("en", status="READY")])
        await recovery.run_audio_recovery_cycle(now=2031)
        self.assertTrue(registry_entry_complete(self.saved_entry(), ["descriptive"]))
        self.assertFalse(registry_work_due(self.saved_entry(), 2100, ["descriptive"]))
        self.add.assert_not_called()

    async def test_unknown_status_does_not_invent_success_or_replace_the_track(self):
        self.prepare("descriptive")
        self.payload = response([audio_track("en", status="UNSPECIFIED")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertFalse(registry_entry_complete(self.saved_entry(), ["descriptive"]))
        self.add.assert_not_called()
        self.delete_ids.assert_not_called()

    async def test_missing_snapshot_after_acceptance_does_not_undo_success_or_upload_a_duplicate(self):
        for kind in ("dubbed", "descriptive"):
            with self.subTest(kind=kind):
                self.prepare(kind)
                await recovery.run_audio_recovery_cycle(now=2000)
                self.payload = response()
                await recovery.run_audio_recovery_cycle(now=2031)
                self.assertTrue(registry_entry_complete(self.saved_entry(), [kind]))
                self.add.assert_not_called()
                self.delete_ids.assert_not_called()

    async def test_processing_clears_a_previous_failure_message(self):
        self.prepare("descriptive")
        state = self.manager.load_state("audio_recovery")
        state["entries"]["channel"]["video"]["description_attempts"] = {
            "en": {"succeeded": False, "message": "old error", "count": 1}
        }
        self.manager.save_state("audio_recovery", state)
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertTrue(self.saved_entry()["description_attempts"]["en"]["succeeded"])
        self.assertNotIn("old error", self.saved_entry()["description_attempts"]["en"]["message"])
