# RECOVERED: partial depyo recovery; unresolved regions marked below
import asyncio, random, tempfile, threading, time
from collections.abc import Awaitable, Callable
from pathlib import Path
from loguru import logger
from nicegui import context, ui
from src.audio_language import (
    call_audio_update_with_retry,
    invalid_language_codes,
    parse_language_codes,
)
from src.channel_store import channel_store
from src.module.audio_module import update_audio_module
from src.module.upload_video_module import (
    VideoProcessingResult,
    VideoProcessingState,
    upload_video_module,
)
from src.state_manager import state_manager
from src.task_runtime import (
    TaskStopped,
    bind_run_context,
    create_run_context,
    current_run_context,
)
from src.utils import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS, FFprobeError, build_intermittent_audio, get_channels_info, get_video_duration, list_media_files, multiply_audio, mux_audio_into_video, normalize_path
from web.components.common import create_channel_selection, select_directory, select_file
from web.components.drawer import nav_state; STEP_STYLE = {"pending": ("schedule", "text-gray-400", "Chờ"), "processing": ("hourglass_top", "text-blue-600", "Đang xử lý"), "successful": ("check_circle", "text-green-600", "Xong"), "stopped": ("stop_circle", "text-amber-600", "Đã dừng"), "unsuccessful": ("error", "text-red-600", "Lỗi")}
from web.theme import app_card, page_header, section_header, workflow_steps

MAX_ACTIVE_VIDEOS = 5
MAX_FFMPEG_JOBS = 5
MAX_UPLOAD_JOBS = 5
MAX_ADD_AUDIO_JOBS = 1
YOUTUBE_PROCESSING_TIMEOUT_SECONDS = 1200
YOUTUBE_PROCESSING_POLL_INTERVAL_SECONDS = 15
YOUTUBE_STATUS_MAX_CONSECUTIVE_TRANSIENT_ERRORS = 3

# NiceGUI can open the same page in multiple browser tabs.  Keep one flow run
# per application instance so two tabs cannot overwrite output_0/output_1...
_FLOW_RUN_GUARD = threading.Lock()


class YouTubeProcessingWaitError(RuntimeError):
    """A classified failure while waiting for YouTube video processing."""

    def __init__(self, message: str, *, state: VideoProcessingState):
        super().__init__(message)
        self.state = state


class YouTubeProcessingTimeoutError(TimeoutError):
    """The video remained in a real processing state until the deadline."""


def _processing_deadline_error(
    *,
    video_id: str,
    timeout_seconds: float,
    poll_count: int,
    elapsed: float,
    last_result: VideoProcessingResult | None,
) -> Exception:
    if (
        last_result is not None
        and last_result.state == VideoProcessingState.TRANSIENT_ERROR
    ):
        return YouTubeProcessingWaitError(
            "YouTube status check không phục hồi trước deadline "
            f"(video_id={video_id}, polls={poll_count}, elapsed={elapsed:.1f}s): "
            f"{last_result.message}",
            state=VideoProcessingState.TRANSIENT_ERROR,
        )
    return YouTubeProcessingTimeoutError(
        f"YouTube processing timeout sau {timeout_seconds:g}s "
        f"(video_id={video_id}, polls={poll_count}, elapsed={elapsed:.1f}s)"
    )


async def _wait_for_youtube_processing(
    status_check: Callable[[], Awaitable[VideoProcessingResult]],
    *,
    video_id: str,
    timeout_seconds: float = YOUTUBE_PROCESSING_TIMEOUT_SECONDS,
    poll_interval_seconds: float = YOUTUBE_PROCESSING_POLL_INTERVAL_SECONDS,
    max_consecutive_transient_errors: int = YOUTUBE_STATUS_MAX_CONSECUTIVE_TRANSIENT_ERRORS,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    checkpoint: Callable[[], None] = lambda: None,
    on_transient_error: Callable[[VideoProcessingResult, int, int, float], None]
    | None = None,
    on_poll_wait: Callable[[float], None] | None = None,
) -> VideoProcessingResult:
    """Poll a classified status using a wall-time deadline and bounded retries."""
    started_at = monotonic()
    deadline = started_at + max(0.0, timeout_seconds)
    poll_count = 0
    consecutive_transient_errors = 0
    last_result = None

    while True:
        checkpoint()
        now = monotonic()
        elapsed = max(0.0, now - started_at)
        if now >= deadline:
            raise _processing_deadline_error(
                video_id=video_id,
                timeout_seconds=timeout_seconds,
                poll_count=poll_count,
                elapsed=elapsed,
                last_result=last_result,
            )

        poll_count += 1
        result = await status_check()
        last_result = result
        elapsed = max(0.0, monotonic() - started_at)

        if result.state == VideoProcessingState.PROCESSED:
            return result
        if result.state == VideoProcessingState.PROCESSING:
            consecutive_transient_errors = 0
        elif result.state == VideoProcessingState.TRANSIENT_ERROR:
            consecutive_transient_errors += 1
            logger.warning(
                "YouTube status check transient failure: video_id={} poll={} "
                "elapsed={:.1f}s consecutive={}/{} error_type={} http_status={} detail={}",
                video_id,
                poll_count,
                elapsed,
                consecutive_transient_errors,
                max_consecutive_transient_errors,
                result.error_type or "unknown",
                result.http_status,
                result.message,
            )
            if on_transient_error is not None:
                on_transient_error(
                    result,
                    consecutive_transient_errors,
                    poll_count,
                    elapsed,
                )
            if consecutive_transient_errors >= max(
                1, max_consecutive_transient_errors
            ):
                raise YouTubeProcessingWaitError(
                    "YouTube status check failed sau "
                    f"{consecutive_transient_errors} lỗi tạm thời liên tiếp "
                    f"(video_id={video_id}, poll={poll_count}, elapsed={elapsed:.1f}s): "
                    f"{result.message}",
                    state=result.state,
                )
        else:
            logger.error(
                "YouTube status check failed: video_id={} poll={} elapsed={:.1f}s "
                "state={} error_type={} http_status={} youtube_status={} detail={}",
                video_id,
                poll_count,
                elapsed,
                result.state.value,
                result.error_type or "unknown",
                result.http_status,
                result.youtube_status or "unknown",
                result.message,
            )
            raise YouTubeProcessingWaitError(
                f"{result.message} (video_id={video_id}, poll={poll_count}, elapsed={elapsed:.1f}s)",
                state=result.state,
            )

        remaining = deadline - monotonic()
        if remaining <= 0:
            raise _processing_deadline_error(
                video_id=video_id,
                timeout_seconds=timeout_seconds,
                poll_count=poll_count,
                elapsed=elapsed,
                last_result=last_result,
            )
        if on_poll_wait is not None:
            on_poll_wait(elapsed)
        await sleep(min(max(0.0, poll_interval_seconds), remaining))


def _best_effort_ui(
    action: str,
    callback: Callable[[], object],
    *,
    is_available: Callable[[], bool] = lambda: True,
) -> bool:
    """Run a UI-only callback without allowing it to affect backend work."""
    if not is_available():
        return False
    try:
        callback()
        return True
    except Exception as exc:
        logger.warning("Add Audio UI update '{}' was skipped: {}", action, exc)
        return False


def _persist_then_ui(
    persist: Callable[[], object],
    ui_steps: list[tuple[str, Callable[[], object]]],
) -> object:
    """Persist a domain checkpoint before running any best-effort UI work."""
    result = persist()
    for name, callback in ui_steps:
        _best_effort_ui(name, callback)
    return result


def _run_finalizers(steps: list[tuple[str, Callable[[], object]]]) -> list[Exception]:
    """Run every finalizer even when an earlier finalizer fails."""
    errors = []
    for name, callback in steps:
        try:
            callback()
        except Exception as exc:
            errors.append(exc)
            logger.exception("Add Audio finalizer '{}' failed: {}", name, exc)
    return errors


async def _run_supervised_queue(
    entries: list,
    worker_count: int,
    process_item: Callable[[object], Awaitable[None]],
    should_stop: Callable[[], bool],
    on_unexpected_error: Callable[[object, Exception], None],
) -> tuple[list[Exception], list]:
    """Drain a queue despite item exceptions, or preserve leftovers on stop."""
    queue: asyncio.Queue = asyncio.Queue()
    for entry in entries:
        queue.put_nowait(entry)

    unexpected_errors: list[Exception] = []

    async def worker() -> None:
        while not should_stop():
            try:
                entry = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await process_item(entry)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                unexpected_errors.append(exc)
                try:
                    on_unexpected_error(entry, exc)
                except Exception as report_exc:
                    logger.exception(
                        "Failed to record unexpected Add Audio item error: {}",
                        report_exc,
                    )
            finally:
                queue.task_done()

    workers = [
        asyncio.create_task(worker())
        for _ in range(min(max(1, worker_count), len(entries)))
    ]
    worker_results = await asyncio.gather(*workers, return_exceptions=True)
    fatal_worker_errors = [
        result for result in worker_results if isinstance(result, BaseException)
    ]

    remaining = []
    while not queue.empty():
        try:
            remaining.append(queue.get_nowait())
            queue.task_done()
        except asyncio.QueueEmpty:
            break
    await queue.join()

    if remaining and not should_stop():
        details = "; ".join(str(error) for error in fatal_worker_errors) or "unknown worker exit"
        raise RuntimeError(
            f"Add Audio queue còn {len(remaining)} item sau khi worker kết thúc: {details}"
        )
    if fatal_worker_errors and not should_stop():
        raise RuntimeError(
            "Add Audio worker kết thúc bất thường: "
            + "; ".join(str(error) for error in fatal_worker_errors)
        )
    return unexpected_errors, remaining


def _restore_steps(saved_steps: dict | None, *, reset_processing: bool) -> dict:
    steps = {**_new_steps(), **(saved_steps or {})}
    if reset_processing:
        for key, value in steps.items():
            if value == "processing":
                steps[key] = "pending"
    return steps


def _replace_status_snapshot(target: dict, source: dict) -> None:
    """Replace the reload source so later list rebuilds cannot restore stale state."""
    target.clear()
    target.update(source)


def _replace_video_items_unless_processing(
    videos_state: dict,
    items: list,
    *,
    is_processing: bool,
) -> bool:
    """Do not detach workers from the item objects they are currently updating."""
    if is_processing:
        return False
    videos_state["items"] = items
    return True


def _upload_resume_point(item: dict) -> str:
    """Return the first remote upload operation which has not been checkpointed."""
    if item.get("video_id"):
        return "done"
    if item.get("frontend_upload_id") and item.get("scotty_resource_id"):
        return "create_video"
    return "upload"


def _require_checkpoint(persist: Callable[[], object], label: str) -> None:
    """Do not start another remote side effect after a failed critical checkpoint."""
    if persist() is False:
        raise RuntimeError(f"Không thể lưu checkpoint: {label}")

def _human_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            if unit == "B":
                return f"{num:.0f} {unit}"
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"
def _fmt_duration(seconds: float | None) -> str:
    if not seconds or seconds <= 0:
        return "--:--"
    total = int(seconds); m, s = divmod(total, 60); h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    
    return f"{m}:{s:02d}"

def _new_steps() -> dict:
    return {"merge": "pending", "upload": "pending", "wait": "pending", "add_audio": "pending"}
def create_add_audio_flow_page():
    try:
        page_client = context.client
    except RuntimeError:
        page_client = None
    ui_lifecycle = {"available": page_client is not None}
    paths_state = {"video_folder": "", "music_folder": "", "output_folder": ""}; options_state = {"random_music": False, "audio_language": "en"}; selected_channel = {"id": None}; channels = get_channels_info(); videos_state = {"items": []}; saved_status_map = {}; video_list_container = None; suppress_autosave = {"value": False}; ui_refs = {"random_switch": None, "lang_input": None, "process_btn": None, "clear_btn": None, "refresh_channel_display": None, "refresh_overlay": None, "stop_btn": None}; folder_selectors = {}; progress_refs = {}; processing = {"value": False}; stop_requested = {"value": False}; active_run = {"parent": None, "children": {}}; PERSIST_FIELDS = ("music", "music_path", "audio_path", "output_path", "video_id", "scotty_resource_id", "frontend_upload_id", "audio_language_results")

    def client_is_alive() -> bool:
        return (
            ui_lifecycle["available"]
            and page_client is not None
            and not getattr(page_client, "_deleted", False)
        )

    def element_is_alive(element) -> bool:
        return (
            client_is_alive()
            and element is not None
            and not getattr(element, "is_deleted", False)
        )

    def safe_ui(action: str, callback: Callable[[], object]) -> bool:
        def invoke():
            with page_client:
                return callback()

        return _best_effort_ui(action, invoke, is_available=client_is_alive)

    def safe_element_call(element, method: str, *args) -> bool:
        if not element_is_alive(element):
            return False
        return safe_ui(
            f"{method} on {type(element).__name__}",
            lambda: getattr(element, method)(*args),
        )

    def safe_notify(message: str, **kwargs) -> bool:
        return safe_ui("notification", lambda: ui.notify(message, **kwargs))

    def configuration_change_blocked() -> bool:
        """Keep a detached run's persisted inputs stable until it finishes."""
        if not _FLOW_RUN_GUARD.locked():
            return False
        safe_notify(
            "Không thể thay đổi cấu hình khi Add Audio Flow đang chạy.",
            type="warning",
        )
        return True

    def deactivate_state_sync_timer() -> None:
        timer = state_sync_timer["value"]
        if timer is not None:
            _best_effort_ui("deactivate state sync timer", timer.deactivate)

    def mark_client_unavailable() -> None:
        ui_lifecycle["available"] = False
        logger.info(
            "Add Audio page disconnected; backend flow will continue without UI updates"
        )

    if page_client is not None:
        page_client.on_disconnect(mark_client_unavailable)

    def save_state():
        try:
            if suppress_autosave["value"]:
                return False
            statuses = {}
            for it in videos_state["items"]:
                entry = {"steps": it["steps"]}
                for field in PERSIST_FIELDS:
                    entry[field] = it.get(field, "")
                statuses[it["name"]] = entry
            _replace_status_snapshot(saved_status_map, statuses)
            return state_manager.save_state("add_audio_flow", {"video_folder": paths_state["video_folder"], "music_folder": paths_state["music_folder"], "output_folder": paths_state["output_folder"], "random_music": options_state["random_music"], "audio_language": options_state["audio_language"], "selected_channel": selected_channel["id"], "statuses": statuses})
        except Exception as e:
            logger.error(f"Failed to save add_audio_flow state: {e}")
            return False
    def load_state():
        try:
            state = state_manager.load_state("add_audio_flow")
            if not state:
                return None
            paths_state["video_folder"] = state.get("video_folder", "")
            paths_state["music_folder"] = state.get("music_folder", "")
            paths_state["output_folder"] = state.get("output_folder", "")
            options_state["random_music"] = state.get("random_music", False)
            options_state["audio_language"] = state.get("audio_language", "en")
            selected_channel["id"] = state.get("selected_channel")
            _replace_status_snapshot(saved_status_map, state.get("statuses", {}))
            def update_ui():
                try:
                    for render in folder_selectors.values():
                        render()
                    if ui_refs["random_switch"]:
                        ui_refs["random_switch"].value = options_state["random_music"]
                    if ui_refs["lang_input"]:
                        ui_refs["lang_input"].value = options_state["audio_language"]
                    if selected_channel["id"] and ui_refs["refresh_channel_display"]:
                        ui_refs["refresh_channel_display"]()
                    if ui_refs.get("refresh_overlay"):
                        ui_refs["refresh_overlay"]()
                    load_videos()
                except Exception as e:
                    logger.error(f"Failed to update UI: {e}")
            ui.timer(0.5, update_ui, once=True)
        except Exception as e:
            logger.error(f"Failed to load add_audio_flow state: {e}")
    def load_videos():
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
                    "duration_error": "",
                    "steps": _restore_steps(
                        saved.get("steps"),
                        reset_processing=not _FLOW_RUN_GUARD.locked(),
                    ),
                }
                for field in PERSIST_FIELDS:
                    default = {} if field == "audio_language_results" else ""
                    item[field] = saved.get(field, default)
                items.append(item)
        if not _replace_video_items_unless_processing(
            videos_state,
            items,
            is_processing=processing["value"],
        ):
            return
        refresh_video_list()
        if items:
            ui.timer(0.05, load_durations, once=True)
    async def load_durations():
        for item in videos_state["items"]:
            if item["duration"] is None:
                try:
                    item["duration"] = await asyncio.to_thread(
                        get_video_duration, item["path"]
                    )
                    item["duration_error"] = ""
                except FFprobeError as exc:
                    item["duration_error"] = str(exc)
                except Exception as exc:
                    item["duration_error"] = f"Unexpected metadata error: {exc}"
                    logger.exception(
                        "Unexpected duration error for {}: {}", item["path"], exc
                    )
                refresh_video_list()

    state_sync_timer = {
        "value": None,
        "observed_active_run": _FLOW_RUN_GUARD.locked(),
    }

    def sync_persisted_running_state():
        """Let a reloaded page observe the still-running detached backend job."""
        if not client_is_alive():
            deactivate_state_sync_timer()
            return
        detached_run_active = _FLOW_RUN_GUARD.locked()
        if detached_run_active:
            state_sync_timer["observed_active_run"] = True
        state = state_manager.load_state("add_audio_flow")
        if not state:
            if not detached_run_active and not state_sync_timer["observed_active_run"]:
                deactivate_state_sync_timer()
            return
        statuses = state.get("statuses") or {}
        _replace_status_snapshot(saved_status_map, statuses)
        changed = False
        for item in videos_state["items"]:
            saved = statuses.get(item["name"])
            if not saved:
                continue
            restored_steps = _restore_steps(
                saved.get("steps"),
                reset_processing=False,
            )
            if item["steps"] != restored_steps:
                item["steps"] = restored_steps
                changed = True
            for field in PERSIST_FIELDS:
                restored_value = saved.get(
                    field,
                    {} if field == "audio_language_results" else "",
                )
                if item.get(field) != restored_value:
                    item[field] = restored_value
                    changed = True
        if changed:
            refresh_video_list()
        safe_element_call(
            ui_refs.get("process_btn"), "set_enabled", not detached_run_active
        )
        safe_element_call(
            ui_refs.get("clear_btn"), "set_enabled", not detached_run_active
        )
        if detached_run_active:
            safe_element_call(
                progress_refs.get("current"),
                "set_text",
                "Backend đang tiếp tục xử lý sau khi trang được tải lại",
            )
        else:
            deactivate_state_sync_timer()

    def step_badge(status: str):
        icon, color, label = STEP_STYLE.get(status, STEP_STYLE["pending"])
        with ui.row().classes(f"app-step-chip app-step-chip--{status} items-center justify-center gap-1 flex-nowrap"):
            ui.icon(icon).classes(f"text-sm shrink-0 {color}")
            ui.label(label).classes(f"text-xs font-medium whitespace-nowrap {color}")
    def refresh_video_list():
        if not element_is_alive(video_list_container):
            return False

        def render():
            video_list_container.clear()
            items = videos_state["items"]
            with video_list_container:
                with ui.row().classes("items-center gap-2 mb-1"):
                    ui.icon("video_library").classes("text-gray-500")
                    ui.label(f"Tìm thấy {len(items)} video").classes("text-sm font-semibold text-gray-700")
                if not items:
                    ui.label("Chưa chọn folder video hoặc folder không có video nào.").classes("text-gray-500 italic text-sm")
                    return

                with ui.row().classes("w-full min-h-[42px] items-center font-semibold text-xs text-gray-500 bg-gray-50 border-b border-gray-200 px-3 flex-nowrap"):
                    ui.label("#").classes("w-1/12")
                    ui.label("Video").classes("w-3/12")
                    ui.label("ID").classes("w-2/12")
                    ui.label("Nhạc").classes("w-2/12")
                    ui.label("Ghép nhạc").classes("w-1/12 text-center")
                    ui.label("Upload").classes("w-1/12 text-center")
                    ui.label("Chờ xử lý").classes("w-1/12 text-center")
                    ui.label("Add audio").classes("w-1/12 text-center")

                for idx, item in enumerate(items, 1):
                    steps = item["steps"]
                    with ui.row().classes("w-full min-h-[54px] items-center bg-white px-3 py-1 border-b border-gray-100 flex-nowrap hover:bg-gray-50"):
                        ui.label(str(idx)).classes("w-1/12 text-xs text-gray-500")
                        with ui.column().classes("w-3/12 min-w-0 gap-0"):
                            ui.label(item["name"]).classes("truncate text-sm font-medium text-gray-800").tooltip(item["name"])
                            meta = _human_size(item["size"])
                            if item.get("duration_error"):
                                meta += " · không đọc được duration"
                            elif item["duration"] is None:
                                meta += " · đang đọc..."
                            else:
                                meta += f" · {_fmt_duration(item['duration'])}"
                            meta_label = ui.label(meta).classes("text-xs text-gray-400")
                            if item.get("duration_error"):
                                meta_label.tooltip(item["duration_error"])

                        vid = item.get("video_id")
                        with ui.column().classes("w-2/12 min-w-0"):
                            if vid:
                                ui.label(vid).classes("truncate text-xs font-medium text-indigo-600").tooltip(vid)
                            else:
                                ui.label("—").classes("text-xs text-gray-400")

                        ui.label(item.get("music") or "—").classes("w-2/12 truncate text-xs text-gray-600")
                        with ui.element("div").classes("w-1/12 flex justify-center"):
                            step_badge(steps["merge"])
                        with ui.element("div").classes("w-1/12 flex justify-center"):
                            step_badge(steps["upload"])
                        with ui.element("div").classes("w-1/12 flex justify-center"):
                            step_badge(steps["wait"])
                        with ui.element("div").classes("w-1/12 flex justify-center"):
                            step_badge(steps["add_audio"])

        return safe_ui("refresh video list", render)
    async def step_merge(item, output_folder, musics, index, run_config):
        """Render video với nhạc gián đoạn (phát 3s / tắt 7s, 3s cuối luôn có tiếng).

        Xuất 2 file: output_{i}.m4v (audio đã mute) và output_{i}_processed.mp4
        (video đã render với audio đó).
        """
        if item.get("duration") is None:
            item["duration"] = await asyncio.to_thread(
                get_video_duration, item["path"]
            )
            item["duration_error"] = ""

        if run_config["random_music"]:
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
        run_context = current_run_context()
        if run_context is not None:
            run_context.register_cleanup_path(audio_out)
            run_context.register_cleanup_path(video_out)

        overlay_png = run_config["overlay_png"]

        dur = await asyncio.to_thread(
            build_intermittent_audio,
            music_file=str(music),
            audio_out=audio_out,
            play_sec=3.0,
            mute_sec=7.0,
        )
        await asyncio.to_thread(
            mux_audio_into_video,
            video_file=item["path"],
            audio_file=audio_out,
            video_out=video_out,
            duration=dur,
            overlay_png=overlay_png or None,
        )
        if run_context is not None:
            run_context.keep_path(audio_out)
            run_context.keep_path(video_out)
        save_state()
    async def step_upload(item, output_folder, musics, index, run_config):
        """Upload video đã ghép nhạc lên kênh và tạo video.

        Chặng 1 (start) + chặng 2 (finalize) + chặng 3 (createvideo → videoId,
        set title/description). Title mặc định lấy từ tên file.
        """
        channel_id = run_config["channel_id"]
        if not channel_id:
            raise Exception("Chưa chọn kênh")

        resume_point = _upload_resume_point(item)
        if resume_point == "done":
            return

        if resume_point == "upload":
            upload_prog = {"sent": 0, "total": 0}
            item["upload_progress"] = upload_prog
            result = await asyncio.to_thread(
                upload_video_module.upload,
                channel_id=channel_id,
                file_path=item["output_path"],
                index=index,
                progress=upload_prog,
            )

            item["frontend_upload_id"] = result["frontend_upload_id"]
            item["scotty_resource_id"] = result["scotty_resource_id"]
            _require_checkpoint(save_state, "upload resource IDs")
        video_id = await asyncio.to_thread(
            upload_video_module.create_video,
            channel_id=channel_id,
            scotty_resource_id=item["scotty_resource_id"],
            frontend_upload_id=item["frontend_upload_id"],
            title=Path(item.get("music") or item["name"]).stem,
        )
        item["video_id"] = video_id
        _require_checkpoint(save_state, "video ID")
    async def step_wait_processed(item, output_folder, musics, index, run_config):
        """Chờ YouTube xử lý video xong (poll status = VIDEO_STATUS_PROCESSED)."""
        channel_id = run_config["channel_id"]
        video_id = item.get("video_id")
        if not video_id:
            raise Exception("Chưa có video ID (upload chưa xong)")

        step_label = None
        push_log("Chờ YouTube xử lý video xong...", "wait", indent=True)

        def checkpoint() -> None:
            run_context = current_run_context()
            if run_context is not None:
                run_context.checkpoint()
            if stop_requested["value"]:
                raise TaskStopped()

        async def check_status() -> VideoProcessingResult:
            return await asyncio.to_thread(
                upload_video_module.get_processing_status,
                channel_id,
                video_id,
            )

        async def sleep_interruptibly(seconds: float) -> None:
            sleep_deadline = time.monotonic() + seconds
            while True:
                checkpoint()
                remaining = sleep_deadline - time.monotonic()
                if remaining <= 0:
                    return
                await asyncio.sleep(min(0.1, remaining))

        def report_transient_error(
            result: VideoProcessingResult,
            consecutive: int,
            poll_count: int,
            elapsed: float,
        ) -> None:
            push_log(
                "Kiểm tra trạng thái YouTube lỗi tạm thời "
                f"({consecutive}/{YOUTUBE_STATUS_MAX_CONSECUTIVE_TRANSIENT_ERRORS})",
                "wait",
                indent=True,
            )

        def report_poll_wait(elapsed: float) -> None:
            if step_label:
                safe_element_call(
                    step_label,
                    "set_text",
                    f"Bước: Chờ xử lý — {int(elapsed)}s",
                )

        await _wait_for_youtube_processing(
            check_status,
            video_id=video_id,
            checkpoint=checkpoint,
            sleep=sleep_interruptibly,
            on_transient_error=report_transient_error,
            on_poll_wait=report_poll_wait,
        )
        push_log("Video đã xử lý xong", "ok", indent=True)
    async def step_add_audio(item, output_folder, musics, index, run_config):
        """Thêm audio track (file nhạc gốc) cho video_id đã xử lý xong.

        Add track cho từng ngôn ngữ (tách theo khoảng trắng).
        """
        channel_id = run_config["channel_id"]
        video_id = item.get("video_id")
        if not video_id:
            raise Exception("Chưa có video ID (upload chưa xong)")

        audio_path = item.get("music_path")
        if not audio_path or not Path(audio_path).is_file():
            raise Exception(f"Không tìm thấy file nhạc gốc: {audio_path}")

        languages = list(run_config["audio_languages"])

        step_label = None
        if step_label:
            safe_element_call(step_label, "set_text", "Bước: Add audio — chuẩn bị audio khớp thời lượng...")
        info = await asyncio.to_thread(
            upload_video_module._get_video_info,
            video_id=video_id,
            channel_id=channel_id,
        )
        video_dur = info.duration_ms / 1000.0 if info and info.duration_ms > 0 else None

        suffix = Path(audio_path).suffix or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
            matched_path = tf.name
        run_context = current_run_context()
        if run_context is not None:
            run_context.register_cleanup_path(matched_path)

        try:
            if video_dur:
                await asyncio.to_thread(
                    multiply_audio,
                    input_file=normalize_path(audio_path),
                    output_file=matched_path,
                    times=1,
                    extra_minutes=0,
                    video_duration_seconds=video_dur,
                )
                data = await asyncio.to_thread(Path(matched_path).read_bytes)
            else:
                logger.warning(f"Không lấy được thời lượng video {video_id}, dùng nhạc gốc.")
                data = await asyncio.to_thread(Path(audio_path).read_bytes)

            language_errors = []
            language_results = dict(item.get("audio_language_results") or {})
            item["audio_language_results"] = language_results
            for language_index, lang in enumerate(languages, 1):
                previous = language_results.get(lang) or {}
                if previous.get("status") in ("successful", "already_added"):
                    push_log(f"Audio track đã hoàn tất trước đó, bỏ qua: {lang}", "ok", indent=True)
                    continue
                if step_label:
                    safe_element_call(step_label, "set_text", f"Bước: Add audio — ngôn ngữ {lang}")
                push_log(
                    f"Audio {language_index}/{len(languages)} — đang xử lý {lang}",
                    "wait",
                    indent=True,
                )

                def update_one_language(lang=lang):
                    return update_audio_module.add(
                        id_video=video_id,
                        channel_id=channel_id,
                        file_name=audio_path,
                        language=lang,
                        data=data,
                    )

                def log_retry(attempt, delay, exc, lang=lang):
                    logger.warning(
                        "Retry {}/3 for video {} language {} in {}s: {}",
                        attempt,
                        video_id,
                        lang,
                        delay,
                        exc,
                    )
                    push_log(
                        f"{lang}: thử lại sau {delay:g}s ({attempt}/3)",
                        "wait",
                        indent=True,
                    )

                try:
                    status = await call_audio_update_with_retry(
                        update_one_language,
                        on_retry=log_retry,
                    )
                except TaskStopped:
                    raise
                except Exception as exc:
                    message = str(exc)
                    language_results[lang] = {
                        "status": "unsuccessful",
                        "error": message,
                    }
                    language_errors.append(f"{lang}: {message}")
                    save_state()
                    logger.error(
                        "Add audio failed for video {} language {}: {}",
                        video_id,
                        lang,
                        exc,
                    )
                    push_log(
                        f"Audio {lang}: thất bại — tiếp tục mã kế tiếp",
                        "error",
                        indent=True,
                    )
                    continue

                result_status = "successful" if status == 200 else "already_added"
                language_results[lang] = {"status": result_status, "error": ""}
                _require_checkpoint(save_state, f"audio language {lang}")
                if status == 409:
                    push_log(f"Audio track đã tồn tại: {lang}", "ok", indent=True)
                else:
                    push_log(f"Đã thêm audio track: {lang}", "ok", indent=True)

            if language_errors:
                raise Exception(
                    f"{len(language_errors)}/{len(languages)} ngôn ngữ thất bại: "
                    + "; ".join(language_errors)
                )
        finally:
            try:
                if Path(matched_path).exists():
                    Path(matched_path).unlink()
            except Exception as exc:
                logger.warning(f"Không xóa được file tạm {matched_path}: {exc}")

    STEP_SEQUENCE = [
        ("merge", "Ghép nhạc", step_merge),
        ("upload", "Upload", step_upload),
        ("wait", "Chờ xử lý", step_wait_processed),
        ("add_audio", "Add audio", step_add_audio),
    ]
    def set_processing_ui(active: bool, message: str=""):
        """Bật/tắt trạng thái đang xử lý: khóa điều hướng, panel tiến trình, nút."""
        processing["value"] = active

        if active:
            nav_state.lock("Đang xử lý video, vui lòng đợi hoàn tất trước khi chuyển trang.")
        else:
            nav_state.unlock()
        safe_element_call(progress_refs.get("panel"), "set_visibility", active)
        safe_element_call(progress_refs.get("bar"), "set_value", 0)
        if message:
            safe_element_call(progress_refs.get("current"), "set_text", message)
        safe_element_call(ui_refs.get("process_btn"), "set_enabled", not active)
        safe_element_call(ui_refs.get("clear_btn"), "set_enabled", not active)
        safe_element_call(ui_refs.get("stop_btn"), "set_visibility", active)
        safe_element_call(ui_refs.get("stop_btn"), "set_enabled", active)
        if active:
            safe_element_call(progress_refs.get("log"), "clear")
    LOG_STYLE = {"info": ("chevron_right", "text-gray-600"), "work": ("autorenew", "text-blue-600"), "wait": ("hourglass_top", "text-amber-600"), "ok": ("check_circle", "text-green-600"), "error": ("error", "text-red-600")}
    def push_log(message: str, level: str="info", indent: bool=False):
        """Thêm 1 dòng progress thân thiện cho user (không lộ chi tiết kỹ thuật)."""
        log = progress_refs.get("log")
        if not element_is_alive(log):
            return False
        icon, color = LOG_STYLE.get(level, LOG_STYLE["info"])

        def render():
            with log:
                with ui.row().classes(f"items-center gap-1 w-full flex-nowrap {'pl-5' if indent else ''}"):
                    ui.icon(icon).classes(f"text-sm shrink-0 {color}")
                    ui.label(message).classes(f"text-xs {color} truncate")
            area = progress_refs.get("log_area")
            if element_is_alive(area):
                area.scroll_to(percent=1.0)

        return safe_ui("append progress log", render)

    def update_parallel_progress(total: int, stats: dict) -> None:
        active = sum(
            1
            for item in videos_state["items"]
            if any(value == "processing" for value in item["steps"].values())
        )
        finished = stats["finished"]
        safe_element_call(
            progress_refs.get("current"),
            "set_text",
            f"Đang chạy {active}/{MAX_ACTIVE_VIDEOS} video song song",
        )
        safe_element_call(
            progress_refs.get("step"),
            "set_text",
            f"Hoàn tất {finished}/{total} — Lỗi {stats['failed']}",
        )
        safe_element_call(
            progress_refs.get("remaining"),
            "set_text",
            f"Còn lại: {max(0, total - finished)} video",
        )
        safe_element_call(
            progress_refs.get("bar"),
            "set_value",
            finished / total if total else 0,
        )

    async def run_video_item(
        orig_index: int,
        item: dict,
        output_folder: str,
        musics: list,
        run_config: dict,
        step_limits: dict,
        errors: list,
        stats: dict,
        total: int,
    ) -> str:
        context_key = f"{orig_index}:{item['path']}"
        context = create_run_context(f"add_audio_video_{orig_index}")
        active_run["children"][context_key] = context
        failed = False
        try:
            with bind_run_context(context):
                for step_key in _new_steps():
                    if item["steps"].get(step_key) == "processing":
                        item["steps"][step_key] = "pending"

                _persist_then_ui(
                    save_state,
                    [
                        (
                            "announce video start",
                            lambda: push_log(
                                f"Video {orig_index + 1}: {item['name']}", "work"
                            ),
                        ),
                        ("render video start", refresh_video_list),
                        (
                            "render initial progress",
                            lambda: update_parallel_progress(total, stats),
                        ),
                    ],
                )

                for step_key, step_name, step_fn in STEP_SEQUENCE:
                    if stop_requested["value"] or context.stopped:
                        raise TaskStopped()
                    if item["steps"].get(step_key) == "successful":
                        continue

                    item["steps"][step_key] = "processing"
                    _persist_then_ui(
                        save_state,
                        [
                            (
                                "announce step start",
                                lambda: push_log(
                                    f"{item['name']} — {step_name}: đang xử lý...",
                                    "wait",
                                    indent=True,
                                ),
                            ),
                            ("render step start", refresh_video_list),
                            (
                                "render step progress",
                                lambda: update_parallel_progress(total, stats),
                            ),
                        ],
                    )
                    try:
                        semaphore = step_limits.get(step_key)
                        if semaphore is None:
                            await step_fn(item, output_folder, musics, orig_index, run_config)
                        else:
                            async with semaphore:
                                context.checkpoint()
                                await step_fn(item, output_folder, musics, orig_index, run_config)
                        item["steps"][step_key] = "successful"
                        _persist_then_ui(
                            save_state,
                            [
                                (
                                    "announce step success",
                                    lambda: push_log(
                                        f"{item['name']} — {step_name}: xong",
                                        "ok",
                                        indent=True,
                                    ),
                                )
                            ],
                        )
                    except TaskStopped:
                        item["steps"][step_key] = "stopped"
                        save_state()
                        raise
                    except Exception as exc:
                        if context.stopped or stop_requested["value"]:
                            item["steps"][step_key] = "stopped"
                            raise TaskStopped() from exc
                        item["steps"][step_key] = "unsuccessful"
                        failed = True
                        errors.append(f"{item['name']} [{step_name}]: {exc}")
                        _persist_then_ui(
                            save_state,
                            [
                                (
                                    "announce step failure",
                                    lambda: push_log(
                                        f"{item['name']} — {step_name}: thất bại",
                                        "error",
                                        indent=True,
                                    ),
                                )
                            ],
                        )
                        logger.error(
                            "Step '{}' failed for {}: {}",
                            step_key,
                            item["name"],
                            exc,
                        )
                        break
                    finally:
                        refresh_video_list()
                        update_parallel_progress(total, stats)
        except TaskStopped:
            for step_key, value in item["steps"].items():
                if value == "processing":
                    item["steps"][step_key] = "stopped"
            save_state()
            push_log(f"{item['name']}: đã dừng", "info", indent=True)
            return "stopped"
        finally:
            save_state()
            _run_finalizers(
                [
                    ("cleanup item run context", context.cleanup),
                    (
                        "remove active item context",
                        lambda: active_run["children"].pop(context_key, None),
                    ),
                ]
            )
            refresh_video_list()
            update_parallel_progress(total, stats)
        return "failed" if failed else "successful"

    async def run_parallel_queue(
        pending_items: list,
        output_folder: str,
        musics: list,
        run_config: dict,
        errors: list,
    ) -> dict:
        stats = {"finished": 0, "failed": 0}
        step_limits = {
            "merge": asyncio.Semaphore(MAX_FFMPEG_JOBS),
            "upload": asyncio.Semaphore(MAX_UPLOAD_JOBS),
            "add_audio": asyncio.Semaphore(MAX_ADD_AUDIO_JOBS),
        }

        async def process_entry(entry) -> None:
            orig_index, item = entry
            outcome = await run_video_item(
                orig_index,
                item,
                output_folder,
                musics,
                run_config,
                step_limits,
                errors,
                stats,
                len(pending_items),
            )
            stats["finished"] += 1
            if outcome == "failed":
                stats["failed"] += 1
            save_state()
            refresh_video_list()
            update_parallel_progress(len(pending_items), stats)

        def record_unexpected_error(entry, exc: Exception) -> None:
            _, item = entry
            marked = False
            for step_key, value in item.get("steps", {}).items():
                if value == "processing":
                    item["steps"][step_key] = "unsuccessful"
                    marked = True
            if not marked:
                for step_key, value in item.get("steps", {}).items():
                    if value != "successful":
                        item["steps"][step_key] = "unsuccessful"
                        break
            stats["finished"] += 1
            stats["failed"] += 1
            errors.append(f"{item.get('name', '<unknown>')} [unexpected]: {exc}")
            save_state()
            logger.exception(
                "Unexpected Add Audio item failure for {}: {}",
                item.get("name", "<unknown>"),
                exc,
            )

        _, remaining = await _run_supervised_queue(
            pending_items,
            MAX_ACTIVE_VIDEOS,
            process_entry,
            lambda: stop_requested["value"],
            record_unexpected_error,
        )
        if remaining:
            logger.info(
                "Add Audio stopped with {} queued item(s) preserved for retry",
                len(remaining),
            )
        save_state()
        return stats

    async def handle_stop():
        if not processing["value"]:
            return None
        stop_requested["value"] = True

        safe_element_call(ui_refs.get("stop_btn"), "set_enabled", False)
        safe_element_call(
            progress_refs.get("step"), "set_text", "Đang dừng tác vụ hiện tại..."
        )
        safe_notify("Đang dừng tác vụ hiện tại...", type="info")
        contexts = []
        parent = active_run.get("parent")
        if parent is not None:
            contexts.append(parent)
        contexts.extend(list(active_run["children"].values()))
        if contexts:
            await asyncio.gather(
                *(asyncio.to_thread(context.request_stop) for context in contexts),
                return_exceptions=True,
            )

    async def handle_process():
        if processing["value"]:
            safe_notify("Đang xử lý, vui lòng đợi hoàn tất", type="warning")
            return

        video_folder = normalize_path(paths_state["video_folder"])
        music_folder = normalize_path(paths_state["music_folder"])
        output_folder = normalize_path(paths_state["output_folder"])
        if not video_folder or not Path(video_folder).is_dir():
            safe_notify("Folder video không hợp lệ", type="warning")
            return
        if not music_folder or not Path(music_folder).is_dir():
            safe_notify("Folder nhạc không hợp lệ", type="warning")
            return
        if not output_folder:
            safe_notify("Vui lòng chọn folder output", type="warning")
            return
        if not selected_channel["id"]:
            safe_notify("Vui lòng chọn kênh để upload", type="warning")
            return

        items = videos_state["items"]
        if not items:
            safe_notify("Không có video nào để xử lý", type="warning")
            return
        musics = list_media_files(music_folder, AUDIO_EXTENSIONS)
        if not musics:
            safe_notify("Không tìm thấy file nhạc nào trong folder", type="warning")
            return
        try:
            Path(output_folder).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            safe_notify(f"Không tạo được folder output: {e}", type="negative")
            return

        pending_items = [
            (idx, it)
            for idx, it in enumerate(items)
            if not all(it["steps"][k] == "successful" for k, _, _ in STEP_SEQUENCE)
        ]
        if not pending_items:
            safe_notify("Tất cả video đã hoàn thành. Không có gì để chạy.", type="info")
            return

        channel_snapshot = get_channels_info(selected_channel["id"])
        if not channel_snapshot:
            safe_notify("Không tìm thấy dữ liệu kênh đã chọn", type="negative")
            return
        audio_languages = parse_language_codes(options_state.get("audio_language"))
        if not audio_languages:
            safe_notify("Hãy nhập ít nhất một mã ngôn ngữ", type="warning")
            return
        invalid_languages = invalid_language_codes(audio_languages)
        if invalid_languages:
            safe_notify(
                f"Mã ngôn ngữ không hợp lệ: {', '.join(invalid_languages)}",
                type="negative",
            )
            return
        run_config = {
            "channel_id": selected_channel["id"],
            "random_music": bool(options_state["random_music"]),
            "audio_languages": audio_languages,
            "overlay_png": channel_snapshot.overlay_png or "",
        }

        if not _FLOW_RUN_GUARD.acquire(blocking=False):
            safe_notify(
                "Luồng Thêm audio đang chạy ở một cửa sổ khác.",
                type="warning",
            )
            return

        total = len(pending_items)
        errors = []
        stop_requested["value"] = False
        stopped = False
        run_context = None
        try:
            run_context = create_run_context("add_audio_flow")
            active_run["parent"] = run_context
            active_run["children"].clear()
            set_processing_ui(True)
            push_log(
                f"Bắt đầu xử lý {total} video — tối đa {MAX_ACTIVE_VIDEOS} video song song",
                "info",
            )
            stats = await run_parallel_queue(
                pending_items,
                output_folder,
                musics,
                run_config,
                errors,
            )
            stopped = stop_requested["value"] or run_context.stopped
            update_parallel_progress(total, stats)
        except Exception as exc:
            errors.append(f"Lỗi batch: {exc}")
            save_state()
            logger.exception("Add Audio batch failed: {}", exc)
            push_log(f"Batch thất bại: {exc}", "error")
        finally:
            critical_steps = [("persist final state", save_state)]
            if run_context is not None:
                critical_steps.append(("cleanup parent run context", run_context.cleanup))
            critical_steps.extend(
                [
                    (
                        "clear active run references",
                        lambda: (
                            active_run.__setitem__("parent", None),
                            active_run["children"].clear(),
                        ),
                    ),
                    ("release flow guard", _FLOW_RUN_GUARD.release),
                    ("reset processing UI", lambda: set_processing_ui(False)),
                ]
            )
            _run_finalizers(critical_steps)

        if stopped:
            safe_element_call(progress_refs.get("step"), "set_text", "Đã dừng")
            push_log("Đã dừng theo yêu cầu", "info")
        elif errors:
            push_log("Hoàn tất — có một số video lỗi", "error")
        else:
            push_log("Hoàn tất tất cả video", "ok")

        done_count = sum(
            1
            for it in items
            if all(it["steps"][k] == "successful" for k, _, _ in STEP_SEQUENCE)
        )
        if stopped:
            safe_notify(
                f"Đã dừng. {done_count}/{len(items)} video hoàn thành toàn bộ flow. Bấm Xử lý để chạy tiếp phần còn lại.",
                type="info",
            )
            return
        if errors:
            safe_notify(
                f"Hoàn tất với một số lỗi. {done_count}/{len(items)} video hoàn thành. Bấm Xử lý để thử lại phần lỗi.",
                type="warning",
            )
            return
        safe_notify(
            f"Hoàn tất! {done_count}/{len(items)} video đã xử lý xong toàn bộ flow.",
            type="positive",
        )
    def clear_all_inputs():
        if configuration_change_blocked():
            return
        try:
            suppress_autosave["value"] = True
            paths_state["video_folder"] = ""
            paths_state["music_folder"] = ""
            paths_state["output_folder"] = ""
            options_state["random_music"] = False
            videos_state["items"] = []
            saved_status_map.clear()
            for render in folder_selectors.values():
                render()
            if ui_refs["random_switch"]:
                ui_refs["random_switch"].value = False
            refresh_video_list()
            ui.notify("Đã xóa tất cả input", type="info")
        finally:
            suppress_autosave["value"] = False
        save_state()

    if False:
        pass
    if False:
        pass

    def build_folder_selector(key: str, label: str, placeholder: str, icon: str, on_after=None, extra_render=None):
        def pick_folder(_=None):
            if configuration_change_blocked():
                return
            selected = select_directory(initial_dir=paths_state[key] or None, title=label)
            if selected:
                paths_state[key] = selected
                render()
                save_state()
                if on_after:
                    on_after()

        def clear_folder(_=None):
            if configuration_change_blocked():
                return
            paths_state[key] = ""
            render()
            save_state()
            if on_after:
                on_after()

        card = (
            ui.card()
            .classes("app-flow-folder flex-1 min-w-[220px] h-full p-3 cursor-pointer transition")
            .on("click", pick_folder)
        )

        def render():
            path = paths_state[key]
            card.clear()

            with card:
                with ui.column().classes("w-full h-full justify-center"):
                    with ui.row().classes("items-center gap-3 w-full flex-nowrap"):
                        ui.icon(icon).classes("text-2xl shrink-0 " + ("text-emerald-600" if path else "text-gray-400"))
                        with ui.column().classes("gap-0 min-w-0 flex-1"):
                            ui.label(label).classes("text-xs font-semibold text-gray-600")
                            if path:
                                ui.label(path).classes("text-sm text-gray-800 truncate").tooltip(path)
                            else:
                                ui.label(placeholder).classes("text-sm text-gray-400 italic truncate")
                        if extra_render:
                            with ui.element("div").classes("shrink-0").on("click.stop", lambda: None):
                                extra_render()
                        if path:
                            ui.button(icon="close").props("flat round dense size=sm color=grey").classes("shrink-0").on("click.stop", clear_folder).tooltip("Bỏ chọn")

        render()
        folder_selectors[key] = render
    page = ui.column().classes("app-page")
    with page:
        with page_header(
            "Thêm audio flow",
            "Chuẩn bị video, ghép nhạc, upload và thêm audio track trong một quy trình.",
            eyebrow="Quy trình",
        ):
            pass
        workflow_steps(
            [
                {"title": "Ghép nhạc", "description": "Tạo video đầu ra", "state": "current"},
                {"title": "Upload", "description": "Đăng video lên kênh", "state": "pending"},
                {"title": "Chờ xử lý", "description": "Đợi YouTube sẵn sàng", "state": "pending"},
                {"title": "Add audio", "description": "Thêm audio theo ngôn ngữ", "state": "pending"},
            ]
        )
        main_container = ui.column().classes("w-full gap-4")
    with main_container:
        with app_card(compact=True):
            with section_header(
                "Thiết lập quy trình",
                "Chọn kênh, nguồn video, nguồn nhạc và nơi lưu file đầu ra.",
            ):
                pass
        def on_channel_select(channel_id):
            if configuration_change_blocked():
                return
            selected_channel["id"] = channel_id

            save_state()
            if ui_refs.get("refresh_overlay"):
                ui_refs["refresh_overlay"]()
                return None
        _, refresh_channel_display = create_channel_selection(
            channels,
            on_channel_select,
            initial_selected_ids=[selected_channel["id"]] if selected_channel["id"] else None,
        )
        ui_refs["refresh_channel_display"] = refresh_channel_display
        def pick_overlay():
            cid = selected_channel["id"]
            if not cid:
                ui.notify("Hãy chọn kênh trước", type="warning")
                return
            ch = get_channels_info(cid)
            init = str(Path(ch.overlay_png).parent) if ch and ch.overlay_png else None
            path = select_file(
                initial_dir=init,
                title="Chọn ảnh tên kênh (PNG 16:9)",
                filetypes=[("PNG", "*.png"), ("All files", "*.*")],
            )
            if path:
                channel_store.set_overlay_png(cid, path)
                refresh_overlay_display()
                ui.notify("Đã gán ảnh tên kênh cho kênh này", type="positive")
        def clear_overlay():
            cid = selected_channel["id"]
            if cid:
                channel_store.set_overlay_png(cid, "")
                refresh_overlay_display()
                return None
        overlay_row = ui.row().classes("items-center gap-2 mt-1 w-full flex-nowrap")
        def refresh_overlay_display():
            overlay_row.clear()
            with overlay_row:
                cid = selected_channel["id"]
                if not cid:
                    ui.label("Chọn kênh để gán ảnh tên kênh (overlay phủ toàn khung)").classes("text-xs text-gray-400 italic")
                    return
                ch = get_channels_info(cid)
                png = (ch.overlay_png if ch else "") or ""
                exists = bool(png) and Path(normalize_path(png)).is_file()
                if exists:
                    icon, color, text = "check_circle", "text-green-600", Path(png).name
                elif png:
                    icon, color, text = "error", "text-red-600", f"Không tồn tại: {Path(png).name}"
                else:
                    icon, color, text = "error", "text-red-600", "Chưa có ảnh tên kênh"

                ui.icon(icon).classes(f"{color} shrink-0")
                ui.label("Ảnh tên kênh:").classes("text-xs text-gray-600 shrink-0")
                ui.label(text).classes(f"text-xs font-medium {color} truncate max-w-[240px]").tooltip(png or "")
                ui.button("Chọn PNG", icon="upload_file", on_click=pick_overlay).props("dense outline size=sm")
                if png:
                    ui.button(icon="close", on_click=clear_overlay).props("flat round dense size=sm color=grey").tooltip("Bỏ ảnh")
        ui_refs["refresh_overlay"] = refresh_overlay_display
        refresh_overlay_display()
        def on_random_change(e=None):
            if configuration_change_blocked():
                safe_element_call(
                    ui_refs.get("random_switch"),
                    "set_value",
                    options_state["random_music"],
                )
                return
            options_state["random_music"] = bool(e.value if e else False)

            save_state()
        def render_music_switch():
            random_switch = ui.switch("Nhạc ngẫu nhiên", value=options_state["random_music"], on_change=on_random_change).props("dense size=sm").classes("text-sm"); random_switch.tooltip("Bật: mỗi video lấy 1 nhạc ngẫu nhiên. Tắt: ghép lần lượt theo tên file.")
            ui_refs["random_switch"] = random_switch
        with ui.row().classes("w-full gap-3 flex-wrap items-stretch"):
            build_folder_selector("video_folder", "Folder video", "Chọn folder chứa video", "movie", on_after=load_videos)
            build_folder_selector("music_folder", "Folder nhạc", "Chọn folder chứa nhạc", "music_note", extra_render=render_music_switch)
            build_folder_selector("output_folder", "Folder output", "Chọn nơi lưu video đã ghép nhạc", "drive_folder_upload")
        def on_lang_change(e=None):
            if configuration_change_blocked():
                safe_element_call(
                    ui_refs.get("lang_input"),
                    "set_value",
                    options_state["audio_language"],
                )
                return
            options_state["audio_language"] = (lang_input.value or "").strip()
            save_state()

        with ui.row().classes("items-center gap-2 mt-2"):
            lang_input = (
                ui.input(
                    label="Ngôn ngữ audio track",
                    value=options_state["audio_language"],
                    on_change=on_lang_change,
                )
                .props('outlined dense placeholder="en"')
                .classes("w-64")
            )
            ui_refs["lang_input"] = lang_input
            ui.label("Mã ngôn ngữ của audio track thêm ở Bước 3 (vd: en, vi, ja).").classes("text-xs text-gray-500")

        with ui.row().classes("w-full gap-2 mt-3"):
            ui_refs["process_btn"] = ui.button("Xử lý", icon="play_arrow", on_click=handle_process).classes("app-button-primary flex-1")
            ui_refs["stop_btn"] = ui.button("Dừng", icon="stop", on_click=handle_stop).classes("app-button-secondary flex-1")
            ui_refs["stop_btn"].set_visibility(False)
            ui_refs["clear_btn"] = ui.button("Xóa dữ liệu", icon="delete_sweep", on_click=clear_all_inputs).classes("app-button-secondary flex-1")

        progress_panel = ui.card().classes("app-progress-panel w-full mt-2 gap-1 p-3")
        with progress_panel:
            with ui.row().classes("items-center gap-2 w-full flex-nowrap"):
                ui.spinner(size="sm", color="primary")
                progress_refs["current"] = ui.label("Đang chuẩn bị...").classes("text-sm font-medium text-blue-700")
            progress_refs["step"] = ui.label("").classes("text-xs text-gray-600")
            progress_refs["remaining"] = ui.label("").classes("text-xs text-gray-500")
            progress_refs["bar"] = ui.linear_progress(value=0).classes("w-full")
            progress_refs["log_area"] = ui.scroll_area().classes("w-full h-40 bg-white rounded border border-blue-100 mt-1")
            with progress_refs["log_area"]:
                progress_refs["log"] = ui.column().classes("w-full gap-0.5 p-1")
        progress_panel.set_visibility(False)
        progress_refs["panel"] = progress_panel

        with app_card():
            with section_header(
                "Hàng đợi video",
                "Theo dõi trạng thái của từng video trong toàn bộ quy trình.",
            ):
                pass
            video_list_container = ui.column().classes("w-full gap-1")
        refresh_video_list()

    load_state()
    state_sync_timer["value"] = ui.timer(1.0, sync_persisted_running_state)
