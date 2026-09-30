# RECOVERED: depyo output corrected from CPython 3.12 disassembly
import os
import time
import unicodedata
from urllib.parse import quote
import requests
from loguru import logger
from src.module.base import IModule
from src.module.model import ChannelInfo
from src.utils import get_channels_info
from src.task_runtime import TaskStopped, check_stopped, post_with_stop, wait_interruptibly


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
    _CHUNK_SIZE = 16 * 1024 * 1024
    _MAX_UPLOAD_RETRIES = 5
    _UPLOAD_TIMEOUT = (30, 900)
    _TRANSLATION_BATCH_SIZE = 50

    def add(
        self,
        id_video: str,
        channel_id: str,
        file_name: str,
        language: str,
        data: bytes | None = None,
        progress: dict | None = None,
        upload_path: str | None = None,
    ):
        check_stopped()
        channel_info = get_channels_info(channel_id)
        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies])
        session_token = self._get_session_token(channel_info)
        fname_header = quote(os.path.basename(file_name), safe="")
        with requests.Session() as session:
            upload_url, scotty_resource_id = self._upload_http(
                fname_header=fname_header,
                cookie_string=cookie_string,
                session=session,
            )
            # YouTube's audio-track flow first registers the pending Scotty resource
            # with the video, then uploads/finalizes the resource bytes.  Keep the
            # upload synchronous so callers only see success after it has completed.
            res = self._update(
                video_id=id_video,
                scotty_resource_id=scotty_resource_id,
                channel_info=channel_info,
                session_token=session_token,
                cookie_string=cookie_string,
                language=language,
                session=session,
            )
            if res == 409:
                if self._has_audio_track(id_video, channel_id, language):
                    logger.info("Audio track already exists: video={} language={}", id_video, language)
                    return 409
                raise AudioUpdateError(
                    "YouTube báo xung đột (409) nhưng không tìm thấy audio track tương ứng; "
                    "không tự động coi là thành công.",
                    status_code=409,
                )
            self._next_upload_http(
                next_url=upload_url,
                fname_header=fname_header,
                cookie_string=cookie_string,
                data=data,
                file_path=(upload_path or file_name) if data is None else None,
                progress=progress,
                session=session,
            )
            return res
    def _upload_http(
        self,
        fname_header: str,
        cookie_string: str,
        session: requests.Session | None = None,
    ):
        url = "https://upload.youtube.com/upload/audiotrack?authuser=0"; headers = {"Host": "upload.youtube.com", "Cookie": cookie_string, "Content-Length": "2", "Sec-Ch-Ua-Platform": '"Windows"', "Sec-Ch-Ua": '"Chromium";v="139", "Not;A=Brand";v="99"', "Sec-Ch-Ua-Mobile": "?0", "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-File-Name": fname_header, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8", "Accept-Language": "en-US,en;q=0.9", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36", "X-Goog-Upload-Command": "start", "Accept": "*/*", "Origin": "https://studio.youtube.com", "Referer": "https://studio.youtube.com/", "Accept-Encoding": "gzip, deflate, br", "Priority": "u=1, i"}; response = post_with_stop(url, headers=headers, data="{}", session=session)
        if response.status_code != 200:
            raise AudioUpdateError(_youtube_error_message(response, "khởi tạo tải audio"), status_code=response.status_code, retryable=response.status_code == 429 or response.status_code >= 500)
        upload_url = response.headers["X-Goog-Upload-URL"]; scotty_id = response.headers["X-Goog-Upload-Header-Scotty-Resource-Id"]
        return (upload_url, scotty_id)
    def _base_upload_headers(self, fname_header: str, cookie_string: str) -> dict:
        return {
            "Host": "upload.youtube.com",
            "Cookie": cookie_string,
            "X-Goog-Upload-File-Name": fname_header,
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Origin": "https://studio.youtube.com",
            "Referer": "https://studio.youtube.com/",
        }

    def _query_upload_offset(
        self,
        next_url: str,
        base_headers: dict,
        session: requests.Session | None = None,
    ) -> int | None:
        try:
            headers = dict(base_headers)
            headers["X-Goog-Upload-Command"] = "query"
            response = post_with_stop(
                next_url,
                headers=headers,
                data=b"",
                timeout=(15, 60),
                session=session,
            )
            if response.status_code != 200:
                return None
            received = response.headers.get("X-Goog-Upload-Size-Received")
            return int(received) if received is not None else None
        except TaskStopped:
            raise
        except Exception as exc:
            logger.warning("Cannot query audio upload offset: {}", exc)
            return None

    def _next_upload_http(
        self,
        next_url: str,
        fname_header: str,
        cookie_string: str,
        data: bytes | None = None,
        *,
        file_path: str | None = None,
        progress: dict | None = None,
        session: requests.Session | None = None,
    ) -> str:
        """Upload in chunks and resume the same Scotty session after a timeout."""
        base_headers = self._base_upload_headers(fname_header, cookie_string)
        if data is None and not file_path:
            raise AudioUpdateError("Không có dữ liệu audio để tải lên")
        total = len(data) if data is not None else os.path.getsize(str(file_path))
        if total <= 0:
            raise AudioUpdateError("File audio rỗng, không thể tải lên")
        offset = 0
        retries = 0
        started_at = time.monotonic()
        if progress is not None:
            progress.update(
                sent=0,
                total=total,
                started_at=started_at,
                updated_at=started_at,
                status="uploading",
            )
        source_file = open(file_path, "rb") if data is None else None
        try:
            while offset < total:
                check_stopped()
                end = min(offset + self._CHUNK_SIZE, total)
                if source_file is not None:
                    source_file.seek(offset)
                    chunk = source_file.read(end - offset)
                else:
                    chunk = data[offset:end]
                if not chunk:
                    raise AudioUpdateError(
                        f"Không đọc được audio tại vị trí {offset}/{total} byte"
                    )
                headers = dict(base_headers)
                headers["X-Goog-Upload-Offset"] = str(offset)
                headers["X-Goog-Upload-Command"] = "upload, finalize" if end == total else "upload"
                try:
                    response = post_with_stop(
                        next_url,
                        headers=headers,
                        data=chunk,
                        timeout=self._UPLOAD_TIMEOUT,
                        session=session,
                    )
                    if response.status_code != 200:
                        retryable = response.status_code == 429 or response.status_code >= 500
                        raise AudioUpdateError(
                            _youtube_error_message(response, "tải audio"),
                            status_code=response.status_code,
                            retryable=retryable,
                        )
                    offset += len(chunk)
                    retries = 0
                    if progress is not None:
                        progress["sent"] = offset
                        progress["updated_at"] = time.monotonic()
                        progress["status"] = "complete" if offset >= total else "uploading"
                except TaskStopped:
                    raise
                except Exception as exc:
                    if isinstance(exc, AudioUpdateError) and not exc.retryable:
                        raise
                    retries += 1
                    if retries > self._MAX_UPLOAD_RETRIES:
                        raise AudioUpdateError(
                            f"Tải audio bị gián đoạn tại {offset}/{total} byte sau "
                            f"{self._MAX_UPLOAD_RETRIES} lần thử: {exc}",
                            status_code=getattr(exc, "status_code", None),
                        ) from exc
                    server_offset = self._query_upload_offset(
                        next_url,
                        base_headers,
                        session=session,
                    )
                    if server_offset is not None and 0 <= server_offset <= total:
                        offset = server_offset
                    if progress is not None:
                        progress["sent"] = offset
                        progress["updated_at"] = time.monotonic()
                        progress["status"] = "retrying"
                    logger.warning(
                        "Retry audio upload in same session: offset={}/{} attempt={}/{} error={}",
                        offset, total, retries, self._MAX_UPLOAD_RETRIES, exc,
                    )
                    wait_interruptibly(min(2**retries, 10))
                    if progress is not None:
                        progress["status"] = "uploading"
        finally:
            if source_file is not None:
                source_file.close()
        return "final"
    def _update(self, video_id: str, scotty_resource_id: str, channel_info: ChannelInfo, cookie_string: str, session_token: str, language: str, session: requests.Session | None = None):
        url = "https://studio.youtube.com/youtubei/v1/creator/add_audio_track?alt=json"; headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": f"SAPISIDHASH {channel_info.sapisidhash}", "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{video_id}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}; payload = {"videoId": video_id, "resourceId": {"scottyResourceId": {"id": scotty_resource_id}}, "language": language, "audioContentTypeString": "dubbed", "audioTrackSource": "AUDIO_TRACK_SOURCE_CREATOR", "context": {"client": {"clientName": 62, "clientVersion": "1.20250902.04.00", "hl": "en", "gl": "VN", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AWSNWa0l7AGlCHtnt233UutuGGeh33lZ817vfraxpNhL8LY5gqkpaiN73HzUXyRRQ2ApQuCVRfHRtr9rlEQ8rczpjRVn_mm0nP74Qdc4IR95HbzJKhorwIoTVAqfC4o=", "sessionInfo": {"token": session_token}}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clickTracking": {"visualElement": {"veType": 74_618}}, "clientScreenNonce": "UUFKQY_AX3QaOzkG"}}; response = post_with_stop(url, headers=headers, json=payload, session=session)
        if response.status_code not in (200, 409):
            logger.error("YouTube add_audio_track failed: status={} body={}", response.status_code, response.text[:1000])
            raise AudioUpdateError(_youtube_error_message(response, "gắn audio vào video"), status_code=response.status_code, retryable=response.status_code == 429 or response.status_code >= 500)
        return response.status_code
    def delete_track_ids(
        self, id_video: str, channel_id: str, track_ids: list[str]
    ) -> int:
        """Delete only the explicitly selected creator audio tracks.

        Automatic recovery uses this narrow operation so a failed language can
        be replaced without removing healthy/published languages on the same
        video. ``delete`` below intentionally retains its historical
        all-tracks behaviour for the manual "Xóa & thêm audio" action.
        """
        unique_track_ids = list(
            dict.fromkeys(str(track_id).strip() for track_id in track_ids if track_id)
        )
        if not unique_track_ids:
            return 200
        channel_info = get_channels_info(channel_id); url = "https://studio.youtube.com/youtubei/v1/creator/delete_audio_track?alt=json"; cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies]); session_token = self._get_session_token(channel_info); headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": f"SAPISIDHASH {channel_info.sapisidhash}", "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{id_video}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"}
        for track_id in unique_track_ids:
            payload = {"videoId": id_video, "audioTrackId": track_id, "unpublishTrack": False, "context": {"client": {"clientName": 62, "clientVersion": "1.20250902.04.00", "hl": "en", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AWSNWa3PV1e-JQRiHlmMmNXCMA9Kt6en05uq7bbw9WnQgnJdNT8RNsEfMheyglxoOPf_TMIzUzU80CM9khDsuy6zp2Uz9ROtcC5RGvGrdEkSa_rIL5z6FDB2wAAYVWg=", "sessionInfo": {"token": session_token}}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clientScreenNonce": "7nFa5dcSfcGGJAJS"}}
            response = post_with_stop(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise AudioUpdateError(
                    _youtube_error_message(response, "xóa audio track"),
                    status_code=response.status_code,
                    retryable=response.status_code == 429 or response.status_code >= 500,
                )
        return 200

    def delete(self, id_video: str, channel_id: str):
        return self.delete_track_ids(
            id_video,
            channel_id,
            self._get_all_audio_track_ids(id_video, channel_id),
        )
    def _get_video_translation_payload(
        self, video_ids: list[str], channel_id: str
    ) -> dict:
        """Fetch the complete Studio translation/audio response for a batch."""
        if not video_ids:
            return {"videoTranslations": [], "audioTracks": []}
        url = "https://studio.youtube.com/youtubei/v1/crowdsourcing/get_video_translations?alt=json"
        channel_info = get_channels_info(channel_id)
        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies])
        session_token = self._get_session_token(channel_info)
        headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": f"SAPISIDHASH {channel_info.sapisidhash}", "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{video_ids[0]}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"}
        payload = {"context": {"client": {"clientName": 62, "clientVersion": "1.20260924.00.01", "hl": "vi", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_LIGHT", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": self.EATS, "sessionInfo": {"token": session_token}, "consistencyTokenJars": []}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clientScreenNonce": self.CLIENT_SCREEN_NONCE}, "videoIds": video_ids, "filters": ["TRANSLATION_FILTER_DRAFT", "TRANSLATION_FILTER_PUBLISHED"], "fetchAloudData": False, "fetchAutoDubbingData": False, "fetchAutoDubbingAsrData": False, "fetchBulkActionsStatus": False, "fetchDataFromInternalService": False}
        response = post_with_stop(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise AudioUpdateError(
                _youtube_error_message(response, "đọc danh sách audio track"),
                status_code=response.status_code,
                retryable=response.status_code == 429 or response.status_code >= 500,
            )
        try:
            result = response.json()
        except (ValueError, AttributeError) as exc:
            raise AudioUpdateError(
                "YouTube trả dữ liệu trạng thái audio không hợp lệ.",
                status_code=response.status_code,
            ) from exc
        if not isinstance(result, dict):
            raise AudioUpdateError(
                "YouTube trả cấu trúc trạng thái audio không hợp lệ.",
                status_code=response.status_code,
            )
        return result

    def _get_video_translation_groups(
        self, video_ids: list[str], channel_id: str
    ) -> list[dict]:
        """Compatibility helper returning only translation groups."""
        return self._get_video_translation_payload(video_ids, channel_id).get(
            "videoTranslations"
        ) or []

    @staticmethod
    def _translation_group_video_id(group: dict) -> str | None:
        for key in ("videoId", "video_id", "id"):
            value = group.get(key)
            if isinstance(value, str) and value:
                return value
        video = group.get("video") or {}
        value = video.get("videoId") if isinstance(video, dict) else None
        return value if isinstance(value, str) and value else None

    def _get_audio_translation_items(self, id_video: str, channel_id: str) -> list[dict]:
        groups = self._get_video_translation_groups([id_video], channel_id)
        if not groups:
            return []
        for group in groups:
            if self._translation_group_video_id(group) == id_video:
                return group.get("translations") or []
        return groups[0].get("translations") or []

    @staticmethod
    def _status_value_needs_attention(key: str, value) -> bool:
        """Recognize the four audio states selected by the channel scanner.

        Studio returns enum-like strings whose prefixes can themselves contain
        words such as ``PROCESSING`` (for example
        ``AUDIO_TRACK_PROCESSING_STATUS_READY``).  Match the terminal state,
        not just that prefix, so a ready track is never selected accidentally.
        """
        def normalize(raw) -> str:
            # Unicode NFKD strips Vietnamese tone marks but does not decompose
            # the distinct letter Đ, so normalize that one explicitly too.
            decomposed = unicodedata.normalize(
                "NFKD", str(raw).upper().replace("Đ", "D")
            )
            return "".join(
                ch
                for ch in decomposed
                if ch.isalnum() and not unicodedata.combining(ch)
            )

        normalized_key = normalize(key)
        status_key = any(
            marker in normalized_key
            for marker in (
                "STATUS",
                "STATE",
                "ERROR",
                "FAIL",
                "REASON",
                "AVAILABILITY",
                "PROCESSING",
            )
        )
        if isinstance(value, bool):
            return value and any(
                marker in normalized_key for marker in ("ERROR", "FAIL", "PROCESSING")
            )
        if not status_key or not isinstance(value, str):
            return False

        normalized_value = normalize(value)
        if not normalized_value:
            return False
        if normalized_value in {
            "0",
            "FALSE",
            "NONE",
            "NOERROR",
            "OK",
            "READY",
            "SUCCESS",
            "SUCCEEDED",
            "COMPLETE",
            "COMPLETED",
            "UNSPECIFIED",
        } or any(
            normalized_value.endswith(marker)
            for marker in (
                "ERRORNONE",
                "STATUSOK",
                "STATUSREADY",
                "STATUSSUCCESS",
                "STATUSSUCCEEDED",
                "STATUSCOMPLETE",
                "STATUSCOMPLETED",
            )
        ):
            return False
        if any(
            marker in normalized_value
            for marker in (
                "FAILED",
                "FAILURE",
                "ERROR",
                "UNPROCESSABLE",
                "UNABLETOPROCESS",
                "CANNOTPROCESS",
                "COULDNOTPROCESS",
                "REJECTED",
                "SPEECHNOTDETECTED",
                "INELIGIBLE",
                "NOTELIGIBLE",
                "INSUFFICIENTELIGIBILITY",
                "UNSUPPORTED",
                "DELETED",
                "REMOVED",
                "KHONGXULYDUOC",
                "KHONGDUDIEUKIEN",
                "DAXOA",
            )
        ):
            return True

        # These are the non-terminal states rendered by Studio as "Đang xử lý".
        # endswith() avoids matching READY/COMPLETED values whose enum namespace
        # happens to contain AUDIO_TRACK_PROCESSING_STATUS.
        if normalized_value in {
            "PROCESSING",
            "PENDING",
            "TRANSCODING",
            "UPLOADING",
            "INPROGRESS",
            "DANGXULY",
        } or normalized_value.endswith(
            (
                "STATUSPROCESSING",
                "STATEPROCESSING",
                "STATUSPENDING",
                "STATEPENDING",
                "STATUSTRANSCODING",
                "STATETRANSCODING",
                "STATUSUPLOADING",
                "STATEUPLOADING",
                "STATUSINPROGRESS",
                "STATEINPROGRESS",
            )
        ):
            return True

        # Some Studio payloads put a reason code below an error/failure object.
        if any(marker in normalized_key for marker in ("ERROR", "FAIL")):
            return True
        return False

    @classmethod
    def _audio_payload_needs_attention(
        cls, payload, *, assume_audio: bool = False
    ) -> bool:
        """Inspect only audio/dubbing status containers in a Studio payload.

        Depending on the channel feature rollout, a translation row can return
        the audio column through legacy ``audioTranslation`` data or through
        newer Aloud and automatic-dubbing containers. Traversal stays inside
        those containers so caption-editor and video-level eligibility states
        cannot select a video.
        """

        def normalize_key(raw) -> str:
            return "".join(ch for ch in str(raw).upper() if ch.isalnum())

        def is_audio_container(key: str) -> bool:
            normalized = normalize_key(key)
            return any(
                marker in normalized
                for marker in (
                    "AUDIO",
                    "DUBBING",
                    "AUTODUB",
                    "ALOUD",
                )
            )

        def walk(value, parent_key: str = "", in_audio: bool = False) -> bool:
            audio_context = in_audio or is_audio_container(parent_key)
            if audio_context and cls._status_value_needs_attention(parent_key, value):
                return True
            if isinstance(value, dict):
                return any(
                    walk(
                        child,
                        f"{parent_key}.{key}" if parent_key else str(key),
                        audio_context or is_audio_container(str(key)),
                    )
                    for key, child in value.items()
                )
            if isinstance(value, (list, tuple)):
                return any(walk(child, parent_key, audio_context) for child in value)
            return False

        return walk(payload, in_audio=assume_audio)

    @staticmethod
    def _status_value_is_terminal_failure(key: str, value) -> bool:
        """Return true only for an audio state which has definitively failed.

        The broader scanner intentionally treats PROCESSING/PENDING as needing
        attention so it can show those videos in diagnostic views.  Repair
        flows must be stricter: replacing a track which YouTube is still
        processing can create a duplicate, and READY/PUBLISHED tracks must
        never be touched.
        """

        def normalize(raw) -> str:
            decomposed = unicodedata.normalize(
                "NFKD", str(raw).upper().replace("Đ", "D")
            )
            return "".join(
                ch
                for ch in decomposed
                if ch.isalnum() and not unicodedata.combining(ch)
            )

        normalized_key = normalize(key)
        status_key = any(
            marker in normalized_key
            for marker in (
                "STATUS",
                "STATE",
                "ERROR",
                "FAIL",
                "REASON",
                "AVAILABILITY",
                "PROCESSING",
            )
        )
        if isinstance(value, bool):
            return value and any(
                marker in normalized_key for marker in ("ERROR", "FAIL")
            )
        if not status_key or not isinstance(value, str):
            return False

        normalized_value = normalize(value)
        if not normalized_value:
            return False
        if normalized_value in {
            "0",
            "FALSE",
            "NONE",
            "NOERROR",
            "OK",
            "READY",
            "SUCCESS",
            "SUCCEEDED",
            "COMPLETE",
            "COMPLETED",
            "PUBLISHED",
            "PROCESSING",
            "PENDING",
            "TRANSCODING",
            "UPLOADING",
            "INPROGRESS",
            "DANGXULY",
            "UNSPECIFIED",
        } or normalized_value.endswith(
            (
                "ERRORNONE",
                "STATUSOK",
                "STATUSREADY",
                "STATUSSUCCESS",
                "STATUSSUCCEEDED",
                "STATUSCOMPLETE",
                "STATUSCOMPLETED",
                "STATUSPUBLISHED",
                "STATEPUBLISHED",
                "STATUSPROCESSING",
                "STATEPROCESSING",
                "STATUSPENDING",
                "STATEPENDING",
                "STATUSTRANSCODING",
                "STATETRANSCODING",
                "STATUSUPLOADING",
                "STATEUPLOADING",
                "STATUSINPROGRESS",
                "STATEINPROGRESS",
                "REASONUNSPECIFIED",
            )
        ):
            return False
        if any(
            marker in normalized_value
            for marker in (
                "FAILED",
                "FAILURE",
                "ERROR",
                "UNPROCESSABLE",
                "UNABLETOPROCESS",
                "CANNOTPROCESS",
                "COULDNOTPROCESS",
                "REJECTED",
                "SPEECHNOTDETECTED",
                "INELIGIBLE",
                "NOTELIGIBLE",
                "INSUFFICIENTELIGIBILITY",
                "UNSUPPORTED",
                "DELETED",
                "REMOVED",
                "KHONGXULYDUOC",
                "KHONGDUDIEUKIEN",
                "DAXOA",
            )
        ):
            return True
        return any(marker in normalized_key for marker in ("ERROR", "FAIL"))

    @classmethod
    def _audio_payload_has_terminal_failure(
        cls, payload, *, assume_audio: bool = False
    ) -> bool:
        """Inspect audio containers for FAILED/REJECTED/etc., not in-flight states."""

        def normalize_key(raw) -> str:
            return "".join(ch for ch in str(raw).upper() if ch.isalnum())

        def is_audio_container(key: str) -> bool:
            normalized = normalize_key(key)
            return any(
                marker in normalized
                for marker in ("AUDIO", "DUBBING", "AUTODUB", "ALOUD")
            )

        def walk(value, parent_key: str = "", in_audio: bool = False) -> bool:
            audio_context = in_audio or is_audio_container(parent_key)
            if audio_context and cls._status_value_is_terminal_failure(
                parent_key, value
            ):
                return True
            if isinstance(value, dict):
                return any(
                    walk(
                        child,
                        f"{parent_key}.{key}" if parent_key else str(key),
                        audio_context or is_audio_container(str(key)),
                    )
                    for key, child in value.items()
                )
            if isinstance(value, (list, tuple)):
                return any(walk(child, parent_key, audio_context) for child in value)
            return False

        return walk(payload, in_audio=assume_audio)

    @staticmethod
    def _is_creator_dubbed_track(track: dict) -> bool:
        """Return whether ``track`` represents a creator-uploaded dub.

        Studio also exposes the source/original audio in the translations
        response.  Its eligibility can be rendered as the black/grey locked
        "Không đủ điều kiện" row, but that row is not a failed dub and
        must never make the scanner select the video.  Failed uploads use the
        canonical pair ``AUDIO_TRACK_SOURCE_CREATOR`` + ``dubbed``.

        Older payloads occasionally omit one or both discriminator fields. In
        that case keep the legacy behaviour and let the audio status decide;
        whenever a discriminator is present it must explicitly describe a
        creator dub.
        """
        if not isinstance(track, dict):
            return False
        source = str(
            track.get("source")
            or track.get("audioTrackSource")
            or ""
        ).upper()
        content_type = str(
            track.get("audioContentTypeString")
            or track.get("audioContentType")
            or ""
        ).upper()
        if source and "CREATOR" not in source:
            return False
        if content_type and "DUB" not in content_type:
            return False
        return True

    @classmethod
    def _is_trackless_source_ineligible_row(cls, item: dict) -> bool:
        """Identify the locked source-language eligibility row.

        A red rejected creator dub has an ``audioTrackId`` (and, in modern
        responses, a matching entry in ``audioTracks``). The source-language
        eligibility row does not. Restrict this exception to INELIGIBLE values
        so trackless PROCESSING/FAILED legacy payloads remain detectable.
        """
        if not isinstance(item, dict):
            return False
        audio = item.get("audioTranslation")
        if not isinstance(audio, dict) or audio.get("audioTrackId"):
            return False

        def contains_ineligible(value) -> bool:
            if isinstance(value, dict):
                return any(contains_ineligible(child) for child in value.values())
            if isinstance(value, (list, tuple)):
                return any(contains_ineligible(child) for child in value)
            if not isinstance(value, str):
                return False
            normalized = "".join(ch for ch in value.upper() if ch.isalnum())
            return any(
                marker in normalized
                for marker in (
                    "INELIGIBLE",
                    "NOTELIGIBLE",
                    "INSUFFICIENTELIGIBILITY",
                    "KHONGDUDIEUKIEN",
                )
            )

        return contains_ineligible(audio)

    @classmethod
    def _audio_translation_needs_attention(cls, item: dict) -> bool:
        """Return true for processing, failed, ineligible, or deleted audio rows."""
        if not isinstance(item, dict) or not cls._audio_payload_needs_attention(item):
            return False
        return not cls._is_trackless_source_ineligible_row(item)

    # Compatibility aliases for callers/tests created before the scanner was
    # expanded beyond failed-only rows.
    _status_value_is_failure = _status_value_needs_attention
    _audio_translation_has_processing_failure = _audio_translation_needs_attention

    @classmethod
    def _audio_translation_has_terminal_failure(cls, item: dict) -> bool:
        if not isinstance(item, dict):
            return False
        if cls._is_trackless_source_ineligible_row(item):
            return False
        return cls._audio_payload_has_terminal_failure(item)

    @classmethod
    def _terminal_repair_targets_from_payload(
        cls,
        payload: dict,
        requested_order: list[str],
    ) -> tuple[dict[str, list[dict]], set[str]]:
        """Extract language-level creator-dub failures from one Studio response.

        The returned mapping contains only terminal failures. READY/PUBLISHED
        and PROCESSING/PENDING rows are deliberately absent. The second return
        value contains requested video IDs which the response did not describe.
        """
        requested = set(requested_order)
        readable_ids: set[str] = set()
        groups = payload.get("videoTranslations") or []
        if not isinstance(groups, list):
            groups = []
        valid_groups = [group for group in groups if isinstance(group, dict)]
        group_ids = [cls._translation_group_video_id(group) for group in valid_groups]
        if valid_groups and all(group_id is None for group_id in group_ids):
            if len(valid_groups) == len(requested_order):
                group_pairs = list(zip(requested_order, valid_groups))
            elif len(requested_order) == 1:
                group_pairs = [(requested_order[0], valid_groups[0])]
            else:
                group_pairs = []
        else:
            group_pairs = [
                (group_id, group)
                for group_id, group in zip(group_ids, valid_groups)
                if group_id in requested
            ]

        translations_by_video: dict[str, list[dict]] = {}
        translation_by_track_id: dict[tuple[str, str], dict] = {}
        for video_id, group in group_pairs:
            readable_ids.add(video_id)
            translations = group.get("translations") or []
            if not isinstance(translations, list):
                continue
            clean_items = [item for item in translations if isinstance(item, dict)]
            translations_by_video[video_id] = clean_items
            for item in clean_items:
                audio = item.get("audioTranslation") or {}
                if not isinstance(audio, dict):
                    continue
                track_id = str(audio.get("audioTrackId") or "").strip()
                if track_id:
                    translation_by_track_id[(video_id, track_id)] = item

        source_track_ids: dict[str, set[str]] = {}
        creator_tracks_by_video: dict[str, list[dict]] = {}
        tracks = payload.get("audioTracks") or []
        if isinstance(tracks, list):
            for track in tracks:
                if not isinstance(track, dict):
                    continue
                video_id = str(track.get("videoId") or "").strip()
                if video_id not in requested:
                    continue
                readable_ids.add(video_id)
                track_id = str(track.get("audioTrackId") or "").strip()
                if not cls._is_creator_dubbed_track(track):
                    if track_id:
                        source_track_ids.setdefault(video_id, set()).add(track_id)
                    continue
                creator_tracks_by_video.setdefault(video_id, []).append(track)

        target_maps: dict[str, dict[str, dict]] = {}

        def add_target(video_id: str, language: str, track_id: str = "") -> None:
            clean_language = str(language or "").strip()
            if not clean_language:
                return
            language_key = clean_language.casefold()
            target = target_maps.setdefault(video_id, {}).setdefault(
                language_key,
                {
                    "language": clean_language,
                    "track_ids": [],
                    "reason": "terminal",
                },
            )
            if track_id and track_id not in target["track_ids"]:
                target["track_ids"].append(track_id)

        for video_id in requested_order:
            creator_track_ids: set[str] = set()
            for track in creator_tracks_by_video.get(video_id, []):
                track_id = str(track.get("audioTrackId") or "").strip()
                if track_id:
                    creator_track_ids.add(track_id)
                if not cls._audio_payload_has_terminal_failure(
                    track, assume_audio=True
                ):
                    continue
                translation = translation_by_track_id.get((video_id, track_id), {})
                language = cls._translation_language(track) or cls._translation_language(
                    translation
                )
                if not language:
                    logger.warning(
                        "Ignoring terminal creator audio without a language: "
                        "video={} track_id={}",
                        video_id,
                        track_id or "none",
                    )
                    continue
                add_target(video_id, language, track_id)

            # Some Studio variants put the terminal status only in the
            # translation row. Root audioTracks remains authoritative whenever
            # it returned the same creator track ID.
            for item in translations_by_video.get(video_id, []):
                audio = item.get("audioTranslation") or {}
                if not isinstance(audio, dict):
                    continue
                track_id = str(audio.get("audioTrackId") or "").strip()
                if track_id in source_track_ids.get(video_id, set()):
                    continue
                if track_id and track_id in creator_track_ids:
                    continue
                if not cls._audio_translation_has_terminal_failure(item):
                    continue
                language = cls._translation_language(item)
                if not language:
                    logger.warning(
                        "Ignoring terminal audio translation without a language: "
                        "video={} track_id={}",
                        video_id,
                        track_id or "none",
                    )
                    continue
                add_target(video_id, language, track_id)

        targets = {
            video_id: list(target_maps.get(video_id, {}).values())
            for video_id in requested_order
            if target_maps.get(video_id)
        }
        return targets, requested - readable_ids

    def get_terminal_audio_repair_targets(
        self,
        video_ids: list[str],
        channel_id: str,
        unreadable_ids: list[str] | None = None,
    ) -> dict[str, list[dict]]:
        """Return exact failed languages/track IDs which are safe to replace."""
        unique_ids = list(dict.fromkeys(video_id for video_id in video_ids if video_id))
        skipped = unreadable_ids if unreadable_ids is not None else []
        targets: dict[str, list[dict]] = {}

        def mark_unreadable(video_id: str) -> None:
            if video_id not in skipped:
                skipped.append(video_id)

        def merge_targets(found: dict[str, list[dict]]) -> None:
            for video_id, actions in found.items():
                by_language = {
                    str(action.get("language") or "").casefold(): action
                    for action in targets.setdefault(video_id, [])
                }
                for action in actions:
                    language = str(action.get("language") or "").strip()
                    if not language:
                        continue
                    key = language.casefold()
                    existing = by_language.get(key)
                    if existing is None:
                        copied = {
                            "language": language,
                            "track_ids": list(action.get("track_ids") or []),
                            "reason": "terminal",
                        }
                        targets[video_id].append(copied)
                        by_language[key] = copied
                    else:
                        for track_id in action.get("track_ids") or []:
                            if track_id not in existing["track_ids"]:
                                existing["track_ids"].append(track_id)

        def scan_chunk(chunk: list[str]) -> None:
            try:
                payload = self._get_video_translation_payload(chunk, channel_id)
            except AudioUpdateError as exc:
                if exc.status_code != 400:
                    raise
                if len(chunk) > 1:
                    midpoint = len(chunk) // 2
                    scan_chunk(chunk[:midpoint])
                    scan_chunk(chunk[midpoint:])
                    return
                mark_unreadable(chunk[0])
                logger.warning(
                    "YouTube terminal audio status is unavailable for video {}: {}",
                    chunk[0],
                    exc,
                )
                return

            found, missing = self._terminal_repair_targets_from_payload(payload, chunk)
            merge_targets(found)
            if not missing:
                return
            if len(chunk) > 1:
                for video_id in chunk:
                    if video_id in missing:
                        scan_chunk([video_id])
                return
            mark_unreadable(chunk[0])
            logger.warning(
                "YouTube terminal audio response omitted video {}", chunk[0]
            )

        for start in range(0, len(unique_ids), self._TRANSLATION_BATCH_SIZE):
            scan_chunk(unique_ids[start : start + self._TRANSLATION_BATCH_SIZE])
        return targets

    def get_audio_attention_video_ids(
        self,
        video_ids: list[str],
        channel_id: str,
        unreadable_ids: list[str] | None = None,
    ) -> set[str]:
        """Return videos with processing, failed, ineligible, or deleted audio."""
        unique_ids = list(dict.fromkeys(video_id for video_id in video_ids if video_id))
        failed_ids: set[str] = set()
        skipped = unreadable_ids if unreadable_ids is not None else []

        def mark_unreadable(video_id: str) -> None:
            if video_id not in skipped:
                skipped.append(video_id)

        def scan_group(
            video_id: str, group: dict, source_track_ids: set[str]
        ) -> None:
            # Only translation rows render the Studio table's Audio column.
            # Group-level auto-dubbing eligibility and captionsTranslations
            # belong to the source caption editor and must not select a video.
            translations = group.get("translations") or []
            if not isinstance(translations, list):
                return
            candidate_items = []
            for item in translations:
                if not isinstance(item, dict):
                    continue
                audio = item.get("audioTranslation") or {}
                track_id = (
                    str(audio.get("audioTrackId") or "").strip()
                    if isinstance(audio, dict)
                    else ""
                )
                if track_id and track_id in source_track_ids:
                    continue
                candidate_items.append(item)
            if any(self._audio_translation_needs_attention(item) for item in candidate_items):
                failed_ids.add(video_id)

        def scan_audio_tracks(
            chunk: list[str], payload: dict
        ) -> tuple[set[str], set[str], dict[str, set[str]]]:
            requested = set(chunk)
            returned_video_ids: set[str] = set()
            creator_dub_video_ids: set[str] = set()
            source_track_ids: dict[str, set[str]] = {}
            tracks = payload.get("audioTracks") or []
            if not isinstance(tracks, list):
                return returned_video_ids, creator_dub_video_ids, source_track_ids
            for track in tracks:
                if not isinstance(track, dict):
                    continue
                video_id = track.get("videoId")
                if video_id not in requested:
                    continue
                returned_video_ids.add(video_id)
                if not self._is_creator_dubbed_track(track):
                    # Original/source audio can itself be ineligible. It is
                    # represented by the black lock in Studio and is not an
                    # uploaded dub which this tool can repair.
                    track_id = str(track.get("audioTrackId") or "").strip()
                    if track_id:
                        source_track_ids.setdefault(video_id, set()).add(track_id)
                    continue
                creator_dub_video_ids.add(video_id)
                # audioTracks[] is the canonical source for the status rendered
                # in Studio's Audio column. It is separate from
                # videoTranslations[], which only contains the audioTrackId.
                if self._audio_payload_needs_attention(track, assume_audio=True):
                    failed_ids.add(video_id)
            return returned_video_ids, creator_dub_video_ids, source_track_ids

        def scan_chunk(chunk: list[str]) -> None:
            try:
                payload = self._get_video_translation_payload(
                    chunk, channel_id
                )
            except AudioUpdateError as exc:
                if exc.status_code != 400:
                    raise
                if len(chunk) > 1:
                    midpoint = len(chunk) // 2
                    scan_chunk(chunk[:midpoint])
                    scan_chunk(chunk[midpoint:])
                    return
                mark_unreadable(chunk[0])
                logger.warning(
                    "YouTube translation status is unavailable for video {}: {}",
                    chunk[0],
                    exc,
                )
                return

            groups = payload.get("videoTranslations") or []
            if not isinstance(groups, list):
                groups = []
            (
                audio_track_video_ids,
                creator_dub_video_ids,
                source_track_ids,
            ) = scan_audio_tracks(chunk, payload)
            valid_groups = [group for group in groups if isinstance(group, dict)]
            group_ids = [
                self._translation_group_video_id(group) for group in valid_groups
            ]
            pairs: list[tuple[str, dict]] = []

            if valid_groups and all(group_id is None for group_id in group_ids):
                if len(valid_groups) == len(chunk):
                    pairs = list(zip(chunk, valid_groups))
                elif len(chunk) == 1:
                    pairs = [(chunk[0], valid_groups[0])]
            else:
                requested = set(chunk)
                pairs = [
                    (group_id, group)
                    for group_id, group in zip(group_ids, valid_groups)
                    if group_id in requested
                ]

            matched_ids = set(audio_track_video_ids)
            for group_id, group in pairs:
                matched_ids.add(group_id)
                # audioTracks[] is authoritative when Studio returned creator
                # dubs for this video. Do not let the source-language row in
                # videoTranslations[] override a READY creator track.
                if group_id not in creator_dub_video_ids:
                    scan_group(
                        group_id,
                        group,
                        source_track_ids.get(group_id, set()),
                    )

            missing_ids = [
                video_id for video_id in chunk if video_id not in matched_ids
            ]
            if not missing_ids:
                return
            if len(chunk) > 1:
                # A successful batch response can still omit individual videos.
                # Retry only those IDs so missing data is not reported as clean.
                for video_id in missing_ids:
                    scan_chunk([video_id])
                return

            mark_unreadable(chunk[0])
            logger.warning(
                "YouTube translation response omitted video {}",
                chunk[0],
            )

        for start in range(0, len(unique_ids), self._TRANSLATION_BATCH_SIZE):
            scan_chunk(unique_ids[start : start + self._TRANSLATION_BATCH_SIZE])
        return failed_ids

    def get_failed_audio_video_ids(
        self,
        video_ids: list[str],
        channel_id: str,
        unreadable_ids: list[str] | None = None,
    ) -> set[str]:
        """Backward-compatible name for the expanded audio-state scanner."""
        return self.get_audio_attention_video_ids(
            video_ids, channel_id, unreadable_ids
        )

    def get_existing_audio_languages(self, id_video: str, channel_id: str) -> set[str]:
        """Return normalized language codes which already have an audio track."""
        languages = set()
        for item in self._get_audio_translation_items(id_video, channel_id):
            audio = item.get("audioTranslation") or {}
            language = self._translation_language(item)
            if audio.get("audioTrackId") and language:
                languages.add(language.casefold())
        return languages

    @staticmethod
    def _translation_language(item: dict) -> str | None:
        containers = [item, item.get("audioTranslation") or {}]
        for container in containers:
            for key in ("languageCode", "language", "targetLanguage", "translationLanguage"):
                value = container.get(key)
                if isinstance(value, str) and value:
                    return value
                if isinstance(value, dict):
                    for nested_key in ("languageCode", "code", "id"):
                        nested = value.get(nested_key)
                        if isinstance(nested, str) and nested:
                            return nested
        return None

    def _has_audio_track(self, id_video: str, channel_id: str, language: str) -> bool:
        expected = language.casefold()
        for attempt in range(3):
            items = self._get_audio_translation_items(id_video, channel_id)
            for item in items:
                audio = item.get("audioTranslation") or {}
                actual = self._translation_language(item)
                if audio.get("audioTrackId") and actual and actual.casefold() == expected:
                    return True
            if attempt < 2:
                wait_interruptibly(2 * (attempt + 1))
        return False

    def _get_all_audio_track_ids(self, id_video: str, channel_id: str):
        track_ids = []
        for item in self._get_audio_translation_items(id_video, channel_id):
            track_id = (item.get("audioTranslation") or {}).get("audioTrackId")
            if track_id:
                track_ids.append(track_id)
        return track_ids


update_audio_module = UpdateAudioModule()
