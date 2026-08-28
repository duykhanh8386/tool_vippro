# RECOVERED: reconstructed from CPython 3.12 bytecode
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from loguru import logger
from nicegui import ui


_tkinter_root = None


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
    initial_selected_ids: list[str] | None = None,
):
    if multi_select:
        selected_ids = list(initial_selected_ids or [])
    else:
        selected_channel = {"id": (initial_selected_ids or [None])[0]}

    def handle_channel_click(channel_id: str):
        if multi_select:
            if channel_id in selected_ids:
                selected_ids.remove(channel_id)
            else:
                selected_ids.append(channel_id)
            on_channel_select(list(selected_ids))
        elif selected_channel["id"] == channel_id:
            selected_channel["id"] = None
            on_channel_select(None)
        else:
            selected_channel["id"] = channel_id
            on_channel_select(channel_id)
        refresh_channel_display()

    def select_all():
        selected_ids.clear()
        selected_ids.extend(c.id for c in channels)
        on_channel_select(list(selected_ids))
        refresh_channel_display()

    def deselect_all():
        selected_ids.clear()
        on_channel_select([])
        refresh_channel_display()

    def refresh_channel_display():
        channels_container.clear()
        with channels_container:
            if not channels:
                ui.label("Không có kênh nào. Hãy thêm kênh trước.").classes(
                    "text-gray-500 italic"
                )
                return

            for channel_data in channels:
                name = channel_data.name
                avatar = channel_data.img_src
                cid = channel_data.id

                is_selected = (
                    cid in selected_ids
                    if multi_select
                    else selected_channel["id"] == cid
                )

                card_classes = "w-32 p-2 transition rounded-md shadow-sm cursor-pointer"
                if is_selected:
                    card_classes += " bg-blue-200 border-2 border-blue-500"
                else:
                    card_classes += " bg-gray-100 hover:bg-gray-200"

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
                            ui.icon("account_circle").classes(
                                "text-xl text-gray-500"
                            )
                        ui.label(name).classes(
                            "text-xs font-medium text-gray-900 flex-1 truncate"
                        )

                        if is_selected:
                            ui.icon("check_circle").classes(
                                "text-green-600 text-sm"
                            )

    with ui.card().classes("w-full"):
        with ui.row().classes("items-center justify-between mb-2"):
            ui.label("Chọn kênh").classes("text-base font-semibold")
            if multi_select:
                with ui.row().classes("gap-1"):
                    ui.button("Tất cả", on_click=select_all).props(
                        "dense flat size=sm"
                    ).classes("text-blue-600 text-xs")
                    ui.label("·").classes("text-gray-300 self-center")
                    ui.button("Bỏ chọn", on_click=deselect_all).props(
                        "dense flat size=sm"
                    ).classes("text-gray-500 text-xs")

        channels_container = ui.row().classes("gap-2 flex-wrap")
        refresh_channel_display()

    state = {"ids": selected_ids} if multi_select else selected_channel
    return state, refresh_channel_display
