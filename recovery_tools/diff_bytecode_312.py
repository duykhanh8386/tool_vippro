#!/usr/bin/env python3
"""Show semantic instruction mismatches for cross-version CPython 3.12 pyc files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from xdis.load import load_module
from xdis.std import make_std_api


def is_code(value: Any) -> bool:
    return all(hasattr(value, attr) for attr in ("co_name", "co_consts", "co_code"))


def walk(code: Any):
    yield getattr(code, "co_qualname", code.co_name), code
    for value in code.co_consts:
        if is_code(value):
            yield from walk(value)


def normalized_instructions(api: Any, code: Any):
    # CPython 3.12 wordcode uses two bytes per physical instruction. Keeping
    # CACHE and raw arguments avoids xdis's formatter assertion on a few 3.12
    # exception opcodes while still locating the exact byte-level divergence.
    data = bytes(code.co_code)
    return [
        (offset, api.opc.opname[data[offset]], data[offset + 1])
        for offset in range(0, len(data), 2)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("recovered", type=Path)
    parser.add_argument("--code-object", action="append", default=[])
    args = parser.parse_args()

    old_loaded = load_module(str(args.original))
    new_loaded = load_module(str(args.recovered))
    old = dict(walk(old_loaded[3]))
    new = dict(walk(new_loaded[3]))
    api = make_std_api(old_loaded[0])
    selected = set(args.code_object)

    for name in sorted(old.keys() & new.keys()):
        if selected and name not in selected:
            continue
        left = normalized_instructions(api, old[name])
        right = normalized_instructions(api, new[name])
        if left == right:
            continue
        print(f"\n{name}: original={len(left)} instructions recovered={len(right)}")
        limit = min(len(left), len(right))
        mismatch = next((i for i in range(limit) if left[i] != right[i]), limit)
        for index in range(max(0, mismatch - 5), min(max(len(left), len(right)), mismatch + 18)):
            old_item = left[index] if index < len(left) else None
            new_item = right[index] if index < len(right) else None
            flag = "!" if old_item != new_item else " "
            print(f"{flag} {index:4}: {old_item!r} | {new_item!r}")


if __name__ == "__main__":
    main()
