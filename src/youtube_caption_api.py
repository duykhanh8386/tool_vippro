"""Official YouTube Data API caption upload and OAuth support."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from zoneinfo import ZoneInfo

import requests
from loguru import logger

from src.state_manager import state_manager


OAUTH_STATE_NAME = "youtube_caption_oauth"
QUOTA_STATE_NAME = "youtube_caption_quota"
YOUTUBE_FORCE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
_STATE_LOCK = threading.RLock()
_HTTP_TIMEOUT = (30, 180)


class CaptionApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        reasons: tuple[str, ...] = (),
        retryable: bool = False,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.reasons = reasons
        self.retryable = retryable


class CaptionQuotaExceededError(CaptionApiError):
    pass


class CaptionAuthenticationError(CaptionApiError):
    pass


def _load_mapping(name: str) -> dict:
    payload = state_manager.load_state(name) or {}
    return payload if isinstance(payload, dict) else {}


def _save_mapping(name: str, payload: dict) -> None:
    if not state_manager.save_state(name, payload):
        raise RuntimeError(f"Không thể lưu trạng thái {name}")


def _next_pacific_midnight(now: float | None = None) -> float:
    instant = datetime.fromtimestamp(now or time.time(), ZoneInfo("America/Los_Angeles"))
    tomorrow = (instant + timedelta(days=1)).date()
    return datetime.combine(
        tomorrow,
        datetime.min.time(),
        tzinfo=ZoneInfo("America/Los_Angeles"),
    ).timestamp()


def get_caption_quota_status(*, now: float | None = None) -> dict:
    timestamp = float(now if now is not None else time.time())
    with _STATE_LOCK:
        state = _load_mapping(QUOTA_STATE_NAME)
        blocked_until = float(state.get("blocked_until") or 0)
        if blocked_until and blocked_until <= timestamp:
            state = {}
            state_manager.clear_state(QUOTA_STATE_NAME)
        return {
            "blocked": blocked_until > timestamp,
            "blocked_until": blocked_until,
            "message": str(state.get("message") or ""),
        }


def _mark_quota_exhausted(message: str) -> None:
    with _STATE_LOCK:
        _save_mapping(
            QUOTA_STATE_NAME,
            {
                "blocked_until": _next_pacific_midnight(),
                "message": message,
                "detected_at": time.time(),
            },
        )


def clear_caption_quota_block() -> None:
    with _STATE_LOCK:
        state_manager.clear_state(QUOTA_STATE_NAME)


def _oauth_records() -> dict:
    state = _load_mapping(OAUTH_STATE_NAME)
    records = state.get("channels") or {}
    return records if isinstance(records, dict) else {}


def has_caption_oauth(channel_id: str) -> bool:
    with _STATE_LOCK:
        record = _oauth_records().get(str(channel_id)) or {}
        return bool(record.get("refresh_token") or record.get("access_token"))


def disconnect_caption_oauth(channel_id: str) -> None:
    with _STATE_LOCK:
        state = _load_mapping(OAUTH_STATE_NAME)
        records = state.get("channels") or {}
        if isinstance(records, dict):
            records.pop(str(channel_id), None)
        state["channels"] = records
        _save_mapping(OAUTH_STATE_NAME, state)


def _client_configuration(client_json_path: str | Path) -> dict:
    path = Path(client_json_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise CaptionAuthenticationError(
            f"Không đọc được OAuth Client JSON: {path}"
        ) from exc
    config = payload.get("installed") or payload.get("web")
    if not isinstance(config, dict) or not config.get("client_id"):
        raise CaptionAuthenticationError(
            "OAuth Client JSON không có cấu hình installed/web hợp lệ."
        )
    return config


def _save_oauth_record(channel_id: str, record: dict) -> None:
    with _STATE_LOCK:
        state = _load_mapping(OAUTH_STATE_NAME)
        records = state.get("channels") or {}
        if not isinstance(records, dict):
            records = {}
        records[str(channel_id)] = record
        state["channels"] = records
        _save_mapping(OAUTH_STATE_NAME, state)


def _verify_authorized_channel(access_token: str) -> str:
    response = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "id", "mine": "true"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=_HTTP_TIMEOUT,
    )
    if response.status_code != 200:
        raise CaptionAuthenticationError(
            f"Không xác minh được kênh OAuth (HTTP {response.status_code}).",
            status_code=response.status_code,
        )
    items = (response.json() or {}).get("items") or []
    return str(items[0].get("id") or "") if items else ""


def authorize_caption_channel(
    channel_id: str,
    client_json_path: str | Path,
    *,
    timeout_seconds: float = 300,
) -> None:
    """Run a desktop OAuth PKCE flow and persist a refresh token per channel."""
    expected_channel = str(channel_id or "").strip()
    if not expected_channel:
        raise CaptionAuthenticationError("Chưa chọn kênh cần cấp quyền phụ đề.")
    config = _client_configuration(client_json_path)
    callback: dict[str, str] = {}
    expected_state = secrets.token_urlsafe(32)

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
            query = parse_qs(urlparse(self.path).query)
            callback["state"] = str((query.get("state") or [""])[0])
            callback["code"] = str((query.get("code") or [""])[0])
            callback["error"] = str((query.get("error") or [""])[0])
            body = (
                "Đã nhận quyền YouTube. Bạn có thể đóng tab này và quay lại Tuất Videos."
                if callback["code"]
                else "Không thể cấp quyền YouTube. Hãy quay lại Tuất Videos để xem lỗi."
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), CallbackHandler)
    redirect_uri = f"http://127.0.0.1:{server.server_port}/"
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    auth_uri = str(config.get("auth_uri") or "https://accounts.google.com/o/oauth2/v2/auth")
    params = {
        "client_id": config["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": YOUTUBE_FORCE_SSL_SCOPE,
        "access_type": "offline",
        "prompt": "consent select_account",
        "state": expected_state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    webbrowser.open(f"{auth_uri}?{urlencode(params)}", new=1, autoraise=True)
    deadline = time.monotonic() + max(30.0, float(timeout_seconds))
    server.timeout = 1.0
    try:
        while not callback and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    if not callback:
        raise CaptionAuthenticationError("Hết thời gian chờ cấp quyền YouTube.")
    if callback.get("state") != expected_state:
        raise CaptionAuthenticationError("OAuth trả về state không hợp lệ.")
    if callback.get("error") or not callback.get("code"):
        raise CaptionAuthenticationError(
            f"YouTube từ chối cấp quyền: {callback.get('error') or 'missing code'}"
        )

    token_uri = str(config.get("token_uri") or "https://oauth2.googleapis.com/token")
    response = requests.post(
        token_uri,
        data={
            "client_id": config["client_id"],
            "client_secret": config.get("client_secret", ""),
            "code": callback["code"],
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=_HTTP_TIMEOUT,
    )
    if response.status_code != 200:
        raise CaptionAuthenticationError(
            f"Không đổi được mã OAuth (HTTP {response.status_code}).",
            status_code=response.status_code,
        )
    token = response.json()
    access_token = str(token.get("access_token") or "")
    authorized_channel = _verify_authorized_channel(access_token)
    if authorized_channel != expected_channel:
        raise CaptionAuthenticationError(
            "Tài khoản OAuth đang chọn không đúng kênh. "
            f"Cần {expected_channel}, nhận được {authorized_channel or 'không có kênh'}."
        )
    _save_oauth_record(
        expected_channel,
        {
            "client_id": config["client_id"],
            "client_secret": config.get("client_secret", ""),
            "token_uri": token_uri,
            "access_token": access_token,
            "refresh_token": str(token.get("refresh_token") or ""),
            "expires_at": time.time() + int(token.get("expires_in") or 3600),
            "scope": str(token.get("scope") or YOUTUBE_FORCE_SSL_SCOPE),
            "client_json_path": str(Path(client_json_path)),
        },
    )


def _access_token(channel_id: str) -> str:
    with _STATE_LOCK:
        records = _oauth_records()
        record = dict(records.get(str(channel_id)) or {})
    if not record:
        raise CaptionAuthenticationError(
            "Kênh chưa được cấp quyền YouTube Data API để đăng phụ đề."
        )
    access_token = str(record.get("access_token") or "")
    if access_token and float(record.get("expires_at") or 0) > time.time() + 60:
        return access_token
    refresh_token = str(record.get("refresh_token") or "")
    if not refresh_token:
        raise CaptionAuthenticationError(
            "Quyền phụ đề đã hết hạn và không có refresh token; hãy kết nối lại."
        )
    response = requests.post(
        str(record.get("token_uri") or "https://oauth2.googleapis.com/token"),
        data={
            "client_id": record.get("client_id", ""),
            "client_secret": record.get("client_secret", ""),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=_HTTP_TIMEOUT,
    )
    if response.status_code != 200:
        raise CaptionAuthenticationError(
            f"Không làm mới được quyền phụ đề (HTTP {response.status_code}).",
            status_code=response.status_code,
        )
    token = response.json()
    record["access_token"] = str(token.get("access_token") or "")
    record["expires_at"] = time.time() + int(token.get("expires_in") or 3600)
    _save_oauth_record(str(channel_id), record)
    return record["access_token"]


def _error_details(response: requests.Response) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    message = ""
    try:
        error = (response.json() or {}).get("error") or {}
        message = str(error.get("message") or "")
        for item in error.get("errors") or []:
            if isinstance(item, dict) and item.get("reason"):
                reasons.append(str(item["reason"]))
        if error.get("status"):
            reasons.append(str(error["status"]))
    except (ValueError, AttributeError, TypeError):
        message = str(getattr(response, "text", "") or "")[:500]
    return message, tuple(dict.fromkeys(reasons))


def _raise_api_error(response: requests.Response, action: str) -> None:
    message, reasons = _error_details(response)
    normalized = {reason.casefold() for reason in reasons}
    quota_markers = {
        "quotaexceeded",
        "dailylimitexceeded",
        "dailylimitexceededunreg",
        "quota_exceeded",
        "resource_exhausted",
    }
    if response.status_code in {403, 429} and normalized.intersection(quota_markers):
        user_message = (
            "YouTube Data API đã hết quota phụ đề hôm nay. Tool đã dừng phần "
            "phụ đề và Auto Registry sẽ thử tiếp sau khi quota được đặt lại."
        )
        _mark_quota_exhausted(user_message)
        raise CaptionQuotaExceededError(
            user_message,
            status_code=response.status_code,
            reasons=reasons,
        )
    if response.status_code == 401:
        raise CaptionAuthenticationError(
            "Quyền YouTube Data API đã hết hạn; hãy kết nối lại kênh.",
            status_code=401,
            reasons=reasons,
        )
    detail = message or ", ".join(reasons) or "không có chi tiết"
    raise CaptionApiError(
        f"Không thể {action} (HTTP {response.status_code}): {detail}",
        status_code=response.status_code,
        reasons=reasons,
        retryable=response.status_code == 429 or response.status_code >= 500,
    )


def _multipart_body(metadata: dict, media: bytes) -> tuple[bytes, str]:
    boundary = f"tuat-videos-{secrets.token_hex(16)}"
    body = b"".join(
        (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode(),
            json.dumps(metadata, ensure_ascii=False).encode("utf-8"),
            f"\r\n--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n".encode(),
            media,
            f"\r\n--{boundary}--\r\n".encode(),
        )
    )
    return body, f"multipart/related; boundary={boundary}"


class YouTubeCaptionClient:
    def __init__(self, channel_id: str):
        self.channel_id = str(channel_id)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {_access_token(self.channel_id)}"}

    def list_tracks(self, video_id: str) -> list[dict]:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/captions",
            params={"part": "snippet", "videoId": video_id},
            headers=self._headers(),
            timeout=_HTTP_TIMEOUT,
        )
        if response.status_code != 200:
            _raise_api_error(response, "đọc danh sách phụ đề")
        items = (response.json() or {}).get("items") or []
        return [item for item in items if isinstance(item, dict)]

    def _upload(
        self,
        *,
        method: str,
        metadata: dict,
        srt_bytes: bytes,
        part: str,
    ) -> dict:
        body, content_type = _multipart_body(metadata, srt_bytes)
        response = requests.request(
            method,
            "https://www.googleapis.com/upload/youtube/v3/captions",
            params={"part": part, "uploadType": "multipart"},
            headers={**self._headers(), "Content-Type": content_type},
            data=body,
            timeout=_HTTP_TIMEOUT,
        )
        if response.status_code not in {200, 201}:
            _raise_api_error(response, "đăng phụ đề")
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def insert_track(
        self,
        video_id: str,
        language: str,
        srt_bytes: bytes,
    ) -> dict:
        return self._upload(
            method="POST",
            metadata={
                "snippet": {
                    "videoId": video_id,
                    "language": language,
                    "name": f"Tuất Videos {language}",
                    "isDraft": False,
                }
            },
            srt_bytes=srt_bytes,
            part="snippet",
        )

    def update_track(self, caption_id: str, srt_bytes: bytes) -> dict:
        return self._upload(
            method="PUT",
            metadata={"id": caption_id},
            srt_bytes=srt_bytes,
            part="id",
        )

    def download_translation(self, caption_id: str, language: str) -> bytes:
        base_language = str(language).split("-", 1)[0].lower()
        response = requests.get(
            f"https://www.googleapis.com/youtube/v3/captions/{caption_id}",
            params={"tfmt": "srt", "tlang": base_language},
            headers=self._headers(),
            timeout=_HTTP_TIMEOUT,
        )
        if response.status_code != 200:
            _raise_api_error(response, f"dịch phụ đề sang {language}")
        return bytes(response.content)

    @staticmethod
    def track_language(track: dict) -> str:
        snippet = track.get("snippet") or {}
        return str(snippet.get("language") or "").strip()

    def upsert_track(
        self,
        *,
        video_id: str,
        language: str,
        srt_bytes: bytes,
        existing_tracks: list[dict],
        replace_existing: bool,
    ) -> tuple[str, str]:
        existing = next(
            (
                track
                for track in existing_tracks
                if self.track_language(track).casefold() == language.casefold()
            ),
            None,
        )
        if existing is not None and not replace_existing:
            return str(existing.get("id") or ""), "already_added"
        if existing is not None:
            result = self.update_track(str(existing.get("id") or ""), srt_bytes)
            return str(result.get("id") or existing.get("id") or ""), "successful"
        result = self.insert_track(video_id, language, srt_bytes)
        if result:
            existing_tracks.append(result)
        return str(result.get("id") or ""), "successful"


def prepare_source_caption(
    *,
    channel_id: str,
    video_id: str,
    source_language: str,
    source_srt_path: str | Path,
    replace_existing: bool,
) -> tuple[str, list[dict], str]:
    quota = get_caption_quota_status()
    if quota["blocked"]:
        raise CaptionQuotaExceededError(quota["message"])
    source_bytes = Path(source_srt_path).read_bytes()
    client = YouTubeCaptionClient(channel_id)
    tracks = client.list_tracks(video_id)
    track_id, status = client.upsert_track(
        video_id=video_id,
        language=source_language,
        srt_bytes=source_bytes,
        existing_tracks=tracks,
        replace_existing=replace_existing,
    )
    return track_id, tracks, status


def publish_translated_caption(
    *,
    channel_id: str,
    video_id: str,
    source_track_id: str,
    source_language: str,
    source_srt_path: str | Path,
    target_language: str,
    existing_tracks: list[dict] | None = None,
    replace_existing: bool,
) -> str:
    quota = get_caption_quota_status()
    if quota["blocked"]:
        raise CaptionQuotaExceededError(quota["message"])
    client = YouTubeCaptionClient(channel_id)
    tracks = existing_tracks if existing_tracks is not None else client.list_tracks(video_id)
    if target_language.casefold() == source_language.casefold():
        srt_bytes = Path(source_srt_path).read_bytes()
    else:
        srt_bytes = client.download_translation(source_track_id, target_language)
    _, status = client.upsert_track(
        video_id=video_id,
        language=target_language,
        srt_bytes=srt_bytes,
        existing_tracks=tracks,
        replace_existing=replace_existing,
    )
    return status
