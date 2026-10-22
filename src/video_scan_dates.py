"""Upload, publication and scheduled-publication dates for channel scans."""

import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Mapping


VIETNAM_TIMEZONE = timezone(timedelta(hours=7))
DEFAULT_SCAN_DATE_TYPE = "auto"
SCAN_DATE_TYPE_OPTIONS = {
    "auto": "Tự động theo trạng thái video",
    "uploaded": "Ngày tải lên",
    "published": "Ngày công khai",
    "scheduled": "Ngày lên lịch công khai",
}


def normalize_scan_date_type(value: object) -> str:
    clean = str(value or "").strip()
    return clean if clean in SCAN_DATE_TYPE_OPTIONS else DEFAULT_SCAN_DATE_TYPE


def _video_value(video: object, key: str):
    return video.get(key) if isinstance(video, Mapping) else getattr(video, key, None)


def _status_indicates_draft(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, dict):
        for key in ("isDraft", "is_draft"):
            if key in value:
                return _status_indicates_draft(value[key])
        return any(_status_indicates_draft(child) for child in value.values())
    normalized = "".join(ch for ch in str(value or "").upper() if ch.isalnum())
    if not normalized or any(
        marker in normalized for marker in ("NOTDRAFT", "NONDRAFT", "STATUSNONE", "PUBLISHED")
    ):
        return False
    return normalized in {"1", "TRUE", "DRAFT"} or normalized.endswith(("STATUSDRAFT", "STATEDRAFT"))


def _timestamp(value: object, *, depth: int = 0) -> float | None:
    if depth > 8 or isinstance(value, bool) or value is None:
        return None
    if isinstance(value, Mapping):
        for key in (
            "seconds", "secondsSinceEpoch", "publishTimeSeconds", "scheduledPublishTimeSeconds",
            "scheduledPublishingTimeSeconds", "scheduledPublishTime", "scheduledPublishingTime",
            "publishTime", "publishAt", "scheduledTime", "timestamp", "time", "value",
        ):
            if key in value:
                found = _timestamp(value[key], depth=depth + 1)
                if found is not None:
                    return found
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError, OverflowError):
        try:
            moment = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=VIETNAM_TIMEZONE)
            timestamp = moment.timestamp()
            return timestamp if math.isfinite(timestamp) and timestamp > 0 else None
        except (TypeError, ValueError, OverflowError, OSError):
            return None
    if not math.isfinite(timestamp) or timestamp <= 0:
        return None
    # Some date fields contain milliseconds rather than Unix seconds.
    return timestamp / 1000 if timestamp >= 100_000_000_000 else timestamp


def _video_timestamp(video: object, date_type: str) -> float | None:
    is_draft = _status_indicates_draft(_video_value(video, "draft_status")) or _status_indicates_draft(
        _video_value(video, "video_status")
    )
    schedule = _video_value(video, "scheduled_publishing_details")
    if date_type == "auto":
        privacy = str(_video_value(video, "privacy") or "").upper()
        if is_draft:
            date_type = "uploaded"
        elif schedule:
            date_type = "scheduled"
        elif privacy in {
            "PUBLIC", "VIDEO_PRIVACY_PUBLIC", "PRIVACY_PUBLIC",
            "UNLISTED", "VIDEO_PRIVACY_UNLISTED", "PRIVACY_UNLISTED",
        }:
            date_type = "published"
        else:
            date_type = "uploaded"
    if date_type == "uploaded":
        return _timestamp(_video_value(video, "time_created_seconds"))
    if date_type == "published":
        if is_draft or schedule:
            return None
        return _timestamp(_video_value(video, "time_published_seconds"))
    if not schedule or is_draft:
        return None
    # Studio variants expose the planned date either inside the scheduling
    # object or in timePublishedSeconds. Never substitute the upload date.
    return _timestamp(schedule) or _timestamp(_video_value(video, "time_published_seconds"))


def scan_today() -> date:
    return datetime.now(VIETNAM_TIMEZONE).date()


def normalize_scan_start_date(value: object) -> str:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return ""
    try:
        return date.fromisoformat(raw).isoformat()
    except (TypeError, ValueError):
        raise ValueError("Ngày bắt đầu không hợp lệ. Hãy chọn ngày trên lịch.") from None


def scan_date_bounds(start_date: object, *, end_date: date | None = None) -> tuple[float, float] | None:
    normalized = normalize_scan_start_date(start_date)
    if not normalized:
        return None
    first = date.fromisoformat(normalized)
    last = end_date or scan_today()
    if first > last:
        raise ValueError("Ngày bắt đầu không được sau ngày hiện tại.")
    return (
        datetime.combine(first, time.min, VIETNAM_TIMEZONE).timestamp(),
        datetime.combine(last + timedelta(days=1), time.min, VIETNAM_TIMEZONE).timestamp(),
    )


def validate_scan_start_date(value: object) -> str:
    normalized = normalize_scan_start_date(value)
    scan_date_bounds(normalized)
    return normalized


def video_matches_scan_dates(
    video: object, bounds: tuple[float, float] | None, *, date_type: str = "uploaded",
) -> bool:
    if bounds is None:
        return True
    timestamp = _video_timestamp(video, normalize_scan_date_type(date_type))
    return timestamp is not None and bounds[0] <= timestamp < bounds[1]


def scan_date_label(start_date: object, *, end_date: str | None = None, date_type: str = "uploaded") -> str:
    normalized = normalize_scan_start_date(start_date)
    if not normalized:
        return ""
    first = date.fromisoformat(normalized)
    last = date.fromisoformat(end_date) if end_date else scan_today()
    basis = SCAN_DATE_TYPE_OPTIONS[normalize_scan_date_type(date_type)].lower()
    return f"từ {first:%d/%m/%Y} đến {last:%d/%m/%Y} ({basis})"
