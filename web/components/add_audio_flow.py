# RECOVERED: partial depyo recovery; unresolved regions marked below
import asyncio, random, tempfile
from pathlib import Path
from loguru import logger
from nicegui import ui
from src.channel_store import channel_store
from src.module.audio_module import update_audio_module
from src.module.upload_video_module import upload_video_module
from src.state_manager import state_manager
from src.utils import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS, build_intermittent_audio, get_channels_info, get_video_duration, list_media_files, multiply_audio, mux_audio_into_video, normalize_path
from web.components.common import create_channel_selection, select_directory, select_file
from web.components.drawer import nav_state; STEP_STYLE = {"pending": ("schedule", "text-gray-400", "Chờ"), "processing": ("hourglass_top", "text-blue-600", "Đang xử lý"), "successful": ("check_circle", "text-green-600", "Xong"), "unsuccessful": ("error", "text-red-600", "Lỗi")}
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
    paths_state = {"video_folder": "", "music_folder": "", "output_folder": ""}; options_state = {"random_music": False, "audio_language": "en"}; selected_channel = {"id": None}; channels = get_channels_info(); videos_state = {"items": []}; saved_status_map = {}; video_list_container = None; suppress_autosave = {"value": False}; ui_refs = {"random_switch": None, "lang_input": None, "process_btn": None, "clear_btn": None, "refresh_channel_display": None, "refresh_overlay": None, "stop_btn": None}; folder_selectors = {}; progress_refs = {}; processing = {"value": False}; stop_requested = {"value": False}; PERSIST_FIELDS = ("music", "music_path", "audio_path", "output_path", "video_id", "scotty_resource_id", "frontend_upload_id")
    def save_state():
        try:
            if suppress_autosave["value"]:
                return None
            statuses = {}
            for it in videos_state["items"]:
                entry = {"steps": it["steps"]}
                for field in PERSIST_FIELDS:
                    entry[field] = it.get(field, "")
                statuses[it["name"]] = entry
            state_manager.save_state("add_audio_flow", {"video_folder": paths_state["video_folder"], "music_folder": paths_state["music_folder"], "output_folder": paths_state["output_folder"], "random_music": options_state["random_music"], "audio_language": options_state["audio_language"], "selected_channel": selected_channel["id"], "statuses": statuses})
        except Exception as e:
            logger.error(f"Failed to save add_audio_flow state: {e}")
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
            saved_status_map.clear()
            saved_status_map.update(state.get("statuses", {}))
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
                    "steps": {**_new_steps(), **(saved.get("steps") or {})},
                }
                for field in PERSIST_FIELDS:
                    item[field] = saved.get(field, "")
                for k in item["steps"]:
                    if item["steps"][k] == "processing":
                        item["steps"][k] = "pending"
                items.append(item)
        videos_state["items"] = items
        refresh_video_list()
        if items:
            ui.timer(0.05, load_durations, once=True)
    async def load_durations():
        for item in videos_state["items"]:
            if item["duration"] is None:
                try:
                    item["duration"] = await asyncio.to_thread(
                        get_video_duration, item["path"]
                    ) or 0
                except Exception:
                    item["duration"] = 0
                refresh_video_list()

    def step_badge(status: str):
        icon, color, label = STEP_STYLE.get(status, STEP_STYLE["pending"])
        with ui.row().classes("items-center justify-center gap-1 w-full flex-nowrap"):
            ui.icon(icon).classes(f"text-sm shrink-0 {color}")
            ui.label(label).classes(f"text-xs font-medium whitespace-nowrap {color}")
    def refresh_video_list():
        if not video_list_container:
            return
        video_list_container.clear()
        items = videos_state["items"]
        with video_list_container:
            with ui.row().classes("items-center gap-2 mb-1"):
                ui.icon("video_library").classes("text-gray-500")
                ui.label(f"Tìm thấy {len(items)} video").classes("text-sm font-semibold text-gray-700")
            if not items:
                ui.label("Chưa chọn folder video hoặc folder không có video nào.").classes("text-gray-500 italic text-sm")
                return

            with ui.row().classes("w-full items-center font-semibold text-xs text-gray-600 bg-gray-100 px-2 py-2 rounded flex-nowrap"):
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
                with ui.row().classes("w-full items-center bg-white rounded px-2 py-1 border-b border-gray-100 flex-nowrap"):
                    ui.label(str(idx)).classes("w-1/12 text-xs text-gray-500")
                    with ui.column().classes("w-3/12 min-w-0 gap-0"):
                        ui.label(item["name"]).classes("truncate text-sm font-medium text-gray-800").tooltip(item["name"])
                        meta = _human_size(item["size"])
                        if item["duration"] is None:
                            meta += " · đang đọc..."
                        else:
                            meta += f" · {_fmt_duration(item['duration'])}"
                        ui.label(meta).classes("text-xs text-gray-400")

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
    async def step_merge(item, output_folder, musics, index):
        """Render video với nhạc gián đoạn (phát 3s / tắt 7s, 3s cuối luôn có tiếng).

        Xuất 2 file: output_{i}.m4v (audio đã mute) và output_{i}_processed.mp4
        (video đã render với audio đó).
        """
        if options_state["random_music"]:
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

        channel = get_channels_info(selected_channel["id"])
        overlay_png = channel.overlay_png if channel else ""

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
    async def step_upload(item, output_folder, musics, index):
        """Upload video đã ghép nhạc lên kênh và tạo video.

        Chặng 1 (start) + chặng 2 (finalize) + chặng 3 (createvideo → videoId,
        set title/description). Title mặc định lấy từ tên file.
        """
        channel_id = selected_channel["id"]
        if not channel_id:
            raise Exception("Chưa chọn kênh")

        step_label = progress_refs.get("step")
        upload_prog = {"sent": 0, "total": 0}

        def _tick_upload():
            total = upload_prog.get("total", 0)
            if total > 0 and step_label:
                pct = int(upload_prog.get("sent", 0) * 100 / total)
                step_label.set_text(
                    f"Bước: Upload — {pct}% "
                    f"({upload_prog['sent'] / 1_000_000.0:.0f}/{total / 1_000_000.0:.0f} MB)"
                )

        prog_timer = ui.timer(0.5, _tick_upload)
        try:
            result = await asyncio.to_thread(upload_video_module.upload, channel_id=channel_id, file_path=item["output_path"], index=index, progress=upload_prog)
        finally:
            prog_timer.cancel()

        item["frontend_upload_id"] = result["frontend_upload_id"]
        item["scotty_resource_id"] = result["scotty_resource_id"]
        video_id = await asyncio.to_thread(
            upload_video_module.create_video,
            channel_id=channel_id,
            scotty_resource_id=result["scotty_resource_id"],
            frontend_upload_id=result["frontend_upload_id"],
            title=Path(item.get("music") or item["name"]).stem,
        )
        item["video_id"] = video_id
    async def step_wait_processed(item, output_folder, musics, index):
        """Chờ YouTube xử lý video xong (poll status = VIDEO_STATUS_PROCESSED)."""
        channel_id = selected_channel["id"]
        video_id = item.get("video_id")
        if not video_id:
            raise Exception("Chưa có video ID (upload chưa xong)")

        step_label = progress_refs.get("step")
        push_log("Chờ YouTube xử lý video xong...", "wait", indent=True)
        max_wait, interval, waited = 1200, 15, 0
        while True:
            if stop_requested["value"]:
                raise Exception("Đã dừng khi đang chờ video xử lý")
            ready = await asyncio.to_thread(upload_video_module.is_processed, channel_id, video_id)
            if ready:
                break
            if waited >= max_wait:
                raise Exception(f"Video chưa xử lý xong sau {max_wait}s (video_id={video_id})")
            if step_label:
                step_label.set_text(f"Bước: Chờ xử lý — {waited}s")
            await asyncio.sleep(interval)
            waited += interval
        push_log("Video đã xử lý xong", "ok", indent=True)
    async def step_add_audio(item, output_folder, musics, index):
        """Thêm audio track (file nhạc gốc) cho video_id đã xử lý xong.

        Add track cho từng ngôn ngữ (tách theo khoảng trắng).
        """
        channel_id = selected_channel["id"]
        video_id = item.get("video_id")
        if not video_id:
            raise Exception("Chưa có video ID (upload chưa xong)")

        audio_path = item.get("music_path")
        if not audio_path or not Path(audio_path).is_file():
            raise Exception(f"Không tìm thấy file nhạc gốc: {audio_path}")

        seen = set()
        languages = []
        for tok in (options_state.get("audio_language") or "en").split():
            if tok and tok not in seen:
                seen.add(tok)
                languages.append(tok)
        if not languages:
            languages = ["en"]

        step_label = progress_refs.get("step")
        if step_label:
            step_label.set_text("Bước: Add audio — chuẩn bị audio khớp thời lượng...")
        info = await asyncio.to_thread(
            upload_video_module._get_video_info,
            video_id=video_id,
            channel_id=channel_id,
        )
        video_dur = info.duration_ms / 1000.0 if info and info.duration_ms > 0 else None

        suffix = Path(audio_path).suffix or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
            matched_path = tf.name

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

            for lang in languages:
                if step_label:
                    step_label.set_text(f"Bước: Add audio — ngôn ngữ {lang}")
                status = await asyncio.to_thread(
                    update_audio_module.add,
                    id_video=video_id,
                    channel_id=channel_id,
                    file_name=audio_path,
                    language=lang,
                    data=data,
                )
                if status not in (200, 409):
                    raise Exception(f"Add audio ({lang}) thất bại: HTTP {status}")
                push_log(f"Đã thêm audio track: {lang}", "ok", indent=True)
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
        panel = progress_refs.get("panel")
        if panel:
            panel.set_visibility(active)
        if progress_refs.get("bar"):
            progress_refs["bar"].value = 0

        if progress_refs.get("current") and message:
            progress_refs["current"].set_text(message)
        if ui_refs.get("process_btn"):
            ui_refs["process_btn"].set_enabled(not active)

        if ui_refs.get("clear_btn"):
            ui_refs["clear_btn"].set_enabled(not active)
        if ui_refs.get("stop_btn"):
            ui_refs["stop_btn"].set_visibility(active)
            ui_refs["stop_btn"].set_enabled(active)
        if active:
            if progress_refs.get("log"):
                progress_refs["log"].clear()
                return None
            return None
    LOG_STYLE = {"info": ("chevron_right", "text-gray-600"), "work": ("autorenew", "text-blue-600"), "wait": ("hourglass_top", "text-amber-600"), "ok": ("check_circle", "text-green-600"), "error": ("error", "text-red-600")}
    def push_log(message: str, level: str="info", indent: bool=False):
        """Thêm 1 dòng progress thân thiện cho user (không lộ chi tiết kỹ thuật)."""
        log = progress_refs.get("log")
        if not log:
            return None
        icon, color = LOG_STYLE.get(level, LOG_STYLE["info"])

        with log:
            with ui.row().classes(f"items-center gap-1 w-full flex-nowrap {'pl-5' if indent else ''}"):
                ui.icon(icon).classes(f"text-sm shrink-0 {color}")
                ui.label(message).classes(f"text-xs {color} truncate")
        area = progress_refs.get("log_area")
        if area:
            area.scroll_to(percent=1.0)
            return None
    def handle_stop():
        if not processing["value"]:
            return None
        stop_requested["value"] = True

        if ui_refs.get("stop_btn"):
            ui_refs["stop_btn"].set_enabled(False)
        if progress_refs.get("step"):
            progress_refs["step"].set_text("Đang dừng sau khi xong bước hiện tại...")
        ui.notify("Sẽ dừng sau khi hoàn tất bước đang chạy", type="info")

    async def handle_process():
        if processing["value"]:
            ui.notify("Đang xử lý, vui lòng đợi hoàn tất", type="warning")
            return

        video_folder = normalize_path(paths_state["video_folder"])
        music_folder = normalize_path(paths_state["music_folder"])
        output_folder = normalize_path(paths_state["output_folder"])
        if not video_folder or not Path(video_folder).is_dir():
            ui.notify("Folder video không hợp lệ", type="warning")
            return
        if not music_folder or not Path(music_folder).is_dir():
            ui.notify("Folder nhạc không hợp lệ", type="warning")
            return
        if not output_folder:
            ui.notify("Vui lòng chọn folder output", type="warning")
            return
        if not selected_channel["id"]:
            ui.notify("Vui lòng chọn kênh để upload", type="warning")
            return

        items = videos_state["items"]
        if not items:
            ui.notify("Không có video nào để xử lý", type="warning")
            return
        musics = list_media_files(music_folder, AUDIO_EXTENSIONS)
        if not musics:
            ui.notify("Không tìm thấy file nhạc nào trong folder", type="warning")
            return
        try:
            Path(output_folder).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            ui.notify(f"Không tạo được folder output: {e}", type="negative")
            return

        pending_items = [
            (idx, it)
            for idx, it in enumerate(items)
            if not all(it["steps"][k] == "successful" for k, _, _ in STEP_SEQUENCE)
        ]
        if not pending_items:
            ui.notify("Tất cả video đã hoàn thành. Không có gì để chạy.", type="info")
            return

        current_label = progress_refs.get("current")
        step_label = progress_refs.get("step")
        remaining_label = progress_refs.get("remaining")
        progress_bar = progress_refs.get("bar")
        total = len(pending_items)
        errors = []
        stop_requested["value"] = False
        stopped = False
        set_processing_ui(True)
        push_log(f"Bắt đầu xử lý {total} video", "info")
        try:
            for v_index, (orig_index, item) in enumerate(pending_items, 1):
                if stop_requested["value"]:
                    stopped = True
                    break
                if current_label:
                    current_label.set_text(f"Video {v_index}/{total}: {item["name"]}")
                if remaining_label:
                    remaining_label.set_text(f"Còn lại: {total - v_index} video")
                push_log(f"Video {v_index}/{total}: {item['name']}", "work")
                item["steps"] = _new_steps()
                for field in PERSIST_FIELDS:
                    item[field] = ""
                refresh_video_list()
                for step_key, step_name, step_fn in STEP_SEQUENCE:
                    if stop_requested["value"]:
                        stopped = True
                        break
                    if step_label:
                        step_label.set_text(f"Bước: {step_name}")
                    push_log(f"{step_name}: đang xử lý...", "wait", indent=True)
                    item["steps"][step_key] = "processing"
                    refresh_video_list()
                    try:
                        await step_fn(item, output_folder, musics, orig_index)
                        item["steps"][step_key] = "successful"
                    except Exception as exc:
                        logger.error(f"Step '{step_key}' failed for {item['name']}: {exc}")
                        item["steps"][step_key] = "unsuccessful"
                        errors.append(f"{item['name']} [{step_name}]: {exc}")
                        push_log(f"{step_name}: thất bại", "error", indent=True)
                        refresh_video_list()
                        save_state()
                        break
                    done_msg = f"{step_name}: xong"
                    if step_key == "upload" and item.get("video_id"):
                        done_msg = f"{step_name}: xong (ID {item['video_id']})"
                    push_log(done_msg, "ok", indent=True)
                    refresh_video_list()
                    save_state()
                if stopped:
                    break
                if progress_bar:
                    progress_bar.value = v_index / total
        finally:
            set_processing_ui(False)
            save_state()

        if stopped:
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
            ui.notify(
                f"Đã dừng. {done_count}/{len(items)} video hoàn thành toàn bộ flow. Bấm Xử lý để chạy tiếp phần còn lại.",
                type="info",
            )
            return
        if errors:
            ui.notify(
                f"Hoàn tất với một số lỗi. {done_count}/{len(items)} video hoàn thành. Bấm Xử lý để thử lại phần lỗi.",
                type="warning",
            )
            return
        ui.notify(
            f"Hoàn tất! {done_count}/{len(items)} video đã xử lý xong toàn bộ flow.",
            type="positive",
        )
    def clear_all_inputs():
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
            save_state()
            ui.notify("Đã xóa tất cả input", type="info")
        finally:
            suppress_autosave["value"] = False

    if False:
        pass
    if False:
        pass

    def build_folder_selector(key: str, label: str, placeholder: str, icon: str, on_after=None, extra_render=None):
        def pick_folder(_=None):
            selected = select_directory(initial_dir=paths_state[key] or None, title=label)
            if selected:
                paths_state[key] = selected
                render()
                save_state()
                if on_after:
                    on_after()

        def clear_folder(_=None):
            paths_state[key] = ""
            render()
            save_state()
            if on_after:
                on_after()

        card = (
            ui.card()
            .classes("flex-1 min-w-[220px] h-full p-3 cursor-pointer transition hover:shadow-md hover:border-indigo-300 border border-gray-200 bg-gray-50")
            .on("click", pick_folder)
        )

        def render():
            path = paths_state[key]
            card.clear()

            with card:
                with ui.column().classes("w-full h-full justify-center"):
                    with ui.row().classes("items-center gap-3 w-full flex-nowrap"):
                        ui.icon(icon).classes("text-2xl shrink-0 " + ("text-indigo-500" if path else "text-gray-400"))
                        with ui.column().classes("gap-0 min-w-0 flex-1"):
                            ui.label(label).classes("text-xs font-semibold text-gray-500 uppercase tracking-wide")
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
    with ui.card().classes("w-full mx-auto mt-4 bg-white shadow-sm"):
        ui.label("Chọn kênh, folder video, folder nhạc và folder output rồi bấm Xử lý. Flow tự chạy: Ghép nhạc (phát 3s / tắt 7s, 3s cuối luôn có tiếng) → Upload → Add audio và cập nhật trạng thái từng bước trong bảng.").classes("text-sm text-gray-600 mb-2")
        def on_channel_select(channel_id):
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
            options_state["audio_language"] = (lang_input.value or "en").strip() or "en"
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
            ui_refs["process_btn"] = ui.button("Xử lý", icon="play_arrow", on_click=handle_process).classes("flex-1")
            ui_refs["stop_btn"] = ui.button("Dừng", icon="stop", on_click=handle_stop).props("color=orange").classes("flex-1")
            ui_refs["stop_btn"].set_visibility(False)
            ui_refs["clear_btn"] = ui.button("Xóa tất cả", icon="delete_sweep", on_click=clear_all_inputs).props("outline color=red").classes("flex-1")

        progress_panel = ui.card().classes("w-full mt-2 bg-blue-50 border border-blue-200 gap-1 p-3")
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

        ui.separator().classes("my-2")
        video_list_container = ui.column().classes("w-full gap-1")
        refresh_video_list()

    load_state()
