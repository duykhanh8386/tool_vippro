"""Description-only registry decisions and deterministic source-file lookup."""

from pathlib import Path

from src.audio_batch_matcher import load_mapping_csv, normalize_title, scan_audio_files
from src.audio_language import normalize_language_code
from src.module.audio_module import UpdateAudioModule
from src.utils import normalize_path


DESCRIPTION_VERIFY_SECONDS = 30
DESCRIPTION_RETRY_SECONDS = 30


def description_languages(entry: dict) -> list[str]:
    return list(dict.fromkeys(
        normalize_language_code(str(language))
        for language in entry.get("languages") or [] if str(language or "").strip()
    ))


def description_entry_complete(entry: dict) -> bool:
    languages = description_languages(entry)
    completed = {str(language).casefold() for language in entry.get("description_completed_languages") or []}
    return bool(languages) and all(language.casefold() in completed for language in languages)


def description_work_due(entry: dict, now: float) -> bool:
    if description_entry_complete(entry) or not description_languages(entry):
        return False
    try:
        return float(entry.get("description_next_check_at") or 0) <= now
    except (ValueError, TypeError):
        return True


def registry_work_due(entry: dict, now: float) -> bool:
    if description_entry_complete(entry):
        return False
    if description_work_due(entry, now):
        return True
    monitor = entry.get("caption_monitor") or {}
    if not isinstance(monitor, dict) or not monitor.get("languages"):
        return False
    try:
        return float(monitor.get("next_check_at") or 0) <= now
    except (ValueError, TypeError):
        return True


def _confirmed_description(track: dict) -> bool:
    for key in ("status", "publishStatus", "servingStatus"):
        value = str(track.get(key) or "").upper()
        if value in {"READY", "PUBLISHED", "SERVING", "AUDIO_TRACK_STATUS_READY"} or value.endswith("_PUBLISHED"):
            return True
    return str(track.get("statusLabel") or "").casefold() in {"published", "đã xuất bản"}


def build_description_recovery_plan(payload: dict, entries: dict, video_ids) -> tuple[list[dict], set[str], dict]:
    requested = list(dict.fromkeys(str(video_id) for video_id in video_ids))
    readable = UpdateAudioModule._readable_translation_video_ids(payload, requested)
    unreadable = set(requested) - readable
    observations = {}
    actions = []
    for video_id in requested:
        if video_id not in readable:
            continue
        entry = entries.get(video_id) or {}
        completed = {str(lang).casefold() for lang in entry.get("description_completed_languages") or []}
        tracks = [track for track in UpdateAudioModule._video_audio_tracks(payload, video_id)
                  if str(track.get("audioContentTypeString") or track.get("audioContentType") or "").casefold() == "descriptive"]
        video_observations = observations[video_id] = {}
        for language in description_languages(entry):
            key = language.casefold()
            if key in completed:
                continue
            states = {}
            for track in tracks:
                if (UpdateAudioModule._translation_language(track) or "").casefold() != key:
                    continue
                if UpdateAudioModule._audio_payload_has_terminal_failure(track, assume_audio=True):
                    state = "terminal"
                elif UpdateAudioModule._audio_payload_needs_attention(track, assume_audio=True):
                    state = "processing"
                elif _confirmed_description(track):
                    state = "healthy"
                else:
                    state = "processing"
                states.setdefault(state, []).append(str(track["audioTrackId"]))
            state = next((value for value in ("healthy", "processing", "terminal") if value in states), "missing")
            track_ids = sorted(set(states.get(state, [])))
            video_observations[key] = {"language": language, "state": state, "track_ids": track_ids}
            if state in {"missing", "terminal"}:
                actions.append({"video_id": video_id, "language": language, "track_ids": track_ids,
                                "reason": "missing_description" if state == "missing" else "terminal"})
    return actions, unreadable, observations


def resolve_description_audio_path(*, channel_id: str, video_id: str, entry: dict, page_states: dict, title: str = "") -> Path:
    """Use saved bindings first; resolve moved files only when the match is unique."""
    stored = normalize_path(str(entry.get("audio_path") or ""))
    if stored and Path(stored).is_file():
        return Path(stored)
    candidates = []
    folders = set()
    known_names = {Path(stored).name.casefold()} if stored else set()
    if stored and Path(stored).parent.is_dir():
        folders.add(Path(stored).parent)
    for page_name, state in page_states.items():
        if not isinstance(state, dict):
            continue
        if page_name == "add_audio_flow":
            if state.get("selected_channel") != channel_id:
                continue
            for item in (state.get("statuses") or {}).values():
                if isinstance(item, dict) and item.get("video_id") == video_id and item.get("music_path"):
                    candidates.append(Path(normalize_path(str(item["music_path"]))))
            folder = state.get("music_folder")
        else:
            history = (state.get("audio_path_history") or {}).get(channel_id, {})
            historical_path = history.get(video_id)
            if isinstance(historical_path, dict):
                historical_path = historical_path.get("audio_path") or historical_path.get("path")
            if historical_path:
                candidates.append(Path(normalize_path(str(historical_path))))
            settings = state.get("batch_scan_state") or {}
            if (settings.get("result_channel") or state.get("selected_channel")) != channel_id:
                continue
            bound = (state.get("id_to_path") or {}).get(video_id)
            if bound:
                candidates.append(Path(normalize_path(str(bound))))
            folder = settings.get("music_folder")
        if folder and Path(normalize_path(str(folder))).is_dir():
            folders.add(Path(normalize_path(str(folder))))
    existing = {path.resolve() for path in candidates if path.is_file()}
    if len(existing) == 1:
        return existing.pop()
    if len(existing) > 1:
        raise RuntimeError(f"Nhiều file nhạc đã ghép cho video {video_id}; cần xác định lại file đúng.")
    known_names.update(path.name.casefold() for path in candidates)
    files = set()
    mapped = set()
    for folder in folders:
        mappings, errors = load_mapping_csv(folder)
        if video_id in errors:
            raise RuntimeError(errors[video_id])
        if video_id in mappings and mappings[video_id].is_file():
            mapped.add(mappings[video_id].resolve())
        files.update(path.resolve() for path in scan_audio_files(folder))
    normalized_title = normalize_title(title)
    groups = [mapped,
              {path for path in files if path.name.casefold() in known_names},
              {path for path in files if path.stem.casefold() == video_id.casefold()},
              {path for path in files if normalized_title and normalized_title in normalize_title(path.stem)}]
    for matches in groups:
        if len(matches) == 1:
            return matches.pop()
        if len(matches) > 1:
            raise RuntimeError(f"Nhiều file nhạc khớp video {video_id}; đã giữ video trong hàng chờ.")
    raise FileNotFoundError(f"Không tìm thấy file nhạc gốc cho video {video_id}: {stored}")
