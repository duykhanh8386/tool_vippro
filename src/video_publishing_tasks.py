"""Durable sequential SEO/thumbnail/schedule jobs, shared across UI sessions."""
from __future__ import annotations

import copy
import re
import threading
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import requests
from loguru import logger
from selenium.common import exceptions as browser_errors
from urllib3.exceptions import HTTPError as TransportError

from src.module.base import YouTubeRequestError
from src.module.list_videos_module import list_videos_module
from src.module.video_publishing_module import video_publishing_module
from src.paths import get_data_dir
from src import gpt_service
from src.phoma_image_generator import IMAGE_MODELS, PhomaImageGenerator, parse_access_token
from src.publishing_browser import ChatGPTSessionNeedsAction, StudioThumbnailBrowser, YouTubeReferenceBrowser, download_reference_image, normalize_thumbnail
from src.state_manager import state_manager
from src.task_runtime import TaskStopped, bind_run_context, check_stopped, create_run_context
from src.utils import get_channels_info
from src.video_publishing import (
    COPYRIGHT_LABELS, PUBLISHING_SCAN_SCHEMA_VERSION, REFERENCE_SELECTION_VERSION, copyright_category, first_song,
    VIDEO_SCOPE_LABELS, VIDEO_TYPE_LABELS, has_schedule_info, plan_daily, positive_seconds,
    publishing_row_disabled_reason, publishing_row_matches, publishing_row_selectable,
    publishing_video_type, schedule_timestamp, thumbnail_file_stem,
)
from src.video_scan_dates import VIETNAM_TIMEZONE
from src.video_title_matching import parse_manual_title_ids

STATE_KEY = "video_publishing"
STATUS_LABELS = {"scanned": "Đã quét", "ready": "Đã tìm tham chiếu", "processing": "Đang xử lý", "successful": "Đã lên lịch",
                 "skipped": "Bỏ qua", "error": "Lỗi", "stopped": "Đã dừng", "waiting_session": "Chờ phiên ChatGPT"}
STEP_LABELS = {
    "scan": "Quét video", "check_schedules": "Kiểm tra lịch hiện có",
    "validate_video": "Kiểm tra video", "find_reference": "Tìm video tham chiếu",
    "image_session": "Kiểm tra phiên tạo ảnh", "prepare_image": "Chuẩn bị tệp ảnh",
    "download_reference": "Tải ảnh tham chiếu", "generate_image": "Tạo và tải ảnh GPT",
    "normalize_thumbnail": "Chuẩn hóa thumbnail", "upload_thumbnail": "Lưu thumbnail và danh sách phát",
    "assign_playlist": "Lưu danh sách phát", "copy_metadata": "Lưu title/description",
    "schedule_video": "Lưu lịch đăng", "process": "Xử lý video",
}


def default_settings():
    return {"channel_source": "selected", "channel_ids": [], "channel_links": "", "manual_ids": "", "categories": ["clear"], "scope": "unpublished",
            "scan_all": True, "limit": 100, "start_date": (datetime.now(VIETNAM_TIMEZONE).date() + timedelta(days=1)).isoformat(),
            "hour": "18:00", "order": "oldest", "image_prompt": "Vẽ lại thumbnail dựa trên ảnh tham chiếu, bố cục rõ ràng, chữ dễ đọc, phù hợp nội dung bài nhạc; tỷ lệ 16:9.",
            "output_folder": "", "image_model": "gpt-image-2", "image_cleanup": False}


class VideoPublishingController:
    def __init__(self, *, storage=None, module=None, listing=None, reference_factory=None, image_factory=None, thumbnail_factory=None):
        self.storage = storage or state_manager
        self.module = module or video_publishing_module
        self.listing = listing or list_videos_module
        self.reference_factory = reference_factory or YouTubeReferenceBrowser
        self.image_factory = image_factory or PhomaImageGenerator
        self.thumbnail_factory = thumbnail_factory or StudioThumbnailBrowser
        self.lock = threading.RLock()
        saved = self.storage.load_state(STATE_KEY) or {}
        self.settings = {**default_settings(), **saved.get("settings", {})}
        if "channel_source" not in saved.get("settings", {}):
            self.settings["channel_source"] = "links" if self.settings["channel_links"].strip() else "selected"
        # Credentials never belong in persistent state, even from an older file.
        self.settings.pop("cookie", None)
        self.settings.pop("session_text", None)
        self.rows = saved.get("rows", [])
        self.occupied = saved.get("occupied", {})
        for row in self.rows:
            if row.get("status") in {"processing", "waiting_session"}:
                row.update(status="stopped", detail="Phiên trước bị ngắt; tiếp tục để đọc lại kết quả thực tế.")
            if not publishing_row_selectable(row):
                row["selected"] = False
        self.message = saved.get("message", "Chọn kênh, quét trạng thái rồi tìm video tham chiếu.")
        if any(row.get("classification_version") != PUBLISHING_SCAN_SCHEMA_VERSION for row in self.rows):
            self.message = "Danh sách cũ chưa được kiểm tra bằng cách nhận diện bản nháp mới. Quét lại một lần để cập nhật đúng loại video."
        self.session_text = ""
        self.image_session = None
        self.session_busy = False
        self.chatgpt_status = "Chưa kiểm tra phiên ChatGPT."
        self.busy = False
        self.revision = 0
        self.run = self.thread = None

    def _save(self):
        if not self.storage.save_state(STATE_KEY, {"settings": self.settings, "rows": self.rows,
                                                   "occupied": self.occupied, "message": self.message}):
            raise ValueError("Không lưu được tiến độ; đã dừng trước bước tiếp theo.")

    def snapshot(self):
        with self.lock:
            return copy.deepcopy({"settings": self.settings, "rows": self.rows, "message": self.message,
                                  "busy": self.busy, "revision": self.revision, "has_session": bool(self.session_text),
                                  "session_busy": self.session_busy, "chatgpt_status": self.chatgpt_status,
                                  "needs_rescan": any(row.get("classification_version") != PUBLISHING_SCAN_SCHEMA_VERSION for row in self.rows)})

    def set_session(self, text):
        with self.lock:
            if self.busy or self.session_busy:
                raise ValueError("Chờ tác vụ kết thúc trước khi thay session.")
            if text.strip():
                parse_access_token(text)
            self.session_text = text
            if self.image_session is not None:
                self.image_session.update_session(text)
            self.chatgpt_status = "Đã nhận session; bấm Kiểm tra tài khoản để lưu và xác nhận." if text.strip() else "Dùng tài khoản GPT đã chọn và lưu trên máy."

    def _image_session(self):
        with self.lock:
            if self.image_session is None:
                self.image_session = self.image_factory(self.session_text)
            return self.image_session

    def gpt_account_action(self, action, **arguments):
        if action not in {"accounts", "select", "remove", "replace", "rename"}:
            raise ValueError("Thao tác tài khoản GPT không hợp lệ.")
        with self.lock:
            if self.busy or self.session_busy:
                raise ValueError("Dừng tác vụ trước khi thay tài khoản GPT.")
            self.session_busy = True
        try:
            result = gpt_service.call(action, **arguments)
            if action != "accounts":
                with self.lock:
                    self.session_text = ""
                    if self.image_session is not None:
                        self.image_session.close()
                    self.image_session = None
                    self.chatgpt_status = "Đã cập nhật tài khoản GPT; kiểm tra trước khi chạy."
            return result
        finally:
            with self.lock:
                self.session_busy = False

    def _session_progress(self, message):
        with self.lock:
            self.chatgpt_status = message

    def _image_session_state(self, row, state, message):
        self._session_progress(message)
        self._checkpoint(row, status="processing" if state == "ready" else "waiting_session",
                         detail="Phiên ChatGPT sẵn sàng; đang tiếp tục xử lý thumbnail…" if state == "ready" else message)

    def _image_progress(self, row, message):
        self._session_progress(message)
        self._checkpoint(row, status="processing", detail=message)

    def prepare_chatgpt_session(self):
        with self.lock:
            if self.busy or self.session_busy:
                raise ValueError("Chờ tác vụ hiện tại kết thúc trước khi kiểm tra phiên ChatGPT.")
            self.session_busy = True
        try:
            self._image_session().ensure_ready(on_status=self._session_progress)
            with self.lock:
                self.session_text = ""
            self._session_progress("Phiên ChatGPT đã đăng nhập và sẵn sàng.")
        except ChatGPTSessionNeedsAction as exc:
            self._session_progress(str(exc))
            raise
        finally:
            with self.lock:
                self.session_busy = False

    def close_chatgpt_session(self):
        with self.lock:
            if self.busy or self.session_busy:
                raise ValueError("Dừng tác vụ trước khi bỏ phiên xử lý GPT.")
            self.session_busy = True
        try:
            if self.image_session is not None:
                self.image_session.close()
            self._session_progress("Đã bỏ phiên xử lý hiện tại; tài khoản GPT vẫn được lưu trên máy.")
        finally:
            with self.lock:
                self.session_busy = False

    def change_settings(self, **changes):
        with self.lock:
            if self.busy or self.session_busy:
                raise ValueError("Dừng tác vụ trước khi thay thiết lập.")
            if any(key not in default_settings() for key in changes):
                raise ValueError("Thiết lập không hợp lệ.")
            changed = {key for key, value in changes.items() if self.settings.get(key) != value}
            if not changed:
                return
            if changed & {"start_date", "hour"} and any(row.get("thumbnail_uploaded") and row.get("status") != "successful" for row in self.rows):
                raise ValueError("Có video đang chờ xác nhận lịch. Tiếp tục xử lý hoặc quét lại trước khi đổi ngày giờ.")
            if "limit" in changes:
                try:
                    value = float(changes["limit"])
                    if not value.is_integer() or not 1 <= value <= 10000:
                        raise ValueError()
                    changes["limit"] = int(value)
                except (ValueError, TypeError, OverflowError):
                    raise ValueError("Số video mỗi kênh phải là số nguyên từ 1 đến 10000.") from None
            if "scope" in changes and changes["scope"] not in VIDEO_SCOPE_LABELS:
                raise ValueError("Phạm vi quét không hợp lệ.")
            if "channel_source" in changes and changes["channel_source"] not in {"selected", "links"}:
                raise ValueError("Chọn nguồn kênh từ thẻ đã chọn hoặc từ link.")
            if "categories" in changes and (not isinstance(changes["categories"], list) or not set(changes["categories"]) <= set(COPYRIGHT_LABELS)):
                raise ValueError("Bộ lọc bản quyền không hợp lệ.")
            if "order" in changes and changes["order"] not in {"oldest", "newest"}:
                raise ValueError("Thứ tự đăng không hợp lệ.")
            if "image_model" in changes and changes["image_model"] not in IMAGE_MODELS:
                raise ValueError("Model tạo ảnh không hợp lệ.")
            if "image_cleanup" in changes and not isinstance(changes["image_cleanup"], bool):
                raise ValueError("Tùy chọn ẩn hội thoại không hợp lệ.")
            self.settings.update(changes)
            if changed & {"channel_source", "channel_ids", "channel_links", "manual_ids", "scan_all", "limit", "order"}:
                self.rows = []
                self.occupied = {}
                self.message = "Phạm vi đã đổi. Quét lại video."
            elif changed & {"categories", "scope"}:
                self.message = "Đã đổi bộ lọc hiển thị; các video đã chọn được giữ nguyên."
            elif changed & {"start_date", "hour"}:
                for row in self.rows:
                    if row.get("status") != "successful":
                        row.pop("publish_at", None)
                        row.pop("publish_label", None)
            elif changed & {"image_prompt", "image_model"}:
                for row in self.rows:
                    if row.get("status") != "successful" and not row.get("thumbnail_uploaded"):
                        row.pop("thumbnail_path", None)
                        row.pop("conversation_url", None)
                        row.pop("image_request", None)
            self.revision += 1
            self._save()

    def reset_images(self):
        with self.lock:
            if self.busy or self.session_busy:
                raise ValueError("Dừng tác vụ trước khi tạo lại ảnh.")
            for row in self.rows:
                if row.get("selected") and publishing_row_selectable(row) and not row.get("thumbnail_uploaded"):
                    for key in ("thumbnail_path", "conversation_url", "image_request"):
                        row.pop(key, None)
                    row.update(status="scanned", detail="Sẽ gửi yêu cầu tạo ảnh mới bằng phoma.")
            self._checkpoint()

    def select(self, video_ids, *, within_ids=None):
        with self.lock:
            if self.busy:
                return
            selected = set(video_ids)
            within = set(within_ids) if within_ids is not None else None
            for row in self.rows:
                if within is None or row["video_id"] in within:
                    row["selected"] = row["video_id"] in selected and publishing_row_selectable(row)
            self.revision += 1
            self._save()

    def select_filtered(self, *, selected=True):
        with self.lock:
            visible = [row for row in self.rows if publishing_row_matches(row, scope=self.settings["scope"], categories=self.settings["categories"])]
            self.select((row["video_id"] for row in visible if selected), within_ids=[row["video_id"] for row in visible])

    def set_song(self, video_id, query):
        with self.lock:
            if self.busy:
                raise ValueError("Dừng tác vụ trước khi đổi bài nhạc tìm kiếm.")
            row = next((item for item in self.rows if item["video_id"] == video_id), None)
            if not row or row["status"] in {"skipped", "successful"} or row.get("metadata_copied") or row.get("thumbnail_uploaded"):
                raise ValueError("Chỉ sửa bài nhạc cho dòng chưa cập nhật lên YouTube.")
            query = str(query or "").strip()
            if not query:
                raise ValueError("Tên bài nhạc tìm kiếm không được để trống.")
            if query != row["song"]:
                row.update(song=query, status="scanned", detail="Đã đổi từ khóa; sẽ tìm lại video tham chiếu.")
                for key in ("reference", "conversation_url", "thumbnail_path", "image_request"):
                    row.pop(key, None)
                self._checkpoint()

    def _checkpoint(self, row=None, **changes):
        check_stopped()
        with self.lock:
            if row is not None:
                row.update(changes)
            self.revision += 1
            self._save()

    def _remember_conversation(self, row, url):
        # A Stop may arrive immediately after ChatGPT accepts a prompt. Saving
        # this local receipt must still succeed so a retry resumes that request.
        with self.lock:
            row["conversation_url"] = url
            self.revision += 1
            self._save()

    def _remember_image_request(self, row, request):
        with self.lock:
            row["image_request"] = copy.deepcopy(request)
            if request.get("conversation_url"):
                row["conversation_url"] = request["conversation_url"]
            self.revision += 1
            self._save()

    def _remember_thumbnail_saved(self, row):
        with self.lock:
            row["thumbnail_uploaded"] = True
            self.revision += 1
            self._save()

    def _progress(self, message):
        with self.lock:
            self.message = message

    def plan(self):
        with self.lock:
            if self.busy:
                raise ValueError("Chờ tác vụ kết thúc để xem lịch.")
            self._assign_plan()

    def _assign_plan(self):
        plan = plan_daily(self.rows, self.settings["start_date"], self.settings["hour"], occupied=self.occupied)
        by_id = {(row["channel_id"], row["video_id"]): row for row in self.rows}
        for slot in plan:
            by_id[slot["channel_id"], slot["video_id"]].update(slot)
        self._checkpoint()
        return plan

    def start(self, action):
        if action not in {"scan", "references", "run"}:
            raise ValueError("Tác vụ không hợp lệ.")
        with self.lock:
            if self.busy or self.session_busy:
                raise ValueError("Tác vụ đang chạy.")
            if action == "scan":
                if self.settings["channel_source"] == "links" and not self.settings["channel_links"].strip():
                    raise ValueError("Đang chọn nguồn Link kênh. Dán link kênh trước khi quét.")
                if self.settings["channel_source"] == "selected" and not self.settings["channel_ids"]:
                    raise ValueError("Đang chọn nguồn Kênh đã chọn. Chọn ít nhất một thẻ kênh trước khi quét.")
                if self.settings["manual_ids"].strip():
                    parse_manual_title_ids(self.settings["manual_ids"])
            else:
                if not any(row.get("selected") and publishing_row_selectable(row) for row in self.rows):
                    raise ValueError("Chọn ít nhất một video hợp lệ trong bảng.")
                if action == "run":
                    if not self.settings["image_prompt"].strip():
                        raise ValueError("Nhập prompt chung để vẽ thumbnail.")
                    if self.session_text.strip():
                        parse_access_token(self.session_text)
                    self._assign_plan()
            self.busy = True
            self.revision += 1
            self.run = create_run_context("video_publishing")
            self.thread = threading.Thread(target=self._worker, args=(action, self.run), daemon=True, name="video-publishing")
            self.thread.start()

    def stop(self):
        with self.lock:
            run = self.run
            self.message = "Đang dừng; tiến độ đã lưu sẽ được dùng khi tiếp tục."
        if run:
            run.request_stop()

    @staticmethod
    def _error(exc, *, step=None):
        if isinstance(exc, (ValueError, YouTubeRequestError)):
            detail = str(exc)
        else:
            if isinstance(exc, (browser_errors.InvalidSessionIdException, browser_errors.NoSuchWindowException)):
                reason = "Mất phiên hoặc cửa sổ Chrome đang xử lý. Mở lại tác vụ để tiếp tục từ tiến độ đã lưu."
            elif isinstance(exc, browser_errors.SessionNotCreatedException):
                reason = "Không khởi tạo được Chrome. Kiểm tra phiên bản Chrome và ChromeDriver."
            elif isinstance(exc, browser_errors.TimeoutException):
                reason = "Chrome chưa tải xong trang hoặc chưa phản hồi trong thời gian chờ."
            elif isinstance(exc, (browser_errors.ElementClickInterceptedException, browser_errors.ElementNotInteractableException,
                                  browser_errors.NoSuchElementException, browser_errors.StaleElementReferenceException)):
                reason = "Chưa thao tác được điều khiển trên trang; kiểm tra hộp thoại đang mở trong Chrome rồi tiếp tục."
            elif isinstance(exc, browser_errors.WebDriverException):
                reason = "Chrome không thực hiện được lệnh ở bước này. Kiểm tra cửa sổ và phiên trình duyệt."
            elif isinstance(exc, (requests.Timeout, TimeoutError)):
                reason = "Kết nối hết thời gian chờ. Kiểm tra mạng rồi tiếp tục để đọc lại kết quả."
            elif isinstance(exc, (requests.RequestException, TransportError, ConnectionError)):
                reason = "Không nhận được phản hồi qua kết nối. Kiểm tra mạng rồi tiếp tục để đọc lại kết quả."
            elif isinstance(exc, FileNotFoundError):
                reason = "Không tìm thấy tệp cần dùng ở bước này. Kiểm tra thư mục ảnh và các công cụ đã cài."
            elif isinstance(exc, PermissionError):
                reason = "Không có quyền đọc hoặc ghi tệp. Kiểm tra quyền truy cập thư mục ảnh."
            elif isinstance(exc, OSError):
                reason = "Không đọc hoặc ghi được tệp ở bước này. Kiểm tra thư mục ảnh và dung lượng ổ đĩa."
            else:
                reason = "Lỗi xử lý nội bộ. Tiến độ được giữ; gửi mã lỗi và bước này để kiểm tra."
            # Browser/transport exception messages may contain URLs or tokens.
            # Expose their type, never their raw message or request arguments.
            detail = f"{reason} ({type(exc).__name__})"
        return f"{STEP_LABELS.get(step, 'Xử lý video')}: {detail}" if step else detail

    @staticmethod
    def _log_error(exc, *, step, row=None):
        # Keep useful source locations without exception text, source lines,
        # local variables, credential-bearing request URLs or absolute paths.
        chain, seen, current = [], set(), exc
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            frames = traceback.extract_tb(current.__traceback__)
            locations = " > ".join(f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}" for frame in frames)
            chain.append(f"{type(current).__name__}[{locations}]")
            current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
        logger.error("Publishing failed: channel={} video={} step={} type={} stack={}",
                     row.get("channel_id", "") if row else "", row.get("video_id", "") if row else "",
                     step, type(exc).__name__, " | caused by ".join(chain))

    def _scan(self, settings, reference):
        channels = list(settings["channel_ids"])
        if settings["channel_source"] == "links":
            channels = reference.resolve_channels(settings["channel_links"])
        connected = {channel.id for channel in get_channels_info() or []}
        if not channels or any(channel not in connected for channel in channels):
            raise ValueError("Link kênh phải là kênh đã đăng nhập trong mục Tài khoản & kênh.")
        manual = parse_manual_title_ids(settings["manual_ids"]) if settings["manual_ids"].strip() else []
        manual_set = set(manual)
        rows, occupied = [], {}
        for channel_id in dict.fromkeys(channels):
            self._progress(f"Đang quét kênh {channel_id}…")
            seen, tokens, videos = {}, set(), []
            # Include explicit draft listing; not every Studio account returns
            # drafts in the unfiltered list. Always read every page for occupancy.
            for draft_only in (False, True):
                token = None
                tokens.clear()
                while True:
                    check_stopped()
                    page, next_token = self.listing.list_all_videos(channel_id, limit=100, page_token=token, draft_only=draft_only)
                    for video in page:
                        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video.id) or video.channel_id != channel_id:
                            raise ValueError("YouTube trả về video không thuộc kênh đang quét.")
                        if video.id not in seen:
                            seen[video.id] = video
                            videos.append(video)
                        elif draft_only:
                            # Draft-specific responses may supply draftStatus
                            # missing in the broad list. Merge that evidence;
                            # dropping duplicates here used to lose draft rows.
                            previous = seen[video.id]
                            if video.draft_status is not None and video.draft_status != "" and video.draft_status != {}:
                                previous.draft_status = copy.deepcopy(video.draft_status)
                            if video.privacy:
                                previous.privacy = video.privacy
                    self._progress(f"Kênh {channel_id} · đã đọc {len(videos)} video…")
                    if not next_token:
                        break
                    if next_token in tokens:
                        raise ValueError("YouTube trả về phân trang lặp; đã dừng quét.")
                    tokens.add(next_token)
                    token = next_token
            videos = [self._resolve_schedule(video) for video in videos]
            occupied[channel_id] = [stamp for video in videos if (stamp := schedule_timestamp(video))]
            if manual:
                videos = [video for video in videos if video.id in manual_set]
                videos.sort(key=lambda video: manual.index(video.id))
            else:
                from src.video_scan_dates import _timestamp

                videos.sort(key=lambda video: _timestamp(video.time_created_seconds) or 0, reverse=settings["order"] == "newest")
            if not manual and not settings["scan_all"]:
                videos = videos[:int(settings["limit"])]
            for video in videos:
                category = copyright_category(video)
                kind = publishing_video_type(video)
                row = {"video_id": video.id, "channel_id": channel_id, "old_title": video.title,
                       "old_description": video.description, "song": first_song(video.title, video.description),
                       "duration_seconds": (positive_seconds(video.duration_ms) or 0) / 1000,
                       "copyright": category, "copyright_label": COPYRIGHT_LABELS[category],
                       "classification_version": PUBLISHING_SCAN_SCHEMA_VERSION, "draft_status": copy.deepcopy(video.draft_status),
                       "visibility_type": kind, "visibility_label": VIDEO_TYPE_LABELS[kind], "selected": False, "status": "scanned"}
                if stamp := schedule_timestamp(video):
                    row.update(publish_at=int(stamp),publish_label=datetime.fromtimestamp(stamp,VIETNAM_TIMEZONE).strftime("%d/%m/%Y %H:%M"))
                reason = publishing_row_disabled_reason(row)
                row.update(availability_reason=reason, status="skipped" if reason else "scanned",
                           detail=reason or "Tích chọn dòng này hoặc chọn hàng loạt theo bộ lọc để xử lý.")
                rows.append(row)
        if manual:
            found = {row["video_id"] for row in rows}
            missing = manual_set - found
            if missing:
                raise ValueError("Không tìm thấy Video ID trong các kênh đã chọn: " + ", ".join(sorted(missing)))
        with self.lock:
            self.rows, self.occupied = rows, occupied
            self.message = f"Đã quét {len(rows)} video · {sum(publishing_row_selectable(row) for row in rows)} có thể chọn lên lịch. Lọc loại video bên dưới rồi tích chọn."
            self._checkpoint()

    def _process(self, settings, reference, image, action):
        selected = [row for row in self.rows if row.get("selected") and publishing_row_selectable(row)]
        thumbnail = self.thumbnail_factory() if action == "run" else None
        output = Path(settings["output_folder"]).expanduser() if settings["output_folder"].strip() else get_data_dir() / "publishing_thumbnails"
        for index, row in enumerate(selected, 1):
            check_stopped()
            self._progress(f"{index}/{len(selected)} · {row['channel_id']} · {row['video_id']}")
            self._checkpoint(row, status="processing", step="validate_video", error_step="", error_type="",
                             detail="Đang kiểm tra video và tìm tham chiếu…")
            try:
                # Scan categories remain a display filter. Later copyright
                # changes must not cancel an explicitly selected video.
                categories = [row["copyright"]]
                current = self.module.require_eligible(row["channel_id"], row["video_id"], categories, publish_at=row.get("publish_at"))
                duration_ms = positive_seconds(getattr(current, "duration_ms", None))
                if duration_ms is not None:
                    self._checkpoint(row, duration_seconds=duration_ms / 1000)
                previous = row.get("reference") or {}
                # Re-evaluate old previews using the new priority order. Keep a
                # source stable once remote metadata/thumbnail updates began.
                stale_selection = previous.get("selection_version") != REFERENCE_SELECTION_VERSION or (
                    previous.get("selection") != "id" and previous.get("target_duration_seconds") != positive_seconds(row.get("duration_seconds")))
                replace_preview = stale_selection and not (row.get("metadata_copied") or row.get("thumbnail_uploaded"))
                if not previous or replace_preview:
                    self._checkpoint(row, step="find_reference", detail="Đang tìm video tham chiếu…")
                    found = reference.find(row["song"], source_title=row["old_title"], duration_seconds=row.get("duration_seconds"),
                                           exclude_ids=[entry["video_id"] for entry in self.rows])
                    if previous and any(found.get(key) != previous.get(key) for key in ("video_id", "title", "description", "thumbnail")):
                        with self.lock:
                            row.pop("thumbnail_path", None)
                            row.pop("conversation_url", None)
                            row.pop("image_request", None)
                    self._checkpoint(row, reference=found)
                if action == "references":
                    method = row["reference"].get("selection_label", "Đã tìm video tham chiếu")
                    self._checkpoint(row, status="ready", detail=method + "; title và description sẽ chép nguyên văn.")
                    continue
                if not row.get("thumbnail_path") or not Path(row["thumbnail_path"]).is_file():
                    self._checkpoint(row, step="image_session", detail="Đang kiểm tra phiên tạo ảnh…")
                    if image is None:
                        image = self._image_session()
                    image.ensure_ready(wait_for_user=True, allow_image_result=True,
                                       on_state=lambda state, message, row=row: self._image_session_state(row, state, message))
                    self._checkpoint(row, step="prepare_image", detail="Đang chuẩn bị thư mục và tệp ảnh…")
                    folder = output / row["channel_id"]
                    folder.mkdir(parents=True, exist_ok=True)
                    base = str(folder / thumbnail_file_stem(row["reference"]["title"], row["video_id"]))
                    reference_path = base + ".reference.jpg"
                    if not row.get("conversation_url") and not row.get("image_request"):
                        self._checkpoint(row, step="download_reference", detail="Đang tải ảnh tham chiếu và chuyển sang JPEG…")
                        reference_path = download_reference_image(row["reference"]["thumbnail"], reference_path)
                    self._checkpoint(row, step="generate_image", detail="Đang yêu cầu ChatGPT vẽ lại thumbnail…")
                    raw = image.generate(reference_path, settings["image_prompt"], row["reference"], base + ".generated",
                                         conversation_url=row.get("conversation_url", ""),
                                         video_id=row["video_id"], request=row.get("image_request"),
                                         on_request=lambda request, row=row: self._remember_image_request(row, request),
                                         on_conversation=lambda url, row=row: self._remember_conversation(row, url),
                                         on_state=lambda state, message, row=row: self._image_session_state(row, state, message),
                                         on_progress=lambda message, row=row: self._image_progress(row, message),
                                         model=settings["image_model"], cleanup=settings["image_cleanup"])
                    self._checkpoint(row, step="normalize_thumbnail", detail="Đã tải ảnh ChatGPT; đang chuẩn hóa thumbnail JPEG 1280×720…")
                    path = normalize_thumbnail(raw, base + ".jpg")
                    self._checkpoint(row, thumbnail_path=path)
                if not row.get("thumbnail_uploaded"):
                    self._checkpoint(row, step="upload_thumbnail", detail="Đang tải thumbnail và đọc lại ảnh đã lưu trên YouTube…")
                    self.module.require_eligible(row["channel_id"], row["video_id"], categories, publish_at=row["publish_at"])
                    playlist = thumbnail.upload(row["channel_id"], row["video_id"], row["thumbnail_path"], ensure_playlist=True,
                                                on_saved=lambda row=row:self._remember_thumbnail_saved(row))
                    self._checkpoint(row, thumbnail_uploaded=True)
                elif not row.get("playlist_assigned"):
                    self._checkpoint(row, step="assign_playlist", detail="Đang chọn và lưu danh sách phát đầu tiên…")
                    playlist = thumbnail.assign_first_playlist(row["channel_id"],row["video_id"])
                else:
                    playlist = None
                if not row.get("playlist_assigned"):
                    if not isinstance(playlist,dict) or not playlist.get("playlist_id"):
                        raise ValueError("Chưa xác nhận được danh sách phát đầu tiên; chưa đặt lịch video này.")
                    self._checkpoint(row,playlist_assigned=True,**playlist)
                self._checkpoint(row, step="copy_metadata", detail="Đã xác nhận thumbnail và danh sách phát. Đang chép title/description…")
                self.module.copy_metadata(row["channel_id"], row["video_id"], row["reference"],
                                          expected_title=row["old_title"], expected_description=row["old_description"],
                                          categories=categories, publish_at=row["publish_at"])
                self._checkpoint(row, metadata_copied=True)
                self._checkpoint(row, step="schedule_video", detail="Đang đặt lịch và đọc lại kết quả…")
                self.module.schedule(row["channel_id"], row["video_id"], row["publish_at"], row["reference"], categories=categories)
                self._checkpoint(row, status="successful", selected=False, detail="Đã xác nhận metadata và lịch đăng trên YouTube.")
            except ChatGPTSessionNeedsAction as exc:
                self._session_progress(str(exc))
                self._checkpoint(row, status="waiting_session", detail=str(exc))
                raise
            except TaskStopped:
                raise
            except Exception as exc:
                step = row["step"]
                self._log_error(exc, step=step, row=row)
                self._checkpoint(row, status="error", error_step=step, error_type=type(exc).__name__, detail=self._error(exc, step=step))
                if isinstance(exc, YouTubeRequestError) and exc.status_code in {401, 403}:
                    raise
        successes = sum(row["status"] == "successful" for row in self.rows)
        failed = sum(row["status"] == "error" for row in self.rows)
        self._progress(f"Hoàn tất lượt xử lý · {successes} đã lên lịch · {failed} lỗi." if action == "run" else f"Đã tìm tham chiếu · {failed} lỗi. Kiểm tra bảng trước khi chạy.")

    def _check_schedule_conflicts(self):
        """Detect schedules added since the preview before any remote mutation."""
        selected = [row for row in self.rows if row.get("selected") and row.get("publish_at")]
        occupied = copy.deepcopy(self.occupied)
        remote_pending = {}
        for channel_id in dict.fromkeys(row["channel_id"] for row in selected):
            self._progress(f"Đang kiểm tra lại lịch hiện có trên kênh {channel_id}…")
            token, tokens, seen = None, set(), {}
            while True:
                page, next_token = self.listing.list_all_videos(channel_id, limit=100, page_token=token)
                for video in page:
                    if video.channel_id != channel_id:
                        raise ValueError("YouTube trả về lịch của kênh khác.")
                    seen[video.id] = self._resolve_schedule(video)
                if not next_token:
                    break
                if next_token in tokens:
                    raise ValueError("YouTube trả về phân trang lịch bị lặp.")
                tokens.add(next_token)
                token = next_token
            for row in [item for item in selected if item["channel_id"] == channel_id]:
                current = self.module.read_video(channel_id, row["video_id"])
                if current.id != row["video_id"] or current.channel_id != channel_id:
                    raise ValueError("Video đọc lại không thuộc đúng kênh; chưa đặt lịch.")
                current = self._resolve_schedule(current)
                seen[current.id] = current
                kind = publishing_video_type(current)
                stamp = schedule_timestamp(current)
                if kind in {"scheduled", "public"}:
                    changes = dict(selected=False, visibility_type=kind, visibility_label=VIDEO_TYPE_LABELS[kind], status="skipped",
                                   availability_reason="Video đã có lịch đăng; giữ lịch hiện tại." if kind=="scheduled" else "Video đã công khai; giữ trạng thái hiện tại.",
                                   detail="Đã đọc lại trạng thái trên YouTube; không đặt lại lịch video này.")
                    if stamp:
                        changes.update(publish_at=int(stamp),publish_label=datetime.fromtimestamp(stamp,VIETNAM_TIMEZONE).strftime("%d/%m/%Y %H:%M"))
                    self._checkpoint(row,**changes)
                elif stamp:
                    remote_pending[row["video_id"]] = int(stamp)
            occupied[channel_id] = [stamp for video in seen.values() if (stamp:=schedule_timestamp(video))]
        with self.lock:
            self.occupied = occupied
            for row in selected:
                if row.get("selected"):
                    row.pop("publish_at",None)
                    row.pop("publish_label",None)
                    if row["video_id"] in remote_pending:
                        row["publish_at"] = remote_pending[row["video_id"]]
            self._assign_plan()

    def _resolve_schedule(self, video):
        if not has_schedule_info(video) or schedule_timestamp(video) is not None:
            return video
        current = self.module.read_video(video.channel_id, video.id)
        if current.id != video.id or current.channel_id != video.channel_id:
            raise ValueError("Video đọc lại không thuộc đúng kênh; chưa xác nhận lịch.")
        if has_schedule_info(current) and schedule_timestamp(current) is None:
            raise ValueError("Video " + video.id + " có thông tin lịch nhưng chưa đọc được ngày giờ sau khi tải lại từ Studio; chưa đặt thêm lịch cho kênh này.")
        return current

    def _worker(self, action, run):
        reference = image = None
        step = "scan" if action == "scan" else "process"
        try:
            with bind_run_context(run):
                settings = copy.deepcopy(self.settings)
                reference = self.reference_factory()
                if action == "scan":
                    self._scan(settings, reference)
                else:
                    if action == "run":
                        step = "check_schedules"
                        self._check_schedule_conflicts()
                    step = "process"
                    self._process(settings, reference, image, action)
        except ChatGPTSessionNeedsAction as exc:
            self._session_progress(str(exc))
            self._progress("Đã dừng lượt xử lý để khôi phục phiên ChatGPT. " + str(exc))
        except TaskStopped:
            self._progress("Đã dừng; có thể tiếp tục các dòng chưa xong.")
        except Exception as exc:
            self._log_error(exc, step=step)
            self._progress(self._error(exc, step=step))
        finally:
            # The image adapter is app-owned; only per-run reference browsers close.
            for adapter in (reference,):
                if adapter:
                    try:
                        adapter.close()
                    except Exception:
                        pass
            with self.lock:
                for row in self.rows:
                    if row["status"] == "processing" or (run.stopped and row["status"] == "waiting_session"):
                        row.update(status="stopped", detail="Tiếp tục để đọc lại kết quả đã gửi.")
                self.busy, self.run = False, None
                self.revision += 1
                try:
                    self._save()
                except ValueError as exc:
                    self.message = str(exc)
            run.cleanup()


_controller = None
_controller_lock = threading.Lock()


def get_video_publishing_controller():
    global _controller
    with _controller_lock:
        if _controller is None:
            _controller = VideoPublishingController()
        return _controller
