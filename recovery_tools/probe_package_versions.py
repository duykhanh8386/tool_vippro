"""Statically report version assignments/imports from CPython 3.12 .pyc files.

This script deserializes code objects and disassembles them. It never executes a
recovered code object or imports a recovered package.
"""

from __future__ import annotations

import dis
import marshal
import sys
from pathlib import Path


VERSION_NAMES = {"__version__", "VERSION", "version", "version_info"}


def load_code(path: Path):
    with path.open("rb") as stream:
        header = stream.read(16)
        if len(header) != 16:
            raise ValueError("short pyc header")
        return header[:4].hex(), marshal.load(stream)


def probe(path: Path) -> None:
    magic, code = load_code(path)
    instructions = list(dis.get_instructions(code, show_caches=False))
    print(f"FILE {path} magic={magic} co_filename={code.co_filename!r}")
    found = False
    for index, instruction in enumerate(instructions):
        if instruction.opname in {"STORE_NAME", "STORE_GLOBAL"} and instruction.argval in VERSION_NAMES:
            found = True
            start = max(0, index - 4)
            end = min(len(instructions), index + 2)
            print(f"  ASSIGN {instruction.argval}")
            for item in instructions[start:end]:
                print(f"    {item.offset:>4} {item.opname:<22} {item.argrepr}")
        elif instruction.opname == "IMPORT_FROM" and instruction.argval in VERSION_NAMES:
            found = True
            print(f"  IMPORT_FROM {instruction.argval} at offset {instruction.offset}")
    if not found:
        candidates = [
            value
            for value in code.co_consts
            if isinstance(value, (str, tuple)) and any(char.isdigit() for char in str(value))
        ]
        print(f"  NO_DIRECT_VERSION_ASSIGNMENT candidate_constants={candidates!r}")


for argument in sys.argv[1:]:
    probe(Path(argument))
