import copy
import inspect
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from nicegui import Client, ui
from nicegui.page import page

from src.task_runtime import TaskStopped
from web.components import add_audio_flow, delete_back_flow


class FlowMusicMatchingTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def flow_page(self, module, *, matching=None, duplicate=False, checkpoint=False, transition=None):
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
            if transition is not None:
                saved["loop_transition"] = transition
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
                    transition_switch = next(element for element in client.elements.values()
                                             if isinstance(element, ui.switch) and not element.is_deleted
                                             and element.text == "Cross Dissolve giữa các lần lặp video")
                    yield SimpleNamespace(
                        process=process, scope=scope, switch=switch, state=state,
                        notify=notify, validate=validate, root=root,
                        transition_switch=transition_switch,
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

    async def test_transition_defaults_off_and_persists_without_changing_music_mode(self):
        for module in (add_audio_flow, delete_back_flow):
            with self.subTest(flow=module.__name__):
                async with self.flow_page(module, matching=True) as h:
                    self.assertFalse(h.transition_switch.value)
                    h.transition_switch.set_value(True)
                    self.assertTrue(h.scope["options_state"]["loop_transition"])
                    self.assertTrue(h.state.save_state.call_args.args[1]["loop_transition"])
                    self.assertTrue(h.scope["options_state"]["match_music_by_name"])
                    module._FLOW_RUN_GUARD.acquire()
                    try:
                        h.transition_switch.set_value(False)
                        self.assertTrue(h.transition_switch.value)
                        self.assertTrue(h.scope["options_state"]["loop_transition"])
                    finally:
                        module._FLOW_RUN_GUARD.release()

    async def test_both_flows_match_real_thai_filenames_with_different_unicode(self):
        for module in (add_audio_flow, delete_back_flow):
            with self.subTest(flow=module.__name__):
                async with self.flow_page(module, matching=True) as h:
                    track = h.root / "music" / "น้ำ [09BPAunBaEE].mp3"
                    (h.root / "music" / "CLIP.m4a").rename(track)
                    video = h.root / "videos" / "น\u0e4d\u0e49า\u200b [09BPAunBaEE].mp4"
                    (h.root / "videos" / "clip.mp4").rename(video)
                    item = h.scope["videos_state"]["items"][0]
                    item.update(name=video.name, path=str(video))
                    h.validate.side_effect = TaskStopped()
                    with patch.object(module, "build_balanced_music_plan", wraps=module.build_balanced_music_plan) as build:
                        await h.process()
                    h.validate.assert_called_once()
                    plan = module.build_balanced_music_plan(*build.call_args.args, **build.call_args.kwargs)
                    self.assertEqual(plan[0], track)

    async def _check_queue_music_alignment(self, module, *, matching, pending_indexes=None):
        async with self.flow_page(module, matching=matching) as h:
            template = h.scope["videos_state"]["items"][0]
            items = []
            for index in range(5):
                name = f"clip-{index} [video-{index}]"
                video = h.root / "videos" / f"{name}.mp4"
                video.touch()
                (h.root / "music" / f"{name}.mp3").touch()
                item = copy.deepcopy(template)
                item.update(name=video.name, path=str(video))
                items.append(item)
            h.scope["videos_state"]["items"] = items
            sequence = h.scope.get("STEP_SEQUENCE")
            if sequence is None:
                worker = inspect.getclosurevars(h.scope["run_parallel_queue"]).nonlocals["run_video_item"]
                sequence = inspect.getclosurevars(worker).nonlocals["STEP_SEQUENCE"]
            # Run the real queue and merge; replace every remote operation.
            sequence[:] = [(key, label, fn if key == "merge" else AsyncMock())
                           for key, label, fn in sequence]
            planner = module.build_balanced_music_plan
            expected = {}

            def capture_plan(*args, **kwargs):
                plan = planner(*args, **kwargs)
                expected.update(plan)
                return plan

            with (
                patch.object(module, "build_balanced_music_plan", side_effect=capture_plan),
                patch.object(module, "mux_audio_into_video") as mux,
                patch.object(add_audio_flow, "build_intermittent_audio", return_value=60) as intermittent,
            ):
                if pending_indexes is None:
                    pending_indexes = list(range(len(items)))
                    await h.process()
                else:
                    musics = list((h.root / "music").iterdir())
                    plan = capture_plan(musics, items, randomize=True, match_by_name=matching)
                    config = {"music_plan": plan, "overlay_png": "", "loop_transition": False}
                    errors = []
                    stats = await h.scope["run_parallel_queue"](
                        [(index, items[index]) for index in pending_indexes],
                        str(h.root / "output"), musics, config, errors,
                    )
                    self.assertEqual(errors, [])
                    self.assertEqual(stats, {"finished": len(pending_indexes), "failed": 0})

            rendered = {call.kwargs["video_file"]: call.kwargs for call in mux.call_args_list}
            audio_sources = {call.kwargs["audio_out"]: call.kwargs["music_file"]
                             for call in intermittent.call_args_list}
            self.assertEqual(len(rendered), len(pending_indexes))
            for index in pending_indexes:
                item = items[index]
                with self.subTest(index=index):
                    self.assertEqual(item["steps"]["merge"], "successful")
                    self.assertEqual(item["music_path"], str(expected[index]))
                    self.assertEqual(item["music"], expected[index].name)
                    actual_audio = rendered[item["path"]]["audio_file"]
                    if module is add_audio_flow:
                        actual_audio = audio_sources[actual_audio]
                    self.assertEqual(actual_audio, str(expected[index]))
                    if matching:
                        self.assertEqual(expected[index].stem, Path(item["name"]).stem)

    async def test_full_batch_keeps_music_with_its_video_in_both_modes_and_flows(self):
        for module in (add_audio_flow, delete_back_flow):
            for matching in (True, False):
                with self.subTest(flow=module.__name__, matching=matching):
                    await self._check_queue_music_alignment(module, matching=matching)

    async def test_resumed_queue_preserves_original_indexes_with_gaps(self):
        for module in (add_audio_flow, delete_back_flow):
            for matching in (True, False):
                with self.subTest(flow=module.__name__, matching=matching):
                    await self._check_queue_music_alignment(
                        module, matching=matching, pending_indexes=[1, 3, 4],
                    )

    async def test_transition_restores_and_reaches_the_renderer_in_both_flows(self):
        for module in (add_audio_flow, delete_back_flow):
            with self.subTest(flow=module.__name__):
                async with self.flow_page(module, transition=True, checkpoint=True) as h:
                    self.assertTrue(h.transition_switch.value)
                    item = h.scope["videos_state"]["items"][0]
                    self.assertEqual(item["music"], "checkpoint.mp3")
                    sequence = h.scope.get("STEP_SEQUENCE")
                    if sequence is None:
                        worker = inspect.getclosurevars(h.scope["run_parallel_queue"]).nonlocals["run_video_item"]
                        sequence = inspect.getclosurevars(worker).nonlocals["STEP_SEQUENCE"]
                    merge = next(step for key, _label, step in sequence if key == "merge")
                    track = h.root / "music" / "CLIP.m4a"
                    config = {"music_plan": {0: track}, "overlay_png": "", "loop_transition": True}
                    with patch.object(module, "mux_audio_into_video") as mux:
                        if module is add_audio_flow:
                            with patch.object(module, "build_intermittent_audio", return_value=60):
                                await merge(item, str(h.root / "output"), [track], 0, config)
                        else:
                            await merge(item, str(h.root / "output"), [track], 0, config)
                    self.assertTrue(mux.call_args.kwargs["loop_transition"])


if __name__ == "__main__":
    unittest.main()
