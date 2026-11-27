"""Copy exact reference metadata and schedule existing videos through Studio.

Schedule wire format: https://github.com/yusufusta/ytstudio/blob/master/ytstudio/templates.py
Mutations are confirmed by reading the video back, including uncertain responses.
"""
from datetime import datetime, timezone
import unicodedata

import requests

from src.audio_recovery import _is_currently_public_video
from src.module.base import YouTubeRequestError, _response_json_or_error, studio_video_from_payload
from src.module.video_title_module import VideoTitleModule
from src.task_runtime import check_stopped, post_with_stop, wait_interruptibly
from src.utils import get_channels_info
from src.video_publishing import has_schedule_info, schedule_timestamp
from src.video_scan_dates import _status_indicates_draft
from src.youtube_auth import studio_authorization_header


class VideoPublishingModule(VideoTitleModule):
    def _get_video_info(self, video_id, channel_id):
        return super()._get_video_info(video_id, channel_id, critical_read=True)

    @staticmethod
    def _same_text(left, right):
        def normal(value):
            return unicodedata.normalize("NFC", str(value or "").replace("\r\n", "\n").replace("\r", "\n"))
        return normal(left) == normal(right)

    def _metadata_matches(self, video, reference):
        return self._same_text(video.title, reference["title"]) and self._same_text(video.description, reference["description"])

    def require_eligible(self, channel_id, video_id, categories, *, publish_at=None):
        video = self.read_video(channel_id, video_id)
        # Copyright categories filter the scan, not an already selected job.
        # Claims may change while the thumbnail is generated; keep processing
        # that video and let Studio report any actual publishing restriction.
        existing = schedule_timestamp(video)
        if has_schedule_info(video) and existing is None:
            raise ValueError("Video có lịch đăng nhưng chưa đọc được thời gian; giữ nguyên lịch hiện tại.")
        if existing and (not publish_at or abs(existing - publish_at) > 1):
            raise ValueError("Video đã có lịch đăng khác; quét lại để giữ lịch đã đặt.")
        if _is_currently_public_video(video):
            raise ValueError("Video đã công khai; tác vụ lên lịch chỉ xử lý video chưa công khai.")
        if str(video.privacy).upper() not in {"PRIVATE", "UNLISTED", "PUBLIC", "VIDEO_PRIVACY_PRIVATE", "VIDEO_PRIVACY_UNLISTED", "VIDEO_PRIVACY_PUBLIC"} and not _status_indicates_draft(video.draft_status):
            raise ValueError("Chưa đọc được trạng thái hiển thị video; đã dừng trước khi thay đổi.")
        return video

    def _mutate(self, channel_id, video_id, fields, matches, message, *, mismatch=lambda video: "dữ liệu đã lưu"):
        channel = get_channels_info(channel_id)
        if not channel or channel.id != channel_id:
            raise ValueError("Không tìm thấy phiên kênh. Load lại kênh trước khi tiếp tục.")
        token = self._get_session_token(channel)
        context = self._current_studio_context(channel, token)
        payload = {"encryptedVideoId": video_id, "context": context,
                   "delegationContext": dict(context["user"]["delegationContext"]),
                   "videoReadMask": {"videoId": True, "channelId": True, "title": True, "description": True,
                                     "privacy": True, "draftStatus": True, "scheduledPublishingDetails": {"all": True},
                                     "thumbnailDetails": {"all": True}, "thumbnailEditorState": {"all": True}}, **fields}
        headers = {"origin": "https://studio.youtube.com", "content-type": "application/json",
                   "cookie": channel.cookie_string(), "authorization": studio_authorization_header(channel.cookies),
                   "user-agent": context["client"].get("userAgent") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139.0.0.0 Safari/537.36",
                   "referer": f"https://studio.youtube.com/video/{video_id}/edit"}
        result = None
        try:
            response = post_with_stop("https://studio.youtube.com/youtubei/v1/video_manager/metadata_update?alt=json",
                                      headers=headers, json=payload)
            result = _response_json_or_error(response, message)
            if result.get("error") or result.get("success") is False:
                raise YouTubeRequestError("YouTube từ chối lưu thay đổi.", status_code=response.status_code)
        except requests.RequestException:
            # A disconnected response must not trigger a second mutation.
            pass
        # A mutation response can already contain the persisted video. Do not
        # discard that evidence and replace it with an eventually stale read.
        if isinstance(result, dict):
            candidates = [result.get("video")] + (result.get("videos") if isinstance(result.get("videos"), list) else [])
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                if candidate.get("videoId") == video_id and candidate.get("channelId") == channel_id:
                    saved = studio_video_from_payload(candidate)
                    if matches(saved):
                        return saved
        saved = None
        delays = (1, 2, 3, 5, 8, 10, 12)
        for attempt in range(len(delays) + 1):
            check_stopped()
            saved = self.read_video(channel_id, video_id)
            if matches(saved):
                return saved
            if attempt < len(delays):
                wait_interruptibly(delays[attempt])
        phase = "title/description" if message == "copy metadata" else "lịch đăng"
        raise ValueError("Chưa xác nhận " + phase + " trên YouTube: còn khác " + mismatch(saved) + ". Tiến độ và ảnh được giữ; chạy tiếp sẽ đọc lại trước khi gửi thêm thay đổi.")

    def copy_metadata(self, channel_id, video_id, reference, *, expected_title, expected_description, categories, publish_at=None):
        before = self.require_eligible(channel_id, video_id, categories, publish_at=publish_at)
        title, description = reference["title"], reference["description"]
        if not isinstance(title, str) or not title or not isinstance(description, str):
            raise ValueError("Thiếu title hoặc description của video tham chiếu.")
        if len(title.encode("utf-16-le")) > 200 or len(description.encode("utf-16-le")) > 10000:
            raise ValueError("Metadata tham chiếu vượt giới hạn YouTube; không cắt ngắn dữ liệu nguồn.")
        if self._metadata_matches(before, reference):
            return before
        if (not any(self._same_text(before.title, value) for value in (expected_title, title))
                or not any(self._same_text(before.description, value) for value in (expected_description, description))):
            raise ValueError("Title/description đã thay đổi sau lần quét. Quét lại trước khi chép đè.")
        return self._mutate(channel_id, video_id,
                            {"title": {"newTitle": title}, "description": {"newDescription": description, "shouldSegment": True}},
                            lambda video: self._metadata_matches(video, reference), "copy metadata",
                            mismatch=lambda video: ", ".join(name for name, actual, expected in (
                                ("tiêu đề", video.title, title), ("mô tả", video.description, description)) if not self._same_text(actual, expected)))

    def schedule(self, channel_id, video_id, publish_at, reference, *, categories):
        before = self.require_eligible(channel_id, video_id, categories, publish_at=publish_at)
        if not self._metadata_matches(before, reference):
            raise ValueError("Metadata hiện tại khác video tham chiếu; chưa lên lịch.")
        if schedule_timestamp(before) and abs(schedule_timestamp(before) - publish_at) <= 1 and not _status_indicates_draft(before.draft_status):
            return before
        if publish_at <= datetime.now(timezone.utc).timestamp():
            raise ValueError("Giờ đăng đã qua. Chọn ngày bắt đầu mới rồi tạo lại lịch.")
        return self._mutate(channel_id, video_id,
                            {"flowType": "MDE_FLOW_TYPE_UPLOAD", "privacyState": {"newPrivacy": "PRIVATE"},
                             "scheduledPublishing": {"set": {"timeSec": str(int(publish_at)), "privacy": "PUBLIC"}},
                             "draftState": {"operation": "MDE_DRAFT_STATE_UPDATE_OPERATION_REMOVE_DRAFT_STATE"}},
                            lambda video: bool(schedule_timestamp(video)) and abs(schedule_timestamp(video) - publish_at) <= 1
                                and not _status_indicates_draft(video.draft_status),
                            "schedule video", mismatch=lambda video: "ngày giờ hoặc trạng thái bản nháp")


video_publishing_module = VideoPublishingModule()
