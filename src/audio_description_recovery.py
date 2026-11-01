"""Registry track decisions, completion checkpoints and source-file lookup."""

from pathlib import Path

from src.audio_batch_matcher import load_mapping_csv, normalize_title, scan_audio_files
from src.audio_language import normalize_language_code
from src.module.audio_module import UpdateAudioModule
from src.utils import normalize_path


DESCRIPTION_VERIFY_SECONDS = 30
DESCRIPTION_RETRY_SECONDS = 30
AUDIO_CONTENT_TYPES = ("dubbed", "descriptive")


def enabled_audio_types(state: dict) -> tuple[str, ...]:
    selected = state.get("audio_content_types", AUDIO_CONTENT_TYPES)
    if not isinstance(selected, (list, tuple)):
        selected = AUDIO_CONTENT_TYPES
    return tuple(kind for kind in AUDIO_CONTENT_TYPES if kind in selected)


def track_state_prefix(audio_content_type: str) -> str:
    return "dubbed" if audio_content_type == "dubbed" else "description"


def description_languages(entry: dict) -> list[str]:
    return list(dict.fromkeys(
        normalize_language_code(str(language))
        for language in entry.get("languages") or [] if str(language or "").strip()
    ))


def description_entry_complete(entry: dict) -> bool:
    return audio_entry_complete(entry, "descriptive")


def audio_entry_complete(entry: dict, audio_content_type: str) -> bool:
    languages = description_languages(entry)
    completed = {str(language).casefold() for language in entry.get(track_state_prefix(audio_content_type) + "_completed_languages") or []}
    return bool(languages) and all(language.casefold() in completed for language in languages)


def registry_entry_complete(entry: dict, audio_types) -> bool:
    return bool(audio_types) and all(audio_entry_complete(entry, kind) for kind in audio_types)


def description_work_due(entry: dict, now: float) -> bool:
    return audio_work_due(entry, now, "descriptive")


def audio_work_due(entry: dict, now: float, audio_content_type: str) -> bool:
    if audio_entry_complete(entry, audio_content_type) or not description_languages(entry):
        return False
    try:
        return float(entry.get(track_state_prefix(audio_content_type) + "_next_check_at") or 0) <= now
    except (ValueError, TypeError):
        return True


def registry_work_due(entry: dict, now: float, audio_types=("descriptive",)) -> bool:
    if audio_types and registry_entry_complete(entry, audio_types):
        return False
    if any(audio_work_due(entry, now, kind) for kind in audio_types):
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


def _original_audio_track(track: dict) -> bool:
    kind = str(track.get("audioContentTypeString") or track.get("audioContentType") or "").casefold()
    source = str(track.get("source") or track.get("audioTrackSource") or "").upper()
    return kind == "original" or (kind in {"", "dubbed"} and source == "AUDIO_TRACK_SOURCE_UPLOAD")


def build_description_recovery_plan(payload: dict, entries: dict, video_ids, audio_content_type="descriptive") -> tuple[list[dict], set[str], dict]:
    requested = list(dict.fromkeys(str(video_id) for video_id in video_ids))
    readable = UpdateAudioModule._readable_translation_video_ids(payload, requested)
    unreadable = set(requested) - readable
    observations = {}
    actions = []
    for video_id in requested:
        if video_id not in readable:
            continue
        entry = entries.get(video_id) or {}
        completed = {str(lang).casefold() for lang in entry.get(track_state_prefix(audio_content_type) + "_completed_languages") or []}
        tracks = [track for track in UpdateAudioModule._video_audio_tracks(payload, video_id)
                  if ((_original_audio_track(track) or UpdateAudioModule._is_creator_dubbed_track(track))
                      if audio_content_type == "dubbed" else
                      str(track.get("audioContentTypeString") or track.get("audioContentType") or "").casefold() == "descriptive")]
        video_observations = observations[video_id] = {}
        for language in description_languages(entry):
            key = language.casefold()
            if key in completed:
                continue
            states = {}
            original = False
            for track in tracks:
                if (UpdateAudioModule._translation_language(track) or "").casefold() != key:
                    continue
                if audio_content_type == "dubbed" and _original_audio_track(track):
                    state = "healthy"
                    original = True
                elif UpdateAudioModule._audio_payload_has_terminal_failure(track, assume_audio=True):
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
            if audio_content_type == "dubbed" and state == "healthy" and not original:
                track_ids = sorted({track_id for ids in states.values() for track_id in ids})
            video_observations[key] = {"language": language, "state": state, "track_ids": track_ids}
            if original:
                video_observations[key]["original"] = True
            if state in {"missing", "terminal"}:
                actions.append({"video_id": video_id, "language": language, "track_ids": track_ids,
                                "reason": ("missing_description" if audio_content_type == "descriptive" else "missing_audio") if state == "missing" else "terminal",
                                "audio_content_type": audio_content_type})
    return actions, unreadable, observations


def build_registry_recovery_plan(payload: dict, entries: dict, video_ids, audio_types, now: float):
    actions, unreadable, observations = [], set(), {}
    for kind in audio_types:
        selected = {}
        for video_id in video_ids:
            entry = entries[video_id]
            if audio_work_due(entry, now, kind) or (kind == "dubbed" and "descriptive" in audio_types
                                                   and description_work_due(entry, now)):
                selected[video_id] = dict(entry)
                if kind == "dubbed" and "descriptive" in audio_types:
                    selected[video_id]["dubbed_completed_languages"] = []
        planned, missing, observed = build_description_recovery_plan(payload, selected, list(selected), kind)
        actions.extend(planned)
        unreadable.update(missing)
        observations[kind] = observed
    if set(audio_types) == set(AUDIO_CONTENT_TYPES):
        deferred_descriptions = set()
        normal_actions = {(action["video_id"], action["language"].casefold()): action
                          for action in actions if action["audio_content_type"] == "dubbed"}
        for action in list(actions):
            if action["audio_content_type"] != "descriptive":
                continue
            video_id, key = action["video_id"], action["language"].casefold()
            normal = observations.get("dubbed", {}).get(video_id, {}).get(key, {})
            if normal.get("state") == "processing" and (video_id, key) not in normal_actions:
                deferred_descriptions.add((video_id, key))
            if (video_id, key) in normal_actions:
                normal_actions[video_id, key]["description_pair"] = True
            elif (normal.get("state") == "healthy" and not normal.get("original")
                  and key not in {str(lang).casefold() for lang in entries[video_id].get("dubbed_prepared_for_description") or []}):
                actions.append({"video_id": video_id, "language": action["language"],
                                "audio_content_type": "dubbed", "reason": "paired_description",
                                "track_ids": normal["track_ids"], "description_pair": True})
        actions = [action for action in actions if action["audio_content_type"] != "descriptive"
                   or (action["video_id"], action["language"].casefold()) not in deferred_descriptions]
    actions.sort(key=lambda action: AUDIO_CONTENT_TYPES.index(action["audio_content_type"]))
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
