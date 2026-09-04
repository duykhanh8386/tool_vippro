import asyncio
import tempfile
import unittest
from pathlib import Path

from web.components.audio import (
    _best_effort_ui as audio_best_effort_ui,
    _cleanup_temp_audio_file,
    _run_sequentially_isolated,
)
from web.components.remove_audio import (
    _best_effort_ui as remove_audio_best_effort_ui,
    _gather_isolated,
)


class AudioPageLifecycleTests(unittest.IsolatedAsyncioTestCase):
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
