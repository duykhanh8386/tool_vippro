#!/usr/bin/env python3
"""Decode the NSIS payload's Base64/UTF-16LE path components safely."""

from __future__ import annotations

import argparse
import base64
import binascii
import shutil
from pathlib import Path, PurePath


def decode_component(component: str) -> str:
    try:
        raw = base64.b64decode(component, validate=True)
        decoded = raw.decode("utf-16-le")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return component
    if not decoded or any(char in decoded for char in "\\/\0") or decoded in {".", ".."}:
        raise ValueError(f"Unsafe decoded path component: {component!r} -> {decoded!r}")
    return decoded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)

    copied = 0
    markers = 0
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        parts = [decode_component(part) for part in relative.parts]
        if parts[-1] == "empty.empty":
            (destination / PurePath(*parts[:-1])).mkdir(parents=True, exist_ok=True)
            markers += 1
            continue
        target = destination / PurePath(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"Decoded path collision: {target}")
        shutil.copy2(item, target)
        copied += 1

    print(f"copied_files={copied}")
    print(f"directory_markers={markers}")
    print(f"destination={destination}")


if __name__ == "__main__":
    main()
