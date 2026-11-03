import inspect
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nicegui import Client, ui
from nicegui.page import page

from src.module.audio_module import AudioUpdateError
from src.task_runtime import TaskStopped
from web.components import add_audio_flow as flow


class FlowAudioContinuationTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def flow_page(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "video.mp4").touch()
            (root / "music.mp3").write_bytes(b"full original music")
            saved = {
                "video_folder": folder, "music_folder": folder, "output_folder": folder,
                "selected_channel": "channel", "audio_language": "en es",
                "statuses": {"video.mp4": {
                    "video_id": "video", "music_path": str(root / "music.mp3"),
                    "steps": {
                        "merge": "successful", "upload": "successful", "wait": "successful",
                        "add_audio": "pending", "add_description": "pending",
                    },
                }},
            }
            channel = SimpleNamespace(id="channel", name="Channel", img_src="", owner_email="", overlay_png="")
            client = Client(page("/test-flow-audio-continuation"), request=None)
            callbacks = []

            def timer(_interval, callback, **kwargs):
                if kwargs.get("once"):
                    callbacks.append(callback)
                return Mock()

            def prepare(**kwargs):
                self.assertEqual(kwargs["input_file"], str(root / "music.mp3"))
                Path(kwargs["output_file"]).write_bytes(b"full original music")

            try:
                with (
                    patch.object(flow, "get_channels_info", side_effect=lambda cid=None: channel if cid else [channel]),
                    patch.object(flow, "state_manager") as state,
                    patch.object(flow, "get_video_duration", return_value=60),
                    patch.object(flow.ui, "timer", side_effect=timer),
                    patch.object(flow.ui, "notify"),
                    patch.object(flow.upload_video_module, "validate_session"),
                    patch.object(flow.upload_video_module, "upload") as video_upload,
                    patch.object(flow.upload_video_module, "_get_video_info", return_value=SimpleNamespace(
                        id="video", audio_language="pcm", duration_ms=60000,
                    )),
                    patch.object(flow, "multiply_audio", side_effect=prepare) as render,
                    patch.object(flow.update_audio_module, "add", return_value=200) as add,
                    patch.object(flow, "register_audio_recovery", return_value=True),
                    client,
                ):
                    state.load_state.return_value = saved
                    state.save_state.return_value = True
                    flow.create_add_audio_flow_page()
                    for callback in list(callbacks):
                        result = callback()
                        if inspect.isawaitable(result):
                            await result
                    button = next(element for element in client.elements.values()
                                  if isinstance(element, ui.button) and element.text == "Xử lý")
                    listener = next(listener for listener in button._event_listeners.values() if listener.type == "click")
                    process = inspect.getclosurevars(listener.handler).nonlocals["callback"]
                    yield SimpleNamespace(process=process, state=state, add=add, render=render,
                                          video_upload=video_upload)
            finally:
                client.delete()

    @staticmethod
    def stored(harness):
        return harness.state.save_state.call_args.args[1]["statuses"]["video.mp4"]

    async def test_partial_normal_failure_still_adds_all_descriptions_and_resumes_only_failed_normal(self):
        async with self.flow_page() as h:
            attempted = []

            def upload(**kwargs):
                key = (kwargs.get("audio_content_type", "dubbed"), kwargs["language"])
                attempted.append(key)
                self.assertEqual(Path(kwargs["upload_path"]).read_bytes(), b"full original music")
                if key == ("dubbed", "en") and attempted.count(key) == 1:
                    raise AudioUpdateError("AUDIO_TRACK_STATUS_FAILED")
                return 200

            h.add.side_effect = upload
            await h.process()
            self.assertEqual(attempted, [
                ("dubbed", "en"), ("dubbed", "es"),
                ("descriptive", "pcm"), ("descriptive", "en"), ("descriptive", "es"),
            ])
            stored = self.stored(h)
            self.assertEqual(stored["steps"]["add_audio"], "unsuccessful")
            self.assertEqual(stored["steps"]["add_description"], "successful")
            self.assertIn("AUDIO_TRACK_STATUS_FAILED", stored["audio_language_results"]["en"]["error"])
            self.assertEqual(stored["audio_language_results"]["es"]["status"], "successful")
            await h.process()
            self.assertEqual(attempted[-1], ("dubbed", "en"))
            self.assertEqual(len(attempted), 6)
            self.assertEqual(self.stored(h)["steps"]["add_audio"], "successful")
            h.video_upload.assert_not_called()
            self.assertFalse(flow._FLOW_RUN_GUARD.locked())

    async def test_all_normal_languages_failed_still_attempts_each_description(self):
        async with self.flow_page() as h:
            def upload(**kwargs):
                if kwargs.get("audio_content_type", "dubbed") == "dubbed":
                    raise AudioUpdateError("AUDIO_TRACK_STATUS_FAILED")
                if kwargs["language"] == "en":
                    raise AudioUpdateError("description rejected")
                return 200

            h.add.side_effect = upload
            await h.process()
            self.assertEqual(h.add.call_count, 5)
            stored = self.stored(h)
            self.assertEqual(stored["steps"]["add_audio"], "unsuccessful")
            self.assertEqual(stored["steps"]["add_description"], "unsuccessful")
            self.assertEqual(stored["audio_description_results"]["en"]["status"], "unsuccessful")
            self.assertEqual(stored["audio_description_results"]["es"]["status"], "successful")

    async def test_stop_during_normal_upload_does_not_start_descriptions(self):
        async with self.flow_page() as h:
            h.add.side_effect = TaskStopped()
            await h.process()
            h.add.assert_called_once()
            self.assertEqual(self.stored(h)["steps"]["add_audio"], "stopped")
            self.assertEqual(self.stored(h)["steps"]["add_description"], "pending")
            self.assertFalse(flow._FLOW_RUN_GUARD.locked())

    async def test_preparation_failure_does_not_start_uploads(self):
        async with self.flow_page() as h:
            h.render.side_effect = RuntimeError("cannot prepare audio")
            await h.process()
            h.add.assert_not_called()
            h.render.assert_called_once()
            self.assertEqual(self.stored(h)["steps"]["add_audio"], "unsuccessful")
            self.assertEqual(self.stored(h)["steps"]["add_description"], "pending")

    async def test_failed_checkpoint_after_normal_error_stops_further_uploads(self):
        async with self.flow_page() as h:
            def save(_page, state):
                results = state["statuses"]["video.mp4"]["audio_language_results"]
                return not results.get("en", {}).get("error")

            h.state.save_state.side_effect = save
            h.add.side_effect = AudioUpdateError("AUDIO_TRACK_STATUS_FAILED")
            await h.process()
            h.add.assert_called_once()
            self.assertEqual(self.stored(h)["steps"]["add_audio"], "unsuccessful")
            self.assertEqual(self.stored(h)["steps"]["add_description"], "pending")
            self.assertFalse(flow._FLOW_RUN_GUARD.locked())


if __name__ == "__main__":
    unittest.main()
