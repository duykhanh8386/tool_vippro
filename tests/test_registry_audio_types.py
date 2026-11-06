import copy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src import audio_recovery as recovery
from src.audio_description_recovery import enabled_audio_types, registry_entry_complete
from src.module.audio_module import AudioUpdateError, UpdateAudioModule
from test_registry_descriptions import RegistryAudioFixture, audio_track, response
from test_audio_module import Response


class RegistryAudioTypeTests(RegistryAudioFixture, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.assertTrue(recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"]))
        self.events = []
        self.upload_status = "READY"
        self.add.side_effect = self.upload
        self.delete_ids.side_effect = self.delete_tracks

    def upload(self, **kwargs):
        kind, language = kwargs["audio_content_type"], kwargs["language"]
        self.assertIn(kind, enabled_audio_types(recovery.get_audio_recovery_state()))
        self.assertEqual(Path(kwargs["file_name"]).read_bytes(), self.source.read_bytes())
        self.assertTrue(recovery.get_audio_mutation_guard("channel").locked())
        self.events.append(("add", kind, language))
        self.payload["audioTracks"].append(audio_track(language, kind, self.upload_status))
        return 200

    def delete_tracks(self, video_id, channel_id, track_ids):
        self.assertEqual((video_id, channel_id), ("video", "channel"))
        self.assertTrue(recovery.get_audio_mutation_guard("channel").locked())
        for track in self.payload["audioTracks"]:
            if track["audioTrackId"] in track_ids:
                self.assertIn(track["audioContentTypeString"], enabled_audio_types(recovery.get_audio_recovery_state()))
                self.assertNotEqual(track["audioContentTypeString"], "original")
        self.events.append(("delete", tuple(track_ids)))
        self.payload["audioTracks"] = [t for t in self.payload["audioTracks"] if t["audioTrackId"] not in track_ids]
        return 200

    def selected(self):
        return enabled_audio_types(recovery.get_audio_recovery_state())

    async def test_new_and_legacy_state_defaults_to_both_types(self):
        state = recovery.get_audio_recovery_state()
        state.pop("audio_content_types")
        self.manager.save_state("audio_recovery", state)
        self.assertEqual(self.selected(), ("dubbed", "descriptive"))

    async def test_all_switch_combinations_survive_restart_without_enabling_master_or_losing_entries(self):
        recovery.set_audio_recovery_enabled(False)
        entries = copy.deepcopy(recovery.get_audio_recovery_state()["entries"])
        for selected in ([], ["dubbed"], ["descriptive"], ["dubbed", "descriptive"]):
            with self.subTest(selected=selected):
                self.assertTrue(recovery.set_audio_recovery_audio_types(selected))
                self.manager._conn.close()
                self.manager._conn = None
                self.assertEqual(list(self.selected()), selected)
                self.assertFalse(recovery.is_audio_recovery_enabled())
                self.assertEqual(recovery.get_audio_recovery_state()["entries"], entries)

    async def test_dubbed_only_repairs_language_audio_and_never_touches_descriptions(self):
        recovery.set_audio_recovery_audio_types(["dubbed"])
        self.payload = response([audio_track("en", "dubbed", "FAILED"), audio_track("en", status="FAILED")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [
            ("delete", ("video-en-dubbed",)), ("add", "dubbed", "en"), ("add", "dubbed", "vi"),
        ])
        self.assertNotIn("description_attempts", self.saved_entry())
        await recovery.run_audio_recovery_cycle(now=2031)
        self.assertTrue(registry_entry_complete(self.saved_entry(), self.selected()))
        self.fetch.reset_mock()
        await recovery.run_audio_recovery_cycle(now=2100)
        self.fetch.assert_not_called()

    async def test_registration_preserves_switches_and_each_types_existing_progress(self):
        state = recovery.get_audio_recovery_state()
        entry = state["entries"]["channel"]["video"]
        entry.update(dubbed_completed_languages=["en"], description_completed_languages=["vi"],
                     dubbed_prepared_for_description=["en"])
        self.manager.save_state("audio_recovery", state)
        recovery.set_audio_recovery_audio_types([])
        recovery.set_audio_recovery_enabled(False)
        self.assertTrue(recovery.register_audio_recovery(
            channel_id="channel", video_id="video", audio_path=str(self.source),
            languages=["fr"], repeat_times=1, extra_minutes=0, merge_languages=True,
        ))
        self.assertEqual(self.selected(), ())
        self.assertFalse(recovery.is_audio_recovery_enabled())
        self.assertEqual(self.saved_entry()["dubbed_completed_languages"], ["en"])
        self.assertEqual(self.saved_entry()["description_completed_languages"], ["vi"])
        self.assertEqual(self.saved_entry()["dubbed_prepared_for_description"], ["en"])
        self.assertEqual(self.saved_entry()["languages"], ["en", "vi", "fr"])

    async def test_descriptive_only_ignores_failed_language_audio(self):
        recovery.set_audio_recovery_audio_types(["descriptive"])
        self.payload = response([audio_track("en", "dubbed", "FAILED"), audio_track("en", status="FAILED")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [
            ("delete", ("video-en-descriptive",)), ("add", "descriptive", "en"), ("add", "descriptive", "vi"),
        ])
        self.assertNotIn("dubbed_attempts", self.saved_entry())

    async def test_both_types_upload_each_language_and_its_description_before_the_next_language(self):
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [
            ("add", "dubbed", "en"), ("add", "descriptive", "en"),
            ("add", "dubbed", "vi"), ("add", "descriptive", "vi"),
        ])
        self.assertTrue(registry_entry_complete(self.saved_entry(), self.selected()))
        await recovery.run_audio_recovery_cycle(now=2031)
        self.assertTrue(registry_entry_complete(self.saved_entry(), self.selected()))

    async def test_both_types_preserve_healthy_language_audio_and_replace_only_failed_description(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"])
        self.payload = response([audio_track("en", "dubbed"), audio_track("en", status="FAILED")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [
            ("delete", ("video-en-descriptive",)), ("add", "descriptive", "en"),
        ])

    async def test_description_follows_completed_upload_even_while_youtube_is_processing(self):
        self.upload_status = "PROCESSING"
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [
            ("add", "dubbed", "en"), ("add", "descriptive", "en"),
            ("add", "dubbed", "vi"), ("add", "descriptive", "vi"),
        ])
        for track in self.payload["audioTracks"]:
            track["status"] = "AUDIO_TRACK_STATUS_READY"
        await recovery.run_audio_recovery_cycle(now=2031)
        self.assertEqual(len(self.events), 4)
        self.assertTrue(registry_entry_complete(self.saved_entry(), self.selected()))

    def use_verified_backend(self, normal_status="PENDING", publish=True):
        module = UpdateAudioModule()
        self.add.side_effect = module.add
        self.stack.enter_context(patch.object(module, "_get_video_translation_payload",
                                             side_effect=lambda *_: copy.deepcopy(self.payload)))
        self.stack.enter_context(patch("src.module.audio_module.get_channels_info",
                                      return_value=SimpleNamespace(cookies=[])))
        self.stack.enter_context(patch.object(module, "_get_session_token", return_value="token"))
        self.stack.enter_context(patch.object(module, "_upload_http", return_value=("https://session", "resource")))
        self.stack.enter_context(patch.object(module, "_next_upload_http", return_value="final"))
        self.stack.enter_context(patch("src.module.audio_module.wait_interruptibly"))

        def register(**kwargs):
            kind, language = kwargs["audio_content_type"], kwargs["language"]
            self.events.append(("add", kind, language))
            if publish:
                self.payload["audioTracks"].append(audio_track(
                    language, kind, normal_status if kind == "dubbed" else "PROCESSED",
                ))
            return 200

        self.stack.enter_context(patch.object(module, "_update", side_effect=register))

    async def test_real_backend_verifies_each_language_then_its_description(self):
        self.use_verified_backend()
        result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [("add", kind, lang) for lang in ("en", "vi") for kind in ("dubbed", "descriptive")])
        report = result["channel_results"][0]
        self.assertEqual(report["submitted"], 4)
        self.assertEqual(report["processing_submitted"], 2)
        self.assertEqual(report["published_submitted"], 2)
        self.assertIn("AUDIO_TRACK_STATUS_PENDING", self.saved_entry()["dubbed_attempts"]["en"]["message"])

    async def test_verified_normal_processing_failure_is_reported_and_description_still_gets_its_attempt(self):
        self.use_verified_backend(normal_status="FAILED")
        result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [("add", kind, lang) for lang in ("en", "vi") for kind in ("dubbed", "descriptive")])
        self.assertEqual((result["repaired"], result["failed"]), (2, 2))
        self.assertEqual(result["channel_results"][0]["submitted"], 2)
        self.assertFalse(self.saved_entry()["dubbed_attempts"]["en"]["succeeded"])
        self.assertTrue(self.saved_entry()["description_attempts"]["en"]["succeeded"])

    async def test_http_success_with_no_new_tracks_does_not_increment_submitted(self):
        self.use_verified_backend(publish=False)
        result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual((result["repaired"], result["failed"]), (0, 4))
        self.assertEqual(result["channel_results"][0]["submitted"], 0)
        self.assertFalse(self.saved_entry()["description_attempts"]["en"]["succeeded"])

    async def test_early_registered_dub_failure_does_not_block_its_description(self):
        def upload(**kwargs):
            kind, language = kwargs["audio_content_type"], kwargs["language"]
            if kind == "dubbed":
                self.events.append(("add", kind, language))
                self.payload["audioTracks"].append(audio_track(language, kind, "FAILED"))
                kwargs["progress"].update(registered=True, file_finalized=False, server_rejected=True,
                                          studio_state="failed", track_status="AUDIO_TRACK_STATUS_FAILED")
                raise AudioUpdateError("server rejected track during transfer")
            return self.upload(**kwargs)

        self.add.side_effect = upload
        result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [("add", kind, lang) for lang in ("en", "vi") for kind in ("dubbed", "descriptive")])
        self.assertEqual((result["repaired"], result["failed"]), (2, 2))
        self.assertFalse(self.saved_entry()["dubbed_attempts"]["en"]["succeeded"])
        self.assertTrue(self.saved_entry()["description_attempts"]["en"]["succeeded"])

    async def test_failed_description_is_not_added_until_youtube_commits_its_deletion(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"])
        self.payload = response([audio_track("en", "dubbed"), audio_track("en", status="FAILED")])
        module = UpdateAudioModule()
        self.delete_ids.side_effect = module.delete_track_ids
        reads = []

        def committed_inventory(*_args):
            reads.append(len(reads))
            self.assertFalse(any(event[0] == "add" for event in self.events))
            if len(reads) == 2:
                self.payload["audioTracks"] = [t for t in self.payload["audioTracks"] if t["audioContentTypeString"] != "descriptive"]
            return copy.deepcopy(self.payload)

        with (
            patch("src.module.audio_module.get_channels_info", return_value=SimpleNamespace(
                id="channel", role="OWNER", delegated_session_id="owner", cookies=[],
            )),
            patch("src.module.audio_module.studio_authorization_header", return_value="auth"),
            patch.object(module, "_get_session_token", return_value="token"),
            patch("src.module.audio_module.post_with_stop", return_value=Response(200)) as post,
            patch.object(module, "_get_video_translation_payload", side_effect=committed_inventory),
            patch("src.module.audio_module.wait_interruptibly"),
        ):
            result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(len(reads), 2)
        self.assertEqual(post.call_args.kwargs["json"]["audioTrackId"], "video-en-descriptive")
        self.assertEqual(self.events, [("add", "descriptive", "en")])
        self.assertEqual(result["repaired"], 1)

    async def test_auto_does_not_add_description_when_youtube_has_not_committed_the_delete(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        self.payload = response([audio_track("en", "dubbed"), audio_track("en", status="FAILED")])
        module = UpdateAudioModule()
        self.delete_ids.side_effect = lambda vid, channel, ids: (
            module._confirm_audio_tracks_deleted(vid, channel, ids) or 200
        )
        with (
            patch.object(module, "_get_video_translation_payload", side_effect=lambda *_: copy.deepcopy(self.payload)),
            patch("src.module.audio_module.wait_interruptibly"),
        ):
            result = await recovery.run_audio_recovery_cycle(now=2000)
        self.add.assert_not_called()
        self.assertEqual(result["failed"], 1)
        self.assertFalse(self.saved_entry()["description_attempts"]["en"]["succeeded"])

    async def test_healthy_dub_duplicate_keeps_language_audio_while_description_is_replaced(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"])
        self.payload = response([
            audio_track("en", "dubbed"), audio_track("en", "dubbed", "FAILED", track_id="duplicate-failed"),
            audio_track("en", status="FAILED"), audio_track("fr", "dubbed"), audio_track("fr"),
        ])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events[0], ("delete", ("video-en-descriptive",)))
        self.assertTrue(all("video-fr" not in str(event) for event in self.events))
        self.assertEqual([event for event in self.events if event[0] == "add"], [
            ("add", "descriptive", "en"),
        ])

    async def test_processed_tracks_are_completed_and_not_replaced_as_if_they_were_stuck(self):
        self.payload = response([audio_track(lang, kind, "PROCESSED")
                                 for lang in ("en", "vi") for kind in ("dubbed", "descriptive")])
        for track in self.payload["audioTracks"]:
            track.update(failureReason="AUDIO_TRACK_FAILURE_REASON_UNSPECIFIED",
                         rejectedReason="AUDIO_TRACK_REJECTED_REASON_UNSPECIFIED")
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertTrue(registry_entry_complete(self.saved_entry(), self.selected()))
        self.delete_ids.assert_not_called()
        self.add.assert_not_called()

    async def test_restart_can_add_descriptions_after_a_confirmed_upload_still_processing_on_youtube(self):
        state = recovery.get_audio_recovery_state()
        state["entries"]["channel"]["video"]["dubbed_attempts"] = {
            lang: {"succeeded": True, "attempted_at": 1900} for lang in ("en", "vi")
        }
        self.manager.save_state("audio_recovery", state)
        self.manager._conn.close()
        self.manager._conn = None
        self.payload = response([audio_track(lang, "dubbed", "PROCESSING") for lang in ("en", "vi")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [("add", "descriptive", "en"), ("add", "descriptive", "vi")])

    async def test_description_ready_during_render_does_not_trigger_unnecessary_language_replacement(self):
        self.payload = response([audio_track("en", "dubbed"), audio_track("vi", "dubbed")])

        def render(**kwargs):
            Path(kwargs["output_file"]).write_bytes(self.source.read_bytes())
            self.payload = response([audio_track("en", "dubbed"), audio_track("vi", "dubbed"), audio_track("en"), audio_track("vi")])

        self.render.side_effect = render
        await recovery.run_audio_recovery_cycle(now=2000)
        self.delete_ids.assert_not_called()
        self.add.assert_not_called()
        self.assertTrue(registry_entry_complete(self.saved_entry(), self.selected()))

    async def test_description_retry_never_deletes_healthy_language_audio(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"])
        self.payload = response([audio_track("en", "dubbed"), audio_track("en", status="FAILED")])

        def upload(**kwargs):
            if kwargs["audio_content_type"] == "descriptive":
                raise AudioUpdateError("description upload failed", status_code=400)
            return self.upload(**kwargs)

        self.add.side_effect = upload
        await recovery.run_audio_recovery_cycle(now=2000)
        await recovery.run_audio_recovery_cycle(now=2031)
        self.assertEqual([event for event in self.events if event[0] == "add"], [])
        self.assertEqual([event for event in self.events if event == ("delete", ("video-en-dubbed",))], [])
        self.assertFalse(self.saved_entry()["description_attempts"]["en"]["succeeded"])

    async def test_language_processed_during_render_is_preserved_while_failed_description_is_replaced(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"])
        self.payload = response([audio_track("en", "dubbed", "FAILED"), audio_track("en", status="FAILED")])

        def render(**kwargs):
            Path(kwargs["output_file"]).write_bytes(self.source.read_bytes())
            self.payload = response([audio_track("en", "dubbed", "PROCESSED"), audio_track("en", status="FAILED")])

        self.render.side_effect = render
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [("delete", ("video-en-descriptive",)), ("add", "descriptive", "en")])

    async def test_language_delete_retry_keeps_a_track_which_has_become_processed(self):
        from src.audio_language import call_audio_update_with_retry as retry
        self.entry["languages"] = ["en"]
        self.reset_registry()
        recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"])
        self.payload = response([audio_track("en", "dubbed", "FAILED")])

        def fail_delete(*_args):
            self.payload = response([audio_track("en", "dubbed", "PROCESSED")])
            raise AudioUpdateError("retry later", status_code=503, retryable=True)

        async def fast_retry(operation, **kwargs):
            return await retry(operation, sleep=AsyncMock(), **kwargs)

        self.delete_ids.side_effect = fail_delete
        with patch.object(recovery, "call_audio_update_with_retry", side_effect=fast_retry):
            await recovery.run_audio_recovery_cycle(now=2000)
        self.delete_ids.assert_called_once_with("video", "channel", ["video-en-dubbed"])
        self.assertEqual(self.events, [("add", "descriptive", "en")])
        self.assertEqual(self.saved_entry()["dubbed_completed_languages"], ["en"])

    async def test_processing_language_audio_allows_descriptions_without_repeated_rendering(self):
        self.payload = response([audio_track("en", "dubbed", "PROCESSING"), audio_track("vi", "dubbed", "PROCESSING")])
        await recovery.run_audio_recovery_cycle(now=2000)
        await recovery.run_audio_recovery_cycle(now=2031)
        self.metadata.assert_called_once()
        self.render.assert_called_once()
        self.assertEqual(self.events, [("add", "descriptive", "en"), ("add", "descriptive", "vi")])
        self.delete_ids.assert_not_called()

    async def test_original_audio_is_preserved_when_both_types_are_enabled(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"])
        self.payload = response([audio_track("en", "original", "INELIGIBLE")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.delete_ids.assert_not_called()
        self.assertEqual(self.events, [("add", "descriptive", "en")])

    async def test_turning_both_switches_off_makes_no_youtube_calls(self):
        recovery.set_audio_recovery_audio_types([])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.visibility.assert_not_called()
        self.fetch.assert_not_called()
        self.render.assert_not_called()
        self.add.assert_not_called()
        self.delete_ids.assert_not_called()

    async def test_legacy_source_lock_without_content_type_is_not_deleted_or_replaced(self):
        self.entry["languages"] = ["pcm"]
        self.reset_registry()
        recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"])
        self.payload = {"videoTranslations": [{"videoId": "video", "translations": [{
            "languageCode": "pcm", "audioTranslation": {
                "audioTrackId": "original-source", "source": "AUDIO_TRACK_SOURCE_UPLOAD",
                "status": "AUDIO_TRACK_STATUS_INELIGIBLE",
            },
        }]}], "audioTracks": []}
        await recovery.run_audio_recovery_cycle(now=2000)
        self.delete_ids.assert_not_called()
        self.assertEqual(self.events, [("add", "descriptive", "pcm")])

    async def test_switching_audio_off_does_not_disable_pending_caption_work(self):
        recovery.set_audio_recovery_audio_types([])
        state = recovery.get_audio_recovery_state()
        state["entries"]["channel"]["video"]["caption_monitor"] = {"languages": ["en"], "next_check_at": 0}
        self.manager.save_state("audio_recovery", state)
        captions = AsyncMock(return_value={"repaired": 0, "failed": 0, "quota_message": ""})
        with patch.object(recovery, "_monitor_failed_caption_tracks", captions):
            await recovery.run_audio_recovery_cycle(now=2000)
        captions.assert_awaited_once()
        self.fetch.assert_not_called()
        self.render.assert_not_called()
        self.add.assert_not_called()
        self.delete_ids.assert_not_called()

    async def test_language_checkpoint_failure_stops_before_deleting_the_track(self):
        recovery.set_audio_recovery_audio_types(["dubbed"])
        self.payload = response([audio_track("en", "dubbed", "FAILED")])
        save = self.manager.save_state

        def fail_checkpoint(name, state):
            attempted = state.get("entries", {}).get("channel", {}).get("video", {}).get("dubbed_attempts", {})
            if any(attempt.get("succeeded", True) is None for attempt in attempted.values()):
                return False
            return save(name, state)

        with patch.object(self.manager, "save_state", side_effect=fail_checkpoint):
            await recovery.run_audio_recovery_cycle(now=2000)
        self.delete_ids.assert_not_called()
        self.add.assert_not_called()

    async def test_disabling_language_audio_during_upload_stops_scheduling_that_type(self):
        def upload(**kwargs):
            result = self.upload(**kwargs)
            if kwargs["audio_content_type"] == "dubbed":
                recovery.set_audio_recovery_audio_types(["descriptive"])
            return result

        self.add.side_effect = upload
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [
            ("add", "dubbed", "en"), ("add", "descriptive", "en"), ("add", "descriptive", "vi"),
        ])

    async def test_enabling_another_type_reopens_old_complete_registrations(self):
        recovery.set_audio_recovery_audio_types(["descriptive"])
        self.payload = response([audio_track("en"), audio_track("vi")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertTrue(registry_entry_complete(self.saved_entry(), self.selected()))
        recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"])
        await recovery.run_audio_recovery_cycle(now=2031)
        self.assertEqual(self.events, [("add", "dubbed", "en"), ("add", "dubbed", "vi")])
        self.assertEqual(self.saved_entry()["description_completed_languages"], ["en", "vi"])

    async def test_failed_language_delete_prevents_its_upload_and_description_but_other_languages_continue(self):
        self.payload = response([audio_track("en", "dubbed", "FAILED")])
        self.delete_ids.side_effect = AudioUpdateError("cannot delete language audio", status_code=400)
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [("add", "dubbed", "vi"), ("add", "descriptive", "vi")])
        self.assertFalse(self.saved_entry()["dubbed_attempts"]["en"]["succeeded"])
        self.assertNotIn("en", self.saved_entry().get("description_attempts", {}))

    async def test_all_fifteen_regional_codes_get_both_types_from_the_same_full_file(self):
        languages = "en-AU en-CA en-IN en-IE en-GB en-US pt pt-BR pt-PT es es-419 es-MX es-ES es-US fr".split()
        self.entry["languages"] = languages
        self.reset_registry()
        recovery.set_audio_recovery_audio_types(["dubbed", "descriptive"])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(self.events, [("add", kind, lang) for lang in languages for kind in ("dubbed", "descriptive")])
        self.render.assert_called_once()


if __name__ == "__main__":
    unittest.main()
