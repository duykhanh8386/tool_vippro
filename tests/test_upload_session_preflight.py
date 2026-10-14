import tempfile
import inspect
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nicegui import Client, ui
from nicegui.page import page

from src.module.base import YouTubeRequestError
from src.module.upload_video_module import UploadVideoModule


class UploadSessionPreflightTests(unittest.TestCase):
    def test_invalid_session_is_reported_before_an_upload_starts(self):
        module = UploadVideoModule()
        channel = SimpleNamespace(id="channel")
        with patch("src.module.upload_video_module.get_channels_info", return_value=channel), patch.object(
            module, "_get_session_token", side_effect=YouTubeRequestError("reauth failed", status_code=400)
        ) as token, patch.object(module, "upload") as upload:
            with self.assertRaises(YouTubeRequestError):
                module.validate_session("channel")
        token.assert_called_once_with(channel)
        upload.assert_not_called()


class FlowSessionPreflightTests(unittest.IsolatedAsyncioTestCase):
    async def test_both_flows_leave_queue_untouched_when_session_validation_fails(self):
        from web.components import add_audio_flow, delete_back_flow

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            video_folder = root / "videos"
            music_folder = root / "music"
            output_folder = root / "output"
            for directory in (video_folder, music_folder, output_folder):
                directory.mkdir()
            (video_folder / "video.mp4").write_bytes(b"fake-video")
            (music_folder / "music.mp3").write_bytes(b"fake-music")
            saved = {
                "video_folder": str(video_folder), "music_folder": str(music_folder),
                "output_folder": str(output_folder), "selected_channel": "channel",
                "audio_language": "en", "statuses": {},
            }
            channel = SimpleNamespace(id="channel", name="Channel", img_src="", owner_email="user@gmail.com", overlay_png="")
            for module, create in (
                (add_audio_flow, add_audio_flow.create_add_audio_flow_page),
                (delete_back_flow, delete_back_flow.create_delete_back_flow_page),
            ):
                with self.subTest(flow=module.__name__):
                    client = Client(page("/test-upload-preflight"), request=None)
                    callbacks = []

                    def timer(_interval, callback, **kwargs):
                        if kwargs.get("once"):
                            callbacks.append(callback)
                        return Mock()

                    try:
                        with (
                            patch.object(module, "get_channels_info", side_effect=lambda cid=None: channel if cid else [channel]),
                            patch.object(module, "state_manager") as state,
                            patch.object(module, "get_video_duration", return_value=60.0),
                            patch.object(module.ui, "timer", side_effect=timer),
                            patch.object(module.ui, "notify"),
                            patch.object(module.upload_video_module, "validate_session", side_effect=YouTubeRequestError("reauth failed", status_code=400)) as validate,
                            patch.object(module.upload_video_module, "upload") as upload,
                            patch.object(module, "mux_audio_into_video") as render,
                            client,
                        ):
                            state.load_state.return_value = saved
                            state.save_state.return_value = True
                            create()
                            for callback in list(callbacks):
                                result = callback()
                                if inspect.isawaitable(result):
                                    await result
                            button = next(element for element in client.elements.values()
                                          if isinstance(element, ui.button) and element.text == "Xử lý")
                            listener = next(listener for listener in button._event_listeners.values() if listener.type == "click")
                            callback = inspect.getclosurevars(listener.handler).nonlocals["callback"]
                            await callback()
                            validate.assert_called_once_with("channel")
                            upload.assert_not_called()
                            render.assert_not_called()
                            self.assertFalse(module._FLOW_RUN_GUARD.locked())
                            saved_statuses = state.save_state.call_args.args[1]["statuses"]
                            self.assertTrue(saved_statuses)
                            self.assertTrue(all(step == "pending" for item in saved_statuses.values()
                                                for step in item["steps"].values()))
                    finally:
                        client.delete()

