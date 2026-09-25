"""Scan an audio folder and match files to YouTube channel videos."""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable

from src.utils import AUDIO_INPUT_EXTENSIONS, get_video_duration

if TYPE_CHECKING:
    from src.module.model import Video


_MAPPING_FILENAMES = ("mapping.csv", "audio_mapping.csv")
_AUDIO_COLUMN_NAMES = ("audio_file", "audio_path", "path", "file")


@dataclass(frozen=True)
class AudioMatch:
    video_id: str
    title: str
    path: str | None
    status: str
    detail: str
    candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class AudioBatchMatchResult:
    matches: tuple[AudioMatch, ...]
    audio_file_count: int
    extra_files: tuple[str, ...]

    @property
    def matched(self) -> tuple[AudioMatch, ...]:
        return tuple(item for item in self.matches if item.path)

    @property
    def unmatched(self) -> tuple[AudioMatch, ...]:
        return tuple(item for item in self.matches if item.status == "unmatched")

    @property
    def ambiguous(self) -> tuple[AudioMatch, ...]:
        return tuple(item for item in self.matches if item.status == "ambiguous")


@dataclass(frozen=True)
class AudioRename:
    video_id: str
    source: Path
    target: Path


def normalize_title(value: str) -> str:
    """Normalize a title for filename containment matching."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    ascii_like = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    ascii_like = ascii_like.replace("đ", "d").replace("Đ", "D")
    return "".join(ch.casefold() for ch in ascii_like if ch.isalnum())


def scan_audio_files(folder: str | Path, *, recursive: bool = True) -> list[Path]:
    root = Path(folder).expanduser()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Thư mục nhạc không tồn tại: {root}")
    iterator = root.rglob("*") if recursive else root.glob("*")
    return sorted(
        (path.resolve() for path in iterator if path.is_file() and path.suffix.lower() in AUDIO_INPUT_EXTENSIONS),
        key=lambda path: str(path).casefold(),
    )


def _natural_path_key(path: Path) -> tuple:
    parts = re.split(r"(\d+)", str(path).casefold())
    return tuple(int(part) if part.isdigit() else part for part in parts)


def match_audio_files_sequentially(
    videos: Iterable["Video"],
    folder: str | Path,
    *,
    recursive: bool = True,
) -> AudioBatchMatchResult:
    """Pair channel order with natural filename order for explicit preview."""
    videos = [video for video in videos if (video.id or "").strip()]
    files = sorted(scan_audio_files(folder, recursive=recursive), key=_natural_path_key)
    matched_count = min(len(videos), len(files))
    matches = [
        AudioMatch(
            video.id.strip(),
            video.title or "",
            str(files[index]),
            "sequential",
            f"Ghép lần lượt #{index + 1}",
        )
        for index, video in enumerate(videos[:matched_count])
    ]
    matches.extend(
        AudioMatch(
            video.id.strip(),
            video.title or "",
            None,
            "unmatched",
            "Không còn file nhạc để ghép lần lượt",
        )
        for video in videos[matched_count:]
    )
    return AudioBatchMatchResult(
        tuple(matches),
        len(files),
        tuple(str(path) for path in files[matched_count:]),
    )


def build_audio_rename_plan(
    assignments: Iterable[tuple[str, str | Path]],
) -> tuple[AudioRename, ...]:
    """Validate a safe plan which renames assigned files to VIDEO_ID.ext."""
    plan: list[AudioRename] = []
    target_keys: set[str] = set()
    for video_id, source_value in assignments:
        source = Path(source_value).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"File không tồn tại: {source}")
        target = source.with_name(f"{video_id}{source.suffix.lower()}")
        if source.name.casefold() == target.name.casefold():
            continue
        target_key = str(target).casefold()
        if target_key in target_keys:
            raise ValueError(f"Nhiều file sẽ trùng tên đích: {target}")
        if target.exists():
            raise ValueError(f"Tên đích đã tồn tại: {target}")
        target_keys.add(target_key)
        plan.append(AudioRename(video_id, source, target))
    return tuple(plan)


def execute_audio_rename_plan(plan: Iterable[AudioRename]) -> dict[str, str]:
    """Execute a validated plan and roll completed renames back on failure."""
    plan = tuple(plan)
    # Revalidate immediately before the first filesystem mutation.
    build_audio_rename_plan((item.video_id, item.source) for item in plan)
    completed: list[AudioRename] = []
    try:
        for item in plan:
            item.source.rename(item.target)
            completed.append(item)
    except Exception:
        for item in reversed(completed):
            try:
                if item.target.exists() and not item.source.exists():
                    item.target.rename(item.source)
            except OSError:
                pass
        raise
    return {item.video_id: str(item.target) for item in plan}


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp1258", "cp1252"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return [
                    {
                        str(key or "").strip().casefold(): str(value or "").strip()
                        for key, value in row.items()
                    }
                    for row in csv.DictReader(handle)
                ]
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Không thể đọc {path.name}: {last_error}")


def load_mapping_csv(folder: str | Path) -> tuple[dict[str, Path], dict[str, str]]:
    """Load an optional mapping.csv and return valid paths plus row errors."""
    root = Path(folder).expanduser().resolve()
    mapping_file = next((root / name for name in _MAPPING_FILENAMES if (root / name).is_file()), None)
    if mapping_file is None:
        return {}, {}

    mappings: dict[str, Path] = {}
    errors: dict[str, str] = {}
    for row_number, row in enumerate(_read_csv_rows(mapping_file), 2):
        video_id = (row.get("video_id") or row.get("videoid") or "").strip()
        audio_value = next((row.get(name, "") for name in _AUDIO_COLUMN_NAMES if row.get(name)), "").strip()
        if not video_id:
            continue
        if video_id in mappings or video_id in errors:
            mappings.pop(video_id, None)
            errors[video_id] = f"{mapping_file.name}: Video ID bị lặp ở dòng {row_number}"
            continue
        if not audio_value:
            errors[video_id] = f"{mapping_file.name}: thiếu audio_file ở dòng {row_number}"
            continue
        audio_path = Path(audio_value).expanduser()
        if not audio_path.is_absolute():
            audio_path = root / audio_path
        audio_path = audio_path.resolve()
        if not audio_path.is_file():
            errors[video_id] = f"File trong {mapping_file.name} không tồn tại: {audio_value}"
            continue
        if audio_path.suffix.lower() not in AUDIO_INPUT_EXTENSIONS:
            errors[video_id] = f"Định dạng file trong {mapping_file.name} không được hỗ trợ: {audio_value}"
            continue
        mappings[video_id] = audio_path
    return mappings, errors


def _title_is_in_filename(title: str, path: Path) -> bool:
    normalized_title = normalize_title(title)
    return bool(normalized_title) and normalized_title in normalize_title(path.stem)


def match_audio_files(
    videos: Iterable["Video"],
    folder: str | Path,
    *,
    recursive: bool = True,
    tolerance_seconds: float = 2.0,
    duration_reader: Callable[[str], float] = get_video_duration,
) -> AudioBatchMatchResult:
    """Match audio by YouTube duration, allowing a small configurable delta."""
    if tolerance_seconds < 0:
        raise ValueError("Sai lệch thời lượng không được nhỏ hơn 0 giây")
    videos = list(videos)
    files = scan_audio_files(folder, recursive=recursive)
    mappings, mapping_errors = load_mapping_csv(folder)
    mapped_paths = set(mappings.values())
    durations: dict[Path, float] = {}
    for path in files:
        if path in mapped_paths:
            continue
        try:
            duration = float(duration_reader(str(path)))
            if duration > 0:
                durations[path] = duration
        except Exception:
            # Invalid/unreadable files remain visible in the unused-files list.
            continue

    assigned: dict[int, AudioMatch] = {}
    used_paths: set[Path] = set()
    eligible: list[tuple[int, "Video", float]] = []
    for video_index, video in enumerate(videos):
        video_id = (video.id or "").strip()
        title = video.title or ""
        if not video_id:
            continue

        mapped_path = mappings.get(video_id)
        if mapped_path is not None:
            used_paths.add(mapped_path)
            assigned[video_index] = AudioMatch(
                video_id, title, str(mapped_path), "mapping", "mapping.csv"
            )
            continue
        if video_id in mapping_errors:
            assigned[video_index] = AudioMatch(
                video_id, title, None, "ambiguous", mapping_errors[video_id]
            )
            continue

        video_duration = float(getattr(video, "duration_ms", 0) or 0) / 1000.0
        if video_duration <= 0:
            assigned[video_index] = AudioMatch(
                video_id,
                title,
                None,
                "unmatched",
                "YouTube không trả về thời lượng video",
            )
            continue
        eligible.append((video_index, video, video_duration))

    # Rank every possible audio/video pair globally. This prevents whichever
    # video happens to be visited first from stealing a file that is closer to
    # another video with a similar duration.
    candidate_paths: dict[int, list[Path]] = {}
    ranked_pairs = []
    for video_index, video, video_duration in eligible:
        title = video.title or ""
        for path, audio_duration in durations.items():
            if path in used_paths:
                continue
            delta = abs(audio_duration - video_duration)
            if delta > tolerance_seconds:
                continue
            candidate_paths.setdefault(video_index, []).append(path)
            ranked_pairs.append(
                (
                    delta,
                    0 if _title_is_in_filename(title, path) else 1,
                    video_index,
                    _natural_path_key(path),
                    path,
                    video_duration,
                    audio_duration,
                )
            )

    ranked_pairs.sort(key=lambda item: item[:4])
    for (
        delta,
        title_penalty,
        video_index,
        _path_key,
        path,
        video_duration,
        audio_duration,
    ) in ranked_pairs:
        if video_index in assigned or path in used_paths:
            continue
        video = videos[video_index]
        video_id = (video.id or "").strip()
        title_hint = " · tên file chứa tiêu đề" if title_penalty == 0 else ""
        assigned[video_index] = AudioMatch(
            video_id,
            video.title or "",
            str(path),
            "duration",
            f"Video {video_duration:.1f}s · audio {audio_duration:.1f}s · "
            f"lệch {delta:.1f}s{title_hint}",
        )
        used_paths.add(path)

    results: list[AudioMatch] = []
    for video_index, video in enumerate(videos):
        video_id = (video.id or "").strip()
        if not video_id:
            continue
        if video_index in assigned:
            results.append(assigned[video_index])
            continue
        if candidate_paths.get(video_index):
            detail = "Audio phù hợp đã được ghép cho video có thời lượng gần hơn"
        else:
            detail = f"Không có audio lệch tối đa {tolerance_seconds:g} giây"
        results.append(AudioMatch(video_id, video.title or "", None, "unmatched", detail))

    extra_files = tuple(str(path) for path in files if path not in used_paths)
    return AudioBatchMatchResult(tuple(results), len(files), extra_files)


def match_audio_files_by_title(
    videos: Iterable["Video"],
    folder: str | Path,
    *,
    recursive: bool = True,
) -> AudioBatchMatchResult:
    """Match when the normalized YouTube title occurs anywhere in a filename."""
    videos = list(videos)
    files = scan_audio_files(folder, recursive=recursive)
    mappings, mapping_errors = load_mapping_csv(folder)
    title_counts: dict[str, int] = {}
    for video in videos:
        normalized = normalize_title(video.title or "")
        if normalized:
            title_counts[normalized] = title_counts.get(normalized, 0) + 1

    results: list[AudioMatch] = []
    used_paths: set[Path] = set()
    for video in videos:
        video_id = (video.id or "").strip()
        title = video.title or ""
        if not video_id:
            continue
        mapped_path = mappings.get(video_id)
        if mapped_path is not None:
            used_paths.add(mapped_path)
            results.append(AudioMatch(video_id, title, str(mapped_path), "mapping", "mapping.csv"))
            continue
        if video_id in mapping_errors:
            results.append(AudioMatch(video_id, title, None, "ambiguous", mapping_errors[video_id]))
            continue

        normalized_title = normalize_title(title)
        if not normalized_title:
            results.append(AudioMatch(video_id, title, None, "unmatched", "Video không có tiêu đề"))
            continue
        if title_counts.get(normalized_title, 0) > 1:
            results.append(
                AudioMatch(
                    video_id,
                    title,
                    None,
                    "ambiguous",
                    "Kênh có nhiều video trùng tiêu đề",
                )
            )
            continue

        candidates = [
            path
            for path in files
            if path not in used_paths and _title_is_in_filename(title, path)
        ]
        if len(candidates) == 1:
            path = candidates[0]
            used_paths.add(path)
            results.append(
                AudioMatch(video_id, title, str(path), "title", "Tiêu đề YouTube có trong tên file")
            )
        elif len(candidates) > 1:
            results.append(
                AudioMatch(
                    video_id,
                    title,
                    None,
                    "ambiguous",
                    "Có nhiều file chứa cùng tiêu đề YouTube",
                    tuple(str(path) for path in candidates),
                )
            )
        else:
            results.append(
                AudioMatch(video_id, title, None, "unmatched", "Tiêu đề YouTube không có trong tên file")
            )

    extra_files = tuple(str(path) for path in files if path not in used_paths)
    return AudioBatchMatchResult(tuple(results), len(files), extra_files)
