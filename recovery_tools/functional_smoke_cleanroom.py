"""Isolated functional smoke tests for the three clean-room UI modules.

No recovered application server is started. All external, media, browser,
network, upload, and delete dependencies are replaced before module loading.
"""

from __future__ import annotations

import asyncio
import copy
import importlib.util
import inspect
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "recovered_project"


class Element:
    def __init__(self, ui, kind, args, kwargs):
        self.ui = ui
        self.kind = kind
        self.args = args
        self.kwargs = kwargs
        self.value = kwargs.get("value")
        self.visible = True
        self.enabled = True
        self.text = args[0] if args and isinstance(args[0], str) else ""
        self.handlers = {}
        self.cancelled = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def classes(self, *_args, **_kwargs):
        return self

    def props(self, *_args, **_kwargs):
        return self

    def tooltip(self, *_args, **_kwargs):
        return self

    def clear(self):
        return self

    def open(self):
        self.visible = True
        return self

    def close(self):
        self.visible = False
        return self

    def cancel(self):
        self.cancelled = True

    def on(self, event, callback):
        self.handlers[event] = callback
        self.ui.event_handlers.append((self, event, callback))
        return self

    def set_visibility(self, value):
        self.visible = bool(value)
        return self

    def set_enabled(self, value):
        self.enabled = bool(value)
        return self

    def set_value(self, value):
        self.value = value
        return self

    def set_text(self, value):
        self.text = value
        return self


class FakeUI:
    def __init__(self):
        self.elements = []
        self.buttons = []
        self.textareas = []
        self.timers = []
        self.notifications = []
        self.event_handlers = []

    def notify(self, message, **kwargs):
        self.notifications.append({"message": message, **kwargs})

    def timer(self, interval, callback, **kwargs):
        element = Element(self, "timer", (interval,), {"callback": callback, **kwargs})
        self.timers.append(element)
        return element

    def __getattr__(self, kind):
        def factory(*args, **kwargs):
            element = Element(self, kind, args, kwargs)
            self.elements.append(element)
            if kind == "button":
                self.buttons.append(element)
            elif kind == "textarea":
                self.textareas.append(element)
            return element

        return factory


class Logger:
    def __init__(self):
        self.entries = []

    def __getattr__(self, level):
        return lambda message, *args, **kwargs: self.entries.append(
            (level, str(message), args, kwargs)
        )


class StateManager:
    def __init__(self):
        self.loaded = {}
        self.saved = []

    def load_state(self, key):
        return copy.deepcopy(self.loaded.get(key))

    def save_state(self, key, state):
        snapshot = copy.deepcopy(state)
        self.loaded[key] = snapshot
        self.saved.append((key, snapshot))
        return True


class DeleteController:
    def __init__(self):
        self.selected_channel_ids = []
        self.all_videos = []
        self.version = 0
        self.status_text = "idle"
        self.output_dir = Path("mock-output")
        self.log_file = Path("mock-output/deleted.csv")
        self.polling = False
        self.next_poll_at = 0
        self.running = False
        self.calls = []
        self.raise_start = False

    def counts(self, statuses):
        return {status: 0 for status in statuses}

    def is_running(self):
        return self.running

    def start(self, channel_ids, max_workers):
        self.calls.append(("start", list(channel_ids), max_workers))
        if self.raise_start:
            raise RuntimeError("mock scan failure")
        self.running = True
        self.version += 1

    def stop(self):
        self.calls.append(("stop",))
        self.running = False
        self.version += 1

    def set_output_dir(self, path):
        self.output_dir = Path(path)


class NavState:
    def __init__(self):
        self.events = []

    def lock(self, message):
        self.events.append(("lock", message))

    def unlock(self):
        self.events.append(("unlock",))


class CommonMocks:
    def __init__(self):
        self.channel_callbacks = []
        self.directory_choices = []

    def create_channel_selection(self, channels, callback, **kwargs):
        self.channel_callbacks.append(callback)
        return {}, lambda: None

    def select_directory(self, **kwargs):
        return self.directory_choices.pop(0) if self.directory_choices else None

    def select_file(self, **kwargs):
        return None


def module(name, **attrs):
    result = types.ModuleType(name)
    result.__dict__.update(attrs)
    return result


def load_source(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, PROJECT / relative_path)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


def install_base_mocks(ui, logger, state_manager, common, nav_state):
    sys.modules["nicegui"] = module("nicegui", ui=ui)
    sys.modules["loguru"] = module("loguru", logger=logger)
    sys.modules["src.state_manager"] = module(
        "src.state_manager", state_manager=state_manager
    )
    sys.modules["web.components.common"] = module(
        "web.components.common",
        create_channel_selection=common.create_channel_selection,
        select_directory=common.select_directory,
        select_file=common.select_file,
    )
    sys.modules["web.components.drawer"] = module(
        "web.components.drawer", nav_state=nav_state
    )


def callback_for_icon(ui, icon):
    matches = [b.kwargs.get("on_click") for b in ui.buttons if b.kwargs.get("icon") == icon]
    matches = [callback for callback in matches if callback]
    assert matches, f"button callback not found for icon {icon}"
    return matches[-1]


async def test_delete_video():
    ui, logger, states = FakeUI(), Logger(), StateManager()
    common, nav, controller = CommonMocks(), NavState(), DeleteController()
    install_base_mocks(ui, logger, states, common, nav)
    sys.modules["src.utils"] = module("src.utils", get_channels_info=lambda: [])
    sys.modules["web.components.delete_video_controller"] = module(
        "web.components.delete_video_controller", delete_controller=controller
    )

    target = load_source("smoke_delete_video", "web/components/delete_video.py")
    target.create_delete_video_page()
    common.channel_callbacks[-1](["channel-1", "channel-2"])
    scan = callback_for_icon(ui, "auto_delete")
    stop = callback_for_icon(ui, "stop")

    await scan()
    assert controller.calls[-1] == ("start", ["channel-1", "channel-2"], 5)
    assert controller.running is True
    await stop()
    assert controller.calls[-1] == ("stop",)
    assert controller.running is False

    controller.raise_start = True
    await scan()
    assert ui.notifications[-1]["type"] == "negative"
    return {
        "status": "PASS",
        "checks": [
            "channel selection state reached controller.start",
            "async scan and stop callbacks updated controller state",
            "scan exception was converted to a negative notification",
            "no real scan/delete/network operation was called",
        ],
    }


async def test_remove_audio():
    ui, logger, states = FakeUI(), Logger(), StateManager()
    common, nav = CommonMocks(), NavState()
    install_base_mocks(ui, logger, states, common, nav)
    delete_calls = []

    class UpdateAudio:
        def delete(self, *, id_video, channel_id):
            delete_calls.append((id_video, channel_id))
            if id_video == "bad-id":
                raise RuntimeError("mock delete failure")

    sys.modules["src.module.audio_module"] = module(
        "src.module.audio_module", update_audio_module=UpdateAudio()
    )
    sys.modules["src.utils"] = module("src.utils", get_channels_info=lambda: [])

    target = load_source("smoke_remove_audio", "web/components/remove_audio.py")
    assert target.parse_ids_from_text("id-1, id-2\nid-1") == ["id-1", "id-2"]
    target.create_remove_audio_page()
    textarea = ui.textareas[-1]
    textarea.value = "good-id\nbad-id\ngood-id"
    textarea.kwargs["on_change"](types.SimpleNamespace(value=textarea.value))
    common.channel_callbacks[-1]("channel-1")
    process = next(
        b.kwargs["on_click"]
        for b in ui.buttons
        if inspect.iscoroutinefunction(b.kwargs.get("on_click"))
    )
    await process()

    assert delete_calls == [("good-id", "channel-1"), ("bad-id", "channel-1")]
    saved = states.loaded[target.STATE_KEY]
    assert saved["video_processing_status"] == {
        "good-id": "successful",
        "bad-id": "unsuccessful",
    }
    assert ui.notifications[-1]["type"] == "warning"

    save_count = len(states.saved)
    clear = next(
        b.kwargs["on_click"]
        for b in ui.buttons
        if b.kwargs.get("on_click")
        and not inspect.iscoroutinefunction(b.kwargs["on_click"])
    )
    clear()
    clear_persisted = len(states.saved) > save_count and not states.saved[-1][1]["ids"]
    return {
        "status": "FAIL" if not clear_persisted else "PASS",
        "checks": [
            "ID parsing preserved order and removed duplicates",
            "async bounded flow recorded one success and one mocked failure",
            "per-video status and warning notification were persisted",
        ],
        "failure": None
        if clear_persisted
        else "clear_all_inputs suppresses save_remove_state and never persists the cleared state",
    }


async def test_delete_back_flow():
    ui, logger, states = FakeUI(), Logger(), StateManager()
    common, nav = CommonMocks(), NavState()
    install_base_mocks(ui, logger, states, common, nav)
    calls = []

    class ChannelStore:
        def get_overlay_png(self, channel_id):
            return ""

        def set_overlay_png(self, channel_id, value):
            calls.append(("overlay", channel_id, value))

    class Upload:
        def upload(self, **kwargs):
            calls.append(("upload", kwargs["channel_id"], kwargs["file_path"]))
            return {"frontend_upload_id": "front-1", "scotty_resource_id": "scotty-1"}

        def create_video(self, **kwargs):
            calls.append(("create_video", kwargs["channel_id"], kwargs["title"]))
            return "video-new"

    class ListVideos:
        def get_copyright_statuses(self, channel_id, video_ids):
            calls.append(("status", channel_id, sorted(video_ids)))
            return {"video-new": "UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_COMPLETED"}

    class DeleteVideo:
        def delete(self, video_id, channel_id):
            calls.append(("delete", video_id, channel_id))
            return 204

    sys.modules["src.channel_store"] = module(
        "src.channel_store", channel_store=ChannelStore()
    )
    sys.modules["src.module.upload_video_module"] = module(
        "src.module.upload_video_module", upload_video_module=Upload()
    )
    sys.modules["src.module.list_videos_module"] = module(
        "src.module.list_videos_module", list_videos_module=ListVideos()
    )
    sys.modules["src.module.delete_video_module"] = module(
        "src.module.delete_video_module", delete_video_module=DeleteVideo()
    )

    # Existing harmless files are used only for Path.is_dir/stat metadata. The
    # media-list mock assigns them media roles; neither file is opened by a
    # media implementation and no fixture needs to be created or deleted.
    video_dir = music_dir = output_dir = PROJECT
    video = PROJECT / "VERSION"
    music = PROJECT / "requirements.txt"

    def list_media_files(folder, extensions):
        return [video] if extensions == (".mp4",) else [music]

    def build_audio(**kwargs):
        calls.append(("build_audio", kwargs["music_file"], kwargs["audio_out"]))
        return 1.0

    def mux(**kwargs):
        calls.append(("mux", kwargs["video_file"], kwargs["video_out"]))

    channel = types.SimpleNamespace(id="channel-1", name="Channel One")
    sys.modules["src.utils"] = module(
        "src.utils",
        AUDIO_EXTENSIONS=(".mp3",),
        VIDEO_EXTENSIONS=(".mp4",),
        build_intermittent_audio=build_audio,
        get_channels_info=lambda: [channel],
        get_video_duration=lambda _path: 10,
        list_media_files=list_media_files,
        mux_audio_into_video=mux,
        normalize_path=lambda path: str(path),
    )
    common.directory_choices = [str(video_dir), str(music_dir), str(output_dir)]
    target = load_source("smoke_delete_back_flow", "web/components/delete_back_flow.py")
    target._log_deleted = lambda **kwargs: calls.append(("log_deleted", kwargs["video_id"]))
    target.create_delete_back_flow_page()
    common.channel_callbacks[-1]("channel-1")

    folder_clicks = [
        callback
        for element, event, callback in ui.event_handlers
        if event == "click" and element.kind == "card"
    ][-3:]
    for callback in folder_clicks:
        callback()

    process = callback_for_icon(ui, "play_arrow")
    await process()
    saved = states.loaded[target.STATE_KEY]
    status = saved["statuses"]["VERSION"]["steps"]
    assert all(value == "successful" for value in status.values())
    assert [entry[0] for entry in calls] == [
        "build_audio",
        "mux",
        "upload",
        "create_video",
        "status",
        "delete",
        "log_deleted",
    ]
    assert nav.events[0][0] == "lock" and nav.events[-1][0] == "unlock"

    save_count = len(states.saved)
    clear = callback_for_icon(ui, "delete_sweep")
    clear()
    clear_persisted = (
        len(states.saved) > save_count
        and states.saved[-1][1]["video_folder"] == ""
        and states.saved[-1][1]["statuses"] == {}
    )

    # Re-populate the in-memory flow and force the first media step to fail.
    # The later mocked upload/delete operations must not be reached.
    common.directory_choices = [str(video_dir), str(music_dir), str(output_dir)]
    target.mux_audio_into_video = lambda **_kwargs: (_ for _ in ()).throw(
        RuntimeError("mock mux failure")
    )
    common.channel_callbacks[-1]("channel-1")
    for callback in folder_clicks:
        callback()
    calls_before_error = len(calls)
    await process()
    error_steps = states.loaded[target.STATE_KEY]["statuses"]["VERSION"]["steps"]
    expected_error_steps = {
        "merge": "error",
        "upload": "pending",
        "wait": "pending",
        "delete_back": "pending",
    }
    assert error_steps == expected_error_steps, (error_steps, expected_error_steps)
    assert not any(
        entry[0] in {"upload", "create_video", "status", "delete"}
        for entry in calls[calls_before_error:]
    )
    assert nav.events[-1][0] == "unlock"

    return {
        "status": "FAIL" if not clear_persisted else "PASS",
        "checks": [
            "mocked merge, upload, processing poll, delete, and audit-log calls ran in order",
            "all four async step states reached successful",
            "navigation lock was always released by the finally path",
            "mocked merge failure marked only merge as error and skipped later operations",
            "no real media, upload, delete, browser, or network implementation was called",
        ],
        "failure": None
        if clear_persisted
        else "clear_all_inputs suppresses save_state and never persists the cleared state",
    }


async def main():
    results = {
        "delete_video.py": await test_delete_video(),
        "remove_audio.py": await test_remove_audio(),
        "delete_back_flow.py": await test_delete_back_flow(),
    }
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 1 if any(result["status"] == "FAIL" for result in results.values()) else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
