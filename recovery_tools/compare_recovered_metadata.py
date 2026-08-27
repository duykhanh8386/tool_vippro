#!/usr/bin/env python3
"""Compare recovered-source code metadata against original cross-version .pyc."""

from __future__ import annotations

import argparse
import types
from pathlib import Path
from typing import Any

from xdis.load import load_module


def is_code(value: Any) -> bool:
    return all(hasattr(value, attr) for attr in ("co_name", "co_consts", "co_names", "co_code"))


def walk(code: Any):
    yield getattr(code, "co_qualname", code.co_name), code
    for const in code.co_consts:
        if is_code(const):
            yield from walk(const)


def leaf_consts(code: Any) -> list[str]:
    return [repr(value) for value in code.co_consts if not is_code(value)]


def compare(original_path: Path, source_path: Path) -> list[str]:
    original = load_module(str(original_path))[3]
    if source_path.suffix == ".pyc":
        recovered = load_module(str(source_path))[3]
    else:
        recovered = compile(
            source_path.read_text(encoding="utf-8"),
            str(source_path),
            "exec",
            dont_inherit=True,
        )
    original_map = dict(walk(original))
    recovered_map = dict(walk(recovered))
    failures: list[str] = []

    if set(original_map) != set(recovered_map):
        failures.append(
            f"qualnames differ: missing={sorted(set(original_map)-set(recovered_map))}, "
            f"extra={sorted(set(recovered_map)-set(original_map))}"
        )

    for qualname in sorted(set(original_map) & set(recovered_map)):
        old = original_map[qualname]
        new = recovered_map[qualname]
        checks = {
            "co_names": tuple(old.co_names) == tuple(new.co_names),
            "co_varnames": tuple(old.co_varnames) == tuple(new.co_varnames),
            "co_freevars": tuple(old.co_freevars) == tuple(new.co_freevars),
            "co_cellvars": tuple(old.co_cellvars) == tuple(new.co_cellvars),
            "leaf_consts": leaf_consts(old) == leaf_consts(new),
            "argcount": old.co_argcount == new.co_argcount,
            "posonlyargcount": old.co_posonlyargcount == new.co_posonlyargcount,
            "kwonlyargcount": old.co_kwonlyargcount == new.co_kwonlyargcount,
            "semantic_flags": (old.co_flags & 0x1EC) == (new.co_flags & 0x1EC),
            "co_code": bytes(old.co_code) == bytes(new.co_code),
            "co_exceptiontable": bytes(getattr(old, "co_exceptiontable", b""))
            == bytes(getattr(new, "co_exceptiontable", b"")),
        }
        for label, passed in checks.items():
            if not passed:
                failures.append(f"{qualname}: {label} differs")
                if label == "co_names":
                    failures.append(f"{qualname}: original co_names={tuple(old.co_names)!r}")
                    failures.append(f"{qualname}: recovered co_names={tuple(new.co_names)!r}")
                elif label == "leaf_consts":
                    failures.append(f"{qualname}: original leaf_consts={leaf_consts(old)!r}")
                    failures.append(f"{qualname}: recovered leaf_consts={leaf_consts(new)!r}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs", nargs="+", help="original.pyc=recovered.py")
    args = parser.parse_args()
    any_failed = False
    for pair in args.pairs:
        original_text, source_text = pair.split("=", 1)
        original = Path(original_text)
        source = Path(source_text)
        failures = compare(original, source)
        if failures:
            any_failed = True
            print(f"FAIL {source}")
            for failure in failures:
                print(f"  - {failure}")
        else:
            print(f"PASS {source}: code-object metadata matches")
    raise SystemExit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
