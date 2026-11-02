# RECOVERED: depyo output corrected from CPython 3.12 disassembly
import os
import time
import unicodedata
from io import BytesIO
from urllib.parse import quote
import requests
from loguru import logger
from src.module.base import IModule
from src.module.model import ChannelInfo
from src.utils import get_channels_info
from src.task_runtime import TaskStopped, check_stopped, post_with_stop, wait_interruptibly
from src.youtube_auth import studio_authorization_header


class AudioUpdateError(Exception):
    """An API error with a user-facing message and retry information."""

    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class _AudioUploadBody(BytesIO):
    """Report bytes handed to HTTP without waiting for a whole chunk's reply."""

    def __init__(self, data: bytes, offset: int, progress: dict | None):
        super().__init__(data)
        self._size = len(data)
        self._offset = offset
        self._progress = progress

    def __len__(self) -> int:
        return self._size

    def read(self, size: int = -1) -> bytes:
        check_stopped()
        block = super().read(size)
        if block and self._progress is not None:
            sent = self._offset + self.tell()
            self._progress.update(
                sent=sent,
                updated_at=time.monotonic(),
                status="finalizing" if sent >= self._progress["total"] else "uploading",
            )
        return block


class _AudioUploadFile:
    """Stream one whole HTTP body without buffering the complete music file."""

    def __init__(self, source, size: int, progress: dict | None):
        self.source = source
        self.size = size
        self.progress = progress

    def __len__(self):
        return self.size

    def __iter__(self):
        return self

    def __next__(self):
        block = self.read(64 * 1024)
        if not block:
            raise StopIteration
        return block

    def tell(self):
        return self.source.tell()

    def seek(self, offset, whence=0):
        return self.source.seek(offset, whence)

    def read(self, size=-1):
        check_stopped()
        remaining = self.size - self.tell()
        block = self.source.read(remaining if size is None or size < 0 else min(size, remaining))
        if not block and remaining:
            raise AudioUpdateError("File audio bị thay đổi hoặc không đọc đủ dữ liệu khi tải lên")
        if self.progress is not None:
            self.progress.update(sent=self.tell(), updated_at=time.monotonic(),
                                 status="finalizing" if self.tell() >= self.size else "uploading")
        return block

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        # The upload loop owns the file across retries and closes it once.
        pass


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

    @staticmethod
    def _serialized_delegation_context(channel_info) -> str:
        captured = getattr(channel_info, "studio_context", {}) or {}
        user = captured.get("user") or {} if isinstance(captured, dict) else {}
        if not isinstance(user, dict):
            raise AudioUpdateError("Ngữ cảnh đăng nhập không hợp lệ; hãy quét lại kênh")
        delegation = user.get("delegationContext") or {}
        if not isinstance(delegation, dict):
            raise AudioUpdateError("Thông tin ủy quyền kênh không hợp lệ; hãy quét lại kênh")
        if delegation.get("externalChannelId") not in (None, "", channel_info.id):
            raise AudioUpdateError("Ngữ cảnh đăng nhập thuộc kênh khác; hãy quét lại đúng kênh trước khi sửa audio")
        value = getattr(channel_info, "serialized_delegation_context", "") or user.get("serializedDelegationContext", "")
        return value if isinstance(value, str) else ""

    def add(
        self,
        id_video: str,
        channel_id: str,
        file_name: str,
        language: str,
        data: bytes | None = None,
        progress: dict | None = None,
        upload_path: str | None = None,
        audio_content_type: str = "dubbed",
    ):
        if audio_content_type not in ("dubbed", "descriptive"):
            raise ValueError(f"Unsupported audio content type: {audio_content_type}")
        check_stopped()
        source_path = (upload_path or file_name) if data is None else None
        file_size = len(data) if data is not None else os.path.getsize(source_path)
        if file_size <= 0:
            raise AudioUpdateError("File audio rỗng, không thể tải lên")
        if progress is not None:
            progress.update(file_finalized=False, registered=False, track_id="", track_status="", studio_state="")
        before = self._audio_upload_snapshot(id_video, channel_id, language, audio_content_type)
        if any(self._audio_upload_track_state(track) == "published" for track in before.values()):
            if progress is not None:
                progress.update(status="complete", studio_state="published")
            return 409
        if any(self._audio_upload_track_state(track) == "processing" for track in before.values()):
            raise AudioUpdateError(f"YouTube đang xử lý {audio_content_type} ({language}); giữ track hiện có")
        if progress is not None:
            progress["status"] = "authenticating"
        channel_info = get_channels_info(channel_id)
        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies])
        fname_header = quote(os.path.basename(file_name), safe="")
        with requests.Session() as session:
            if progress is not None:
                progress["status"] = "starting"
            upload_url, scotty_resource_id = self._upload_http(
                fname_header=fname_header,
                cookie_string=cookie_string,
                session=session,
            )
            # Finish the file before publishing its resource, as with Studio's
            # file picker followed by Publish. A pending resource must never be
            # mistaken for a successfully uploaded language track.
            self._next_upload_http(
                next_url=upload_url,
                fname_header=fname_header,
                cookie_string=cookie_string,
                data=data,
                file_path=source_path,
                progress=progress,
                session=session,
                single_request=True,
            )
            if progress is not None:
                progress.update(file_finalized=True, status="registering")
            # Large files can outlive the session-token cache's TTL.
            session_token = self._get_session_token(channel_info)
            res = self._update(
                video_id=id_video,
                scotty_resource_id=scotty_resource_id,
                channel_info=channel_info,
                session_token=session_token,
                cookie_string=cookie_string,
                language=language,
                session=session,
                audio_content_type=audio_content_type,
            )
            if res == 409:
                if self._has_audio_track(
                    id_video, channel_id, language,
                    audio_content_type=audio_content_type,
                ):
                    logger.info("Audio track already exists: video={} language={}", id_video, language)
                    return 409
                raise AudioUpdateError(
                    "YouTube báo xung đột (409) nhưng audio track chưa READY/PUBLISHED "
                    "(có thể đang xử lý hoặc đã lỗi); không coi là thành công.",
                    status_code=409,
                )
            if progress is not None:
                progress["registered"] = True
            self._verify_audio_upload(
                id_video, channel_id, language, audio_content_type, before,
                progress=progress,
            )
            return res

    def _audio_upload_snapshot(self, video_id, channel_id, language, content_type):
        payload = self._get_video_translation_payload([video_id], channel_id)
        if video_id not in self._readable_translation_video_ids(payload, [video_id]):
            raise AudioUpdateError("Không đọc được audio của đúng video để xác nhận tải lên")
        return {
            str(track["audioTrackId"]): track
            for track in self._video_audio_tracks(payload, video_id)
            if (self._translation_language(track) or "").casefold() == language.casefold()
            and str(track.get("audioContentTypeString") or track.get("audioContentType") or
                    ("dubbed" if self._is_creator_dubbed_track(track) else "")).casefold() == content_type
        }

    def _verify_audio_upload(self, video_id, channel_id, language, content_type, before, *, progress=None):
        if progress is not None:
            progress["status"] = "verifying"
        last = "missing"
        for attempt in range(4):
            check_stopped()
            tracks = self._audio_upload_snapshot(video_id, channel_id, language, content_type)
            candidates = {
                track_id: track for track_id, track in tracks.items()
                if track_id not in before or (
                    self._audio_upload_track_state(before[track_id]) == "failed"
                    and self._audio_upload_track_state(track) in {"processing", "published"}
                )
            }
            for track_id, track in sorted(candidates.items(), key=lambda item: (
                {"published": 0, "processing": 1, "failed": 2, "unknown": 3}[self._audio_upload_track_state(item[1])],
                item[0],
            )):
                last = str(track.get("status") or track.get("publishStatus") or "unknown")
                state = self._audio_upload_track_state(track)
                if state == "failed":
                    reason = str(track.get("failureReason") or track.get("rejectedReason") or "unknown")
                    if progress is not None:
                        progress.update(status="error", track_id=track_id, track_status=last)
                    raise AudioUpdateError(
                        f"YouTube trả {last} sau khi tải {content_type} ({language}); "
                        f"track={track_id}, reason={reason}. Không tính là đã thêm thành công."
                    )
                if state in {"published", "processing"}:
                    if progress is not None:
                        progress.update(status="complete", track_id=track_id, track_status=last,
                                        studio_state=state)
                    logger.info(
                        "YouTube audio upload verified: video={} language={} type={} track_id={} status={}",
                        video_id, language, content_type, track_id, last,
                    )
                    return
            if tracks and not candidates:
                last = "unchanged: " + ",".join(sorted(tracks))
            if attempt < 3:
                wait_interruptibly(2 * (attempt + 1))
        if progress is not None:
            progress["status"] = "error"
        raise AudioUpdateError(
            f"YouTube chưa xác nhận track mới {content_type} ({language}) trên video {video_id}: {last}. "
            "Không tính là đã thêm thành công; kiểm tra lại Studio trước khi thử lại."
        )

    @classmethod
    def _audio_upload_track_state(cls, track):
        if cls._audio_payload_has_terminal_failure(track, assume_audio=True):
            return "failed"
        if cls._audio_payload_needs_attention(track, assume_audio=True):
            return "processing"
        for key in ("status", "publishStatus", "servingStatus"):
            value = str(track.get(key) or "").upper()
            if value in {"READY", "PROCESSED", "PUBLISHED", "SERVING"} or value.endswith(
                ("_STATUS_READY", "_STATUS_PROCESSED", "_PUBLISHED", "_SERVING")
            ):
                return "published"
        return "unknown"

    @staticmethod
    def _check_audio_rpc_response(response, action):
        try:
            payload = response.json()
        except (ValueError, AttributeError) as exc:
            raise AudioUpdateError(f"YouTube trả phản hồi {action} không phải JSON hợp lệ") from exc
        if not isinstance(payload, dict):
            raise AudioUpdateError(f"YouTube trả cấu trúc phản hồi {action} không hợp lệ")
        error = payload.get("error")
        if error:
            code = error.get("code") if isinstance(error, dict) else None
            message = str(error.get("message") or error.get("status") or "unknown") if isinstance(error, dict) else "unknown"
            raise AudioUpdateError(
                f"YouTube từ chối {action}: {message[:400]}", status_code=code,
                retryable=code == 429 or isinstance(code, int) and code >= 500,
            )
        return payload

    def _upload_http(
        self,
        fname_header: str,
        cookie_string: str,
        session: requests.Session | None = None,
    ):
        url = "https://upload.youtube.com/upload/audiotrack?authuser=0"
        headers = self._base_upload_headers(fname_header, cookie_string)
        # Match TV Automation's audiotrack initialization (the body is just {}).
        headers.update({"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start"})
        response = post_with_stop(url, headers=headers, data="{}", session=session)
        if response.status_code != 200:
            raise AudioUpdateError(_youtube_error_message(response, "khởi tạo tải audio"), status_code=response.status_code, retryable=response.status_code == 429 or response.status_code >= 500)
        status = str(response.headers.get("X-Goog-Upload-Status") or "").lower()
        if status and status != "active":
            raise AudioUpdateError(f"YouTube không mở phiên tải audio: {status}")
        upload_url = response.headers.get("X-Goog-Upload-URL")
        scotty_id = response.headers.get("X-Goog-Upload-Header-Scotty-Resource-Id")
        if not upload_url or not scotty_id:
            raise AudioUpdateError("YouTube không trả đủ thông tin phiên tải audio")
        return (upload_url, scotty_id)
    def _base_upload_headers(self, fname_header: str, cookie_string: str) -> dict:
        return {
            "Host": "upload.youtube.com",
            "Cookie": cookie_string,
            "X-Goog-Upload-File-Name": fname_header,
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Ch-Ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
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
        upload_state: dict | None = None,
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
            if upload_state is not None:
                upload_state["status"] = str(response.headers.get("X-Goog-Upload-Status") or "").lower()
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
        single_request: bool = False,
    ) -> str:
        """Upload a complete body like TV Automation, with resumable retries."""
        base_headers = self._base_upload_headers(fname_header, cookie_string)
        if data is None and not file_path:
            raise AudioUpdateError("Không có dữ liệu audio để tải lên")
        total = len(data) if data is not None else os.path.getsize(str(file_path))
        if total <= 0:
            raise AudioUpdateError("File audio rỗng, không thể tải lên")
        offset = 0
        retries = 0
        needs_finalize = False
        finalize_attempts = 0
        started_at = time.monotonic()
        if progress is not None:
            progress.update(
                sent=0,
                confirmed=0,
                total=total,
                started_at=started_at,
                updated_at=started_at,
                status="uploading",
            )
        source_file = open(file_path, "rb") if data is None else None
        try:
            while offset < total or needs_finalize:
                check_stopped()
                end = total if single_request else min(offset + self._CHUNK_SIZE, total)
                if single_request and source_file is not None and offset < total:
                    source_file.seek(offset)
                    body = _AudioUploadFile(source_file, total, progress)
                    body_size = end - offset
                elif source_file is not None:
                    source_file.seek(offset)
                    chunk = source_file.read(end - offset)
                    body = _AudioUploadBody(chunk, offset, progress)
                    body_size = len(chunk)
                else:
                    chunk = data[offset:end]
                    body = _AudioUploadBody(chunk, offset, progress)
                    body_size = len(chunk)
                if not body_size and not needs_finalize:
                    raise AudioUpdateError(
                        f"Không đọc được audio tại vị trí {offset}/{total} byte"
                    )
                headers = dict(base_headers)
                headers["X-Goog-Upload-Offset"] = str(offset)
                headers["X-Goog-Upload-Command"] = "upload, finalize" if end == total else "upload"
                try:
                    with body:
                        response = post_with_stop(
                            next_url,
                            headers=headers,
                            data=body if body_size else b"",
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
                    try:
                        upload_payload = response.json()
                    except (ValueError, AttributeError):
                        upload_payload = {}
                    if isinstance(upload_payload, dict) and upload_payload.get("error"):
                        self._check_audio_rpc_response(response, "hoàn tất file audio")
                    server_status = str(response.headers.get("X-Goog-Upload-Status") or "").lower()
                    if not server_status:
                        upload_state = {}
                        self._query_upload_offset(next_url, base_headers, session=session, upload_state=upload_state)
                        server_status = upload_state.get("status", "")
                        if not server_status:
                            raise AudioUpdateError("YouTube không xác nhận trạng thái phiên tải file; không coi là đã tải xong")
                    if server_status and server_status not in {"active", "final"}:
                        raise AudioUpdateError(f"YouTube từ chối phiên tải audio: {server_status}")
                    offset += body_size
                    needs_finalize = offset >= total and server_status == "active"
                    if needs_finalize:
                        finalize_attempts += 1
                        if finalize_attempts > self._MAX_UPLOAD_RETRIES:
                            raise AudioUpdateError("YouTube chưa xác nhận hoàn tất tải audio; không coi là đã tải xong")
                        wait_interruptibly(min(finalize_attempts, 3))
                    retries = 0
                    if progress is not None:
                        progress["sent"] = offset
                        progress["confirmed"] = offset
                        progress["updated_at"] = time.monotonic()
                        progress["status"] = "finalizing" if needs_finalize else "complete" if offset >= total else "uploading"
                except TaskStopped:
                    raise
                except Exception as exc:
                    if isinstance(exc, AudioUpdateError) and not exc.retryable:
                        if progress is not None:
                            progress["status"] = "error"
                        raise
                    retries += 1
                    if retries > self._MAX_UPLOAD_RETRIES:
                        if progress is not None:
                            progress["status"] = "error"
                        raise AudioUpdateError(
                            f"Tải audio bị gián đoạn tại {offset}/{total} byte sau "
                            f"{self._MAX_UPLOAD_RETRIES} lần thử: {exc}",
                            status_code=getattr(exc, "status_code", None),
                        ) from exc
                    upload_state = {}
                    server_offset = self._query_upload_offset(
                        next_url,
                        base_headers,
                        session=session,
                        upload_state=upload_state,
                    )
                    if upload_state.get("status") == "final":
                        offset = total
                        needs_finalize = False
                    elif server_offset is not None and 0 <= server_offset <= total:
                        offset = server_offset
                        needs_finalize = offset >= total and upload_state.get("status") != "final"
                    if progress is not None:
                        progress["sent"] = offset
                        progress["confirmed"] = offset
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
        if progress is not None:
            progress["status"] = "complete"
        return "final"
    def _update(self, video_id: str, scotty_resource_id: str, channel_info: ChannelInfo, cookie_string: str, session_token: str, language: str, session: requests.Session | None = None, audio_content_type: str = "dubbed"):
        url = "https://studio.youtube.com/youtubei/v1/creator/add_audio_track?alt=json"; headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": studio_authorization_header(channel_info.cookies), "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{video_id}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}; payload = {"videoId": video_id, "resourceId": {"scottyResourceId": {"id": scotty_resource_id}}, "language": language, "audioContentTypeString": audio_content_type, "audioTrackSource": "AUDIO_TRACK_SOURCE_CREATOR", "context": {"client": {"clientName": 62, "clientVersion": "1.20250902.04.00", "hl": "en", "gl": "VN", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AWSNWa0l7AGlCHtnt233UutuGGeh33lZ817vfraxpNhL8LY5gqkpaiN73HzUXyRRQ2ApQuCVRfHRtr9rlEQ8rczpjRVn_mm0nP74Qdc4IR95HbzJKhorwIoTVAqfC4o=", "sessionInfo": {"token": session_token}}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": self._serialized_delegation_context(channel_info)}, "clickTracking": {"visualElement": {"veType": 74_618}}, "clientScreenNonce": "UUFKQY_AX3QaOzkG"}}; response = post_with_stop(url, headers=headers, json=payload, session=session)
        if response.status_code not in (200, 409):
            logger.error("YouTube add_audio_track failed: status={} body={}", response.status_code, response.text[:1000])
            raise AudioUpdateError(_youtube_error_message(response, "gắn audio vào video"), status_code=response.status_code, retryable=response.status_code == 429 or response.status_code >= 500)
        if response.status_code == 200:
            self._check_audio_rpc_response(response, "gắn audio vào video")
        return response.status_code
    def delete_track_ids(
        self, id_video: str, channel_id: str, track_ids: list[str]
    ) -> int:
        """Delete only the explicitly selected creator audio tracks.

        Automatic recovery uses this narrow operation so a failed language can
        be replaced without removing healthy/published languages on the same
        video. ``delete`` below removes creator dubs for the manual
        "Xóa & thêm audio" action while preserving source/descriptive tracks.
        """
        unique_track_ids = list(
            dict.fromkeys(str(track_id).strip() for track_id in track_ids if track_id)
        )
        if not unique_track_ids:
            return 200
        channel_info = get_channels_info(channel_id); url = "https://studio.youtube.com/youtubei/v1/creator/delete_audio_track?alt=json"; cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in channel_info.cookies]); session_token = self._get_session_token(channel_info); headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": studio_authorization_header(channel_info.cookies), "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{id_video}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"}
        for track_id in unique_track_ids:
            payload = {"videoId": id_video, "audioTrackId": track_id, "unpublishTrack": False, "context": {"client": {"clientName": 62, "clientVersion": "1.20250902.04.00", "hl": "en", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_DARK", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": "AWSNWa3PV1e-JQRiHlmMmNXCMA9Kt6en05uq7bbw9WnQgnJdNT8RNsEfMheyglxoOPf_TMIzUzU80CM9khDsuy6zp2Uz9ROtcC5RGvGrdEkSa_rIL5z6FDB2wAAYVWg=", "sessionInfo": {"token": session_token}}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": self._serialized_delegation_context(channel_info)}, "clientScreenNonce": "7nFa5dcSfcGGJAJS"}}
            response = post_with_stop(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise AudioUpdateError(
                    _youtube_error_message(response, "xóa audio track"),
                    status_code=response.status_code,
                    retryable=response.status_code == 429 or response.status_code >= 500,
                )
            self._check_audio_rpc_response(response, "xóa audio track")
        self._confirm_audio_tracks_deleted(id_video, channel_id, unique_track_ids)
        return 200

    def _confirm_audio_tracks_deleted(self, video_id: str, channel_id: str, track_ids: list[str]) -> None:
        """Wait for Studio's committed inventory before uploading a replacement."""
        expected = set(track_ids)
        remaining = expected
        for attempt in range(4):
            check_stopped()
            payload = self._get_video_translation_payload([video_id], channel_id)
            if video_id not in self._readable_translation_video_ids(payload, [video_id]):
                raise AudioUpdateError("Không đọc được trạng thái video sau khi xóa audio; chưa thêm bản thay thế")
            remaining = {
                str(track["audioTrackId"])
                for track in self._video_audio_tracks(payload, video_id)
                if str(track["audioTrackId"]) in expected
                and not str(track.get("status") or "").upper().endswith(("DELETED", "REMOVED"))
            }
            if not remaining:
                logger.info("YouTube audio deletion verified: video={} track_ids={}", video_id, ",".join(sorted(expected)))
                return
            if attempt < 3:
                wait_interruptibly(2 * (attempt + 1))
        raise AudioUpdateError(
            "YouTube chưa áp dụng việc xóa audio; chưa thêm bản thay thế. "
            f"video={video_id}, track_ids={','.join(sorted(remaining))}"
        )

    def delete(self, id_video: str, channel_id: str, languages: list[str] | None = None):
        """Delete creator dubs, optionally scoped to exact language codes."""
        return self.delete_track_ids(
            id_video,
            channel_id,
            self._get_all_audio_track_ids(id_video, channel_id)
            if languages is None else self._get_all_audio_track_ids(id_video, channel_id, languages),
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
        headers = {"Host": "studio.youtube.com", "Cookie": cookie_string, "Authorization": studio_authorization_header(channel_info.cookies), "Content-Type": "application/json", "Origin": "https://studio.youtube.com", "Referer": f"https://studio.youtube.com/video/{video_ids[0]}/translations", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"}
        payload = {"context": {"client": {"clientName": 62, "clientVersion": "1.20260924.00.01", "hl": "vi", "gl": "VN", "experimentsToken": "", "utcOffsetMinutes": 420, "userInterfaceTheme": "USER_INTERFACE_THEME_LIGHT", "screenWidthPoints": 1920, "screenHeightPoints": 945, "screenPixelDensity": 1, "screenDensityFloat": 1}, "request": {"returnLogEntry": True, "internalExperimentFlags": [], "eats": self.EATS, "sessionInfo": {"token": session_token}, "consistencyTokenJars": []}, "user": {"onBehalfOfUser": channel_info.delegated_session_id, "delegationContext": {"externalChannelId": channel_info.id, "roleType": {"channelRoleType": channel_info.role}}, "serializedDelegationContext": self._serialized_delegation_context(channel_info)}, "clientScreenNonce": self.CLIENT_SCREEN_NONCE}, "videoIds": video_ids, "filters": ["TRANSLATION_FILTER_DRAFT", "TRANSLATION_FILTER_PUBLISHED"], "fetchAloudData": False, "fetchAutoDubbingData": False, "fetchAutoDubbingAsrData": False, "fetchBulkActionsStatus": False, "fetchDataFromInternalService": False}
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
            "PROCESSED",
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
                "STATUSPROCESSED",
                "STATEPROCESSED",
                "STATUSSUCCESS",
                "STATUSSUCCEEDED",
                "STATUSCOMPLETE",
                "STATUSCOMPLETED",
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
        # Human-readable Studio labels append a percentage, for example
        # ``Đang xử lý... 95%``. READY/COMPLETED enum values were already
        # excluded above, so matching these markers here is safe.
        if any(
            marker in normalized_value
            for marker in (
                "DANGXULY",
                "PROCESSING",
                "PENDING",
                "TRANSCODING",
                "UPLOADING",
                "INPROGRESS",
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
        *,
        include_missing_audio: bool = False,
        include_processing: bool = False,
    ) -> tuple[dict[str, list[dict]], set[str]]:
        """Extract language-level creator-dub failures from one Studio response.

        By default the mapping contains only terminal failures. READY/PUBLISHED
        and PROCESSING/PENDING rows are deliberately absent. The second return
        value contains requested video IDs which the response did not describe.
        Manual scans may opt into PROCESSING/PENDING tracks, or request a
        language-neutral ``missing`` action for a single empty Audio column.
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
        missing_audio_candidates: set[str] = set()
        for video_id, group in group_pairs:
            readable_ids.add(video_id)
            translations = group.get("translations") or []
            if not isinstance(translations, list):
                continue
            clean_items = [item for item in translations if isinstance(item, dict)]
            translations_by_video[video_id] = clean_items
            if (
                include_missing_audio
                and len(translations) == 1
                and len(clean_items) == 1
                and cls._translation_has_no_audio(clean_items[0])
                and cls._translation_language(clean_items[0])
                and cls._translation_row_has_table_content(clean_items[0])
            ):
                missing_audio_candidates.add(video_id)
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

        def add_target(video_id: str, language: str, track_id: str = "", *, reason: str = "terminal") -> None:
            clean_language = str(language or "").strip()
            if not clean_language:
                return
            language_key = clean_language.casefold()
            target = target_maps.setdefault(video_id, {}).setdefault(
                language_key,
                {
                    "language": clean_language,
                    "track_ids": [],
                    "reason": reason,
                },
            )
            if track_id and track_id not in target["track_ids"]:
                target["track_ids"].append(track_id)
            if reason == "terminal":
                target["reason"] = reason

        for video_id in requested_order:
            creator_track_ids: set[str] = set()
            for track in creator_tracks_by_video.get(video_id, []):
                track_id = str(track.get("audioTrackId") or "").strip()
                if track_id:
                    creator_track_ids.add(track_id)
                if cls._audio_payload_has_terminal_failure(track, assume_audio=True):
                    reason = "terminal"
                elif include_processing and track_id and cls._audio_payload_needs_attention(track, assume_audio=True):
                    reason = "processing"
                else:
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
                add_target(video_id, language, track_id, reason=reason)

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
                if cls._audio_translation_has_terminal_failure(item):
                    reason = "terminal"
                elif include_processing and track_id and cls._audio_payload_needs_attention(item):
                    reason = "processing"
                else:
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
                add_target(video_id, language, track_id, reason=reason)

        targets = {
            video_id: list(target_maps.get(video_id, {}).values())
            for video_id in requested_order
            if target_maps.get(video_id)
        }
        for video_id in requested_order:
            if (
                video_id in missing_audio_candidates
                and isinstance(tracks, list)
                and all(isinstance(track, dict) for track in tracks)
                and not creator_tracks_by_video.get(video_id)
                and video_id not in targets
            ):
                targets[video_id] = [
                    {"language": "", "track_ids": [], "reason": "missing"}
                ]
        return targets, requested - readable_ids

    @classmethod
    def _translation_row_has_table_content(cls, item: dict) -> bool:
        """Return True if ``item`` represents an actual row in Studio's Subtitles/Bản dịch table.

        When a video only has its default video language configured in details without
        any published/draft captions or translated metadata, Studio displays an entirely
        empty table ('trống hoàn toàn'). A row only appears in the table when there are
        captions, translated metadata, or audio tracks.
        """
        if not isinstance(item, dict):
            return False
        captions = item.get("captionsTranslations")
        if isinstance(captions, list) and captions:
            for cap in captions:
                if isinstance(cap, dict) and (
                    cap.get("captionTrackId")
                    or str(cap.get("publishStatus") or "").strip().upper() in {"PUBLISHED", "DRAFT"}
                    or str(cap.get("statusLabel") or "").strip()
                ):
                    return True
        caption = item.get("captionTranslation")
        if isinstance(caption, dict) and caption:
            if (
                caption.get("captionTrackId")
                or str(caption.get("publishStatus") or "").strip().upper() in {"PUBLISHED", "DRAFT"}
                or str(caption.get("statusLabel") or "").strip()
            ):
                return True
        for meta_key in ("metadataTranslations", "metadataTranslation", "titleTranslation", "descriptionTranslation"):
            meta = item.get(meta_key)
            if isinstance(meta, dict) and meta:
                return True
            if isinstance(meta, list) and meta:
                return True
        audio = item.get("audioTranslation")
        if isinstance(audio, dict) and audio.get("audioTrackId"):
            return True
        return False

    @staticmethod
    def _translation_has_no_audio(item: dict) -> bool:
        """Recognize an empty Audio column, including Studio's dash label."""
        for key, value in item.items():
            normalized = "".join(ch for ch in str(key).upper() if ch.isalnum())
            if not any(marker in normalized for marker in ("AUDIO", "DUBBING", "ALOUD")):
                continue
            if value is None or value == {}:
                continue
            if (
                key == "audioTranslation"
                and isinstance(value, dict)
                and set(value) <= {"videoId", "statusLabel"}
                and str(value.get("statusLabel") or "").strip() in {"-", "–", "—"}
            ):
                continue
            return False
        return True

    def get_terminal_audio_repair_targets(
        self,
        video_ids: list[str],
        channel_id: str,
        unreadable_ids: list[str] | None = None,
        *,
        include_missing_audio: bool = False,
        include_processing: bool = False,
    ) -> dict[str, list[dict]]:
        """Return exact failed tracks; manual callers can include processing/missing audio."""
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
                    if not language and action.get("reason") == "missing":
                        if "" not in by_language:
                            copied = {"language": "", "track_ids": [], "reason": "missing"}
                            targets[video_id].append(copied)
                            by_language[""] = copied
                        continue
                    if not language:
                        continue
                    key = language.casefold()
                    existing = by_language.get(key)
                    if existing is None:
                        copied = {
                            "language": language,
                            "track_ids": list(action.get("track_ids") or []),
                            "reason": action.get("reason") or "terminal",
                        }
                        targets[video_id].append(copied)
                        by_language[key] = copied
                    else:
                        if action.get("reason") == "terminal":
                            existing["reason"] = "terminal"
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

            found, missing = self._terminal_repair_targets_from_payload(
                payload, chunk, include_missing_audio=include_missing_audio,
                include_processing=include_processing,
            )
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

    def get_original_audio_language(self, id_video: str, channel_id: str) -> str:
        """Read the source track language without guessing from dubbed tracks."""
        payload = self._get_video_translation_payload([id_video], channel_id)
        for track in payload.get("audioTracks") or []:
            if not isinstance(track, dict) or track.get("videoId") != id_video:
                continue
            if str(track.get("audioContentTypeString") or "").casefold() == "original":
                language = self._translation_language(track)
                if language:
                    return language
        return ""

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

    @classmethod
    def _audio_language_state_from_payload(
        cls,
        payload: dict,
        video_id: str,
        language: str,
        audio_content_type: str = "dubbed",
    ) -> str:
        """Return ``healthy``, ``inflight``, ``terminal``, or ``missing``.

        A 409 response only proves that a language row already exists.  It may
        be an orphan whose upload never finalized or a track stuck at 95%.
        Callers must only treat READY/PUBLISHED tracks as already added.
        """
        expected = str(language or "").strip().casefold()
        if not expected:
            return "missing"

        root_tracks: dict[str, dict] = {}
        tracks = payload.get("audioTracks") or []
        if isinstance(tracks, list):
            for track in tracks:
                if not isinstance(track, dict):
                    continue
                track_video_id = str(track.get("videoId") or "").strip()
                if track_video_id and track_video_id != video_id:
                    continue
                track_id = str(track.get("audioTrackId") or "").strip()
                if track_id:
                    root_tracks[track_id] = track

        groups = payload.get("videoTranslations") or []
        if not isinstance(groups, list):
            groups = []
        matching_groups = [
            group
            for group in groups
            if isinstance(group, dict)
            and cls._translation_group_video_id(group) == video_id
        ]
        if not matching_groups and len(groups) == 1 and isinstance(groups[0], dict):
            # Some Studio variants omit videoId for a single-video request.
            matching_groups = [groups[0]]

        states: set[str] = set()
        for group in matching_groups:
            translations = group.get("translations") or []
            if not isinstance(translations, list):
                continue
            for item in translations:
                if not isinstance(item, dict):
                    continue
                actual = cls._translation_language(item)
                if not actual or actual.casefold() != expected:
                    continue
                audio = item.get("audioTranslation") or {}
                if not isinstance(audio, dict):
                    continue
                track_id = str(audio.get("audioTrackId") or "").strip()
                if not track_id:
                    continue
                root_track = root_tracks.get(track_id)
                actual_type = str(
                    (root_track or audio).get("audioContentTypeString")
                    or (root_track or audio).get("audioContentType")
                    or ""
                ).casefold()
                if actual_type != audio_content_type and (
                    actual_type or audio_content_type != "dubbed"
                ):
                    continue
                status_payload = root_track if root_track is not None else item
                if cls._audio_payload_has_terminal_failure(
                    status_payload,
                    assume_audio=root_track is not None,
                ):
                    states.add("terminal")
                elif cls._audio_payload_needs_attention(
                    status_payload,
                    assume_audio=root_track is not None,
                ):
                    states.add("inflight")
                else:
                    states.add("healthy")

        # Some responses expose tracks only at the root. Verify the requested
        # type and language; source audio cannot verify a description conflict.
        for track in root_tracks.values():
            actual_type = str(track.get("audioContentTypeString") or track.get("audioContentType") or "").casefold()
            actual_language = cls._translation_language(track)
            matches_type = actual_type == audio_content_type or (
                not actual_type and audio_content_type == "dubbed" and cls._is_creator_dubbed_track(track)
            )
            if not matches_type or not actual_language or actual_language.casefold() != expected:
                continue
            if cls._audio_payload_has_terminal_failure(track, assume_audio=True):
                states.add("terminal")
            elif cls._audio_payload_needs_attention(track, assume_audio=True):
                states.add("inflight")
            elif str(track.get("status") or "").upper() in (
                "AUDIO_TRACK_STATUS_READY", "AUDIO_TRACK_STATUS_PROCESSED", "READY", "PROCESSED", "PUBLISHED",
            ) or str(track.get("publishStatus") or "").upper() == "PUBLISHED":
                states.add("healthy")

        # A good duplicate always wins. Never replace it because an older copy
        # of the same language is still processing or failed.
        if "healthy" in states:
            return "healthy"
        if "inflight" in states:
            return "inflight"
        if "terminal" in states:
            return "terminal"
        return "missing"

    def _has_audio_track(
        self, id_video: str, channel_id: str, language: str,
        audio_content_type: str = "dubbed",
    ) -> bool:
        """Return true only when the existing language is READY/PUBLISHED."""
        for attempt in range(3):
            payload = self._get_video_translation_payload([id_video], channel_id)
            state = self._audio_language_state_from_payload(
                payload,
                id_video,
                language,
                audio_content_type=audio_content_type,
            )
            if state == "healthy":
                return True
            if attempt < 2:
                wait_interruptibly(2 * (attempt + 1))
        return False

    @classmethod
    def _video_audio_tracks(cls, payload: dict, video_id: str) -> list[dict]:
        """Join typed root tracks to their language rows without mixing videos."""
        groups = [group for group in payload.get("videoTranslations") or [] if isinstance(group, dict)]
        matching = [group for group in groups if cls._translation_group_video_id(group) == video_id]
        if not matching and len(groups) == 1 and cls._translation_group_video_id(groups[0]) is None:
            matching = groups
        roots = {
            str(track["audioTrackId"]): track
            for track in payload.get("audioTracks") or []
            if isinstance(track, dict) and track.get("audioTrackId")
            and track.get("videoId") in (None, "", video_id)
        }
        foreign_ids = {
            str(track["audioTrackId"]) for track in payload.get("audioTracks") or []
            if isinstance(track, dict) and track.get("audioTrackId")
            and track.get("videoId") not in (None, "", video_id)
        }
        tracks = {
            track_id: dict(track) for track_id, track in roots.items()
            if track.get("videoId") == video_id
        }

        def visit(value, language: str, content_type: str | None = None):
            if isinstance(value, list):
                for child in value:
                    visit(child, language, content_type)
            elif isinstance(value, dict):
                track_id = str(value.get("audioTrackId") or "").strip()
                if (
                    track_id and track_id not in foreign_ids
                    and value.get("videoId") in (None, "", video_id)
                    and (track_id in roots or content_type or value.get("audioContentTypeString"))
                ):
                    track = dict(roots.get(track_id) or value)
                    if not cls._translation_language(track):
                        track["language"] = language
                    if content_type:
                        track.setdefault("audioContentTypeString", content_type)
                    tracks[track_id] = track
                for key, child in value.items():
                    if isinstance(child, (dict, list)):
                        normalized_key = str(key).casefold()
                        child_type = (
                            "dubbed" if key == "audioTranslation" else
                            "descriptive" if "audio" in normalized_key and "descript" in normalized_key else None
                        )
                        visit(child, language, child_type)

        for group in matching:
            for item in group.get("translations") or []:
                if isinstance(item, dict):
                    visit(item, cls._translation_language(item) or "")
        return list(tracks.values())

    @classmethod
    def _audio_track_states_from_payload(cls, payload: dict, video_id: str, languages) -> dict:
        tracks = cls._video_audio_tracks(payload, video_id)
        result = {}
        for language in languages:
            entry = {}
            for content_type in ("dubbed", "descriptive"):
                states = set()
                failed_ids = []
                for track in tracks:
                    actual_language = cls._translation_language(track)
                    if not actual_language or actual_language.casefold() != language.casefold():
                        continue
                    actual_type = str(track.get("audioContentTypeString") or track.get("audioContentType") or "").casefold()
                    if not actual_type and cls._is_creator_dubbed_track(track):
                        actual_type = "dubbed"
                    if actual_type != content_type and not (content_type == "dubbed" and actual_type == "original"):
                        continue
                    if actual_type == "original":
                        # Source eligibility locks describe automatic dubbing;
                        # they do not mean the video's original audio is absent.
                        states.add("healthy")
                        continue
                    if cls._audio_payload_has_terminal_failure(track, assume_audio=True):
                        states.add("terminal")
                        if actual_type != "original":
                            failed_ids.append(str(track["audioTrackId"]))
                    elif cls._audio_payload_needs_attention(track, assume_audio=True):
                        states.add("inflight")
                    else:
                        states.add("healthy")
                entry[content_type] = next((state for state in ("healthy", "inflight", "terminal") if state in states), "missing")
                entry[content_type + "_track_ids"] = failed_ids
            result[language] = entry
        return result

    @classmethod
    def _readable_translation_video_ids(cls, payload: dict, requested: list[str]) -> set[str]:
        if not isinstance(payload.get("videoTranslations", []), list) or not isinstance(payload.get("audioTracks", []), list):
            return set()
        groups = [group for group in payload.get("videoTranslations") or [] if isinstance(group, dict)]
        readable = {
            cls._translation_group_video_id(group) for group in groups
            if not any(word in str(group.get("status") or "").upper() for word in ("ERROR", "FAILED"))
        }
        if len(requested) == 1 and len(groups) == 1 and cls._translation_group_video_id(groups[0]) is None and None in readable:
            readable.add(requested[0])
        readable.update(
            track.get("videoId") for track in payload.get("audioTracks") or []
            if isinstance(track, dict) and track.get("videoId")
        )
        return set(requested).intersection(readable)

    def get_audio_track_states(self, video_id: str, channel_id: str, languages) -> dict:
        payload = self._get_video_translation_payload([video_id], channel_id)
        if video_id not in self._readable_translation_video_ids(payload, [video_id]):
            raise AudioUpdateError("YouTube không trả trạng thái audio của đúng video; hãy thử lại.")
        return self._audio_track_states_from_payload(payload, video_id, languages)

    def get_missing_audio_description_targets(
        self, video_ids: list[str], channel_id: str, languages,
        unreadable_ids: list[str] | None = None,
    ) -> dict[str, list[dict]]:
        """Find missing/failed descriptions in selected languages, keeping processing tracks."""
        targets = {}
        languages = list(dict.fromkeys(languages))
        skipped = unreadable_ids if unreadable_ids is not None else []
        unique_ids = list(dict.fromkeys(video_id for video_id in video_ids if video_id))

        def scan(chunk):
            try:
                payload = self._get_video_translation_payload(chunk, channel_id)
            except AudioUpdateError as exc:
                if exc.status_code != 400:
                    raise
                if len(chunk) > 1:
                    middle = len(chunk) // 2
                    scan(chunk[:middle])
                    scan(chunk[middle:])
                    return
                if chunk[0] not in skipped:
                    skipped.append(chunk[0])
                return
            readable = self._readable_translation_video_ids(payload, chunk)
            for video_id in chunk:
                if video_id not in readable:
                    if len(chunk) > 1:
                        scan([video_id])
                    elif video_id not in skipped:
                        skipped.append(video_id)
                    continue
                states = self._audio_track_states_from_payload(payload, video_id, languages)
                actions = [
                    {"language": lang, "reason": "missing_description",
                     "track_ids": state["dubbed_track_ids"] if state["dubbed"] == "terminal" else [],
                     "audio_present": state["dubbed"] in ("healthy", "inflight")}
                    for lang, state in states.items() if state["descriptive"] in ("missing", "terminal")
                ]
                if actions:
                    targets[video_id] = actions

        for start in range(0, len(unique_ids), self._TRANSLATION_BATCH_SIZE):
            scan(unique_ids[start:start + self._TRANSLATION_BATCH_SIZE])
        return targets

    def _get_all_audio_track_ids(self, id_video: str, channel_id: str, languages: list[str] | None = None):
        payload = self._get_video_translation_payload([id_video], channel_id)
        selected = None if languages is None else {str(language).casefold() for language in languages}
        if selected is not None and id_video not in self._readable_translation_video_ids(payload, [id_video]):
            raise AudioUpdateError("YouTube không trả trạng thái audio của đúng video để xóa theo ngôn ngữ")
        return [
            track["audioTrackId"] for track in self._video_audio_tracks(payload, id_video)
            if self._is_creator_dubbed_track(track)
            and (selected is None or (self._translation_language(track) or "").casefold() in selected)
        ]


update_audio_module = UpdateAudioModule()
