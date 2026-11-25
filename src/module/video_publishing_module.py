"""Copy exact reference metadata and schedule existing videos through Studio.

Schedule wire format: https://github.com/yusufusta/ytstudio/blob/master/ytstudio/templates.py
Mutations are confirmed by reading the video back, including uncertain responses.
"""
from datetime import datetime, timezone

import requests

from src.audio_recovery import _is_currently_public_video
from src.module.base import YouTubeRequestError, _response_json_or_error
from src.module.video_title_module import VideoTitleModule
from src.task_runtime import check_stopped, post_with_stop, wait_interruptibly
from src.utils import get_channels_info
from src.video_publishing import copyright_category, schedule_timestamp
from src.video_scan_dates import _status_indicates_draft
from src.youtube_auth import studio_authorization_header


class VideoPublishingModule(VideoTitleModule):
    def require_eligible(self, channel_id, video_id, categories, *, publish_at=None):
        video = self.read_video(channel_id, video_id)
        category = copyright_category(video)
        if category not in set(categories) or category in {"unknown", "checking"}:
            raise ValueError("Trạng thái bản quyền đã thay đổi so với lúc chọn video. Quét lại video này.")
        existing = schedule_timestamp(video)
        if video.scheduled_publishing_details and existing is None:
            raise ValueError("Video có lịch đăng nhưng chưa đọc được thời gian; giữ nguyên lịch hiện tại.")
        if existing and (not publish_at or abs(existing - publish_at) > 1):
            raise ValueError("Video đã có lịch đăng khác; quét lại để giữ lịch đã đặt.")
        if _is_currently_public_video(video):
            raise ValueError("Video đã công khai; tác vụ lên lịch chỉ xử lý video chưa công khai.")
        if str(video.privacy).upper() not in {"PRIVATE", "UNLISTED", "PUBLIC", "VIDEO_PRIVACY_PRIVATE", "VIDEO_PRIVACY_UNLISTED", "VIDEO_PRIVACY_PUBLIC"} and not _status_indicates_draft(video.draft_status):
            raise ValueError("Chưa đọc được trạng thái hiển thị video; đã dừng trước khi thay đổi.")
        return video

    def _mutate(self, channel_id, video_id, fields, matches, message):
        channel = get_channels_info(channel_id)
        if not channel or channel.id != channel_id:
            raise ValueError("Không tìm thấy phiên kênh. Load lại kênh trước khi tiếp tục.")
        token = self._get_session_token(channel)
        context = self._build_context(channel.id, channel.role, channel.delegated_session_id,
                                      extra_request_fields={"sessionInfo": {"token": token}})
        payload = {"encryptedVideoId": video_id, "context": context,
                   "delegationContext": dict(context["user"]["delegationContext"]),
                   "videoReadMask": {"videoId": True, "channelId": True, "title": True, "description": True,
                                     "privacy": True, "draftStatus": True, "scheduledPublishingDetails": {"all": True}}, **fields}
        headers = {"origin": "https://studio.youtube.com", "content-type": "application/json",
                   "cookie": channel.cookie_string(), "authorization": studio_authorization_header(channel.cookies),
                   "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139.0.0.0 Safari/537.36",
                   "referer": f"https://studio.youtube.com/video/{video_id}/edit"}
        try:
            response = post_with_stop("https://studio.youtube.com/youtubei/v1/video_manager/metadata_update?alt=json",
                                      headers=headers, json=payload)
            result = _response_json_or_error(response, message)
            if result.get("error") or result.get("success") is False:
                raise YouTubeRequestError("YouTube từ chối lưu thay đổi.", status_code=response.status_code)
        except requests.RequestException:
            # A disconnected response must not trigger a second mutation.
            pass
        for attempt in range(4):
            check_stopped()
            saved = self.read_video(channel_id, video_id)
            if matches(saved):
                return saved
            if attempt < 3:
                wait_interruptibly(2)
        raise ValueError("Chưa đọc lại được đúng thay đổi trên YouTube. Tiến độ được giữ để kiểm tra lại khi tiếp tục.")

    def copy_metadata(self, channel_id, video_id, reference, *, expected_title, expected_description, categories, publish_at=None):
        before = self.require_eligible(channel_id, video_id, categories, publish_at=publish_at)
        title, description = reference["title"], reference["description"]
        if not isinstance(title, str) or not title or not isinstance(description, str):
            raise ValueError("Thiếu title hoặc description của video tham chiếu.")
        if len(title.encode("utf-16-le")) > 200 or len(description.encode("utf-16-le")) > 10000:
            raise ValueError("Metadata tham chiếu vượt giới hạn YouTube; không cắt ngắn dữ liệu nguồn.")
        if before.title == title and before.description == description:
            return before
        if before.title != expected_title or before.description != expected_description:
            raise ValueError("Title/description đã thay đổi sau lần quét. Quét lại trước khi chép đè.")
        return self._mutate(channel_id, video_id,
                            {"title": {"newTitle": title}, "description": {"newDescription": description, "shouldSegment": True}},
                            lambda video: video.title == title and video.description == description, "copy metadata")

    def schedule(self, channel_id, video_id, publish_at, reference, *, categories):
        before = self.require_eligible(channel_id, video_id, categories, publish_at=publish_at)
        if before.title != reference["title"] or before.description != reference["description"]:
            raise ValueError("Metadata hiện tại khác video tham chiếu; chưa lên lịch.")
        if schedule_timestamp(before) and abs(schedule_timestamp(before) - publish_at) <= 1:
            return before
        if publish_at <= datetime.now(timezone.utc).timestamp():
            raise ValueError("Giờ đăng đã qua. Chọn ngày bắt đầu mới rồi tạo lại lịch.")
        return self._mutate(channel_id, video_id,
                            {"flowType": "MDE_FLOW_TYPE_UPLOAD", "privacyState": {"newPrivacy": "PRIVATE"},
                             "scheduledPublishing": {"set": {"timeSec": str(int(publish_at)), "privacy": "PUBLIC"}},
                             "draftState": {"operation": "MDE_DRAFT_STATE_UPDATE_OPERATION_REMOVE_DRAFT_STATE"}},
                            lambda video: bool(schedule_timestamp(video)) and abs(schedule_timestamp(video) - publish_at) <= 1,
                            "schedule video")


video_publishing_module = VideoPublishingModule()
