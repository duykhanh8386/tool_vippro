import asyncio
import copy
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.state_manager import StateManager
from web.components.delete_video_controller import DeleteVideoController
from web.components.delete_back_flow import (
    ORIGINAL_AUDIO_RENDER_MODE,
    PERSIST_FIELDS,
    _repair_missing_upload_input,
    _replace_video_items_unless_processing,
    _require_checkpoint,
    _restore_delete_back_steps,
    _restore_steps,
    _upload_resume_point,
)


class DeleteBackFlowRecoveryTests(unittest.TestCase):
    def test_interrupted_step_is_retryable_without_losing_completed_steps(self):
        recovered = _restore_steps(
            {
                "merge": "successful",
                "upload": "successful",
                "wait": "processing",
                "delete_back": "pending",
            },
            reset_processing=True,
        )

        self.assertEqual(recovered["merge"], "successful")
        self.assertEqual(recovered["upload"], "successful")
        self.assertEqual(recovered["wait"], "pending")
        self.assertEqual(recovered["delete_back"], "pending")

    def test_live_background_run_keeps_processing_status_for_page_reattach(self):
        steps = {"merge": "successful", "upload": "processing"}

        self.assertEqual(
            _restore_steps(steps, reset_processing=False)["upload"], "processing"
        )

    def test_resume_uses_saved_remote_ids(self):
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

    def test_failed_checkpoint_prevents_next_remote_request(self):
        with self.assertRaisesRegex(RuntimeError, "upload resource IDs"):
            _require_checkpoint(lambda: False, "upload resource IDs")

    def test_refresh_does_not_detach_active_worker_item(self):
        current = {"name": "video.mp4", "steps": {"upload": "processing"}}
        state = {"items": [current]}

        replaced = _replace_video_items_unless_processing(
            state,
            [{"name": "video.mp4", "steps": {"upload": "pending"}}],
            is_processing=True,
        )

        self.assertFalse(replaced)
        self.assertIs(state["items"][0], current)

    def test_delete_intent_is_checkpointed_for_safe_recovery(self):
        self.assertIn("delete_requested", PERSIST_FIELDS)

    def test_legacy_gated_render_is_retried_before_upload(self):
        saved = {"steps": {"merge": "successful", "upload": "pending"}}

        restored = _restore_delete_back_steps(saved, reset_processing=True)

        self.assertEqual(restored["merge"], "pending")
        self.assertEqual(restored["upload"], "pending")
        self.assertEqual(saved["steps"]["merge"], "successful")

    def test_original_music_render_checkpoint_is_preserved(self):
        saved = {
            "steps": {"merge": "successful"},
            "render_audio_mode": ORIGINAL_AUDIO_RENDER_MODE,
        }

        self.assertEqual(
            _restore_delete_back_steps(saved, reset_processing=True)["merge"],
            "successful",
        )
        self.assertIn("render_audio_mode", PERSIST_FIELDS)

    def test_legacy_render_is_not_repeated_after_remote_side_effects(self):
        for field in (
            "video_id", "frontend_upload_id", "scotty_resource_id", "delete_requested"
        ):
            with self.subTest(field=field):
                saved = {"steps": {"merge": "successful"}, field: "saved-id"}
                self.assertEqual(
                    _restore_delete_back_steps(saved, reset_processing=True)["merge"],
                    "successful",
                )

    def test_completed_or_live_legacy_flow_is_not_reset(self):
        completed = {"steps": {key: "successful" for key in (
            "merge", "upload", "wait", "delete_back"
        )}}
        self.assertEqual(
            _restore_delete_back_steps(completed, reset_processing=True),
            completed["steps"],
        )
        live = {"steps": {"merge": "successful", "upload": "processing"}}
        restored = _restore_delete_back_steps(live, reset_processing=False)
        self.assertEqual(restored["merge"], "successful")
        self.assertEqual(restored["upload"], "processing")

    def test_missing_merged_output_restarts_local_pipeline(self):
        item = {
            "output_path": "",
            "steps": {
                "merge": "successful",
                "upload": "error",
                "wait": "pending",
                "delete_back": "pending",
            },
        }

        self.assertTrue(_repair_missing_upload_input(item))
        self.assertEqual(
            item["steps"],
            {
                "merge": "pending",
                "upload": "pending",
                "wait": "pending",
                "delete_back": "pending",
            },
        )

    def test_existing_merged_output_is_kept(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as output:
            item = {
                "output_path": output.name,
                "steps": {
                    "merge": "successful",
                    "upload": "error",
                    "wait": "pending",
                    "delete_back": "pending",
                },
            }

            self.assertFalse(_repair_missing_upload_input(item))
            self.assertEqual(item["steps"]["merge"], "successful")

    def test_remote_upload_checkpoint_does_not_need_local_output(self):
        item = {
            "output_path": "",
            "frontend_upload_id": "frontend-id",
            "scotty_resource_id": "scotty-id",
            "steps": {
                "merge": "successful",
                "upload": "processing",
                "wait": "pending",
                "delete_back": "pending",
            },
        }

        self.assertFalse(_repair_missing_upload_input(item))
        self.assertEqual(item["steps"]["merge"], "successful")

    def test_successful_upload_is_never_retried_without_remote_ids(self):
        item = {
            "output_path": "",
            "steps": {
                "merge": "successful",
                "upload": "successful",
                "wait": "successful",
                "delete_back": "successful",
            },
        }

        self.assertFalse(_repair_missing_upload_input(item))
        self.assertEqual(item["steps"]["upload"], "successful")


class StateManagerDurabilityTests(unittest.TestCase):
    def test_state_database_uses_full_synchronous_commits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("src.state_manager.get_data_dir", return_value=Path(temp_dir)):
                manager = StateManager()
                self.assertTrue(manager.save_state("recovery-test", {"saved": True}))
                self.assertEqual(manager.load_state("recovery-test"), {"saved": True})
                synchronous = manager._get_conn().execute("PRAGMA synchronous").fetchone()[0]
                self.assertEqual(synchronous, 2)  # SQLite FULL
                manager._conn.close()


class DeleteVideoControllerRecoveryTests(unittest.TestCase):
    def test_scan_queue_is_restored_and_interrupted_delete_is_retryable(self):
        class MemoryStateManager:
            def __init__(self):
                self.states = {}

            def save_state(self, key, value):
                self.states[key] = value
                return True

            def load_state(self, key):
                return self.states.get(key)

        memory_state = MemoryStateManager()
        with patch("web.components.delete_video_controller.state_manager", memory_state):
            controller = DeleteVideoController()
            controller.selected_channel_ids = ["channel-1"]
            controller.all_videos = [
                {
                    "id": "video-1",
                    "channel_id": "channel-1",
                    "row_status": "deleting",
                    "delete_requested": True,
                },
                {
                    "id": "video-2",
                    "channel_id": "channel-1",
                    "row_status": "deleted",
                    "delete_requested": False,
                },
            ]
            controller._save_run_state()

            restored = DeleteVideoController()

        self.assertEqual(restored.selected_channel_ids, ["channel-1"])
        self.assertEqual(restored.all_videos[0]["row_status"], "ready")
        self.assertTrue(restored.all_videos[0]["delete_requested"])
        self.assertEqual(restored.all_videos[1]["row_status"], "deleted")
        self.assertEqual(
            restored.all_videos[1]["video_url"],
            "https://www.youtube.com/watch?v=video-2",
        )


class DeleteVideoHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_stopped_scan_keeps_rows_after_controller_reload(self):
        class MemoryStateManager:
            def __init__(self):
                self.states = {}

            def save_state(self, key, value):
                self.states[key] = copy.deepcopy(value)
                return True

            def load_state(self, key):
                return copy.deepcopy(self.states.get(key))

        memory_state = MemoryStateManager()
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "web.components.delete_video_controller.state_manager", memory_state
        ), patch(
            "web.components.delete_video_controller._load_output_dir",
            return_value=Path(temp_dir),
        ):
            controller = DeleteVideoController()
            controller.all_videos = [
                {
                    "id": "finished-id",
                    "channel_id": "channel-id",
                    "row_status": "deleted",
                    "delete_requested": False,
                }
            ]

            async def no_scan(_channel_id, _semaphore):
                await asyncio.sleep(0)

            with patch.object(controller, "refresh_channel_maps"), patch.object(
                controller, "_process_channel", side_effect=no_scan
            ):
                controller.start(["channel-id"])
                await asyncio.sleep(0)
                await controller.stop()

            restored = DeleteVideoController()

        self.assertEqual(restored.all_videos[0]["id"], "finished-id")
        self.assertEqual(restored.all_videos[0]["row_status"], "deleted")
        self.assertEqual(
            restored.all_videos[0]["video_url"],
            "https://www.youtube.com/watch?v=finished-id",
        )

    def test_deleted_rows_restore_from_csv_when_checkpoint_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "deleted_videos.csv"
            log_file.write_text(
                "video_id,channel_id,channel_name,deleted_at\n"
                "saved-id,channel-id,Channel,2026-09-01 12:00:00\n",
                encoding="utf-8",
            )

            class MemoryStateManager:
                def __init__(self):
                    self.states = {"delete_video_settings": {"output_dir": temp_dir}}

                def save_state(self, key, value):
                    self.states[key] = value
                    return True

                def load_state(self, key):
                    return self.states.get(key)

            memory_state = MemoryStateManager()
            with patch("web.components.delete_video_controller.state_manager", memory_state):
                controller = DeleteVideoController()

            self.assertEqual(len(controller.all_videos), 1)
            self.assertEqual(controller.all_videos[0]["row_status"], "deleted")
            self.assertEqual(
                controller.all_videos[0]["video_url"],
                "https://www.youtube.com/watch?v=saved-id",
            )
            self.assertEqual(
                memory_state.load_state("delete_video_run")["all_videos"][0]["id"],
                "saved-id",
            )

    def test_existing_delete_log_gains_links_without_losing_old_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "web.components.delete_video_controller.state_manager"
        ) as memory_state:
            memory_state.load_state.return_value = None
            controller = DeleteVideoController()
            controller.output_dir = Path(temp_dir)
            controller.log_file.write_text(
                "video_id,channel_id,channel_name,deleted_at\n"
                "old-id,old-channel,Old,2026-09-01 12:00:00\n",
                encoding="utf-8",
            )

            self.assertTrue(controller.ensure_log_links())
            with controller.log_file.open(newline="", encoding="utf-8") as log:
                old_rows = list(csv.DictReader(log))
            self.assertEqual(len(old_rows), 1)
            self.assertEqual(
                old_rows[0]["video_url"], "https://www.youtube.com/watch?v=old-id"
            )

            controller._log_deleted(
                {"id": "new-id", "channel_id": "new-channel", "channel_name": "New"}
            )

            with controller.log_file.open(newline="", encoding="utf-8") as log:
                rows = list(csv.DictReader(log))
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                rows[0]["video_url"], "https://www.youtube.com/watch?v=old-id"
            )
            self.assertEqual(
                rows[1]["video_url"], "https://www.youtube.com/watch?v=new-id"
            )

    async def test_scanning_another_channel_keeps_previous_video_links_in_checkpoint(self):
        class MemoryStateManager:
            def __init__(self):
                self.states = {}

            def save_state(self, key, value):
                self.states[key] = value
                return True

            def load_state(self, key):
                return self.states.get(key)

        memory_state = MemoryStateManager()
        release_run = asyncio.Event()

        async def held_run(_context):
            await release_run.wait()

        with patch("web.components.delete_video_controller.state_manager", memory_state), patch(
            "web.components.delete_video_controller.create_run_context",
            return_value=Mock(),
        ):
            controller = DeleteVideoController()
            controller.selected_channel_ids = ["old-channel"]
            controller.all_videos = [
                {
                    "id": "saved-video-id",
                    "channel_id": "old-channel",
                    "row_status": "deleted",
                }
            ]
            with patch.object(controller, "refresh_channel_maps"), patch.object(
                controller, "_run_loop", side_effect=held_run
            ):
                controller.start(["new-channel"])
                self.assertEqual(controller.selected_channel_ids, ["new-channel"])
                self.assertEqual(controller.all_videos[0]["id"], "saved-video-id")
                self.assertEqual(
                    memory_state.load_state("delete_video_run")["all_videos"][0]["id"],
                    "saved-video-id",
                )
                release_run.set()
                await controller._task


if __name__ == "__main__":
    unittest.main()
