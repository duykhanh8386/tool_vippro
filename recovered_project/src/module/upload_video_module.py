# RECOVERED: reconstructed from CPython 3.12 bytecode
import json, os, time, uuid
from urllib.parse import quote
import requests
from loguru import logger
from src.module.base import IModule
from src.utils import get_channels_info
from src.task_runtime import (
    TaskStopped,
    check_stopped,
    post_with_stop,
    wait_interruptibly,
)

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"


def make_frontend_upload_id(index: int = 0) -> str:
    """Client-generated id for an upload session (không lấy từ server)."""
    return f"innertube_studio:{str(uuid.uuid4()).upper()}:{index}"


def _sanitize_title(title: str) -> str:
    """YouTube title: bỏ '<' '>' và xuống dòng, cắt tối đa 100 ký tự."""
    cleaned = (title or "").replace("<", "").replace(">", "").replace("\n", " ").replace("\r", " ").strip()
    return cleaned[:100] or "Untitled"


class UploadVideoModule(IModule):
    """Upload một file video lên YouTube qua resumable protocol (chặng 1 + 2).

    Chặng 3 (tạo video + set title/description) sẽ được bổ sung sau.
    """
    # Smaller chunks give the Stop button a frequent cancellation checkpoint
    # without changing the resumable upload protocol.
    _CHUNK_TARGET = 8_388_608
    _MAX_CHUNK_RETRIES = 5

    pass
    pass
    def upload(self, channel_id: str, file_path: str, index: int = 0, progress: dict | None = None) -> dict:
        """Chạy chặng 1 (start) + chặng 2 (upload theo chunk, resumable).

        `progress` (nếu truyền) là dict được cập nhật {"sent": bytes, "total": bytes}
        sau mỗi chunk để UI hiển thị %.

        Trả về dict gồm frontend_upload_id, scotty_resource_id (dùng cho chặng 3).
        """
        check_stopped()
        channel_info = get_channels_info(channel_id)
        if not channel_info:
            raise Exception(f"Không tìm thấy kênh: {channel_id}")
        if not os.path.isfile(file_path):
            raise Exception(f"File không tồn tại: {file_path}")
        cookie_string = channel_info.cookie_string()
        file_size = os.path.getsize(file_path)
        fname_header = quote(os.path.basename(file_path), safe="")
        frontend_upload_id = make_frontend_upload_id(index)
        upload_url, scotty_resource_id, granularity = self._start(
            cookie_string=cookie_string, fname_header=fname_header, file_size=file_size,
            frontend_upload_id=frontend_upload_id,
        )
        self._upload_bytes(
            upload_url=upload_url, cookie_string=cookie_string, fname_header=fname_header,
            file_path=file_path, granularity=granularity, progress=progress,
        )
        logger.info(f"Uploaded '{os.path.basename(file_path)}' (frontendUploadId={frontend_upload_id})")
        return {
            "frontend_upload_id": frontend_upload_id, "scotty_resource_id": scotty_resource_id,
            "upload_url": upload_url, "file_name": os.path.basename(file_path), "file_size": file_size,
        }

    def _start(self, cookie_string: str, fname_header: str, file_size: int, frontend_upload_id: str) -> tuple[(str, str, int)]:
        url = "https://upload.youtube.com/upload/studio?authuser=0"
        headers = {
            "Host": "upload.youtube.com", "Cookie": cookie_string,
            "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-File-Name": fname_header, "X-Goog-Upload-Header-Content-Length": str(file_size),
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8", "User-Agent": _USER_AGENT,
            "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9", "Origin": "https://studio.youtube.com",
            "Referer": "https://studio.youtube.com/",
        }
        body = json.dumps({"frontendUploadId": frontend_upload_id})
        response = post_with_stop(url, headers=headers, data=body)
        if response.status_code != 200:
            raise Exception(f"Upload start thất bại: HTTP {response.status_code}")
        status = response.headers.get("X-Goog-Upload-Status")
        if status != "active":
            raise Exception(f"Trạng thái start không hợp lệ: {status}")
        upload_url = response.headers.get("X-Goog-Upload-URL")
        scotty_resource_id = response.headers.get("X-Goog-Upload-Header-Scotty-Resource-Id")
        if not upload_url or not scotty_resource_id:
            raise Exception("Thiếu upload URL hoặc scotty resource id trong response")
        try:
            granularity = int(response.headers.get("X-Goog-Upload-Chunk-Granularity", 262_144))
        except (TypeError, ValueError):
            granularity = 262_144
        return upload_url, scotty_resource_id, granularity

    def _base_upload_headers(self, cookie_string: str, fname_header: str) -> dict:
        return {
            "Host": "upload.youtube.com", "Cookie": cookie_string, "X-Goog-Upload-File-Name": fname_header,
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8", "User-Agent": _USER_AGENT,
            "Accept": "*/*", "Origin": "https://studio.youtube.com", "Referer": "https://studio.youtube.com/",
        }

    def _query_offset(self, upload_url: str, base_headers: dict) -> int | None:
        """Hỏi server đã nhận được bao nhiêu byte (để resume)."""
        try:
            headers = dict(base_headers)
            headers["X-Goog-Upload-Command"] = "query"
            resp = post_with_stop(upload_url, headers=headers, data=b"")
            recv = resp.headers.get("X-Goog-Upload-Size-Received")
            return int(recv) if recv is not None else None
        except TaskStopped:
            raise
        except Exception as e:
            logger.warning(f"Query upload offset lỗi: {e}")
            return None

    pass
    pass
    def _upload_bytes(self, upload_url: str, cookie_string: str, fname_header: str, file_path: str, granularity: int = 262_144, progress: dict | None = None) -> None:
        file_size = os.path.getsize(file_path)
        if progress is not None:
            progress["total"] = file_size
            progress["sent"] = 0
        granularity = max(1, granularity)
        chunk_size = max(granularity, self._CHUNK_TARGET // granularity * granularity)
        base_headers = self._base_upload_headers(cookie_string, fname_header)
        offset = 0
        retries = 0
        with open(file_path, "rb") as f:
            while offset < file_size:
                check_stopped()
                f.seek(offset)
                chunk = f.read(chunk_size)
                is_last = offset + len(chunk) >= file_size
                headers = dict(base_headers)
                headers["X-Goog-Upload-Command"] = "upload, finalize" if is_last else "upload"
                headers["X-Goog-Upload-Offset"] = str(offset)
                try:
                    resp = post_with_stop(
                        upload_url,
                        headers=headers,
                        data=chunk,
                        timeout=(15, 60),
                    )
                    if resp.status_code == 200:
                        offset += len(chunk)
                        retries = 0
                        if progress is not None:
                            progress["sent"] = offset
                        if is_last:
                            status = resp.headers.get("X-Goog-Upload-Status")
                            if status and status not in ("final", "active"):
                                logger.warning(f"Trạng thái finalize bất thường: {status}")
                        continue
                    raise Exception(f"HTTP {resp.status_code}")
                except TaskStopped:
                    raise
                except Exception as e:
                    retries += 1
                    logger.warning(f"Upload chunk lỗi tại offset {offset} (lần {retries}/{self._MAX_CHUNK_RETRIES}): {e}")
                    if retries > self._MAX_CHUNK_RETRIES:
                        raise Exception(f"Upload thất bại tại offset {offset} sau nhiều lần thử")
                    srv = self._query_offset(upload_url, base_headers)
                    if srv is not None and 0 <= srv <= file_size:
                        offset = srv
                        if progress is not None:
                            progress["sent"] = offset
                    wait_interruptibly(2)

    pass
    pass
    pass
    pass
    def create_video(self, channel_id: str, scotty_resource_id: str, frontend_upload_id: str, title: str, description: str = "", tags: list[str] | None = None, privacy: str = "PRIVATE", is_draft: bool = True) -> str:
        """Chặng 3: tạo video từ scottyResourceId, set title/description/tags.

        Trả về videoId. Metadata được set ngay khi tạo (không cần call update).
        """
        check_stopped()
        channel_info = get_channels_info(channel_id)
        if not channel_info:
            raise Exception(f"Không tìm thấy kênh: {channel_id}")
        session_token = self._get_session_token(channel_info)
        channel_info = get_channels_info(channel_id)
        cookie_string = channel_info.cookie_string()
        context = self._build_context(
            channel_info.id, channel_info.role, channel_info.delegated_session_id,
            client_version="1.20260708.06.00", hl="vi",
            extra_request_fields={
                "attestationResponseData": {"challenge": channel_info.challenge, "webResponse": channel_info.botguardResponse},
                "sessionInfo": {"token": session_token},
            },
        )
        payload = {
            "channelId": channel_info.id,
            "resourceId": {"scottyResourceId": {"id": scotty_resource_id}},
            "frontendUploadId": frontend_upload_id,
            "initialMetadata": {
                "title": {"newTitle": _sanitize_title(title)}, "privacy": {"newPrivacy": privacy},
                "draftState": {"isDraft": is_draft}, "description": {"newDescription": description or ""},
                "tags": {"newTags": tags or []},
            },
            "contentLevelProtection": {"enableRequiresContentLevelProtection": False},
            "context": context, "presumedShort": False,
        }
        headers = {
            "Host": "studio.youtube.com", "Cookie": cookie_string,
            "Authorization": f"SAPISIDHASH {channel_info.sapisidhash}", "Content-Type": "application/json",
            "Origin": "https://studio.youtube.com", "X-Origin": "https://studio.youtube.com",
            "Referer": "https://studio.youtube.com/", "User-Agent": _USER_AGENT, "X-Goog-AuthUser": "0",
            "X-Youtube-Client-Name": "62", "X-Youtube-Client-Version": "1.20260708.06.00",
        }
        url = "https://studio.youtube.com/youtubei/v1/upload/createvideo?alt=json"
        response = post_with_stop(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"createvideo thất bại: HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()
        video_id = data.get("videoId")
        if not video_id:
            raise Exception(f"createvideo không trả videoId: {str(data)[:300]}")
        logger.info(f"Created video {video_id} (title='{_sanitize_title(title)}')")
        return video_id

    def is_processed(self, channel_id: str, video_id: str) -> bool:
        """Kiểm tra video đã được YouTube xử lý xong chưa.

        Trả True khi video.status == "VIDEO_STATUS_PROCESSED".
        """
        check_stopped()
        try:
            info = self._get_video_info(video_id=video_id, channel_id=channel_id)
        except TaskStopped:
            raise
        except Exception as e:
            logger.warning(f"Không lấy được trạng thái video {video_id}: {e}")
            return False
        return bool(info and info.video_status == "VIDEO_STATUS_PROCESSED")


upload_video_module = UploadVideoModule()
