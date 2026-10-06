import asyncio
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from web.components.audio import (
    DEFAULT_AUDIO_UPLOAD_CONCURRENCY,
    DEFAULT_RECENT_VIDEO_LIMIT,
    MAX_AUDIO_UPLOAD_CONCURRENCY,
    MAX_RECENT_VIDEO_LIMIT,
    MIN_AUDIO_UPLOAD_CONCURRENCY,
    _audio_workflow_signature,
    _ADD_AUDIO_RUN_GUARD,
    _best_effort_ui as audio_best_effort_ui,
    _clear_audio_ui_workflow_data,
    _clamp_upload_concurrency,
    _cleanup_temp_audio_file,
    _fetch_channel_videos,
    _fetch_all_channel_videos,
    _is_draft_video,
    _is_youtube_auth_error,
    _normalize_recent_video_limit,
    _restore_audio_performance_settings,
    _restore_audio_path_history,
    _restore_cleanup_statuses,
    _restore_language_statuses,
    _run_concurrently_isolated,
    _run_client_independent,
    _run_in_target_slot,
    _run_sequentially_isolated,
    _own_audio_run_lock,
    _remember_audio_path_history,
    _select_videos_by_ids,
    _select_terminal_repair_actions,
    _stop_active_audio_runs,
    _upload_progress_summary,
    _video_from_snapshot,
    _video_snapshot,
)
from src.audio_recovery import get_audio_mutation_guard
from src.module.model import Video
from src.module.list_videos_module import ListVideosModule
from src.utils import multiply_audio
from src.task_runtime import check_stopped
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
    def test_manual_run_state_is_separate_from_automatic_recovery_guard(self):
        self.assertIsNot(_ADD_AUDIO_RUN_GUARD, get_audio_mutation_guard("channel"))

    def test_clear_page_data_preserves_the_separate_recovery_registry(self):
        video_ids_state = {"ids": ["video-a"]}
        page_maps = [
            {"video-a": "audio.mp3"},
            {"video-a": {"en": "processing"}},
            {"video-a": {"en": "failed"}},
        ]
        recovery_registry = {
            "channel-a": {
                "video-a": {
                    "audio_path": "audio.mp3",
                    "languages": ["en"],
                }
            }
        }

        _clear_audio_ui_workflow_data(video_ids_state, *page_maps)

        self.assertEqual(video_ids_state["ids"], [])
        self.assertTrue(all(mapping == {} for mapping in page_maps))
        self.assertIn("video-a", recovery_registry["channel-a"])

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

    def test_error_scan_plan_keeps_only_selected_terminal_languages(self):
        targets = {
            "video-a": [
                {
                    "language": "es",
                    "track_ids": ["failed-es", "failed-es"],
                    "reason": "terminal",
                }
            ],
            "video-b": [
                {
                    "language": "pt-PT",
                    "track_ids": ["failed-pt"],
                    "reason": "terminal",
                }
            ],
        }

        selected = _select_terminal_repair_actions(
            targets,
            ["video-a", "video-b"],
            ["en", "ES"],
        )

        self.assertEqual(
            selected,
            {
                "video-a": [
                    {
                        "language": "ES",
                        "track_ids": ["failed-es"],
                        "reason": "terminal",
                    }
                ]
            },
        )

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

    def test_public_scan_keeps_only_public_videos(self):
        videos = [
            SimpleNamespace(id="public", privacy="VIDEO_PRIVACY_PUBLIC"),
            SimpleNamespace(id="private", privacy="VIDEO_PRIVACY_PRIVATE"),
            SimpleNamespace(id="unlisted", privacy="VIDEO_PRIVACY_UNLISTED"),
        ]
        with patch(
            "web.components.audio.list_videos_module.list_all_videos",
            return_value=(videos, None),
        ):
            selected = _fetch_channel_videos("channel", scope="public")

        self.assertEqual([video.id for video in selected], ["public"])

    def test_draft_scan_requests_the_server_side_draft_filter(self):
        videos = [
            SimpleNamespace(
                id="draft-enum",
                privacy="VIDEO_PRIVACY_PRIVATE",
                draft_status="VIDEO_DRAFT_STATUS_DRAFT",
            ),
            SimpleNamespace(
                id="draft-object",
                privacy="VIDEO_PRIVACY_PRIVATE",
                draft_status={"isDraft": True},
            ),
            SimpleNamespace(
                id="draft-status-fallback",
                privacy="VIDEO_PRIVACY_PRIVATE",
                draft_status="",
                video_status="VIDEO_STATUS_DRAFT",
            ),
        ]
        with patch(
            "web.components.audio.list_videos_module.list_all_videos",
            return_value=(videos, None),
        ) as list_videos:
            selected = _fetch_channel_videos("channel", scope="draft")

        self.assertEqual(
            [video.id for video in selected],
            ["draft-enum", "draft-object", "draft-status-fallback"],
        )
        self.assertTrue(list_videos.call_args.kwargs["draft_only"])
        self.assertFalse(
            _is_draft_video(
                SimpleNamespace(
                    privacy="VIDEO_PRIVACY_PRIVATE",
                    draft_status="VIDEO_DRAFT_STATUS_NONE",
                )
            )
        )

    def test_studio_draft_request_contains_is_draft_operand(self):
        channel = SimpleNamespace(
            id="channel",
            delegated_session_id="delegate",
            role="CREATOR_CHANNEL_ROLE_TYPE_OWNER",
            sapisidhash="hash",
            cookies=[{"name": "SAPISID", "value": "cookie-secret"}],
            cookie_string=lambda: "SID=value",
        )
        response = SimpleNamespace(status_code=200, json=lambda: {"videos": []})
        module = ListVideosModule()

        with (
            patch(
                "src.module.list_videos_module.get_channels_info",
                return_value=channel,
            ),
            patch.object(module, "_get_session_token", return_value="token"),
            patch(
                "src.module.list_videos_module.post_with_stop",
                return_value=response,
            ) as post,
        ):
            module.list_all_videos("channel", draft_only=True)

        operands = post.call_args.kwargs["json"]["filter"]["and"]["operands"]
        self.assertIn({"isDraft": {}}, operands)

    def test_recent_scan_stops_at_selected_newest_video_count(self):
        pages = [
            ([SimpleNamespace(id="A"), SimpleNamespace(id="B")], "next"),
            ([SimpleNamespace(id="C"), SimpleNamespace(id="D")], None),
        ]
        with patch(
            "web.components.audio.list_videos_module.list_all_videos",
            side_effect=pages,
        ) as list_videos:
            selected = _fetch_channel_videos(
                "channel", scope="recent", recent_limit=3
            )

        self.assertEqual([video.id for video in selected], ["A", "B", "C"])
        self.assertEqual(list_videos.call_args_list[0].kwargs["limit"], 3)
        self.assertEqual(list_videos.call_args_list[1].kwargs["limit"], 1)

    def test_recent_scan_limit_is_bounded(self):
        self.assertEqual(
            _normalize_recent_video_limit(None), DEFAULT_RECENT_VIDEO_LIMIT
        )
        self.assertEqual(_normalize_recent_video_limit(0), 1)
        self.assertEqual(
            _normalize_recent_video_limit(MAX_RECENT_VIDEO_LIMIT + 1),
            MAX_RECENT_VIDEO_LIMIT,
        )

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
            draft_status="VIDEO_DRAFT_STATUS_DRAFT",
        )

        restored = _video_from_snapshot(_video_snapshot(original))

        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.channel_id, original.channel_id)
        self.assertEqual(restored.title, original.title)
        self.assertEqual(restored.duration_ms, original.duration_ms)
        self.assertEqual(restored.draft_status, original.draft_status)

    def test_previous_audio_path_is_restored_when_failed_video_is_scanned_again(self):
        history = {}
        remembered = _remember_audio_path_history(
            history,
            "channel-a",
            {"video-a": "D:/music/shared.mp3", "video-b": ""},
        )

        restored = _restore_audio_path_history(
            history, "channel-a", ["video-a", "video-c"]
        )

        self.assertEqual(remembered, 1)
        self.assertEqual(restored, {"video-a": "D:/music/shared.mp3"})
        self.assertEqual(
            _restore_audio_path_history(history, "channel-b", ["video-a"]), {}
        )

    async def test_client_cancellation_does_not_cancel_backend_audio_job(self):
        started = asyncio.Event()
        release = asyncio.Event()
        finished = asyncio.Event()

        async def backend_job():
            started.set()
            await release.wait()
            finished.set()

        client_task = asyncio.create_task(
            _run_client_independent(backend_job())
        )
        await started.wait()
        client_task.cancel()
        await client_task
        self.assertFalse(finished.is_set())

        release.set()
        await asyncio.wait_for(finished.wait(), timeout=1)

    async def test_stop_releases_owned_worker_lock_and_allows_next_run(self):
        worker_lock = threading.Lock()
        first_started = asyncio.Event()
        ui_checkpoint = {"video-a": {"en": "processing"}}

        async def first_job():
            self.assertTrue(_ADD_AUDIO_RUN_GUARD.acquire(blocking=False))
            _own_audio_run_lock(_ADD_AUDIO_RUN_GUARD)
            self.assertTrue(worker_lock.acquire(blocking=False))
            _own_audio_run_lock(worker_lock)
            first_started.set()
            while True:
                await asyncio.sleep(0.01)
                check_stopped()

        first_client_task = asyncio.create_task(
            _run_client_independent(first_job())
        )
        await asyncio.wait_for(first_started.wait(), timeout=1)

        self.assertEqual(await _stop_active_audio_runs(), 1)
        await asyncio.wait_for(first_client_task, timeout=1)
        self.assertFalse(_ADD_AUDIO_RUN_GUARD.locked())
        self.assertFalse(worker_lock.locked())
        self.assertEqual(ui_checkpoint, {"video-a": {"en": "processing"}})

        second_finished = asyncio.Event()

        async def second_job():
            self.assertTrue(_ADD_AUDIO_RUN_GUARD.acquire(blocking=False))
            _own_audio_run_lock(_ADD_AUDIO_RUN_GUARD)
            self.assertTrue(worker_lock.acquire(blocking=False))
            _own_audio_run_lock(worker_lock)
            second_finished.set()

        await asyncio.wait_for(
            _run_client_independent(second_job()),
            timeout=1,
        )
        self.assertTrue(second_finished.is_set())
        self.assertFalse(_ADD_AUDIO_RUN_GUARD.locked())
        self.assertFalse(worker_lock.locked())

    async def test_stop_manual_worker_does_not_release_auto_registry_guard(self):
        registry_guard = get_audio_mutation_guard("registry-owned-channel")
        self.assertTrue(registry_guard.acquire(blocking=False))
        try:
            self.assertEqual(await _stop_active_audio_runs(), 0)
            self.assertTrue(registry_guard.locked())
        finally:
            registry_guard.release()

    async def test_detached_audio_job_enters_the_page_target_slot(self):
        events = []

        class FakeContainer:
            def __enter__(self):
                events.append("enter")
                return self

            def __exit__(self, *_args):
                events.append("exit")

        async def backend_job():
            events.append("job")

        await _run_in_target_slot(FakeContainer(), backend_job())

        self.assertEqual(events, ["enter", "job", "exit"])

    def test_multiply_audio_encodes_one_mp3_audio_stream_directly(self):
        with (
            patch("src.utils.get_video_duration", return_value=30),
            patch("src.utils.run_owned_process") as run_process,
        ):
            multiply_audio("source.m4a", "output.mp3", times=2)

        command = run_process.call_args.args[0]
        self.assertIn("-map", command)
        self.assertIn("0:a:0", command)
        self.assertIn("-vn", command)
        self.assertIn("libmp3lame", command)
        self.assertNotIn("copy", command)
        run_process.assert_called_once()

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
