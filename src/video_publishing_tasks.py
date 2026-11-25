"""Durable sequential SEO/thumbnail/schedule jobs, shared across UI sessions."""
from __future__ import annotations

import copy
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path

from src.module.base import YouTubeRequestError
from src.module.list_videos_module import list_videos_module
from src.module.video_publishing_module import video_publishing_module
from src.paths import get_data_dir
from src.publishing_browser import ChatGPTImageBrowser, ChatGPTSessionNeedsAction, StudioThumbnailBrowser, YouTubeReferenceBrowser, download_reference_image, normalize_thumbnail
from src.state_manager import state_manager
from src.task_runtime import TaskStopped, bind_run_context, check_stopped, create_run_context
from src.utils import get_channels_info
from src.video_publishing import (
    COPYRIGHT_LABELS, PUBLISHING_SCAN_SCHEMA_VERSION, REFERENCE_SELECTION_VERSION, copyright_category, first_song,
    VIDEO_SCOPE_LABELS, VIDEO_TYPE_LABELS, parse_chatgpt_cookies, plan_daily, positive_seconds,
    publishing_row_disabled_reason, publishing_row_matches, publishing_row_selectable,
    publishing_video_type, schedule_timestamp,
)
from src.video_scan_dates import VIETNAM_TIMEZONE
from src.video_title_matching import parse_manual_title_ids

STATE_KEY = "video_publishing"
STATUS_LABELS = {"scanned": "Đã quét", "ready": "Đã tìm tham chiếu", "processing": "Đang xử lý", "successful": "Đã lên lịch",
                 "skipped": "Bỏ qua", "error": "Lỗi", "stopped": "Đã dừng", "waiting_session": "Chờ phiên ChatGPT"}


def default_settings():
    return {"channel_source": "selected", "channel_ids": [], "channel_links": "", "manual_ids": "", "categories": ["clear"], "scope": "unpublished",
            "scan_all": True, "limit": 100, "start_date": (datetime.now(VIETNAM_TIMEZONE).date() + timedelta(days=1)).isoformat(),
            "hour": "18:00", "order": "oldest", "image_prompt": "Vẽ lại thumbnail dựa trên ảnh tham chiếu, bố cục rõ ràng, chữ dễ đọc, phù hợp nội dung bài nhạc; tỷ lệ 16:9.",
            "output_folder": ""}


class VideoPublishingController:
    def __init__(self, *, storage=None, module=None, listing=None, reference_factory=None, image_factory=None, thumbnail_factory=None):
        self.storage = storage or state_manager
        self.module = module or video_publishing_module
        self.listing = listing or list_videos_module
        self.reference_factory = reference_factory or YouTubeReferenceBrowser
        self.image_factory = image_factory or ChatGPTImageBrowser
        self.thumbnail_factory = thumbnail_factory or StudioThumbnailBrowser
        self.lock = threading.RLock()
        saved = self.storage.load_state(STATE_KEY) or {}
        self.settings = {**default_settings(), **saved.get("settings", {})}
        if "channel_source" not in saved.get("settings", {}):
            self.settings["channel_source"] = "links" if self.settings["channel_links"].strip() else "selected"
        # Credentials never belong in persistent state, even from an older file.
        self.settings.pop("cookie", None)
        self.rows = saved.get("rows", [])
        self.occupied = saved.get("occupied", {})
        for row in self.rows:
            if row.get("status") == "processing":
                row.update(status="stopped", detail="Phiên trước bị ngắt; tiếp tục để đọc lại kết quả thực tế.")
            if not publishing_row_selectable(row):
                row["selected"] = False
        self.message = saved.get("message", "Chọn kênh, quét trạng thái rồi tìm video tham chiếu.")
        if any(row.get("classification_version") != PUBLISHING_SCAN_SCHEMA_VERSION for row in self.rows):
            self.message = "Danh sách cũ chưa được kiểm tra bằng cách nhận diện bản nháp mới. Quét lại một lần để cập nhật đúng loại video."
        self.cookie = ""
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
                                  "busy": self.busy, "revision": self.revision, "has_cookie": bool(self.cookie),
                                  "session_busy": self.session_busy, "chatgpt_status": self.chatgpt_status,
                                  "needs_rescan": any(row.get("classification_version") != PUBLISHING_SCAN_SCHEMA_VERSION for row in self.rows)})

    def set_cookie(self, text):
        with self.lock:
            if self.busy or self.session_busy:
                raise ValueError("Chờ tác vụ kết thúc trước khi thay cookie.")
            if text.strip():
                parse_chatgpt_cookies(text)
            self.cookie = text
            if self.image_session is not None:
                self.image_session.update_cookies(text)
            self.chatgpt_status = "Đã nhận cookie; bấm Mở / kiểm tra phiên để xác nhận đăng nhập." if text.strip() else "Đã bỏ cookie nhập tay; có thể dùng phiên Chrome đã lưu."

    def _image_session(self):
        with self.lock:
            if self.image_session is None:
                self.image_session = self.image_factory(self.cookie)
            return self.image_session

    def _session_progress(self, message):
        with self.lock:
            self.chatgpt_status = message

    def prepare_chatgpt_session(self):
        with self.lock:
            if self.busy or self.session_busy:
                raise ValueError("Chờ tác vụ hiện tại kết thúc trước khi kiểm tra phiên ChatGPT.")
            self.session_busy = True
        try:
            self._image_session().ensure_ready(on_status=self._session_progress)
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
                raise ValueError("Dừng tác vụ trước khi đóng cửa sổ phiên ChatGPT.")
            self.session_busy = True
        try:
            if self.image_session is not None:
                self.image_session.close()
            self._session_progress("Đã đóng cửa sổ. Phiên đăng nhập vẫn được Chrome lưu riêng cho tool.")
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
            elif "image_prompt" in changed:
                for row in self.rows:
                    if row.get("status") != "successful" and not row.get("thumbnail_uploaded"):
                        row.pop("thumbnail_path", None)
                        row.pop("conversation_url", None)
            self.revision += 1
            self._save()

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
                for key in ("reference", "conversation_url", "thumbnail_path"):
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
                    if self.cookie.strip():
                        parse_chatgpt_cookies(self.cookie)
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
    def _error(exc):
        return str(exc) if isinstance(exc, (ValueError, YouTubeRequestError)) else "Không hoàn tất do lỗi kết nối/trình duyệt. Kiểm tra Chrome và phiên đăng nhập rồi tiếp tục."

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
            self._checkpoint(row, status="processing", detail="Đang kiểm tra video và tìm tham chiếu…")
            try:
                # Each explicit row selection authorizes that row's scanned
                # copyright type, independently of the current display filter.
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
                    found = reference.find(row["song"], source_title=row["old_title"], duration_seconds=row.get("duration_seconds"),
                                           exclude_ids=[entry["video_id"] for entry in self.rows])
                    if previous and any(found.get(key) != previous.get(key) for key in ("video_id", "title", "description", "thumbnail")):
                        with self.lock:
                            row.pop("thumbnail_path", None)
                            row.pop("conversation_url", None)
                    self._checkpoint(row, reference=found)
                if action == "references":
                    method = row["reference"].get("selection_label", "Đã tìm video tham chiếu")
                    self._checkpoint(row, status="ready", detail=method + "; title và description sẽ chép nguyên văn.")
                    continue
                if not row.get("thumbnail_path") or not Path(row["thumbnail_path"]).is_file():
                    folder = output / row["channel_id"]
                    folder.mkdir(parents=True, exist_ok=True)
                    base = folder / row["video_id"]
                    reference_path = download_reference_image(row["reference"]["thumbnail"], base.with_suffix(".reference.jpg"))
                    self._checkpoint(row, detail="Đang yêu cầu ChatGPT vẽ lại thumbnail…")
                    if image is None:
                        image = self._image_session()
                    raw = image.generate(reference_path, settings["image_prompt"], row["reference"], base.with_suffix(".generated"),
                                         conversation_url=row.get("conversation_url", ""),
                                         on_conversation=lambda url, row=row: self._remember_conversation(row, url))
                    path = normalize_thumbnail(raw, base.with_suffix(".jpg"))
                    self._checkpoint(row, thumbnail_path=path)
                self.module.copy_metadata(row["channel_id"], row["video_id"], row["reference"],
                                          expected_title=row["old_title"], expected_description=row["old_description"],
                                          categories=categories, publish_at=row["publish_at"])
                self._checkpoint(row, metadata_copied=True, detail="Đã xác nhận title/description. Đang tải thumbnail…")
                if not row.get("thumbnail_uploaded"):
                    self.module.require_eligible(row["channel_id"], row["video_id"], categories, publish_at=row["publish_at"])
                    thumbnail.upload(row["channel_id"], row["video_id"], row["thumbnail_path"])
                    self._checkpoint(row, thumbnail_uploaded=True)
                self._checkpoint(row, detail="Đang đặt lịch và đọc lại kết quả…")
                self.module.schedule(row["channel_id"], row["video_id"], row["publish_at"], row["reference"], categories=categories)
                self._checkpoint(row, status="successful", selected=False, detail="Đã xác nhận metadata và lịch đăng trên YouTube.")
            except ChatGPTSessionNeedsAction as exc:
                self._session_progress(str(exc))
                self._checkpoint(row, status="waiting_session", detail=str(exc))
                raise
            except TaskStopped:
                raise
            except Exception as exc:
                self._checkpoint(row, status="error", detail=self._error(exc))
                if isinstance(exc, YouTubeRequestError) and exc.status_code in {401, 403}:
                    raise
        successes = sum(row["status"] == "successful" for row in self.rows)
        failed = sum(row["status"] == "error" for row in self.rows)
        self._progress(f"Hoàn tất lượt xử lý · {successes} đã lên lịch · {failed} lỗi." if action == "run" else f"Đã tìm tham chiếu · {failed} lỗi. Kiểm tra bảng trước khi chạy.")

    def _check_schedule_conflicts(self):
        """Detect schedules added since the preview before any remote mutation."""
        selected = [row for row in self.rows if row.get("selected") and row.get("publish_at")]
        for channel_id in dict.fromkeys(row["channel_id"] for row in selected):
            self._progress(f"Đang kiểm tra lại lịch hiện có trên kênh {channel_id}…")
            token, tokens = None, set()
            while True:
                page, next_token = self.listing.list_all_videos(channel_id, limit=100, page_token=token)
                for video in page:
                    if video.channel_id != channel_id:
                        raise ValueError("YouTube trả về lịch của kênh khác.")
                    stamp = schedule_timestamp(video)
                    if video.scheduled_publishing_details and stamp is None:
                        raise ValueError("Có video đã lên lịch nhưng chưa đọc được ngày giờ. Kiểm tra Studio trước khi đặt thêm lịch.")
                    if not stamp:
                        continue
                    day = datetime.fromtimestamp(stamp, VIETNAM_TIMEZONE).date()
                    if any(row["channel_id"] == channel_id and row["video_id"] != video.id
                           and datetime.fromtimestamp(row["publish_at"], VIETNAM_TIMEZONE).date() == day for row in selected):
                        raise ValueError("Kênh đã có video khác được lên lịch vào ngày dự kiến sau lần quét. Quét lại để cập nhật ngày trống.")
                if not next_token:
                    break
                if next_token in tokens:
                    raise ValueError("YouTube trả về phân trang lịch bị lặp.")
                tokens.add(next_token)
                token = next_token

    def _worker(self, action, run):
        reference = image = None
        try:
            with bind_run_context(run):
                settings = copy.deepcopy(self.settings)
                reference = self.reference_factory()
                if action == "scan":
                    self._scan(settings, reference)
                else:
                    if action == "run":
                        self._check_schedule_conflicts()
                        pending_images = [row for row in self.rows if row.get("selected") and publishing_row_selectable(row)
                                          and (not row.get("thumbnail_path") or not Path(row["thumbnail_path"]).is_file())]
                        if pending_images:
                            image = self._image_session()
                            self._progress("Đang kiểm tra phiên ChatGPT trước khi xử lý danh sách…")
                            try:
                                image.ensure_ready(on_status=self._session_progress)
                            except ChatGPTSessionNeedsAction as exc:
                                self._checkpoint(pending_images[0], status="waiting_session", detail=str(exc))
                                raise
                    self._process(settings, reference, image, action)
        except ChatGPTSessionNeedsAction as exc:
            self._session_progress(str(exc))
            self._progress("Đã dừng lượt xử lý để khôi phục phiên ChatGPT. " + str(exc))
        except TaskStopped:
            self._progress("Đã dừng; có thể tiếp tục các dòng chưa xong.")
        except Exception as exc:
            self._progress(self._error(exc))
        finally:
            # The ChatGPT browser belongs to the app. Keep it open for manual
            # verification and reuse; only per-run reference browsers close.
            for adapter in (reference,):
                if adapter:
                    try:
                        adapter.close()
                    except Exception:
                        pass
            with self.lock:
                for row in self.rows:
                    if row["status"] == "processing":
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
