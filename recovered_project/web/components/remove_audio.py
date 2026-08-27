# RECOVERED: clean-room implementation based on NiceGUI components & update_audio_module API
import asyncio
from pathlib import Path
from nicegui import ui
from loguru import logger

from src.module.audio_module import update_audio_module
from src.state_manager import state_manager
from src.utils import get_channels_info
from web.components.common import create_channel_selection

STATE_KEY = "audio_remove"


def parse_ids_from_text(text: str) -> list[str]:
    """Parse raw text into a list of unique video IDs."""
    if not text:
        return []
    ids = []
    seen = set()
    for line in text.splitlines():
        for item in line.replace(",", " ").split():
            clean_id = item.strip()
            if clean_id and clean_id not in seen:
                seen.add(clean_id)
                ids.append(clean_id)
    return ids


def create_remove_audio_page():
    channels = get_channels_info() or []
    selected_remove_channel = {"id": None}
    ids_state = {"ids": []}
    video_processing_status = {}
    performance_settings = {"max_concurrency": 5}
    suppress_autosave = {"value": False}
    ui_refs = {
        "ids_textarea": None,
        "refresh_remove_channel_display": None,
    }

    def save_remove_state():
        if suppress_autosave["value"]:
            return
        state = {
            "selected_channel": selected_remove_channel["id"],
            "ids": ids_state["ids"],
            "video_processing_status": video_processing_status,
        }
        try:
            state_manager.save_state(STATE_KEY, state)
        except Exception as e:
            logger.error(f"Failed to save remove audio state: {e}")

    def load_remove_state():
        try:
            state = state_manager.load_state(STATE_KEY)
            if not state:
                return
            selected_remove_channel["id"] = state.get("selected_channel")
            ids_state["ids"] = state.get("ids", [])
            video_processing_status.clear()
            video_processing_status.update(state.get("video_processing_status", {}))

            def update_ui():
                if ui_refs["ids_textarea"] and ids_state["ids"]:
                    ui_refs["ids_textarea"].value = "\n".join(ids_state["ids"])
                if ui_refs["refresh_remove_channel_display"]:
                    ui_refs["refresh_remove_channel_display"]()
                refresh_right_panel()
                logger.info("Remove audio state loaded and UI updated")

            ui.timer(0.5, update_ui, once=True)
        except Exception as e:
            logger.error(f"Failed to load remove audio state: {e}")

    def on_channel_select(channel_id: str):
        selected_remove_channel["id"] = channel_id
        save_remove_state()

    def refresh_right_panel():
        right_panel_container.clear()
        with right_panel_container:
            if not ids_state["ids"]:
                with ui.column().classes(
                    "w-full items-center justify-center py-12 text-gray-400 gap-2"
                ):
                    ui.icon("layers_clear").classes("text-4xl")
                    ui.label("Chưa có Video ID nào.").classes("text-sm")
                return

            with ui.row().classes(
                "w-full items-center font-semibold text-sm text-gray-700 bg-gray-100 px-2 py-1 rounded"
            ):
                ui.label("Video ID").classes("w-8/12 p-2")
                ui.label("Status").classes("w-3/12 p-2 text-center")
                ui.label("").classes("w-1/12")

            for vid in ids_state["ids"]:
                status = video_processing_status.get(vid, "pending")
                if status == "successful":
                    status_icon, status_color = "check_circle", "text-green-600"
                elif status == "unsuccessful":
                    status_icon, status_color = "error", "text-red-600"
                else:
                    status_icon, status_color = "schedule", "text-yellow-600"

                with ui.row().classes(
                    "w-full items-center rounded bg-gray-100 flex-nowrap mb-1"
                ):
                    with ui.column().classes("w-8/12 p-2"):
                        ui.label(vid).classes(
                            "truncate px-2 py-1 rounded bg-red-200 font-medium text-gray-800 text-xs"
                        )
                    with ui.column().classes("w-3/12 text-center p-2"):
                        with ui.row().classes("items-center justify-center gap-1"):
                            ui.icon(status_icon).classes(f"text-sm {status_color}")
                            ui.label(status.title()).classes(
                                f"text-xs font-medium {status_color}"
                            )

                    def make_delete(video_id=vid):
                        def _delete():
                            if video_id in ids_state["ids"]:
                                ids_state["ids"].remove(video_id)
                            video_processing_status.pop(video_id, None)
                            refresh_right_panel()
                            if ids_state["ids"]:
                                ids_textarea.value = "\n".join(ids_state["ids"])
                            else:
                                ids_textarea.value = ""
                            save_remove_state()

                        return _delete

                    with ui.column().classes("w-1/12 flex justify-center"):
                        ui.button(icon="delete", on_click=make_delete(vid)).props(
                            "flat round dense"
                        )

    def on_ids_input():
        if not ids_textarea.value:
            ids_state["ids"] = []
            video_processing_status.clear()
        else:
            new_ids = parse_ids_from_text(ids_textarea.value)
            ids_state["ids"] = new_ids
            to_delete = [
                k for k in video_processing_status if k not in new_ids
            ]
            for k in to_delete:
                del video_processing_status[k]
        refresh_right_panel()
        save_remove_state()

    async def handle_remove_audio():
        if not ids_state["ids"]:
            ui.notify("Vui lòng nhập ít nhất một Video ID", type="warning")
            return
        if not selected_remove_channel["id"]:
            ui.notify("Vui lòng chọn kênh", type="warning")
            return

        with ui.dialog() as progress_dialog:
            with ui.card().classes("w-96"):
                ui.label("Đang xóa âm thanh...").classes("text-base font-semibold")
                status_label = ui.label("").classes("text-sm text-gray-600")
                progress_bar = ui.linear_progress(value=0)

        progress_dialog.props("persistent")
        progress_dialog.open()

        total_tasks = max(1, len(ids_state["ids"]))
        completed_tasks = 0
        overall_errors = []
        semaphore = asyncio.Semaphore(performance_settings["max_concurrency"])

        async def run_delete(vid: str):
            nonlocal completed_tasks
            async with semaphore:
                try:
                    video_processing_status[vid] = "pending"
                    refresh_right_panel()
                    status_label.set_text(f"{vid} - Đang xóa...")
                    await asyncio.to_thread(
                        update_audio_module.delete,
                        id_video=vid,
                        channel_id=selected_remove_channel["id"],
                    )
                    video_processing_status[vid] = "successful"
                except Exception as exc:
                    video_processing_status[vid] = "unsuccessful"
                    overall_errors.append(f"{vid}: {exc}")
                finally:
                    completed_tasks += 1
                    progress_bar.value = completed_tasks / total_tasks
                    refresh_right_panel()

        tasks = [
            asyncio.create_task(run_delete(vid))
            for vid in list(ids_state["ids"])
        ]
        await asyncio.gather(*tasks)

        progress_dialog.close()
        save_remove_state()
        refresh_right_panel()

        if overall_errors:
            ui.notify(
                "Quá trình hoàn tất với một số lỗi. Kiểm tra trạng thái từng video bên dưới.",
                type="warning",
            )
        else:
            ui.notify(
                "Quá trình hoàn tất thành công! Kiểm tra trạng thái từng video bên dưới.",
                type="positive",
            )

    def clear_all_inputs():
        try:
            suppress_autosave["value"] = True
            if ui_refs["ids_textarea"]:
                ui_refs["ids_textarea"].value = ""
            ids_state["ids"] = []
            video_processing_status.clear()
            selected_remove_channel["id"] = None
            refresh_right_panel()
            if ui_refs["refresh_remove_channel_display"]:
                ui_refs["refresh_remove_channel_display"]()
        finally:
            suppress_autosave["value"] = False
        save_remove_state()
        ui.notify("Đã xóa tất cả input và trạng thái", type="info")

    # Page layout
    with ui.card().classes("w-full mx-auto mt-4 bg-red-50 border-red-200"):
        (
            remove_channel_state,
            refresh_remove_channel_display,
        ) = create_channel_selection(channels, on_channel_select)
        ui_refs["refresh_remove_channel_display"] = refresh_remove_channel_display

        with ui.row().classes("w-full items-start gap-3 flex-nowrap"):
            with ui.column().classes("basis-2/12 min-w-64"):
                ui.label("Danh sách Video ID:").classes(
                    "text-sm font-semibold text-gray-700 mt-2"
                )
                ids_textarea = ui.textarea(
                    on_change=lambda e: on_ids_input()
                ).props("outlined autocomplete=off rows=10 placeholder=Mỗi Video ID một dòng")
                ui_refs["ids_textarea"] = ids_textarea

                with ui.row().classes("w-full gap-2 mt-3"):
                    ui.button("Cập nhật", on_click=handle_remove_audio).classes(
                        "flex-1"
                    )
                    ui.button("Xóa tất cả", on_click=clear_all_inputs).props(
                        "color=red"
                    ).classes("flex-1")

            with ui.column().classes("basis-10/12 min-w-0"):
                right_panel_container = ui.column().classes("w-full")

    load_remove_state()
