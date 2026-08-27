"""Collapse excessive blank runs in promoted decompiler output.

This is formatting-only: it does not parse, import, or execute the target source.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    text = args.path.read_text(encoding="utf-8")
    compacted = re.sub(r"(?:[ \t]*\n){3,}", "\n\n", text)
    args.path.write_text(compacted, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
