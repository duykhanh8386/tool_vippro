import asyncio
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests

from src.module.audio_module import UpdateAudioModule
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

    async def test_busy_application_thread_pool_does_not_block_recovery_channels(self):
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
        default_worker_started = asyncio.Event()
        release_default_worker = threading.Event()

        def occupy_application_worker():
            loop.call_soon_threadsafe(default_worker_started.set)
            if not release_default_worker.wait(timeout=5):
                raise AssertionError("Test did not release application worker")

        async def wait_for_recovery_uploads():
            while not self.first_three_uploads.is_set():
                await asyncio.sleep(0.01)

        busy_task = asyncio.create_task(asyncio.to_thread(occupy_application_worker))
        await asyncio.wait_for(default_worker_started.wait(), timeout=1)
        self.release_uploads.clear()
        task = asyncio.create_task(run_audio_recovery_cycle(now=2000))
        try:
            await asyncio.wait_for(wait_for_recovery_uploads(), timeout=1)
            self.assertFalse(busy_task.done())
            self.assertEqual(get_audio_recovery_runtime_status()["active_channel_count"], 3)
        finally:
            release_default_worker.set()
            self.release_uploads.set()
            await asyncio.wait_for(busy_task, timeout=3)
            result = await asyncio.wait_for(task, timeout=4)
        self.assertEqual(result["repaired"], 10)

    async def test_transport_progress_for_three_registry_channels_advances_before_any_response(self):
        self.channels = self.channels[:3]
        state = get_audio_recovery_state()
        state["entries"] = {channel: state["entries"][channel] for channel in self.channels}
        for videos in state["entries"].values():
            for entry in videos.values():
                entry["languages"] = ["en"]
        self.manager.save_state("audio_recovery", state)
        module = UpdateAudioModule()
        self.mocks["update_audio_module.add"].side_effect = module.add
        loop = asyncio.get_running_loop()
        all_started = asyncio.Event()
        advanced = asyncio.Event()
        gates = {channel: threading.Event() for channel in self.channels}
        finish = threading.Event()
        started = set()

        def send(request, **_kwargs):
            channel = request.url.rsplit("/", 1)[1]
            self.assertTrue(get_audio_mutation_guard(channel).locked())
            self.assertEqual(request.headers["Content-Length"], "200")
            self.assertEqual(len(request.body.read(40)), 40)
            with self.lock:
                started.add(channel)
                if len(started) == 3:
                    loop.call_soon_threadsafe(all_started.set)
            if not gates[channel].wait(timeout=5):
                raise AssertionError("Test did not advance the upload")
            self.assertEqual(len(request.body.read(40)), 40)
            if channel == self.channels[1]:
                loop.call_soon_threadsafe(advanced.set)
            if not finish.wait(timeout=5):
                raise AssertionError("Test did not release the HTTP response")
            self.assertEqual(len(request.body.read()), 120)
            response = requests.Response()
            response.status_code = 200
            response._content = b""
            return response

        with (
            patch("src.module.audio_module.get_channels_info", side_effect=lambda channel: SimpleNamespace(
                cookies=[{"name": "test", "value": channel}],
            )),
            patch.object(module, "_get_session_token", return_value="test-token"),
            patch.object(module, "_upload_http", side_effect=lambda **kwargs: (
                f"https://upload.test/{kwargs['cookie_string'].split('=')[1]}", "resource",
            )),
            patch.object(module, "_update", return_value=200),
            patch("requests.sessions.Session.send", side_effect=send),
        ):
            task = asyncio.create_task(run_audio_recovery_cycle(now=2000))
            try:
                await asyncio.wait_for(all_started.wait(), timeout=3)
                jobs = {job["channel_id"]: job for job in get_audio_recovery_runtime_status()["channels"]}
                self.assertEqual(set(jobs), set(self.channels))
                self.assertTrue(all(job["upload_sent"] == 40 for job in jobs.values()))
                self.assertTrue(all(job["upload_confirmed"] == 0 for job in jobs.values()))
                gates[self.channels[1]].set()
                await asyncio.wait_for(advanced.wait(), timeout=3)
                jobs = {job["channel_id"]: job for job in get_audio_recovery_runtime_status()["channels"]}
                self.assertEqual([jobs[channel]["upload_sent"] for channel in self.channels], [40, 80, 40])
                self.assertEqual([jobs[channel]["upload_fraction"] for channel in self.channels], [0.2, 0.4, 0.2])
                self.assertTrue(all(job["upload_status"] == "uploading" for job in jobs.values()))
                self.assertFalse(task.done())
            finally:
                for gate in gates.values():
                    gate.set()
                finish.set()
                result = await asyncio.wait_for(task, timeout=4)
        self.assertEqual(result["repaired"], 3)
        self.assertEqual(result["failed"], 0)

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

    async def test_channel_can_prepare_and_upload_while_another_upload_is_blocked(self):
        self.channels = self.channels[:2]
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
        other_source = Path(self.folder.name) / "source-b.mp3"
        other_source.write_bytes(b"source")
        state = get_audio_recovery_state()
        state["entries"] = {channel: state["entries"][channel] for channel in self.channels}
        state["entries"][self.channels[1]][f"{self.channels[1]}-video"]["audio_path"] = str(other_source)
        self.manager.save_state("audio_recovery", state)

        upload_started = asyncio.Event()
        other_render_started = asyncio.Event()
        other_upload_started = asyncio.Event()
        release_upload = threading.Event()
        release_render = threading.Event()
        render = self.mocks["multiply_audio"].side_effect
        upload = self.mocks["update_audio_module.add"].side_effect

        def controlled_render(**kwargs):
            render(**kwargs)
            if Path(kwargs["input_file"]).name == other_source.name:
                loop.call_soon_threadsafe(other_render_started.set)
                if not release_render.wait(timeout=5):
                    raise AssertionError("Test did not release rendering")

        def controlled_upload(**kwargs):
            if kwargs["channel_id"] == self.channels[0] and kwargs["language"] == "en":
                loop.call_soon_threadsafe(upload_started.set)
                if not release_upload.wait(timeout=5):
                    raise AssertionError("Test did not release upload")
            if kwargs["channel_id"] == self.channels[1]:
                loop.call_soon_threadsafe(other_upload_started.set)
            return upload(**kwargs)

        self.mocks["multiply_audio"].side_effect = controlled_render
        self.mocks["update_audio_module.add"].side_effect = controlled_upload
        task = asyncio.create_task(run_audio_recovery_cycle(now=2000))
        try:
            await asyncio.wait_for(
                asyncio.gather(upload_started.wait(), other_render_started.wait()), timeout=3,
            )
            status = get_audio_recovery_runtime_status()
            jobs = {job["channel_id"]: job for job in status["channels"]}
            self.assertEqual(jobs[self.channels[0]]["phase"], "uploading")
            preparing = jobs[self.channels[1]]
            self.assertEqual(preparing["phase"], "preparing")
            self.assertEqual(preparing["preparation_stage"], "rendering")
            self.assertEqual(preparing["preparation_bytes"], 200)
            self.assertGreaterEqual(preparing["preparation_elapsed_seconds"], 0)
            self.assertNotIn("_preparation_output_path", preparing)
            release_render.set()
            await asyncio.wait_for(other_upload_started.wait(), timeout=3)
            self.assertFalse(release_upload.is_set())
            self.assertTrue(get_audio_mutation_guard(self.channels[0]).locked())
        finally:
            release_render.set()
            release_upload.set()
            result = await self.finish_cycle(task)
        self.assertEqual(result["repaired"], 4)

    async def test_two_channels_can_show_one_finished_while_other_is_still_uploading(self):
        self.channels = self.channels[:2]
        state = get_audio_recovery_state()
        state["entries"] = {channel: state["entries"][channel] for channel in self.channels}
        self.manager.save_state("audio_recovery", state)
        release_slow_channel = threading.Event()
        upload = self.mocks["update_audio_module.add"].side_effect

        def upload_with_slow_channel(**kwargs):
            if kwargs["channel_id"] == self.channels[1] and kwargs["language"] == "en":
                if not release_slow_channel.wait(timeout=5):
                    raise AssertionError("Test did not release slow channel")
            return upload(**kwargs)

        async def wait_for_first_channel_to_finish():
            while True:
                status = get_audio_recovery_runtime_status()
                if status["completed_channel_count"] == 1 and status["active_channel_count"] == 1:
                    return status
                await asyncio.sleep(0.01)

        self.mocks["update_audio_module.add"].side_effect = upload_with_slow_channel
        task = asyncio.create_task(run_audio_recovery_cycle(now=2000))
        try:
            status = await asyncio.wait_for(wait_for_first_channel_to_finish(), timeout=3)
            self.assertEqual(status["channel_total"], 2)
            self.assertEqual(status["channel_concurrency"], 3)
            self.assertEqual(len(status["channels"]), 1)
            self.assertEqual(status["channels"][0]["channel_id"], self.channels[1])
            self.assertEqual(len(status["channel_results"]), 1)
            finished = status["channel_results"][0]
            self.assertEqual(finished["channel_id"], self.channels[0])
            self.assertEqual(finished["submitted"], 2)
            self.assertEqual(finished["outcome"], "submitted")
            self.assertIn("chờ YouTube xử lý", finished["message"])
            self.assertEqual(self.mocks["_get_registered_video_scan_statuses"].call_count, 2)
            self.assertEqual(self.events[self.channels[0]], [
                ("delete", "en"), ("add", "en"), ("delete", "es"), ("add", "es"),
            ])
        finally:
            release_slow_channel.set()
            result = await self.finish_cycle(task)
        self.assertEqual(result["repaired"], 4)
        self.assertEqual(result["scanned_channels"], 2)

    async def test_dns_failure_remains_visible_after_channel_finishes_and_is_saved(self):
        failed_channel = self.channels[0]
        visibility = self.mocks["_get_registered_video_scan_statuses"].side_effect

        def visibility_with_dns_error(channel_id, video_ids, **kwargs):
            if channel_id == failed_channel:
                raise RuntimeError("NameResolutionError: Failed to resolve 'studio.youtube.com' (getaddrinfo failed)")
            return visibility(channel_id, video_ids, **kwargs)

        self.mocks["_get_registered_video_scan_statuses"].side_effect = visibility_with_dns_error
        self.release_uploads.clear()
        task = asyncio.create_task(run_audio_recovery_cycle(now=2000))
        try:
            await self.wait_for_three_uploads()
            status = get_audio_recovery_runtime_status()
            self.assertEqual(status["completed_channel_count"], 1)
            self.assertEqual(status["active_channel_count"], 3)
            report = next(item for item in status["channel_results"] if item["channel_id"] == failed_channel)
            self.assertEqual(report["outcome"], "error")
            self.assertEqual(report["scanned_videos"], 0)
            self.assertEqual(report["submitted"], 0)
            self.assertIn("Lỗi DNS", report["message"])
        finally:
            result = await self.finish_cycle(task)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["repaired"], 8)
        self.assertEqual(self.events[failed_channel], [])
        saved_results = get_audio_recovery_state()["last_cycle_result"]["channel_results"]
        self.assertEqual(saved_results, result["channel_results"])
        saved_failure = next(item for item in saved_results if item["channel_id"] == failed_channel)
        self.assertEqual(saved_failure["outcome"], "error")

    async def test_finished_channel_is_rescanned_and_repaired_while_other_upload_is_running(self):
        self.channels = self.channels[:2]
        fast, slow = self.channels
        state = get_audio_recovery_state()
        state["entries"] = {channel: state["entries"][channel] for channel in self.channels}
        self.manager.save_state("audio_recovery", state)
        loop = asyncio.get_running_loop()
        stop = asyncio.Event()
        release_slow = threading.Event()
        third_read_started = asyncio.Event()
        release_third_read = threading.Event()
        payload = self.mocks["update_audio_module._get_video_translation_payload"].side_effect
        upload = self.mocks["update_audio_module.add"].side_effect
        reads = {channel: 0 for channel in self.channels}

        def fresh_payload(video_ids, channel_id):
            reads[channel_id] += 1
            response = payload(video_ids, channel_id)
            if channel_id == fast and reads[channel_id] >= 2:
                status = "DELETED" if reads[channel_id] == 2 else "PROCESSING"
                for track in response["audioTracks"]:
                    track["status"] = f"AUDIO_TRACK_STATUS_{status}"
                if reads[channel_id] == 3:
                    loop.call_soon_threadsafe(third_read_started.set)
                    if not release_third_read.wait(timeout=5):
                        raise AssertionError("Test did not release the third scan")
            return response

        def slow_upload(**kwargs):
            if kwargs["channel_id"] == slow and kwargs["language"] == "en":
                if not release_slow.wait(timeout=5):
                    raise AssertionError("Test did not release the slow upload")
            return upload(**kwargs)

        async def wait_for_processing_report():
            while True:
                result = get_audio_recovery_state().get("last_cycle_result") or {}
                report = next((r for r in result.get("channel_results", []) if r["channel_id"] == fast), {})
                if report.get("processing_tracks") == 2:
                    return report
                await asyncio.sleep(0.005)

        self.mocks["update_audio_module._get_video_translation_payload"].side_effect = fresh_payload
        self.mocks["update_audio_module.add"].side_effect = slow_upload
        task = asyncio.create_task(run_audio_recovery_cycle(now=2000, stop_event=stop))
        try:
            await asyncio.wait_for(third_read_started.wait(), timeout=3)
            self.assertFalse(release_slow.is_set())
            self.assertTrue(get_audio_mutation_guard(slow).locked())
            self.assertEqual(reads[slow], 1)
            self.assertEqual([event for event in self.events[fast] if event[0] == "add"], [
                ("add", "en"), ("add", "es"), ("add", "en"), ("add", "es"),
            ])
            # Results survive before the slow channel or the monitoring session ends.
            saved = get_audio_recovery_state()["last_cycle_result"]["channel_results"]
            report = next(r for r in saved if r["channel_id"] == fast)
            self.assertEqual(report["pass_count"], 2)
            self.assertEqual(report["submitted"], 2)
            status = get_audio_recovery_runtime_status()
            self.assertEqual(status["channel_total"], 2)
            self.assertEqual(status["active_channel_count"], 2)
            self.assertEqual(status["completed_pass_count"], 2)
            self.assertEqual(status["channel_results"], [])
            self.assertNotIn("_channel_passes", status)
            job = next(job for job in status["channels"] if job["channel_id"] == fast)
            self.assertEqual(job["pass_index"], 3)
            release_third_read.set()
            report = await asyncio.wait_for(wait_for_processing_report(), timeout=3)
            self.assertEqual(report["submitted"], 0)
            self.assertGreaterEqual(report["pass_count"], 3)
            self.assertEqual(len([e for e in self.events[fast] if e[0] == "add"]), 4)
        finally:
            stop.set()
            release_third_read.set()
            release_slow.set()
            result = await asyncio.wait_for(task, timeout=4)
        self.assertFalse(result["cancelled_by_clear"])
        self.assertFalse(get_audio_mutation_guard(fast).locked())
        self.assertFalse(get_audio_mutation_guard(slow).locked())
        self.assertTrue(all(not Path(path).exists() for path in self.temp_files))

    async def test_two_failed_channels_repair_immediately_despite_legacy_grace_or_recent_attempt(self):
        self.channels = self.channels[:2]
        upload = self.mocks["update_audio_module.add"].side_effect
        for legacy_delay in ("initial_grace", "retry_after_success", "retry_after_failure"):
            with self.subTest(legacy_delay=legacy_delay):
                for channel_id in self.channels:
                    self.events[channel_id].clear()
                state = get_audio_recovery_state()
                state["initial_grace_seconds"] = 15 * 60
                state["retry_cooldown_seconds"] = 15 * 60
                state["entries"] = {
                    channel: {f"{channel}-video": {
                        "audio_path": str(self.source), "languages": ["en", "es"],
                    }} for channel in self.channels
                }
                recent_entry = state["entries"][self.channels[0]][f"{self.channels[0]}-video"]
                if legacy_delay == "initial_grace":
                    recent_entry["registered_at"] = 2000
                else:
                    recent_entry["attempts"] = {
                        language: {"attempted_at": 1999, "succeeded": legacy_delay == "retry_after_success"}
                        for language in ("en", "es")
                    }
                self.manager.save_state("audio_recovery", state)
                release_slow_channel = threading.Event()

                def slow_upload(**kwargs):
                    if kwargs["channel_id"] == self.channels[1] and kwargs["language"] == "en":
                        if not release_slow_channel.wait(timeout=5):
                            raise AssertionError("Test did not release slow channel")
                    return upload(**kwargs)

                async def wait_for_repaired_channel_to_finish():
                    while True:
                        status = get_audio_recovery_runtime_status()
                        if status["completed_channel_count"] == 1 and status["active_channel_count"] == 1:
                            return status
                        await asyncio.sleep(0.01)

                self.mocks["update_audio_module.add"].side_effect = slow_upload
                task = asyncio.create_task(run_audio_recovery_cycle(now=2000))
                try:
                    status = await asyncio.wait_for(wait_for_repaired_channel_to_finish(), timeout=3)
                    self.assertEqual(status["channel_total"], 2)
                    report = status["channel_results"][0]
                    self.assertEqual(report["channel_id"], self.channels[0])
                    self.assertEqual(report["submitted"], 2)
                    self.assertEqual(report["outcome"], "submitted")
                    self.assertEqual(report["scanned_videos"], 1)
                    self.assertEqual(report["cooldown_tracks"], 0)
                    self.assertEqual(self.events[self.channels[0]], [
                        ("delete", "en"), ("add", "en"), ("delete", "es"), ("add", "es"),
                    ])
                finally:
                    release_slow_channel.set()
                    result = await self.finish_cycle(task)
                self.assertEqual(result["repaired"], 4)

    async def test_failed_tracks_retry_on_next_scan_immediately_after_submission(self):
        await run_audio_recovery_cycle(now=2000)
        add = self.mocks["update_audio_module.add"]
        add.reset_mock()
        result = await run_audio_recovery_cycle(now=2000)
        self.assertEqual(add.call_count, 10)
        self.assertEqual(result["repaired"], 10)
        self.assertEqual(len(result["channel_results"]), 5)
        for report in result["channel_results"]:
            self.assertEqual(report["outcome"], "submitted")
            self.assertEqual(report["submitted"], 2)
            self.assertEqual(report["cooldown_tracks"], 0)

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

    async def test_continuous_monitor_cancellation_drains_uploads_before_releasing_guards(self):
        self.release_uploads.clear()
        task = asyncio.create_task(run_audio_recovery_cycle(now=2000, stop_event=asyncio.Event()))
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
        self.assertEqual(self.mocks["update_audio_module.add"].call_count, 3)
        self.assertTrue(all(not get_audio_mutation_guard(channel).locked() for channel in self.channels))
        self.assertTrue(all(not Path(path).exists() for path in self.temp_files))
        saved = get_audio_recovery_state()["last_cycle_result"]
        self.assertEqual(saved["repaired"], 3)
        self.assertFalse(saved["cancelled_by_clear"])


if __name__ == "__main__":
    unittest.main()
