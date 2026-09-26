# RECOVERED: depyo output corrected from CPython 3.12 disassembly
import os
import time
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
    def delete(self, id_video: str, channel_id: str):
        channel_info = get_channels_info(channel_id); url = "https://studio.youtube.com/youtubei/v1/creator/delete_audio_track?alt=json"; cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies]); session_token = self._get_session_token(channel_info); all_track_ids = self._get_all_audio_track_ids(id_video, channel_id); headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": f"SAPISIDHASH {channel_info.sapisidhash}", "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{id_video}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"}
        for track_id in all_track_ids:
            payload = {"videoId": id_video, "audioTrackId": track_id, "unpublishTrack": False, "context": {"client": {"clientName": 62, "clientVersion": "1.20250902.04.00", "hl": "en", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AWSNWa3PV1e-JQRiHlmMmNXCMA9Kt6en05uq7bbw9WnQgnJdNT8RNsEfMheyglxoOPf_TMIzUzU80CM9khDsuy6zp2Uz9ROtcC5RGvGrdEkSa_rIL5z6FDB2wAAYVWg=", "sessionInfo": {"token": session_token}}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clientScreenNonce": "7nFa5dcSfcGGJAJS"}}
            response = post_with_stop(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise AudioUpdateError(
                    _youtube_error_message(response, "xóa audio track"),
                    status_code=response.status_code,
                    retryable=response.status_code == 429 or response.status_code >= 500,
                )
        return 200
    def _get_video_translation_groups(
        self, video_ids: list[str], channel_id: str
    ) -> list[dict]:
        """Fetch Studio translation data for one batch of videos."""
        if not video_ids:
            return []
        url = "https://studio.youtube.com/youtubei/v1/crowdsourcing/get_video_translations?alt=json"
        channel_info = get_channels_info(channel_id)
        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies])
        session_token = self._get_session_token(channel_info)
        headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": f"SAPISIDHASH {channel_info.sapisidhash}", "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{video_ids[0]}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"}
        payload = {"context": {"client": {"clientName": 62, "clientVersion": "1.20250902.04.00", "hl": "en", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AWSNWa3PV1e-JQRiHlmMmNXCMA9Kt6en05uq7bbw9WnQgnJdNT8RNsEfMheyglxoOPf_TMIzUzU80CM9khDsuy6zp2Uz9ROtcC5RGvGrdEkSa_rIL5z6FDB2wAAYVWg=", "sessionInfo": {"token": session_token}, "consistencyTokenJars": []}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": ""}, "clientScreenNonce": "7nFa5dcSfcGGJAJS"}, "videoIds": video_ids, "filters": [], "fetchAloudData": False, "fetchAutoDubbingData": False, "fetchAutoDubbingAsrData": False, "fetchBulkActionsStatus": False}
        response = post_with_stop(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise AudioUpdateError(
                _youtube_error_message(response, "đọc danh sách audio track"),
                status_code=response.status_code,
                retryable=response.status_code == 429 or response.status_code >= 500,
            )
        return response.json().get("videoTranslations") or []

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
    def _status_value_is_failure(key: str, value) -> bool:
        """Recognize YouTube Studio failure enums without treating ineligible as failed."""
        normalized_key = "".join(ch for ch in str(key).upper() if ch.isalnum())
        status_key = any(
            marker in normalized_key
            for marker in (
                "STATUS",
                "STATE",
                "ERROR",
                "FAIL",
                "REASON",
                "AVAILABILITY",
            )
        )
        if isinstance(value, bool):
            return value and any(marker in normalized_key for marker in ("ERROR", "FAIL"))
        if not status_key or not isinstance(value, str):
            return False

        normalized_value = "".join(ch for ch in value.upper() if ch.isalnum())
        if not normalized_value or any(
            marker in normalized_value
            for marker in ("INELIGIBLE", "NOTELIGIBLE", "INSUFFICIENTELIGIBILITY")
        ):
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
            "UNSPECIFIED",
        } or any(
            normalized_value.endswith(marker)
            for marker in ("ERRORNONE", "STATUSOK", "STATUSREADY", "STATUSSUCCEEDED")
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
            )
        ):
            return True

        # Some Studio payloads put a reason code below an error/failure object.
        if any(marker in normalized_key for marker in ("ERROR", "FAIL")):
            return True
        return False

    @classmethod
    def _audio_translation_has_processing_failure(cls, item: dict) -> bool:
        """Return true for an audio row rendered by Studio as processing failed."""
        audio = item.get("audioTranslation") or {}
        automatic_audio_rows = item.get("captionsTranslations") or []

        def walk(value, parent_key: str = "") -> bool:
            if cls._status_value_is_failure(parent_key, value):
                return True
            if isinstance(value, dict):
                return any(
                    walk(child, f"{parent_key}.{key}" if parent_key else str(key))
                    for key, child in value.items()
                )
            if isinstance(value, (list, tuple)):
                return any(walk(child, parent_key) for child in value)
            return False

        # Studio currently exposes uploaded audio as audioTranslation and some
        # automatic dubbing failures through captionsTranslations/processingEta.
        # Limit inspection to these objects so titles cannot cause a false match.
        if isinstance(audio, dict) and walk(audio):
            return True
        return isinstance(automatic_audio_rows, list) and any(
            isinstance(row, dict) and walk(row) for row in automatic_audio_rows
        )

    def get_failed_audio_video_ids(
        self,
        video_ids: list[str],
        channel_id: str,
        unreadable_ids: list[str] | None = None,
    ) -> set[str]:
        """Return videos which contain at least one failed audio translation row."""
        unique_ids = list(dict.fromkeys(video_id for video_id in video_ids if video_id))
        failed_ids: set[str] = set()
        skipped = unreadable_ids if unreadable_ids is not None else []

        def scan_chunk(chunk: list[str]) -> None:
            try:
                groups = self._get_video_translation_groups(
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
                skipped.append(chunk[0])
                logger.warning(
                    "YouTube translation status is unavailable for video {}: {}",
                    chunk[0],
                    exc,
                )
                return

            group_ids = [self._translation_group_video_id(group) for group in groups]

            if groups and any(group_id is None for group_id in group_ids):
                if len(groups) == len(chunk):
                    group_ids = chunk
                elif len(chunk) == 1:
                    group_ids = chunk
                else:
                    # A response without videoId cannot safely be paired when
                    # YouTube omitted one or more clean videos from the batch.
                    for video_id in chunk:
                        scan_chunk([video_id])
                    return

            for group_id, group in zip(group_ids, groups):
                if not group_id:
                    continue
                items = group.get("translations") or []
                if any(
                    self._audio_translation_has_processing_failure(item)
                    for item in items
                ):
                    failed_ids.add(group_id)

        for start in range(0, len(unique_ids), self._TRANSLATION_BATCH_SIZE):
            scan_chunk(unique_ids[start : start + self._TRANSLATION_BATCH_SIZE])
        return failed_ids

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
