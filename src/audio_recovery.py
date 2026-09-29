"""Persistent background recovery for creator-uploaded YouTube audio tracks.

The registry lives in the app SQLite database, so it survives browser/NiceGUI
disconnects and process restarts on the same machine or VM.  The monitor only
replaces the failed/missing languages recorded after a successful manual run;
it never deletes healthy languages or the source/original audio track.
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
from src.state_manager import state_manager
from src.utils import multiply_audio, normalize_path


RECOVERY_STATE_NAME = "audio_recovery"
DEFAULT_RECOVERY_INTERVAL_SECONDS = 6 * 60 * 60
DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS = 6 * 60 * 60
INITIAL_RECOVERY_DELAY_SECONDS = 60
REAUTH_ALERT_REASON = "encoded_reauth_proof_token_missing"

# Shared with the manual add-audio page. Mutations are serialized per channel,
# so recovery on channel A can continue while the user works on channel B,
# without ever allowing two delete/add flows to collide on the same channel.
_AUDIO_MUTATION_GUARDS: dict[str, threading.Lock] = {}
_AUDIO_MUTATION_GUARDS_LOCK = threading.RLock()

_STATE_LOCK = threading.RLock()
_MONITOR_TASK: asyncio.Task | None = None
_MONITOR_STOP: asyncio.Event | None = None
_RECOVERY_CLEAR_GENERATION = 0


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


def _default_state() -> dict:
    return {
        "enabled": True,
        "interval_seconds": DEFAULT_RECOVERY_INTERVAL_SECONDS,
        "retry_cooldown_seconds": DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS,
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
    # The recovery cadence is a product-level safety limit rather than a
    # per-page preference. Normalize older 15-minute state after an upgrade.
    state["interval_seconds"] = DEFAULT_RECOVERY_INTERVAL_SECONDS
    return state


def register_audio_recovery(
    *,
    channel_id: str,
    video_id: str,
    audio_path: str,
    languages: Iterable[str],
    repeat_times: int,
    extra_minutes: float,
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
            same_configuration = (
                str(previous.get("audio_path") or "") == clean_path
                and list(previous.get("languages") or []) == clean_languages
                and int(previous.get("repeat_times") or 1) == max(1, int(repeat_times))
                and float(previous.get("extra_minutes") or 0)
                == max(0.0, float(extra_minutes))
            )
            if not same_configuration:
                attempts = {}
        videos[clean_video] = {
            "audio_path": clean_path,
            "languages": clean_languages,
            "repeat_times": max(1, int(repeat_times)),
            "extra_minutes": max(0.0, float(extra_minutes)),
            "registered_at": time.time(),
            "attempts": attempts if isinstance(attempts, dict) else {},
        }
        saved = state_manager.save_state(RECOVERY_STATE_NAME, state)
    if saved:
        logger.info(
            "Audio auto-recovery registered: channel={} video={} languages={}",
            clean_channel,
            clean_video,
            ",".join(clean_languages),
        )
    return saved


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
    readable_ids: set[str] = set()
    groups = payload.get("videoTranslations") or []
    valid_groups = [group for group in groups if isinstance(group, dict)]
    group_ids = [
        update_audio_module._translation_group_video_id(group)
        for group in valid_groups
    ]
    if valid_groups and all(group_id is None for group_id in group_ids):
        if len(valid_groups) == len(requested_order):
            readable_ids.update(requested_order)
        elif len(requested_order) == 1:
            readable_ids.add(requested_order[0])
    else:
        readable_ids.update(
            group_id for group_id in group_ids if group_id in requested
        )

    tracks_by_video: dict[str, list[dict]] = {}
    tracks = payload.get("audioTracks") or []
    if isinstance(tracks, list):
        for track in tracks:
            if not isinstance(track, dict):
                continue
            video_id = str(track.get("videoId") or "")
            if video_id not in requested:
                continue
            readable_ids.add(video_id)
            if update_audio_module._is_creator_dubbed_track(track):
                tracks_by_video.setdefault(video_id, []).append(track)

    actions: list[dict] = []
    for video_id, entry in requested_entries.items():
        if video_id not in readable_ids or not isinstance(entry, dict):
            continue
        creator_tracks = tracks_by_video.get(video_id, [])
        by_language: dict[str, list[dict]] = {}
        for track in creator_tracks:
            language = _track_language(track).casefold()
            if language:
                by_language.setdefault(language, []).append(track)

        for language in entry.get("languages") or []:
            clean_language = str(language or "").strip()
            if not clean_language:
                continue
            matching = by_language.get(clean_language.casefold(), [])
            if matching and any(
                not update_audio_module._audio_payload_needs_attention(
                    track, assume_audio=True
                )
                for track in matching
            ):
                continue
            terminal = [track for track in matching if _track_has_terminal_failure(track)]
            if matching and not terminal:
                # PROCESSING/PENDING is not a terminal loss. Let YouTube finish
                # instead of deleting a valid in-flight upload.
                continue
            actions.append(
                {
                    "video_id": video_id,
                    "language": clean_language,
                    "track_ids": list(
                        dict.fromkeys(
                            str(track.get("audioTrackId") or "").strip()
                            for track in terminal
                            if str(track.get("audioTrackId") or "").strip()
                        )
                    ),
                    "reason": "terminal" if terminal else "missing",
                }
            )

    return actions, requested - readable_ids


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


def _cooldown_elapsed(entry: dict, language: str, now: float, cooldown: float) -> bool:
    attempt = (entry.get("attempts") or {}).get(language.casefold()) or {}
    try:
        attempted_at = float(attempt.get("attempted_at") or 0)
    except (TypeError, ValueError):
        attempted_at = 0
    return now - attempted_at >= cooldown


async def run_audio_recovery_cycle(*, now: float | None = None) -> dict:
    """Scan the persistent registry once and selectively repair lost tracks."""
    cycle_time = float(now if now is not None else time.time())
    repaired = 0
    failed = 0
    unreadable: list[str] = []
    deferred_busy = 0
    cancelled_by_clear = False
    owned_mutation_guard: threading.Lock | None = None
    with _STATE_LOCK:
        cycle_generation = _RECOVERY_CLEAR_GENERATION
    try:
        state = get_audio_recovery_state()
        if not state.get("enabled", True):
            return {"skipped": "disabled", "repaired": 0, "failed": 0}
        entries_by_channel = state.get("entries") or {}
        refresh_alerts = state.get("channel_refresh_alerts") or {}
        try:
            cooldown = max(0.0, float(state.get("retry_cooldown_seconds") or 0))
        except (TypeError, ValueError):
            cooldown = DEFAULT_RECOVERY_RETRY_COOLDOWN_SECONDS
        if not entries_by_channel:
            return {"skipped": "empty", "repaired": 0, "failed": 0}

        logger.info("Audio auto-recovery scan started for {} channel(s).", len(entries_by_channel))
        for channel_id, video_entries in list(entries_by_channel.items()):
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
            video_ids = list(video_entries)
            batch_size = update_audio_module._TRANSLATION_BATCH_SIZE
            channel_actions: list[dict] = []
            channel_requires_refresh = False
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
                actions, missing = build_audio_recovery_plan(
                    payload,
                    {video_id: video_entries[video_id] for video_id in chunk},
                    chunk,
                )
                channel_actions.extend(actions)
                unreadable.extend(sorted(missing))

            if cancelled_by_clear:
                break
            if channel_requires_refresh:
                continue

            actions_by_video: dict[str, list[dict]] = {}
            for action in channel_actions:
                entry = video_entries.get(action["video_id"]) or {}
                if _cooldown_elapsed(entry, action["language"], cycle_time, cooldown):
                    actions_by_video.setdefault(action["video_id"], []).append(action)

            for video_id, actions in actions_by_video.items():
                if _recovery_was_cleared(cycle_generation):
                    cancelled_by_clear = True
                    break
                entry = video_entries.get(video_id) or {}
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
                        channel_mutation_guard = get_audio_mutation_guard(channel_id)
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
                                )
                            )
                            repaired += 1
                            _record_recovery_attempt(
                                channel_id,
                                video_id,
                                language,
                                succeeded=True,
                                message=action["reason"],
                                attempted_at=cycle_time,
                            )
                            logger.info(
                                "Audio auto-recovery completed: channel={} video={} language={} reason={}",
                                channel_id,
                                video_id,
                                language,
                                action["reason"],
                            )
                        except Exception as exc:
                            failed += 1
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
            "unreadable": list(dict.fromkeys(unreadable)),
            "reauth_required": sorted(get_channel_refresh_alerts()),
            "deferred_busy": deferred_busy,
            "cancelled_by_clear": cancelled_by_clear,
        }
        with _STATE_LOCK:
            latest = _load_state()
            latest["last_cycle_at"] = cycle_time
            latest["last_cycle_result"] = result
            state_manager.save_state(RECOVERY_STATE_NAME, latest)
        logger.info(
            "Audio auto-recovery scan finished: repaired={} failed={} unreadable={}.",
            repaired,
            failed,
            len(result["unreadable"]),
        )
        return result
    finally:
        # Defensive cleanup for cancellation between acquisition and the
        # language-level mutation finally block.
        if owned_mutation_guard is not None:
            owned_mutation_guard.release()


async def _monitor_loop(stop_event: asyncio.Event) -> None:
    state = get_audio_recovery_state()
    try:
        last_cycle_at = float(state.get("last_cycle_at") or 0)
    except (TypeError, ValueError):
        last_cycle_at = 0
    if last_cycle_at > 0:
        initial_delay = max(
            0.0,
            DEFAULT_RECOVERY_INTERVAL_SECONDS - (time.time() - last_cycle_at),
        )
        if (state.get("last_cycle_result") or {}).get("deferred_busy"):
            initial_delay = min(initial_delay, 60.0)
    else:
        initial_delay = INITIAL_RECOVERY_DELAY_SECONDS
    try:
        await asyncio.wait_for(
            stop_event.wait(), timeout=initial_delay
        )
        return
    except asyncio.TimeoutError:
        pass
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
    _MONITOR_STOP = asyncio.Event()
    _MONITOR_TASK = asyncio.create_task(
        _monitor_loop(_MONITOR_STOP), name="audio-auto-recovery"
    )
    logger.info(
        "Audio auto-recovery monitor is running (interval={}h).",
        DEFAULT_RECOVERY_INTERVAL_SECONDS / 3600,
    )


def stop_audio_recovery_monitor() -> None:
    global _MONITOR_TASK, _MONITOR_STOP
    if _MONITOR_STOP is not None:
        _MONITOR_STOP.set()
    if _MONITOR_TASK is not None and not _MONITOR_TASK.done():
        _MONITOR_TASK.cancel()
    _MONITOR_TASK = None
    _MONITOR_STOP = None
