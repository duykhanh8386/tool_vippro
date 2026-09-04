import asyncio
import threading
import unittest

from web.components.add_audio_flow import (
    _best_effort_ui,
    _persist_then_ui,
    _replace_status_snapshot,
    _replace_video_items_unless_processing,
    _require_checkpoint,
    _restore_steps,
    _run_finalizers,
    _run_supervised_queue,
    _upload_resume_point,
)


class AddAudioFlowHardeningTests(unittest.IsolatedAsyncioTestCase):
    async def test_happy_path_drains_all_items_with_parallel_workers(self):
        processed = []
        state = {item: "pending" for item in range(12)}
        persisted = []

        async def process_item(item):
            await asyncio.sleep(0)
            processed.append(item)
            state[item] = "successful"
            persisted.append(dict(state))

        errors, remaining = await _run_supervised_queue(
            list(range(12)),
            5,
            process_item,
            lambda: False,
            lambda item, exc: self.fail(f"unexpected error for {item}: {exc}"),
        )

        self.assertEqual(sorted(processed), list(range(12)))
        self.assertTrue(all(value == "successful" for value in persisted[-1].values()))
        self.assertEqual(errors, [])
        self.assertEqual(remaining, [])

    async def test_business_failure_does_not_stop_other_items(self):
        states = {name: "pending" for name in "ABCD"}

        async def process_item(item):
            await asyncio.sleep(0)
            if item == "B":
                states[item] = "failed"
                return
            states[item] = "successful"

        errors, remaining = await _run_supervised_queue(
            list(states),
            2,
            process_item,
            lambda: False,
            lambda item, exc: self.fail(f"unexpected error for {item}: {exc}"),
        )

        self.assertEqual(
            states,
            {"A": "successful", "B": "failed", "C": "successful", "D": "successful"},
        )
        self.assertEqual(errors, [])
        self.assertEqual(remaining, [])

    async def test_unexpected_item_exception_is_reported_and_queue_continues(self):
        processed = []
        reported = []

        async def process_item(item):
            processed.append(item)
            if item == "B":
                raise RuntimeError("unexpected")

        errors, remaining = await _run_supervised_queue(
            ["A", "B", "C", "D"],
            2,
            process_item,
            lambda: False,
            lambda item, exc: reported.append((item, str(exc))),
        )

        self.assertCountEqual(processed, ["A", "B", "C", "D"])
        self.assertEqual(reported, [("B", "unexpected")])
        self.assertEqual([str(error) for error in errors], ["unexpected"])
        self.assertEqual(remaining, [])

    async def test_fatal_worker_exit_cannot_leave_queue_silently(self):
        class WorkerCrash(BaseException):
            pass

        processed = []

        async def process_item(item):
            processed.append(item)
            raise WorkerCrash("worker crashed")

        with self.assertRaisesRegex(RuntimeError, "queue còn 2 item"):
            await asyncio.wait_for(
                _run_supervised_queue(
                    ["A", "B", "C"],
                    1,
                    process_item,
                    lambda: False,
                    lambda item, exc: self.fail("BaseException must reach supervision"),
                ),
                timeout=1,
            )

        self.assertEqual(processed, ["A"])

    async def test_intentional_stop_returns_unclaimed_items_for_retry(self):
        stop = {"value": False}
        processed = []

        async def process_item(item):
            processed.append(item)
            stop["value"] = True

        errors, remaining = await _run_supervised_queue(
            ["A", "B", "C"],
            1,
            process_item,
            lambda: stop["value"],
            lambda item, exc: self.fail(f"unexpected error for {item}: {exc}"),
        )

        self.assertEqual(processed, ["A"])
        self.assertEqual(remaining, ["B", "C"])
        self.assertEqual(errors, [])

    def test_backend_checkpoint_is_persisted_before_failing_ui(self):
        state = {
            "status": "processing",
            "frontend_upload_id": "",
            "scotty_resource_id": "",
            "video_id": "",
        }
        snapshots = []

        state.update(
            status="successful",
            frontend_upload_id="frontend-id",
            scotty_resource_id="scotty-id",
            video_id="video-id",
        )
        _persist_then_ui(
            lambda: snapshots.append(dict(state)),
            [("render success", lambda: (_ for _ in ()).throw(RuntimeError("deleted client")))],
        )

        self.assertEqual(
            snapshots,
            [
                {
                    "status": "successful",
                    "frontend_upload_id": "frontend-id",
                    "scotty_resource_id": "scotty-id",
                    "video_id": "video-id",
                }
            ],
        )

    def test_unavailable_client_skips_ui_without_touching_backend(self):
        called = []
        result = _best_effort_ui(
            "render",
            lambda: called.append(True),
            is_available=lambda: False,
        )
        self.assertFalse(result)
        self.assertEqual(called, [])

    async def test_client_loss_mid_run_keeps_backend_persistence_and_cleanup(self):
        ui_available = {"value": True}
        states = {item: "pending" for item in "ABC"}
        persisted = []
        rendered = []
        cleanup = []

        async def process_item(item):
            await asyncio.sleep(0)
            if item == "B":
                ui_available["value"] = False
            states[item] = "successful"
            persisted.append(dict(states))
            _best_effort_ui(
                f"render {item}",
                lambda: rendered.append(item),
                is_available=lambda: ui_available["value"],
            )

        errors, remaining = await _run_supervised_queue(
            list(states),
            1,
            process_item,
            lambda: False,
            lambda item, exc: self.fail(f"unexpected error for {item}: {exc}"),
        )
        _run_finalizers([("cleanup", lambda: cleanup.append(True))])

        self.assertEqual(states, {"A": "successful", "B": "successful", "C": "successful"})
        self.assertTrue(all(value == "successful" for value in persisted[-1].values()))
        self.assertEqual(rendered, ["A"])
        self.assertEqual(cleanup, [True])
        self.assertEqual(errors, [])
        self.assertEqual(remaining, [])

    def test_cleanup_and_guard_release_survive_ui_cleanup_error(self):
        guard = threading.Lock()
        guard.acquire()
        calls = []

        errors = _run_finalizers(
            [
                ("persist", lambda: calls.append("persist")),
                ("cleanup", lambda: calls.append("cleanup")),
                ("release", lambda: (guard.release(), calls.append("release"))),
                ("ui cleanup", lambda: (_ for _ in ()).throw(RuntimeError("deleted client"))),
            ]
        )

        self.assertEqual(calls, ["persist", "cleanup", "release"])
        self.assertFalse(guard.locked())
        self.assertEqual([str(error) for error in errors], ["deleted client"])

    def test_reload_preserves_terminal_state_and_only_recovers_stale_processing(self):
        saved = {
            "merge": "successful",
            "upload": "unsuccessful",
            "wait": "processing",
            "add_audio": "pending",
        }

        detached_live = _restore_steps(saved, reset_processing=False)
        crashed_run = _restore_steps(saved, reset_processing=True)

        self.assertEqual(detached_live, saved)
        self.assertEqual(crashed_run["merge"], "successful")
        self.assertEqual(crashed_run["upload"], "unsuccessful")
        self.assertEqual(crashed_run["wait"], "pending")

    def test_reattach_refreshes_snapshot_used_by_later_list_rebuild(self):
        snapshot = {
            "video.mp4": {
                "steps": {
                    "merge": "successful",
                    "upload": "processing",
                    "wait": "pending",
                    "add_audio": "pending",
                }
            }
        }
        terminal = {
            "video.mp4": {
                "steps": {
                    "merge": "successful",
                    "upload": "successful",
                    "wait": "successful",
                    "add_audio": "unsuccessful",
                }
            }
        }

        _replace_status_snapshot(snapshot, terminal)
        rebuilt = _restore_steps(
            snapshot["video.mp4"]["steps"],
            reset_processing=True,
        )

        self.assertEqual(rebuilt["upload"], "successful")
        self.assertEqual(rebuilt["wait"], "successful")
        self.assertEqual(rebuilt["add_audio"], "unsuccessful")

    def test_delayed_reload_cannot_replace_items_owned_by_active_workers(self):
        active_item = {"name": "video.mp4", "steps": {"upload": "processing"}}
        videos_state = {"items": [active_item]}
        delayed_reload_items = [
            {"name": "video.mp4", "steps": {"upload": "pending"}}
        ]

        replaced = _replace_video_items_unless_processing(
            videos_state,
            delayed_reload_items,
            is_processing=True,
        )

        self.assertFalse(replaced)
        self.assertIs(videos_state["items"][0], active_item)

    def test_upload_resume_point_reuses_persisted_remote_ids(self):
        self.assertEqual(_upload_resume_point({}), "upload")
        self.assertEqual(
            _upload_resume_point(
                {
                    "frontend_upload_id": "frontend-id",
                    "scotty_resource_id": "scotty-id",
                }
            ),
            "create_video",
        )
        self.assertEqual(
            _upload_resume_point(
                {
                    "frontend_upload_id": "frontend-id",
                    "scotty_resource_id": "scotty-id",
                    "video_id": "video-id",
                }
            ),
            "done",
        )

    def test_failed_remote_id_checkpoint_blocks_the_next_side_effect(self):
        with self.assertRaisesRegex(RuntimeError, "upload resource IDs"):
            _require_checkpoint(lambda: False, "upload resource IDs")


if __name__ == "__main__":
    unittest.main()
