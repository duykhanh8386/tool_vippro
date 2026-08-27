#!/usr/bin/env python3
"""Compile a source tree to a mirrored .pyc tree without importing modules."""

from __future__ import annotations

import argparse
import py_compile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()

    failures = 0
    for source in sorted(args.source_root.rglob("*.py")):
        relative = source.relative_to(args.source_root).with_suffix(".pyc")
        output = args.output_root / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            py_compile.compile(str(source), cfile=str(output), doraise=True)
        except py_compile.PyCompileError as exc:
            failures += 1
            print(f"FAIL {relative}: {exc.msg}")
        else:
            print(f"PASS {relative}")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
