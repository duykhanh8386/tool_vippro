import inspect
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nicegui import Client, ui
from nicegui.page import page

from src.task_runtime import TaskStopped
from web.components import add_audio_flow, delete_back_flow


class FlowMusicMatchingTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def flow_page(self, module, *, matching=None, duplicate=False, checkpoint=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            videos, music, output = (root / name for name in ("videos", "music", "output"))
            videos.mkdir()
            music.mkdir()
            (videos / "clip.mp4").touch()
            (music / "other.mp3").touch()
            (music / "CLIP.m4a").touch()
            if duplicate:
                (music / "clip.wav").touch()
            saved = {
                "video_folder": str(videos), "music_folder": str(music),
                "output_folder": str(output), "selected_channel": "channel",
                "audio_language": "en", "random_music": False, "statuses": {},
            }
            if matching is not None:
                saved["match_music_by_name"] = matching
            if checkpoint:
                saved["statuses"]["clip.mp4"] = {
                    "source_path": str(videos / "clip.mp4"),
                    "steps": {"merge": "pending"},
                    "music": "checkpoint.mp3",
                }
            channel = SimpleNamespace(
                id="channel", name="Channel", img_src="", owner_email="", overlay_png=""
            )
            client = Client(page("/test-music-matching"), request=None)
            callbacks = []

            def timer(_interval, callback, **kwargs):
                if kwargs.get("once"):
                    callbacks.append(callback)
                return Mock()

            try:
                with (
                    patch.object(module, "get_channels_info", side_effect=lambda cid=None: channel if cid else [channel]),
                    patch.object(module, "state_manager") as state,
                    patch.object(module, "get_video_duration", return_value=60),
                    patch.object(module.ui, "timer", side_effect=timer),
                    patch.object(module.ui, "notify") as notify,
                    patch.object(module.upload_video_module, "validate_session") as validate,
                    client,
                ):
                    state.load_state.return_value = saved
                    state.save_state.return_value = True
                    create = (module.create_add_audio_flow_page if module is add_audio_flow
                              else module.create_delete_back_flow_page)
                    create()
                    for callback in list(callbacks):
                        result = callback()
                        if inspect.isawaitable(result):
                            await result
                    button = next(element for element in client.elements.values()
                                  if isinstance(element, ui.button) and element.text == "Xử lý")
                    listener = next(item for item in button._event_listeners.values()
                                    if item.type == "click")
                    process = inspect.getclosurevars(listener.handler).nonlocals["callback"]
                    scope = inspect.getclosurevars(process).nonlocals
                    switch = next(element for element in reversed(list(client.elements.values()))
                                  if isinstance(element, ui.switch) and not element.is_deleted
                                  and element.text == "Ghép nhạc trùng tên video")
                    yield SimpleNamespace(
                        process=process, scope=scope, switch=switch, state=state,
                        notify=notify, validate=validate, root=root,
                    )
            finally:
                client.delete()

    async def test_both_flows_use_matching_plan_and_persist_the_option(self):
        for module in (add_audio_flow, delete_back_flow):
            with self.subTest(flow=module.__name__):
                async with self.flow_page(module, matching=True) as h:
                    self.assertTrue(h.switch.value)
                    self.assertTrue(h.scope["options_state"]["match_music_by_name"])
                    # Stop at session validation: no render, upload, or delete is run.
                    h.validate.side_effect = TaskStopped()
                    with patch.object(module, "build_balanced_music_plan", wraps=module.build_balanced_music_plan) as build:
                        await h.process()
                    self.assertEqual(build.call_count, 1)
                    self.assertTrue(build.call_args.kwargs["match_by_name"])
                    plan = module.build_balanced_music_plan(*build.call_args.args, **build.call_args.kwargs)
                    self.assertEqual(plan[0].name, "CLIP.m4a")
                    self.assertTrue(h.state.save_state.call_args.args[1]["match_music_by_name"])
                    self.assertFalse(module._FLOW_RUN_GUARD.locked())

    async def test_missing_or_ambiguous_matches_stop_before_session_or_work(self):
        for module in (add_audio_flow, delete_back_flow):
            for duplicate in (False, True):
                with self.subTest(flow=module.__name__, duplicate=duplicate):
                    async with self.flow_page(module, matching=True, duplicate=duplicate) as h:
                        if not duplicate:
                            (h.root / "music" / "CLIP.m4a").unlink()
                        await h.process()
                        h.validate.assert_not_called()
                        self.assertIn("clip.mp4", h.notify.call_args.args[0])
                        self.assertFalse(module._FLOW_RUN_GUARD.locked())

    async def test_legacy_state_defaults_to_matching_off_and_random_on(self):
        for module in (add_audio_flow, delete_back_flow):
            with self.subTest(flow=module.__name__):
                async with self.flow_page(module) as h:
                    self.assertFalse(h.switch.value)
                    h.validate.side_effect = TaskStopped()
                    with patch.object(module, "build_balanced_music_plan", wraps=module.build_balanced_music_plan) as build:
                        await h.process()
                    self.assertFalse(build.call_args.kwargs["match_by_name"])
                    self.assertTrue(build.call_args.kwargs["randomize"])

    async def test_switch_persists_mode_and_cannot_change_during_a_run(self):
        for module in (add_audio_flow, delete_back_flow):
            with self.subTest(flow=module.__name__):
                async with self.flow_page(module) as h:
                    h.switch.set_value(True)
                    self.assertTrue(h.scope["options_state"]["match_music_by_name"])
                    self.assertTrue(h.state.save_state.call_args.args[1]["match_music_by_name"])
                    module._FLOW_RUN_GUARD.acquire()
                    try:
                        h.switch.set_value(False)
                        self.assertTrue(h.switch.value)
                        self.assertTrue(h.scope["options_state"]["match_music_by_name"])
                    finally:
                        module._FLOW_RUN_GUARD.release()

    async def test_restoring_enabled_mode_preserves_video_checkpoints(self):
        for module in (add_audio_flow, delete_back_flow):
            with self.subTest(flow=module.__name__):
                async with self.flow_page(module, matching=True, checkpoint=True) as h:
                    item = h.scope["videos_state"]["items"][0]
                    self.assertEqual(item["music"], "checkpoint.mp3")
                    self.assertEqual(item["steps"]["merge"], "pending")


if __name__ == "__main__":
    unittest.main()
