import asyncio
import copy
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src import audio_recovery as recovery
from src.audio_description_recovery import (
    build_description_recovery_plan, description_entry_complete,
    resolve_description_audio_path,
)
from src.module.audio_module import AudioUpdateError
from src.state_manager import StateManager


def audio_track(language, kind="descriptive", status="READY", video_id="video", track_id=None):
    return {"videoId": video_id, "language": language,
            "audioTrackId": track_id or f"{video_id}-{language}-{kind}",
            "audioContentTypeString": kind, "source": "AUDIO_TRACK_SOURCE_CREATOR",
            "status": "AUDIO_TRACK_STATUS_" + status}


def response(tracks=(), video_id="video"):
    return {"videoTranslations": [{"videoId": video_id, "translations": []}], "audioTracks": list(tracks)}


class RegistryAudioFixture:
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.folder = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch("src.state_manager.get_data_dir", return_value=self.folder))
        self.manager = StateManager()
        self.addCleanup(lambda: self.manager._conn.close() if self.manager._conn is not None else None)
        self.stack.enter_context(patch.object(recovery, "state_manager", self.manager))
        self.source = self.folder / "song.mp3"
        self.source.write_bytes(b"full uninterrupted music")
        self.entry = {"audio_path": str(self.source), "languages": ["en", "vi"],
                      "repeat_times": 1, "extra_minutes": 0}
        self.reset_registry()
        self.payload = response()
        self.visibility = self.stack.enter_context(patch.object(
            recovery, "_get_registered_video_scan_statuses",
            side_effect=lambda channel, ids, **kwargs: (dict.fromkeys(ids, True), set()),
        ))
        self.fetch = self.stack.enter_context(patch.object(
            recovery.update_audio_module, "_get_video_translation_payload", side_effect=lambda *args: copy.deepcopy(self.payload),
        ))
        self.metadata = self.stack.enter_context(patch.object(
            recovery.update_audio_module, "_get_video_info", return_value=SimpleNamespace(duration_ms=60500, title="Song"),
        ))
        self.temp_paths = []

        def render(**kwargs):
            self.assertEqual(kwargs["input_file"], str(self.source))
            self.assertEqual(kwargs["video_duration_seconds"], 60.5)
            path = Path(kwargs["output_file"])
            self.temp_paths.append(path)
            path.write_bytes(self.source.read_bytes())

        self.render = self.stack.enter_context(patch.object(recovery, "multiply_audio", side_effect=render))

        def upload(**kwargs):
            self.assertEqual(kwargs["audio_content_type"], "descriptive")
            self.assertEqual(Path(kwargs["file_name"]).read_bytes(), self.source.read_bytes())
            self.assertTrue(recovery.get_audio_mutation_guard("channel").locked())
            return 200

        self.add = self.stack.enter_context(patch.object(recovery.update_audio_module, "add", side_effect=upload))
        self.delete = self.stack.enter_context(patch.object(recovery.update_audio_module, "delete", side_effect=AssertionError("must never delete")))
        self.delete_ids = self.stack.enter_context(patch.object(recovery.update_audio_module, "delete_track_ids", side_effect=AssertionError("unexpected track deletion")))
        self.addCleanup(self.delete.assert_not_called)

    def reset_registry(self):
        self.manager.save_state("audio_recovery", {"audio_content_types": ["descriptive"], "entries": {"channel": {"video": copy.deepcopy(self.entry)}}})

    def saved_entry(self):
        return recovery.get_audio_recovery_state()["entries"]["channel"]["video"]

class RegistryDescriptionTests(RegistryAudioFixture, unittest.IsolatedAsyncioTestCase):
    async def test_legacy_entries_receive_full_descriptions_regardless_of_dub_status(self):
        for status in ("READY", "PROCESSING", "FAILED", "DELETED"):
            with self.subTest(status=status):
                self.reset_registry()
                self.add.reset_mock()
                self.payload = response([audio_track("en", "dubbed", status), audio_track("vi", "dubbed", status)])
                result = await recovery.run_audio_recovery_cycle(now=2000)
                self.assertEqual(result["repaired"], 2)
                self.assertEqual([call.kwargs["language"] for call in self.add.call_args_list], ["en", "vi"])
                self.assertTrue(all(call.kwargs["audio_content_type"] == "descriptive" for call in self.add.call_args_list))
                self.assertFalse(description_entry_complete(self.saved_entry()))
        self.assertTrue(all(not path.exists() for path in self.temp_paths))

    async def test_confirmed_descriptions_are_completed_and_never_rescanned_after_restart(self):
        self.payload = response([audio_track("en"), audio_track("vi")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertTrue(description_entry_complete(self.saved_entry()))
        self.add.assert_not_called()
        state = recovery.get_audio_recovery_state()
        state["entries"]["channel"]["video"]["caption_monitor"] = {"languages": ["en"], "next_check_at": 0}
        self.manager.save_state("audio_recovery", state)
        self.manager._conn.close()
        self.manager._conn = None
        self.fetch.reset_mock()
        self.visibility.reset_mock()
        self.payload = response([audio_track("en", status="DELETED")])
        result = await recovery.run_audio_recovery_cycle(now=10000)
        self.assertEqual(result["skipped"], "complete_or_waiting")
        self.fetch.assert_not_called()
        self.visibility.assert_not_called()
        self.metadata.assert_not_called()

    async def test_only_missing_language_is_submitted_then_verified_before_completion(self):
        self.payload = response([audio_track("en"), audio_track("vi", "dubbed", "DELETED")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual([call.kwargs["language"] for call in self.add.call_args_list], ["vi"])
        self.assertEqual(self.saved_entry()["description_completed_languages"], ["en"])
        self.assertTrue(self.saved_entry()["description_attempts"]["vi"]["succeeded"])
        self.fetch.reset_mock()
        await recovery.run_audio_recovery_cycle(now=2005)
        self.fetch.assert_not_called()
        self.payload = response([audio_track("vi")])
        await recovery.run_audio_recovery_cycle(now=2031)
        self.assertTrue(description_entry_complete(self.saved_entry()))
        self.add.assert_called_once()

    async def test_failed_description_is_deleted_before_retry_and_verified_before_completion(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        self.payload = response([
            audio_track("en", status="FAILED", track_id="failed-description"),
            audio_track("en", "dubbed", "FAILED", track_id="failed-dub"),
            audio_track("en", "original", track_id="original"),
            audio_track("fr", status="FAILED", track_id="other-language"),
        ])
        events = []

        def delete(video_id, channel_id, track_ids):
            self.assertEqual((video_id, channel_id, track_ids), ("video", "channel", ["failed-description"]))
            self.assertTrue(recovery.get_audio_mutation_guard("channel").locked())
            self.assertIsNone(self.saved_entry()["description_attempts"]["en"]["succeeded"])
            events.append("delete")
            return 200

        self.delete_ids.side_effect = delete

        def add(**kwargs):
            self.assertEqual(kwargs["audio_content_type"], "descriptive")
            events.append("add")
            raise AudioUpdateError("conflict; description not ready", status_code=409)

        self.add.side_effect = add
        await recovery.run_audio_recovery_cycle(now=2000)
        await recovery.run_audio_recovery_cycle(now=2031)
        self.assertEqual(self.add.call_count, 2)
        self.assertEqual(events, ["delete", "add", "delete", "add"])
        self.assertFalse(description_entry_complete(self.saved_entry()))
        self.assertFalse(self.saved_entry()["description_attempts"]["en"]["succeeded"])
        self.payload = response([audio_track("en")])
        await recovery.run_audio_recovery_cycle(now=2062)
        self.assertTrue(description_entry_complete(self.saved_entry()))
        self.assertEqual(self.add.call_count, 2)
        self.assertEqual(self.delete_ids.call_count, 2)

    async def test_delete_failure_prevents_upload_and_retries_in_the_next_cycle(self):
        self.entry["languages"] = ["es-MX"]
        self.reset_registry()
        self.payload = response([audio_track("es-MX", status="FAILED", track_id="failed-description")])
        self.delete_ids.side_effect = AudioUpdateError("cannot delete", status_code=403)
        result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(result["failed"], 1)
        self.add.assert_not_called()
        self.assertFalse(self.saved_entry()["description_attempts"]["es-mx"]["succeeded"])
        self.assertIn("cannot delete", self.saved_entry()["description_attempts"]["es-mx"]["message"])
        self.delete_ids.side_effect = None
        self.delete_ids.return_value = 200
        self.payload = response()
        await recovery.run_audio_recovery_cycle(now=2031)
        self.add.assert_called_once()
        self.assertFalse(description_entry_complete(self.saved_entry()))
        self.payload = response([audio_track("es-MX")])
        await recovery.run_audio_recovery_cycle(now=2062)
        self.assertTrue(description_entry_complete(self.saved_entry()))

    async def test_failed_description_is_rechecked_before_each_language_delete(self):
        self.payload = response([
            audio_track("en", status="FAILED", track_id="failed-en"),
            audio_track("vi", status="FAILED", track_id="old-vi"),
        ])
        events = []

        def delete(video_id, channel_id, track_ids):
            events.append(("delete", track_ids))
            return 200

        def upload(**kwargs):
            events.append(("add", kwargs["language"]))
            # The other language finished processing while this upload ran.
            self.payload = response([audio_track("en", status="PROCESSING"), audio_track("vi")])
            return 200

        self.delete_ids.side_effect = delete
        self.add.side_effect = upload
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(events, [("delete", ["failed-en"]), ("add", "en")])
        self.assertEqual(self.saved_entry()["description_completed_languages"], ["vi"])

    async def test_changed_failed_description_uses_fresh_track_ids(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        self.payload = response([audio_track("en", status="FAILED", track_id="old-track")])

        def render(**kwargs):
            Path(kwargs["output_file"]).write_bytes(self.source.read_bytes())
            self.payload = response([audio_track("en", status="FAILED", track_id="new-track")])

        self.render.side_effect = render
        self.delete_ids.side_effect = None
        self.delete_ids.return_value = 200
        await recovery.run_audio_recovery_cycle(now=2000)
        self.delete_ids.assert_called_once_with("video", "channel", ["new-track"])
        self.add.assert_called_once()

    async def test_deleted_description_is_added_without_deleting_a_stale_track_id(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        self.payload = response([audio_track("en", status="FAILED")])

        def render(**kwargs):
            Path(kwargs["output_file"]).write_bytes(self.source.read_bytes())
            self.payload = response()

        self.render.side_effect = render
        await recovery.run_audio_recovery_cycle(now=2000)
        self.delete_ids.assert_not_called()
        self.add.assert_called_once()

    async def test_healthy_duplicate_wins_over_a_failed_description(self):
        self.payload = response([audio_track("en"), audio_track("en", status="FAILED", track_id="old-failed"), audio_track("vi")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.add.assert_not_called()
        self.delete_ids.assert_not_called()
        self.assertTrue(description_entry_complete(self.saved_entry()))

    async def test_processing_description_is_retried_only_after_two_hours_without_delete(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        self.payload = response([audio_track("en", status="PROCESSING")])
        await recovery.run_audio_recovery_cycle(now=2000)
        await recovery.run_audio_recovery_cycle(now=2031)
        self.add.assert_not_called()
        await recovery.run_audio_recovery_cycle(now=9201)
        self.add.assert_called_once()
        self.delete_ids.assert_not_called()
        self.assertFalse(description_entry_complete(self.saved_entry()))

    async def test_description_ready_during_render_is_not_uploaded_again(self):
        def render(**kwargs):
            Path(kwargs["output_file"]).write_bytes(b"full music")
            self.payload = response([audio_track("en"), audio_track("vi")])

        self.render.side_effect = render
        await recovery.run_audio_recovery_cycle(now=2000)
        self.add.assert_not_called()
        self.assertTrue(description_entry_complete(self.saved_entry()))

    async def test_unreadable_status_is_neither_missing_nor_completed(self):
        self.payload = response(video_id="other")
        result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(result["unreadable"], ["video"])
        self.add.assert_not_called()
        self.assertFalse(description_entry_complete(self.saved_entry()))

    async def test_new_languages_resume_a_completed_legacy_registration(self):
        self.payload = response([audio_track("en"), audio_track("vi")])
        await recovery.run_audio_recovery_cycle(now=2000)
        recovery.register_audio_recovery(channel_id="channel", video_id="video", audio_path=str(self.source),
                                        languages=["en", "vi", "fr"], repeat_times=1, extra_minutes=0)
        self.assertFalse(description_entry_complete(self.saved_entry()))
        await recovery.run_audio_recovery_cycle(now=2001)
        self.assertEqual([call.kwargs["language"] for call in self.add.call_args_list], ["fr"])
        self.assertEqual(self.saved_entry()["description_completed_languages"], ["en", "vi"])

    async def test_missing_old_source_is_recovered_from_the_saved_channel_history(self):
        self.entry["audio_path"] = str(self.folder / "moved" / "song.mp3")
        self.reset_registry()
        self.manager.save_state("audio_add", {"audio_path_history": {"channel": {"video": str(self.source)}}})
        result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(result["repaired"], 2)
        self.assertEqual(self.saved_entry()["audio_path"], str(self.source))

    async def test_disabled_registry_stays_off_and_manual_operations_are_not_required(self):
        recovery.set_audio_recovery_enabled(False)
        result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(result["skipped"], "disabled")
        self.fetch.assert_not_called()
        recovery.set_audio_recovery_enabled(True)
        result = await recovery.run_audio_recovery_cycle(now=2001)
        self.assertEqual(result["repaired"], 2)

    async def test_all_fifteen_registered_language_variants_receive_the_same_full_source(self):
        languages = (
            "en-AU en-CA en-IN en-IE en-GB en-US pt pt-BR pt-PT "
            "es es-419 es-MX es-ES es-US fr"
        ).split()
        self.entry["languages"] = languages
        self.reset_registry()
        result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertEqual(result["repaired"], 15)
        self.assertEqual([call.kwargs["language"] for call in self.add.call_args_list], languages)
        self.render.assert_called_once()
        self.payload = response([audio_track(language) for language in languages])
        await recovery.run_audio_recovery_cycle(now=2031)
        self.assertTrue(description_entry_complete(self.saved_entry()))

    async def test_changed_processing_track_is_left_to_finish_after_render(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        self.payload = response([audio_track("en", status="PROCESSING")])
        await recovery.run_audio_recovery_cycle(now=2000)

        def render(**kwargs):
            Path(kwargs["output_file"]).write_bytes(b"full music")
            self.payload = response([audio_track("en", status="PROCESSING", track_id="new-track")])

        self.render.side_effect = render
        await recovery.run_audio_recovery_cycle(now=9201)
        self.add.assert_not_called()
        self.assertFalse(description_entry_complete(self.saved_entry()))
        self.assertEqual(self.saved_entry()["description_processing_observations"]["en"]["track_ids"], ["new-track"])

    async def test_unknown_description_status_is_not_prematurely_completed(self):
        track = audio_track("en")
        track.pop("status")
        self.payload = response([track, audio_track("vi")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.add.assert_not_called()
        self.assertFalse(description_entry_complete(self.saved_entry()))
        self.assertEqual(self.saved_entry()["description_completed_languages"], ["vi"])

    async def test_failure_to_checkpoint_prevents_upload(self):
        with patch.object(self.manager, "save_state", return_value=False):
            result = await recovery.run_audio_recovery_cycle(now=2000)
        self.assertGreater(result["failed"], 0)
        self.add.assert_not_called()
        self.assertFalse(description_entry_complete(self.saved_entry()))

    async def test_cancel_drains_the_current_upload_and_stops_next_language(self):
        started, release = threading.Event(), threading.Event()

        def upload(**kwargs):
            started.set()
            if not release.wait(3):
                raise AssertionError("upload not released")
            return 200

        self.add.side_effect = upload
        task = asyncio.create_task(recovery.run_audio_recovery_cycle(now=2000))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 2))
            task.cancel()
            await asyncio.sleep(0)
            self.assertTrue(recovery.get_audio_mutation_guard("channel").locked())
            self.assertTrue(self.temp_paths[0].exists())
        finally:
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.add.assert_called_once()
        self.assertFalse(recovery.get_audio_mutation_guard("channel").locked())
        self.assertTrue(all(not path.exists() for path in self.temp_paths))

    async def test_manual_repair_reopens_only_the_failed_language_of_a_completed_registration(self):
        self.payload = response([audio_track("en"), audio_track("vi")])
        await recovery.run_audio_recovery_cycle(now=2000)
        self.assertTrue(description_entry_complete(self.saved_entry()))
        self.assertTrue(recovery.invalidate_description_completion("channel", "video", ["EN"]))
        self.assertEqual(self.saved_entry()["description_completed_languages"], ["vi"])
        self.assertNotIn("description_completed_at", self.saved_entry())
        recovery.register_audio_recovery(channel_id="channel", video_id="video", audio_path=str(self.source),
                                        languages=["en", "vi"], repeat_times=1, extra_minutes=0)
        self.assertFalse(description_entry_complete(self.saved_entry()))
        self.payload = response()
        await recovery.run_audio_recovery_cycle(now=2001)
        self.add.assert_called_once()
        self.assertEqual(self.add.call_args.kwargs["language"], "en")
        self.delete_ids.assert_not_called()

    async def test_failed_checkpoint_prevents_deleting_a_failed_description(self):
        self.entry["languages"] = ["en"]
        self.reset_registry()
        self.payload = response([audio_track("en", status="FAILED")])
        save = self.manager.save_state

        def fail_attempt_checkpoint(name, state):
            if (state.get("entries", {}).get("channel", {}).get("video", {}).get("description_attempts", {})
                    .get("en", {}).get("succeeded", True)) is None:
                return False
            return save(name, state)

        with patch.object(self.manager, "save_state", side_effect=fail_attempt_checkpoint):
            await recovery.run_audio_recovery_cycle(now=2000)
        self.delete_ids.assert_not_called()
        self.add.assert_not_called()

    async def test_cancel_drains_description_delete_and_does_not_start_upload(self):
        self.payload = response([audio_track("en", status="FAILED"), audio_track("vi", status="FAILED")])
        started, release = threading.Event(), threading.Event()

        def delete(*args):
            started.set()
            if not release.wait(3):
                raise AssertionError("delete not released")
            return 200

        self.delete_ids.side_effect = delete
        task = asyncio.create_task(recovery.run_audio_recovery_cycle(now=2000))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 2))
            task.cancel()
            await asyncio.sleep(0)
            self.assertTrue(recovery.get_audio_mutation_guard("channel").locked())
        finally:
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.delete_ids.assert_called_once()
        self.add.assert_not_called()
        self.assertFalse(recovery.get_audio_mutation_guard("channel").locked())
        self.assertTrue(all(not path.exists() for path in self.temp_paths))


class DescriptionSourceLookupTests(unittest.TestCase):
    def test_mapping_csv_and_video_title_can_find_the_source_without_manual_rematching(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "My Song full.mp3"
            path.write_bytes(b"music")
            pages = {"audio_add": {"selected_channel": "channel", "batch_scan_state": {"music_folder": folder}}}
            self.assertEqual(resolve_description_audio_path(channel_id="channel", video_id="video", entry={},
                             page_states=pages, title="My Song"), path)
            (Path(folder) / "mapping.csv").write_text("video_id,audio_file\nvideo,My Song full.mp3\n", encoding="utf-8")
            self.assertEqual(resolve_description_audio_path(channel_id="channel", video_id="video", entry={},
                             page_states=pages), path)

    def test_moved_source_is_found_in_configured_folder_by_name(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "song.mp3"
            path.write_bytes(b"full music")
            found = resolve_description_audio_path(
                channel_id="channel", video_id="video", entry={"audio_path": str(Path(folder) / "old" / "song.mp3")},
                page_states={"audio_add": {"selected_channel": "channel", "batch_scan_state": {"music_folder": folder}}},
            )
            self.assertEqual(found, path)

    def test_ambiguous_files_are_not_chosen_arbitrarily(self):
        with tempfile.TemporaryDirectory() as folder:
            for directory in ("one", "two"):
                sub = Path(folder) / directory
                sub.mkdir()
                (sub / "song.mp3").write_bytes(b"music")
            with self.assertRaisesRegex(RuntimeError, "video"):
                resolve_description_audio_path(
                    channel_id="channel", video_id="video", entry={"audio_path": "missing/song.mp3"},
                    page_states={"audio_add": {"selected_channel": "channel", "batch_scan_state": {"music_folder": folder}}},
                )

    def test_another_channels_flow_is_not_used(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "music.mp3"
            path.write_bytes(b"music")
            with self.assertRaises(FileNotFoundError):
                resolve_description_audio_path(channel_id="channel", video_id="video", entry={}, page_states={
                    "add_audio_flow": {"selected_channel": "other", "statuses": {"v.mp4": {"video_id": "video", "music_path": str(path)}}},
                })


if __name__ == "__main__":
    unittest.main()
