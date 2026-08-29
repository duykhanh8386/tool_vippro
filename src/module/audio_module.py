# RECOVERED: depyo output corrected from CPython 3.12 disassembly
import os
from urllib.parse import quote
import requests
from loguru import logger
from src.module.base import IModule
from src.module.model import ChannelInfo
from src.utils import get_channels_info
from src.task_runtime import check_stopped, post_with_stop


class AudioUpdateError(Exception):
    """An API error with a user-facing message and retry information."""

    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def _youtube_error_message(response: requests.Response, action: str) -> str:
    try:
        api_message = response.json().get("error", {}).get("message", "")
    except (ValueError, AttributeError):
        api_message = response.text.strip()[:500]

    if response.status_code == 403 and "Channel not permitted to edit video" in api_message:
        return (
            "Kênh chưa được YouTube cấp quyền thêm âm thanh đa ngôn ngữ. "
            "Hãy vào YouTube Studio → Cài đặt → Kênh → Điều kiện sử dụng tính năng "
            "và bật Tính năng nâng cao; sau đó kiểm tra mục Ngôn ngữ của video có nút Audio/Dub."
        )
    if response.status_code == 401:
        return "Phiên đăng nhập YouTube đã hết hạn. Hãy đăng nhập và quét lại kênh."
    if response.status_code == 403:
        return f"YouTube từ chối quyền {action}. {api_message or 'Kênh không có quyền thực hiện thao tác này.'}"
    if response.status_code == 429:
        return "YouTube đang giới hạn số lượng yêu cầu. Hãy chờ một lúc rồi thử lại."
    if response.status_code >= 500:
        return "Máy chủ YouTube đang gặp lỗi tạm thời. Hãy thử lại sau."
    return f"Không thể {action} (HTTP {response.status_code}). {api_message}".strip()


class UpdateAudioModule(IModule):
    def add(self, id_video: str, channel_id: str, file_name: str, language: str, data: bytes):
        check_stopped()
        channel_info = get_channels_info(channel_id)
        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies])
        session_token = self._get_session_token(channel_info)
        fname_header = quote(os.path.basename(file_name), safe="")
        upload_url, scotty_resource_id = self._upload_http(fname_header=fname_header, cookie_string=cookie_string)
        # YouTube's audio-track flow first registers the pending Scotty resource
        # with the video, then uploads/finalizes the resource bytes.  Keep the
        # upload synchronous so callers only see success after it has completed.
        res = self._update(video_id=id_video, scotty_resource_id=scotty_resource_id, channel_info=channel_info, session_token=session_token, cookie_string=cookie_string, language=language)
        self._next_upload_http(next_url=upload_url, fname_header=fname_header, cookie_string=cookie_string, data=data)
        return res
    def _upload_http(self, fname_header: str, cookie_string: str):
        url = "https://upload.youtube.com/upload/audiotrack?authuser=0"; headers = {"Host": "upload.youtube.com", "Cookie": cookie_string, "Content-Length": "2", "Sec-Ch-Ua-Platform": '"Windows"', "Sec-Ch-Ua": '"Chromium";v="139", "Not;A=Brand";v="99"', "Sec-Ch-Ua-Mobile": "?0", "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-File-Name": fname_header, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8", "Accept-Language": "en-US,en;q=0.9", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36", "X-Goog-Upload-Command": "start", "Accept": "*/*", "Origin": "https://studio.youtube.com", "Referer": "https://studio.youtube.com/", "Accept-Encoding": "gzip, deflate, br", "Priority": "u=1, i"}; response = post_with_stop(url, headers=headers, data="{}")
        if response.status_code != 200:
            raise AudioUpdateError(_youtube_error_message(response, "khởi tạo tải audio"), status_code=response.status_code, retryable=response.status_code == 429 or response.status_code >= 500)
        upload_url = response.headers["X-Goog-Upload-URL"]; scotty_id = response.headers["X-Goog-Upload-Header-Scotty-Resource-Id"]
        return (upload_url, scotty_id)
    def _next_upload_http(self, next_url: str, fname_header: str, cookie_string: str, data: bytes) -> str:
        headers = {"Host": "upload.youtube.com", "Cookie": cookie_string, "X-Goog-Upload-File-Name": fname_header, "Content-Type": "application/x-www-form-urlencoded;charset=utf-8", "Accept-Language": "en-US,en;q=0.9", "X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36", "Accept": "*/*", "Origin": "https://studio.youtube.com", "Referer": "https://studio.youtube.com/", "Accept-Encoding": "gzip, deflate, br", "Priority": "u=1, i"}; response = post_with_stop(next_url, headers=headers, data=data)
        if response.status_code != 200:
            raise AudioUpdateError(_youtube_error_message(response, "tải audio"), status_code=response.status_code, retryable=response.status_code == 429 or response.status_code >= 500)
    def _update(self, video_id: str, scotty_resource_id: str, channel_info: ChannelInfo, cookie_string: str, session_token: str, language: str):
        url = "https://studio.youtube.com/youtubei/v1/creator/add_audio_track?alt=json"; headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": f"SAPISIDHASH {channel_info.sapisidhash}", "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{video_id}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}; payload = {"videoId": video_id, "resourceId": {"scottyResourceId": {"id": scotty_resource_id}}, "language": language, "audioContentTypeString": "dubbed", "audioTrackSource": "AUDIO_TRACK_SOURCE_CREATOR", "context": {"client": {"clientName": 62, "clientVersion": "1.20250902.04.00", "hl": "en", "gl": "VN", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AWSNWa0l7AGlCHtnt233UutuGGeh33lZ817vfraxpNhL8LY5gqkpaiN73HzUXyRRQ2ApQuCVRfHRtr9rlEQ8rczpjRVn_mm0nP74Qdc4IR95HbzJKhorwIoTVAqfC4o=", "sessionInfo": {"token": session_token}}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clickTracking": {"visualElement": {"veType": 74_618}}, "clientScreenNonce": "UUFKQY_AX3QaOzkG"}}; response = post_with_stop(url, headers=headers, json=payload)
        if response.status_code not in (200, 409):
            logger.error("YouTube add_audio_track failed: status={} body={}", response.status_code, response.text[:1000])
            raise AudioUpdateError(_youtube_error_message(response, "gắn audio vào video"), status_code=response.status_code, retryable=response.status_code == 429 or response.status_code >= 500)
        return response.status_code
    def delete(self, id_video: str, channel_id: str):
        channel_info = get_channels_info(channel_id); url = "https://studio.youtube.com/youtubei/v1/creator/delete_audio_track?alt=json"; cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies]); session_token = self._get_session_token(channel_info); all_track_ids = self._get_all_audio_track_ids(id_video, channel_id); headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": f"SAPISIDHASH {channel_info.sapisidhash}", "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{id_video}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"}
        for track_id in all_track_ids:
            payload = {"videoId": id_video, "audioTrackId": track_id, "unpublishTrack": False, "context": {"client": {"clientName": 62, "clientVersion": "1.20250902.04.00", "hl": "en", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AWSNWa3PV1e-JQRiHlmMmNXCMA9Kt6en05uq7bbw9WnQgnJdNT8RNsEfMheyglxoOPf_TMIzUzU80CM9khDsuy6zp2Uz9ROtcC5RGvGrdEkSa_rIL5z6FDB2wAAYVWg=", "sessionInfo": {"token": session_token}}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clientScreenNonce": "7nFa5dcSfcGGJAJS"}}
            response = post_with_stop(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.exception(f"Failed to delete audio track: {response}")
    def _get_all_audio_track_ids(self, id_video: str, channel_id: str):
        url = "https://studio.youtube.com/youtubei/v1/crowdsourcing/get_video_translations?alt=json"
        channel_info = get_channels_info(channel_id)
        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies])
        session_token = self._get_session_token(channel_info)
        headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": f"SAPISIDHASH {channel_info.sapisidhash}", "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{id_video}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"}
        payload = payload = {"context": {"client": {"clientName": 62, "clientVersion": "1.20250902.04.00", "hl": "en", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AWSNWa3PV1e-JQRiHlmMmNXCMA9Kt6en05uq7bbw9WnQgnJdNT8RNsEfMheyglxoOPf_TMIzUzU80CM9khDsuy6zp2Uz9ROtcC5RGvGrdEkSa_rIL5z6FDB2wAAYVWg=", "sessionInfo": {"token": session_token}, "consistencyTokenJars": []}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clientScreenNonce": "7nFa5dcSfcGGJAJS"}, "videoIds": [id_video], "filters": [], "fetchAloudData": False, "fetchAutoDubbingData": False, "fetchAutoDubbingAsrData": False, "fetchBulkActionsStatus": False}
        response = post_with_stop(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to get audio track IDs: {response.status_code}")
        all_track_ids = []
        for item in response.json()["videoTranslations"][0]["translations"]:
            try:
                all_track_ids.append(item["audioTranslation"]["audioTrackId"])
            except:
                pass
        return all_track_ids


update_audio_module = UpdateAudioModule()
