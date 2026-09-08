# RECOVERED: clean-room implementation based on NiceGUI components & update_audio_module API
import asyncio
import threading
from pathlib import Path
from typing import Awaitable, Callable, Iterable, TypeVar
from nicegui import context, ui
from loguru import logger

from src.module.audio_module import update_audio_module
from src.state_manager import state_manager
from src.utils import get_channels_info
from web.components.common import create_channel_selection
from web.theme import app_card, empty_state, page_header, page_shell, section_header

STATE_KEY = "audio_remove"
_T = TypeVar("_T")
_REMOVE_AUDIO_RUN_GUARD = threading.Lock()


def _best_effort_ui(
    action: str,
    callback: Callable[[], object],
    *,
    is_available: Callable[[], bool] = lambda: True,
) -> bool:
    if not is_available():
        return False
    try:
        callback()
        return True
    except Exception as exc:
        logger.warning("Remove Audio UI action '{}' was skipped: {}", action, exc)
        return False


async def _gather_isolated(
    awaitables: Iterable[Awaitable[_T]],
) -> list[_T | BaseException]:
    return await asyncio.gather(*awaitables, return_exceptions=True)


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


def _restore_remove_statuses(statuses: dict | None, *, reset_processing: bool) -> dict:
    """Make a state from a stopped process retryable on the next launch."""
    restored = dict(statuses or {})
    if reset_processing:
        for video_id, status in restored.items():
            if status == "processing":
                restored[video_id] = "pending"
    return restored


def create_remove_audio_page():
    try:
        page_client = context.client
    except RuntimeError:
        page_client = None
    ui_available = {"value": True}

    def client_is_alive() -> bool:
        return (
            ui_available["value"]
            and page_client is not None
            and not getattr(page_client, "_deleted", False)
        )

    def best_effort_ui(action: str, callback: Callable[[], object]) -> bool:
        return _best_effort_ui(action, callback, is_available=client_is_alive)

    def mark_client_unavailable() -> None:
        ui_available["value"] = False

    if page_client is not None:
        page_client.on_disconnect(mark_client_unavailable)

    channels = get_channels_info() or []
    selected_remove_channel = {"id": None}
    ids_state = {"ids": []}
    video_processing_status = {}
    # Kept separately from the display status.  It is set *before* a
    # destructive request so a restart can verify what YouTube received.
    delete_requested = {}
    performance_settings = {"max_concurrency": 5}
    suppress_autosave = {"value": False}
    ui_refs = {
        "ids_textarea": None,
        "refresh_remove_channel_display": None,
    }

    def configuration_change_blocked() -> bool:
        if not _REMOVE_AUDIO_RUN_GUARD.locked():
            return False
        best_effort_ui(
            "notify locked remove-audio configuration",
            lambda: ui.notify("Xóa audio đang chạy; chưa thể thay đổi dữ liệu.", type="warning"),
        )
        return True

    def save_remove_state() -> bool:
        if suppress_autosave["value"]:
            return False
        state = {
            "selected_channel": selected_remove_channel["id"],
            "ids": ids_state["ids"],
            "video_processing_status": video_processing_status,
            "delete_requested": delete_requested,
        }
        try:
            return state_manager.save_state(STATE_KEY, state)
        except Exception as e:
            logger.error(f"Failed to save remove audio state: {e}")
            return False

    def load_remove_state():
        try:
            state = state_manager.load_state(STATE_KEY)
            if not state:
                return
            selected_remove_channel["id"] = state.get("selected_channel")
            ids_state["ids"] = state.get("ids", [])
            restored_statuses = _restore_remove_statuses(
                state.get("video_processing_status"),
                reset_processing=not _REMOVE_AUDIO_RUN_GUARD.locked(),
            )
            video_processing_status.clear()
            video_processing_status.update(restored_statuses)
            delete_requested.clear()
            delete_requested.update(state.get("delete_requested") or {})
            if restored_statuses != (state.get("video_processing_status") or {}):
                save_remove_state()

            def update_ui():
                def render_loaded_state():
                    if ui_refs["ids_textarea"] and ids_state["ids"]:
                        ui_refs["ids_textarea"].value = "\n".join(ids_state["ids"])
                    if ui_refs["refresh_remove_channel_display"]:
                        ui_refs["refresh_remove_channel_display"]()
                    refresh_right_panel()
                    logger.info("Remove audio state loaded and UI updated")

                best_effort_ui("render loaded remove-audio state", render_loaded_state)

            ui.timer(0.5, update_ui, once=True)
        except Exception as e:
            logger.error(f"Failed to load remove audio state: {e}")

    def on_channel_select(channel_id: str):
        if configuration_change_blocked():
            return
        selected_remove_channel["id"] = channel_id
        save_remove_state()

    def refresh_right_panel():
        right_panel_container.clear()
        with right_panel_container:
            if not ids_state["ids"]:
                empty_state(
                    "Chưa có Video ID",
                    "Nhập danh sách ID ở cột bên trái để bắt đầu.",
                    icon="o_layers_clear",
                )
                return

            with ui.row().classes(
                "w-full min-h-[42px] items-center font-semibold text-xs text-gray-500 bg-gray-50 border-b border-gray-200 px-3"
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
                elif status == "processing":
                    status_icon, status_color = "autorenew", "text-blue-600"
                else:
                    status_icon, status_color = "schedule", "text-yellow-600"

                with ui.row().classes(
                    "w-full min-h-[52px] items-center bg-white border-b border-gray-100 flex-nowrap px-1"
                ):
                    with ui.column().classes("w-8/12 p-2"):
                        ui.label(vid).classes(
                            "truncate px-2 py-1 font-medium text-gray-800 text-xs"
                        )
                    with ui.column().classes("w-3/12 text-center p-2"):
                        with ui.row().classes("items-center justify-center gap-1"):
                            ui.icon(status_icon).classes(f"text-sm {status_color}")
                            ui.label(status.title()).classes(
                                f"text-xs font-medium {status_color}"
                            )

                    def make_delete(video_id=vid):
                        def _delete():
                            if configuration_change_blocked():
                                return
                            if video_id in ids_state["ids"]:
                                ids_state["ids"].remove(video_id)
                            video_processing_status.pop(video_id, None)
                            delete_requested.pop(video_id, None)
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
        if configuration_change_blocked():
            if ui_refs["ids_textarea"]:
                ui_refs["ids_textarea"].value = "\n".join(ids_state["ids"])
            return
        if not ids_textarea.value:
            ids_state["ids"] = []
            video_processing_status.clear()
            delete_requested.clear()
        else:
            new_ids = parse_ids_from_text(ids_textarea.value)
            ids_state["ids"] = new_ids
            to_delete = [
                k for k in video_processing_status if k not in new_ids
            ]
            for k in to_delete:
                del video_processing_status[k]
                delete_requested.pop(k, None)
        refresh_right_panel()
        save_remove_state()

    async def handle_remove_audio():
        if not ids_state["ids"]:
            ui.notify("Vui lòng nhập ít nhất một Video ID", type="warning")
            return
        if not selected_remove_channel["id"]:
            ui.notify("Vui lòng chọn kênh", type="warning")
            return

        if not _REMOVE_AUDIO_RUN_GUARD.acquire(blocking=False):
            ui.notify("Xóa audio đang chạy ở một trang khác.", type="warning")
            return

        with ui.dialog() as progress_dialog:
            with ui.card().classes("app-card w-96"):
                ui.label("Đang xóa âm thanh...").classes("text-base font-semibold")
                status_label = ui.label("").classes("text-sm text-gray-600")
                progress_bar = ui.linear_progress(value=0)

        progress_dialog.props("persistent")
        best_effort_ui("open remove-audio progress dialog", progress_dialog.open)

        channel_id = selected_remove_channel["id"]
        video_ids_to_process = [
            video_id
            for video_id in ids_state["ids"]
            if video_processing_status.get(video_id) != "successful"
        ]
        if not video_ids_to_process:
            best_effort_ui(
                "close empty remove-audio progress dialog", progress_dialog.close
            )
            _REMOVE_AUDIO_RUN_GUARD.release()
            best_effort_ui(
                "notify no pending remove-audio videos",
                lambda: ui.notify("Các video đã xóa audio xong.", type="info"),
            )
            return
        total_tasks = max(1, len(video_ids_to_process))
        completed_tasks = 0
        overall_errors = []
        semaphore = asyncio.Semaphore(performance_settings["max_concurrency"])

        async def run_delete(vid: str):
            nonlocal completed_tasks
            async with semaphore:
                try:
                    if delete_requested.get(vid):
                        # A power loss can occur after the DELETE request is
                        # accepted but before its result is saved.  If no
                        # translated tracks remain, treat that request as
                        # completed instead of issuing a duplicate one.
                        remaining_tracks = await asyncio.to_thread(
                            update_audio_module._get_all_audio_track_ids,
                            vid,
                            channel_id,
                        )
                        if not remaining_tracks:
                            video_processing_status[vid] = "successful"
                            delete_requested.pop(vid, None)
                            if save_remove_state() is False:
                                delete_requested[vid] = True
                                video_processing_status[vid] = "pending"
                                raise RuntimeError(
                                    "Không thể lưu checkpoint xác nhận xóa audio"
                                )
                            return

                    video_processing_status[vid] = "processing"
                    delete_requested[vid] = True
                    if save_remove_state() is False:
                        raise RuntimeError("Không thể lưu checkpoint trước khi xóa audio")
                    best_effort_ui(
                        "render pending remove-audio video",
                        lambda: (
                            refresh_right_panel(),
                            status_label.set_text(f"{vid} - Đang xóa..."),
                        ),
                    )
                    await asyncio.to_thread(
                        update_audio_module.delete,
                        id_video=vid,
                        channel_id=channel_id,
                    )
                    video_processing_status[vid] = "successful"
                    delete_requested.pop(vid, None)
                    if save_remove_state() is False:
                        # Leave the intent in the next successful checkpoint;
                        # a restart will verify the remote result first.
                        delete_requested[vid] = True
                        video_processing_status[vid] = "pending"
                        raise RuntimeError(
                            "Không thể lưu checkpoint sau khi xóa audio"
                        )
                except Exception as exc:
                    video_processing_status[vid] = "unsuccessful"
                    # Keep the intent so an uncertain request is verified on
                    # the next resume rather than blindly repeated.
                    overall_errors.append(f"{vid}: {exc}")
                    save_remove_state()
                finally:
                    completed_tasks += 1
                    save_remove_state()
                    best_effort_ui(
                        "render completed remove-audio video",
                        lambda: (
                            setattr(
                                progress_bar,
                                "value",
                                completed_tasks / total_tasks,
                            ),
                            refresh_right_panel(),
                        ),
                    )

        tasks = [
            asyncio.create_task(run_delete(vid))
            for vid in video_ids_to_process
        ]
        try:
            results = await _gather_isolated(tasks)
            for vid, result in zip(video_ids_to_process, results):
                if isinstance(result, BaseException):
                    logger.error(
                        "Unexpected remove-audio worker failure for {}: {}", vid, result
                    )
                    video_processing_status[vid] = "unsuccessful"
                    overall_errors.append(f"{vid}: {result}")
                    save_remove_state()
        finally:
            save_remove_state()
            best_effort_ui("close remove-audio progress dialog", progress_dialog.close)
            best_effort_ui("render final remove-audio state", refresh_right_panel)
            _REMOVE_AUDIO_RUN_GUARD.release()

        if overall_errors:
            best_effort_ui(
                "notify remove-audio errors",
                lambda: ui.notify(
                    "Quá trình hoàn tất với một số lỗi. Kiểm tra trạng thái từng video bên dưới.",
                    type="warning",
                ),
            )
        else:
            best_effort_ui(
                "notify remove-audio completion",
                lambda: ui.notify(
                    "Quá trình hoàn tất thành công! Kiểm tra trạng thái từng video bên dưới.",
                    type="positive",
                ),
            )

    def clear_all_inputs():
        if configuration_change_blocked():
            return
        try:
            suppress_autosave["value"] = True
            if ui_refs["ids_textarea"]:
                ui_refs["ids_textarea"].value = ""
            ids_state["ids"] = []
            video_processing_status.clear()
            delete_requested.clear()
            selected_remove_channel["id"] = None
            refresh_right_panel()
            if ui_refs["refresh_remove_channel_display"]:
                ui_refs["refresh_remove_channel_display"]()
        finally:
            suppress_autosave["value"] = False
        save_remove_state()
        ui.notify("Đã xóa tất cả input và trạng thái", type="info")

    # Page layout
    with page_shell():
        with page_header(
            "Xóa audio",
            "Xóa audio track đã thêm khỏi danh sách video trên kênh được chọn.",
            eyebrow="Tác vụ",
        ):
            ui.button(
                "Xóa dữ liệu",
                icon="delete_sweep",
                on_click=clear_all_inputs,
            ).classes("app-button-secondary")
            ui.button(
                "Bắt đầu xóa",
                icon="play_arrow",
                on_click=handle_remove_audio,
            ).classes("app-button-primary")

        (
            remove_channel_state,
            refresh_remove_channel_display,
        ) = create_channel_selection(channels, on_channel_select)
        ui_refs["refresh_remove_channel_display"] = refresh_remove_channel_display

        with app_card():
            with section_header(
                "Video cần xử lý",
                "Mỗi dòng là một Video ID. Trạng thái được cập nhật ở bảng bên phải.",
            ):
                pass
            with ui.row().classes("w-full items-start gap-5 flex-wrap"):
                with ui.column().classes("w-72 shrink-0 gap-2"):
                    ui.label("Danh sách Video ID").classes(
                        "text-sm font-semibold text-gray-700"
                    )
                    ids_textarea = ui.textarea(
                        on_change=lambda e: on_ids_input()
                    ).props(
                        'outlined autocomplete=off rows=10 placeholder="Mỗi Video ID một dòng"'
                    ).classes("w-full")
                    ui_refs["ids_textarea"] = ids_textarea

                with ui.column().classes("flex-1 min-w-[420px]"):
                    right_panel_container = ui.column().classes(
                        "w-full border border-gray-200 rounded-lg overflow-hidden gap-0"
                    )

    load_remove_state()

    state_sync_timer = {
        "value": None,
        "observed_active_run": _REMOVE_AUDIO_RUN_GUARD.locked(),
    }

    def deactivate_state_sync_timer() -> None:
        timer = state_sync_timer["value"]
        if timer is not None:
            try:
                timer.deactivate()
            except RuntimeError:
                pass

    def sync_persisted_running_state() -> None:
        """Keep a reloaded page attached to a still-running delete job."""
        if not client_is_alive():
            deactivate_state_sync_timer()
            return

        run_is_active = _REMOVE_AUDIO_RUN_GUARD.locked()
        if run_is_active:
            state_sync_timer["observed_active_run"] = True
        if not run_is_active and not state_sync_timer["observed_active_run"]:
            deactivate_state_sync_timer()
            return

        try:
            state = state_manager.load_state(STATE_KEY) or {}
            refreshed_statuses = _restore_remove_statuses(
                state.get("video_processing_status"), reset_processing=False
            )
            refreshed_intents = state.get("delete_requested") or {}
            if (
                refreshed_statuses != video_processing_status
                or refreshed_intents != delete_requested
            ):
                video_processing_status.clear()
                video_processing_status.update(refreshed_statuses)
                delete_requested.clear()
                delete_requested.update(refreshed_intents)
                refresh_right_panel()
        except Exception as exc:
            logger.warning("Failed to sync remove-audio checkpoint: {}", exc)

        if not run_is_active:
            deactivate_state_sync_timer()

    state_sync_timer["value"] = ui.timer(0.5, sync_persisted_running_state)
