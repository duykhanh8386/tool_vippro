#!/usr/bin/env python3
"""Generate Markdown-wrapped xdis output for static recovery notes."""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from xdis.disasm import disassemble_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for source in args.inputs:
        buffer = io.StringIO()
        disassemble_file(str(source), buffer)
        target = args.output_dir / f"{source.stem}.md"
        text = (
            f"# Static CPython 3.12 disassembly — `{source.name}`\n\n"
            "Generated with `xdis 6.3.0`; the code object was deserialized but never executed.\n\n"
            "```text\n"
            f"{buffer.getvalue()}"
            "```\n"
        )
        target.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
