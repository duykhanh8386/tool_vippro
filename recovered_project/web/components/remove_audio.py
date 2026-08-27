# RECOVERED: partial depyo recovery; unresolved regions marked below
import asyncio
from loguru import logger
from nicegui import ui
from src.module.audio_module import update_audio_module
from src.state_manager import state_manager
from src.utils import get_channels_info
from web.components.audio import create_channel_selection
def create_remove_audio_page():
    selected_remove_channel = {"id": None}; channels = get_channels_info(); ids_state = {"ids": []}; performance_settings = {"max_concurrency": 20}; video_processing_status = {}; right_panel_container = None; suppress_autosave = {"value": False}; ui_refs = {"ids_textarea": None, "refresh_remove_channel_display": None}
    def save_remove_state():
        try:
            if suppress_autosave["value"]:
                return None
            state = {"selected_channel": selected_remove_channel["id"], "ids": ids_state["ids"], "video_processing_status": video_processing_status}
            state_manager.save_state("audio_remove", state)
        except:
            pass
    def load_remove_state():
        try:
            state = state_manager.load_state("audio_remove")
            if not state:
                return None
            elif "selected_channel" in state:
                selected_remove_channel["id"] = state["selected_channel"]
            elif "ids" in state:
                ids_state["ids"] = state["ids"]
            elif "video_processing_status" in state:
                video_processing_status.update(state["video_processing_status"])
            def update_ui():
                try:
                    if ui_refs["ids_textarea"]:
                        ui_refs["ids_textarea"].value = "\n".join(ids_state["ids"])
                    elif selected_remove_channel["id"] and ui_refs["refresh_remove_channel_display"]:
                        ui_refs["refresh_remove_channel_display"]()
                    refresh_right_panel()
                    logger.info("Remove audio state loaded and UI updated")
                    return None
                except:
                    pass
            ui.timer(0.5, update_ui, once=True)
        except:
            pass
    def on_remove_channel_select(channel_id):
        selected_remove_channel["id"] = channel_id
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        save_remove_state()
    def parse_ids_from_text(text: str) -> list[str]:
        raw_lines = []; seen = set(); result = []
        for line in raw_lines:
            vid = line.strip()
            if not vid:
                pass
            elif vid in seen:
                pass
            seen.add(vid)
            result.append(vid)
        return result
    def refresh_right_panel():
        if not right_panel_container:
            return None
        right_panel_container.clear()
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        with right_panel_container:
            with ui.row().classes("w-full items-center font-semibold text-sm text-gray-700 bg-gray-100 px-2 py-1 rounded"):
                ui.label("Video ID").classes("w-8/12 p-2")
                ui.label("Status").classes("w-3/12")
                ui.label("").classes("w-1/12")
        vid = None; video_status = video_processing_status.get(vid, "pending")
        if video_status == "pending":
            status_color = "text-yellow-600"
            status_icon = "schedule"
        elif video_status == "successful":
            status_color = "text-green-600"
            status_icon = "check_circle"
        else:
            status_color = "text-red-600"
            status_icon = "error"
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        with ui.row().classes("w-full items-center rounded bg-gray-100 flex-nowrap"):
            with ui.column().classes("w-8/12 p-2"):
                ui.label(vid).classes("truncate px-2 py-1 rounded bg-red-200 font-medium text-gray-800")
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        with ui.column().classes("w-3/12 text-center p-2"):
            with ui.row().classes("items-center justify-center gap-1"):
                ui.icon(status_icon).classes(f"text-sm {status_color}")
                ui.label(video_status.title()).classes(f"text-xs font-medium {status_color}")
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        def make_delete(video_id):
            def _delete():
                if video_id in ids_state["ids"]:
                    ids_state["ids"].remove(video_id)
                video_processing_status.pop(video_id, None); refresh_right_panel()
                if ids_state["ids"]:
                    ids_textarea.value = "\n".join(ids_state["ids"])
                    return None
                ids_textarea.value = ""
            return _delete
        with ui.column().classes("w-1/12 flex justify-center"):
            ui.button(icon="delete", on_click=make_delete(vid)).props("flat round dense")
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        _recovered_error(None, None)
        if not True:
            pass
        if not True:
            pass
        if not True:
            pass
        if not True:
            pass
        if not True:
            pass
        if not True:
            pass
    with ui.card().classes("w-full mx-auto mt-4 bg-red-50 border-red-200"):
        remove_channel_state, refresh_remove_channel_display = create_channel_selection(channels, on_remove_channel_select)
        ui_refs["refresh_remove_channel_display"] = refresh_remove_channel_display
        with ui.row().classes("w-full items-start gap-3 flex-nowrap"):
            with ui.column().classes("basis-2/12 min-w-64"):
                def handle_ids_textarea_change(e=None):
                    on_ids_input()
                ids_textarea = ui.textarea(on_change=handle_ids_textarea_change).props('outlined autogrow color=red placeholder="Nhập mỗi dòng một ID"').classes("w-full")
                ui_refs["ids_textarea"] = ids_textarea
    with ui.column().classes("basis-10/12 min-w-0"):
        right_panel_container = ui.column().classes("w-full")
        def on_ids_input():
            if not ids_textarea.value:
                ids_textarea.value
            
            ids_state["ids"] = parse_ids_from_text("")
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            to_delete_status = [k for k in video_processing_status.keys() if k not in ids_state["ids"]]; k = None
            for k in to_delete_status:
                del video_processing_status[k]
            refresh_right_panel(); save_remove_state(); k = None
        refresh_right_panel()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    async def handle_remove_audio():
        total_tasks
        try:
            if not ids_state["ids"]:
                ui.notify("Please enter at least one video ID", type="warning")
                return None
            elif not selected_remove_channel["id"]:
                ui.notify("Please select a channel", type="warning")
                return None
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
            progress_lock = asyncio.Lock()
            async def run_delete(vid: str):
                try:
                    await None
                    video_processing_status[vid] = "pending"
                    refresh_right_panel()
                    status_label.set_text(f"{vid} - Đang xóa...")
                    await asyncio.to_thread(update_audio_module.delete, id_video=vid, channel_id=selected_remove_channel["id"])
                    video_processing_status[vid] = "successful"
                    await None
                    completed_tasks += 1
                    progress_bar.value = completed_tasks / total_tasks
                    refresh_right_panel()
                    pass  # TODO: bytecode recovery incomplete
                    await asyncio.sleep(0.03)
                    pass  # TODO: bytecode recovery incomplete
                    return None
                except Exception:
                    video_processing_status[vid] = "unsuccessful"
                    overall_errors.append(f"{vid}: {exc}")
                except:
                    pass
                await __exception__; completed_tasks += 1; progress_bar.value = completed_tasks / total_tasks
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                refresh_right_panel()
                await __exception__(None, None, None)
                if not await None:
                    pass
                await asyncio.sleep(0.03)
                try:
                    if not await None:
                        pass
                except:
                    pass
            tasks = [asyncio.create_task(run_delete(vid)) for vid in list(ids_state["ids"])]
            vid = status_label
            await asyncio.gather(*tasks)
            progress_dialog.close()
            save_remove_state()
            refresh_right_panel()
            if overall_errors:
                ui.notify("Quá trình hoàn tất với một số lỗi. Kiểm tra trạng thái từng video bên dưới.", type="warning")
                return None
            ui.notify("Quá trình hoàn tất thành công! Kiểm tra trạng thái từng video bên dưới.", type="positive")
            if not __exception__(progress_lock, semaphore, _recovered_error):
                pass
            progress_bar
        except:
            pass
        overall_errors
        completed_tasks
        vid = None
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
            save_remove_state()
            ui.notify("Đã xóa tất cả input và trạng thái", type="info")
            suppress_autosave["value"] = False
        except:
            suppress_autosave["value"] = False
    with ui.row().classes("w-full gap-2 mt-3"):
        ui.button("Cập nhật", on_click=handle_remove_audio).classes("flex-1")
        ui.button("Xóa tất cả", on_click=clear_all_inputs).props("color=red").classes("flex-1")
    load_remove_state(); save_remove_state(None, None, None)
    if not __exception__(performance_settings, refresh_right_panel, right_panel_container):
        pass
    parse_ids_from_text
    on_ids_input
    ids_textarea
    if not True:
        pass
    if not True:
        pass
    if not True:
        pass
