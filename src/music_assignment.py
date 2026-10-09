"""Balanced music assignment shared by video processing flows."""

from __future__ import annotations

import os
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def _path_key(value: str | os.PathLike[str]) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(value)))


def build_balanced_music_plan(
    musics: Sequence[Path],
    items: Sequence[Mapping[str, Any]],
    *,
    randomize: bool,
    rng: random.Random | None = None,
) -> dict[int, Path]:
    """Assign songs randomly while keeping their usage as even as possible.

    Completed merge steps retain their original music so resuming a checkpoint
    cannot silently change an already-rendered video.
    """
    tracks = list(musics)
    if not tracks:
        raise ValueError("At least one music file is required")

    if not randomize:
        return {index: tracks[index % len(tracks)] for index in range(len(items))}

    random_source = rng or random
    track_indexes_by_path = {
        _path_key(track): index for index, track in enumerate(tracks)
    }
    track_indexes_by_name = {
        track.name.casefold(): index for index, track in enumerate(tracks)
    }
    counts: Counter[int] = Counter()
    assignments: dict[int, Path] = {}

    for item_index, item in enumerate(items):
        if item.get("steps", {}).get("merge") != "successful":
            continue

        track_index = None
        saved_path = item.get("music_path")
        if saved_path:
            track_index = track_indexes_by_path.get(_path_key(saved_path))
        if track_index is None and item.get("music"):
            track_index = track_indexes_by_name.get(str(item["music"]).casefold())
        if track_index is None:
            continue

        assignments[item_index] = tracks[track_index]
        counts[track_index] += 1

    # Each new slot is assigned only to a currently least-used song. Therefore,
    # a fresh batch always ends with usage counts differing by at most one.
    for item_index in range(len(items)):
        if item_index in assignments:
            continue
        minimum_usage = min(counts[index] for index in range(len(tracks)))
        least_used = [
            index
            for index in range(len(tracks))
            if counts[index] == minimum_usage
        ]
        track_index = random_source.choice(least_used)
        assignments[item_index] = tracks[track_index]
        counts[track_index] += 1

    return assignments
