#!/usr/bin/env python3
"""Deserialize a CPython 3.12 .pyc and pass its code object to depyf.

This helper never calls exec(), eval(), FunctionType(), or imports the target
module.  It is intended only for an independent static decompiler comparison.
"""

from __future__ import annotations

import argparse
import marshal
from pathlib import Path

import depyf


def load_code(path: Path):
    with path.open("rb") as stream:
        header = stream.read(16)
        if header[:4] != bytes.fromhex("cb0d0d0a"):
            raise ValueError(f"unexpected Python magic in {path}: {header[:4].hex()}")
        return marshal.load(stream)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    code = load_code(args.input)
    source = depyf.decompile(code)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
