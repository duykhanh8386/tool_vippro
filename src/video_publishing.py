"""Copyright decisions and daily publication plans, independent of browser state."""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import datetime, time, timedelta

from src.video_scan_dates import VIETNAM_TIMEZONE, _status_indicates_draft, _timestamp

COPYRIGHT_LABELS = {
    "clear": "Không có vấn đề bản quyền",
    "limited": "Có thể bị hạn chế thu nhập / có khiếu nại",
    "partial": "Bị chặn một phần",
    "blocked": "Bị chặn",
    "checking": "Đang kiểm tra",
    "unknown": "Chưa xác định",
}
VIDEO_TYPE_LABELS = {
    "draft": "Bản nháp", "private": "Riêng tư", "unlisted": "Không công khai",
    "scheduled": "Đã lên lịch", "public": "Đã công khai", "unknown": "Chưa đọc được loại video",
}
VIDEO_SCOPE_LABELS = {"all": "Tất cả loại video", "unpublished": "Chưa công khai (nháp / riêng tư / không công khai)", **VIDEO_TYPE_LABELS}
SELECTABLE_COPYRIGHT_TYPES = {"clear", "limited", "partial", "blocked"}
PUBLISHING_SCAN_SCHEMA_VERSION = 2


def _schedule_sources(video):
    def meaningful(value):
        if isinstance(value, dict):
            return any(meaningful(child) for key,child in value.items() if key not in {"privacy","targetPrivacy","newPrivacy"})
        if isinstance(value,list):
            return any(meaningful(child) for child in value)
        return value not in (None,False,0,"","0")
    for value in (getattr(video, "scheduled_publishing_details", None), getattr(video, "scheduled_creator_visibility", None)):
        if isinstance(value, dict) and any(value.get(key) is False for key in ("isScheduled", "scheduled")):
            continue
        if isinstance(value, str) and any(marker in value.upper() for marker in ("UNSPECIFIED", "_NONE")):
            continue
        if meaningful(value):
            yield value


def has_schedule_info(video):
    return any(True for _ in _schedule_sources(video))


def publishing_video_type(video) -> str:
    if _status_indicates_draft(getattr(video, "draft_status", None)) or _status_indicates_draft(getattr(video, "video_status", None)):
        return "draft"
    if has_schedule_info(video):
        return "scheduled"
    privacy = str(getattr(video, "privacy", "") or "").upper()
    for kind in ("private", "unlisted", "public"):
        if privacy == kind.upper() or privacy.endswith("_" + kind.upper()):
            return kind
    return "unknown"


def publishing_row_matches(row, *, scope="all", categories=()) -> bool:
    kind = row.get("visibility_type", "unknown")
    in_scope = scope == "all" or (scope == "unpublished" and kind in {"draft", "private", "unlisted"}) or scope == kind
    return in_scope and (not categories or row.get("copyright") in categories)


def publishing_row_disabled_reason(row) -> str:
    if row.get("status") == "successful":
        return "Đã hoàn tất lên lịch."
    if row.get("availability_reason"):
        return row["availability_reason"]
    if row.get("status") == "skipped":
        return row.get("detail") or "Quét lại để đọc loại video và lý do không thể chọn."
    kind = row.get("visibility_type")
    if kind == "public":
        return "Video đã công khai; không thể lên lịch lần đầu."
    if kind == "scheduled":
        return "Video đã có lịch đăng; giữ lịch hiện tại."
    if kind == "unknown":
        return "Chưa đọc được loại video; quét lại trước khi chọn."
    if row.get("copyright") not in SELECTABLE_COPYRIGHT_TYPES:
        return COPYRIGHT_LABELS.get(row.get("copyright"), "Chưa xác định bản quyền") + "; quét lại để kiểm tra."
    return ""


def publishing_row_selectable(row) -> bool:
    return not publishing_row_disabled_reason(row)

REFERENCE_SELECTION_VERSION = 2


def thumbnail_file_stem(title, video_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(video_id)):
        raise ValueError("Video ID không hợp lệ để lưu thumbnail.")
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(title or "")).strip(" .") or "Thumbnail"
    if text.split(".", 1)[0].upper() in {"CON", "PRN", "AUX", "NUL", *("COM" + str(n) for n in range(1, 10)), *("LPT" + str(n) for n in range(1, 10))}:
        text = "_" + text
    while len(text.encode("utf-16-le")) > 160:
        text = text[:-1]
    text = text.rstrip(" .") or "Thumbnail"
    return text + " [" + video_id + "]"


_SOURCE_ID_SUFFIX = re.compile(r"\[([A-Za-z0-9_-]{11})\]\s*(?:\.(?:mp4|m4v|mkv|mov|webm))?\s*$", re.I)


def reference_video_id(title: str) -> str:
    """Recognize a downloader's [YouTube ID] suffix, with or without .mp4."""
    match = _SOURCE_ID_SUFFIX.search(str(title or "").strip())
    return match[1] if match else ""


def reference_search_query(query: str) -> str:
    text = _SOURCE_ID_SUFFIX.sub("", str(query or "").strip()).strip()
    return re.sub(r"\.(?:mp4|m4v|mkv|mov|webm)\s*$", "", text, flags=re.I).strip()


def positive_seconds(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        seconds = float(value)
        return seconds if math.isfinite(seconds) and seconds > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def restriction_details(payload: dict) -> dict:
    return {key: payload[key] for key in (
        "allRestrictions", "copyrightSummary", "claimDetails", "ownedClaimDetails",
        "videoPrechecks", "statusDetails",
    ) if key in payload}


def copyright_check_status(payload: dict) -> str:
    checks = payload.get("videoPrechecks") or {}
    for key in ("videoUploadChecksMonetized", "videoUploadChecksNotMonetized"):
        check = (checks.get(key) or {}).get("copyrightCheck") or {}
        if check.get("checkStatus"):
            return str(check["checkStatus"])
    return ""


def _leaves(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _leaves(child, path + "." + key.lower())
    elif isinstance(value, list):
        for child in value:
            yield from _leaves(child, path)
    else:
        yield path, str(value).upper()


def copyright_category(video) -> str:
    """A finished check is not evidence that a video is claim-free."""
    details = getattr(video, "restriction_details", {}) or {}
    leaves = list(_leaves(details))
    status = str(getattr(video, "copyright_check_status", "") or copyright_check_status(details)).upper()
    values = [value for _, value in leaves] + [status]
    # Explicit negative values must not be mistaken for blocking/claims.
    active = [value for value in values if not any(marker in value for marker in
              ("NOT_BLOCKED", "NO_BLOCK", "NO_CLAIM", "NO_RESTRICTION", "NO_ISSUE", "UNBLOCKED"))]
    if any("BLOCKED_WORLDWIDE" in value or "BLOCKED_GLOBALLY" in value for value in active):
        return "blocked"
    if any(value == "TRUE" and path.endswith((".isblockedworldwide", ".isblockedglobally")) for path, value in leaves):
        return "blocked"
    if any(any(marker in value for marker in ("PARTIALLY_BLOCKED", "PARTIAL_BLOCK", "BLOCKED_IN_SOME", "BLOCK_SOME", "BLOCKED_IN_SOME_TERRITORIES", "BỊ CHẶN MỘT PHẦN")) for value in active):
        return "partial"
    if any(value.endswith(("_BLOCKED", "_BLOCK", "BLOCKED_WORLDWIDE")) or value in {"BLOCKED", "BLOCK", "BỊ CHẶN"} for value in active):
        return "blocked"
    if any(any(marker in value for marker in ("LIMITED_MONETIZATION", "MONETIZATION_LIMITED", "COPYRIGHT_CLAIM", "HAS_CLAIM", "CLAIMED", "HẠN CHẾ THU NHẬP")) for value in active):
        return "limited"
    # Structured claims with IDs are positive evidence even without a label.
    if any("claim" in path and path.endswith((".claimid", ".claim_id")) and value for path, value in leaves):
        return "limited"
    if any(value == "TRUE" and path.endswith((".hasclaims", ".hascopyrightclaims", ".hascopyrightclaim", ".hascopyright", ".iscopyrightclaimed")) for path, value in leaves):
        return "limited"
    if any(any(marker in value for marker in ("IN_PROGRESS", "PENDING", "CHECKING", "NOT_STARTED")) for value in active):
        return "checking"
    # Ignore unrelated NONE values (e.g. statusDetails.ageRestriction).
    copyright_values = [value for path, value in leaves if "copyright" in path or "claim" in path] + [status]
    if any(any(marker in value for marker in ("NO_ISSUE", "NO_CLAIM", "NO_RESTRICTION", "CHECK_PASSED", "CHECK_SUCCESS", "CHECK_OK")) or value == "CLEAR" for value in copyright_values):
        return "clear"
    if any(value == "FALSE" and path.endswith((".hasclaims", ".hascopyrightclaims", ".hascopyrightclaim", ".hascopyright")) for path, value in leaves):
        return "clear"
    restrictions = details.get("allRestrictions")
    if isinstance(restrictions, dict) and restrictions.get("restrictions") == [] and "COMPLETE" in status:
        return "clear"
    return "unknown"


def first_song(title: str, description: str) -> str:
    """Prefer the first timestamped track, preserving accents and song wording."""
    for line in str(description or "").splitlines():
        match = re.match(r"^\s*(?:[\[\(]?\d{1,2}:\d{2}(?::\d{2})?[\]\)]?)\s*[-–—|.:]?\s*(.+?)\s*$", line)
        if match:
            song = match[1].strip()
            if song:
                return song
        match = re.match(r"^\s*(.+?)\s+\[?\(?\d{1,2}:\d{2}(?::\d{2})?\)?\]?\s*$", line)
        if match:
            return re.sub(r"^\s*\d+[.)-]\s*", "", match[1]).strip()
    return str(title or "").strip()


def parse_chatgpt_cookies(text: str) -> list[dict]:
    """Accept a browser JSON export or a Cookie header, only for chatgpt.com."""
    text = str(text or "").strip()
    if not text:
        raise ValueError("Dán cookie ChatGPT trước khi tạo thumbnail.")
    try:
        if text.startswith(("[", "{")):
            raw = json.loads(text)
            raw = raw.get("cookies", []) if isinstance(raw, dict) else raw
        else:
            raw = [{"name": pair.split("=", 1)[0].strip(), "value": pair.split("=", 1)[1].strip()}
                   for pair in re.sub(r"^cookie\s*:\s*", "", text, flags=re.I).split(";") if "=" in pair]
        if not isinstance(raw, list):
            raise ValueError()
        cookies = []
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError()
            domain = str(item.get("domain") or "chatgpt.com").lstrip(".").lower()
            if domain != "chatgpt.com":
                continue
            name, value = str(item.get("name") or ""), str(item.get("value") or "")
            if not name or not value or re.search(r"[\s;=]", name) or "\n" in value or "\r" in value:
                continue
            cookie = {"name": name, "value": value, "path": item.get("path") or "/", "secure": True,
                      "httpOnly": bool(item.get("httpOnly", False))}
            if not name.startswith("__Host-"):
                cookie["domain"] = ".chatgpt.com"
            expiry = item.get("expirationDate", item.get("expiry"))
            if expiry is not None and float(expiry) > 0:
                cookie["expiry"] = int(float(expiry))
            cookies.append(cookie)
        if not cookies:
            raise ValueError()
        return cookies
    except (ValueError, TypeError, KeyError, OverflowError):
        raise ValueError("Cookie không hợp lệ. Dùng JSON export từ chatgpt.com hoặc chuỗi name=value; name=value.") from None


def schedule_timestamp(video) -> float | None:
    if not has_schedule_info(video):
        return None
    for candidate in _schedule_sources(video):
        # Studio has returned both its publication object and the metadata
        # command shape for scheduledPublishingDetails across client versions.
        stamp = _timestamp(candidate)
        nested = (candidate.get("scheduledPublishing") or candidate.get("set") or candidate.get("scheduledCreatorVisibility")) if isinstance(candidate, dict) else None
        if isinstance(nested, dict):
            nested = nested.get("set", nested)
            stamp = stamp or _timestamp(nested.get("timeSec")) or _timestamp(nested)
        if stamp:
            return stamp
    return _timestamp(getattr(video, "time_published_seconds", None))


def plan_daily(rows: list[dict], start_date: str, hour: str, *, occupied=None, now=None) -> list[dict]:
    """One future slot per channel/day; keep existing/resumed assignments stable."""
    now = now or datetime.now(VIETNAM_TIMEZONE)
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        clock = time.fromisoformat(hour)
        if clock.tzinfo or clock.second or clock.microsecond:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Chọn ngày bắt đầu và giờ đăng hợp lệ (HH:MM).") from None
    initial = datetime.combine(start, clock, VIETNAM_TIMEZONE)
    needs_new_slot = any(row.get("selected") and row.get("status") != "successful" and not row.get("publish_at") for row in rows)
    if initial <= now and needs_new_slot:
        raise ValueError("Ngày và giờ bắt đầu phải ở tương lai (giờ Việt Nam, UTC+7).")
    reserved = defaultdict(set)
    for channel_id, stamps in (occupied or {}).items():
        reserved[channel_id].update(datetime.fromtimestamp(stamp, VIETNAM_TIMEZONE).date() for stamp in stamps)
    for row in rows:
        if row.get("publish_at"):
            day = datetime.fromtimestamp(row["publish_at"], VIETNAM_TIMEZONE).date()
            reserved[row["channel_id"]].add(day)
    cursors = defaultdict(lambda: start)
    plan = []
    for row in rows:
        if not row.get("selected") or row.get("status") == "successful":
            continue
        if row.get("publish_at"):
            stamp = row["publish_at"]
            if stamp <= now.timestamp():
                raise ValueError("Có lịch chưa hoàn tất đã qua giờ đăng. Quét lại và chọn ngày bắt đầu mới.")
        else:
            channel_id = row["channel_id"]
            day = cursors[channel_id]
            while day in reserved[channel_id]:
                day += timedelta(days=1)
            stamp = int(datetime.combine(day, clock, VIETNAM_TIMEZONE).timestamp())
            reserved[channel_id].add(day)
            cursors[channel_id] = day + timedelta(days=1)
        plan.append({"video_id": row["video_id"], "channel_id": row["channel_id"], "publish_at": int(stamp),
                     "publish_label": datetime.fromtimestamp(stamp, VIETNAM_TIMEZONE).strftime("%d/%m/%Y %H:%M")})
    return plan
