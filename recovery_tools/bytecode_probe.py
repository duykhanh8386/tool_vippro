#!/usr/bin/env python3
"""Statically inspect .pyc code objects with xdis; never executes them."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from xdis.load import load_module


def is_code(value: Any) -> bool:
    return all(hasattr(value, name) for name in ("co_code", "co_consts", "co_name", "co_names"))


def safe_repr(value: Any) -> str:
    if is_code(value):
        return f"<code name={value.co_name!r} filename={value.co_filename!r}>"
    try:
        return repr(value)
    except Exception as exc:  # pragma: no cover - defensive for odd marshal values
        return f"<unrepresentable {type(value).__name__}: {exc}>"


def signature_metadata(code: Any) -> dict[str, Any]:
    positional = int(getattr(code, "co_argcount", 0))
    posonly = int(getattr(code, "co_posonlyargcount", 0))
    kwonly = int(getattr(code, "co_kwonlyargcount", 0))
    varnames = list(getattr(code, "co_varnames", ()))
    flags = int(getattr(code, "co_flags", 0))
    cursor = positional + kwonly
    vararg = varnames[cursor] if flags & 0x04 and cursor < len(varnames) else None
    if vararg is not None:
        cursor += 1
    varkw = varnames[cursor] if flags & 0x08 and cursor < len(varnames) else None
    return {
        "positional_count": positional,
        "posonly_count": posonly,
        "kwonly_count": kwonly,
        "positional_names": varnames[:positional],
        "kwonly_names": varnames[positional:positional + kwonly],
        "vararg": vararg,
        "varkw": varkw,
    }


def inspect_code(code: Any, depth: int = 0) -> dict[str, Any]:
    consts = list(getattr(code, "co_consts", ()))
    nested = [inspect_code(item, depth + 1) for item in consts if is_code(item)]
    names = list(getattr(code, "co_names", ()))
    probable_kind = "code"
    if code.co_name == "<module>":
        probable_kind = "module"
    elif "__module__" in names and "__qualname__" in names:
        probable_kind = "probable class body"
    else:
        probable_kind = "function/lambda/comprehension"
    return {
        "depth": depth,
        "name": code.co_name,
        "qualname": getattr(code, "co_qualname", code.co_name),
        "probable_kind": probable_kind,
        "filename": code.co_filename,
        "firstlineno": int(getattr(code, "co_firstlineno", 0)),
        "flags": f"0x{int(getattr(code, 'co_flags', 0)):x}",
        "stacksize": int(getattr(code, "co_stacksize", 0)),
        "names": names,
        "varnames": list(getattr(code, "co_varnames", ())),
        "freevars": list(getattr(code, "co_freevars", ())),
        "cellvars": list(getattr(code, "co_cellvars", ())),
        "signature": signature_metadata(code),
        "constants": [safe_repr(item) for item in consts],
        "bytecode_size": len(getattr(code, "co_code", b"")),
        "exception_table_size": len(getattr(code, "co_exceptiontable", b"")),
        "nested": nested,
    }


def inspect_pyc(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    version, timestamp, magic_int, code, implementation, source_size, sip_hash, metadata = load_module(str(path))
    return {
        "path": str(path.resolve()),
        "size": len(raw),
        "magic_hex": raw[:4].hex(),
        "header_hex": raw[:16].hex(),
        "xdis_version_tuple": list(version),
        "xdis_magic_int": magic_int,
        "implementation": str(implementation),
        "timestamp": timestamp,
        "source_size": source_size,
        "sip_hash": sip_hash.hex() if isinstance(sip_hash, bytes) else sip_hash,
        "load_success": True,
        "root": inspect_code(code),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps([inspect_pyc(path) for path in args.paths], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
