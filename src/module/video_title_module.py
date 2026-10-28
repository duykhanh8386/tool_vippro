"""Change only a video's title using its existing Tuất Studio session.

Wire format reference: https://github.com/yusufusta/ytstudio/blob/master/ytstudio/templates.py
This is a Studio endpoint; always read back the saved title before success.
"""
import re
import math

import requests

from src.module.base import IModule, YouTubeRequestError, _response_json_or_error
from src.task_runtime import check_stopped, current_run_context, post_with_stop
from src.utils import get_channels_info
from src.video_title_matching import clean_video_title
from src.youtube_auth import studio_authorization_header


class VideoTitleModule(IModule):
    def _read_owned(self, video_id, channel_id):
        check_stopped()
        video = self._get_video_info(video_id, channel_id)
        if video.id != video_id or video.channel_id != channel_id:
            raise ValueError("Video không thuộc đúng kênh đã chọn; chưa gửi lệnh đổi tiêu đề.")
        return video

    def update_title(self, channel_id, video_id, title, *, expected_title, audio_duration=None, tolerance=2.0):
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id or ""):
            raise ValueError("Video ID không hợp lệ.")
        title = clean_video_title(title)
        before = self._read_owned(video_id, channel_id)
        if audio_duration is not None:
            current_duration = float(before.duration_ms or 0) / 1000
            if not math.isfinite(current_duration) or current_duration <= 0 or abs(current_duration - audio_duration) > tolerance + 1e-6:
                raise ValueError("Thời lượng video hiện tại không còn khớp bài nhạc. Quét và ghép lại trước khi đổi tiêu đề.")
        if before.title == title:
            return {"title": title, "changed": False}
        if before.title != expected_title:
            raise ValueError("Tiêu đề YouTube đã thay đổi sau lần quét. Quét lại trước khi đổi để giữ thay đổi mới.")
        channel = get_channels_info(channel_id)
        if channel is None or channel.id != channel_id:
            raise ValueError("Không tìm thấy phiên của kênh đã chọn. Load lại kênh trong Tuất.")
        token = self._get_session_token(channel)
        context = self._build_context(channel.id, channel.role, channel.delegated_session_id,
                                      extra_request_fields={"sessionInfo": {"token": token}})
        payload = {"encryptedVideoId": video_id, "title": {"newTitle": title}, "context": context,
                   "delegationContext": dict(context["user"]["delegationContext"]),
                   "videoReadMask": {"videoId": True, "channelId": True, "title": True}}
        headers = {"origin": "https://studio.youtube.com", "content-type": "application/json",
                   "cookie": channel.cookie_string(), "authorization": studio_authorization_header(channel.cookies),
                   "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139.0.0.0 Safari/537.36",
                   "referer": f"https://studio.youtube.com/video/{video_id}/edit"}
        uncertain = False
        try:
            response = post_with_stop("https://studio.youtube.com/youtubei/v1/video_manager/metadata_update?alt=json",
                                      headers=headers, json=payload)
            result = _response_json_or_error(response, "title update")
            if result.get("error") or result.get("success") is False:
                raise YouTubeRequestError("YouTube từ chối đổi tiêu đề; chưa ghi nhận thành công.", status_code=response.status_code)
        except requests.RequestException:
            # A lost response may follow a successful save. Read rather than
            # submitting a second mutation blindly.
            uncertain = True
        for attempt in range(3):
            check_stopped()
            saved = self._read_owned(video_id, channel_id)
            if saved.title == title:
                return {"title": title, "changed": True}
            if saved.title != expected_title:
                raise ValueError("YouTube đang có tiêu đề khác kết quả đã xem trước. Kiểm tra Studio trước khi thử lại.")
            if attempt < 2:
                run = current_run_context()
                if run:
                    run.wait(1)
                else:
                    import time
                    time.sleep(1)
        suffix = " sau khi mất phản hồi mạng" if uncertain else ""
        raise ValueError(f"Chưa xác nhận được tiêu đề mới trên YouTube{suffix}. Chạy lại sẽ đọc trước khi gửi tiếp.")


video_title_module = VideoTitleModule()
