import asyncio
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.audio_recovery import (
    clear_audio_recovery_registry,
    get_audio_mutation_guard,
    get_audio_recovery_runtime_status,
    get_audio_recovery_state,
    run_audio_recovery_cycle,
    set_audio_recovery_items_enabled,
)
from src.state_manager import StateManager


class AudioRecoveryConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        path_patch = patch("src.state_manager.get_data_dir", return_value=Path(self.folder.name))
        path_patch.start()
        self.addCleanup(path_patch.stop)
        self.manager = StateManager()
        self.addCleanup(lambda: self.manager._conn.close())
        state_patch = patch("src.audio_recovery.state_manager", self.manager)
        state_patch.start()
        self.addCleanup(state_patch.stop)
        self.source = Path(self.folder.name) / "source.mp3"
        self.source.write_bytes(b"source")
        self.channels = [f"parallel-{index}" for index in range(5)]
        self.manager.save_state("audio_recovery", {"entries": {
            channel: {f"{channel}-video": {
                "audio_path": str(self.source), "languages": ["en", "es"],
            }} for channel in self.channels
        }})
        self.lock = threading.Lock()
        self.release_uploads = threading.Event()
        self.release_uploads.set()
        self.first_three_uploads = threading.Event()
        self.active_channels = set()
        self.max_active = 0
        self.events = {channel: [] for channel in self.channels}
        self.temp_files = set()
        self.fail_channel = None

        def visibility(channel_id, video_ids, **_kwargs):
            self.assertFalse(get_audio_mutation_guard(channel_id).locked())
            return dict.fromkeys(video_ids, True), set()

        def payload(video_ids, channel_id):
            self.assertEqual(video_ids, [f"{channel_id}-video"])
            return {
                "videoTranslations": [{"videoId": video_ids[0], "translations": []}],
                "audioTracks": [{
                    "videoId": video_ids[0], "audioTrackId": f"{channel_id}-{language}",
                    "language": language, "source": "AUDIO_TRACK_SOURCE_CREATOR",
                    "audioContentTypeString": "dubbed", "status": "AUDIO_TRACK_STATUS_FAILED",
                } for language in ("en", "es")],
            }

        def render(*, output_file, **_kwargs):
            Path(output_file).write_bytes(b"x" * 200)

        def delete(video_id, channel_id, track_ids):
            self.assertTrue(get_audio_mutation_guard(channel_id).locked())
            self.assertEqual(video_id, f"{channel_id}-video")
            language = track_ids[0].removeprefix(f"{channel_id}-")
            self.assertIn(language, ("en", "es"))
            with self.lock:
                self.events[channel_id].append(("delete", language))
            return 200

        def upload(*, id_video, channel_id, file_name, language, progress, **_kwargs):
            self.assertTrue(get_audio_mutation_guard(channel_id).locked())
            self.assertEqual(id_video, f"{channel_id}-video")
            self.assertTrue(Path(file_name).is_file())
            with self.lock:
                self.assertNotIn(channel_id, self.active_channels)
                self.active_channels.add(channel_id)
                self.max_active = max(self.max_active, len(self.active_channels))
                self.temp_files.add(file_name)
                self.events[channel_id].append(("add", language))
                progress["sent"] = (self.channels.index(channel_id) + 1) * 10
                if len(self.active_channels) == 3:
                    self.first_three_uploads.set()
            try:
                if not self.release_uploads.wait(timeout=5):
                    raise AssertionError("Test did not release blocked uploads")
                if channel_id == self.fail_channel and language == "en":
                    raise RuntimeError("upload failed")
                return 200
            finally:
                with self.lock:
                    self.active_channels.remove(channel_id)

        patches = {
            "_get_registered_video_scan_statuses": visibility,
            "update_audio_module._get_video_translation_payload": payload,
            "update_audio_module._get_video_info": lambda **_kwargs: SimpleNamespace(duration_ms=60000),
            "multiply_audio": render,
            "update_audio_module.delete_track_ids": delete,
            "update_audio_module.add": upload,
        }
        self.mocks = {}
        for target, operation in patches.items():
            patcher = patch(f"src.audio_recovery.{target}", side_effect=operation)
            self.mocks[target] = patcher.start()
            self.addCleanup(patcher.stop)

    async def wait_for_three_uploads(self):
        ready = await asyncio.wait_for(
            asyncio.to_thread(self.first_three_uploads.wait, 3), timeout=4,
        )
        self.assertTrue(ready, "Three channels did not start together")

    async def finish_cycle(self, task):
        self.release_uploads.set()
        return await asyncio.wait_for(task, timeout=4)

    async def test_three_channels_run_together_and_remaining_channels_queue(self):
        self.release_uploads.clear()
        task = asyncio.create_task(run_audio_recovery_cycle(now=2000))
        try:
            await self.wait_for_three_uploads()
            self.assertEqual(self.mocks["_get_registered_video_scan_statuses"].call_count, 3)
            status = get_audio_recovery_runtime_status()
            self.assertEqual(status["active_channel_count"], 3)
            self.assertEqual(status["channel_concurrency"], 3)
            self.assertEqual(len(status["channels"]), 3)
            self.assertNotIn("_upload_progress", status)
            for job in status["channels"]:
                channel_id = job["channel_id"]
                self.assertEqual(job["video_id"], f"{channel_id}-video")
                self.assertEqual(job["phase"], "uploading")
                self.assertEqual(job["language"], "en")
                self.assertEqual(job["upload_sent"], (self.channels.index(channel_id) + 1) * 10)
                self.assertEqual(job["upload_total"], 200)
                self.assertNotIn("_upload_progress", job)
        finally:
            result = await self.finish_cycle(task)

        self.assertEqual(self.max_active, 3)
        self.assertEqual(result["repaired"], 10)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["scanned_channels"], 5)
        for channel_id in self.channels:
            self.assertEqual(self.events[channel_id], [
                ("delete", "en"), ("add", "en"), ("delete", "es"), ("add", "es"),
            ])
        self.assertEqual(len(self.temp_files), 5)
        self.assertTrue(all(not Path(path).exists() for path in self.temp_files))
        status = get_audio_recovery_runtime_status()
        self.assertEqual(status["completed_channel_count"], 5)
        self.assertEqual(status["active_channel_count"], 0)
        self.assertEqual(status["channels"], [])

    async def test_upload_failure_does_not_stop_other_channels_or_lose_saved_attempts(self):
        self.fail_channel = self.channels[0]
        result = await run_audio_recovery_cycle(now=2000)
        self.assertEqual(result["repaired"], 9)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["scanned_channels"], 5)
        entries = get_audio_recovery_state()["entries"]
        for channel_id in self.channels:
            attempts = entries[channel_id][f"{channel_id}-video"]["attempts"]
            self.assertEqual(attempts["en"]["succeeded"], channel_id != self.fail_channel)
            self.assertTrue(attempts["es"]["succeeded"])

    async def test_deactivating_queued_channel_prevents_its_scan_and_mutations(self):
        self.release_uploads.clear()
        task = asyncio.create_task(run_audio_recovery_cycle(now=2000))
        try:
            await self.wait_for_three_uploads()
            set_audio_recovery_items_enabled(enabled=False, channel_ids=self.channels[3:])
        finally:
            result = await self.finish_cycle(task)
        self.assertEqual(result["repaired"], 6)
        self.assertEqual(result["scanned_channels"], 3)
        self.assertEqual(result["scope_skipped_channel_ids"], self.channels[3:])
        self.assertTrue(all(not self.events[channel] for channel in self.channels[3:]))

    async def test_clearing_registry_finishes_active_uploads_without_starting_more(self):
        self.release_uploads.clear()
        task = asyncio.create_task(run_audio_recovery_cycle(now=2000))
        try:
            await self.wait_for_three_uploads()
            clear_audio_recovery_registry()
        finally:
            result = await self.finish_cycle(task)
        self.assertTrue(result["cancelled_by_clear"])
        self.assertEqual(result["repaired"], 3)
        self.assertEqual(get_audio_recovery_state()["entries"], {})
        self.assertTrue(all(not self.events[channel] for channel in self.channels[3:]))

    async def test_cancellation_keeps_active_upload_guards_until_threads_finish(self):
        self.release_uploads.clear()
        task = asyncio.create_task(run_audio_recovery_cycle(now=2000))
        try:
            await self.wait_for_three_uploads()
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            for channel_id in self.channels[:3]:
                self.assertTrue(get_audio_mutation_guard(channel_id).locked())
        finally:
            with self.assertRaises(asyncio.CancelledError):
                await self.finish_cycle(task)
        for channel_id in self.channels:
            self.assertFalse(get_audio_mutation_guard(channel_id).locked())
        self.assertEqual(self.mocks["update_audio_module.add"].call_count, 3)
        self.assertTrue(all(not self.events[channel] for channel in self.channels[3:]))
        self.assertTrue(all(not Path(path).exists() for path in self.temp_files))
        self.assertFalse(get_audio_recovery_runtime_status()["active"])


if __name__ == "__main__":
    unittest.main()
