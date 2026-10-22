# RECOVERED: reconstructed from CPython 3.12 bytecode
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from loguru import logger
from nicegui import ui
from src.channel_groups import (
    ALL_GMAILS,
    channel_gmail,
    filter_channels_by_gmail,
    gmail_filter_options,
)
from web.theme import app_card
from src.video_scan_dates import DEFAULT_SCAN_DATE_TYPE, SCAN_DATE_TYPE_OPTIONS, scan_today


_tkinter_root = None


def create_scan_date_input(*, value: str = "", on_change):
    with ui.column().classes("gap-1"):
        field = ui.input("Quét từ ngày", value=value, on_change=on_change).props(
            f"outlined type=date clearable max={scan_today().isoformat()}"
        ).classes("w-52")
        field.tooltip(
            "Lọc theo loại ngày đã chọn, từ ngày bắt đầu đến hết hôm nay (giờ Việt Nam). "
            "Để trống để quét không giới hạn ngày."
        )
        field.on("focus", lambda: field.props(f"max={scan_today().isoformat()}"))
        ui.label("Đến hôm nay · giờ Việt Nam").classes("text-xs text-gray-500")
    return field


def create_scan_date_type_select(*, value=DEFAULT_SCAN_DATE_TYPE, on_change):
    return ui.select(
        SCAN_DATE_TYPE_OPTIONS, label="Tính theo ngày", value=value, on_change=on_change,
    ).props("outlined").classes("w-64").tooltip(
        "Tự động: video công khai dùng ngày công khai; video lên lịch dùng ngày dự kiến công khai; "
        "bản nháp và video chưa công khai dùng ngày tải lên."
    )


def get_tkinter_root():
    global _tkinter_root
    try:
        if _tkinter_root is None:
            _tkinter_root = tk.Tk()
            _tkinter_root.withdraw()
        else:
            try:
                _tkinter_root.winfo_exists()
            except tk.TclError:
                _tkinter_root = tk.Tk()
                _tkinter_root.withdraw()
        return _tkinter_root
    except Exception as e:
        logger.warning(f"Could not create tkinter root: {e}")
        return None


def select_directory(initial_dir: str | None = None, title: str = "Chọn thư mục") -> str | None:
    """Open a native folder picker and return the chosen path (or None).

    Runs synchronously on the main thread — tkinter is not thread-safe, so this
    must not be offloaded to a worker thread. It briefly blocks the event loop
    while the modal dialog is open, which is acceptable for this local tool.
    """
    root = get_tkinter_root()
    if root is None:
        return None
    try:
        root.update()

        root.wm_attributes("-topmost", 1)
        path = filedialog.askdirectory(
            parent=root,
            initialdir=initial_dir or str(Path.home()),
            title=title,
            mustexist=False,
        )

        return path or None
    except Exception as e:
        logger.error(f"Directory selection failed: {e}")
        return None


def select_file(
    initial_dir: str | None = None,
    title: str = "Chọn file",
    filetypes: list[tuple[str, str]] | None = None,
) -> str | None:
    """Open a native file picker and return the chosen path (or None).

    Runs synchronously on the main thread (tkinter is not thread-safe).
    """
    root = get_tkinter_root()
    if root is None:
        return None
    try:
        root.update()
        root.wm_attributes("-topmost", 1)
        path = filedialog.askopenfilename(
            parent=root,
            initialdir=initial_dir or str(Path.home()),
            title=title,
            filetypes=filetypes or [("All files", "*.*")],
        )

        return path or None
    except Exception as e:
        logger.error(f"File selection failed: {e}")
        return None


def reset_tkinter_root():
    global _tkinter_root
    try:
        if _tkinter_root:
            return None
    except Exception as e:
        logger.warning(f"Error resetting tkinter root: {e}")
        _tkinter_root = None


def create_channel_selection(
    channels,
    on_channel_select,
    multi_select: bool = False,
    initial_selected_ids: list[str] | str | None = None,
    *,
    can_change_selection=None,
    selection_state: dict | None = None,
):
    channels = list(channels or [])
    initial_ids = (
        [initial_selected_ids] if isinstance(initial_selected_ids, str)
        else list(initial_selected_ids or [])
    )
    selected_gmail = {"value": ALL_GMAILS}
    if multi_select:
        selected_ids = initial_ids
    else:
        selected_channel = selection_state if selection_state is not None else {}
        selected_channel.setdefault("id", (initial_ids or [None])[0])

    def change_allowed():
        return can_change_selection is None or can_change_selection()

    def visible_channels():
        return filter_channels_by_gmail(channels, selected_gmail["value"])

    def handle_gmail_change(event):
        previous = selected_gmail["value"]
        requested = event.value
        if requested == previous:
            return
        if not change_allowed():
            gmail_select.set_value(previous)
            return
        visible_ids = {
            channel.id for channel in filter_channels_by_gmail(channels, requested)
        }
        if multi_select:
            retained_ids = [cid for cid in selected_ids if cid in visible_ids]
            if retained_ids != selected_ids:
                if on_channel_select(retained_ids) is False:
                    gmail_select.set_value(previous)
                    return
                selected_ids[:] = retained_ids
        elif selected_channel["id"] and selected_channel["id"] not in visible_ids:
            if on_channel_select(None) is False:
                gmail_select.set_value(previous)
                return
            selected_channel["id"] = None
        selected_gmail["value"] = requested
        refresh_channel_display()

    def handle_channel_click(channel_id: str):
        if not change_allowed():
            return
        if multi_select:
            requested_ids = list(selected_ids)
            if channel_id in requested_ids:
                requested_ids.remove(channel_id)
            else:
                requested_ids.append(channel_id)
            if on_channel_select(requested_ids) is False:
                return
            selected_ids[:] = requested_ids
        else:
            requested_id = None if selected_channel["id"] == channel_id else channel_id
            if on_channel_select(requested_id) is False:
                return
            selected_channel["id"] = requested_id
        refresh_channel_display()

    def select_all():
        if not change_allowed():
            return
        requested_ids = [c.id for c in visible_channels()]
        if on_channel_select(requested_ids) is False:
            return
        selected_ids[:] = requested_ids
        refresh_channel_display()

    def deselect_all():
        if not change_allowed() or on_channel_select([]) is False:
            return
        selected_ids.clear()
        refresh_channel_display()

    def refresh_channel_display():
        channels_container.clear()
        with channels_container:
            if not channels:
                ui.label("Không có kênh nào. Hãy thêm kênh trước.").classes(
                    "text-gray-500 italic"
                )
                return

            for channel_data in visible_channels():
                name = channel_data.name
                avatar = channel_data.img_src
                cid = channel_data.id

                is_selected = (
                    cid in selected_ids
                    if multi_select
                    else selected_channel["id"] == cid
                )

                card_classes = "app-channel-card"
                if is_selected:
                    card_classes += " app-channel-card--selected"

                def create_channel_click_handler(channel_id):
                    def channel_click_handler():
                        handle_channel_click(channel_id)

                    return channel_click_handler

                with ui.card().classes(card_classes).on(
                    "click", create_channel_click_handler(cid)
                ):
                    with ui.row().classes("items-center gap-2 w-full"):
                        if avatar:
                            ui.image(avatar).classes("w-6 h-6 rounded-full")
                        else:
                            ui.icon("o_account_circle").classes(
                                "text-xl text-gray-400"
                            )
                        with ui.column().classes("gap-0 flex-1 min-w-0"):
                            ui.label(name).classes(
                                "text-xs font-medium text-gray-900 truncate w-full"
                            )
                            ui.label(channel_gmail(channel_data) or "Chưa xác định Gmail").classes(
                                "text-[10px] text-gray-500 truncate w-full"
                            )

                        if is_selected:
                            ui.icon("check_circle").classes(
                                "text-emerald-600 text-sm"
                            )

    with app_card(compact=True):
        with ui.row().classes("items-center justify-between mb-2"):
            with ui.column().classes("gap-0"):
                ui.label("Chọn kênh").classes("app-section-title")
                ui.label("Chọn kênh sẽ được sử dụng cho tác vụ này.").classes(
                    "app-section-copy"
                )
            if multi_select:
                with ui.row().classes("gap-1"):
                    ui.button("Tất cả", on_click=select_all).props(
                        "dense flat size=sm"
                    ).classes("text-emerald-600 text-xs")
                    ui.label("·").classes("text-gray-300 self-center")
                    ui.button("Bỏ chọn", on_click=deselect_all).props(
                        "dense flat size=sm"
                    ).classes("text-gray-500 text-xs")

        gmail_select = ui.select(
            gmail_filter_options(channels),
            value=ALL_GMAILS,
            label="Lọc kênh theo Gmail đã quét",
            on_change=handle_gmail_change,
        ).props("outlined dense options-dense").classes("w-full max-w-sm mb-3")
        if any(not channel_gmail(channel) for channel in channels):
            ui.label(
                "Kênh cũ chưa có Gmail: vào Tài khoản & kênh → Quét Gmail để cập nhật."
            ).classes("text-xs text-gray-500 mb-2")
        channels_container = ui.row().classes("gap-2 flex-wrap")
        refresh_channel_display()

    state = {"ids": selected_ids} if multi_select else selected_channel
    return state, refresh_channel_display
