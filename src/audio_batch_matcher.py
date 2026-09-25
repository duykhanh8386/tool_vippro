"""Scan an audio folder and match files to YouTube channel videos."""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from src.utils import AUDIO_INPUT_EXTENSIONS

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


def normalize_title(value: str) -> str:
    """Normalize a title for conservative, exact fallback matching."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    ascii_like = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
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


def _id_named_candidates(video_id: str, files: Iterable[Path]) -> list[Path]:
    escaped = re.escape(video_id)
    pattern = re.compile(rf"^{escaped}(?:$|__|[ ._-])", re.IGNORECASE)
    return [path for path in files if pattern.match(path.stem)]


def match_audio_files(
    videos: Iterable["Video"],
    folder: str | Path,
    *,
    recursive: bool = True,
) -> AudioBatchMatchResult:
    """Match one audio file per video, preferring explicit and exact rules."""
    videos = list(videos)
    files = scan_audio_files(folder, recursive=recursive)
    mappings, mapping_errors = load_mapping_csv(folder)
    title_index: dict[str, list[Path]] = {}
    for path in files:
        title_index.setdefault(normalize_title(path.stem), []).append(path)
    video_title_counts: dict[str, int] = {}
    for video in videos:
        normalized = normalize_title(video.title or "")
        if normalized:
            video_title_counts[normalized] = video_title_counts.get(normalized, 0) + 1

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

        id_candidates = _id_named_candidates(video_id, files)
        if len(id_candidates) == 1:
            path = id_candidates[0]
            used_paths.add(path)
            results.append(AudioMatch(video_id, title, str(path), "video_id", "Khớp Video ID"))
            continue
        if len(id_candidates) > 1:
            results.append(
                AudioMatch(
                    video_id,
                    title,
                    None,
                    "ambiguous",
                    "Có nhiều file cùng khớp Video ID",
                    tuple(str(path) for path in id_candidates),
                )
            )
            continue

        normalized_title = normalize_title(title)
        title_candidates = (
            [path for path in title_index.get(normalized_title, []) if path not in used_paths]
            if normalized_title and video_title_counts.get(normalized_title) == 1
            else []
        )
        if len(title_candidates) == 1:
            path = title_candidates[0]
            used_paths.add(path)
            results.append(AudioMatch(video_id, title, str(path), "title", "Khớp chính xác tiêu đề"))
            continue
        if len(title_candidates) > 1:
            results.append(
                AudioMatch(
                    video_id,
                    title,
                    None,
                    "ambiguous",
                    "Có nhiều file cùng khớp tiêu đề",
                    tuple(str(path) for path in title_candidates),
                )
            )
            continue

        results.append(AudioMatch(video_id, title, None, "unmatched", "Không tìm thấy file phù hợp"))

    extra_files = tuple(str(path) for path in files if path not in used_paths)
    return AudioBatchMatchResult(tuple(results), len(files), extra_files)
