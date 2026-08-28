# RECOVERED: partial depyo recovery; unresolved regions marked below
import asyncio, tempfile
from pathlib import Path
from loguru import logger
from nicegui import ui
from src.module.audio_module import AudioUpdateError, update_audio_module
from src.state_manager import state_manager
from src.utils import get_channels_info, multiply_audio, normalize_path, validate_path_text
def create_channel_selection(channels, on_channel_select):
    """Create a channel selection interface similar to studio page"""
    selected_channel = {"id": None}

    def handle_channel_click(channel_id):
        if selected_channel["id"] == channel_id:
            selected_channel["id"] = None
            on_channel_select(None)
        else:
            selected_channel["id"] = channel_id
            on_channel_select(channel_id)
        refresh_channel_display()

    def refresh_channel_display():
        channels_container.clear()
        with channels_container:
            if not channels:
                ui.label("Không có kênh nào. Hãy thêm kênh trước.").classes("text-gray-500 italic")
                return
            for channel_data in channels:
                name = channel_data.name
                avatar = channel_data.img_src
                cid = channel_data.id
                is_selected = selected_channel["id"] == cid
                card_classes = "w-32 p-2 transition rounded-md shadow-sm cursor-pointer"
                if is_selected:
                    card_classes += " bg-blue-200 border-2 border-blue-500"
                else:
                    card_classes += " bg-gray-100 hover:bg-gray-200"

                def create_channel_click_handler(channel_id):
                    def channel_click_handler():
                        handle_channel_click(channel_id)

                    return channel_click_handler

                with ui.card().classes(card_classes).on("click", create_channel_click_handler(cid)):
                    with ui.row().classes("items-center gap-2 w-full"):
                        if avatar:
                            ui.image(avatar).classes("w-6 h-6 rounded-full")
                        else:
                            ui.icon("account_circle").classes("text-xl text-gray-500")
                        ui.label(name).classes("text-xs font-medium text-gray-900 flex-1 truncate")
                        if is_selected:
                            ui.icon("check_circle").classes("text-green-600 text-sm")

    with ui.card().classes("w-full"):
        ui.label("Chọn kênh").classes("text-base font-semibold mb-2")
        channels_container = ui.row().classes("gap-2 flex-wrap")
        refresh_channel_display()
    return selected_channel, refresh_channel_display
def create_add_audio_page():
    selected_channel = {"id": None}; selected_languages = {"languages": []}; channels = get_channels_info(); video_ids_state = {"ids": []}; id_to_path = {}; video_processing_status = {}; video_processing_errors = {}; repeat_settings = {"times": 2, "extra_minutes": 0}; performance_settings = {"max_concurrency": 50}; right_panel_container = None; suppress_autosave = {"value": False}; ui_refs = {"ids_textarea": None, "language_input": None, "times_input": None, "minutes_input": None, "refresh_channel_display": None, "refresh_language_chips": None, "concurrency_input": None}
    def save_right_panel_state():
        """Save the current state of right_panel_container to file"""
        try:
            if suppress_autosave["value"]:
                return
            state = {"video_ids": video_ids_state["ids"], "id_to_path": id_to_path, "video_processing_status": video_processing_status, "video_processing_errors": video_processing_errors, "selected_languages": selected_languages["languages"], "repeat_settings": repeat_settings, "selected_channel": selected_channel["id"], "performance_settings": performance_settings}
            state_manager.save_state("audio_add", state)
        except Exception as e:
            logger.error(f"Failed to save right panel state: {e}")
    def load_right_panel_state():
        """Load the saved state from file"""
        try:
            state = state_manager.load_state("audio_add")
            if not state:
                return
            if "video_ids" in state:
                video_ids_state["ids"] = state["video_ids"]
            if "id_to_path" in state:
                id_to_path.update(state["id_to_path"])
            if "video_processing_status" in state:
                video_processing_status.update(state["video_processing_status"])
            if "video_processing_errors" in state:
                video_processing_errors.update(state["video_processing_errors"])
            if "selected_languages" in state:
                selected_languages["languages"] = state["selected_languages"]
            if "repeat_settings" in state:
                repeat_settings.update(state["repeat_settings"])
            if "selected_channel" in state:
                selected_channel["id"] = state["selected_channel"]
            if "performance_settings" in state:
                performance_settings.update(state["performance_settings"])
            def update_ui():
                try:
                    if ui_refs["ids_textarea"]:
                        ui_refs["ids_textarea"].value = "\n".join(video_ids_state["ids"])
                    if ui_refs["language_input"]:
                        ui_refs["language_input"].value = " ".join(selected_languages["languages"])
                    if ui_refs["times_input"]:
                        ui_refs["times_input"].value = repeat_settings["times"]
                    if ui_refs["minutes_input"]:
                        ui_refs["minutes_input"].value = repeat_settings["extra_minutes"]
                    if ui_refs["concurrency_input"]:
                        ui_refs["concurrency_input"].value = performance_settings["max_concurrency"]
                    refresh_right_panel()
                    if ui_refs["refresh_language_chips"]:
                        ui_refs["refresh_language_chips"]()
                    if selected_channel["id"] and ui_refs["refresh_channel_display"]:
                        ui_refs["refresh_channel_display"]()
                except Exception as e:
                    logger.error(f"Failed to update UI: {e}")
            ui.timer(0.5, update_ui, once=True)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
    def on_channel_select(channel_id):
        selected_channel["id"] = channel_id

        save_right_panel_state()
    def create_language_input_and_chips():
        """Create manual language input and display entered languages as chips"""
        def parse_languages(text: str) -> list[str]:
            tokens = (text or "").strip().split()
            seen = set()
            result = []
            for token in tokens:
                lang = token.strip()
                if not lang:
                    continue
                if lang in seen:
                    continue
                seen.add(lang)
                result.append(lang)
            return result
        def refresh_language_chips():
            language_chips_container.clear()
            with language_chips_container:
                for language in list(selected_languages["languages"]):
                    chip_classes = "px-2 py-1 rounded-full text-xs font-medium cursor-pointer transition-all duration-200 border bg-blue-500 text-white border-blue-500 hover:bg-blue-600"
                    def create_remove_handler(lang: str):
                        def _remove():
                            if lang in selected_languages["languages"]:
                                selected_languages["languages"].remove(lang)
                                language_input.value = " ".join(selected_languages["languages"])
                                refresh_language_chips()
                                return None
                                return None
                        return _remove
                    ui.label(language).classes(chip_classes).on("click", create_remove_handler(language))
            pass  # TODO: bytecode recovery incomplete
        def on_language_input_change(e=None):
            selected_languages["languages"] = parse_languages(language_input.value)

            refresh_language_chips(); save_right_panel_state()
        def reset_languages():
            selected_languages["languages"] = []

            language_input.value = ""; refresh_language_chips()

        with ui.card().classes("w-full mt-2"):
            with ui.row().classes("items-center justify-between mb-2"):
                ui.label("Nhập ngôn ngữ").classes("text-base font-semibold")
                ui.button("Đặt lại", on_click=reset_languages).props("dense color=red").classes("text-xs")
            language_input = ui.input(label="Mã ngôn ngữ, cách nhau bởi khoảng trắng").props('outlined clearable placeholder="en vi ja ..."').classes("w-full")
            ui_refs["language_input"] = language_input
            language_input.on("input", on_language_input_change)
            language_input.on("change", on_language_input_change)
            language_chips_container = ui.row().classes("gap-1 flex-wrap mt-2")
            refresh_language_chips()

        ui_refs["refresh_language_chips"] = refresh_language_chips
        return refresh_language_chips
    def create_repeat_settings():
        """Create repeat settings interface"""
        with ui.card().classes("w-full mt-2"):
            ui.label("Cài đặt lặp lại âm thanh").classes("text-base font-semibold mb-2")
            with ui.row().classes("gap-4 items-end"):
                times_input = ui.number(label="Số lần lặp lại (n)", value=repeat_settings["times"], min=1, max=10, step=1).props("outlined").classes("w-32")
                ui_refs["times_input"] = times_input
                def update_times(e):
                    value = int(e.args) if e.args and int(e.args) >= 1 else 1
                    repeat_settings["times"] = value

                    times_input.value = value; save_right_panel_state()
                times_input.on("change", update_times)
                minutes_input = ui.number(label="Phút bổ sung (m)", value=repeat_settings["extra_minutes"], min=0, max=60, step=1).props("outlined").classes("w-32")
                ui_refs["minutes_input"] = minutes_input
                def update_minutes(e):
                    value = float(e.args) if e.args and float(e.args) >= 0 else 0
                    repeat_settings["extra_minutes"] = value

                    minutes_input.value = value; save_right_panel_state()
                minutes_input.on("change", update_minutes)
                ui.label("Âm thanh sẽ được lặp lại n lần, với m phút bổ sung từ đầu âm thanh gốc").classes("text-xs text-gray-600 flex-1")

    def parse_ids_from_text(text: str) -> list[str]:
        """Parse newline-separated IDs, strip, deduplicate preserving order."""
        raw_lines = text.splitlines() if text else []
        seen = set()
        result = []
        for line in raw_lines:
            vid = line.strip()
            if not vid:
                continue
            if vid in seen:
                continue
            seen.add(vid)
            result.append(vid)
        return result
    def refresh_right_panel():
        if not right_panel_container:
            return
        right_panel_container.clear()

        with right_panel_container:
            with ui.row().classes("w-full items-center font-semibold text-sm text-gray-700 bg-gray-100 px-2 py-1 rounded"):
                ui.label("Video ID").classes("w-2/12 p-2")
                ui.label("Audio Path").classes("w-5/12")
                ui.label("Languages").classes("w-2/12")
                ui.label("Status").classes("w-2/12")
                ui.label("").classes("w-1/12")
            for vid in video_ids_state["ids"]:
                current_path_value = id_to_path.get(vid, "")
                video_status = video_processing_status.get(vid, {})
                video_errors = video_processing_errors.get(vid, {})
                total_languages = len(selected_languages["languages"])
                successful_count = sum(1 for status in video_status.values() if status == "successful")
                already_added_count = sum(1 for status in video_status.values() if status == "already_added")
                unsuccessful_count = sum(1 for status in video_status.values() if status == "unsuccessful")
                effective_success = successful_count + already_added_count
                pending_count = total_languages - effective_success - unsuccessful_count
                if total_languages == 0:
                    overall_status = "pending"
                    status_color = "text-yellow-600"
                    status_icon = "schedule"
                elif effective_success > total_languages * 0.5:
                    overall_status = "successful"
                    status_color = "text-green-600"
                    status_icon = "check_circle"
                elif unsuccessful_count > 0 and effective_success + pending_count <= total_languages * 0.5:
                    overall_status = "unsuccessful"
                    status_color = "text-red-600"
                    status_icon = "error"
                else:
                    overall_status = "pending"
                    status_color = "text-yellow-600"
                    status_icon = "schedule"
                status_text = {
                    "pending": "Chờ xử lý",
                    "successful": "Thành công",
                    "unsuccessful": "Thất bại",
                }[overall_status]

                with ui.row().classes("w-full items-center rounded bg-gray-100 flex-nowrap"):
                    with ui.column().classes("w-2/12 p-2"):
                        ui.label(vid).classes("truncate px-2 py-1 rounded bg-green-200 font-medium text-gray-800")

                    def make_path_on_change(video_id: str, input_ref):
                        def _on_change(e=None):
                            id_to_path[video_id] = (input_ref.value or "").strip()
                            save_right_panel_state()

                        return _on_change

                    with ui.column().classes("w-5/12 min-w-0"):
                        path_input = ui.input("Audio Path").props("outlined clearable").classes("w-full")
                        path_input.value = current_path_value
                        path_input.on("change", make_path_on_change(vid, path_input))

                    with ui.column().classes("w-2/12 text-center ml-20"):
                        ui.label(f"{successful_count}/{total_languages}").classes("text-sm font-medium text-gray-700")
                        if already_added_count > 0:
                            ui.label(f"{already_added_count} đã có").classes("text-xs text-orange-500")

                    with ui.column().classes("w-2/12 text-center p-2"):
                        with ui.row().classes("items-center justify-center gap-1"):
                            ui.icon(status_icon).classes(f"text-sm {status_color}")
                            ui.label(status_text).classes(f"text-xs font-medium {status_color}")

                    def make_delete(video_id: str):
                        def _delete():
                            if video_id in video_ids_state["ids"]:
                                video_ids_state["ids"].remove(video_id)
                            id_to_path.pop(video_id, None)
                            video_processing_status.pop(video_id, None)
                            video_processing_errors.pop(video_id, None)
                            refresh_right_panel()
                            if video_ids_state["ids"]:
                                ids_textarea.value = "\n".join(video_ids_state["ids"])
                            else:
                                ids_textarea.value = ""

                        return _delete

                    with ui.column().classes("w-1/12 flex justify-center"):
                        ui.button(icon="delete", on_click=make_delete(vid)).props("flat round dense")

                if video_errors:
                    with ui.card().classes("w-full bg-red-50 border border-red-300 px-4 py-2 mt-1"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("error").classes("text-red-600")
                            ui.label(f"Không thể cập nhật audio cho video {vid}").classes("font-semibold text-red-700")
                        for error_lang, error_message in video_errors.items():
                            ui.label(f"Ngôn ngữ {error_lang}: {error_message}").classes("text-sm text-red-700 whitespace-normal break-words")
    async def handle_add_audio():
        if not selected_channel["id"]:
            ui.notify("Hãy chọn kênh", type="warning")
            return None
        elif len(selected_languages["languages"]) == 0:
            ui.notify("Hãy chọn ít nhất một ngôn ngữ", type="warning")
            return None
        elif len(video_ids_state["ids"]) == 0:
            ui.notify("Vui lòng nhập ít nhất một Video ID", type="warning")
            return None
        row_errors = []
        for vid in video_ids_state["ids"]:
            path_text = (id_to_path.get(vid) or "").strip()
            ok, msg = validate_path_text(path_text)
            if not ok:
                row_errors.append(f"{vid}: {msg}")
        if row_errors:
            ui.notify("Một số hàng không hợp lệ. Hãy kiểm tra lại.", type="negative")
            for err in row_errors:
                logger.error(err)
            return None
        video_processing_errors.clear()
        with ui.dialog() as progress_dialog:
            with ui.card().classes("w-96"):
                ui.label("Đang thêm âm thanh...").classes("text-base font-semibold")
                current_video_label = ui.label("").classes("text-sm font-medium text-blue-600")
                status_label = ui.label("").classes("text-sm text-gray-600")
                remaining_label = ui.label("").classes("text-xs text-gray-500")
                concurrent_label = ui.label("").classes("text-xs text-gray-500 mt-1")
                progress_bar = ui.linear_progress(value=0)
        progress_dialog.props("persistent")
        progress_dialog.open()
        total_videos = len(video_ids_state["ids"])
        total_tasks = total_videos * len(selected_languages["languages"])
        completed_tasks = 0
        overall_errors = []
        active_uploads = {"count": 0}
        upload_semaphore = asyncio.Semaphore(performance_settings["max_concurrency"])

        async def run_upload(vid: str, lang: str, temp_audio_path: Path, file_bytes: bytes):
            async with upload_semaphore:
                try:
                    if vid not in video_processing_status:
                        video_processing_status[vid] = {}
                    video_processing_status[vid][lang] = "pending"
                    refresh_right_panel()
                    active_uploads["count"] += 1
                    concurrent_label.set_text(f"Đang tải lên {active_uploads['count']} ngôn ngữ đồng thời")
                    status_code = None
                    last_error = None
                    max_retries = 3
                    for attempt in range(max_retries + 1):
                        try:
                            status_code = await asyncio.to_thread(
                                update_audio_module.add,
                                id_video=vid,
                                channel_id=selected_channel["id"],
                                file_name=str(temp_audio_path),
                                language=lang,
                                data=file_bytes,
                            )
                            if status_code in (200, 409):
                                break
                        except Exception as e:
                            last_error = str(e)
                            logger.error(f"Upload attempt {attempt + 1}/{max_retries + 1} failed for {vid}-{lang}: {e}", exc_info=True)
                            if isinstance(e, AudioUpdateError) and not e.retryable:
                                break
                        if attempt < max_retries:
                            await asyncio.sleep(2)
                    if status_code == 200:
                        video_processing_status[vid][lang] = "successful"
                    elif status_code == 409:
                        video_processing_status[vid][lang] = "already_added"
                    else:
                        video_processing_status[vid][lang] = "unsuccessful"
                        error_message = last_error or f"YouTube trả về HTTP {status_code}"
                        video_processing_errors.setdefault(vid, {})[lang] = error_message
                        overall_errors.append(f"{vid}-{lang}: {error_message}")
                except Exception as exc:
                    if vid in video_processing_status:
                        video_processing_status[vid][lang] = "unsuccessful"
                    overall_errors.append(f"{vid}-{lang}: {exc}")
                    video_processing_errors.setdefault(vid, {})[lang] = str(exc)
                finally:
                    active_uploads["count"] -= 1
                    if active_uploads["count"] > 0:
                        concurrent_label.set_text(f"Đang tải lên {active_uploads['count']} ngôn ngữ đồng thời")
                    else:
                        concurrent_label.set_text("")

        try:
            for video_index, vid in enumerate(list(video_ids_state["ids"]), 1):
                try:
                    file_path = Path((id_to_path.get(vid) or "").strip())
                    current_video_label.set_text(f"Video {video_index}/{total_videos}: {vid}")
                    remaining_label.set_text(f"Còn lại: {total_videos - video_index} video")
                    status_label.set_text("Đang lấy thông tin video...")
                    video_info = await asyncio.to_thread(
                        update_audio_module._get_video_info,
                        video_id=vid,
                        channel_id=selected_channel["id"],
                    )
                    video_duration_seconds = video_info.duration_ms / 1000.0 if video_info.duration_ms > 0 else None
                    status_label.set_text("Đang xử lý âm thanh...")
                    with tempfile.NamedTemporaryFile(suffix=file_path.suffix, delete=False) as temp_file:
                        temp_audio_path = Path(temp_file.name)
                    await asyncio.to_thread(
                        multiply_audio,
                        input_file=normalize_path(str(file_path)),
                        output_file=str(temp_audio_path),
                        times=repeat_settings["times"],
                        extra_minutes=repeat_settings["extra_minutes"],
                        video_duration_seconds=video_duration_seconds,
                    )
                    file_bytes = await asyncio.to_thread(temp_audio_path.read_bytes)
                    status_label.set_text(f"Đang tải lên {len(selected_languages['languages'])} ngôn ngữ đồng thời...")
                    upload_tasks = []
                    for lang in selected_languages["languages"]:
                        task = asyncio.create_task(run_upload(vid=vid, lang=lang, temp_audio_path=temp_audio_path, file_bytes=file_bytes))
                        upload_tasks.append((task, lang))
                    for task, lang in upload_tasks:
                        await task
                        completed_tasks += 1
                        progress_bar.value = completed_tasks / total_tasks
                        refresh_right_panel()
                        completed_for_video = sum(1 for t, _ in upload_tasks if t.done())
                        status_label.set_text(f"Hoàn thành {completed_for_video}/{len(selected_languages['languages'])} ngôn ngữ cho video {vid}")
                    try:
                        if "temp_audio_path" in locals() and temp_audio_path.exists():
                            temp_audio_path.unlink()
                    except Exception as exc:
                        logger.warning(f"Failed to clean up temporary file {temp_audio_path}: {exc}")
                except Exception as vid_exc:
                    logger.error(f"Error processing video {vid}: {vid_exc}")
                    overall_errors.append(f"{vid}: {vid_exc}")
                    video_processing_errors.setdefault(vid, {})["xử lý"] = str(vid_exc)
                    completed_tasks += len(selected_languages["languages"])
                    progress_bar.value = completed_tasks / total_tasks
                    refresh_right_panel()
        except Exception as main_exc:
            logger.error(f"Main processing error: {main_exc}")
            overall_errors.append(f"Main process: {main_exc}")

        progress_dialog.close()
        save_right_panel_state()
        refresh_right_panel()
        total_videos = len(video_ids_state["ids"])
        successful_videos = 0
        for vid in video_ids_state["ids"]:
            video_status = video_processing_status.get(vid, {})
            total_languages = len(selected_languages["languages"])
            successful_count = sum(1 for status in video_status.values() if status in ("successful", "already_added"))
            if total_languages > 0 and successful_count > total_languages * 0.5:
                successful_videos += 1
        success_percentage = successful_videos / total_videos * 100 if total_videos > 0 else 0
        if overall_errors:
            ui.notify(f"Cập nhật thất bại: {overall_errors[0]}. Xem chi tiết trong khung màu đỏ bên dưới.", type="negative")
        else:
            ui.notify(f"Quá trình hoàn tất! {successful_videos}/{total_videos} video thành công. Kiểm tra trạng thái từng video bên dưới.", type="positive" if success_percentage >= 50 else "warning")

    with ui.card().classes("w-full mx-auto mt-4 bg-green-50 border-green-200"):
        channel_state, refresh_channel_display = create_channel_selection(channels, on_channel_select)
        ui_refs["refresh_channel_display"] = refresh_channel_display
        refresh_language_chips = create_language_input_and_chips()
        create_repeat_settings()
        with ui.row().classes("w-full items-start gap-3 flex-nowrap"):
            with ui.column().classes("basis-2/12 min-w-64"):
                def handle_ids_textarea_change(e=None):
                    on_ids_input()
                ids_textarea = ui.textarea(on_change=handle_ids_textarea_change).props('outlined autogrow color=green placeholder="Nhập mỗi dòng một ID"').classes("w-full")
                ui_refs["ids_textarea"] = ids_textarea
            with ui.column().classes("basis-10/12 min-w-0"):
                right_panel_container = ui.column().classes("w-full")
                def on_ids_input():
                    video_ids_state["ids"] = parse_ids_from_text(ids_textarea.value or "")
                    to_delete_path = [k for k in id_to_path.keys() if k not in video_ids_state["ids"]]
                    for k in to_delete_path:
                        del id_to_path[k]
                        video_processing_status.pop(k, None)
                        video_processing_errors.pop(k, None)
                    refresh_right_panel()
                    save_right_panel_state()
                refresh_right_panel()
        load_right_panel_state()
        def clear_all_inputs():
            """Clear all inputs and reset form state"""
            try:
                suppress_autosave["value"] = True
                if ui_refs["ids_textarea"]:
                    ui_refs["ids_textarea"].value = ""
                if ui_refs["language_input"]:
                    ui_refs["language_input"].value = ""
                if ui_refs["times_input"]:
                    ui_refs["times_input"].value = 2
                if ui_refs["minutes_input"]:
                    ui_refs["minutes_input"].value = 0
                if ui_refs["concurrency_input"]:
                    ui_refs["concurrency_input"].value = 50
                video_ids_state["ids"] = []
                id_to_path.clear()
                video_processing_status.clear()
                video_processing_errors.clear()
                selected_channel["id"] = None
                selected_languages["languages"] = []
                repeat_settings["times"] = 2
                repeat_settings["extra_minutes"] = 0
                performance_settings["max_concurrency"] = 50
                refresh_right_panel()
                if ui_refs["refresh_language_chips"]:
                    ui_refs["refresh_language_chips"]()
                if ui_refs["refresh_channel_display"]:
                    ui_refs["refresh_channel_display"]()
                save_right_panel_state()
                ui.notify("Đã xóa tất cả input và trạng thái", type="info")
            finally:
                suppress_autosave["value"] = False

        with ui.row().classes("w-full gap-2 mt-3"):
            ui.button("Cập nhật", on_click=handle_add_audio).classes("flex-1")
            ui.button("Xóa tất cả", on_click=clear_all_inputs).props("color=red").classes("flex-1")
