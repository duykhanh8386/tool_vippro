"""Persistent background recovery for creator-uploaded YouTube audio tracks.

The registry lives in the app SQLite database, so it survives browser/NiceGUI
disconnects and process restarts on the same machine or VM. The monitor only
replaces registered languages for which Studio returns an explicit terminal
failure; it never infers failure from an omitted row, deletes healthy languages,
or touches the source/original audio track.
"""

from __future__ import annotations

import asyncio
import tempfile
import threading
import time
from pathlib import Path
from typing import Iterable

from loguru import logger

from src.audio_language import call_audio_update_with_retry
from src.module.audio_module import update_audio_module
from src.module.list_videos_module import list_videos_module
from src.state_manager import state_manager
from src.utils import multiply_audio, normalize_path
from src.youtube_caption_api import (
    CaptionAuthenticationError,
    CaptionQuotaExceededError,
    YouTubeCaptionClient,
    get_caption_quota_status,
)


RECOVERY_STATE_NAME = "audio_recovery"
DEFAULT_RECOVERY_INTERVAL_SECONDS = 15 * 60
DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS = 15 * 60
DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS = 15 * 60
CAPTION_STATUS_CHECK_INTERVAL_SECONDS = 6 * 60 * 60
CAPTION_REPAIR_VERIFY_SECONDS = 15 * 60
REAUTH_ALERT_REASON = "encoded_reauth_proof_token_missing"
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
    "channel_id": "",
    "video_id": "",
    "language": "",
    "repair_index": 0,
    "repair_total": 0,
    "repaired": 0,
    "failed": 0,
    "captions_repaired": 0,
    "captions_failed": 0,
    "caption_quota_message": "",
    "deferred_non_public": 0,
    "deferred_visibility_unknown": 0,
    "_upload_progress": None,
}


def _update_runtime_status(**changes) -> None:
    with _RUNTIME_STATUS_LOCK:
        _RUNTIME_STATUS.update(changes)


def get_audio_recovery_runtime_status() -> dict:
    """Return UI-safe live scan/upload progress for the global drawer."""
    with _RUNTIME_STATUS_LOCK:
        snapshot = dict(_RUNTIME_STATUS)
        upload_progress = snapshot.pop("_upload_progress", None)

    # The uploader updates this small mapping from a worker thread. Read its
    # fixed keys individually so a simultaneous ``update`` cannot invalidate a
    # dictionary iterator while the UI polls progress.
    upload = upload_progress if isinstance(upload_progress, dict) else {}

    try:
        sent = max(0, int(upload.get("sent") or 0))
    except (TypeError, ValueError):
        sent = 0
    try:
        total = max(0, int(upload.get("total") or 0))
    except (TypeError, ValueError):
        total = 0
    snapshot["upload_sent"] = sent
    snapshot["upload_total"] = total
    snapshot["upload_status"] = str(upload.get("status") or "")
    snapshot["upload_fraction"] = min(1.0, sent / total) if total else 0.0
    return snapshot


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


def _status_indicates_draft(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, dict):
        for key in ("isDraft", "is_draft"):
            if key in value:
                return _status_indicates_draft(value[key])
        return any(
            _status_indicates_draft(child) for child in value.values()
        )
    normalized = "".join(ch for ch in str(value or "").upper() if ch.isalnum())
    if not normalized or any(
        marker in normalized
        for marker in ("NOTDRAFT", "NONDRAFT", "STATUSNONE", "PUBLISHED")
    ):
        return False
    return normalized in {"1", "TRUE", "DRAFT"} or normalized.endswith(
        ("STATUSDRAFT", "STATEDRAFT")
    )


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


def _get_registered_video_public_statuses(
    channel_id: str,
    video_ids: Iterable[str],
) -> tuple[dict[str, bool], set[str]]:
    """Resolve whether registered IDs are currently and actually public.

    Returns ``(public_status_by_video_id, unresolved_video_ids)``. Draft rows
    are not consistently returned by Studio's unfiltered listing; unresolved
    IDs are therefore deferred just like known non-public videos and remain
    registered for a later cycle.
    """
    requested = list(
        dict.fromkeys(str(video_id or "").strip() for video_id in video_ids)
    )
    requested = [video_id for video_id in requested if video_id]
    remaining = set(requested)
    public_status_by_video_id: dict[str, bool] = {}
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
            public_status_by_video_id[video_id] = _is_currently_public_video(
                video
            )
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

    return public_status_by_video_id, remaining


def _default_state() -> dict:
    return {
        "enabled": True,
        "interval_seconds": DEFAULT_RECOVERY_INTERVAL_SECONDS,
        "retry_cooldown_seconds": DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS,
        "initial_grace_seconds": DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS,
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
    # Recovery cadence is a product-level safety limit rather than a per-page
    # preference. Normalize older six-hour state after an upgrade so existing
    # installations receive the faster verification and retry schedule.
    state["interval_seconds"] = DEFAULT_RECOVERY_INTERVAL_SECONDS
    state["retry_cooldown_seconds"] = DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS
    state["initial_grace_seconds"] = DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS
    return state


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
        videos[clean_video] = updated_entry
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
                "next_check_at": timestamp + DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS,
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

    imported = 0
    for item in statuses.values():
        if not isinstance(item, dict):
            continue
        video_id = str(item.get("video_id") or "").strip()
        audio_path = str(item.get("music_path") or "").strip()
        if not video_id or not audio_path or video_id in existing_video_ids:
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
) -> bool:
    """Persist a reload warning after YouTube rejects the reauth proof flow."""
    clean_channel_id = str(channel_id or "").strip()
    if not clean_channel_id:
        return False
    requested_at = float(now if now is not None else time.time())
    with _STATE_LOCK:
        state = _load_state()
        alerts = state.setdefault("channel_refresh_alerts", {})
        alerts[clean_channel_id] = {
            "requested_at": requested_at,
            "reason": REAUTH_ALERT_REASON,
            "error": str(error),
            "message": (
                "YouTube không cấp token xác thực cho kênh. Vui lòng đăng nhập "
                "và tải lại thông tin kênh để tiếp tục tự động khôi phục audio."
            ),
        }
        saved = state_manager.save_state(RECOVERY_STATE_NAME, state)
    if saved:
        logger.warning(
            "Audio auto-recovery paused for channel={}: missing encodedReauthProofToken; "
            "login/channel reload required.",
            clean_channel_id,
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
) -> tuple[list[dict], set[str]]:
    """Build language-level repairs from one Studio response.

    Returns ``(actions, unreadable_video_ids)``. Each action contains only
    failed track IDs for one registered language; healthy creator dubs and the
    original/source track are left untouched.
    """
    requested_order = requested_order or list(requested_entries)
    requested = set(requested_entries)
    terminal_targets, unreadable_ids = (
        update_audio_module._terminal_repair_targets_from_payload(
            payload, requested_order
        )
    )
    readable_ids = requested - unreadable_ids

    groups = payload.get("videoTranslations") or []
    if not isinstance(groups, list):
        groups = []
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
                translations_by_track[(video_id, track_id)] = item

    source_track_ids: dict[str, set[str]] = {}
    creator_track_ids: dict[str, set[str]] = {}
    observations: dict[str, dict[str, set[str]]] = {}

    def observe(
        video_id: str,
        language: str,
        state: str,
    ) -> None:
        clean_language = str(language or "").strip().casefold()
        if clean_language:
            observations.setdefault(video_id, {}).setdefault(
                clean_language, set()
            ).add(state)

    tracks = payload.get("audioTracks") or []
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
            else:
                state = "healthy"
            observe(video_id, language, state)

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
            else:
                state = "healthy"
            observe(video_id, language, state)

    terminal_by_video = {
        video_id: {
            str(action.get("language") or "").casefold(): action
            for action in video_actions
        }
        for video_id, video_actions in terminal_targets.items()
    }
    actions: list[dict] = []
    for video_id, entry in requested_entries.items():
        if video_id not in readable_ids or not isinstance(entry, dict):
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
            # Absence is not proof of failure. Studio may omit a published
            # language from one response collection, so automatically adding a
            # "missing" row can duplicate an already-published track. Wait for
            # an explicit terminal status in a later scan instead.

    return actions, unreadable_ids


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
) -> dict:
    """Verify recently submitted tracks and re-upload only explicit failures."""
    repaired = 0
    failed = 0
    quota_message = ""
    guard = get_audio_mutation_guard(channel_id)

    for video_id, entry in entries.items():
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
            tracks = await asyncio.to_thread(client.list_tracks, video_id)
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
                    await asyncio.to_thread(
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
                    if language.casefold() == source_language.casefold():
                        continue
                    # YouTube cannot reliably translate from a source track
                    # while that source is itself being reprocessed. Keep the
                    # failed target monitored and retry it after the repaired
                    # source reaches ``serving``.
                    if source_status != "serving":
                        continue
                    _update_runtime_status(language=language)
                    translated = await asyncio.to_thread(
                        client.download_translation,
                        str(source_track.get("id") or ""),
                        language,
                    )
                    await asyncio.to_thread(
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


def _cooldown_elapsed(entry: dict, language: str, now: float, cooldown: float) -> bool:
    attempt = (entry.get("attempts") or {}).get(language.casefold()) or {}
    try:
        attempted_at = float(attempt.get("attempted_at") or 0)
    except (TypeError, ValueError):
        attempted_at = 0
    return now - attempted_at >= cooldown


def _initial_grace_elapsed(entry: dict, now: float, grace: float) -> bool:
    """Delay the first verification long enough for Studio to settle a new track.

    Legacy entries do not have ``registered_at`` and remain immediately eligible.
    With a 15-minute monitor cadence, a new entry is first checked between 15 and
    30 minutes after it was registered.
    """
    try:
        registered_at = float(entry.get("registered_at") or 0)
    except (TypeError, ValueError):
        registered_at = 0
    return registered_at <= 0 or now - registered_at >= grace


def _registered_language_count(video_entries: dict[str, dict]) -> int:
    return sum(
        len(entry.get("languages") or [])
        for entry in video_entries.values()
        if isinstance(entry, dict)
    )


async def run_audio_recovery_cycle(*, now: float | None = None) -> dict:
    """Scan the persistent registry once and selectively repair audio tracks."""
    cycle_time = float(now if now is not None else time.time())
    with _RUNTIME_STATUS_LOCK:
        cycle_id = int(_RUNTIME_STATUS.get("cycle_id") or 0) + 1
    final_message = "Đã hoàn tất vòng quét tự động"
    repaired = 0
    failed = 0
    captions_repaired = 0
    captions_failed = 0
    caption_quota_message = ""
    unreadable: list[str] = []
    deferred_busy = 0
    deferred_initial_grace = 0
    deferred_non_public = 0
    deferred_visibility_unknown = 0
    cancelled_by_clear = False
    owned_mutation_guard: threading.Lock | None = None
    _update_runtime_status(
        active=True,
        phase="scanning",
        message="Đang tự động quét trạng thái audio...",
        cycle_id=cycle_id,
        cycle_started_at=cycle_time,
        channel_index=0,
        channel_total=0,
        channel_id="",
        video_id="",
        language="",
        repair_index=0,
        repair_total=0,
        repaired=0,
        failed=0,
        captions_repaired=0,
        captions_failed=0,
        caption_quota_message="",
        deferred_non_public=0,
        deferred_visibility_unknown=0,
        _upload_progress=None,
    )
    with _STATE_LOCK:
        cycle_generation = _RECOVERY_CLEAR_GENERATION
    try:
        state = get_audio_recovery_state()
        if not state.get("enabled", True):
            final_message = "Tự động khôi phục audio đang tắt"
            return {"skipped": "disabled", "repaired": 0, "failed": 0}
        entries_by_channel = state.get("entries") or {}
        refresh_alerts = state.get("channel_refresh_alerts") or {}
        try:
            cooldown = max(0.0, float(state.get("retry_cooldown_seconds") or 0))
        except (TypeError, ValueError):
            cooldown = DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS
        try:
            raw_initial_grace = state.get(
                "initial_grace_seconds",
                DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS,
            )
            if raw_initial_grace is None:
                raw_initial_grace = DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS
            initial_grace = max(
                0.0,
                float(raw_initial_grace),
            )
        except (TypeError, ValueError):
            initial_grace = DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS
        if not entries_by_channel:
            final_message = "Chưa có video được đăng ký tự động khôi phục"
            return {"skipped": "empty", "repaired": 0, "failed": 0}

        channel_total = len(entries_by_channel)
        _update_runtime_status(
            channel_total=channel_total,
            message=f"Đang tự động quét {channel_total} kênh...",
        )
        logger.info("Audio auto-recovery scan started for {} channel(s).", len(entries_by_channel))
        for channel_index, (channel_id, video_entries) in enumerate(
            list(entries_by_channel.items()), 1
        ):
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
            if _recovery_was_cleared(cycle_generation):
                cancelled_by_clear = True
                break
            if not isinstance(video_entries, dict):
                continue
            if channel_id in refresh_alerts:
                logger.info(
                    "Audio auto-recovery paused for channel={}: waiting for full channel refresh.",
                    channel_id,
                )
                continue
            eligible_entries = {
                video_id: entry
                for video_id, entry in video_entries.items()
                if isinstance(entry, dict)
                and _initial_grace_elapsed(entry, cycle_time, initial_grace)
            }
            deferred_initial_grace += len(video_entries) - len(eligible_entries)
            if not eligible_entries:
                continue

            # The normal/manual flow owns this guard for its entire channel
            # batch. Do not even scan YouTube while it is active; defer this
            # channel to keep recovery traffic and state decisions isolated.
            channel_mutation_guard = get_audio_mutation_guard(channel_id)
            if channel_mutation_guard.locked():
                deferred_busy += _registered_language_count(eligible_entries)
                logger.info(
                    "Audio auto-recovery deferred for channel={}: "
                    "manual audio flow has priority.",
                    channel_id,
                )
                continue

            video_ids = list(eligible_entries)
            channel_requires_refresh = False
            try:
                (
                    public_status_by_video_id,
                    unresolved_video_ids,
                ) = await asyncio.to_thread(
                    _get_registered_video_public_statuses,
                    channel_id,
                    video_ids,
                )
            except Exception as exc:
                failed += len(video_ids)
                unreadable.extend(video_ids)
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
                continue

            public_video_ids = [
                video_id
                for video_id in video_ids
                if public_status_by_video_id.get(video_id) is True
            ]
            known_non_public = [
                video_id
                for video_id in video_ids
                if video_id in public_status_by_video_id
                and video_id not in public_video_ids
            ]
            deferred_non_public += len(known_non_public)
            deferred_visibility_unknown += len(unresolved_video_ids)
            if known_non_public or unresolved_video_ids:
                logger.info(
                    "Audio auto-recovery deferred non-public videos: channel={} "
                    "non_public={} visibility_unresolved={}",
                    channel_id,
                    len(known_non_public),
                    len(unresolved_video_ids),
                )
            if not public_video_ids:
                continue

            eligible_entries = {
                video_id: eligible_entries[video_id]
                for video_id in public_video_ids
            }
            video_ids = public_video_ids

            # Caption recovery is intentionally narrower than audio recovery:
            # only recently submitted tracks are monitored, and only an
            # explicit YouTube ``failed`` status is updated. Missing tracks are
            # never inserted here. This runs after the visibility filter so a
            # draft/private/scheduled video cannot consume caption quota.
            if not caption_quota_message:
                caption_result = await _monitor_failed_caption_tracks(
                    channel_id=channel_id,
                    entries=eligible_entries,
                    cycle_time=cycle_time,
                )
                captions_repaired += int(caption_result.get("repaired") or 0)
                captions_failed += int(caption_result.get("failed") or 0)
                caption_quota_message = str(
                    caption_result.get("quota_message") or ""
                )
                _update_runtime_status(
                    captions_repaired=captions_repaired,
                    captions_failed=captions_failed,
                    caption_quota_message=caption_quota_message,
                )

            batch_size = update_audio_module._TRANSLATION_BATCH_SIZE
            channel_actions: list[dict] = []
            for start in range(0, len(video_ids), batch_size):
                if _recovery_was_cleared(cycle_generation):
                    cancelled_by_clear = True
                    break
                chunk = video_ids[start : start + batch_size]
                try:
                    payload = await asyncio.to_thread(
                        update_audio_module._get_video_translation_payload,
                        chunk,
                        channel_id,
                    )
                except Exception as exc:
                    failed += len(chunk)
                    unreadable.extend(chunk)
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
                actions, unreadable_chunk = build_audio_recovery_plan(
                    payload,
                    {video_id: eligible_entries[video_id] for video_id in chunk},
                    chunk,
                )
                channel_actions.extend(actions)
                unreadable.extend(sorted(unreadable_chunk))

            if cancelled_by_clear:
                break
            if channel_requires_refresh:
                continue

            actions_by_video: dict[str, list[dict]] = {}
            for action in channel_actions:
                entry = eligible_entries.get(action["video_id"]) or {}
                if _cooldown_elapsed(entry, action["language"], cycle_time, cooldown):
                    actions_by_video.setdefault(action["video_id"], []).append(action)

            for video_id, actions in actions_by_video.items():
                if _recovery_was_cleared(cycle_generation):
                    cancelled_by_clear = True
                    break
                entry = eligible_entries.get(video_id) or {}
                channel_mutation_guard = get_audio_mutation_guard(channel_id)
                if channel_mutation_guard.locked():
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
                try:
                    _update_runtime_status(
                        phase="preparing",
                        message="Đang chuẩn bị file audio để tự động add lại",
                        channel_id=channel_id,
                        video_id=video_id,
                        language="",
                        repair_index=0,
                        repair_total=len(actions),
                        _upload_progress=None,
                    )
                    video_info = await asyncio.to_thread(
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
                    await asyncio.to_thread(
                        multiply_audio,
                        input_file=normalize_path(str(audio_path)),
                        output_file=str(temp_audio_path),
                        times=max(1, int(entry.get("repeat_times") or 1)),
                        extra_minutes=max(0.0, float(entry.get("extra_minutes") or 0)),
                        video_duration_seconds=duration_seconds,
                    )

                    for action_index, action in enumerate(actions):
                        if _recovery_was_cleared(cycle_generation):
                            cancelled_by_clear = True
                            break
                        language = action["language"]
                        if not channel_mutation_guard.acquire(blocking=False):
                            deferred_busy += len(actions) - action_index
                            logger.info(
                                "Audio auto-recovery deferred for channel={}: "
                                "another audio mutation has priority.",
                                channel_id,
                            )
                            break
                        owned_mutation_guard = channel_mutation_guard
                        try:
                            upload_progress = {
                                "sent": 0,
                                "total": temp_audio_path.stat().st_size,
                                "status": "starting",
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
                                    )
                                )
                            await call_audio_update_with_retry(
                                lambda language=language: update_audio_module.add(
                                    id_video=video_id,
                                    channel_id=channel_id,
                                    file_name=str(temp_audio_path),
                                    language=language,
                                    data=None,
                                    progress=upload_progress,
                                )
                            )
                            repaired += 1
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
                    if _requires_channel_refresh(exc):
                        mark_channel_refresh_required(channel_id, exc, now=cycle_time)
                        channel_requires_refresh = True
                    logger.error(
                        "Audio auto-recovery preparation failed: channel={} video={} error={}",
                        channel_id,
                        video_id,
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
                if cancelled_by_clear:
                    break

            if cancelled_by_clear:
                break

        result = {
            "repaired": repaired,
            "failed": failed,
            "captions_repaired": captions_repaired,
            "captions_failed": captions_failed,
            "caption_quota_message": caption_quota_message,
            "unreadable": list(dict.fromkeys(unreadable)),
            "reauth_required": sorted(get_channel_refresh_alerts()),
            "deferred_busy": deferred_busy,
            "deferred_initial_grace": deferred_initial_grace,
            "deferred_non_public": deferred_non_public,
            "deferred_visibility_unknown": deferred_visibility_unknown,
            "cancelled_by_clear": cancelled_by_clear,
        }
        with _STATE_LOCK:
            latest = _load_state()
            latest["last_cycle_at"] = cycle_time
            latest["last_cycle_result"] = result
            state_manager.save_state(RECOVERY_STATE_NAME, latest)
        logger.info(
            "Auto-recovery scan finished: audio_repaired={} audio_failed={} "
            "captions_repaired={} captions_failed={} unreadable={}.",
            repaired,
            failed,
            captions_repaired,
            captions_failed,
            len(result["unreadable"]),
        )
        final_message = (
            f"Quét xong: đã gửi lại {repaired}, hoãn "
            f"{deferred_non_public + deferred_visibility_unknown} video chưa "
            f"công khai, lỗi {failed}; phụ đề failed đã sửa "
            f"{captions_repaired}, lỗi {captions_failed}"
        )
        return result
    except asyncio.CancelledError:
        final_message = "Đã dừng tự động quét audio"
        raise
    except Exception:
        final_message = "Vòng quét tự động gặp lỗi"
        raise
    finally:
        # Defensive cleanup for cancellation between acquisition and the
        # language-level mutation finally block.
        if owned_mutation_guard is not None:
            owned_mutation_guard.release()
        with _RUNTIME_STATUS_LOCK:
            if _RUNTIME_STATUS.get("cycle_id") == cycle_id:
                _RUNTIME_STATUS.update(
                    active=False,
                    phase="idle",
                    message=final_message,
                    last_cycle_finished_at=time.time(),
                    video_id="",
                    language="",
                    repair_index=0,
                    repair_total=0,
                    repaired=repaired,
                    failed=failed,
                    captions_repaired=captions_repaired,
                    captions_failed=captions_failed,
                    caption_quota_message=caption_quota_message,
                    deferred_non_public=deferred_non_public,
                    deferred_visibility_unknown=deferred_visibility_unknown,
                    _upload_progress=None,
                )


async def _monitor_loop(stop_event: asyncio.Event) -> None:
    # Always run one cycle as soon as the process starts. Persisted
    # ``last_cycle_at`` is diagnostic only and must not postpone recovery after
    # the tool has been closed and reopened.
    while not stop_event.is_set():
        result: dict = {}
        try:
            result = await run_audio_recovery_cycle()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Unexpected audio auto-recovery monitor error")
        state = get_audio_recovery_state()
        try:
            interval = max(60.0, float(state.get("interval_seconds") or 0))
        except (TypeError, ValueError):
            interval = DEFAULT_RECOVERY_INTERVAL_SECONDS
        if isinstance(result, dict) and result.get("deferred_busy"):
            interval = 60.0
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
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
    logger.info(
        "Audio auto-recovery monitor is running (interval={}m, initial_grace={}m).",
        DEFAULT_RECOVERY_INTERVAL_SECONDS / 60,
        DEFAULT_INITIAL_RECOVERY_GRACE_SECONDS / 60,
    )


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
