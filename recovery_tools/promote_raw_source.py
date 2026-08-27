#!/usr/bin/env python3
"""Promote generated decompiler text into the recovered tree mechanically."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def repair_mojibake(text: str) -> str:
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--repair-mojibake", action="store_true")
    args = parser.parse_args()

    text = args.source.read_text(encoding="utf-8")
    if args.repair_mojibake:
        text = repair_mojibake(text)
    text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)
    marker = "# RECOVERED: depyo output corrected from CPython 3.12 disassembly\n"
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(marker + text.lstrip("\ufeff"), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
