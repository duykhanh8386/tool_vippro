# RECOVERED: partial depyo recovery; unresolved regions marked below
import asyncio, tempfile, threading
from pathlib import Path
from typing import Awaitable, Callable, Iterable, TypeVar
from loguru import logger
from nicegui import context, ui
from src.audio_batch_matcher import (
    AudioBatchMatchResult,
    build_audio_rename_plan,
    execute_audio_rename_plan,
    match_audio_files,
    match_audio_files_by_title,
    match_audio_files_sequentially,
)
from src.audio_language import (
    call_audio_update_with_retry,
    invalid_language_codes,
    parse_language_codes,
)
from src.module.audio_module import update_audio_module
from src.module.list_videos_module import list_videos_module
from src.module.model import Video
from src.state_manager import state_manager
from src.utils import get_channels_info, multiply_audio, normalize_path, validate_path_text
from web.components.common import select_directory
from web.theme import app_card, page_header, section_header


_T = TypeVar("_T")
_ADD_AUDIO_RUN_GUARD = threading.Lock()


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
    *,
    stop_on_error: Callable[[Exception], bool] | None = None,
) -> list[tuple[_T, Exception]]:
    failures: list[tuple[_T, Exception]] = []
    for item in items:
        try:
            await process_item(item)
        except Exception as exc:
            failures.append((item, exc))
            on_error(item, exc)
            if stop_on_error is not None and stop_on_error(exc):
                raise
    return failures


def _is_youtube_auth_error(exc: BaseException) -> bool:
    if getattr(exc, "status_code", None) == 401:
        return True
    message = str(exc).casefold()
    return "http 401" in message or "authentication credential" in message


def _fetch_all_channel_videos(channel_id: str):
    """Fetch every channel page and guard against a repeated continuation token."""
    videos = []
    seen_ids = set()
    seen_tokens = set()
    page_token = None
    while True:
        page, next_token = list_videos_module.list_all_videos(
            channel_id, limit=50, page_token=page_token
        )
        for video in page:
            if video.id and video.id not in seen_ids:
                seen_ids.add(video.id)
                videos.append(video)
        if not next_token:
            return videos
        if next_token in seen_tokens:
            raise RuntimeError("YouTube trả về mã phân trang bị lặp; đã dừng quét để tránh treo.")
        seen_tokens.add(next_token)
        page_token = next_token


def _select_videos_by_ids(videos: Iterable[Video], video_ids: Iterable[str]):
    """Select channel videos in the exact order of the active ID source."""
    by_id = {video.id: video for video in videos if video.id}
    selected = []
    missing = []
    for video_id in dict.fromkeys(video_id for video_id in video_ids if video_id):
        video = by_id.get(video_id)
        if video is None:
            missing.append(video_id)
        else:
            selected.append(video)
    return selected, missing


def _video_snapshot(video: Video) -> dict:
    return {
        "id": video.id,
        "channel_id": video.channel_id,
        "title": video.title,
        "duration_ms": video.duration_ms,
    }


def _video_from_snapshot(snapshot: dict) -> Video:
    return Video(
        id=str(snapshot.get("id") or ""),
        channel_id=str(snapshot.get("channel_id") or ""),
        title=str(snapshot.get("title") or ""),
        description=str(snapshot.get("description") or ""),
        thumbnail=str(snapshot.get("thumbnail") or ""),
        duration_ms=int(snapshot.get("duration_ms") or 0),
        privacy=str(snapshot.get("privacy") or ""),
        video_status=str(snapshot.get("video_status") or ""),
        copyright_check_status=str(snapshot.get("copyright_check_status") or ""),
    )


def _cleanup_temp_audio_file(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.exists():
            path.unlink()
    except Exception as exc:
        logger.warning("Failed to clean up temporary file {}: {}", path, exc)


def _restore_language_statuses(
    statuses: dict | None, *, reset_processing: bool
) -> dict:
    """Keep completed languages and retry only work interrupted by a process exit."""
    restored = {
        video_id: dict(language_statuses)
        for video_id, language_statuses in (statuses or {}).items()
        if isinstance(language_statuses, dict)
    }
    if reset_processing:
        for language_statuses in restored.values():
            for language, status in language_statuses.items():
                if status == "processing":
                    language_statuses[language] = "pending"
    return restored


def create_channel_selection(channels, on_channel_select):
    """Create a channel selection interface similar to studio page"""
    selected_channel = {"id": None}

    def handle_channel_click(channel_id):
        new_channel_id = None if selected_channel["id"] == channel_id else channel_id
        # Callers can decline a change while their background job owns the
        # persisted configuration.  In that case keep this visual selector in
        # sync with the real state as well.
        if on_channel_select(new_channel_id) is False:
            return
        selected_channel["id"] = new_channel_id
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

    selected_channel = {"id": None}
    selected_languages = {"languages": []}
    channels = get_channels_info()
    video_ids_state = {"ids": []}
    id_to_path = {}
    video_titles = {}
    auto_match_info = {}
    video_processing_status = {}
    video_processing_errors = {}
    repeat_settings = {"times": 2, "extra_minutes": 0}
    performance_settings = {"max_concurrency": 1}
    batch_scan_state = {
        "music_folder": "",
        "recursive": True,
        "duration_tolerance": 2.0,
        "result_channel": None,
        "summary": {},
        "issues": [],
        "extra_files": [],
    }
    video_source_state = {
        "mode": "manual",
        "manual_ids": [],
        "failed_channel": None,
        "failed_videos": [],
        "scan_total": 0,
        "scan_skipped": 0,
    }
    right_panel_container = None
    scan_preview_container = None
    video_source_status_container = None
    suppress_autosave = {"value": False}
    ui_refs = {
        "ids_textarea": None,
        "language_input": None,
        "times_input": None,
        "minutes_input": None,
        "refresh_channel_display": None,
        "refresh_language_chips": None,
        "concurrency_input": None,
        "music_folder_input": None,
        "recursive_switch": None,
        "scan_button": None,
        "title_button": None,
        "sequential_button": None,
        "rename_button": None,
        "duration_tolerance_input": None,
        "video_source_toggle": None,
        "failed_video_scan_button": None,
    }

    def configuration_change_blocked() -> bool:
        """Do not let a form edit overwrite a checkpoint owned by a live run."""
        if not _ADD_AUDIO_RUN_GUARD.locked():
            return False
        best_effort_ui(
            "notify locked add-audio configuration",
            lambda: ui.notify(
                "Thêm audio đang chạy; chưa thể thay đổi dữ liệu.", type="warning"
            ),
        )
        return True

    def save_right_panel_state() -> bool:
        """Save the current state of right_panel_container to file"""
        try:
            if suppress_autosave["value"]:
                return False
            state = {
                "video_ids": video_ids_state["ids"],
                "id_to_path": id_to_path,
                "video_titles": video_titles,
                "auto_match_info": auto_match_info,
                "video_processing_status": video_processing_status,
                "video_processing_errors": video_processing_errors,
                "selected_languages": selected_languages["languages"],
                "repeat_settings": repeat_settings,
                "selected_channel": selected_channel["id"],
                "performance_settings": performance_settings,
                "batch_scan_state": batch_scan_state,
                "video_source_state": video_source_state,
            }
            return state_manager.save_state("audio_add", state)
        except Exception as e:
            logger.error(f"Failed to save right panel state: {e}")
            return False
    def load_right_panel_state():
        """Load the saved state from file"""
        try:
            state = state_manager.load_state("audio_add")
            if not state:
                return
            needs_checkpoint_save = False
            if "video_ids" in state:
                video_ids_state["ids"] = state["video_ids"]
            if "id_to_path" in state:
                id_to_path.update(state["id_to_path"])
            if "video_titles" in state:
                video_titles.update(state["video_titles"])
            if "auto_match_info" in state:
                auto_match_info.update(state["auto_match_info"])
            if "video_processing_status" in state:
                restored_statuses = _restore_language_statuses(
                    state["video_processing_status"],
                    reset_processing=not _ADD_AUDIO_RUN_GUARD.locked(),
                )
                video_processing_status.clear()
                video_processing_status.update(restored_statuses)
                if restored_statuses != state["video_processing_status"]:
                    needs_checkpoint_save = True
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
            if "batch_scan_state" in state:
                batch_scan_state.update(state["batch_scan_state"])
            if "video_source_state" in state:
                saved_source = state["video_source_state"] or {}
                video_source_state.update(saved_source)
            else:
                video_source_state["manual_ids"] = list(video_ids_state["ids"])
            if video_source_state.get("mode") not in {"manual", "failed"}:
                video_source_state["mode"] = "manual"
            if needs_checkpoint_save:
                save_right_panel_state()
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
                    if ui_refs["music_folder_input"]:
                        ui_refs["music_folder_input"].value = batch_scan_state["music_folder"]
                    if ui_refs["recursive_switch"]:
                        ui_refs["recursive_switch"].value = batch_scan_state["recursive"]
                    if ui_refs["duration_tolerance_input"]:
                        ui_refs["duration_tolerance_input"].value = batch_scan_state[
                            "duration_tolerance"
                        ]
                    refresh_video_source_controls()
                    refresh_right_panel()
                    refresh_scan_preview()
                    refresh_rename_button()
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
        if configuration_change_blocked():
            return False
        selected_channel["id"] = channel_id

        if (
            video_source_state.get("mode") == "failed"
            and video_source_state.get("failed_channel") != channel_id
        ):
            video_source_state["failed_channel"] = None
            video_source_state["failed_videos"] = []
            video_source_state["scan_total"] = 0
            video_source_state["scan_skipped"] = 0
            replace_active_video_list([])

        refresh_video_source_controls()
        save_right_panel_state()
        return True
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
                            if configuration_change_blocked():
                                return
                            if lang in selected_languages["languages"]:
                                selected_languages["languages"].remove(lang)
                                language_input.value = " ".join(selected_languages["languages"])
                                refresh_language_chips()
                                save_right_panel_state()
                        return _remove
                    ui.label(language).classes(chip_classes).on("click", create_remove_handler(language))
            pass  # TODO: bytecode recovery incomplete
        def on_language_input_change(e=None):
            if configuration_change_blocked():
                language_input.value = " ".join(selected_languages["languages"])
                return
            selected_languages["languages"] = parse_languages(language_input.value)

            refresh_language_chips(); save_right_panel_state()
        def reset_languages():
            if configuration_change_blocked():
                return
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
                    if configuration_change_blocked():
                        times_input.value = repeat_settings["times"]
                        return
                    value = int(e.args) if e.args and int(e.args) >= 1 else 1
                    repeat_settings["times"] = value

                    times_input.value = value; save_right_panel_state()
                times_input.on("change", update_times)
                minutes_input = ui.number(label="Phút bổ sung (m)", value=repeat_settings["extra_minutes"], min=0, max=60, step=1).props("outlined").classes("w-32")
                ui_refs["minutes_input"] = minutes_input
                def update_minutes(e):
                    if configuration_change_blocked():
                        minutes_input.value = repeat_settings["extra_minutes"]
                        return
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

    def replace_active_video_list(
        video_ids: Iterable[str], *, videos: Iterable[Video] = ()
    ) -> None:
        """Replace the active source and discard matches from the previous source."""
        new_ids = list(dict.fromkeys(video_id for video_id in video_ids if video_id))
        snapshots_by_id = {video.id: video for video in videos if video.id}
        video_ids_state["ids"] = new_ids
        id_to_path.clear()
        video_titles.clear()
        video_titles.update(
            {
                video_id: snapshots_by_id[video_id].title
                for video_id in new_ids
                if video_id in snapshots_by_id
            }
        )
        auto_match_info.clear()
        video_processing_status.clear()
        video_processing_errors.clear()
        batch_scan_state["result_channel"] = selected_channel["id"]
        batch_scan_state["summary"] = {}
        batch_scan_state["issues"] = []
        batch_scan_state["extra_files"] = []
        if ui_refs["ids_textarea"]:
            ui_refs["ids_textarea"].value = "\n".join(new_ids)
        refresh_right_panel()
        refresh_scan_preview()
        refresh_rename_button()

    def refresh_video_source_controls() -> None:
        mode = video_source_state.get("mode", "manual")
        toggle = ui_refs.get("video_source_toggle")
        if toggle and toggle.value != mode:
            toggle.value = mode

        scan_button = ui_refs.get("failed_video_scan_button")
        if scan_button:
            if mode == "failed" and not scan_runtime["running"]:
                scan_button.props(remove="disable")
            else:
                scan_button.props("disable")

        match_ready = bool(video_ids_state["ids"]) and bool(selected_channel["id"]) and (
            mode == "manual"
            or video_source_state.get("failed_channel") == selected_channel["id"]
        )
        for key in ("scan_button", "title_button", "sequential_button"):
            match_button = ui_refs.get(key)
            if not match_button:
                continue
            if match_ready and not scan_runtime["running"]:
                match_button.props(remove="disable")
            else:
                match_button.props("disable")

        textarea = ui_refs.get("ids_textarea")
        if textarea:
            if mode == "failed":
                textarea.props("readonly")
            else:
                textarea.props(remove="readonly")

        if not video_source_status_container:
            return
        video_source_status_container.clear()
        with video_source_status_container:
            if mode == "manual":
                ui.label(
                    f"Đang dùng {len(video_ids_state['ids'])} Video ID nhập thủ công."
                ).classes("text-xs text-gray-600")
                return
            failed_channel = video_source_state.get("failed_channel")
            if not failed_channel:
                ui.label(
                    "Chưa quét. Hãy chọn kênh rồi bấm Quét ID lỗi audio."
                ).classes("text-xs text-orange-600")
                return
            if failed_channel != selected_channel["id"]:
                ui.label(
                    "Kết quả quét thuộc kênh khác. Hãy quét lại kênh đang chọn."
                ).classes("text-xs text-orange-600")
                return
            ui.label(
                f"Đã tìm thấy {len(video_source_state.get('failed_videos') or [])}/"
                f"{video_source_state.get('scan_total', 0)} video có audio xử lý lỗi."
            ).classes("text-xs font-medium text-emerald-700")
            if video_source_state.get("scan_skipped", 0):
                ui.label(
                    f"YouTube không cho đọc trạng thái của "
                    f"{video_source_state['scan_skipped']} video."
                ).classes("text-xs text-orange-600")

    def refresh_scan_preview():
        if not scan_preview_container:
            return
        scan_preview_container.clear()
        summary = batch_scan_state.get("summary") or {}
        issues = batch_scan_state.get("issues") or []
        extra_files = batch_scan_state.get("extra_files") or []
        if not summary:
            return
        with scan_preview_container:
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.icon("task_alt").classes("text-emerald-600")
                ui.label(
                    f"Đã quét {summary.get('videos', 0)} video và "
                    f"{summary.get('audio_files', 0)} file · "
                    f"ghép được {summary.get('matched', 0)}"
                ).classes("text-sm font-semibold text-gray-700")
                ui.label(
                    f"Thiếu {summary.get('unmatched', 0)} · "
                    f"trùng {summary.get('ambiguous', 0)} · "
                    f"file dư {summary.get('extra_files', 0)}"
                ).classes("text-xs text-gray-500")
                mode_label = {
                    "duration": "Chế độ: khớp thời lượng",
                    "title": "Chế độ: khớp tiêu đề",
                    "sequential": "Chế độ: ghép lần lượt",
                }.get(summary.get("mode"))
                if mode_label:
                    ui.label(mode_label).classes(
                        "text-xs font-medium text-blue-600"
                    )
            if issues:
                total_issues = summary.get("unmatched", 0) + summary.get("ambiguous", 0)
                with ui.expansion(
                    f"Xem {total_issues} video chưa thể ghép tự động",
                    icon="warning_amber",
                ).classes("w-full text-sm"):
                    for issue in issues:
                        title = issue.get("title") or "Không có tiêu đề"
                        ui.label(
                            f"{issue.get('video_id', '')} · {title}: {issue.get('detail', '')}"
                        ).classes("text-xs text-gray-600 break-words")
                    if total_issues > len(issues):
                        ui.label(
                            f"Còn {total_issues - len(issues)} video khác; hãy đổi tên file theo Video ID rồi quét lại."
                        ).classes("text-xs text-orange-600")
            if extra_files:
                total_extra = summary.get("extra_files", len(extra_files))
                with ui.expansion(
                    f"Xem {total_extra} file chưa được dùng",
                    icon="audio_file",
                ).classes("w-full text-sm"):
                    for path in extra_files:
                        ui.label(path).classes("text-xs text-gray-600 break-all")
                    if total_extra > len(extra_files):
                        ui.label(f"Còn {total_extra - len(extra_files)} file khác.").classes(
                            "text-xs text-orange-600"
                        )

    def refresh_rename_button():
        button = ui_refs.get("rename_button")
        if not button:
            return
        has_renameable_matches = any(
            (auto_match_info.get(video_id) or {}).get("status")
            in {"duration", "title", "sequential"}
            and id_to_path.get(video_id)
            for video_id in video_ids_state["ids"]
        )
        if has_renameable_matches:
            button.props(remove="disable")
        else:
            button.props("disable")

    def apply_batch_match(result: AudioBatchMatchResult, *, mode: str) -> int:
        matched = list(result.matched)
        issues = [
            {
                "video_id": item.video_id,
                "title": item.title,
                "status": item.status,
                "detail": item.detail,
                "candidates": list(item.candidates),
            }
            for item in result.matches
            if not item.path
        ]
        batch_scan_state["summary"] = {
            "videos": len(result.matches),
            "audio_files": result.audio_file_count,
            "matched": len(matched),
            "unmatched": len(result.unmatched),
            "ambiguous": len(result.ambiguous),
            "extra_files": len(result.extra_files),
            "mode": mode,
        }
        # Keep the checkpoint compact for very large channels while retaining
        # totals in the summary above.
        batch_scan_state["issues"] = issues[:200]
        batch_scan_state["extra_files"] = list(result.extra_files[:200])

        old_paths = dict(id_to_path)
        new_ids = [item.video_id for item in result.matches]
        new_paths = {item.video_id: item.path or "" for item in result.matches}
        new_titles = {item.video_id: item.title for item in result.matches}
        new_match_info = {
            item.video_id: {"status": item.status, "detail": item.detail}
            for item in result.matches
            if item.path
        }

        for video_id in set(video_ids_state["ids"]) | set(new_ids):
            if video_id not in new_paths or old_paths.get(video_id) != new_paths.get(video_id):
                video_processing_status.pop(video_id, None)
                video_processing_errors.pop(video_id, None)

        video_ids_state["ids"] = new_ids
        batch_scan_state["result_channel"] = selected_channel["id"]
        id_to_path.clear()
        id_to_path.update(new_paths)
        video_titles.clear()
        video_titles.update(new_titles)
        auto_match_info.clear()
        auto_match_info.update(new_match_info)
        if ui_refs["ids_textarea"]:
            ui_refs["ids_textarea"].value = "\n".join(new_ids)
        refresh_right_panel()
        refresh_scan_preview()
        refresh_rename_button()
        save_right_panel_state()
        return len(matched)

    scan_runtime = {"running": False}

    def set_scan_controls_busy(busy: bool, *, loading_key: str | None = None) -> None:
        for key in (
            "failed_video_scan_button",
            "scan_button",
            "title_button",
            "sequential_button",
        ):
            button = ui_refs.get(key)
            if not button:
                continue
            if busy:
                button.props("disable")
            else:
                button.props(remove="disable")
            if key == loading_key:
                if busy:
                    button.props("loading")
                else:
                    button.props(remove="loading")
        if not busy:
            refresh_video_source_controls()

    def source_videos_for_matching(channel_id: str) -> list[Video]:
        active_ids = list(video_ids_state["ids"])
        if not active_ids:
            raise ValueError("Danh sách Video ID đang trống.")

        if video_source_state.get("mode") == "failed":
            if video_source_state.get("failed_channel") != channel_id:
                raise ValueError("Hãy quét lại danh sách video lỗi audio cho kênh đang chọn.")
            cached = [
                _video_from_snapshot(item)
                for item in video_source_state.get("failed_videos") or []
                if isinstance(item, dict)
            ]
            selected, missing = _select_videos_by_ids(cached, active_ids)
        else:
            channel_videos = _fetch_all_channel_videos(channel_id)
            selected, missing = _select_videos_by_ids(channel_videos, active_ids)

        if missing:
            preview = ", ".join(missing[:5])
            suffix = f" và {len(missing) - 5} ID khác" if len(missing) > 5 else ""
            raise ValueError(
                f"Không tìm thấy thông tin video cho ID: {preview}{suffix}. Hãy quét lại kênh."
            )
        return selected

    async def handle_failed_video_scan():
        if configuration_change_blocked():
            return
        if scan_runtime["running"]:
            ui.notify("Một tác vụ quét đang chạy.", type="warning")
            return
        if video_source_state.get("mode") != "failed":
            ui.notify("Hãy chọn chế độ Quét ID lỗi audio trước.", type="warning")
            return
        if not selected_channel["id"]:
            ui.notify("Hãy chọn kênh trước khi quét", type="warning")
            return

        scan_runtime["running"] = True
        set_scan_controls_busy(True, loading_key="failed_video_scan_button")
        try:
            channel_id = selected_channel["id"]
            ui.notify("Đang đọc video và trạng thái audio trên kênh...", type="info")
            videos = await asyncio.to_thread(_fetch_all_channel_videos, channel_id)
            unreadable_ids: list[str] = []
            failed_ids = await asyncio.to_thread(
                update_audio_module.get_failed_audio_video_ids,
                [video.id for video in videos],
                channel_id,
                unreadable_ids,
            )
            failed_videos = [video for video in videos if video.id in failed_ids]

            video_source_state["failed_channel"] = channel_id
            video_source_state["failed_videos"] = [
                _video_snapshot(video) for video in failed_videos
            ]
            video_source_state["scan_total"] = len(videos)
            video_source_state["scan_skipped"] = len(unreadable_ids)
            replace_active_video_list(
                [video.id for video in failed_videos], videos=failed_videos
            )
            refresh_video_source_controls()
            save_right_panel_state()
            if failed_videos:
                ui.notify(
                    f"Đã lấy {len(failed_videos)}/{len(videos)} Video ID có audio xử lý lỗi. "
                    "Bây giờ hãy chọn cách ghép.",
                    type="positive",
                )
            else:
                ui.notify(
                    f"Đã quét {len(videos)} video, không thấy audio nào ở trạng thái xử lý lỗi.",
                    type="warning",
                )
        except Exception as exc:
            logger.exception("Failed to scan videos with audio processing errors")
            if _is_youtube_auth_error(exc):
                message = "Phiên đăng nhập YouTube đã hết hạn. Hãy đăng nhập và quét lại kênh."
            else:
                message = f"Không thể quét ID lỗi audio: {exc}"
            ui.notify(message, type="negative")
        finally:
            scan_runtime["running"] = False
            set_scan_controls_busy(False, loading_key="failed_video_scan_button")

    async def run_folder_scan(*, mode: str):
        if configuration_change_blocked():
            return
        if scan_runtime["running"]:
            ui.notify("Đang quét video và thư mục nhạc.", type="warning")
            return
        if not selected_channel["id"]:
            ui.notify("Hãy chọn kênh trước khi quét", type="warning")
            return
        folder_text = normalize_path(batch_scan_state.get("music_folder") or "")
        folder = Path(folder_text)
        if not folder_text or not folder.is_dir():
            ui.notify("Hãy chọn một thư mục nhạc hợp lệ", type="warning")
            return

        scan_runtime["running"] = True
        active_button_key = {
            "duration": "scan_button",
            "title": "title_button",
            "sequential": "sequential_button",
        }[mode]
        set_scan_controls_busy(True, loading_key=active_button_key)
        try:
            ui.notify("Đang đọc thông tin các Video ID đã chọn...", type="info")
            videos = await asyncio.to_thread(
                source_videos_for_matching, selected_channel["id"]
            )
            matcher = {
                "duration": match_audio_files,
                "title": match_audio_files_by_title,
                "sequential": match_audio_files_sequentially,
            }[mode]
            matcher_kwargs = {
                "recursive": bool(batch_scan_state.get("recursive", True))
            }
            if mode == "duration":
                matcher_kwargs["tolerance_seconds"] = float(
                    batch_scan_state.get("duration_tolerance", 2.0)
                )
            result = await asyncio.to_thread(
                matcher,
                videos,
                folder,
                **matcher_kwargs,
            )
            matched_count = apply_batch_match(result, mode=mode)
            if matched_count:
                action = {
                    "duration": "ghép theo thời lượng",
                    "title": "ghép theo tiêu đề",
                    "sequential": "ghép lần lượt",
                }[mode]
                ui.notify(
                    f"Đã {action} {matched_count}/{len(videos)} video. Hãy kiểm tra bảng rồi cập nhật audio.",
                    type="positive",
                )
            else:
                message = {
                    "duration": "Không tìm thấy file có thời lượng phù hợp.",
                    "title": "Không tìm thấy file chứa tiêu đề YouTube trong tên file.",
                    "sequential": "Thư mục không có file âm thanh để ghép lần lượt.",
                }[mode]
                ui.notify(message, type="warning")
        except Exception as exc:
            logger.exception("Automatic audio scan failed")
            if _is_youtube_auth_error(exc):
                message = "Phiên đăng nhập YouTube đã hết hạn. Hãy đăng nhập và quét lại kênh."
            else:
                message = f"Không thể quét tự động: {exc}"
            ui.notify(message, type="negative")
        finally:
            scan_runtime["running"] = False
            set_scan_controls_busy(False, loading_key=active_button_key)

    async def handle_auto_scan():
        await run_folder_scan(mode="duration")

    async def handle_title_scan():
        await run_folder_scan(mode="title")

    async def handle_sequential_scan():
        await run_folder_scan(mode="sequential")

    def open_rename_dialog():
        if configuration_change_blocked():
            return
        if scan_runtime["running"]:
            ui.notify("Hãy chờ quét video và thư mục nhạc hoàn tất.", type="warning")
            return
        assignments = [
            (video_id, id_to_path[video_id])
            for video_id in video_ids_state["ids"]
            if id_to_path.get(video_id)
            and (auto_match_info.get(video_id) or {}).get("status")
            in {"duration", "title", "sequential"}
        ]
        if not assignments:
            ui.notify("Chưa có kết quả ghép tự động để đổi tên.", type="warning")
            return
        try:
            plan = build_audio_rename_plan(assignments)
        except Exception as exc:
            ui.notify(f"Không thể tạo kế hoạch đổi tên: {exc}", type="negative")
            return
        if not plan:
            ui.notify("Các file đã mang đúng Video ID.", type="info")
            return

        with ui.dialog() as rename_dialog, ui.card().classes("app-card w-[680px] max-w-[95vw]"):
            ui.label("Đổi tên file nhạc theo Video ID?").classes("text-lg font-semibold")
            ui.label(
                f"{len(plan)} file sẽ được đổi tên thật trên ổ đĩa. Định dạng file được giữ nguyên."
            ).classes("text-sm text-gray-600")
            with ui.scroll_area().classes("w-full h-64 border rounded p-2"):
                for item in plan[:100]:
                    ui.label(f"{item.source.name}  →  {item.target.name}").classes(
                        "text-xs text-gray-700 break-all"
                    )
                if len(plan) > 100:
                    ui.label(f"Còn {len(plan) - 100} file khác.").classes(
                        "text-xs text-orange-600"
                    )

            def confirm_rename():
                try:
                    changed_paths = execute_audio_rename_plan(plan)
                except Exception as exc:
                    logger.exception("Could not rename sequential audio files")
                    ui.notify(f"Đổi tên thất bại: {exc}", type="negative")
                    return
                for video_id, new_path in changed_paths.items():
                    id_to_path[video_id] = new_path
                    auto_match_info[video_id] = {
                        "status": "video_id",
                        "detail": "Đã đổi tên theo Video ID",
                    }
                batch_scan_state["summary"]["mode"] = "renamed"
                refresh_right_panel()
                refresh_rename_button()
                save_right_panel_state()
                rename_dialog.close()
                ui.notify(f"Đã đổi tên {len(changed_paths)} file.", type="positive")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Hủy", on_click=rename_dialog.close).props("flat")
                ui.button(
                    "Đổi tên file",
                    icon="drive_file_rename_outline",
                    on_click=confirm_rename,
                ).classes("app-button-primary")
        rename_dialog.open()

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
                        if video_titles.get(vid):
                            ui.label(video_titles[vid]).classes(
                                "truncate px-2 text-[11px] text-gray-500"
                            ).tooltip(video_titles[vid])
                        match = auto_match_info.get(vid) or {}
                        if match:
                            match_label = {
                                "mapping": "mapping.csv",
                                "video_id": "Khớp ID",
                                "duration": "Khớp thời lượng",
                                "title": "Khớp tiêu đề",
                                "sequential": "Ghép lần lượt",
                                "manual": "Thủ công",
                            }.get(match.get("status"), match.get("detail", ""))
                            ui.label(match_label).classes(
                                "px-2 text-[10px] font-medium text-emerald-600"
                            )

                    def make_path_on_change(video_id: str, input_ref):
                        def _on_change(e=None):
                            if configuration_change_blocked():
                                input_ref.value = id_to_path.get(video_id, "")
                                return
                            new_path = (input_ref.value or "").strip()
                            if id_to_path.get(video_id, "") != new_path:
                                video_processing_status.pop(video_id, None)
                                video_processing_errors.pop(video_id, None)
                            id_to_path[video_id] = new_path
                            auto_match_info[video_id] = {
                                "status": "manual",
                                "detail": "Đã sửa đường dẫn thủ công",
                            }
                            refresh_right_panel()
                            refresh_rename_button()
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
                            if configuration_change_blocked():
                                return
                            if video_id in video_ids_state["ids"]:
                                video_ids_state["ids"].remove(video_id)
                            id_to_path.pop(video_id, None)
                            video_titles.pop(video_id, None)
                            auto_match_info.pop(video_id, None)
                            video_processing_status.pop(video_id, None)
                            video_processing_errors.pop(video_id, None)
                            if video_source_state.get("mode") == "manual":
                                video_source_state["manual_ids"] = list(
                                    video_ids_state["ids"]
                                )
                            else:
                                active_ids = set(video_ids_state["ids"])
                                video_source_state["failed_videos"] = [
                                    item
                                    for item in video_source_state.get("failed_videos") or []
                                    if isinstance(item, dict)
                                    and item.get("id") in active_ids
                                ]
                            refresh_right_panel()
                            refresh_rename_button()
                            refresh_video_source_controls()
                            if video_ids_state["ids"]:
                                ids_textarea.value = "\n".join(video_ids_state["ids"])
                            else:
                                ids_textarea.value = ""
                            save_right_panel_state()

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
        if _ADD_AUDIO_RUN_GUARD.locked():
            ui.notify("Thêm audio đang chạy ở một trang khác.", type="warning")
            return None
        if not selected_channel["id"]:
            ui.notify("Hãy chọn kênh", type="warning")
            return None
        data_channel = batch_scan_state.get("result_channel")
        if data_channel and data_channel != selected_channel["id"]:
            ui.notify(
                "Danh sách video thuộc kênh đã chọn trước đó. Hãy quét lại hoặc nhập lại Video ID cho kênh hiện tại.",
                type="warning",
            )
            return None
        if len(selected_languages["languages"]) == 0:
            ui.notify("Hãy chọn ít nhất một ngôn ngữ", type="warning")
            return None
        if len(video_ids_state["ids"]) == 0:
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
        if not _ADD_AUDIO_RUN_GUARD.acquire(blocking=False):
            ui.notify("Thêm audio đang chạy ở một trang khác.", type="warning")
            return None
        channel_id = selected_channel["id"]
        repeat_times = repeat_settings["times"]
        extra_minutes = repeat_settings["extra_minutes"]
        video_processing_errors.clear()
        if save_right_panel_state() is False:
            _ADD_AUDIO_RUN_GUARD.release()
            ui.notify("Không thể lưu phiên xử lý. Vui lòng thử lại.", type="negative")
            return None
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
                video_processing_status[vid][lang] = "processing"
                video_processing_errors.setdefault(vid, {}).pop(lang, None)
                if save_right_panel_state() is False:
                    raise RuntimeError("Không thể lưu checkpoint trước khi thêm audio")
                best_effort_ui("render pending language", refresh_right_panel)

                def update_one_language():
                    return update_audio_module.add(
                        id_video=vid,
                        channel_id=channel_id,
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
                if save_right_panel_state() is False:
                    raise RuntimeError("Không thể lưu checkpoint sau khi thêm audio")
            except Exception as exc:
                video_processing_status.setdefault(vid, {})[lang] = "unsuccessful"
                overall_errors.append(f"{vid}-{lang}: {exc}")
                video_processing_errors.setdefault(vid, {})[lang] = str(exc)
                save_right_panel_state()
                if _is_youtube_auth_error(exc):
                    raise

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

                try:
                    existing_remote_languages = await asyncio.to_thread(
                        update_audio_module.get_existing_audio_languages,
                        vid,
                        channel_id,
                    )
                except Exception as exc:
                    if _is_youtube_auth_error(exc):
                        raise
                    logger.warning(
                        "Could not inspect existing audio tracks for {}: {}", vid, exc
                    )
                else:
                    already_on_youtube = [
                        lang
                        for lang in missing_languages
                        if lang.casefold() in existing_remote_languages
                    ]
                    for lang in already_on_youtube:
                        existing_status[lang] = "already_added"
                        video_processing_errors.setdefault(vid, {}).pop(lang, None)
                    if already_on_youtube:
                        completed_tasks += len(already_on_youtube)
                        save_right_panel_state()
                        best_effort_ui(
                            "render remote audio tracks",
                            lambda: (
                                setattr(
                                    progress_bar,
                                    "value",
                                    completed_tasks / total_tasks,
                                ),
                                refresh_right_panel(),
                            ),
                        )
                    missing_languages = [
                        lang for lang in missing_languages if lang not in already_on_youtube
                    ]
                    if not missing_languages:
                        best_effort_ui(
                            "render remotely complete video",
                            lambda: status_label.set_text(
                                "YouTube đã có đủ audio track — đã bỏ qua"
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
                    channel_id=channel_id,
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
                # Normalize every supported input container/codec to one upload
                # format. This also makes M4A, FLAC, OGG, WMA, etc. reliable
                # when stream copy into their original container is impossible.
                with tempfile.NamedTemporaryFile(
                    suffix=".mp3", delete=False
                ) as temp_file:
                    temp_audio_path = Path(temp_file.name)
                await asyncio.to_thread(
                    multiply_audio,
                    input_file=normalize_path(str(file_path)),
                    output_file=str(temp_audio_path),
                    times=repeat_times,
                    extra_minutes=extra_minutes,
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
                stop_on_error=_is_youtube_auth_error,
            )
        except Exception as main_exc:
            logger.error("Main processing error: {}", main_exc)
            overall_errors.append(f"Main process: {main_exc}")
        finally:
            save_right_panel_state()
            best_effort_ui("close progress dialog", progress_dialog.close)
            best_effort_ui("render final audio state", refresh_right_panel)
            _ADD_AUDIO_RUN_GUARD.release()
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
        selected_channel = channel_state
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
            "Quét tự động theo kênh và thư mục nhạc, hoặc nhập Video ID thủ công. "
            "Hỗ trợ MP3, M4A, WAV, AAC, FLAC, OGG, OPUS, WMA và các định dạng phổ biến khác.",
        ):
            pass

        def on_music_folder_change(e=None):
            if configuration_change_blocked():
                if ui_refs["music_folder_input"]:
                    ui_refs["music_folder_input"].value = batch_scan_state["music_folder"]
                return
            value = (
                ui_refs["music_folder_input"].value
                if ui_refs["music_folder_input"]
                else ""
            )
            batch_scan_state["music_folder"] = normalize_path(value or "")
            save_right_panel_state()

        def pick_music_folder():
            if configuration_change_blocked():
                return
            selected = select_directory(
                initial_dir=batch_scan_state["music_folder"] or None,
                title="Chọn thư mục nhạc để ghép theo Video ID",
            )
            if selected:
                batch_scan_state["music_folder"] = normalize_path(selected)
                if ui_refs["music_folder_input"]:
                    ui_refs["music_folder_input"].value = batch_scan_state["music_folder"]
                save_right_panel_state()

        def on_recursive_change(e):
            if configuration_change_blocked():
                if hasattr(e, "sender"):
                    e.sender.value = batch_scan_state["recursive"]
                return
            batch_scan_state["recursive"] = bool(e.value)
            save_right_panel_state()

        def on_duration_tolerance_change(e=None):
            if configuration_change_blocked():
                if ui_refs["duration_tolerance_input"]:
                    ui_refs["duration_tolerance_input"].value = batch_scan_state[
                        "duration_tolerance"
                    ]
                return
            input_ref = ui_refs["duration_tolerance_input"]
            try:
                value = float(input_ref.value if input_ref else 2.0)
            except (TypeError, ValueError):
                value = 2.0
            value = min(10.0, max(0.0, value))
            batch_scan_state["duration_tolerance"] = value
            if input_ref:
                input_ref.value = value
            save_right_panel_state()

        def on_video_source_change(e):
            requested_mode = str(e.value or "manual")
            current_mode = video_source_state.get("mode", "manual")
            if requested_mode not in {"manual", "failed"}:
                requested_mode = "manual"
            if configuration_change_blocked():
                if ui_refs["video_source_toggle"]:
                    ui_refs["video_source_toggle"].value = current_mode
                return
            if scan_runtime["running"]:
                ui.notify("Hãy chờ tác vụ quét hoàn tất.", type="warning")
                if ui_refs["video_source_toggle"]:
                    ui_refs["video_source_toggle"].value = current_mode
                return
            if requested_mode == current_mode:
                return

            if current_mode == "manual":
                video_source_state["manual_ids"] = list(video_ids_state["ids"])
            video_source_state["mode"] = requested_mode
            if requested_mode == "manual":
                replace_active_video_list(video_source_state.get("manual_ids") or [])
            elif video_source_state.get("failed_channel") == selected_channel["id"]:
                cached_videos = [
                    _video_from_snapshot(item)
                    for item in video_source_state.get("failed_videos") or []
                    if isinstance(item, dict)
                ]
                replace_active_video_list(
                    [video.id for video in cached_videos], videos=cached_videos
                )
            else:
                replace_active_video_list([])
            refresh_video_source_controls()
            save_right_panel_state()

        with ui.card().classes("w-full bg-emerald-50 border border-emerald-200 p-3 mb-4"):
            with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
                with ui.column().classes("gap-1"):
                    ui.label("Nguồn Video ID").classes("text-sm font-semibold text-gray-700")
                    source_toggle = ui.toggle(
                        {
                            "manual": "Nhập ID thủ công",
                            "failed": "Quét ID lỗi audio",
                        },
                        value=video_source_state["mode"],
                        on_change=on_video_source_change,
                    ).props("no-caps")
                    ui_refs["video_source_toggle"] = source_toggle
                failed_video_scan_button = ui.button(
                    "Quét ID lỗi audio",
                    icon="report_problem",
                    on_click=handle_failed_video_scan,
                ).props("outline disable")
                ui_refs["failed_video_scan_button"] = failed_video_scan_button
            video_source_status_container = ui.column().classes("w-full gap-0")
            refresh_video_source_controls()
            ui.separator().classes("my-1")
            with ui.row().classes("w-full items-end gap-2 flex-wrap"):
                music_folder_input = ui.input(
                    "Thư mục nhạc",
                    value=batch_scan_state["music_folder"],
                ).props('outlined clearable placeholder="Chọn thư mục chứa file âm thanh"').classes("flex-1 min-w-[320px]")
                music_folder_input.on("change", on_music_folder_change)
                ui_refs["music_folder_input"] = music_folder_input
                ui.button(
                    "Chọn thư mục",
                    icon="folder_open",
                    on_click=pick_music_folder,
                ).props("outline")
            with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap"):
                with ui.row().classes("items-center gap-3"):
                    recursive_switch = ui.switch(
                        "Quét cả thư mục con",
                        value=batch_scan_state["recursive"],
                        on_change=on_recursive_change,
                    ).props("dense")
                    ui_refs["recursive_switch"] = recursive_switch
                    duration_tolerance_input = ui.number(
                        "Lệch tối đa (giây)",
                        value=batch_scan_state["duration_tolerance"],
                        min=0,
                        max=10,
                        step=0.5,
                        on_change=on_duration_tolerance_change,
                    ).props("outlined dense").classes("w-36")
                    ui_refs["duration_tolerance_input"] = duration_tolerance_input
                with ui.row().classes("items-center gap-2 flex-wrap"):
                    scan_button = ui.button(
                        "Ghép theo thời lượng",
                        icon="timer",
                        on_click=handle_auto_scan,
                    ).props("outline")
                    ui_refs["scan_button"] = scan_button
                    title_button = ui.button(
                        "Ghép theo tiêu đề",
                        icon="title",
                        on_click=handle_title_scan,
                    ).props("outline")
                    ui_refs["title_button"] = title_button
                    sequential_button = ui.button(
                        "Ghép lần lượt",
                        icon="format_list_numbered",
                        on_click=handle_sequential_scan,
                    ).classes("app-button-primary")
                    ui_refs["sequential_button"] = sequential_button
                    rename_button = ui.button(
                        "Đổi tên theo Video ID",
                        icon="drive_file_rename_outline",
                        on_click=open_rename_dialog,
                    ).props("outline disable")
                    ui_refs["rename_button"] = rename_button
            ui.label(
                "Ghép theo thời lượng dùng thời lượng video YouTube và mức sai lệch bên trên. "
                "Nếu nhiều video cùng phù hợp một file, tool chọn video có thời lượng gần nhất. "
                "Ghép theo tiêu đề chỉ cần toàn bộ tiêu đề YouTube xuất hiện trong tên file, "
                "không cần giống 100%. Vẫn có thể dùng Ghép lần lượt hoặc mapping.csv."
            ).classes("text-xs text-gray-600")
            scan_preview_container = ui.column().classes("w-full gap-1")
            refresh_scan_preview()
            refresh_rename_button()
            refresh_video_source_controls()

        with ui.row().classes("w-full items-start gap-5 flex-wrap"):
            with ui.column().classes("w-72 shrink-0"):
                def handle_ids_textarea_change(e=None):
                    on_ids_input()
                ids_textarea = ui.textarea(
                    label="Danh sách Video ID",
                    on_change=handle_ids_textarea_change,
                ).props('outlined autogrow color=green placeholder="Nhập mỗi dòng một ID"').classes("w-full")
                ui_refs["ids_textarea"] = ids_textarea
            with ui.column().classes("flex-1 min-w-[560px]"):
                right_panel_container = ui.column().classes("audio-add-table w-full gap-1")
                def on_ids_input():
                    if configuration_change_blocked():
                        ids_textarea.value = "\n".join(video_ids_state["ids"])
                        return
                    if video_source_state.get("mode") != "manual":
                        ids_textarea.value = "\n".join(video_ids_state["ids"])
                        return
                    video_ids_state["ids"] = parse_ids_from_text(ids_textarea.value or "")
                    video_source_state["manual_ids"] = list(video_ids_state["ids"])
                    batch_scan_state["result_channel"] = selected_channel["id"]
                    to_delete_path = [k for k in id_to_path.keys() if k not in video_ids_state["ids"]]
                    for k in to_delete_path:
                        del id_to_path[k]
                        video_titles.pop(k, None)
                        auto_match_info.pop(k, None)
                        video_processing_status.pop(k, None)
                        video_processing_errors.pop(k, None)
                    refresh_right_panel()
                    refresh_rename_button()
                    refresh_video_source_controls()
                    save_right_panel_state()
                refresh_right_panel()
        load_right_panel_state()

        state_sync_timer = {
            "value": None,
            "observed_active_run": _ADD_AUDIO_RUN_GUARD.locked(),
        }

        def deactivate_state_sync_timer() -> None:
            timer = state_sync_timer["value"]
            if timer is not None:
                try:
                    timer.deactivate()
                except RuntimeError:
                    pass

        def sync_persisted_running_state() -> None:
            """Let a freshly reloaded page follow its detached worker's state."""
            if not client_is_alive():
                deactivate_state_sync_timer()
                return

            run_is_active = _ADD_AUDIO_RUN_GUARD.locked()
            if run_is_active:
                state_sync_timer["observed_active_run"] = True
            if not run_is_active and not state_sync_timer["observed_active_run"]:
                deactivate_state_sync_timer()
                return

            try:
                state = state_manager.load_state("audio_add") or {}
                refreshed_statuses = _restore_language_statuses(
                    state.get("video_processing_status"), reset_processing=False
                )
                refreshed_errors = state.get("video_processing_errors") or {}
                if (
                    refreshed_statuses != video_processing_status
                    or refreshed_errors != video_processing_errors
                ):
                    video_processing_status.clear()
                    video_processing_status.update(refreshed_statuses)
                    video_processing_errors.clear()
                    video_processing_errors.update(refreshed_errors)
                    refresh_right_panel()
            except Exception as exc:
                logger.warning("Failed to sync add-audio checkpoint: {}", exc)

            if not run_is_active:
                deactivate_state_sync_timer()

        state_sync_timer["value"] = ui.timer(0.5, sync_persisted_running_state)

        def clear_all_inputs():
            """Clear all inputs and reset form state"""
            if configuration_change_blocked():
                return
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
                if ui_refs["music_folder_input"]:
                    ui_refs["music_folder_input"].value = ""
                if ui_refs["recursive_switch"]:
                    ui_refs["recursive_switch"].value = True
                if ui_refs["duration_tolerance_input"]:
                    ui_refs["duration_tolerance_input"].value = 2.0
                video_ids_state["ids"] = []
                id_to_path.clear()
                video_titles.clear()
                auto_match_info.clear()
                video_processing_status.clear()
                video_processing_errors.clear()
                selected_channel["id"] = None
                selected_languages["languages"] = []
                repeat_settings["times"] = 2
                repeat_settings["extra_minutes"] = 0
                performance_settings["max_concurrency"] = 1
                batch_scan_state["music_folder"] = ""
                batch_scan_state["recursive"] = True
                batch_scan_state["duration_tolerance"] = 2.0
                batch_scan_state["result_channel"] = None
                batch_scan_state["summary"] = {}
                batch_scan_state["issues"] = []
                batch_scan_state["extra_files"] = []
                video_source_state["mode"] = "manual"
                video_source_state["manual_ids"] = []
                video_source_state["failed_channel"] = None
                video_source_state["failed_videos"] = []
                video_source_state["scan_total"] = 0
                video_source_state["scan_skipped"] = 0
                refresh_right_panel()
                refresh_scan_preview()
                refresh_rename_button()
                refresh_video_source_controls()
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
