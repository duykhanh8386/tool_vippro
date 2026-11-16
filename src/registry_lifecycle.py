"""Dates, ordering and list filters for the persistent audio registry."""
from __future__ import annotations

import math
import unicodedata
from datetime import datetime
from pathlib import Path

DAY_SECONDS = 86400
AUTO_RECOVERY_DAYS = 20
AUTO_RECOVERY_SECONDS = AUTO_RECOVERY_DAYS * DAY_SECONDS


def timestamp(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _video_metadata(state, channel_id, video_id):
    metadata = state.get("registry_metadata") or {}
    channel = metadata.get(channel_id) if isinstance(metadata, dict) else None
    video = channel.get(video_id) if isinstance(channel, dict) else None
    return video if isinstance(video, dict) else {}


def registry_added_at(state, channel_id, video_id):
    metadata = _video_metadata(state, channel_id, video_id)
    channel = (state.get("entries") or {}).get(channel_id)
    entry = channel.get(video_id) if isinstance(channel, dict) else None
    entry = entry if isinstance(entry, dict) else {}
    return timestamp(metadata.get("added_at")) or timestamp(entry.get("registered_at"))


def registry_expired(state, channel_id, video_id, now):
    added = registry_added_at(state, channel_id, video_id)
    metadata = _video_metadata(state, channel_id, video_id)
    return bool(timestamp(metadata.get("expired_at"))) or (
        added is not None and now >= added + AUTO_RECOVERY_SECONDS
    )


def sync_registry_metadata(state, now):
    """Keep the original enrollment date; migrate undated legacy rows once."""
    old = state.get("registry_metadata")
    old = old if isinstance(old, dict) else {}
    metadata = {}
    for channel_id, entries in (state.get("entries") or {}).items():
        if not isinstance(entries, dict):
            continue
        previous = old.get(channel_id)
        previous = previous if isinstance(previous, dict) else {}
        for video_id, entry in entries.items():
            if not isinstance(entry, dict):
                continue
            saved = previous.get(video_id)
            saved = dict(saved) if isinstance(saved, dict) else {}
            if timestamp(saved.get("added_at")) is None:
                registered = timestamp(entry.get("registered_at"))
                saved.update(added_at=registered or now, date_estimated=registered is None)
            saved["added_at"] = float(saved["added_at"])
            if now >= saved["added_at"] + AUTO_RECOVERY_SECONDS:
                saved["expired_at"] = saved["added_at"] + AUTO_RECOVERY_SECONDS
            metadata.setdefault(channel_id, {})[video_id] = saved
    changed = metadata != old or "registry_metadata" not in state
    state["registry_metadata"] = metadata
    return changed


def newest_registry_video_ids(state, channel_id, entries):
    # Reverse insertion order breaks equal timestamps in favor of the latest row.
    return sorted(reversed(list(entries)), key=lambda video_id:
                  registry_added_at(state, channel_id, video_id) or 0, reverse=True)


def registry_title(entry):
    return str(entry.get("title") or Path(str(entry.get("audio_path") or "")).stem)


def _search_text(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


def filter_registry_videos(rows, *, query="", min_days=None, max_days=None,
                           start_date="", end_date="", now):
    """Intersect title/ID/channel search, elapsed-day range and local dates."""
    needle = _search_text(query)
    result = []
    for row in rows:
        if needle and needle not in _search_text(" ".join(str(row.get(field) or "")
                for field in ("title", "video_id", "channel_id", "name", "audio_path"))):
            continue
        added = timestamp(row.get("added_at"))
        if any(value not in (None, "") for value in (min_days, max_days, start_date, end_date)):
            if added is None:
                continue
            age = max(0, now - added) / DAY_SECONDS
            if min_days is not None and age < float(min_days):
                continue
            if max_days is not None and age >= float(max_days):
                continue
            local_date = datetime.fromtimestamp(added).date().isoformat()
            if start_date and local_date < start_date or end_date and local_date > end_date:
                continue
        result.append(row)
    return result
