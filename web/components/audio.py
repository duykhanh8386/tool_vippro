# RECOVERED: partial depyo recovery; unresolved regions marked below
import asyncio, tempfile
from pathlib import Path
from typing import Awaitable, Callable, Iterable, TypeVar
from loguru import logger
from nicegui import context, ui
from src.audio_language import (
    call_audio_update_with_retry,
    invalid_language_codes,
    parse_language_codes,
)
from src.module.audio_module import update_audio_module
from src.state_manager import state_manager
from src.utils import get_channels_info, multiply_audio, normalize_path, validate_path_text
from web.theme import app_card, page_header, section_header


_T = TypeVar("_T")


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
        logger.warning("Audio UI action '{}' was skipped: {}", action, exc)
        return False


async def _run_sequentially_isolated(
    items: Iterable[_T],
    process_item: Callable[[_T], Awaitable[None]],
    on_error: Callable[[_T, Exception], None],
) -> list[tuple[_T, Exception]]:
    failures: list[tuple[_T, Exception]] = []
    for item in items:
        try:
            await process_item(item)
        except Exception as exc:
            failures.append((item, exc))
            on_error(item, exc)
    return failures


def _cleanup_temp_audio_file(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.exists():
            path.unlink()
    except Exception as exc:
        logger.warning("Failed to clean up temporary file {}: {}", path, exc)


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
                card_classes = "app-channel-card"
                if is_selected:
                    card_classes += " app-channel-card--selected"

                def create_channel_click_handler(channel_id):
                    def channel_click_handler():
                        handle_channel_click(channel_id)

                    return channel_click_handler

                with ui.card().classes(card_classes).on("click", create_channel_click_handler(cid)):
                    with ui.row().classes("items-center gap-2 w-full"):
                        if avatar:
                            ui.image(avatar).classes("w-6 h-6 rounded-full")
                        else:
                            ui.icon("o_account_circle").classes("text-xl text-gray-400")
                        ui.label(name).classes("text-xs font-medium text-gray-900 flex-1 truncate")
                        if is_selected:
                            ui.icon("check_circle").classes("text-green-600 text-sm")

    with app_card(classes="audio-add-section"):
        ui.label("Chọn kênh").classes("app-section-title")
        ui.label("Kênh sở hữu các video cần cập nhật audio.").classes("app-section-copy")
        channels_container = ui.row().classes("gap-2 flex-wrap")
        refresh_channel_display()
    return selected_channel, refresh_channel_display
def create_add_audio_page():
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

    selected_channel = {"id": None}; selected_languages = {"languages": []}; channels = get_channels_info(); video_ids_state = {"ids": []}; id_to_path = {}; video_processing_status = {}; video_processing_errors = {}; repeat_settings = {"times": 2, "extra_minutes": 0}; performance_settings = {"max_concurrency": 1}; right_panel_container = None; suppress_autosave = {"value": False}; ui_refs = {"ids_textarea": None, "language_input": None, "times_input": None, "minutes_input": None, "refresh_channel_display": None, "refresh_language_chips": None, "concurrency_input": None}
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
            # Audio languages for one video must be registered sequentially.
            performance_settings["max_concurrency"] = 1
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
            return parse_language_codes(text)
        def refresh_language_chips():
            language_chips_container.clear()
            with language_chips_container:
                for language in list(selected_languages["languages"]):
                    chip_classes = "px-2 py-1 rounded-full text-xs font-medium cursor-pointer transition-all duration-200 border bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                    def create_remove_handler(lang: str):
                        def _remove():
                            if lang in selected_languages["languages"]:
                                selected_languages["languages"].remove(lang)
                                language_input.value = " ".join(selected_languages["languages"])
                                refresh_language_chips()
                                save_right_panel_state()
                        return _remove
                    ui.label(language).classes(chip_classes).on("click", create_remove_handler(language))
            pass  # TODO: bytecode recovery incomplete
        def on_language_input_change(e=None):
            selected_languages["languages"] = parse_languages(language_input.value)

            refresh_language_chips(); save_right_panel_state()
        def reset_languages():
            selected_languages["languages"] = []

            language_input.value = ""; refresh_language_chips(); save_right_panel_state()

        with app_card(classes="audio-add-section"):
            with ui.row().classes("items-center justify-between mb-2"):
                ui.label("Nhập ngôn ngữ").classes("app-section-title")
                ui.button("Đặt lại", on_click=reset_languages).props("dense flat").classes("text-xs text-gray-500")
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
        with app_card(classes="audio-add-section"):
            ui.label("Cài đặt lặp lại âm thanh").classes("app-section-title mb-2")
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
                ui.label("Âm thanh sẽ được lặp lại n lần, với m phút bổ sung từ đầu âm thanh gốc").classes("app-section-copy flex-1")

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
            with ui.row().classes("audio-add-table-header w-full min-h-[42px] items-center font-semibold text-xs text-gray-500 bg-gray-50 border-b border-gray-200 px-2"):
                ui.label("Video ID").classes("w-2/12 p-2")
                ui.label("Audio Path").classes("w-5/12")
                ui.label("Ngôn ngữ").classes("w-2/12")
                ui.label("Trạng thái").classes("w-2/12")
                ui.label("").classes("w-1/12")
            for vid in video_ids_state["ids"]:
                current_path_value = id_to_path.get(vid, "")
                video_status = video_processing_status.get(vid, {})
                active_languages = list(selected_languages["languages"])
                active_language_set = set(active_languages)
                video_errors = {
                    language: message
                    for language, message in video_processing_errors.get(vid, {}).items()
                    if language in active_language_set or language == "xử lý"
                }
                active_statuses = [video_status.get(language) for language in active_languages]
                total_languages = len(active_languages)
                successful_count = active_statuses.count("successful")
                already_added_count = active_statuses.count("already_added")
                unsuccessful_count = active_statuses.count("unsuccessful")
                effective_success = successful_count + already_added_count
                if total_languages == 0:
                    overall_status = "pending"
                    status_color = "text-yellow-600"
                    status_icon = "schedule"
                elif effective_success == total_languages:
                    overall_status = "successful"
                    status_color = "text-green-600"
                    status_icon = "check_circle"
                elif unsuccessful_count > 0:
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

                with ui.row().classes("audio-add-table-row w-full min-h-[56px] items-center bg-white border-b border-gray-100 flex-nowrap"):
                    with ui.column().classes("w-2/12 p-2"):
                        ui.label(vid).classes("truncate px-2 py-1 font-medium text-gray-800")

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
                        ui.label(f"{effective_success}/{total_languages}").classes("text-sm font-medium text-gray-700")
                        if already_added_count > 0:
                            ui.label(f"{already_added_count} đã có").classes("text-xs text-orange-500")

                    with ui.column().classes("w-2/12 text-center p-2"):
                        status_tone = {
                            "pending": "warning",
                            "successful": "success",
                            "unsuccessful": "danger",
                        }[overall_status]
                        with ui.row().classes(f"app-status app-status--{status_tone} items-center justify-center gap-1 mx-auto"):
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
        languages_to_process = list(selected_languages["languages"])
        invalid_languages = invalid_language_codes(languages_to_process)
        if invalid_languages:
            ui.notify(
                f"Mã ngôn ngữ không hợp lệ: {', '.join(invalid_languages)}",
                type="negative",
            )
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
        save_right_panel_state()
        with ui.dialog() as progress_dialog:
            with ui.card().classes("app-card w-96"):
                ui.label("Đang thêm âm thanh...").classes("text-base font-semibold")
                current_video_label = ui.label("").classes("text-sm font-medium text-blue-600")
                status_label = ui.label("").classes("text-sm text-gray-600")
                remaining_label = ui.label("").classes("text-xs text-gray-500")
                concurrent_label = ui.label("").classes("text-xs text-gray-500 mt-1")
                progress_bar = ui.linear_progress(value=0)
        progress_dialog.props("persistent")
        best_effort_ui("open progress dialog", progress_dialog.open)
        total_videos = len(video_ids_state["ids"])
        total_tasks = total_videos * len(languages_to_process)
        completed_tasks = 0
        overall_errors = []

        async def run_upload(vid: str, lang: str, temp_audio_path: Path, file_bytes: bytes):
            try:
                if vid not in video_processing_status:
                    video_processing_status[vid] = {}
                video_processing_status[vid][lang] = "pending"
                video_processing_errors.setdefault(vid, {}).pop(lang, None)
                save_right_panel_state()
                best_effort_ui("render pending language", refresh_right_panel)

                def update_one_language():
                    return update_audio_module.add(
                        id_video=vid,
                        channel_id=selected_channel["id"],
                        file_name=str(temp_audio_path),
                        language=lang,
                        data=file_bytes,
                    )

                def log_retry(attempt, delay, exc):
                    logger.warning(
                        "Retry {}/3 for {}-{} in {}s: {}",
                        attempt,
                        vid,
                        lang,
                        delay,
                        exc,
                    )

                status_code = await call_audio_update_with_retry(
                    update_one_language,
                    on_retry=log_retry,
                )
                if status_code == 200:
                    video_processing_status[vid][lang] = "successful"
                else:
                    video_processing_status[vid][lang] = "already_added"
                save_right_panel_state()
            except Exception as exc:
                video_processing_status.setdefault(vid, {})[lang] = "unsuccessful"
                overall_errors.append(f"{vid}-{lang}: {exc}")
                video_processing_errors.setdefault(vid, {})[lang] = str(exc)
                save_right_panel_state()

        async def process_video(item: tuple[int, str]) -> None:
            nonlocal completed_tasks
            video_index, vid = item
            temp_audio_path: Path | None = None
            try:
                existing_status = video_processing_status.setdefault(vid, {})
                missing_languages = [
                    lang
                    for lang in languages_to_process
                    if existing_status.get(lang) not in ("successful", "already_added")
                ]
                skipped_count = len(languages_to_process) - len(missing_languages)
                if skipped_count:
                    completed_tasks += skipped_count
                    best_effort_ui(
                        "update skipped-language progress",
                        lambda: setattr(progress_bar, "value", completed_tasks / total_tasks),
                    )
                if not missing_languages:
                    best_effort_ui(
                        "render already-complete video",
                        lambda: (
                            current_video_label.set_text(
                                f"Video {video_index}/{total_videos}: {vid}"
                            ),
                            status_label.set_text(
                                "Đã đủ audio track — không cần tải lại"
                            ),
                            refresh_right_panel(),
                        ),
                    )
                    return

                file_path = Path((id_to_path.get(vid) or "").strip())
                best_effort_ui(
                    "render current audio video",
                    lambda: (
                        current_video_label.set_text(
                            f"Video {video_index}/{total_videos}: {vid}"
                        ),
                        remaining_label.set_text(
                            f"Còn lại: {total_videos - video_index} video"
                        ),
                        status_label.set_text("Đang lấy thông tin video..."),
                    ),
                )
                video_info = await asyncio.to_thread(
                    update_audio_module._get_video_info,
                    video_id=vid,
                    channel_id=selected_channel["id"],
                )
                video_duration_seconds = (
                    video_info.duration_ms / 1000.0
                    if video_info.duration_ms > 0
                    else None
                )
                best_effort_ui(
                    "render audio processing state",
                    lambda: status_label.set_text("Đang xử lý âm thanh..."),
                )
                with tempfile.NamedTemporaryFile(
                    suffix=file_path.suffix, delete=False
                ) as temp_file:
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
                best_effort_ui(
                    "render sequential upload state",
                    lambda: concurrent_label.set_text(
                        "Đang xử lý tuần tự để YouTube nhận đủ từng ngôn ngữ"
                    ),
                )
                for language_index, lang in enumerate(missing_languages, 1):
                    best_effort_ui(
                        "render language upload state",
                        lambda language_index=language_index, lang=lang: status_label.set_text(
                            f"Đang tải mã còn thiếu {language_index}/{len(missing_languages)}: {lang}"
                        ),
                    )
                    await run_upload(
                        vid=vid,
                        lang=lang,
                        temp_audio_path=temp_audio_path,
                        file_bytes=file_bytes,
                    )
                    completed_tasks += 1
                    save_right_panel_state()
                    best_effort_ui(
                        "render completed language",
                        lambda language_index=language_index: (
                            setattr(
                                progress_bar,
                                "value",
                                completed_tasks / total_tasks,
                            ),
                            refresh_right_panel(),
                            status_label.set_text(
                                f"Hoàn thành {language_index}/{len(missing_languages)} mã còn thiếu cho video {vid}"
                            ),
                        ),
                    )
                best_effort_ui(
                    "clear sequential upload state",
                    lambda: concurrent_label.set_text(""),
                )
            finally:
                _cleanup_temp_audio_file(temp_audio_path)

        def handle_video_error(item: tuple[int, str], vid_exc: Exception) -> None:
            nonlocal completed_tasks
            _, vid = item
            logger.error("Error processing video {}: {}", vid, vid_exc)
            overall_errors.append(f"{vid}: {vid_exc}")
            video_processing_errors.setdefault(vid, {})["xử lý"] = str(vid_exc)
            completed_tasks = min(
                total_tasks,
                completed_tasks + len(languages_to_process),
            )
            save_right_panel_state()
            best_effort_ui(
                "render failed audio video",
                lambda: (
                    setattr(progress_bar, "value", completed_tasks / total_tasks),
                    refresh_right_panel(),
                ),
            )

        try:
            await _run_sequentially_isolated(
                enumerate(list(video_ids_state["ids"]), 1),
                process_video,
                handle_video_error,
            )
        except Exception as main_exc:
            logger.error("Main processing error: {}", main_exc)
            overall_errors.append(f"Main process: {main_exc}")
        finally:
            save_right_panel_state()
            best_effort_ui("close progress dialog", progress_dialog.close)
            best_effort_ui("render final audio state", refresh_right_panel)
        total_videos = len(video_ids_state["ids"])
        successful_videos = 0
        for vid in video_ids_state["ids"]:
            video_status = video_processing_status.get(vid, {})
            total_languages = len(languages_to_process)
            successful_count = sum(
                1
                for language in languages_to_process
                if video_status.get(language) in ("successful", "already_added")
            )
            if total_languages > 0 and successful_count == total_languages:
                successful_videos += 1
        success_percentage = successful_videos / total_videos * 100 if total_videos > 0 else 0
        if overall_errors:
            best_effort_ui(
                "notify audio errors",
                lambda: ui.notify(
                    f"Cập nhật thất bại: {overall_errors[0]}. Xem chi tiết trong khung màu đỏ bên dưới.",
                    type="negative",
                ),
            )
        else:
            best_effort_ui(
                "notify audio completion",
                lambda: ui.notify(
                    f"Quá trình hoàn tất! {successful_videos}/{total_videos} video thành công. Kiểm tra trạng thái từng video bên dưới.",
                    type="positive" if success_percentage >= 50 else "warning",
                ),
            )

    page = ui.column().classes("app-page audio-add-page")
    with page:
        with page_header(
            "Thêm audio",
            "Thêm audio track theo ngôn ngữ vào video YouTube đã có trên kênh.",
            eyebrow="Tác vụ",
        ):
            pass
    with page:
        channel_state, refresh_channel_display = create_channel_selection(channels, on_channel_select)
        ui_refs["refresh_channel_display"] = refresh_channel_display
    with page:
        refresh_language_chips = create_language_input_and_chips()
    with page:
        create_repeat_settings()
    with page:
        main_card = ui.card().classes("app-card audio-add-main-card")
    with main_card:
        with section_header(
            "Video và file audio",
            "Nhập Video ID, sau đó cung cấp đường dẫn audio tương ứng trong bảng.",
        ):
            pass
        with ui.row().classes("w-full items-start gap-5 flex-wrap"):
            with ui.column().classes("w-72 shrink-0"):
                def handle_ids_textarea_change(e=None):
                    on_ids_input()
                ids_textarea = ui.textarea(on_change=handle_ids_textarea_change).props('outlined autogrow color=green placeholder="Nhập mỗi dòng một ID"').classes("w-full")
                ui_refs["ids_textarea"] = ids_textarea
            with ui.column().classes("flex-1 min-w-[560px]"):
                right_panel_container = ui.column().classes("audio-add-table w-full gap-1")
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
                    ui_refs["concurrency_input"].value = 1
                video_ids_state["ids"] = []
                id_to_path.clear()
                video_processing_status.clear()
                video_processing_errors.clear()
                selected_channel["id"] = None
                selected_languages["languages"] = []
                repeat_settings["times"] = 2
                repeat_settings["extra_minutes"] = 0
                performance_settings["max_concurrency"] = 1
                refresh_right_panel()
                if ui_refs["refresh_language_chips"]:
                    ui_refs["refresh_language_chips"]()
                if ui_refs["refresh_channel_display"]:
                    ui_refs["refresh_channel_display"]()
                ui.notify("Đã xóa tất cả input và trạng thái", type="info")
            finally:
                suppress_autosave["value"] = False
            save_right_panel_state()

        with ui.row().classes("w-full gap-2 mt-3"):
            ui.button("Cập nhật audio", icon="play_arrow", on_click=handle_add_audio).classes("app-button-primary flex-1")
            ui.button("Xóa dữ liệu", icon="delete_sweep", on_click=clear_all_inputs).classes("audio-add-destructive flex-1")
