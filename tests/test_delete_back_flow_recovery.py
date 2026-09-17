import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.state_manager import StateManager
from web.components.delete_video_controller import DeleteVideoController
from web.components.delete_back_flow import (
    ORIGINAL_AUDIO_RENDER_MODE,
    PERSIST_FIELDS,
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


if __name__ == "__main__":
    unittest.main()
