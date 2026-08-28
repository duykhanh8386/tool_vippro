# RECOVERED: clean-room implementation based on NiceGUI components & delete_back_flow pipeline API
import asyncio
import csv
import random
from datetime import datetime
from pathlib import Path

from loguru import logger
from nicegui import ui

from src.channel_store import channel_store
from src.module.delete_video_module import delete_video_module
from src.module.list_videos_module import list_videos_module
from src.module.upload_video_module import upload_video_module
from src.state_manager import state_manager
from src.utils import (
    AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS,
    build_intermittent_audio,
    get_channels_info,
    get_video_duration,
    list_media_files,
    mux_audio_into_video,
    normalize_path,
)
from web.components.common import create_channel_selection, select_directory, select_file
from web.components.drawer import nav_state

STATE_KEY = "delete_back_flow"
_DELETE_LOG_FILENAME = "deleted_back_videos.csv"
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
    paths_state = {"video_folder": "", "music_folder": "", "output_folder": ""}
    options_state = {"random_music": False}
    selected_channel = {"id": None}
    videos_state = {"items": []}
    saved_status_map = {}
    suppress_autosave = {"value": False}
    stop_requested = {"value": False}
    processing = {"value": False}

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
                dur = await asyncio.to_thread(get_video_duration, item["path"])
                item["duration"] = dur or 0
                refresh_video_list()

    def step_badge(status: str):
        icon, color, label = STEP_STYLE.get(status, STEP_STYLE["pending"])
        with ui.row().classes("items-center justify-center gap-1 w-full flex-nowrap"):
            ui.icon(icon).classes(f"text-sm shrink-0 {color}")
            ui.label(label).classes(f"text-xs font-medium whitespace-nowrap {color}")

    def refresh_video_list():
        if not video_list_container:
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
                "w-full items-center font-semibold text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded"
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
                    "w-full items-center bg-white rounded px-2 py-1 border-b border-gray-100 flex-nowrap hover:bg-gray-50"
                ):
                    ui.label(str(idx)).classes("w-1/12 text-xs text-gray-500")
                    with ui.column().classes("w-3/12 min-w-0 gap-0"):
                        ui.label(item["name"]).classes(
                            "truncate text-sm font-medium text-gray-800"
                        ).tooltip(item["name"])
                        size_str = _human_size(item["size"])
                        dur_str = (
                            "đang đọc..."
                            if item["duration"] is None
                            else _fmt_duration(item["duration"])
                        )
                        ui.label(f"{size_str} · {dur_str}").classes("text-xs text-gray-400")

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
        if not log_col:
            return
        style_cls = LOG_STYLE.get(level, LOG_STYLE["info"])
        ts = datetime.now().strftime("%H:%M:%S")
        with log_col:
            ui.label(f"[{ts}] {message}").classes(f"text-xs font-mono {style_cls}")

    def set_processing_ui(is_processing: bool):
        processing["value"] = is_processing
        if is_processing:
            nav_state.lock("Đang chạy Delete-Back Flow, hãy bấm Dừng trước khi chuyển trang.")
            if ui_refs["process_btn"]:
                ui_refs["process_btn"].set_visibility(False)
            if ui_refs["stop_btn"]:
                ui_refs["stop_btn"].set_visibility(True)
            if ui_refs["clear_btn"]:
                ui_refs["clear_btn"].set_enabled(False)
            if progress_refs["panel"]:
                progress_refs["panel"].set_visibility(True)
        else:
            nav_state.unlock()
            if ui_refs["process_btn"]:
                ui_refs["process_btn"].set_visibility(True)
            if ui_refs["stop_btn"]:
                ui_refs["stop_btn"].set_visibility(False)
            if ui_refs["clear_btn"]:
                ui_refs["clear_btn"].set_enabled(True)

    async def step_merge(item, output_folder, musics, index):
        if options_state["random_music"]:
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

        cid = selected_channel["id"]
        overlay_png = channel_store.get_overlay_png(cid) if cid else ""

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
            overlay_png=overlay_png,
        )

    async def step_upload(item, output_folder, index):
        channel_id = selected_channel["id"]
        assert channel_id, "Chưa chọn kênh"

        step_label = progress_refs.get("step")
        upload_prog = {"sent": 0, "total": 0}

        def _tick_upload():
            total = upload_prog.get("total", 0)
            if total > 0 and step_label:
                pct = int(upload_prog.get("sent", 0) * 100 / total)
                sent_mb = upload_prog.get("sent", 0) / 1000000.0
                total_mb = total / 1000000.0
                step_label.set_text(
                    f"Bước: Upload — {pct}% ({sent_mb:.1f} MB / {total_mb:.1f} MB)"
                )

        prog_timer = ui.timer(0.5, _tick_upload)
        try:
            result = await asyncio.to_thread(
                upload_video_module.upload,
                channel_id=channel_id,
                file_path=item["output_path"],
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
        finally:
            prog_timer.cancel()

    async def step_wait_processed(item, output_folder, index):
        channel_id = selected_channel["id"]
        assert channel_id, "Chưa chọn kênh"
        video_id = item.get("video_id")
        assert video_id, "Chưa có Video ID"

        step_label = progress_refs.get("step")
        max_attempts = 60
        for attempt in range(1, max_attempts + 1):
            if stop_requested["value"]:
                raise RuntimeError("Người dùng đã dừng")
            if step_label:
                step_label.set_text(
                    f"Bước: Chờ xử lý — Thử lần {attempt}/{max_attempts}..."
                )
            statuses = await asyncio.to_thread(
                list_videos_module.get_copyright_statuses, channel_id, {video_id}
            )
            st = (statuses or {}).get(video_id)
            if st in (
                "UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_COMPLETED",
                "UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_STARTED",
            ):
                return
            await asyncio.sleep(5)

    async def step_delete_back(item, output_folder, index):
        channel_id = selected_channel["id"]
        assert channel_id, "Chưa chọn kênh"
        video_id = item.get("video_id")
        assert video_id, "Chưa có Video ID"

        code = await asyncio.to_thread(
            delete_video_module.delete, video_id, channel_id
        )
        if code in (200, 204):
            channels_info = get_channels_info() or []
            ch_name = next(
                (ch.name for ch in channels_info if ch.id == channel_id), channel_id
            )
            _log_deleted(
                output_folder=output_folder,
                video_id=video_id,
                channel_id=channel_id,
                channel_name=ch_name,
                title=item["name"],
            )
        else:
            raise RuntimeError(f"Xóa thất bại với status code HTTP {code}")

    async def handle_process():
        if not selected_channel["id"]:
            ui.notify("Vui lòng chọn kênh trước khi xử lý", type="warning")
            return
        if not paths_state["video_folder"]:
            ui.notify("Vui lòng chọn folder video", type="warning")
            return
        if not paths_state["music_folder"]:
            ui.notify("Vui lòng chọn folder nhạc", type="warning")
            return
        if not paths_state["output_folder"]:
            ui.notify("Vui lòng chọn folder output", type="warning")
            return

        music_dir = normalize_path(paths_state["music_folder"])
        musics = list_media_files(music_dir, AUDIO_EXTENSIONS)
        if not musics:
            ui.notify(f"Folder nhạc không có file {AUDIO_EXTENSIONS}", type="warning")
            return

        pending_items = [
            it
            for it in videos_state["items"]
            if any(st != "successful" for st in it["steps"].values())
        ]
        if not pending_items:
            ui.notify("Tất cả video đã hoàn thành thành công!", type="info")
            return

        stop_requested["value"] = False
        set_processing_ui(True)
        push_log("Bắt đầu Delete-Back Flow...", "info")

        total_items = len(pending_items)
        try:
            for idx, item in enumerate(pending_items, 1):
                if stop_requested["value"]:
                    push_log("Đã nhận yêu cầu dừng từ người dùng.", "warning")
                    break

                if progress_refs["current"]:
                    progress_refs["current"].set_text(
                        f"Đang xử lý ({idx}/{total_items}): {item['name']}"
                    )
                if progress_refs["remaining"]:
                    progress_refs["remaining"].set_text(
                        f"Còn lại: {total_items - idx} video"
                    )

                steps = item["steps"]
                # 1. Merge
                if steps["merge"] != "successful":
                    steps["merge"] = "processing"
                    refresh_video_list()
                    save_state()
                    if progress_refs["step"]:
                        progress_refs["step"].set_text("Bước: Ghép nhạc...")
                    try:
                        await step_merge(
                            item, paths_state["output_folder"], musics, idx
                        )
                        steps["merge"] = "successful"
                        push_log(f"{item['name']} - Ghép nhạc thành công", "success")
                    except Exception as exc:
                        steps["merge"] = "error"
                        push_log(f"{item['name']} - Ghép nhạc lỗi: {exc}", "error")
                        refresh_video_list()
                        save_state()
                        continue

                # 2. Upload
                if steps["upload"] != "successful":
                    steps["upload"] = "processing"
                    refresh_video_list()
                    save_state()
                    try:
                        await step_upload(item, paths_state["output_folder"], idx)
                        steps["upload"] = "successful"
                        push_log(
                            f"{item['name']} - Upload thành công (ID: {item.get('video_id')})",
                            "success",
                        )
                    except Exception as exc:
                        steps["upload"] = "error"
                        push_log(f"{item['name']} - Upload lỗi: {exc}", "error")
                        refresh_video_list()
                        save_state()
                        continue

                # 3. Wait
                if steps["wait"] != "successful":
                    steps["wait"] = "processing"
                    refresh_video_list()
                    save_state()
                    try:
                        await step_wait_processed(
                            item, paths_state["output_folder"], idx
                        )
                        steps["wait"] = "successful"
                        push_log(
                            f"{item['name']} - Xử lý bản quyền hoàn tất",
                            "success",
                        )
                    except Exception as exc:
                        steps["wait"] = "error"
                        push_log(f"{item['name']} - Chờ xử lý lỗi: {exc}", "error")
                        refresh_video_list()
                        save_state()
                        continue

                # 4. Delete-Back
                if steps["delete_back"] != "successful":
                    steps["delete_back"] = "processing"
                    refresh_video_list()
                    save_state()
                    try:
                        await step_delete_back(
                            item, paths_state["output_folder"], idx
                        )
                        steps["delete_back"] = "successful"
                        push_log(
                            f"{item['name']} - Xóa - Back thành công!",
                            "success",
                        )
                    except Exception as exc:
                        steps["delete_back"] = "error"
                        push_log(f"{item['name']} - Xóa - Back lỗi: {exc}", "error")

                refresh_video_list()
                save_state()

            ui.notify("Quá trình xử lý kết thúc.", type="info")
        finally:
            set_processing_ui(False)

    def handle_stop():
        stop_requested["value"] = True
        push_log("Đã nhấn Dừng. Đang đợi task hiện tại kết thúc...", "warning")

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
        ui.notify("Đã xóa tất cả input và trạng thái", type="info")

    def build_folder_selector(key: str, label: str, placeholder: str, icon: str):
        card = ui.card().classes(
            "flex-1 min-w-[280px] p-3 border border-gray-200 cursor-pointer hover:border-blue-400 transition-colors"
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
                    ui.icon(icon).classes("text-2xl shrink-0 text-blue-500")
                    with ui.column().classes("gap-0 min-w-0 flex-1"):
                        ui.label(label).classes(
                            "text-xs font-semibold text-gray-500 uppercase tracking-wider"
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

    with ui.card().classes("w-full mx-auto mt-4 bg-white shadow-sm"):
        ui.label(
            "Chọn kênh, folder video, folder nhạc và folder output rồi bấm Xử lý. Flow tự chạy: Ghép nhạc → Upload → Chờ xử lý → Xóa - Back."
        ).classes("text-sm text-gray-600 mb-3")

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
                ui.notify("Hãy chọn kênh trước", type="warning")
                return
            path = select_file(title="Chọn ảnh tên kênh (PNG)")
            if path:
                channel_store.set_overlay_png(cid, path)
                refresh_overlay_display()
                ui.notify("Đã gán ảnh tên kênh cho kênh này", type="positive")

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
                .classes("flex-1 bg-blue-600 text-white")
            )
            ui_refs["stop_btn"] = (
                ui.button("Dừng", icon="stop", on_click=handle_stop)
                .props("color=orange")
                .classes("flex-1")
            )
            ui_refs["stop_btn"].set_visibility(False)
            ui_refs["clear_btn"] = (
                ui.button("Xóa tất cả", icon="delete_sweep", on_click=clear_all_inputs)
                .props("color=red")
                .classes("flex-1")
            )

        progress_panel = ui.card().classes(
            "w-full mt-2 bg-blue-50 border border-blue-200 gap-1 p-3"
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

        ui.separator().classes("my-2")
        video_list_container = ui.column().classes("w-full gap-1")
        refresh_video_list()

    load_state()
