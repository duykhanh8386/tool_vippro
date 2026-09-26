import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from web.components.audio import (
    DEFAULT_AUDIO_UPLOAD_CONCURRENCY,
    MAX_AUDIO_UPLOAD_CONCURRENCY,
    MIN_AUDIO_UPLOAD_CONCURRENCY,
    _audio_workflow_signature,
    _best_effort_ui as audio_best_effort_ui,
    _clamp_upload_concurrency,
    _cleanup_temp_audio_file,
    _fetch_all_channel_videos,
    _is_youtube_auth_error,
    _restore_audio_performance_settings,
    _restore_cleanup_statuses,
    _restore_language_statuses,
    _run_concurrently_isolated,
    _run_sequentially_isolated,
    _select_videos_by_ids,
    _upload_progress_summary,
    _video_from_snapshot,
    _video_snapshot,
)
from src.module.model import Video
from web.components.remove_audio import (
    DEFAULT_REMOVE_AUDIO_CONCURRENCY,
    MAX_REMOVE_AUDIO_CONCURRENCY,
    MIN_REMOVE_AUDIO_CONCURRENCY,
    _best_effort_ui as remove_audio_best_effort_ui,
    _clamp_remove_concurrency,
    _fetch_all_channel_videos as fetch_all_remove_audio_channel_videos,
    _gather_isolated,
    _restore_remove_statuses,
)


class AudioPageLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def test_combined_workflow_concurrency_is_limited_to_three_through_five(self):
        self.assertEqual(_clamp_upload_concurrency(None), DEFAULT_AUDIO_UPLOAD_CONCURRENCY)
        self.assertEqual(
            _clamp_upload_concurrency(0), MIN_AUDIO_UPLOAD_CONCURRENCY
        )
        self.assertEqual(
            _clamp_upload_concurrency(99), MAX_AUDIO_UPLOAD_CONCURRENCY
        )

    def test_old_serial_setting_is_migrated_once_then_user_choice_is_kept(self):
        settings, changed = _restore_audio_performance_settings(
            {"max_concurrency": 1}
        )

        self.assertTrue(changed)
        self.assertEqual(settings["max_concurrency"], DEFAULT_AUDIO_UPLOAD_CONCURRENCY)

        settings["max_concurrency"] = MIN_AUDIO_UPLOAD_CONCURRENCY
        restored, changed_again = _restore_audio_performance_settings(settings)
        self.assertFalse(changed_again)
        self.assertEqual(
            restored["max_concurrency"], MIN_AUDIO_UPLOAD_CONCURRENCY
        )

    def test_cleanup_checkpoint_retries_only_interrupted_delete(self):
        restored = _restore_cleanup_statuses(
            {"A": "successful", "B": "processing", "C": "unsuccessful"},
            reset_processing=True,
        )

        self.assertEqual(
            restored,
            {"A": "successful", "B": "pending", "C": "unsuccessful"},
        )

    def test_workflow_signature_changes_when_delete_then_add_inputs_change(self):
        base = _audio_workflow_signature(
            channel_id="channel",
            audio_path="music.mp3",
            languages=["en", "vi"],
            repeat_times=2,
            extra_minutes=0,
        )
        changed_audio = _audio_workflow_signature(
            channel_id="channel",
            audio_path="replacement.mp3",
            languages=["en", "vi"],
            repeat_times=2,
            extra_minutes=0,
        )
        changed_languages = _audio_workflow_signature(
            channel_id="channel",
            audio_path="music.mp3",
            languages=["en"],
            repeat_times=2,
            extra_minutes=0,
        )

        self.assertNotEqual(base, changed_audio)
        self.assertNotEqual(base, changed_languages)

    def test_upload_progress_summary_reports_combined_speed_and_bytes(self):
        summary = _upload_progress_summary(
            [
                {
                    "sent": 1024 * 1024,
                    "total": 2 * 1024 * 1024,
                    "started_at": 90.0,
                    "status": "uploading",
                },
                {
                    "sent": 1024 * 1024,
                    "total": 2 * 1024 * 1024,
                    "started_at": 90.0,
                    "status": "uploading",
                },
            ],
            now=100.0,
        )

        self.assertIn("2 luồng tải", summary)
        self.assertIn("2.0/4.0 MB (50%)", summary)
        self.assertIn("0.2 MB/s", summary)
        self.assertIn("còn khoảng 10 giây", summary)

    async def test_concurrent_audio_queue_respects_worker_limit(self):
        active = 0
        peak = 0

        async def process(_item):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1

        failures = await _run_concurrently_isolated(
            range(8),
            process,
            lambda _item, _exc: None,
            max_concurrency=3,
        )

        self.assertEqual(failures, [])
        self.assertEqual(peak, 3)

    async def test_concurrent_audio_queue_stops_claiming_items_after_auth_error(self):
        attempted = []
        first_started = asyncio.Event()
        auth_failed = asyncio.Event()

        class AuthError(RuntimeError):
            status_code = 401

        async def process(item):
            attempted.append(item)
            if item == "A":
                first_started.set()
                await auth_failed.wait()
            elif item == "B":
                await first_started.wait()
                auth_failed.set()
                raise AuthError("HTTP 401")
            else:
                await auth_failed.wait()

        with self.assertRaises(AuthError):
            await _run_concurrently_isolated(
                ["A", "B", "C", "D"],
                process,
                lambda _item, _exc: None,
                max_concurrency=3,
                stop_on_error=_is_youtube_auth_error,
            )

        self.assertIn("A", attempted)
        self.assertIn("B", attempted)
        self.assertTrue(set(attempted).issubset({"A", "B", "C"}))

    def test_channel_scan_follows_pagination_and_deduplicates_video_ids(self):
        pages = [
            ([SimpleNamespace(id="A")], "next"),
            ([SimpleNamespace(id="A"), SimpleNamespace(id="B")], None),
        ]
        with patch(
            "web.components.audio.list_videos_module.list_all_videos",
            side_effect=pages,
        ) as list_videos:
            videos = _fetch_all_channel_videos("channel")

        self.assertEqual([item.id for item in videos], ["A", "B"])
        self.assertEqual(list_videos.call_count, 2)

    def test_channel_scan_rejects_repeated_page_token(self):
        with patch(
            "web.components.audio.list_videos_module.list_all_videos",
            side_effect=[([], "same"), ([], "same")],
        ):
            with self.assertRaisesRegex(RuntimeError, "phân trang bị lặp"):
                _fetch_all_channel_videos("channel")

    def test_manual_source_filters_channel_videos_in_entered_id_order(self):
        videos = [SimpleNamespace(id="A"), SimpleNamespace(id="B")]

        selected, missing = _select_videos_by_ids(videos, ["B", "A", "B", "X"])

        self.assertEqual([video.id for video in selected], ["B", "A"])
        self.assertEqual(missing, ["X"])

    def test_failed_video_snapshot_preserves_matching_metadata(self):
        original = Video(
            id="video-id",
            channel_id="channel",
            title="Video title",
            description="Description",
            thumbnail="thumbnail",
            duration_ms=123000,
            privacy="PUBLIC",
            video_status="UPLOADED",
            copyright_check_status="DONE",
        )

        restored = _video_from_snapshot(_video_snapshot(original))

        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.channel_id, original.channel_id)
        self.assertEqual(restored.title, original.title)
        self.assertEqual(restored.duration_ms, original.duration_ms)

    def test_add_audio_restart_only_retries_interrupted_languages(self):
        restored = _restore_language_statuses(
            {
                "video-1": {
                    "en": "successful",
                    "vi": "processing",
                    "ja": "already_added",
                }
            },
            reset_processing=True,
        )

        self.assertEqual(restored["video-1"]["en"], "successful")
        self.assertEqual(restored["video-1"]["vi"], "pending")
        self.assertEqual(restored["video-1"]["ja"], "already_added")

    async def test_happy_path_processes_multiple_videos(self):
        processed = []

        async def process(video_id):
            processed.append(video_id)

        failures = await _run_sequentially_isolated(
            ["A", "B", "C"], process, lambda _item, _exc: None
        )

        self.assertEqual(processed, ["A", "B", "C"])
        self.assertEqual(failures, [])

    async def test_one_audio_video_failure_does_not_stop_following_video(self):
        attempted = []
        completed = []
        recorded_errors = []

        async def process(video_id):
            attempted.append(video_id)
            if video_id == "B":
                raise RuntimeError("video B failed")
            completed.append(video_id)

        failures = await _run_sequentially_isolated(
            ["A", "B", "C"],
            process,
            lambda item, exc: recorded_errors.append((item, str(exc))),
        )

        self.assertEqual(attempted, ["A", "B", "C"])
        self.assertEqual(completed, ["A", "C"])
        self.assertEqual(recorded_errors, [("B", "video B failed")])
        self.assertEqual([item for item, _ in failures], ["B"])

    async def test_auth_failure_stops_remaining_batch(self):
        attempted = []

        class AuthError(RuntimeError):
            status_code = 401

        async def process(video_id):
            attempted.append(video_id)
            if video_id == "B":
                raise AuthError("HTTP 401")

        with self.assertRaises(AuthError):
            await _run_sequentially_isolated(
                ["A", "B", "C"],
                process,
                lambda _item, _exc: None,
                stop_on_error=_is_youtube_auth_error,
            )

        self.assertEqual(attempted, ["A", "B"])

    async def test_disconnected_audio_client_skips_ui_and_backend_completes(self):
        backend = []
        persisted = []
        ui_calls = []

        async def process(video_id):
            backend.append(video_id)
            persisted.append((video_id, "successful"))
            updated = audio_best_effort_ui(
                "render success",
                lambda: ui_calls.append(video_id),
                is_available=lambda: False,
            )
            self.assertFalse(updated)

        failures = await _run_sequentially_isolated(
            ["A", "B"], process, lambda _item, _exc: None
        )

        self.assertEqual(failures, [])
        self.assertEqual(backend, ["A", "B"])
        self.assertEqual(
            persisted,
            [("A", "successful"), ("B", "successful")],
        )
        self.assertEqual(ui_calls, [])

    async def test_audio_ui_exception_cannot_block_backend_or_checkpoint(self):
        events = []

        def broken_ui():
            events.append("ui")
            raise RuntimeError("deleted client")

        async def process(video_id):
            audio_best_effort_ui("render pending", broken_ui)
            events.append(f"backend:{video_id}")
            events.append(f"persist:{video_id}")
            audio_best_effort_ui("render success", broken_ui)

        failures = await _run_sequentially_isolated(
            ["A"], process, lambda _item, _exc: None
        )

        self.assertEqual(failures, [])
        self.assertIn("backend:A", events)
        self.assertIn("persist:A", events)

    async def test_audio_cleanup_runs_when_ui_raises(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        output_path = Path(temp_dir.name) / "audio.tmp"
        output_path.write_bytes(b"temporary audio")

        async def process(video_id):
            try:
                audio_best_effort_ui(
                    "render",
                    lambda: (_ for _ in ()).throw(RuntimeError("deleted client")),
                )
            finally:
                _cleanup_temp_audio_file(output_path)

        failures = await _run_sequentially_isolated(
            ["A"], process, lambda _item, _exc: None
        )

        self.assertEqual(failures, [])
        self.assertFalse(output_path.exists())


class RemoveAudioPageLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def test_remove_audio_concurrency_is_limited_to_three_through_five(self):
        self.assertEqual(
            _clamp_remove_concurrency(None), DEFAULT_REMOVE_AUDIO_CONCURRENCY
        )
        self.assertEqual(_clamp_remove_concurrency(1), MIN_REMOVE_AUDIO_CONCURRENCY)
        self.assertEqual(_clamp_remove_concurrency(99), MAX_REMOVE_AUDIO_CONCURRENCY)

    def test_remove_audio_channel_scan_paginates_and_deduplicates(self):
        pages = [
            ([SimpleNamespace(id="A"), SimpleNamespace(id="A")], "next"),
            ([SimpleNamespace(id="B")], None),
        ]
        with patch(
            "web.components.remove_audio.list_videos_module.list_all_videos",
            side_effect=pages,
        ):
            videos = fetch_all_remove_audio_channel_videos("channel")

        self.assertEqual([video.id for video in videos], ["A", "B"])

    def test_remove_audio_restart_only_retries_interrupted_videos(self):
        restored = _restore_remove_statuses(
            {"A": "successful", "B": "processing", "C": "unsuccessful"},
            reset_processing=True,
        )

        self.assertEqual(
            restored,
            {"A": "successful", "B": "pending", "C": "unsuccessful"},
        )

    async def test_remove_audio_happy_path_processes_multiple_videos(self):
        completed = []

        async def worker(video_id):
            await asyncio.sleep(0)
            completed.append(video_id)
            return video_id

        results = await _gather_isolated(
            [worker(video_id) for video_id in ["A", "B", "C"]]
        )

        self.assertCountEqual(completed, ["A", "B", "C"])
        self.assertCountEqual(results, ["A", "B", "C"])

    async def test_remove_audio_worker_failure_is_isolated(self):
        attempted = []

        async def worker(video_id):
            attempted.append(video_id)
            await asyncio.sleep(0)
            if video_id == "B":
                raise RuntimeError("video B failed")
            return video_id

        results = await _gather_isolated(
            [worker(video_id) for video_id in ["A", "B", "C"]]
        )

        self.assertCountEqual(attempted, ["A", "B", "C"])
        self.assertEqual(results[0], "A")
        self.assertIsInstance(results[1], RuntimeError)
        self.assertEqual(results[2], "C")

    async def test_disconnected_remove_audio_client_skips_ui(self):
        backend = []
        ui_calls = []

        async def worker(video_id):
            backend.append(video_id)
            updated = remove_audio_best_effort_ui(
                "render success",
                lambda: ui_calls.append(video_id),
                is_available=lambda: False,
            )
            self.assertFalse(updated)

        results = await _gather_isolated([worker("A"), worker("B")])

        self.assertEqual(results, [None, None])
        self.assertCountEqual(backend, ["A", "B"])
        self.assertEqual(ui_calls, [])

    async def test_remove_audio_ui_failure_preserves_backend_state_and_cleanup(self):
        persisted = []
        cleanup = []

        async def worker(video_id):
            try:
                state = "successful"
                persisted.append((video_id, state))
                remove_audio_best_effort_ui(
                    "render success",
                    lambda: (_ for _ in ()).throw(RuntimeError("deleted client")),
                )
            finally:
                cleanup.append(video_id)

        results = await _gather_isolated([worker("A"), worker("B")])

        self.assertEqual(results, [None, None])
        self.assertEqual(
            persisted,
            [("A", "successful"), ("B", "successful")],
        )
        self.assertCountEqual(cleanup, ["A", "B"])


if __name__ == "__main__":
    unittest.main()
