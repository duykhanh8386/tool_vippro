"""Persistent background recovery for creator-uploaded YouTube audio tracks.

The registry lives in the app SQLite database, so it survives browser/NiceGUI
disconnects and process restarts on the same machine or VM. Videos with any
healthy creator dub skip normal failure/missing repairs. Otherwise the monitor replaces failed tracks
and adds missing registered languages, without touching the source/original
audio or treating an unreadable response as an empty video.
Processing tracks observed for at least two hours are replaced by exact Track
ID, after a fresh status check. Younger tracks are left to finish.
"""

from __future__ import annotations

import asyncio
import re
import tempfile
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar, copy_context
from functools import partial
from pathlib import Path
from typing import Callable, Iterable, Mapping

from loguru import logger

from src.audio_language import call_audio_update_with_retry
from src.channel_store import channel_store
from src.module.audio_module import update_audio_module
from src.module.list_videos_module import list_videos_module
from src.state_manager import state_manager
from src.video_scan_dates import (
    DEFAULT_SCAN_DATE_TYPE, _status_indicates_draft, normalize_scan_date_type,
    normalize_scan_start_date, scan_date_bounds, validate_scan_start_date, video_matches_scan_dates,
)
from src.utils import multiply_audio, normalize_path
from src.youtube_caption_api import (
    CaptionAuthenticationError,
    CaptionQuotaExceededError,
    YouTubeCaptionClient,
    get_caption_quota_status,
)


RECOVERY_STATE_NAME = "audio_recovery"
RECOVERY_SCAN_MODE_ALL = "all"
RECOVERY_SCAN_MODE_SELECTED = "selected"
RECOVERY_SCAN_MODES = {
    RECOVERY_SCAN_MODE_ALL,
    RECOVERY_SCAN_MODE_SELECTED,
}
RECOVERY_VIDEO_SCOPE_PUBLIC = "public"
RECOVERY_VIDEO_SCOPE_SCHEDULED = "scheduled"
RECOVERY_VIDEO_SCOPE_BOTH = "public_and_scheduled"
RECOVERY_VIDEO_SCOPE_LABELS = {
    RECOVERY_VIDEO_SCOPE_PUBLIC: "Chỉ video công khai",
    RECOVERY_VIDEO_SCOPE_SCHEDULED: "Chỉ video đã lên lịch",
    RECOVERY_VIDEO_SCOPE_BOTH: "Công khai và đã lên lịch",
}
DEFAULT_RECOVERY_INTERVAL_SECONDS = 0
MONITOR_IDLE_POLL_SECONDS = 1.0
MAX_CONCURRENT_RECOVERY_CHANNELS = 3
DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS = 0
DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS = 0
DEFAULT_STALE_PROCESSING_SECONDS = 2 * 60 * 60
MIN_STALE_PROCESSING_SCANS = 2
PROCESSING_WARNING_REASON = "processing_timeout"
CAPTION_STATUS_CHECK_INTERVAL_SECONDS = 6 * 60 * 60
CAPTION_REPAIR_VERIFY_SECONDS = 15 * 60
REAUTH_ALERT_REASON = "encoded_reauth_proof_token_missing"
_REFRESH_ALERT_SECRET_RE = re.compile(
    r"(?i)\b(authorization|cookie|sapisidhash|sessiontoken|token)\b"
    r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|\S+)"
)
PUBLIC_VIDEO_PRIVACY_VALUES = {
    "PUBLIC",
    "VIDEO_PRIVACY_PUBLIC",
    "PRIVACY_PUBLIC",
}

# Shared with the manual add-audio page. Mutations are serialized per channel,
# so recovery on channel A can continue while the user works on channel B,
# without ever allowing two delete/add flows to collide on the same channel.
_AUDIO_MUTATION_GUARDS: dict[str, threading.Lock] = {}
_AUDIO_MUTATION_GUARDS_LOCK = threading.RLock()

_STATE_LOCK = threading.RLock()
_MONITOR_TASK: asyncio.Task | None = None
_MONITOR_STOP: asyncio.Event | None = None
_RECOVERY_CLEAR_GENERATION = 0

_RUNTIME_STATUS_LOCK = threading.RLock()
_RUNTIME_CHANNEL_CONTEXT: ContextVar[tuple[int, str] | None] = ContextVar(
    "audio_recovery_channel", default=None
)
_RECOVERY_WORKER_POOL: ContextVar[ThreadPoolExecutor | None] = ContextVar(
    "audio_recovery_worker_pool", default=None
)
_RUNTIME_STATUS = {
    "monitor_running": False,
    "active": False,
    "phase": "stopped",
    "message": "Tự động khôi phục audio chưa chạy",
    "cycle_id": 0,
    "cycle_started_at": None,
    "last_cycle_finished_at": None,
    "channel_index": 0,
    "channel_total": 0,
    "channel_concurrency": MAX_CONCURRENT_RECOVERY_CHANNELS,
    "completed_channel_count": 0,
    "completed_pass_count": 0,
    "waiting_channel_count": 0,
    "continuous": False,
    "_channel_passes": {},
    "_channel_jobs": {},
    "_channel_results": {},
    "channel_id": "",
    "video_id": "",
    "language": "",
    "repair_index": 0,
    "repair_total": 0,
    "repaired": 0,
    "failed": 0,
    "processing_warning_count": 0,
    "captions_repaired": 0,
    "captions_failed": 0,
    "caption_quota_message": "",
    "deferred_video_scope": 0,
    "deferred_visibility_unknown": 0,
    "scan_mode": RECOVERY_SCAN_MODE_ALL,
    "video_scan_scope": RECOVERY_VIDEO_SCOPE_PUBLIC,
    "selected_channel_ids": [],
    "_upload_progress": None,
}


async def _run_recovery_blocking(operation, *args, **kwargs):
    """Reserve worker capacity for registry channels, including their uploads."""
    pool = _RECOVERY_WORKER_POOL.get()
    if pool is None:
        return await asyncio.to_thread(operation, *args, **kwargs)
    context = copy_context()
    return await asyncio.get_running_loop().run_in_executor(
        pool, context.run, partial(operation, *args, **kwargs)
    )


def _update_runtime_status(**changes) -> None:
    with _RUNTIME_STATUS_LOCK:
        context = _RUNTIME_CHANNEL_CONTEXT.get()
        if context is None:
            _RUNTIME_STATUS.update(changes)
            return
        cycle_id, channel_id = context
        if _RUNTIME_STATUS.get("cycle_id") != cycle_id:
            return
        jobs = _RUNTIME_STATUS["_channel_jobs"]
        if channel_id not in jobs:
            _RUNTIME_STATUS["_channel_results"].pop(channel_id, None)
            _RUNTIME_STATUS["completed_channel_count"] = len(_RUNTIME_STATUS["_channel_results"])
            jobs[channel_id] = {"pass_index": _RUNTIME_STATUS["_channel_passes"].get(channel_id, 0) + 1}
        jobs[channel_id].update(changes)
        for key in (
            "repaired", "failed", "processing_warning_count", "captions_repaired",
            "captions_failed", "caption_quota_message",
        ):
            if key in changes:
                _RUNTIME_STATUS[key] = changes[key]


def _finish_channel_runtime_status(cycle_id: int, channel_id: str, result: dict) -> None:
    with _RUNTIME_STATUS_LOCK:
        if _RUNTIME_STATUS.get("cycle_id") == cycle_id:
            _RUNTIME_STATUS["_channel_jobs"].pop(channel_id, None)
            pass_count = _RUNTIME_STATUS["_channel_passes"].get(channel_id, 0) + 1
            _RUNTIME_STATUS["_channel_passes"][channel_id] = pass_count
            result["pass_count"] = pass_count
            _RUNTIME_STATUS["_channel_results"][channel_id] = dict(result)
            _RUNTIME_STATUS["completed_channel_count"] = len(_RUNTIME_STATUS["_channel_results"])
            _RUNTIME_STATUS["completed_pass_count"] += 1


def _with_upload_progress(snapshot: dict) -> dict:
    """Snapshot a progress mapping which may be updated by an upload thread."""
    upload = snapshot.pop("_upload_progress", None)
    upload = upload if isinstance(upload, dict) else {}
    try:
        sent = max(0, int(upload.get("sent") or 0))
    except (TypeError, ValueError):
        sent = 0
    try:
        total = max(0, int(upload.get("total") or 0))
    except (TypeError, ValueError):
        total = 0
    try:
        confirmed = max(0, min(total, int(upload.get("confirmed") or 0)))
    except (TypeError, ValueError):
        confirmed = 0
    snapshot["upload_sent"] = sent
    snapshot["upload_total"] = total
    snapshot["upload_confirmed"] = confirmed
    snapshot["upload_status"] = str(upload.get("status") or "")
    snapshot["upload_fraction"] = min(1.0, sent / total) if total else 0.0
    output_path = snapshot.pop("_preparation_output_path", None)
    snapshot["preparation_elapsed_seconds"] = 0
    snapshot["preparation_bytes"] = 0
    if snapshot.get("phase") == "preparing":
        try:
            started_at = float(snapshot.get("preparation_started_at") or time.time())
            snapshot["preparation_elapsed_seconds"] = max(0, int(time.time() - started_at))
        except (ValueError, TypeError):
            pass
        if output_path:
            try:
                snapshot["preparation_bytes"] = Path(output_path).stat().st_size
            except OSError:
                pass
    return snapshot


def get_audio_recovery_runtime_status() -> dict:
    """Return UI-safe live scan/upload progress for the global drawer."""
    with _RUNTIME_STATUS_LOCK:
        snapshot = dict(_RUNTIME_STATUS)
        snapshot.pop("_channel_passes", None)
        jobs = [dict(job) for job in snapshot.pop("_channel_jobs", {}).values()]
        results = snapshot.pop("_channel_results", {})
        snapshot["channel_results"] = [dict(result) for result in results.values()]
    snapshot["channels"] = [_with_upload_progress(job) for job in jobs]
    snapshot["active_channel_count"] = len(jobs)
    if jobs:
        snapshot.pop("_upload_progress", None)
        priority = {"uploading": 3, "preparing": 2, "captioning": 1}
        focus = max(snapshot["channels"], key=lambda job: priority.get(job.get("phase"), 0))
        snapshot.update({
            key: value for key, value in focus.items()
            if key not in {"repaired", "failed", "captions_repaired", "captions_failed",
                           "processing_warning_count", "caption_quota_message", "channel_total"}
        })
        return snapshot
    return _with_upload_progress(snapshot)


def get_audio_mutation_guard(channel_id: str) -> threading.Lock:
    clean_channel_id = str(channel_id or "").strip()
    if not clean_channel_id:
        raise ValueError("channel_id is required for an audio mutation guard")
    with _AUDIO_MUTATION_GUARDS_LOCK:
        guard = _AUDIO_MUTATION_GUARDS.get(clean_channel_id)
        if guard is None:
            guard = threading.Lock()
            _AUDIO_MUTATION_GUARDS[clean_channel_id] = guard
        return guard


def _is_public_video_privacy(value: object) -> bool:
    return str(value or "").strip().upper() in PUBLIC_VIDEO_PRIVACY_VALUES


def _is_currently_public_video(video: object) -> bool:
    if not _is_public_video_privacy(getattr(video, "privacy", "")):
        return False
    if _status_indicates_draft(getattr(video, "draft_status", "")):
        return False
    if _status_indicates_draft(getattr(video, "video_status", "")):
        return False
    # Studio omits this object after scheduled publication. A non-empty value
    # means the video is still waiting for its public release time even if its
    # target privacy is PUBLIC.
    if getattr(video, "scheduled_publishing_details", None):
        return False
    return True


def _is_currently_scheduled_video(video: object) -> bool:
    if _status_indicates_draft(getattr(video, "draft_status", "")):
        return False
    if _status_indicates_draft(getattr(video, "video_status", "")):
        return False
    return bool(getattr(video, "scheduled_publishing_details", None))


def _video_matches_recovery_scope(video: object, video_scan_scope: str) -> bool:
    scope = _normalize_recovery_video_scope(video_scan_scope)
    if scope == RECOVERY_VIDEO_SCOPE_PUBLIC:
        return _is_currently_public_video(video)
    if scope == RECOVERY_VIDEO_SCOPE_SCHEDULED:
        return _is_currently_scheduled_video(video)
    return _is_currently_public_video(video) or _is_currently_scheduled_video(video)


def _get_registered_video_scan_statuses(
    channel_id: str,
    video_ids: Iterable[str],
    *,
    video_scan_scope: str = RECOVERY_VIDEO_SCOPE_PUBLIC,
    scan_start_date: str = "",
    scan_date_type: str = DEFAULT_SCAN_DATE_TYPE,
) -> tuple[dict[str, bool], set[str]]:
    """Resolve whether registered IDs match the selected video scope.

    Returns ``(matches_by_video_id, unresolved_video_ids)``. Draft rows
    are not consistently returned by Studio's unfiltered listing; unresolved
    IDs are therefore deferred just like videos outside the scope and remain
    registered for a later cycle.
    """
    requested = list(
        dict.fromkeys(str(video_id or "").strip() for video_id in video_ids)
    )
    requested = [video_id for video_id in requested if video_id]
    remaining = set(requested)
    date_bounds = scan_date_bounds(scan_start_date)
    matches_by_video_id: dict[str, bool] = {}
    seen_page_tokens: set[str] = set()
    page_token: str | None = None

    while remaining:
        videos, next_page_token = list_videos_module.list_all_videos(
            channel_id,
            limit=50,
            page_token=page_token,
        )
        for video in videos:
            video_id = str(getattr(video, "id", "") or "").strip()
            if video_id not in remaining:
                continue
            matches_by_video_id[video_id] = _video_matches_recovery_scope(
                video, video_scan_scope
            ) and video_matches_scan_dates(video, date_bounds, date_type=scan_date_type)
            remaining.discard(video_id)

        if not next_page_token or not remaining:
            break
        clean_page_token = str(next_page_token)
        if clean_page_token in seen_page_tokens:
            raise RuntimeError(
                "YouTube returned a repeated page token while checking "
                "auto-recovery video visibility"
            )
        seen_page_tokens.add(clean_page_token)
        page_token = clean_page_token

    return matches_by_video_id, remaining


def _default_state() -> dict:
    return {
        "enabled": True,
        # Existing installations intentionally migrate to the product default:
        # every channel which already has entries in the persistent registry.
        "scan_mode": RECOVERY_SCAN_MODE_ALL,
        "video_scan_scope": RECOVERY_VIDEO_SCOPE_PUBLIC,
        "scan_start_date": "",
        "scan_date_type": DEFAULT_SCAN_DATE_TYPE,
        "selected_channel_ids": [],
        "disabled_channel_ids": [],
        "disabled_video_ids": {},
        "removed_video_ids": {},
        "interval_seconds": DEFAULT_RECOVERY_INTERVAL_SECONDS,
        "retry_cooldown_seconds": DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS,
        "initial_grace_seconds": DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS,
        "stale_processing_seconds": DEFAULT_STALE_PROCESSING_SECONDS,
        "entries": {},
        "channel_refresh_alerts": {},
        "last_cycle_at": None,
        "last_cycle_result": {},
    }


def _load_state() -> dict:
    raw = state_manager.load_state(RECOVERY_STATE_NAME) or {}
    state = _default_state()
    if isinstance(raw, dict):
        state.update(raw)
    if not isinstance(state.get("entries"), dict):
        state["entries"] = {}
    state["scan_mode"] = _normalize_recovery_scan_mode(state.get("scan_mode"))
    state["video_scan_scope"] = _normalize_recovery_video_scope(
        state.get("video_scan_scope")
    )
    try:
        state["scan_start_date"] = normalize_scan_start_date(state.get("scan_start_date"))
    except ValueError:
        state["scan_start_date"] = ""
    state["scan_date_type"] = normalize_scan_date_type(state.get("scan_date_type"))
    state["selected_channel_ids"] = _normalize_channel_ids(
        state.get("selected_channel_ids")
    )
    state["disabled_channel_ids"] = _normalize_channel_ids(
        state.get("disabled_channel_ids")
    )
    state["disabled_video_ids"] = _normalize_video_ids_by_channel(
        state.get("disabled_video_ids")
    )
    state["removed_video_ids"] = _normalize_video_ids_by_channel(
        state.get("removed_video_ids")
    )
    if not isinstance(state.get("channel_refresh_alerts"), dict):
        state["channel_refresh_alerts"] = {}
    else:
        # Discard alerts created by the short-lived implementation which
        # required a refresh before every scheduled cycle.  Refresh is now
        # required only after YouTube actually rejects the reauth proof flow.
        state["channel_refresh_alerts"] = {
            str(channel_id): alert
            for channel_id, alert in state["channel_refresh_alerts"].items()
            if isinstance(alert, dict)
            and alert.get("reason") == REAUTH_ALERT_REASON
        }
    # Remove legacy delays for both scanning and audio repair. Every cycle
    # decides from fresh YouTube status, including just-registered tracks.
    state["interval_seconds"] = DEFAULT_RECOVERY_INTERVAL_SECONDS
    state["retry_cooldown_seconds"] = DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS
    state["initial_grace_seconds"] = DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS
    state["stale_processing_seconds"] = DEFAULT_STALE_PROCESSING_SECONDS
    return state


def _normalize_recovery_scan_mode(value: object) -> str:
    mode = str(value or "").strip().casefold()
    if mode not in RECOVERY_SCAN_MODES:
        return RECOVERY_SCAN_MODE_ALL
    return mode


def _normalize_recovery_video_scope(value: object) -> str:
    scope = str(value or "").strip().casefold()
    return scope if scope in RECOVERY_VIDEO_SCOPE_LABELS else RECOVERY_VIDEO_SCOPE_PUBLIC


def _normalize_channel_ids(channel_ids: object) -> list[str]:
    if isinstance(channel_ids, str):
        values = [channel_ids]
    elif isinstance(channel_ids, Iterable):
        values = channel_ids
    else:
        values = []
    return list(
        dict.fromkeys(
            clean_id
            for channel_id in values
            if (clean_id := str(channel_id or "").strip())
        )
    )


def _scan_preferences_from_state(state: dict) -> dict:
    return {
        "scan_mode": _normalize_recovery_scan_mode(state.get("scan_mode")),
        "video_scan_scope": _normalize_recovery_video_scope(state.get("video_scan_scope")),
        "scan_start_date": normalize_scan_start_date(state.get("scan_start_date")),
        "scan_date_type": normalize_scan_date_type(state.get("scan_date_type")),
        "selected_channel_ids": _normalize_channel_ids(
            state.get("selected_channel_ids")
        ),
    }


def _normalize_video_ids_by_channel(value: object) -> dict[str, list[str]]:
    if not isinstance(value, Mapping):
        return {}
    result = {}
    for channel_id, video_ids in value.items():
        clean_channel = str(channel_id or "").strip()
        clean_videos = _normalize_channel_ids(video_ids)
        if clean_channel and clean_videos:
            result[clean_channel] = clean_videos
    return result


def _channel_is_in_recovery_scope(state: dict, channel_id: str) -> bool:
    clean_channel_id = str(channel_id or "").strip()
    if not clean_channel_id or clean_channel_id in _normalize_channel_ids(
        state.get("disabled_channel_ids")
    ):
        return False
    preferences = _scan_preferences_from_state(state)
    if preferences["scan_mode"] == RECOVERY_SCAN_MODE_ALL:
        return True
    return clean_channel_id in set(
        preferences["selected_channel_ids"]
    )


def _video_is_in_recovery_scope(state: dict, channel_id: str, video_id: str) -> bool:
    clean_channel = str(channel_id or "").strip()
    clean_video = str(video_id or "").strip()
    disabled = _normalize_video_ids_by_channel(state.get("disabled_video_ids"))
    entries = (state.get("entries") or {}).get(clean_channel, {})
    return (
        bool(clean_video)
        and isinstance(entries, dict)
        and isinstance(entries.get(clean_video), dict)
        and _channel_is_in_recovery_scope(state, clean_channel)
        and clean_video not in disabled.get(clean_channel, [])
    )


def register_audio_recovery(
    *,
    channel_id: str,
    video_id: str,
    audio_path: str,
    languages: Iterable[str],
    repeat_times: int,
    extra_minutes: float,
    registered_at: float | None = None,
    merge_languages: bool = False,
) -> bool:
    """Persist one successfully matched/uploaded video for later recovery."""
    clean_channel = str(channel_id or "").strip()
    clean_video = str(video_id or "").strip()
    clean_path = str(audio_path or "").strip()
    clean_languages = list(
        dict.fromkeys(
            str(language or "").strip()
            for language in languages
            if str(language or "").strip()
        )
    )
    if not clean_channel or not clean_video or not clean_path or not clean_languages:
        return False

    with _STATE_LOCK:
        state = _load_state()
        channels = state.setdefault("entries", {})
        videos = channels.setdefault(clean_channel, {})
        previous = videos.get(clean_video)
        same_audio_configuration = False
        attempts = previous.get("attempts", {}) if isinstance(previous, dict) else {}
        if isinstance(previous, dict):
            same_audio_configuration = (
                str(previous.get("audio_path") or "") == clean_path
                and int(previous.get("repeat_times") or 1) == max(1, int(repeat_times))
                and float(previous.get("extra_minutes") or 0)
                == max(0.0, float(extra_minutes))
            )
            if merge_languages and same_audio_configuration:
                clean_languages = list(
                    dict.fromkeys(
                        [
                            str(language or "").strip()
                            for language in previous.get("languages") or []
                            if str(language or "").strip()
                        ]
                        + clean_languages
                    )
                )
            languages_changed = (
                list(previous.get("languages") or []) != clean_languages
            )
            if not same_audio_configuration or (
                languages_changed and not merge_languages
            ):
                attempts = {}
        updated_entry = {
            "audio_path": clean_path,
            "languages": clean_languages,
            "repeat_times": max(1, int(repeat_times)),
            "extra_minutes": max(0.0, float(extra_minutes)),
            "registered_at": (
                time.time() if registered_at is None else float(registered_at)
            ),
            "attempts": attempts if isinstance(attempts, dict) else {},
        }
        # Re-registering audio must not discard a caption track which is still
        # waiting for YouTube to settle into ``serving`` or ``failed``.
        if isinstance(previous, dict) and isinstance(
            previous.get("caption_monitor"), dict
        ):
            updated_entry["caption_monitor"] = dict(
                previous["caption_monitor"]
            )
        if (
            same_audio_configuration
            and isinstance(previous, dict)
            and isinstance(previous.get("processing_observations"), dict)
        ):
            # Keep the first-seen timestamp across page reloads and tool
            # restarts. A different source/configuration starts a fresh clock.
            updated_entry["processing_observations"] = dict(
                previous["processing_observations"]
            )
        videos[clean_video] = updated_entry
        # A new manual submission can enroll a previously removed video again.
        removed = _normalize_video_ids_by_channel(state.get("removed_video_ids"))
        remaining = [video for video in removed.get(clean_channel, []) if video != clean_video]
        if remaining:
            removed[clean_channel] = remaining
        else:
            removed.pop(clean_channel, None)
        state["removed_video_ids"] = removed
        saved = state_manager.save_state(RECOVERY_STATE_NAME, state)
    if saved:
        logger.info(
            "Audio auto-recovery registered: channel={} video={} languages={}",
            clean_channel,
            clean_video,
            ",".join(clean_languages),
        )
    return saved


def register_caption_monitor(
    *,
    channel_id: str,
    video_id: str,
    source_srt_path: str,
    source_language: str,
    languages: Iterable[str],
    now: float | None = None,
) -> bool:
    """Monitor only submitted caption tracks until YouTube marks them serving."""
    clean_channel = str(channel_id or "").strip()
    clean_video = str(video_id or "").strip()
    clean_languages = list(
        dict.fromkeys(
            str(language or "").strip()
            for language in languages
            if str(language or "").strip()
        )
    )
    if not clean_channel or not clean_video:
        return False
    timestamp = time.time() if now is None else float(now)
    with _STATE_LOCK:
        state = _load_state()
        entry = (
            state.get("entries", {})
            .get(clean_channel, {})
            .get(clean_video)
        )
        if not isinstance(entry, dict):
            return False
        if clean_languages:
            entry["caption_monitor"] = {
                "source_srt_path": str(source_srt_path or "").strip(),
                "source_language": str(source_language or "").strip(),
                "languages": clean_languages,
                "next_check_at": timestamp + CAPTION_REPAIR_VERIFY_SECONDS,
                "last_error": "",
            }
        else:
            entry.pop("caption_monitor", None)
        return state_manager.save_state(RECOVERY_STATE_NAME, state)


def import_add_audio_flow_recovery_state() -> int:
    """Enroll completed legacy Add Audio Flow items in automatic recovery.

    Older Add Audio Flow runs persisted their video/music/language results but
    did not register them with ``audio_recovery``.  Import the latest persisted
    flow snapshot once at application startup.  Existing recovery mappings are
    never overwritten because they may contain a newer manual configuration.
    """
    flow_state = state_manager.load_state("add_audio_flow") or {}
    if not isinstance(flow_state, dict):
        return 0

    channel_id = str(flow_state.get("selected_channel") or "").strip()
    statuses = flow_state.get("statuses") or {}
    if not channel_id or not isinstance(statuses, dict):
        return 0

    with _STATE_LOCK:
        recovery_state = _load_state()
        existing_videos = (
            recovery_state.get("entries", {}).get(channel_id, {}) or {}
        )
        existing_video_ids = set(existing_videos)
        removed_video_ids = set(
            _normalize_video_ids_by_channel(recovery_state.get("removed_video_ids"))
            .get(channel_id, [])
        )

    imported = 0
    for item in statuses.values():
        if not isinstance(item, dict):
            continue
        video_id = str(item.get("video_id") or "").strip()
        audio_path = str(item.get("music_path") or "").strip()
        if (
            not video_id or not audio_path
            or video_id in existing_video_ids
            or video_id in removed_video_ids
        ):
            continue

        language_results = item.get("audio_language_results") or {}
        if not isinstance(language_results, dict):
            continue
        languages = [
            str(language).strip()
            for language, result in language_results.items()
            if str(language).strip()
            and isinstance(result, dict)
            and result.get("status") in ("successful", "already_added")
        ]
        if not languages:
            continue

        if register_audio_recovery(
            channel_id=channel_id,
            video_id=video_id,
            audio_path=audio_path,
            languages=languages,
            repeat_times=1,
            extra_minutes=0,
            # These are already-completed legacy uploads, so make them eligible
            # for the first startup scan instead of applying a new 15m grace.
            registered_at=0,
        ):
            imported += 1
            existing_video_ids.add(video_id)

    if imported:
        logger.info(
            "Imported {} Add Audio Flow video(s) into audio auto-recovery.",
            imported,
        )
    return imported


def clear_audio_recovery_registry() -> bool:
    """Forget every automatic recovery mapping for the add-audio page."""
    global _RECOVERY_CLEAR_GENERATION
    with _STATE_LOCK:
        # A running cycle holds a snapshot of the old registry. Invalidate it
        # so clearing data also stops any remaining automatic recovery work.
        _RECOVERY_CLEAR_GENERATION += 1
        state = _load_state()
        state["entries"] = {}
        state["channel_refresh_alerts"] = {}
        state["last_cycle_at"] = None
        state["last_cycle_result"] = {}
        return state_manager.save_state(RECOVERY_STATE_NAME, state)


def _recovery_was_cleared(generation: int) -> bool:
    with _STATE_LOCK:
        return generation != _RECOVERY_CLEAR_GENERATION


def get_audio_recovery_state() -> dict:
    """Expose a snapshot for diagnostics and tests."""
    with _STATE_LOCK:
        return _load_state()


def get_audio_recovery_registry_items() -> tuple[list[dict], list[dict]]:
    """List registered channels and videos with their effective scan status."""
    state = get_audio_recovery_state()
    channels = []
    videos = []
    disabled_videos = _normalize_video_ids_by_channel(state.get("disabled_video_ids"))
    for channel_id, entries in sorted((state.get("entries") or {}).items()):
        if not isinstance(entries, dict):
            continue
        channel_enabled = _channel_is_in_recovery_scope(state, channel_id)
        excluded = set(disabled_videos.get(channel_id, []))
        channel_videos = []
        for video_id, entry in sorted(entries.items()):
            if not isinstance(entry, dict):
                continue
            video_enabled = video_id not in excluded
            trackers = entry.get("processing_observations")
            if not isinstance(trackers, dict):
                trackers = {}
            processing_warnings = [
                {
                    "language": tracker.get("language") or language,
                    "reason": tracker["warning_reason"],
                    "track_ids": list(tracker.get("track_ids") or []),
                    "first_seen_at": tracker.get("first_seen_at"),
                    "last_seen_at": tracker.get("last_seen_at"),
                    "warned_at": tracker.get("warned_at"),
                }
                for language, tracker in trackers.items()
                if isinstance(tracker, dict)
                and tracker.get("warning_reason") == PROCESSING_WARNING_REASON
            ]
            channel_videos.append({
                "channel_id": channel_id,
                "video_id": video_id,
                "languages": list(entry.get("languages") or []),
                "processing_warnings": processing_warnings,
                "enabled": (
                    bool(state.get("enabled", True)) and channel_enabled and video_enabled
                ),
                "channel_enabled": channel_enabled,
                "video_enabled": video_enabled,
            })
        videos.extend(channel_videos)
        channels.append({
            "channel_id": channel_id,
            "enabled": bool(state.get("enabled", True)) and channel_enabled,
            "video_count": len(channel_videos),
            "active_video_count": sum(video["enabled"] for video in channel_videos),
            "processing_warning_count": sum(len(video["processing_warnings"]) for video in channel_videos),
        })
    return channels, videos


def get_audio_recovery_scan_preferences() -> dict:
    """Return the persisted channel and video scopes for automatic recovery."""
    with _STATE_LOCK:
        return _scan_preferences_from_state(_load_state())


def set_audio_recovery_scan_preferences(
    *,
    scan_mode: str | None = None,
    selected_channel_ids: Iterable[str] | None = None,
    video_scan_scope: str | None = None,
    scan_start_date: str | None = None,
    scan_date_type: str | None = None,
) -> bool:
    """Persist the scan mode without changing registry entries or history.

    ``selected_channel_ids`` is deliberately preserved when switching to the
    all-channels mode, allowing the previous custom list to be restored later.
    """
    with _STATE_LOCK:
        state = _load_state()
        if scan_mode is not None:
            state["scan_mode"] = _normalize_recovery_scan_mode(scan_mode)
        if video_scan_scope is not None:
            state["video_scan_scope"] = _normalize_recovery_video_scope(video_scan_scope)
        if scan_start_date is not None:
            state["scan_start_date"] = validate_scan_start_date(scan_start_date)
        if scan_date_type is not None:
            state["scan_date_type"] = normalize_scan_date_type(scan_date_type)
        if selected_channel_ids is not None:
            state["selected_channel_ids"] = _normalize_channel_ids(
                selected_channel_ids
            )
        return state_manager.save_state(RECOVERY_STATE_NAME, state)


def is_audio_recovery_channel_enabled(channel_id: str) -> bool:
    """Check the latest scope so a deselection takes effect between tracks."""
    clean_channel_id = str(channel_id or "").strip()
    if not clean_channel_id:
        return False
    with _STATE_LOCK:
        state = _load_state()
        return bool(state.get("enabled", True)) and _channel_is_in_recovery_scope(state, clean_channel_id)


def is_audio_recovery_video_enabled(channel_id: str, video_id: str) -> bool:
    """Check live opt-outs before scheduling another video or language."""
    with _STATE_LOCK:
        return _video_is_in_recovery_scope(_load_state(), channel_id, video_id)


def _enabled_recovery_video_ids(channel_id: str, video_ids: Iterable[str]) -> list[str]:
    """Filter a batch with one state read, even for large channel registries."""
    with _STATE_LOCK:
        state = _load_state()
        if not _channel_is_in_recovery_scope(state, channel_id):
            return []
        disabled = _normalize_video_ids_by_channel(state.get("disabled_video_ids"))
        excluded = set(disabled.get(channel_id, []))
        entries = (state.get("entries") or {}).get(channel_id, {})
        if not isinstance(entries, dict):
            return []
        return [
            video_id for video_id in video_ids
            if video_id not in excluded and isinstance(entries.get(video_id), dict)
        ]


def set_audio_recovery_items_enabled(
    *,
    enabled: bool,
    channel_ids: Iterable[str] = (),
    video_ids_by_channel: Mapping[str, Iterable[str]] | None = None,
) -> bool:
    """Persist bulk opt-outs, keeping registered files, tracks and history intact.

    Channel opt-outs apply even in all-channels mode. Video opt-outs belong to
    their channel and survive re-registration. Enabling a video leaves its
    parent's scan scope unchanged.
    """
    clean_channels = _normalize_channel_ids(channel_ids)
    clean_videos = _normalize_video_ids_by_channel(video_ids_by_channel)
    if not clean_channels and not clean_videos:
        return False
    with _STATE_LOCK:
        state = _load_state()
        disabled_channels = set(state.get("disabled_channel_ids") or [])
        selected_channels = set(state.get("selected_channel_ids") or [])
        if enabled:
            disabled_channels.difference_update(clean_channels)
            if state["scan_mode"] == RECOVERY_SCAN_MODE_SELECTED:
                selected_channels.update(clean_channels)
                state["selected_channel_ids"] = sorted(selected_channels)
        else:
            disabled_channels.update(clean_channels)
        state["disabled_channel_ids"] = sorted(disabled_channels)
        disabled_videos = _normalize_video_ids_by_channel(
            state.get("disabled_video_ids")
        )
        for channel_id, video_ids in clean_videos.items():
            excluded = set(disabled_videos.get(channel_id, []))
            if enabled:
                excluded.difference_update(video_ids)
            else:
                excluded.update(video_ids)
            if excluded:
                disabled_videos[channel_id] = sorted(excluded)
            else:
                disabled_videos.pop(channel_id, None)
        state["disabled_video_ids"] = disabled_videos
        return state_manager.save_state(RECOVERY_STATE_NAME, state)


def remove_audio_recovery_items(
    *,
    channel_ids: Iterable[str] = (),
    video_ids_by_channel: Mapping[str, Iterable[str]] | None = None,
) -> bool:
    """Remove selected registry entries and stop scheduling their recovery.

    Remember removed video IDs so the legacy startup import cannot resurrect
    them. Other registry entries and manual-page history remain intact.
    """
    clean_channels = set(_normalize_channel_ids(channel_ids))
    clean_videos = _normalize_video_ids_by_channel(video_ids_by_channel)
    if not clean_channels and not clean_videos:
        return False
    with _STATE_LOCK:
        state = _load_state()
        entries = state["entries"]
        removed = _normalize_video_ids_by_channel(state.get("removed_video_ids"))
        disabled_videos = _normalize_video_ids_by_channel(state.get("disabled_video_ids"))
        empty_channels = set()

        for channel_id in clean_channels:
            channel_entries = entries.pop(channel_id, {})
            if isinstance(channel_entries, dict):
                removed[channel_id] = sorted(
                    set(removed.get(channel_id, [])) | set(channel_entries)
                )
            disabled_videos.pop(channel_id, None)
            empty_channels.add(channel_id)

        for channel_id, video_ids in clean_videos.items():
            channel_entries = entries.get(channel_id)
            if isinstance(channel_entries, dict):
                for video_id in video_ids:
                    channel_entries.pop(video_id, None)
                if not channel_entries:
                    entries.pop(channel_id, None)
                    empty_channels.add(channel_id)
            removed[channel_id] = sorted(
                set(removed.get(channel_id, [])) | set(video_ids)
            )
            excluded = set(disabled_videos.get(channel_id, [])) - set(video_ids)
            if excluded:
                disabled_videos[channel_id] = sorted(excluded)
            else:
                disabled_videos.pop(channel_id, None)

        state["disabled_channel_ids"] = [
            channel_id for channel_id in state.get("disabled_channel_ids", [])
            if channel_id not in clean_channels
        ]
        state["selected_channel_ids"] = [
            channel_id for channel_id in state.get("selected_channel_ids", [])
            if channel_id not in clean_channels
        ]
        state["disabled_video_ids"] = disabled_videos
        state["removed_video_ids"] = _normalize_video_ids_by_channel(removed)
        alerts = state.get("channel_refresh_alerts") or {}
        for channel_id in empty_channels:
            alerts.pop(channel_id, None)
        state["channel_refresh_alerts"] = alerts
        return state_manager.save_state(RECOVERY_STATE_NAME, state)


def get_channel_refresh_alerts() -> dict[str, dict]:
    """Return channels which must be refreshed before automatic recovery."""
    with _STATE_LOCK:
        alerts = _load_state().get("channel_refresh_alerts") or {}
        return {
            str(channel_id): dict(alert)
            for channel_id, alert in alerts.items()
            if isinstance(alert, dict)
        }


def mark_channel_refresh_required(
    channel_id: str,
    error: BaseException | str,
    *,
    now: float | None = None,
    channel_name: str = "",
    validation_failed: bool = False,
) -> bool:
    """Persist a reload warning after YouTube rejects the reauth proof flow."""
    clean_channel_id = str(channel_id or "").strip()
    if not clean_channel_id:
        return False
    requested_at = float(now if now is not None else time.time())
    clean_channel_name = str(channel_name or "").strip()
    if not clean_channel_name:
        try:
            channel = channel_store.get_channel(clean_channel_id) or {}
            clean_channel_name = str(channel.get("name") or "").strip()
        except Exception:
            clean_channel_name = ""
    error_text = " ".join(str(error or "").split())
    error_text = _REFRESH_ALERT_SECRET_RE.sub(
        lambda match: f"{match.group(1)}=<redacted>", error_text
    )[:500]
    with _STATE_LOCK:
        state = _load_state()
        alerts = state.setdefault("channel_refresh_alerts", {})
        alerts[clean_channel_id] = {
            "requested_at": requested_at,
            "reason": REAUTH_ALERT_REASON,
            "channel_name": clean_channel_name,
            "error": error_text,
            "severity": "error" if validation_failed else "warning",
            "validation_failed": bool(validation_failed),
            "message": (
                "Kiểm tra session token thất bại sau khi load lại kênh."
                if validation_failed
                else "YouTube không cấp token xác thực cho kênh. Vui lòng đăng nhập "
                "và tải lại thông tin kênh để tiếp tục tự động khôi phục audio."
            ),
        }
        saved = state_manager.save_state(RECOVERY_STATE_NAME, state)
    if saved:
        log = logger.error if validation_failed else logger.warning
        log(
            "Audio auto-recovery paused for channel={} name={!r}: session token "
            "validation_failed={}; login/channel reload required.",
            clean_channel_id,
            clean_channel_name,
            bool(validation_failed),
        )
    return saved


def _requires_channel_refresh(error: BaseException) -> bool:
    """Recognize the specific YouTube reauth failure through wrapped errors."""
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if "encodedreauthprooftoken" in str(current).casefold():
            return True
        current = current.__cause__ or current.__context__
    return False


def acknowledge_channel_refresh(channel_ids: Iterable[str]) -> int:
    """Clear alerts for channels successfully reloaded by ChannelFetcher."""
    refreshed = {str(channel_id or "").strip() for channel_id in channel_ids}
    refreshed.discard("")
    if not refreshed:
        return 0
    with _STATE_LOCK:
        state = _load_state()
        alerts = state.setdefault("channel_refresh_alerts", {})
        removed = sum(1 for channel_id in refreshed if channel_id in alerts)
        for channel_id in refreshed:
            alerts.pop(channel_id, None)
        if removed:
            state_manager.save_state(RECOVERY_STATE_NAME, state)
    if removed:
        logger.info(
            "Channel refresh acknowledged for audio recovery: channels={}",
            ",".join(sorted(refreshed)),
        )
    return removed


def _track_language(track: dict) -> str:
    value = (
        track.get("language")
        or track.get("languageCode")
        or track.get("targetLanguage")
        or ""
    )
    if isinstance(value, dict):
        value = value.get("languageCode") or value.get("code") or value.get("id") or ""
    return str(value).strip()


def _track_has_terminal_failure(track: dict) -> bool:
    """Exclude active PROCESSING tracks; repair only failed/deleted outcomes."""
    terminal_markers = (
        "FAILED",
        "FAILURE",
        "ERROR",
        "REJECTED",
        "INELIGIBLE",
        "NOT_ELIGIBLE",
        "UNPROCESSABLE",
        "UNABLE_TO_PROCESS",
        "DELETED",
        "REMOVED",
    )

    def walk(value) -> bool:
        if isinstance(value, dict):
            return any(walk(child) for child in value.values())
        if isinstance(value, (list, tuple)):
            return any(walk(child) for child in value)
        if not isinstance(value, str):
            return False
        normalized = value.upper()
        return any(marker in normalized for marker in terminal_markers)

    return walk(track)


def _terminal_failure_details(track: dict) -> str:
    """Return concise Studio status/reason values for support diagnostics."""
    terminal_markers = (
        "FAILED",
        "FAILURE",
        "ERROR",
        "REJECTED",
        "INELIGIBLE",
        "NOT_ELIGIBLE",
        "UNPROCESSABLE",
        "UNABLE_TO_PROCESS",
        "DELETED",
        "REMOVED",
    )
    details: list[str] = []

    def walk(value, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}" if path else str(key))
            return
        if isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
            return
        if not isinstance(value, str):
            return
        normalized = value.upper()
        if any(marker in normalized for marker in terminal_markers):
            detail = f"{path}={value}" if path else value
            if detail not in details:
                details.append(detail)

    walk(track)
    return "; ".join(details[:8]) or "terminal status without detail"


def build_audio_recovery_plan(
    payload: dict,
    requested_entries: dict[str, dict],
    requested_order: list[str] | None = None,
    *,
    observation_sink: dict | None = None,
) -> tuple[list[dict], set[str]]:
    """Build repairs only for videos without any healthy creator dub.

    Returns ``(actions, unreadable_video_ids)``. Each action either replaces
    failed track IDs or adds a missing registered language. Any healthy creator dub,
    including languages outside the registry, protects the entire video.
    Original/source audio and published subtitles do not count as healthy dubs.
    """
    requested_order = requested_order or list(requested_entries)
    requested = set(requested_entries)
    groups = payload.get("videoTranslations") or []
    tracks = payload.get("audioTracks") or []
    if not isinstance(groups, list) or not isinstance(tracks, list):
        return [], requested
    terminal_targets, unreadable_ids = (
        update_audio_module._terminal_repair_targets_from_payload(
            payload, requested_order
        )
    )
    valid_groups = [group for group in groups if isinstance(group, dict)]
    group_ids = [
        update_audio_module._translation_group_video_id(group)
        for group in valid_groups
    ]
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
    translations_by_track: dict[tuple[str, str], dict] = {}
    for video_id, group in group_pairs:
        translations = group.get("translations") or []
        if not isinstance(translations, list) or any(
            not isinstance(item, dict) for item in translations
        ):
            unreadable_ids.add(video_id)
            continue
        clean_items = [item for item in translations if isinstance(item, dict)]
        translations_by_video[video_id] = clean_items
        for item in clean_items:
            audio = item.get("audioTranslation") or {}
            if not isinstance(audio, dict):
                continue
            track_id = str(audio.get("audioTrackId") or "").strip()
            if track_id:
                translations_by_track[(video_id, track_id)] = item

    source_track_ids: dict[str, set[str]] = {}
    creator_track_ids: dict[str, set[str]] = {}
    observations: dict[str, dict[str, set[str]]] = {}
    observation_track_ids: dict[
        str, dict[str, dict[str, set[str]]]
    ] = {}

    def observe(
        video_id: str,
        language: str,
        state: str,
        track_id: str = "",
    ) -> None:
        clean_language = str(language or "").strip().casefold()
        # A healthy track still protects its video when Studio omits the
        # language. Keep that evidence under the empty key; it never produces
        # a language-level repair action.
        if not clean_language and state != "healthy":
            return
        observations.setdefault(video_id, {}).setdefault(
            clean_language, set()
        ).add(state)
        clean_track_id = str(track_id or "").strip()
        if clean_track_id:
            observation_track_ids.setdefault(video_id, {}).setdefault(
                clean_language, {}
            ).setdefault(state, set()).add(clean_track_id)

    if isinstance(tracks, list):
        for track in tracks:
            if not isinstance(track, dict):
                continue
            video_id = str(track.get("videoId") or "").strip()
            if video_id not in requested:
                continue
            track_id = str(track.get("audioTrackId") or "").strip()
            if not update_audio_module._is_creator_dubbed_track(track):
                if track_id:
                    source_track_ids.setdefault(video_id, set()).add(track_id)
                continue
            if track_id:
                creator_track_ids.setdefault(video_id, set()).add(track_id)
            translation = translations_by_track.get((video_id, track_id), {})
            language = (
                update_audio_module._translation_language(track)
                or update_audio_module._translation_language(translation)
                or ""
            )
            if update_audio_module._audio_payload_has_terminal_failure(
                track, assume_audio=True
            ):
                state = "terminal"
            elif update_audio_module._audio_payload_needs_attention(
                track, assume_audio=True
            ):
                state = "inflight"
            elif not track_id and str(track.get("statusLabel") or "").strip() in {"-", "–", "—"}:
                state = "missing"
            else:
                state = "healthy"
            observe(video_id, language, state, track_id)

    # Published tracks are not always repeated in root audioTracks. Treat the
    # language row's audioTranslation as evidence too, otherwise a published
    # language looks "missing" and is uploaded again.
    for video_id, items in translations_by_video.items():
        for item in items:
            audio = item.get("audioTranslation") or {}
            if not isinstance(audio, dict) or not audio:
                continue
            track_id = str(audio.get("audioTrackId") or "").strip()
            if track_id in source_track_ids.get(video_id, set()):
                continue
            if track_id and track_id in creator_track_ids.get(video_id, set()):
                continue
            language = update_audio_module._translation_language(item) or ""
            if update_audio_module._audio_translation_has_terminal_failure(item):
                state = "terminal"
            elif update_audio_module._audio_payload_needs_attention(item):
                state = "inflight"
            elif not track_id and str(audio.get("statusLabel") or "").strip() in {"-", "–", "—"}:
                state = "missing"
            else:
                state = "healthy"
            observe(video_id, language, state, track_id)

    if observation_sink is not None:
        observation_sink.clear()
        for video_id, language_states in observations.items():
            observation_sink[video_id] = {}
            for language_key, states in language_states.items():
                track_ids_by_state = observation_track_ids.get(
                    video_id, {}
                ).get(language_key, {})
                observation_sink[video_id][language_key] = {
                    "states": sorted(states),
                    "inflight_track_ids": sorted(
                        track_ids_by_state.get("inflight", set())
                    ),
                    "terminal_track_ids": sorted(
                        track_ids_by_state.get("terminal", set())
                    ),
                    "healthy_track_ids": sorted(
                        track_ids_by_state.get("healthy", set())
                    ),
                }

    terminal_by_video = {
        video_id: {
            str(action.get("language") or "").casefold(): action
            for action in video_actions
        }
        for video_id, video_actions in terminal_targets.items()
    }
    actions: list[dict] = []
    readable_ids = requested - unreadable_ids
    for video_id, entry in requested_entries.items():
        if video_id not in readable_ids or not isinstance(entry, dict):
            continue
        if any("healthy" in states for states in observations.get(video_id, {}).values()):
            logger.info(
                "Audio auto-recovery preserving healthy dubs for video={}; "
                "only timed-out processing tracks may need replacement.",
                video_id,
            )
            continue
        for language in entry.get("languages") or []:
            clean_language = str(language or "").strip()
            if not clean_language:
                continue
            language_key = clean_language.casefold()
            states = observations.get(video_id, {}).get(language_key, set())
            # One healthy copy wins over an old failed duplicate. An in-flight
            # copy must also be allowed to finish without replacement.
            if "healthy" in states or "inflight" in states:
                continue
            terminal = terminal_by_video.get(video_id, {}).get(language_key)
            if terminal is not None:
                logger.warning(
                    "Audio auto-recovery detected terminal track: video={} "
                    "language={} track_ids={}",
                    video_id,
                    clean_language,
                    ",".join(terminal.get("track_ids") or []) or "none",
                )
                actions.append(
                    {
                        "video_id": video_id,
                        "language": clean_language,
                        "track_ids": list(terminal.get("track_ids") or []),
                        "reason": "terminal",
                    }
                )
                continue
            # The response describes this video, neither collection has a
            # healthy dub, and this language has no active/failed track. Add it
            # directly: a dash/empty row has no Track ID to delete.
            if not states or states == {"missing"}:
                logger.info(
                    "Audio auto-recovery detected missing audio: video={} language={}",
                    video_id, clean_language,
                )
                actions.append({
                    "video_id": video_id,
                    "language": clean_language,
                    "track_ids": [],
                    "reason": "missing",
                })

    return actions, unreadable_ids


def _record_processing_observations(
    *,
    channel_id: str,
    requested_entries: dict[str, dict],
    observations: dict,
    observed_at: float,
    stale_after_seconds: float = DEFAULT_STALE_PROCESSING_SECONDS,
) -> list[dict]:
    """Persist in-flight ages and return exact tracks eligible for replacement.

    Replacement is allowed only when the same exact Audio Track ID remains in
    PROCESSING across multiple scans for the full stale window. A healthy dub
    protects its own language and clears that language's timer. Terminal
    evidence or a changed/missing Track ID clears the language's timer.
    This makes the decision survive app restarts without treating one delayed
    Studio response as a failure.
    """
    warnings: list[dict] = []
    threshold = max(0.0, float(stale_after_seconds))
    timestamp = float(observed_at)

    with _STATE_LOCK:
        state = _load_state()
        channel_entries = state.get("entries", {}).get(channel_id, {})
        if not isinstance(channel_entries, dict):
            return []

        changed = False
        for video_id, requested_entry in requested_entries.items():
            entry = channel_entries.get(video_id)
            if not isinstance(entry, dict) or not isinstance(requested_entry, dict):
                continue
            video_observations = observations.get(video_id) or {}
            registered_languages = {
                str(language).strip().casefold(): str(language).strip()
                for language in requested_entry.get("languages") or []
                if str(language or "").strip()
            }
            raw_trackers = entry.get("processing_observations")
            trackers = raw_trackers if isinstance(raw_trackers, dict) else {}
            if raw_trackers is not trackers:
                entry["processing_observations"] = trackers
                changed = True

            for obsolete_key in set(trackers) - set(registered_languages):
                trackers.pop(obsolete_key, None)
                changed = True

            for language_key, display_language in registered_languages.items():
                observed = video_observations.get(language_key) or {}
                states = set(observed.get("states") or [])
                track_ids = sorted(
                    {
                        str(track_id).strip()
                        for track_id in observed.get("inflight_track_ids") or []
                        if str(track_id or "").strip()
                    }
                )

                # Any good copy protects the language. Explicit terminal
                # failures are handled immediately by the normal repair plan.
                if "healthy" in states or "terminal" in states:
                    if language_key in trackers:
                        trackers.pop(language_key, None)
                        changed = True
                    continue

                # Missing/ambiguous response data is never proof of a stuck
                # track. Reset the clock so a later row must prove staleness.
                if "inflight" not in states or not track_ids:
                    if language_key in trackers:
                        trackers.pop(language_key, None)
                        changed = True
                    continue

                previous = trackers.get(language_key)
                if isinstance(previous, dict):
                    previous_ids = sorted(
                        str(track_id).strip()
                        for track_id in previous.get("track_ids") or []
                        if str(track_id or "").strip()
                    )
                else:
                    previous_ids = []
                if previous_ids == track_ids:
                    try:
                        first_seen_at = float(previous.get("first_seen_at"))
                    except (TypeError, ValueError):
                        first_seen_at = timestamp
                    try:
                        scan_count = int(previous.get("scan_count") or 0) + 1
                    except (TypeError, ValueError):
                        scan_count = 2
                else:
                    first_seen_at = timestamp
                    scan_count = 1

                current = {
                    "language": display_language,
                    "track_ids": track_ids,
                    "first_seen_at": first_seen_at,
                    "last_seen_at": timestamp,
                    "scan_count": scan_count,
                }
                if (
                    scan_count >= MIN_STALE_PROCESSING_SCANS
                    and timestamp - first_seen_at >= threshold
                ):
                    already_warned = (
                        isinstance(previous, dict)
                        and previous_ids == track_ids
                        and previous.get("warning_reason") == PROCESSING_WARNING_REASON
                    )
                    current["warning_reason"] = PROCESSING_WARNING_REASON
                    current["warned_at"] = (
                        previous.get("warned_at", timestamp) if already_warned else timestamp
                    )
                    if not already_warned:
                        logger.warning(
                            "Audio processing timeout; scheduling exact tracks for delete/reupload: "
                            "channel={} video={} language={} track_ids={} reason={} age_seconds={:.0f}",
                            channel_id,
                            video_id,
                            display_language,
                            ",".join(track_ids),
                            PROCESSING_WARNING_REASON,
                            timestamp - first_seen_at,
                        )
                    warnings.append(
                        {
                            "channel_id": channel_id,
                            "video_id": video_id,
                            "language": display_language,
                            "track_ids": track_ids,
                            "reason": PROCESSING_WARNING_REASON,
                            "age_seconds": max(0, int(timestamp - first_seen_at)),
                        }
                    )

                if previous != current:
                    trackers[language_key] = current
                    changed = True

            if not trackers and "processing_observations" in entry:
                entry.pop("processing_observations", None)
                changed = True

        if changed:
            state_manager.save_state(RECOVERY_STATE_NAME, state)

    return warnings


def _record_recovery_attempt(
    channel_id: str,
    video_id: str,
    language: str,
    *,
    succeeded: bool,
    message: str,
    attempted_at: float,
) -> None:
    with _STATE_LOCK:
        state = _load_state()
        entry = (
            state.get("entries", {})
            .get(channel_id, {})
            .get(video_id)
        )
        if not isinstance(entry, dict):
            return
        attempts = entry.setdefault("attempts", {})
        attempts[language.casefold()] = {
            "attempted_at": attempted_at,
            "succeeded": bool(succeeded),
            "message": str(message),
        }
        if succeeded:
            entry["last_recovered_at"] = attempted_at
            processing = entry.get("processing_observations")
            if isinstance(processing, dict):
                processing.pop(language.casefold(), None)
                if not processing:
                    entry.pop("processing_observations", None)
        state_manager.save_state(RECOVERY_STATE_NAME, state)


def _save_caption_monitor_state(
    channel_id: str,
    video_id: str,
    *,
    languages: Iterable[str],
    next_check_at: float,
    last_error: str = "",
) -> None:
    with _STATE_LOCK:
        state = _load_state()
        entry = state.get("entries", {}).get(channel_id, {}).get(video_id)
        if not isinstance(entry, dict):
            return
        monitor = entry.get("caption_monitor")
        if not isinstance(monitor, dict):
            return
        clean_languages = list(
            dict.fromkeys(
                str(language or "").strip()
                for language in languages
                if str(language or "").strip()
            )
        )
        if clean_languages:
            monitor["languages"] = clean_languages
            monitor["next_check_at"] = float(next_check_at)
            monitor["last_error"] = str(last_error or "")
        else:
            entry.pop("caption_monitor", None)
        state_manager.save_state(RECOVERY_STATE_NAME, state)


async def _monitor_failed_caption_tracks(
    *,
    channel_id: str,
    entries: dict[str, dict],
    cycle_time: float,
    continue_allowed: Callable[[], bool] | None = None,
    video_continue_allowed: Callable[[str], bool] | None = None,
) -> dict:
    """Verify recently submitted tracks and re-upload only explicit failures."""
    repaired = 0
    failed = 0
    quota_message = ""
    guard = get_audio_mutation_guard(channel_id)
    can_continue = continue_allowed or (lambda: True)
    video_can_continue = video_continue_allowed or (lambda _video_id: True)

    for video_id, entry in entries.items():
        if not can_continue():
            break
        if not video_can_continue(video_id):
            continue
        monitor = entry.get("caption_monitor") or {}
        if not isinstance(monitor, dict):
            continue
        languages = [
            str(language).strip()
            for language in monitor.get("languages") or []
            if str(language or "").strip()
        ]
        if not languages:
            continue
        try:
            next_check_at = float(monitor.get("next_check_at") or 0)
        except (TypeError, ValueError):
            next_check_at = 0
        if next_check_at > cycle_time:
            continue
        quota = get_caption_quota_status(now=cycle_time)
        if quota.get("blocked"):
            quota_message = str(quota.get("message") or "Đã hết quota phụ đề.")
            break

        source_path = Path(str(monitor.get("source_srt_path") or ""))
        source_language = str(monitor.get("source_language") or "").strip()
        if not source_path.is_file() or not source_language:
            failed += len(languages)
            _save_caption_monitor_state(
                channel_id,
                video_id,
                languages=languages,
                next_check_at=cycle_time + CAPTION_STATUS_CHECK_INTERVAL_SECONDS,
                last_error="Không còn file SRT nguồn để sửa phụ đề failed.",
            )
            continue
        if not guard.acquire(blocking=False):
            continue
        try:
            _update_runtime_status(
                phase="captioning",
                message="Đang kiểm tra phụ đề YouTube vừa đăng",
                channel_id=channel_id,
                video_id=video_id,
                language="",
            )
            client = YouTubeCaptionClient(channel_id)
            tracks = await _run_recovery_blocking(client.list_tracks, video_id)
            tracks_by_language = {
                client.track_language(track).casefold(): track
                for track in tracks
                if client.track_language(track)
            }
            remaining: list[str] = []
            failed_languages: list[str] = []
            for language in languages:
                track = tracks_by_language.get(language.casefold())
                # An absent track was never accepted (for example quota ended
                # before insert). It remains a manual-page checkpoint and is
                # deliberately not auto-inserted.
                if track is None:
                    continue
                status = str((track.get("snippet") or {}).get("status") or "")
                if status.casefold() == "serving":
                    continue
                remaining.append(language)
                if status.casefold() == "failed":
                    failed_languages.append(language)

            if failed_languages:
                source_track = tracks_by_language.get(source_language.casefold())
                if source_track is None:
                    raise RuntimeError(
                        "Không tìm thấy phụ đề nguồn trên YouTube để sửa track failed."
                    )
                source_bytes = source_path.read_bytes()
                source_status = str(
                    (source_track.get("snippet") or {}).get("status") or ""
                ).casefold()
                if source_status == "failed":
                    if not can_continue():
                        break
                    if not video_can_continue(video_id):
                        continue
                    await _run_recovery_blocking(
                        client.upsert_track,
                        video_id=video_id,
                        language=source_language,
                        srt_bytes=source_bytes,
                        existing_tracks=tracks,
                        replace_existing=False,
                    )
                    repaired += 1
                    source_status = "syncing"

                for language in failed_languages:
                    if not can_continue():
                        break
                    if not video_can_continue(video_id):
                        break
                    if language.casefold() == source_language.casefold():
                        continue
                    # YouTube cannot reliably translate from a source track
                    # while that source is itself being reprocessed. Keep the
                    # failed target monitored and retry it after the repaired
                    # source reaches ``serving``.
                    if source_status != "serving":
                        continue
                    _update_runtime_status(language=language)
                    translated = await _run_recovery_blocking(
                        client.download_translation,
                        str(source_track.get("id") or ""),
                        language,
                    )
                    if not can_continue() or not video_can_continue(video_id):
                        break
                    await _run_recovery_blocking(
                        client.upsert_track,
                        video_id=video_id,
                        language=language,
                        srt_bytes=translated,
                        existing_tracks=tracks,
                        replace_existing=False,
                    )
                    repaired += 1

            _save_caption_monitor_state(
                channel_id,
                video_id,
                languages=remaining,
                next_check_at=cycle_time + (
                    CAPTION_REPAIR_VERIFY_SECONDS
                    if failed_languages
                    else CAPTION_STATUS_CHECK_INTERVAL_SECONDS
                ),
            )
        except CaptionQuotaExceededError as exc:
            quota_message = str(exc)
        except Exception as exc:
            failed += 1
            logger.error(
                "Caption status monitor failed: channel={} video={} error={}",
                channel_id,
                video_id,
                exc,
            )
            _save_caption_monitor_state(
                channel_id,
                video_id,
                languages=languages,
                next_check_at=cycle_time + CAPTION_STATUS_CHECK_INTERVAL_SECONDS,
                last_error=str(exc),
            )
            if isinstance(exc, CaptionAuthenticationError):
                break
        finally:
            guard.release()
        if quota_message:
            break

    return {
        "repaired": repaired,
        "failed": failed,
        "quota_message": quota_message,
    }


def _registered_language_count(video_entries: dict[str, dict]) -> int:
    return sum(
        len(entry.get("languages") or [])
        for entry in video_entries.values()
        if isinstance(entry, dict)
    )


def _recovery_channel_error(error: BaseException) -> str:
    message = str(error)
    if any(marker in message.casefold() for marker in (
        "nameresolutionerror", "getaddrinfo failed", "failed to resolve",
    )):
        return "Lỗi DNS: không phân giải được địa chỉ YouTube; chưa kiểm tra được video"
    if _requires_channel_refresh(error):
        return "YouTube không cấp token xác thực; cần đăng nhập và tải lại đúng kênh"
    return _REFRESH_ALERT_SECRET_RE.sub("[redacted]", message)[:400]


def _summarize_channel_result(result: dict) -> None:
    parts = []
    if result["scanned_videos"]:
        parts.append(f"Đã đọc audio {result['scanned_videos']} video")
    if result["submitted"]:
        parts.append(f"Đã gửi {result['submitted']} audio, chờ YouTube xử lý")
    if result["healthy_skipped"]:
        parts.append(f"Bỏ qua {result['healthy_skipped']} video còn audio tốt")
    if result["processing_tracks"]:
        parts.append(f"Còn {result['processing_tracks']} track đang xử lý, chưa thay lại")
    if result.get("reason"):
        parts.append(result["reason"])
    if result.get("last_error"):
        parts.append(result["last_error"])
    result["outcome"] = (
        "error" if result["errors"] else
        "deferred" if result.get("reason") else
        "submitted" if result["submitted"] else "scanned"
    )
    result["message"] = " · ".join(parts) or "Đã kết thúc lượt; không có audio cần gửi lại"


async def _schedule_recovery_channels(
    process_channel: Callable,
    initial_entries: dict,
    channel_results: dict,
    *,
    stop_event: asyncio.Event,
    should_stop: Callable[[], bool],
    on_complete: Callable[[], None],
) -> None:
    """Reuse idle slots unless a queue requires finishing the entire round."""
    pending = deque(initial_entries)
    repeats: deque[str] = deque()
    started: set[str] = set()
    running: dict[asyncio.Task, str] = {}
    retry_at: dict[str, float] = {}
    queued_round = len(pending) > MAX_CONCURRENT_RECOVERY_CHANNELS
    last_slot_snapshot: tuple[tuple[str, ...], tuple[str, ...]] | None = None
    try:
        while not should_stop():
            latest = get_audio_recovery_state()
            eligible = {
                channel_id: entries
                for channel_id, entries in (latest.get("entries") or {}).items()
                if latest.get("enabled", True) and isinstance(entries, dict)
                and _channel_is_in_recovery_scope(latest, channel_id)
            }
            active_ids = set(running.values())
            started.intersection_update(set(eligible) | active_ids)
            pending = deque(channel for channel in pending if channel in eligible and channel not in active_ids)
            repeats = deque(channel for channel in repeats if channel in eligible and channel not in active_ids)
            known = started | active_ids | set(pending)
            newcomers = [channel for channel in eligible if channel not in known]
            pending.extend(newcomers)
            if (newcomers and started) or (pending and repeats):
                queued_round = True
            if queued_round:
                repeats.clear()

            def launch(channel_id: str) -> None:
                index = list(eligible).index(channel_id) + 1
                task = asyncio.create_task(process_channel(
                    index, channel_id, eligible[channel_id], current_state=latest,
                    current_total=len(eligible),
                ))
                running[task] = channel_id
                started.add(channel_id)

            while pending and len(running) < MAX_CONCURRENT_RECOVERY_CHANNELS:
                launch(pending.popleft())
            if pending:
                queued_round = True
                repeats.clear()
            if not queued_round:
                for _ in range(len(repeats)):
                    channel_id = repeats.popleft()
                    if len(running) < MAX_CONCURRENT_RECOVERY_CHANNELS and time.monotonic() >= retry_at.get(channel_id, 0):
                        launch(channel_id)
                    else:
                        repeats.append(channel_id)

            slot_snapshot = (tuple(sorted(running.values())), tuple(pending))
            if slot_snapshot != last_slot_snapshot:
                logger.info(
                    "Audio auto-recovery slots: active={}/{} channels={} waiting={} waiting_channels={}",
                    len(running), MAX_CONCURRENT_RECOVERY_CHANNELS,
                    ",".join(slot_snapshot[0]) or "none", len(pending),
                    ",".join(pending) or "none",
                )
                last_slot_snapshot = slot_snapshot

            preferences = _scan_preferences_from_state(latest)
            _update_runtime_status(
                channel_total=len(set(eligible) | set(running.values())),
                waiting_channel_count=len(pending),
                scan_mode=preferences["scan_mode"],
                video_scan_scope=preferences["video_scan_scope"],
                selected_channel_ids=preferences["selected_channel_ids"],
            )
            if not running:
                if queued_round or not eligible:
                    return
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=MONITOR_IDLE_POLL_SECONDS)
                except asyncio.TimeoutError:
                    pass
                continue

            done, _ = await asyncio.wait(
                running, timeout=MONITOR_IDLE_POLL_SECONDS,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                channel_id = running.pop(task)
                task.result()
                report = channel_results.get(channel_id) or {}
                if report.get("submitted") or report.get("errors") or report.get("reason"):
                    logger.info(
                        "Audio auto-recovery channel pass finished: channel={} submitted={} errors={} active_other_channels={}",
                        channel_id, report.get("submitted", 0), report.get("errors", 0), len(running),
                    )
                if not queued_round:
                    repeats.append(channel_id)
                    retry_at[channel_id] = time.monotonic() + (
                        MONITOR_IDLE_POLL_SECONDS
                        if report.get("errors") or not report.get("scan_performed") else 0
                    )
                on_complete()
            if queued_round and not pending and not running:
                return
            await asyncio.sleep(0)
    finally:
        # Current uploads own their locks/files until their threads return.
        if running:
            await asyncio.gather(*running)


async def run_audio_recovery_cycle(
    *, now: float | None = None, stop_event: asyncio.Event | None = None,
) -> dict:
    """Scan once, or reuse free channel slots until a queued round finishes."""
    cycle_time = float(now if now is not None else time.time())
    with _RUNTIME_STATUS_LOCK:
        cycle_id = int(_RUNTIME_STATUS.get("cycle_id") or 0) + 1
    final_message = "Đã hoàn tất vòng quét tự động"
    repaired = 0
    failed = 0
    captions_repaired = 0
    captions_failed = 0
    caption_quota_message = ""
    caption_quota_by_channel: dict[str, str] = {}
    unreadable_by_channel: dict[str, set[str]] = {}
    scanned_channels = 0
    warnings_by_channel: dict[str, list[dict]] = {}
    channel_results: dict[str, dict] = {}
    deferred_busy = 0
    deferred_initial_grace = 0
    deferred_video_scope = 0
    deferred_visibility_unknown = 0
    scope_skipped_channel_ids: set[str] = set()
    cancelled_by_clear = False
    worker_pool: ThreadPoolExecutor | None = None
    _update_runtime_status(
        active=True,
        phase="scanning",
        message="Đang tự động quét trạng thái audio...",
        cycle_id=cycle_id,
        cycle_started_at=cycle_time,
        channel_index=0,
        channel_total=0,
        channel_concurrency=MAX_CONCURRENT_RECOVERY_CHANNELS,
        completed_channel_count=0,
        completed_pass_count=0,
        waiting_channel_count=0,
        continuous=stop_event is not None,
        _channel_passes={},
        _channel_jobs={},
        _channel_results={},
        channel_id="",
        video_id="",
        language="",
        repair_index=0,
        repair_total=0,
        repaired=0,
        failed=0,
        processing_warning_count=0,
        captions_repaired=0,
        captions_failed=0,
        caption_quota_message="",
        deferred_video_scope=0,
        deferred_visibility_unknown=0,
        scan_mode=RECOVERY_SCAN_MODE_ALL,
        video_scan_scope=RECOVERY_VIDEO_SCOPE_PUBLIC,
        selected_channel_ids=[],
        _upload_progress=None,
    )
    with _STATE_LOCK:
        cycle_generation = _RECOVERY_CLEAR_GENERATION
    try:
        state = get_audio_recovery_state()
        if not state.get("enabled", True):
            final_message = "Tự động khôi phục audio đang tắt"
            return {"skipped": "disabled", "repaired": 0, "failed": 0}
        all_entries_by_channel = state.get("entries") or {}
        scan_preferences = _scan_preferences_from_state(state)
        selected_channel_ids = set(scan_preferences["selected_channel_ids"])
        entries_by_channel = {
            channel_id: video_entries
            for channel_id, video_entries in all_entries_by_channel.items()
            if _channel_is_in_recovery_scope(state, channel_id)
        }
        scope_skipped_channel_ids.update(
            set(all_entries_by_channel) - set(entries_by_channel)
        )
        _update_runtime_status(
            scan_mode=scan_preferences["scan_mode"],
            video_scan_scope=scan_preferences["video_scan_scope"],
            selected_channel_ids=sorted(selected_channel_ids),
        )
        try:
            stale_processing_seconds = max(
                0.0,
                float(
                    state.get(
                        "stale_processing_seconds",
                        DEFAULT_STALE_PROCESSING_SECONDS,
                    )
                ),
            )
        except (TypeError, ValueError):
            stale_processing_seconds = DEFAULT_STALE_PROCESSING_SECONDS
        if not all_entries_by_channel:
            final_message = "Chưa có video được đăng ký tự động khôi phục"
            return {"skipped": "empty", "repaired": 0, "failed": 0}
        if not entries_by_channel:
            final_message = "Danh sách kênh tự động quét chưa có kênh phù hợp"
            return {
                "skipped": "no_selected_channels",
                "repaired": 0,
                "failed": 0,
                "scan_mode": scan_preferences["scan_mode"],
                "scope_skipped_channel_ids": sorted(scope_skipped_channel_ids),
            }

        channel_total = len(entries_by_channel)
        _update_runtime_status(
            channel_total=channel_total,
            message=f"Đang tự động quét {channel_total} kênh...",
        )
        logger.info("Audio auto-recovery scan started for {} channel(s).", len(entries_by_channel))
        worker_pool = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT_RECOVERY_CHANNELS,
            thread_name_prefix="audio-recovery",
        )
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_RECOVERY_CHANNELS)
        cycle_cancelled = False

        def should_stop() -> bool:
            nonlocal cancelled_by_clear
            cancelled_by_clear = cancelled_by_clear or _recovery_was_cleared(cycle_generation)
            return (
                cycle_cancelled or cancelled_by_clear
                or (stop_event is not None and stop_event.is_set())
            )

        async def process_channel(
            channel_index: int, channel_id: str, video_entries: dict,
            *, current_state: dict | None = None, current_total: int | None = None,
        ) -> None:
            nonlocal repaired, failed, captions_repaired, captions_failed
            nonlocal caption_quota_message, scanned_channels, deferred_busy
            nonlocal deferred_video_scope, deferred_visibility_unknown
            async with semaphore:
                if should_stop():
                    return
                context_token = _RUNTIME_CHANNEL_CONTEXT.set((cycle_id, channel_id))
                pool_token = _RECOVERY_WORKER_POOL.set(worker_pool)
                cycle_time = float(now if now is not None else time.time())
                channel_total = current_total if current_total is not None else len(entries_by_channel)
                pass_state = current_state if current_state is not None else state
                scan_preferences = _scan_preferences_from_state(pass_state)
                refresh_alerts = pass_state.get("channel_refresh_alerts") or {}
                unreadable = unreadable_by_channel[channel_id] = set()
                processing_warnings = warnings_by_channel[channel_id] = []
                owned_mutation_guard: threading.Lock | None = None
                channel_result = {
                    "channel_id": channel_id, "scanned_videos": 0,
                    "submitted": 0, "errors": 0, "healthy_skipped": 0,
                    "cooldown_tracks": 0, "processing_tracks": 0,
                    "scan_performed": False,
                }
                try:
                    _update_runtime_status(
                        phase="scanning",
                        message=f"Đang tự động quét kênh {channel_index}/{channel_total}",
                        channel_index=channel_index,
                        channel_total=channel_total,
                        channel_id=channel_id,
                        video_id="",
                        language="",
                        repair_index=0,
                        repair_total=0,
                        _upload_progress=None,
                    )
                    if should_stop():
                        channel_result["reason"] = "Lượt quét đã bị dừng"
                        return
                    if not is_audio_recovery_channel_enabled(channel_id):
                        channel_result["reason"] = "Kênh đã Deactive hoặc nằm ngoài phạm vi quét"
                        scope_skipped_channel_ids.add(channel_id)
                        logger.info(
                            "Audio auto-recovery skipped deselected channel={}",
                            channel_id,
                        )
                        return
                    if not isinstance(video_entries, dict):
                        channel_result["reason"] = "Danh sách video đăng ký không hợp lệ"
                        return
                    if channel_id in refresh_alerts:
                        channel_result["reason"] = "Tạm dừng: cần đăng nhập và tải lại thông tin kênh"
                        logger.info(
                            "Audio auto-recovery paused for channel={}: waiting for full channel refresh.",
                            channel_id,
                        )
                        return
                    active_entries = {
                        video_id: video_entries[video_id]
                        for video_id in _enabled_recovery_video_ids(channel_id, video_entries)
                    }
                    eligible_entries = {
                        video_id: entry
                        for video_id, entry in active_entries.items()
                        if isinstance(entry, dict)
                    }
                    if not eligible_entries:
                        channel_result["reason"] = "Không có video Active để quét"
                        return

                    # The normal/manual flow owns this guard for its entire channel
                    # batch. Do not even scan YouTube while it is active; defer this
                    # channel to keep recovery traffic and state decisions isolated.
                    channel_mutation_guard = get_audio_mutation_guard(channel_id)
                    if channel_mutation_guard.locked():
                        channel_result["reason"] = "Tạm hoãn: kênh đang chạy tác vụ audio khác"
                        deferred_busy += _registered_language_count(eligible_entries)
                        logger.info(
                            "Audio auto-recovery deferred for channel={}: "
                            "manual audio flow has priority.",
                            channel_id,
                        )
                        return

                    video_ids = list(eligible_entries)
                    channel_requires_refresh = False
                    try:
                        (
                            matches_by_video_id,
                            unresolved_video_ids,
                        ) = await _run_recovery_blocking(
                            _get_registered_video_scan_statuses,
                            channel_id,
                            video_ids,
                            video_scan_scope=scan_preferences["video_scan_scope"],
                            **({"scan_start_date": scan_preferences["scan_start_date"],
                                "scan_date_type": scan_preferences["scan_date_type"]}
                               if scan_preferences["scan_start_date"] else {}),
                        )
                        scanned_channels += 1
                    except Exception as exc:
                        channel_result["errors"] += len(video_ids)
                        channel_result["last_error"] = _recovery_channel_error(exc)
                        failed += len(video_ids)
                        unreadable.update(video_ids)
                        if _requires_channel_refresh(exc):
                            mark_channel_refresh_required(channel_id, exc, now=cycle_time)
                            channel_requires_refresh = True
                        logger.error(
                            "Audio auto-recovery could not check video visibility: "
                            "channel={} videos={} error={}",
                            channel_id,
                            ",".join(video_ids),
                            exc,
                        )
                        return

                    channel_result["scan_performed"] = True
                    matching_video_ids = _enabled_recovery_video_ids(channel_id, [
                        video_id
                        for video_id in video_ids
                        if matches_by_video_id.get(video_id) is True
                    ])
                    outside_video_scope = [
                        video_id
                        for video_id in video_ids
                        if matches_by_video_id.get(video_id) is False
                    ]
                    deferred_video_scope += len(outside_video_scope)
                    deferred_visibility_unknown += len(unresolved_video_ids)
                    if outside_video_scope or unresolved_video_ids:
                        logger.info(
                            "Audio auto-recovery deferred videos: channel={} "
                            "outside_video_scope={} visibility_unresolved={}",
                            channel_id,
                            len(outside_video_scope),
                            len(unresolved_video_ids),
                        )
                    if not matching_video_ids:
                        channel_result["reason"] = (
                            "Chưa đọc được trạng thái công khai/lên lịch"
                            if unresolved_video_ids else
                            "Không có video đăng ký phù hợp loại video/ngày quét đã chọn"
                        )
                        return

                    if not is_audio_recovery_channel_enabled(channel_id):
                        scope_skipped_channel_ids.add(channel_id)
                        return

                    eligible_entries = {
                        video_id: eligible_entries[video_id]
                        for video_id in matching_video_ids
                    }
                    video_ids = matching_video_ids

                    # Caption recovery is intentionally narrower than audio recovery:
                    # only recently submitted tracks are monitored, and only an
                    # explicit YouTube ``failed`` status is updated. Missing tracks are
                    # never inserted here. This runs after the visibility filter so a
                    # draft or unscheduled private video cannot consume caption quota.
                    caption_result = await _monitor_failed_caption_tracks(
                        channel_id=channel_id,
                        entries=eligible_entries,
                        cycle_time=cycle_time,
                        continue_allowed=lambda channel_id=channel_id: (
                            not should_stop() and is_audio_recovery_channel_enabled(channel_id)
                        ),
                        video_continue_allowed=lambda video_id, channel_id=channel_id: (
                            is_audio_recovery_video_enabled(channel_id, video_id)
                        ),
                    )
                    captions_repaired += int(caption_result.get("repaired") or 0)
                    captions_failed += int(caption_result.get("failed") or 0)
                    caption_quota_by_channel[channel_id] = str(caption_result.get("quota_message") or "")
                    caption_quota_message = next(
                        (message for message in caption_quota_by_channel.values() if message), ""
                    )
                    _update_runtime_status(
                        captions_repaired=captions_repaired,
                        captions_failed=captions_failed,
                        caption_quota_message=caption_quota_message,
                    )

                    _update_runtime_status(
                        phase="scanning",
                        message=f"Đang quét audio kênh {channel_index}/{channel_total}",
                        video_id="",
                        language="",
                        _upload_progress=None,
                    )
                    batch_size = update_audio_module._TRANSLATION_BATCH_SIZE
                    channel_actions: list[dict] = []
                    for start in range(0, len(video_ids), batch_size):
                        if should_stop():
                            break
                        if not is_audio_recovery_channel_enabled(channel_id):
                            scope_skipped_channel_ids.add(channel_id)
                            break
                        chunk = _enabled_recovery_video_ids(
                            channel_id, video_ids[start : start + batch_size]
                        )
                        if not chunk:
                            continue
                        try:
                            payload = await _run_recovery_blocking(
                                update_audio_module._get_video_translation_payload,
                                chunk,
                                channel_id,
                            )
                        except Exception as exc:
                            channel_result["errors"] += len(chunk)
                            channel_result["last_error"] = _recovery_channel_error(exc)
                            failed += len(chunk)
                            unreadable.update(chunk)
                            if _requires_channel_refresh(exc):
                                mark_channel_refresh_required(channel_id, exc, now=cycle_time)
                                channel_requires_refresh = True
                            logger.error(
                                "Audio auto-recovery could not scan channel={} videos={}: {}",
                                channel_id,
                                ",".join(chunk),
                                exc,
                            )
                            if channel_requires_refresh:
                                break
                            continue
                        processing_observations: dict = {}
                        chunk_entries = {
                            video_id: eligible_entries[video_id] for video_id in chunk
                        }
                        actions, unreadable_chunk = build_audio_recovery_plan(
                            payload,
                            chunk_entries,
                            chunk,
                            observation_sink=processing_observations,
                        )
                        channel_result["scanned_videos"] += len(chunk) - len(unreadable_chunk)
                        if unreadable_chunk:
                            channel_result["errors"] += len(unreadable_chunk)
                            channel_result["last_error"] = "YouTube chưa trả đủ dữ liệu audio để kiểm tra video"
                        channel_result["processing_tracks"] += sum(
                            "inflight" in observed.get("states", [])
                            for languages in processing_observations.values()
                            for observed in languages.values()
                        )
                        stale_actions = _record_processing_observations(
                            channel_id=channel_id,
                            requested_entries=chunk_entries,
                            observations={
                                video_id: languages
                                for video_id, languages in processing_observations.items()
                                if video_id not in unreadable_chunk
                            },
                            observed_at=float(now if now is not None else time.time()),
                            stale_after_seconds=stale_processing_seconds,
                        )
                        processing_warnings.extend(stale_actions)
                        actions.extend(stale_actions)
                        action_video_ids = {action["video_id"] for action in actions}
                        channel_result["healthy_skipped"] += sum(
                            any("healthy" in observed.get("states", []) for observed in languages.values())
                            for video_id, languages in processing_observations.items()
                            if video_id not in action_video_ids
                        )
                        _update_runtime_status(
                            processing_warning_count=sum(len(warnings) for warnings in warnings_by_channel.values())
                        )
                        channel_actions.extend(actions)
                        unreadable.update(unreadable_chunk)

                    if should_stop():
                        return
                    if channel_requires_refresh:
                        return

                    actions_by_video: dict[str, list[dict]] = {}
                    for action in channel_actions:
                        actions_by_video.setdefault(action["video_id"], []).append(action)

                    for video_id, actions in actions_by_video.items():
                        if should_stop():
                            break
                        if not is_audio_recovery_channel_enabled(channel_id):
                            scope_skipped_channel_ids.add(channel_id)
                            break
                        if not is_audio_recovery_video_enabled(channel_id, video_id):
                            continue
                        entry = eligible_entries.get(video_id) or {}
                        channel_mutation_guard = get_audio_mutation_guard(channel_id)
                        if channel_mutation_guard.locked():
                            channel_result["reason"] = "Tạm hoãn: kênh đang chạy tác vụ audio khác"
                            deferred_busy += len(actions)
                            logger.info(
                                "Audio auto-recovery deferred for channel={} video={}: "
                                "another audio mutation has priority.",
                                channel_id,
                                video_id,
                            )
                            continue
                        audio_path = Path(str(entry.get("audio_path") or ""))
                        if not audio_path.is_file():
                            channel_result["errors"] += len(actions)
                            channel_result["last_error"] = "Không tìm thấy file audio nguồn để tải lại"
                            message = f"Không còn file audio: {audio_path}"
                            logger.error(
                                "Audio auto-recovery skipped channel={} video={}: {}",
                                channel_id,
                                video_id,
                                message,
                            )
                            for action in actions:
                                failed += 1
                                _record_recovery_attempt(
                                    channel_id,
                                    video_id,
                                    action["language"],
                                    succeeded=False,
                                    message=message,
                                    attempted_at=cycle_time,
                                )
                            continue

                        temp_audio_path: Path | None = None
                        preparation_stage = "metadata"
                        preparation_started = time.monotonic()
                        try:
                            _update_runtime_status(
                                phase="preparing",
                                message="Đang đọc thời lượng video từ YouTube",
                                preparation_stage=preparation_stage,
                                preparation_started_at=time.time(),
                                _preparation_output_path=None,
                                channel_id=channel_id,
                                video_id=video_id,
                                language="",
                                repair_index=0,
                                repair_total=len(actions),
                                _upload_progress=None,
                            )
                            logger.info(
                                "Audio auto-recovery preparation started: channel={} video={} stage=metadata",
                                channel_id, video_id,
                            )
                            video_info = await _run_recovery_blocking(
                                update_audio_module._get_video_info,
                                video_id=video_id,
                                channel_id=channel_id,
                            )
                            duration_seconds = (
                                video_info.duration_ms / 1000.0
                                if video_info.duration_ms > 0
                                else None
                            )
                            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                                temp_audio_path = Path(temp_file.name)
                            preparation_stage = "rendering"
                            _update_runtime_status(
                                message="Đang tạo file MP3 cho video",
                                preparation_stage=preparation_stage,
                                _preparation_output_path=str(temp_audio_path),
                            )
                            logger.info(
                                "Audio auto-recovery preparation stage: channel={} video={} stage=rendering "
                                "metadata_seconds={:.1f}",
                                channel_id, video_id, time.monotonic() - preparation_started,
                            )
                            await _run_recovery_blocking(
                                multiply_audio,
                                input_file=normalize_path(str(audio_path)),
                                output_file=str(temp_audio_path),
                                times=max(1, int(entry.get("repeat_times") or 1)),
                                extra_minutes=max(0.0, float(entry.get("extra_minutes") or 0)),
                                video_duration_seconds=duration_seconds,
                            )
                            logger.info(
                                "Audio auto-recovery preparation finished: channel={} video={} elapsed_seconds={:.1f}",
                                channel_id, video_id, time.monotonic() - preparation_started,
                            )

                            for action_index, action in enumerate(actions):
                                if should_stop():
                                    break
                                if not is_audio_recovery_channel_enabled(channel_id):
                                    scope_skipped_channel_ids.add(channel_id)
                                    logger.info(
                                        "Audio auto-recovery stopped scheduling new tracks "
                                        "for deselected channel={}",
                                        channel_id,
                                    )
                                    break
                                if not is_audio_recovery_video_enabled(channel_id, video_id):
                                    break
                                language = action["language"]
                                if not channel_mutation_guard.acquire(blocking=False):
                                    channel_result["reason"] = "Tạm hoãn: kênh đang chạy tác vụ audio khác"
                                    deferred_busy += len(actions) - action_index
                                    logger.info(
                                        "Audio auto-recovery deferred for channel={}: "
                                        "another audio mutation has priority.",
                                        channel_id,
                                    )
                                    break
                                owned_mutation_guard = channel_mutation_guard
                                try:
                                    if action["reason"] == PROCESSING_WARNING_REASON:
                                        # MP3 preparation can take minutes. Re-read under
                                        # the channel guard before deleting a timed-out track.
                                        fresh_payload = await _run_recovery_blocking(
                                            update_audio_module._get_video_translation_payload,
                                            [video_id], channel_id,
                                        )
                                        fresh_observations: dict = {}
                                        _, fresh_unreadable = build_audio_recovery_plan(
                                            fresh_payload, {video_id: entry}, [video_id],
                                            observation_sink=fresh_observations,
                                        )
                                        if video_id in fresh_unreadable:
                                            _record_processing_observations(
                                                channel_id=channel_id,
                                                requested_entries={video_id: entry}, observations={},
                                                observed_at=float(now if now is not None else time.time()),
                                                stale_after_seconds=stale_processing_seconds,
                                            )
                                            raise RuntimeError("Chưa đọc được trạng thái audio trước khi xóa track quá 2 giờ")
                                        fresh_language = fresh_observations.get(video_id, {}).get(language.casefold(), {})
                                        current_ids = set(fresh_language.get("inflight_track_ids") or [])
                                        if (
                                            "healthy" in (fresh_language.get("states") or [])
                                            or current_ids != set(action["track_ids"])
                                        ):
                                            _record_processing_observations(
                                                channel_id=channel_id,
                                                requested_entries={video_id: entry}, observations=fresh_observations,
                                                observed_at=float(now if now is not None else time.time()),
                                                stale_after_seconds=stale_processing_seconds,
                                            )
                                            logger.info(
                                                "Audio timeout repair skipped after fresh check: channel={} video={} language={}",
                                                channel_id, video_id, language,
                                            )
                                            continue
                                    if should_stop() or not is_audio_recovery_video_enabled(channel_id, video_id):
                                        break
                                    upload_progress = {
                                        "sent": 0,
                                        "total": temp_audio_path.stat().st_size,
                                        "status": "deleting" if action["track_ids"] else "starting",
                                    }
                                    _update_runtime_status(
                                        phase="uploading",
                                        message=(
                                            "Đang tự động add lại audio "
                                            f"{action_index + 1}/{len(actions)}"
                                        ),
                                        channel_id=channel_id,
                                        video_id=video_id,
                                        language=language,
                                        repair_index=action_index + 1,
                                        repair_total=len(actions),
                                        repaired=repaired,
                                        failed=failed,
                                        _upload_progress=upload_progress,
                                    )
                                    logger.info(
                                        "Audio auto-recovery upload starting: channel={} video={} "
                                        "language={} reason={} failed_track_ids={}",
                                        channel_id,
                                        video_id,
                                        language,
                                        action["reason"],
                                        ",".join(action["track_ids"]) or "none",
                                    )
                                    if action["track_ids"]:
                                        await call_audio_update_with_retry(
                                            lambda action=action: update_audio_module.delete_track_ids(
                                                video_id,
                                                channel_id,
                                                action["track_ids"],
                                            ),
                                            run_blocking=_run_recovery_blocking,
                                        )
                                    await call_audio_update_with_retry(
                                        lambda language=language: update_audio_module.add(
                                            id_video=video_id,
                                            channel_id=channel_id,
                                            file_name=str(temp_audio_path),
                                            language=language,
                                            data=None,
                                            progress=upload_progress,
                                        ),
                                        run_blocking=_run_recovery_blocking,
                                    )
                                    repaired += 1
                                    channel_result["submitted"] += 1
                                    if action["reason"] == PROCESSING_WARNING_REASON:
                                        channel_result["processing_tracks"] = max(0, channel_result["processing_tracks"] - 1)
                                    _update_runtime_status(repaired=repaired)
                                    _record_recovery_attempt(
                                        channel_id,
                                        video_id,
                                        language,
                                        succeeded=True,
                                        message=action["reason"],
                                        attempted_at=cycle_time,
                                    )
                                    logger.info(
                                        "Audio auto-recovery upload submitted: channel={} video={} "
                                        "language={} reason={} (YouTube processing will be checked in a later cycle)",
                                        channel_id,
                                        video_id,
                                        language,
                                        action["reason"],
                                    )
                                except Exception as exc:
                                    channel_result["errors"] += 1
                                    channel_result["last_error"] = _recovery_channel_error(exc)
                                    failed += 1
                                    _update_runtime_status(failed=failed)
                                    if _requires_channel_refresh(exc):
                                        mark_channel_refresh_required(
                                            channel_id, exc, now=cycle_time
                                        )
                                        channel_requires_refresh = True
                                    _record_recovery_attempt(
                                        channel_id,
                                        video_id,
                                        language,
                                        succeeded=False,
                                        message=str(exc),
                                        attempted_at=cycle_time,
                                    )
                                    logger.error(
                                        "Audio auto-recovery failed: channel={} video={} language={} error={}",
                                        channel_id,
                                        video_id,
                                        language,
                                        exc,
                                    )
                                    if channel_requires_refresh:
                                        break
                                finally:
                                    channel_mutation_guard.release()
                                    owned_mutation_guard = None
                        except Exception as exc:
                            channel_result["errors"] += len(actions)
                            channel_result["last_error"] = _recovery_channel_error(exc)
                            if _requires_channel_refresh(exc):
                                mark_channel_refresh_required(channel_id, exc, now=cycle_time)
                                channel_requires_refresh = True
                            logger.error(
                                "Audio auto-recovery preparation failed: channel={} video={} stage={} error={}",
                                channel_id,
                                video_id,
                                preparation_stage,
                                exc,
                            )
                            for action in actions:
                                failed += 1
                                _record_recovery_attempt(
                                    channel_id,
                                    video_id,
                                    action["language"],
                                    succeeded=False,
                                    message=str(exc),
                                    attempted_at=cycle_time,
                                )
                        finally:
                            if temp_audio_path is not None:
                                try:
                                    temp_audio_path.unlink(missing_ok=True)
                                except OSError as exc:
                                    logger.warning("Could not remove recovery temp file {}: {}", temp_audio_path, exc)
                        if channel_requires_refresh:
                            break
                        if should_stop():
                            break

                    if should_stop():
                        return
                except Exception as exc:
                    affected_videos = list(video_entries) if isinstance(video_entries, dict) else []
                    channel_result["errors"] += max(1, len(affected_videos))
                    channel_result["last_error"] = _recovery_channel_error(exc)
                    failed += max(1, len(affected_videos))
                    unreadable.update(affected_videos)
                    logger.exception("Audio auto-recovery channel failed: channel={} error={}", channel_id, exc)
                finally:
                    if owned_mutation_guard is not None:
                        owned_mutation_guard.release()
                    if should_stop():
                        channel_result["reason"] = "Đã dừng lượt quét"
                    _summarize_channel_result(channel_result)
                    channel_results[channel_id] = channel_result
                    _finish_channel_runtime_status(cycle_id, channel_id, channel_result)
                    _RECOVERY_WORKER_POOL.reset(pool_token)
                    _RUNTIME_CHANNEL_CONTEXT.reset(context_token)

        def save_cycle_result() -> dict:
            with _STATE_LOCK:
                latest = _load_state()
                preferences = _scan_preferences_from_state(latest)
                result = {
                    "repaired": repaired,
                    "failed": failed,
                    "processing_warnings": [
                        warning for warnings in warnings_by_channel.values() for warning in warnings
                    ],
                    "captions_repaired": captions_repaired,
                    "captions_failed": captions_failed,
                    "caption_quota_message": caption_quota_message,
                    "unreadable": sorted(set().union(*unreadable_by_channel.values())),
                    "scanned_channels": scanned_channels,
                    "channel_results": list(channel_results.values()),
                    "reauth_required": sorted(get_channel_refresh_alerts()),
                    "deferred_busy": deferred_busy,
                    "deferred_initial_grace": deferred_initial_grace,
                    "deferred_video_scope": deferred_video_scope,
                    "deferred_visibility_unknown": deferred_visibility_unknown,
                    "cancelled_by_clear": cancelled_by_clear,
                    "scan_mode": preferences["scan_mode"],
                    "video_scan_scope": preferences["video_scan_scope"],
                    "scan_start_date": preferences["scan_start_date"],
                    "scan_date_type": preferences["scan_date_type"],
                    "scope_skipped_channel_ids": sorted(scope_skipped_channel_ids),
                }
                latest["last_cycle_at"] = float(now if now is not None else time.time())
                latest["last_cycle_result"] = result
                state_manager.save_state(RECOVERY_STATE_NAME, latest)
                return result

        if stop_event is None:
            channel_group = asyncio.gather(*[
                asyncio.create_task(process_channel(index, channel_id, video_entries))
                for index, (channel_id, video_entries) in enumerate(entries_by_channel.items(), 1)
            ])
        else:
            channel_group = asyncio.create_task(_schedule_recovery_channels(
                process_channel, entries_by_channel, channel_results,
                stop_event=stop_event, should_stop=should_stop,
                on_complete=save_cycle_result,
            ))
        try:
            await asyncio.shield(channel_group)
        except asyncio.CancelledError:
            # Blocking uploads keep running in their threads. Let the current
            # operation finish with its guard and temp file intact, and prevent
            # queued channels or subsequent tracks from starting.
            cycle_cancelled = True
            await channel_group
            save_cycle_result()
            raise

        result = save_cycle_result()
        logger.info(
            "Auto-recovery scan finished: audio_repaired={} audio_failed={} "
            "captions_repaired={} captions_failed={} unreadable={} processing_warnings={}.",
            repaired,
            failed,
            captions_repaired,
            captions_failed,
            len(result["unreadable"]),
            len(result["processing_warnings"]),
        )
        final_message = (
            f"Quét xong: đã gửi lại {repaired}, hoãn "
            f"{deferred_video_scope} video ngoài loại đã chọn, "
            f"{deferred_visibility_unknown} video chưa đọc được trạng thái, "
            f"lỗi {failed}; phụ đề failed đã sửa "
            f"{captions_repaired}, lỗi {captions_failed}; "
            f"{len(result['processing_warnings'])} audio xử lý quá 2 giờ được phát hiện để thay lại"
        )
        return result
    except asyncio.CancelledError:
        final_message = "Đã dừng tự động quét audio"
        raise
    except Exception:
        final_message = "Vòng quét tự động gặp lỗi"
        raise
    finally:
        if worker_pool is not None:
            worker_pool.shutdown(wait=False, cancel_futures=True)
        with _RUNTIME_STATUS_LOCK:
            if _RUNTIME_STATUS.get("cycle_id") == cycle_id:
                _RUNTIME_STATUS.update(
                    active=False,
                    phase="idle",
                    _channel_jobs={},
                    message=final_message,
                    last_cycle_finished_at=time.time(),
                    video_id="",
                    language="",
                    repair_index=0,
                    repair_total=0,
                    repaired=repaired,
                    failed=failed,
                    processing_warning_count=sum(len(warnings) for warnings in warnings_by_channel.values()),
                    captions_repaired=captions_repaired,
                    captions_failed=captions_failed,
                    caption_quota_message=caption_quota_message,
                    deferred_video_scope=deferred_video_scope,
                    deferred_visibility_unknown=deferred_visibility_unknown,
                    _upload_progress=None,
                )


async def _monitor_loop(stop_event: asyncio.Event) -> None:
    # Always run one cycle as soon as the process starts. Persisted
    # ``last_cycle_at`` is diagnostic only and must not postpone recovery after
    # the tool has been closed and reopened.
    while not stop_event.is_set():
        idle_wait = MONITOR_IDLE_POLL_SECONDS
        try:
            result = await run_audio_recovery_cycle(stop_event=stop_event)
            if result.get("scanned_channels") and not result.get("unreadable"):
                idle_wait = 0
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Unexpected audio auto-recovery monitor error")
        if stop_event.is_set():
            break
        if not idle_wait:
            # Yield to the UI and cancellation without delaying the next scan.
            await asyncio.sleep(0)
            continue
        # Empty, disabled, blocked, or failed cycles can complete without I/O.
        # Poll briefly instead of spinning while there is no scan to perform.
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=idle_wait)
        except asyncio.TimeoutError:
            continue


def start_audio_recovery_monitor() -> None:
    """Start one client-independent monitor for the current app process."""
    global _MONITOR_TASK, _MONITOR_STOP
    if _MONITOR_TASK is not None and not _MONITOR_TASK.done():
        return
    try:
        import_add_audio_flow_recovery_state()
    except Exception:
        # A damaged legacy page snapshot must not prevent the monitor from
        # protecting entries which are already in the recovery registry.
        logger.exception("Could not import legacy Add Audio Flow recovery state")
    _MONITOR_STOP = asyncio.Event()
    _MONITOR_TASK = asyncio.create_task(
        _monitor_loop(_MONITOR_STOP), name="audio-auto-recovery"
    )
    _update_runtime_status(
        monitor_running=True,
        phase="idle",
        message="Tự động khôi phục audio đang hoạt động",
    )
    logger.info("Audio auto-recovery monitor is running (continuous scans, no audio repair delay).")


def stop_audio_recovery_monitor() -> None:
    global _MONITOR_TASK, _MONITOR_STOP
    if _MONITOR_STOP is not None:
        _MONITOR_STOP.set()
    if _MONITOR_TASK is not None and not _MONITOR_TASK.done():
        _MONITOR_TASK.cancel()
    _MONITOR_TASK = None
    _MONITOR_STOP = None
    _update_runtime_status(
        monitor_running=False,
        active=False,
        phase="stopped",
        message="Tự động khôi phục audio đã dừng",
        _upload_progress=None,
    )
