# RECOVERED: clean-room implementation based on NiceGUI components & delete_video_controller API
import os
import time
from nicegui import ui

from src.utils import get_channels_info
from web.components.common import create_channel_selection, select_directory
from web.components.delete_video_controller import delete_controller
from web.components.drawer import nav_state

PRIVACY_BADGE: dict[str, tuple[str, str]] = {
    "VIDEO_PRIVACY_PRIVATE": ("lock", "bg-gray-200 text-gray-600"),
    "VIDEO_PRIVACY_PUBLIC": ("public", "bg-green-100 text-green-700"),
    "VIDEO_PRIVACY_UNLISTED": ("link_off", "bg-orange-100 text-orange-700"),
}

PRIVACY_LABEL: dict[str, str] = {
    "VIDEO_PRIVACY_PRIVATE": "Riêng tư",
    "VIDEO_PRIVACY_PUBLIC": "Công khai",
    "VIDEO_PRIVACY_UNLISTED": "Không công khai",
}

ROW_STATUS_META: dict[str, tuple[str, str, str]] = {
    "waiting": ("hourglass_empty", "bg-yellow-100 text-yellow-700", "Chờ xử lý"),
    "ready": ("schedule_send", "bg-orange-100 text-orange-700", "Sắp xóa"),
    "deleting": ("autorenew", "bg-blue-100 text-blue-700", "Đang xóa..."),
    "deleted": ("check_circle", "bg-green-100 text-green-700", "Đã xóa ✓"),
    "error": ("error", "bg-red-100 text-red-700", "Lỗi ✗"),
    "skipped": ("skip_next", "bg-gray-100 text-gray-500", "Bỏ qua"),
}

NAV_LOCK_MSG = "Đang xử lý Xóa - Back, hãy bấm Dừng trước khi chuyển trang."
SYNC_INTERVAL = 0.5


def create_delete_video_page():
    channels = get_channels_info() or []
    selected_channels = {"ids": list(delete_controller.selected_channel_ids)}
    rendered_status = {}
    row_ui_refs = {}
    last_version = {"v": -1}
    header_drawn = {"value": False}
    ui_refs = {
        "scan_btn": None,
        "stop_btn": None,
        "status_label": None,
        "progress_bar": None,
        "summary_label": None,
        "table_container": None,
        "countdown_label": None,
        "folder_label": None,
    }

    def _render_chip(container, status: str):
        container.clear()
        icon_name, chip_cls, label_text = ROW_STATUS_META.get(
            status, ("help", "bg-gray-100 text-gray-600", status)
        )
        with container:
            with ui.row().classes(
                f"items-center gap-1 px-2 py-0.5 rounded text-xs font-medium {chip_cls}"
            ):
                ui.icon(icon_name).classes("text-sm")
                ui.label(label_text)

    def _render_header():
        with ui.row().classes(
            "w-full items-center font-semibold text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded mb-1"
        ):
            ui.label("Thumb").classes("w-16 shrink-0")
            ui.label("Kênh").classes("w-40 shrink-0")
            ui.label("Video ID").classes("w-28 shrink-0")
            ui.label("Tiêu đề").classes("flex-1")
            ui.label("Quyền riêng tư").classes("w-28 shrink-0")
            ui.label("Trạng thái").classes("w-36 shrink-0")

    def _render_row(video: dict):
        vid_id = video["id"]
        with ui.row().classes(
            "w-full items-center flex-nowrap border border-gray-100 rounded mb-0.5 bg-white hover:bg-gray-50"
        ):
            # Thumb
            with ui.column().classes("w-16 shrink-0 p-1"):
                if video.get("thumbnail"):
                    ui.image(video["thumbnail"]).classes(
                        "w-full aspect-video object-cover rounded"
                    )
                else:
                    ui.icon("videocam_off").classes(
                        "text-xl text-gray-300 mx-auto block"
                    )

            # Channel
            with ui.row().classes(
                "w-40 shrink-0 items-center gap-2 px-1 flex-nowrap"
            ):
                avatar = video.get("channel_avatar")
                if avatar:
                    ui.image(avatar).classes("w-6 h-6 rounded-full shrink-0")
                else:
                    ui.icon("account_circle").classes(
                        "text-xl text-gray-400 shrink-0"
                    )
                ch_name = video.get("channel_name") or "–"
                ui.label(ch_name).classes("text-xs text-gray-700 truncate")

            # Video ID
            with ui.column().classes("w-28 shrink-0 px-1"):
                ui.label(vid_id).classes(
                    "text-xs font-mono bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded break-all leading-tight"
                )

            # Title
            with ui.column().classes("flex-1 min-w-0 px-1"):
                ui.label(video.get("title") or "–").classes(
                    "text-xs font-medium text-gray-800 line-clamp-2 leading-tight"
                )

            # Privacy
            with ui.column().classes("w-28 shrink-0 px-1"):
                priv = video.get("privacy", "")
                p_icon, p_cls = PRIVACY_BADGE.get(
                    priv, ("help", "bg-gray-100 text-gray-600")
                )
                p_text = PRIVACY_LABEL.get(priv, priv or "–")
                with ui.row().classes(
                    f"items-center gap-1 px-2 py-0.5 rounded text-xs font-medium {p_cls}"
                ):
                    ui.icon(p_icon).classes("text-sm")
                    ui.label(p_text)

            # Status Chip container
            chip_box = ui.column().classes("w-36 shrink-0 px-1")
            _render_chip(chip_box, video.get("row_status", "waiting"))
            row_ui_refs[vid_id] = chip_box
            rendered_status[vid_id] = video.get("row_status")

    def _full_rebuild(video_list: list):
        tc = ui_refs["table_container"]
        if not tc:
            return
        tc.clear()
        rendered_status.clear()
        row_ui_refs.clear()
        with tc:
            if video_list:
                _render_header()
                for v in video_list:
                    _render_row(v)
            else:
                with ui.column().classes(
                    "w-full items-center justify-center py-8 text-gray-400 gap-2"
                ):
                    ui.icon("inbox").classes("text-4xl")
                    ui.label("Chưa có video nào trong danh sách.").classes(
                        "text-sm"
                    )

    def _reconcile_table():
        tc = ui_refs["table_container"]
        if not tc:
            return
        current_videos = delete_controller.all_videos
        current_ids = [v["id"] for v in current_videos]
        rendered_ids = list(rendered_status.keys())

        if current_ids != rendered_ids:
            _full_rebuild(current_videos)
            return

        for v in current_videos:
            vid_id = v["id"]
            new_st = v.get("row_status")
            if rendered_status.get(vid_id) != new_st:
                chip_box = row_ui_refs.get(vid_id)
                if chip_box:
                    _render_chip(chip_box, new_st)
                    rendered_status[vid_id] = new_st

    def _update_summary():
        counts = delete_controller.counts(ROW_STATUS_META.keys())
        total = len(delete_controller.all_videos)
        pb = ui_refs["progress_bar"]
        if pb:
            pb.set_visibility(bool(total))
            if total > 0:
                done_cnt = counts.get("deleted", 0) + counts.get("skipped", 0) + counts.get("error", 0)
                pb.set_value(done_cnt / total)
            else:
                pb.set_value(0)
        lbl = ui_refs["summary_label"]
        if lbl:
            parts = []
            if counts.get("waiting"):
                parts.append(f"⏳ {counts['waiting']} chờ xử lý")
            if counts.get("ready"):
                parts.append(f"🟠 {counts['ready']} sắp xóa")
            if counts.get("deleting"):
                parts.append(f"🔵 {counts['deleting']} đang xóa")
            if counts.get("deleted"):
                parts.append(f"✅ {counts['deleted']} đã xóa")
            if counts.get("error"):
                parts.append(f"❌ {counts['error']} lỗi")
            if counts.get("skipped"):
                parts.append(f"⏭ {counts['skipped']} bỏ qua")
            summary_str = " | ".join(parts) if parts else (f"Tổng số: {total} video" if total else "")
            lbl.set_text(summary_str)

    def _apply_run_state():
        running = delete_controller.is_running()
        scan_btn = ui_refs["scan_btn"]
        stop_btn = ui_refs["stop_btn"]
        if scan_btn:
            scan_btn.set_enabled(not running)
        if stop_btn:
            stop_btn.set_enabled(running)
        if running:
            nav_state.lock(NAV_LOCK_MSG)
        else:
            nav_state.unlock()

    def _update_countdown():
        cd = ui_refs["countdown_label"]
        if not cd:
            return
        if not delete_controller.is_running():
            cd.set_visibility(False)
            return
        cd.set_visibility(True)
        if delete_controller.polling:
            cd.set_text("Đang kiểm tra trạng thái...")
            return
        remaining = max(0, int(delete_controller.next_poll_at - time.time()))
        if remaining > 0:
            cd.set_text(f"Kiểm tra lại sau {remaining}s...")
        else:
            cd.set_text("Đang kiểm tra trạng thái...")

    def _sync_tick():
        if last_version["v"] != delete_controller.version:
            last_version["v"] = delete_controller.version
            _reconcile_table()
            _update_summary()
            _apply_run_state()
            status = ui_refs["status_label"]
            if status:
                status.set_text(delete_controller.status_text)
        _update_countdown()

    def on_channel_select(channel_ids: list):
        selected_channels["ids"] = channel_ids

    async def handle_scan():
        try:
            channel_ids = selected_channels["ids"]
            if not channel_ids:
                ui.notify("Vui lòng chọn ít nhất một kênh!", type="warning")
                return
            if delete_controller.is_running():
                return
            delete_controller.start(channel_ids, max_workers=5)
            last_version["v"] = -1
            _sync_tick()
        except Exception as exc:
            ui.notify(f"Lỗi khi bắt đầu quét: {exc}", type="negative")

    async def handle_stop():
        try:
            delete_controller.stop()
            last_version["v"] = -1
            _sync_tick()
        except Exception as exc:
            ui.notify(f"Lỗi khi dừng: {exc}", type="negative")

    def handle_pick_folder():
        chosen = select_directory(
            initial_dir=str(delete_controller.output_dir),
            title="Chọn thư mục lưu lịch sử xóa",
        )
        if not chosen:
            return
        delete_controller.set_output_dir(chosen)
        lbl = ui_refs["folder_label"]
        if lbl:
            lbl.set_text(str(delete_controller.output_dir))
        ui.notify(f"Đã chọn thư mục lưu: {delete_controller.output_dir}", type="positive")

    def handle_open_history():
        log_file = delete_controller.log_file
        if not log_file.exists():
            ui.notify(
                "Chưa có file lịch sử xóa. File sẽ được tạo sau khi xóa video.",
                type="warning",
            )
            return
        try:
            os.startfile(str(log_file))
        except Exception as exc:
            ui.notify(f"Không thể mở file lịch sử: {exc}", type="negative")

    # Main UI Layout
    with ui.column().classes("w-full max-w-5xl mx-auto p-4 gap-4"):
        # Header
        with ui.row().classes("items-center gap-3 mb-2"):
            ui.icon("delete_sweep").classes("text-3xl text-red-500")
            with ui.column().classes("gap-0"):
                ui.label("Xóa - Back").classes("text-2xl font-bold text-gray-800")
                ui.label("Tự động theo dõi bản quyền & xóa video vi phạm").classes(
                    "text-xs text-gray-500"
                )

        # Channel selection widget
        create_channel_selection(
            channels,
            on_channel_select,
            multi_select=True,
            initial_selected_ids=list(delete_controller.selected_channel_ids),
        )

        # Output dir settings card
        with ui.card().classes("w-full p-3"):
            with ui.row().classes("items-center gap-2 w-full flex-nowrap"):
                ui.icon("folder").classes("text-amber-500 shrink-0")
                ui.label("Thư mục lưu lịch sử xóa:").classes(
                    "text-sm text-gray-600 shrink-0"
                )
                ui_refs["folder_label"] = ui.label(
                    str(delete_controller.output_dir)
                ).classes("text-sm font-mono text-gray-800 truncate flex-1")
                ui.button(
                    "Chọn thư mục", icon="folder_open", on_click=handle_pick_folder
                ).props("outline dense").classes("text-xs")
                ui.button(
                    "Mở file lịch sử", icon="description", on_click=handle_open_history
                ).props("outline dense").classes("text-xs")

        # Controls card (Scan / Stop)
        with ui.card().classes("w-full p-4"):
            with ui.row().classes("items-center gap-3 flex-wrap"):
                scan_btn = (
                    ui.button("Quét & Xóa", icon="auto_delete", on_click=handle_scan)
                    .props("outline")
                    .classes("bg-red-50 text-red-600 border-red-200")
                )
                ui_refs["scan_btn"] = scan_btn
                stop_btn = (
                    ui.button("Dừng", icon="stop", on_click=handle_stop)
                    .props("outline")
                    .classes("text-gray-600")
                )
                ui_refs["stop_btn"] = stop_btn
            ui.separator().classes("my-2 opacity-40")
            ui_refs["status_label"] = ui.label(delete_controller.status_text).classes(
                "text-sm text-gray-600 italic"
            )

        # Video status list card
        with ui.card().classes("w-full p-4"):
            pb = ui.linear_progress(value=0).classes("w-full mb-1")
            pb.set_visibility(False)
            ui_refs["progress_bar"] = pb
            with ui.row().classes("items-center justify-between mb-3"):
                ui_refs["summary_label"] = ui.label("").classes(
                    "text-xs text-gray-500"
                )
                cd_lbl = ui.label("").classes("text-xs text-orange-400 italic")
                cd_lbl.set_visibility(False)
                ui_refs["countdown_label"] = cd_lbl

            table_container = ui.column().classes("w-full gap-0")
            ui_refs["table_container"] = table_container

    # Initial render & timer setup
    _full_rebuild(list(delete_controller.all_videos))
    last_version["v"] = delete_controller.version
    _update_summary()
    _apply_run_state()
    _update_countdown()
    ui.timer(SYNC_INTERVAL, _sync_tick)
