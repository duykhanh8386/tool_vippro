# RECOVERED: clean-room implementation based on NiceGUI components & delete_back_flow pipeline API
import asyncio
import csv
import random
import threading
from datetime import datetime
from pathlib import Path

from loguru import logger
from nicegui import context, ui

from src.channel_store import channel_store
from src.module.delete_video_module import delete_video_module
from src.module.list_videos_module import list_videos_module
from src.module.upload_video_module import upload_video_module
from src.state_manager import state_manager
from src.task_runtime import (
    TaskStopped,
    bind_run_context,
    create_run_context,
    current_run_context,
)
from src.utils import (
    AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS,
    FFprobeError,
    build_intermittent_audio,
    get_channels_info,
    get_video_duration,
    list_media_files,
    mux_audio_into_video,
    normalize_path,
)
from web.components.common import create_channel_selection, select_directory, select_file
from web.components.drawer import nav_state
from web.theme import app_card, page_header, section_header, workflow_steps

STATE_KEY = "delete_back_flow"
_DELETE_LOG_FILENAME = "deleted_back_videos.csv"
MAX_ACTIVE_VIDEOS = 5
MAX_FFMPEG_JOBS = 5
MAX_UPLOAD_JOBS = 5
MAX_WAIT_JOBS = 5
MAX_DELETE_JOBS = 5
COPYRIGHT_WAIT_TIMEOUT_SECONDS = 300
COPYRIGHT_POLL_INTERVAL_SECONDS = 5

_FLOW_RUN_GUARD = threading.Lock()
_DELETE_LOG_LOCK = threading.Lock()
PERSIST_FIELDS = (
    "music",
    "music_path",
    "audio_path",
    "output_path",
    "video_id",
    "frontend_upload_id",
    "scotty_resource_id",
)

STEP_STYLE = {
    "pending": ("hourglass_empty", "text-gray-400", "Chờ"),
    "processing": ("autorenew", "text-blue-600", "Đang xử lý..."),
    "successful": ("check_circle", "text-green-600", "Thành công"),
    "stopped": ("stop_circle", "text-amber-600", "Đã dừng"),
    "error": ("error", "text-red-600", "Lỗi"),
    "skipped": ("skip_next", "text-gray-400", "Bỏ qua"),
}

LOG_STYLE = {
    "info": "text-gray-700",
    "success": "text-green-600 font-medium",
    "error": "text-red-600 font-medium",
    "warning": "text-amber-600",
}


def _human_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            if unit == "B":
                return f"{num:.0f} {unit}"
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def _fmt_duration(seconds: float | None) -> str:
    if seconds is None or seconds <= 0:
        return "--:--"
    total = int(seconds)
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _new_steps() -> dict:
    return {
        "merge": "pending",
        "upload": "pending",
        "wait": "pending",
        "delete_back": "pending",
    }


def _log_deleted(
    output_folder: str,
    video_id: str,
    channel_id: str,
    channel_name: str,
    title: str = "",
):
    try:
        with _DELETE_LOG_LOCK:
            log_file = Path(normalize_path(output_folder)) / _DELETE_LOG_FILENAME
            log_file.parent.mkdir(parents=True, exist_ok=True)
            exists = log_file.exists()
            with log_file.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not exists:
                    writer.writerow(
                        ["video_id", "channel_id", "channel_name", "title", "deleted_at"]
                    )
                writer.writerow(
                    [
                        video_id,
                        channel_id,
                        channel_name,
                        title,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )
    except Exception as exc:
        logger.error(f"Không ghi được {_DELETE_LOG_FILENAME}: {exc}")


def create_delete_back_flow_page():
    try:
        page_client = context.client
    except RuntimeError:
        page_client = None

    paths_state = {"video_folder": "", "music_folder": "", "output_folder": ""}
    options_state = {"random_music": False}
    selected_channel = {"id": None}
    videos_state = {"items": []}
    saved_status_map = {}
    suppress_autosave = {"value": False}
    stop_requested = {"value": False}
    processing = {"value": False}
    active_run = {"parent": None, "children": {}}

    ui_refs = {
        "refresh_channel_display": None,
        "refresh_overlay": None,
        "random_switch": None,
        "process_btn": None,
        "stop_btn": None,
        "clear_btn": None,
    }
    folder_selectors = {}
    progress_refs = {
        "panel": None,
        "current": None,
        "step": None,
        "remaining": None,
        "log": None,
    }

    def client_is_alive() -> bool:
        """Return whether this page's NiceGUI client can still receive UI updates."""
        return page_client is not None and not getattr(page_client, "_deleted", False)

    def element_is_alive(element) -> bool:
        return (
            client_is_alive()
            and element is not None
            and not getattr(element, "is_deleted", False)
        )

    def safe_element_call(element, method: str, *args) -> bool:
        """Update an element unless its page was closed or reloaded meanwhile."""
        if not element_is_alive(element):
            return False
        try:
            getattr(element, method)(*args)
            return True
        except RuntimeError as exc:
            if "has been deleted" in str(exc):
                return False
            raise

    def safe_notify(message: str, **kwargs) -> bool:
        if not client_is_alive():
            return False
        try:
            with page_client:
                ui.notify(message, **kwargs)
            return True
        except RuntimeError as exc:
            if "has been deleted" in str(exc):
                return False
            raise

    async def stop_run_when_client_disconnects() -> None:
        """Prevent an orphaned flow when its browser tab is closed or reloaded."""
        if not processing["value"]:
            return
        stop_requested["value"] = True
        contexts = []
        parent = active_run.get("parent")
        if parent is not None:
            contexts.append(parent)
        contexts.extend(list(active_run["children"].values()))
        logger.info(
            "Delete-Back page disconnected; stopping {} owned run context(s)",
            len(contexts),
        )
        if contexts:
            await asyncio.gather(
                *(asyncio.to_thread(run_context.request_stop) for run_context in contexts),
                return_exceptions=True,
            )

    if page_client is not None:
        page_client.on_disconnect(stop_run_when_client_disconnects)

    def save_state():
        if suppress_autosave["value"]:
            return
        statuses = {}
        for it in videos_state["items"]:
            entry = {"steps": it["steps"]}
            for field in PERSIST_FIELDS:
                entry[field] = it.get(field, "")
            statuses[it["name"]] = entry
        try:
            state_manager.save_state(
                STATE_KEY,
                {
                    "video_folder": paths_state["video_folder"],
                    "music_folder": paths_state["music_folder"],
                    "output_folder": paths_state["output_folder"],
                    "random_music": options_state["random_music"],
                    "selected_channel": selected_channel["id"],
                    "statuses": statuses,
                },
            )
        except Exception as e:
            logger.error(f"Failed to save delete_back_flow state: {e}")

    def load_state():
        try:
            state = state_manager.load_state(STATE_KEY)
            if not state:
                return
            paths_state["video_folder"] = state.get("video_folder", "")
            paths_state["music_folder"] = state.get("music_folder", "")
            paths_state["output_folder"] = state.get("output_folder", "")
            options_state["random_music"] = state.get("random_music", False)
            selected_channel["id"] = state.get("selected_channel")
            saved_status_map.clear()
            saved_status_map.update(state.get("statuses", {}))

            def update_ui():
                if not client_is_alive():
                    return
                for render in folder_selectors.values():
                    render()
                if ui_refs["random_switch"]:
                    ui_refs["random_switch"].value = options_state["random_music"]
                if selected_channel["id"] and ui_refs["refresh_channel_display"]:
                    ui_refs["refresh_channel_display"]()
                if ui_refs.get("refresh_overlay"):
                    ui_refs["refresh_overlay"]()
                load_videos()

            ui.timer(0.5, update_ui, once=True)
        except Exception as e:
            logger.error(f"Failed to load delete_back_flow state: {e}")

    def load_videos():
        try:
            folder = normalize_path(paths_state["video_folder"])
            items = []
            if folder and Path(folder).is_dir():
                for p in list_media_files(folder, VIDEO_EXTENSIONS):
                    saved = saved_status_map.get(p.name, {})
                    try:
                        size = p.stat().st_size
                    except OSError:
                        size = 0

                    item = {
                        "name": p.name,
                        "path": str(p),
                        "size": size,
                        "duration": None,
                        "duration_error": "",
                        "steps": saved.get("steps") or _new_steps(),
                    }
                    for field in PERSIST_FIELDS:
                        item[field] = saved.get(field, "")

                    for k, st in item["steps"].items():
                        if st == "processing":
                            item["steps"][k] = "pending"

                    items.append(item)
            videos_state["items"] = items
            refresh_video_list()
            if items:
                ui.timer(0.05, load_durations, once=True)
        except Exception as e:
            logger.error(f"Error loading videos: {e}")

    async def load_durations():
        for item in videos_state["items"]:
            if item["duration"] is None:
                try:
                    item["duration"] = await asyncio.to_thread(
                        get_video_duration, item["path"]
                    )
                    item["duration_error"] = ""
                except FFprobeError as exc:
                    item["duration_error"] = str(exc)
                except Exception as exc:
                    item["duration_error"] = f"Unexpected metadata error: {exc}"
                    logger.exception(
                        "Unexpected duration error for {}: {}", item["path"], exc
                    )
                refresh_video_list()

    def step_badge(status: str):
        icon, color, label = STEP_STYLE.get(status, STEP_STYLE["pending"])
        with ui.row().classes(f"app-step-chip app-step-chip--{status} items-center justify-center gap-1 flex-nowrap"):
            ui.icon(icon).classes(f"text-sm shrink-0 {color}")
            ui.label(label).classes(f"text-xs font-medium whitespace-nowrap {color}")

    def refresh_video_list():
        if not element_is_alive(video_list_container):
            return
        video_list_container.clear()
        items = videos_state["items"]
        with video_list_container:
            with ui.row().classes("items-center gap-2 mb-1"):
                ui.icon("video_library").classes("text-gray-500")
                ui.label(f"Tìm thấy {len(items)} video").classes(
                    "text-sm font-semibold text-gray-700"
                )

            if not items:
                ui.label("Chưa chọn folder video hoặc folder không có video nào.").classes(
                    "text-gray-500 italic text-xs py-4"
                )
                return

            with ui.row().classes(
                "w-full min-h-[42px] items-center font-semibold text-xs text-gray-500 bg-gray-50 border-b border-gray-200 px-3"
            ):
                ui.label("#").classes("w-1/12")
                ui.label("Video").classes("w-3/12")
                ui.label("ID").classes("w-2/12")
                ui.label("Nhạc").classes("w-2/12")
                ui.label("Ghép nhạc").classes("w-1/12 text-center")
                ui.label("Upload").classes("w-1/12 text-center")
                ui.label("Chờ xử lý").classes("w-1/12 text-center")
                ui.label("Xóa - Back").classes("w-1/12 text-center")

            for idx, item in enumerate(items, 1):
                steps = item["steps"]
                with ui.row().classes(
                    "w-full min-h-[54px] items-center bg-white px-3 py-1 border-b border-gray-100 flex-nowrap hover:bg-gray-50"
                ):
                    ui.label(str(idx)).classes("w-1/12 text-xs text-gray-500")
                    with ui.column().classes("w-3/12 min-w-0 gap-0"):
                        ui.label(item["name"]).classes(
                            "truncate text-sm font-medium text-gray-800"
                        ).tooltip(item["name"])
                        size_str = _human_size(item["size"])
                        if item.get("duration_error"):
                            dur_str = "không đọc được duration"
                        elif item["duration"] is None:
                            dur_str = "đang đọc..."
                        else:
                            dur_str = _fmt_duration(item["duration"])
                        meta_label = ui.label(f"{size_str} · {dur_str}").classes("text-xs text-gray-400")
                        if item.get("duration_error"):
                            meta_label.tooltip(item["duration_error"])

                    vid = item.get("video_id")
                    with ui.column().classes("w-2/12 min-w-0"):
                        if vid:
                            ui.label(vid).classes(
                                "truncate text-xs font-medium text-indigo-600"
                            ).tooltip(vid)
                        else:
                            ui.label("—").classes("text-xs text-gray-400")

                    music_name = item.get("music") or "—"
                    ui.label(music_name).classes(
                        "w-2/12 truncate text-xs text-gray-600"
                    ).tooltip(music_name)

                    with ui.element("div").classes("w-1/12 flex justify-center"):
                        step_badge(steps["merge"])
                    with ui.element("div").classes("w-1/12 flex justify-center"):
                        step_badge(steps["upload"])
                    with ui.element("div").classes("w-1/12 flex justify-center"):
                        step_badge(steps["wait"])
                    with ui.element("div").classes("w-1/12 flex justify-center"):
                        step_badge(steps["delete_back"])

    def push_log(message: str, level: str = "info"):
        log_col = progress_refs["log"]
        if not element_is_alive(log_col):
            return
        style_cls = LOG_STYLE.get(level, LOG_STYLE["info"])
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            with log_col:
                ui.label(f"[{ts}] {message}").classes(f"text-xs font-mono {style_cls}")
        except RuntimeError as exc:
            if "has been deleted" not in str(exc):
                raise

    def set_processing_ui(is_processing: bool):
        processing["value"] = is_processing
        if is_processing:
            nav_state.lock("Đang chạy Delete-Back Flow, hãy bấm Dừng trước khi chuyển trang.")
            safe_element_call(ui_refs["process_btn"], "set_visibility", False)
            safe_element_call(ui_refs["stop_btn"], "set_visibility", True)
            safe_element_call(ui_refs["stop_btn"], "set_enabled", True)
            safe_element_call(ui_refs["clear_btn"], "set_enabled", False)
            safe_element_call(progress_refs["panel"], "set_visibility", True)
        else:
            nav_state.unlock()
            safe_element_call(ui_refs["process_btn"], "set_visibility", True)
            safe_element_call(ui_refs["stop_btn"], "set_visibility", False)
            safe_element_call(ui_refs["clear_btn"], "set_enabled", True)

    async def step_merge(item, output_folder, musics, index, run_config):
        if item.get("duration") is None:
            item["duration"] = await asyncio.to_thread(
                get_video_duration, item["path"]
            )
            item["duration_error"] = ""

        if run_config["random_music"]:
            music = random.choice(musics)
        else:
            music = musics[index % len(musics)]

        item["music"] = music.name
        item["music_path"] = str(music)
        base = str(Path(output_folder) / f"output_{index}")
        audio_out = f"{base}.m4v"
        video_out = f"{base}_processed.mp4"
        item["audio_path"] = audio_out
        item["output_path"] = video_out
        run_context = current_run_context()
        if run_context is not None:
            run_context.register_cleanup_path(audio_out)
            run_context.register_cleanup_path(video_out)

        overlay_png = run_config["overlay_png"]

        dur = await asyncio.to_thread(
            build_intermittent_audio,
            music_file=str(music),
            audio_out=audio_out,
        )
        await asyncio.to_thread(
            mux_audio_into_video,
            video_file=item["path"],
            audio_file=audio_out,
            video_out=video_out,
            duration=dur,
            overlay_png=overlay_png,
        )
        if run_context is not None:
            run_context.keep_path(audio_out)
            run_context.keep_path(video_out)

    async def step_upload(item, output_folder, musics, index, run_config):
        channel_id = run_config["channel_id"]
        assert channel_id, "Chưa chọn kênh"

        upload_prog = {"sent": 0, "total": 0}
        item["upload_progress"] = upload_prog
        result = await asyncio.to_thread(
            upload_video_module.upload,
            channel_id=channel_id,
            file_path=item["output_path"],
            index=index,
            progress=upload_prog,
        )
        item["frontend_upload_id"] = result["frontend_upload_id"]
        item["scotty_resource_id"] = result["scotty_resource_id"]

        video_id = await asyncio.to_thread(
            upload_video_module.create_video,
            channel_id=channel_id,
            title=Path(item["name"]).stem,
            frontend_upload_id=result["frontend_upload_id"],
            scotty_resource_id=result["scotty_resource_id"],
        )
        item["video_id"] = video_id

    async def step_wait_processed(item, output_folder, musics, index, run_config):
        channel_id = run_config["channel_id"]
        assert channel_id, "Chưa chọn kênh"
        video_id = item.get("video_id")
        assert video_id, "Chưa có Video ID"

        started_at = asyncio.get_running_loop().time()
        attempt = 0
        previous_status = object()
        while True:
            attempt += 1
            run_context = current_run_context()
            if run_context is not None:
                run_context.checkpoint()
            if stop_requested["value"]:
                raise TaskStopped()
            item["wait_attempt"] = attempt
            statuses = await asyncio.to_thread(
                list_videos_module.get_copyright_statuses, channel_id, {video_id}
            )
            st = (statuses or {}).get(video_id)
            if st == "UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_COMPLETED":
                return

            elapsed = int(asyncio.get_running_loop().time() - started_at)
            status_text = st or "chưa tìm thấy video trên YouTube Studio"
            safe_element_call(
                progress_refs.get("step"),
                "set_text",
                f"{item['name']}: lần kiểm tra {attempt} — {status_text} ({elapsed}s)",
            )
            if st != previous_status or attempt == 1 or attempt % 6 == 0:
                push_log(
                    f"{item['name']} - YouTube check #{attempt}: {status_text}",
                    "warning" if st is None else "info",
                )
                previous_status = st

            remaining = COPYRIGHT_WAIT_TIMEOUT_SECONDS - (
                asyncio.get_running_loop().time() - started_at
            )
            if remaining <= 0:
                break
            sleep_seconds = min(COPYRIGHT_POLL_INTERVAL_SECONDS, remaining)
            for _ in range(max(1, int(sleep_seconds * 10))):
                if run_context is not None:
                    run_context.checkpoint()
                await asyncio.sleep(0.1)
        raise TimeoutError(
            "YouTube chưa hoàn tất kiểm tra bản quyền sau "
            f"{COPYRIGHT_WAIT_TIMEOUT_SECONDS} giây; trạng thái cuối: "
            f"{previous_status or 'không tìm thấy video'}"
        )

    async def step_delete_back(item, output_folder, musics, index, run_config):
        channel_id = run_config["channel_id"]
        assert channel_id, "Chưa chọn kênh"
        video_id = item.get("video_id")
        assert video_id, "Chưa có Video ID"

        code = await asyncio.to_thread(
            delete_video_module.delete, video_id, channel_id
        )
        if code in (200, 204):
            _log_deleted(
                output_folder=output_folder,
                video_id=video_id,
                channel_id=channel_id,
                channel_name=run_config["channel_name"],
                title=item["name"],
            )
        else:
            raise RuntimeError(f"Xóa thất bại với status code HTTP {code}")

    STEP_SEQUENCE = [
        ("merge", "Ghép nhạc", step_merge),
        ("upload", "Upload", step_upload),
        ("wait", "Chờ kiểm tra bản quyền", step_wait_processed),
        ("delete_back", "Xóa - Back", step_delete_back),
    ]

    def update_parallel_progress(total: int, stats: dict) -> None:
        active = sum(
            1
            for item in videos_state["items"]
            if any(value == "processing" for value in item["steps"].values())
        )
        finished = stats["finished"]
        safe_element_call(
            progress_refs.get("current"),
            "set_text",
            f"Đang chạy {active}/{MAX_ACTIVE_VIDEOS} video song song",
        )
        safe_element_call(
            progress_refs.get("step"),
            "set_text",
            f"Hoàn tất {finished}/{total} — Lỗi {stats['failed']}",
        )
        safe_element_call(
            progress_refs.get("remaining"),
            "set_text",
            f"Còn lại: {max(0, total - finished)} video",
        )

    async def run_video_item(
        orig_index: int,
        item: dict,
        output_folder: str,
        musics: list,
        run_config: dict,
        step_limits: dict,
        errors: list,
        stats: dict,
        total: int,
    ) -> None:
        context_key = f"{orig_index}:{item['path']}"
        context = create_run_context(f"delete_back_video_{orig_index}")
        active_run["children"][context_key] = context
        failed = False
        file_index = orig_index + 1
        try:
            with bind_run_context(context):
                for step_key in _new_steps():
                    if item["steps"].get(step_key) == "processing":
                        item["steps"][step_key] = "pending"

                push_log(f"Video {file_index}: {item['name']}", "info")
                refresh_video_list()
                update_parallel_progress(total, stats)

                for step_key, step_name, step_fn in STEP_SEQUENCE:
                    if stop_requested["value"] or context.stopped:
                        raise TaskStopped()
                    if item["steps"].get(step_key) == "successful":
                        continue

                    item["steps"][step_key] = "processing"
                    push_log(f"{item['name']} - {step_name}: đang xử lý", "info")
                    refresh_video_list()
                    save_state()
                    update_parallel_progress(total, stats)
                    try:
                        async with step_limits[step_key]:
                            context.checkpoint()
                            await step_fn(
                                item,
                                output_folder,
                                musics,
                                file_index,
                                run_config,
                            )
                        item["steps"][step_key] = "successful"
                        push_log(
                            f"{item['name']} - {step_name}: thành công",
                            "success",
                        )
                    except TaskStopped:
                        item["steps"][step_key] = "stopped"
                        raise
                    except Exception as exc:
                        if context.stopped or stop_requested["value"]:
                            item["steps"][step_key] = "stopped"
                            raise TaskStopped() from exc
                        item["steps"][step_key] = "error"
                        failed = True
                        errors.append(f"{item['name']} [{step_name}]: {exc}")
                        logger.error(
                            "Delete-Back step '{}' failed for {}: {}",
                            step_key,
                            item["name"],
                            exc,
                        )
                        push_log(
                            f"{item['name']} - {step_name}: lỗi {exc}",
                            "error",
                        )
                        break
                    finally:
                        refresh_video_list()
                        save_state()
                        update_parallel_progress(total, stats)
        except TaskStopped:
            for step_key, value in item["steps"].items():
                if value == "processing":
                    item["steps"][step_key] = "stopped"
            push_log(f"{item['name']}: đã dừng", "warning")
        finally:
            context.cleanup()
            active_run["children"].pop(context_key, None)
            stats["finished"] += 1
            if failed:
                stats["failed"] += 1
            refresh_video_list()
            save_state()
            update_parallel_progress(total, stats)

    async def run_parallel_queue(
        pending_items: list,
        output_folder: str,
        musics: list,
        run_config: dict,
        errors: list,
    ) -> dict:
        queue: asyncio.Queue = asyncio.Queue()
        for entry in pending_items:
            queue.put_nowait(entry)

        stats = {"finished": 0, "failed": 0}
        step_limits = {
            "merge": asyncio.Semaphore(MAX_FFMPEG_JOBS),
            "upload": asyncio.Semaphore(MAX_UPLOAD_JOBS),
            "wait": asyncio.Semaphore(MAX_WAIT_JOBS),
            "delete_back": asyncio.Semaphore(MAX_DELETE_JOBS),
        }

        async def worker() -> None:
            while not stop_requested["value"]:
                try:
                    orig_index, item = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    await run_video_item(
                        orig_index,
                        item,
                        output_folder,
                        musics,
                        run_config,
                        step_limits,
                        errors,
                        stats,
                        len(pending_items),
                    )
                finally:
                    queue.task_done()

        workers = [
            asyncio.create_task(worker())
            for _ in range(min(MAX_ACTIVE_VIDEOS, len(pending_items)))
        ]
        worker_results = await asyncio.gather(*workers, return_exceptions=True)
        for result in worker_results:
            if isinstance(result, BaseException):
                stats["failed"] += 1
                errors.append(f"Lỗi worker: {result}")
                logger.error("Delete-Back worker failed: {}", result)
        return stats

    async def handle_process():
        if processing["value"]:
            safe_notify("Delete-Back Flow đang chạy", type="warning")
            return
        if not selected_channel["id"]:
            safe_notify("Vui lòng chọn kênh trước khi xử lý", type="warning")
            return
        if not paths_state["video_folder"]:
            safe_notify("Vui lòng chọn folder video", type="warning")
            return
        if not paths_state["music_folder"]:
            safe_notify("Vui lòng chọn folder nhạc", type="warning")
            return
        if not paths_state["output_folder"]:
            safe_notify("Vui lòng chọn folder output", type="warning")
            return

        music_dir = normalize_path(paths_state["music_folder"])
        musics = list_media_files(music_dir, AUDIO_EXTENSIONS)
        if not musics:
            safe_notify(f"Folder nhạc không có file {AUDIO_EXTENSIONS}", type="warning")
            return

        output_folder = normalize_path(paths_state["output_folder"])
        try:
            Path(output_folder).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            safe_notify(f"Không tạo được folder output: {exc}", type="negative")
            return

        pending_items = [
            (index, item)
            for index, item in enumerate(videos_state["items"])
            if any(st != "successful" for st in item["steps"].values())
        ]
        if not pending_items:
            safe_notify("Tất cả video đã hoàn thành thành công!", type="info")
            return

        channel_snapshot = get_channels_info(selected_channel["id"])
        if not channel_snapshot:
            safe_notify("Không tìm thấy dữ liệu kênh đã chọn", type="negative")
            return
        run_config = {
            "channel_id": selected_channel["id"],
            "channel_name": channel_snapshot.name or selected_channel["id"],
            "random_music": bool(options_state["random_music"]),
            "overlay_png": channel_snapshot.overlay_png or "",
        }

        if not _FLOW_RUN_GUARD.acquire(blocking=False):
            safe_notify(
                "Delete-Back Flow đang chạy ở một cửa sổ khác.",
                type="warning",
            )
            return

        stop_requested["value"] = False
        stopped = False
        total_items = len(pending_items)
        errors = []
        run_context = None
        try:
            run_context = create_run_context("delete_back_flow")
            active_run["parent"] = run_context
            active_run["children"].clear()
            set_processing_ui(True)
            push_log(
                f"Bắt đầu Delete-Back Flow — tối đa {MAX_ACTIVE_VIDEOS} video song song",
                "info",
            )
            stats = await run_parallel_queue(
                pending_items,
                output_folder,
                musics,
                run_config,
                errors,
            )
            stopped = stop_requested["value"] or run_context.stopped
            update_parallel_progress(total_items, stats)
        finally:
            set_processing_ui(False)
            save_state()
            if run_context is not None:
                run_context.cleanup()
            active_run["parent"] = None
            active_run["children"].clear()
            _FLOW_RUN_GUARD.release()

        done_count = sum(
            1
            for item in videos_state["items"]
            if all(value == "successful" for value in item["steps"].values())
        )
        if stopped:
            safe_element_call(progress_refs.get("step"), "set_text", "Đã dừng")
            push_log("Đã dừng theo yêu cầu. Có thể bấm Xử lý để chạy lại.", "warning")
            safe_notify(
                f"Đã dừng. {done_count}/{len(videos_state['items'])} video hoàn thành.",
                type="info",
            )
        elif errors:
            push_log("Quá trình kết thúc với một số video lỗi.", "error")
            safe_notify(
                f"Hoàn tất với lỗi. {done_count}/{len(videos_state['items'])} video thành công.",
                type="warning",
            )
        else:
            push_log("Delete-Back Flow đã hoàn tất.", "success")
            safe_notify("Quá trình xử lý kết thúc.", type="positive")

    async def handle_stop():
        stop_requested["value"] = True
        safe_element_call(ui_refs.get("stop_btn"), "set_enabled", False)
        safe_element_call(
            progress_refs.get("step"),
            "set_text",
            "Đang dừng tác vụ hiện tại...",
        )
        push_log("Đã nhấn Dừng. Đang kết thúc tài nguyên của tác vụ hiện tại...", "warning")
        contexts = []
        parent = active_run.get("parent")
        if parent is not None:
            contexts.append(parent)
        contexts.extend(list(active_run["children"].values()))
        if contexts:
            await asyncio.gather(
                *(asyncio.to_thread(context.request_stop) for context in contexts),
                return_exceptions=True,
            )

    def clear_all_inputs():
        try:
            suppress_autosave["value"] = True
            paths_state["video_folder"] = ""
            paths_state["music_folder"] = ""
            paths_state["output_folder"] = ""
            options_state["random_music"] = False
            selected_channel["id"] = None
            videos_state["items"] = []
            saved_status_map.clear()
            for render in folder_selectors.values():
                render()
            if ui_refs["random_switch"]:
                ui_refs["random_switch"].value = False
            if ui_refs["refresh_channel_display"]:
                ui_refs["refresh_channel_display"]()
            if ui_refs.get("refresh_overlay"):
                ui_refs["refresh_overlay"]()
            refresh_video_list()
        finally:
            suppress_autosave["value"] = False
        save_state()
        safe_notify("Đã xóa tất cả input và trạng thái", type="info")

    def build_folder_selector(key: str, label: str, placeholder: str, icon: str):
        card = ui.card().classes(
            "app-flow-folder flex-1 min-w-[280px] p-3 cursor-pointer transition-colors"
        )

        def pick_folder():
            chosen = select_directory(
                initial_dir=paths_state[key], title=f"Chọn {label}"
            )
            if chosen:
                paths_state[key] = chosen
                render()
                save_state()
                if key == "video_folder":
                    load_videos()

        def clear_folder(e=None):
            paths_state[key] = ""
            render()
            save_state()
            if key == "video_folder":
                load_videos()

        card.on("click", pick_folder)

        def render():
            path = paths_state[key]
            card.clear()
            with card:
                with ui.row().classes("items-center gap-3 w-full flex-nowrap"):
                    ui.icon(icon).classes("text-2xl shrink-0 text-emerald-600")
                    with ui.column().classes("gap-0 min-w-0 flex-1"):
                        ui.label(label).classes(
                            "text-xs font-semibold text-gray-600"
                        )
                        if path:
                            ui.label(path).classes(
                                "text-sm text-gray-800 truncate"
                            ).tooltip(path)
                        else:
                            ui.label(placeholder).classes(
                                "text-sm text-gray-400 italic truncate"
                            )

                    if path:
                        ui.button(icon="close", on_click=clear_folder).props(
                            "flat round dense size=sm color=grey"
                        ).classes("shrink-0")

        folder_selectors[key] = render
        render()

    channels = get_channels_info() or []

    page = ui.column().classes("app-page")
    with page:
        with page_header(
            "Xóa Back flow",
            "Ghép nhạc, upload, chờ YouTube xử lý và chạy bước Xóa - Back tự động.",
            eyebrow="Quy trình",
        ):
            pass
        workflow_steps(
            [
                {"title": "Ghép nhạc", "description": "Tạo video đầu ra", "state": "current"},
                {"title": "Upload", "description": "Đăng video lên kênh", "state": "pending"},
                {"title": "Chờ xử lý", "description": "Đợi trạng thái YouTube", "state": "pending"},
                {"title": "Xóa - Back", "description": "Hoàn tất quy trình", "state": "pending"},
            ]
        )
        main_container = ui.column().classes("w-full gap-4")
    with main_container:
        with app_card(compact=True):
            with section_header(
                "Thiết lập quy trình",
                "Chọn kênh, nguồn video, nguồn nhạc và nơi lưu file đầu ra.",
            ):
                pass

        def on_channel_select(channel_id: str):
            selected_channel["id"] = channel_id
            save_state()
            if ui_refs.get("refresh_overlay"):
                ui_refs["refresh_overlay"]()

        _, refresh_channel_display = create_channel_selection(
            channels,
            on_channel_select,
            initial_selected_ids=selected_channel["id"],
        )
        ui_refs["refresh_channel_display"] = refresh_channel_display

        def pick_overlay():
            cid = selected_channel["id"]
            if not cid:
                safe_notify("Hãy chọn kênh trước", type="warning")
                return
            path = select_file(title="Chọn ảnh tên kênh (PNG)")
            if path:
                channel_store.set_overlay_png(cid, path)
                refresh_overlay_display()
                safe_notify("Đã gán ảnh tên kênh cho kênh này", type="positive")

        def clear_overlay():
            cid = selected_channel["id"]
            if cid:
                channel_store.set_overlay_png(cid, "")
                refresh_overlay_display()

        overlay_row = ui.row().classes("items-center gap-2 mt-1 w-full flex-nowrap")

        def refresh_overlay_display():
            overlay_row.clear()
            with overlay_row:
                cid = selected_channel["id"]
                if not cid:
                    ui.label(
                        "Chọn kênh để gán ảnh tên kênh (overlay phủ toàn khung)"
                    ).classes("text-xs text-gray-400 italic")
                    return

                png = channel_store.get_overlay_png(cid)
                exists = Path(normalize_path(png)).is_file() if png else False

                if exists:
                    text = Path(png).name
                    color = "text-green-600"
                    icon_name = "check_circle"
                elif png:
                    text = f"Không tồn tại: {Path(png).name}"
                    color = "text-red-600"
                    icon_name = "error"
                else:
                    icon_name, color, text = (
                        "error",
                        "text-red-600",
                        "Chưa có ảnh tên kênh",
                    )

                ui.icon(icon_name).classes(f"{color} shrink-0")
                ui.label("Ảnh tên kênh:").classes("text-xs text-gray-600 shrink-0")
                ui.label(text).classes(
                    f"text-xs font-medium {color} truncate max-w-[240px]"
                ).tooltip(png)
                ui.button(
                    "Chọn PNG", icon="upload_file", on_click=pick_overlay
                ).props("dense outline size=sm")
                if png:
                    ui.button(icon="close", on_click=clear_overlay).props(
                        "flat round dense size=sm color=grey"
                    )

        ui_refs["refresh_overlay"] = refresh_overlay_display
        refresh_overlay_display()

        def on_random_change(e):
            options_state["random_music"] = bool(e.value)
            save_state()

        with ui.row().classes("w-full gap-3 flex-wrap items-stretch mt-3"):
            build_folder_selector(
                "video_folder", "Folder video", "Chọn folder chứa video", "movie"
            )
            build_folder_selector(
                "music_folder", "Folder nhạc", "Chọn folder chứa nhạc", "music_note"
            )
            build_folder_selector(
                "output_folder",
                "Folder output",
                "Chọn nơi lưu video đã ghép nhạc",
                "folder_output",
            )

        with ui.row().classes("mt-2 items-center"):
            random_switch = ui.switch(
                "Nhạc ngẫu nhiên",
                value=options_state["random_music"],
                on_change=on_random_change,
            )
            ui_refs["random_switch"] = random_switch

        with ui.row().classes("w-full gap-2 mt-3"):
            ui_refs["process_btn"] = (
                ui.button("Xử lý", icon="play_arrow", on_click=handle_process)
                .classes("app-button-primary flex-1")
            )
            ui_refs["stop_btn"] = (
                ui.button("Dừng", icon="stop", on_click=handle_stop)
                .classes("app-button-secondary flex-1")
            )
            ui_refs["stop_btn"].set_visibility(False)
            ui_refs["clear_btn"] = (
                ui.button("Xóa tất cả", icon="delete_sweep", on_click=clear_all_inputs)
                .classes("app-button-secondary flex-1")
            )

        progress_panel = ui.card().classes(
            "app-progress-panel w-full mt-2 gap-1 p-3"
        )
        with progress_panel:
            with ui.row().classes("items-center gap-2 w-full flex-nowrap"):
                ui.spinner(size="sm", color="primary")
                progress_refs["current"] = ui.label("Đang chuẩn bị...").classes(
                    "text-sm font-medium text-blue-900 flex-1 truncate"
                )
                progress_refs["remaining"] = ui.label("").classes(
                    "text-xs text-blue-700 shrink-0"
                )
            progress_refs["step"] = ui.label("").classes("text-xs text-gray-600")
            progress_refs["log_area"] = ui.scroll_area().classes(
                "w-full h-28 bg-white rounded border border-blue-100 mt-1"
            )
            with progress_refs["log_area"]:
                progress_refs["log"] = ui.column().classes("w-full gap-0.5 p-1")

        progress_panel.set_visibility(False)
        progress_refs["panel"] = progress_panel

        with app_card():
            with section_header(
                "Hàng đợi video",
                "Theo dõi trạng thái của từng video trong toàn bộ quy trình.",
            ):
                pass
            video_list_container = ui.column().classes("w-full gap-1")
        refresh_video_list()

    load_state()
