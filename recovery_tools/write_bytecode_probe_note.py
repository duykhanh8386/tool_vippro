#!/usr/bin/env python3
"""Write the required Markdown bytecode probe for selected .pyc files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from bytecode_probe import inspect_pyc


def inline(values: list[Any]) -> str:
    return ", ".join(f"`{str(value).replace('`', '′')}`" for value in values) or "_(empty)_"


def code_sections(code: dict[str, Any], level: int = 3) -> list[str]:
    heading = "#" * min(level, 6)
    lines = [
        f"{heading} `{code['qualname']}`",
        "",
        f"- Kind: {code['probable_kind']}",
        f"- `co_name`: `{code['name']}`",
        f"- `co_filename`: `{code['filename']}`",
        f"- First line: {code['firstlineno']}",
        f"- Flags: `{code['flags']}`; stack size: {code['stacksize']}; bytecode: {code['bytecode_size']} bytes",
        f"- Exception table: {code['exception_table_size']} bytes",
        f"- Signature metadata: `{code['signature']}`",
        f"- `co_varnames`: {inline(code['varnames'])}",
        f"- `co_names`: {inline(code['names'])}",
        f"- `co_freevars`: {inline(code['freevars'])}",
        f"- `co_cellvars`: {inline(code['cellvars'])}",
        "- `co_consts`:",
        "",
    ]
    if code["constants"]:
        lines.extend(f"  {index}. `{value.replace('`', '′')}`" for index, value in enumerate(code["constants"]))
    else:
        lines.append("  _(empty)_")
    lines.append("")
    for child in code["nested"]:
        lines.extend(code_sections(child, level + 1))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    reports = [inspect_pyc(path) for path in args.inputs]

    lines = [
        "# 04 — CPython 3.12 bytecode probe",
        "",
        "## Method and safety",
        "",
        "The five selected `.pyc` files were deserialized statically with `xdis 6.3.0`. No code object was passed to `exec`, `eval`, a function constructor, or any import mechanism.",
        "",
        "All five files use magic `cb0d0d0a` (magic integer 3531), identified by xdis as CPython 3.12.0 bytecode. The zeroed 16-byte headers originate from PyInstaller extraction and do not prevent code-object loading.",
        "",
        "## File-level results",
        "",
        "| File | Size | Magic | Load | `co_filename` | Nested code objects |",
        "|---|---:|---|:---:|---|---:|",
    ]
    for report in reports:
        nested_count = sum(1 for _ in walk(report["root"])) - 1
        lines.append(
            f"| `{Path(report['path']).name}` | {report['size']} | `{report['magic_hex']}` | yes | "
            f"`{report['root']['filename']}` | {nested_count} |"
        )
    lines.extend(["", "## Detailed code-object metadata", ""])

    for report in reports:
        lines.extend([f"## `{Path(report['path']).name}`", ""])
        lines.extend(code_sections(report["root"], 3))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")


def walk(code: dict[str, Any]):
    yield code
    for child in code["nested"]:
        yield from walk(child)


if __name__ == "__main__":
    main()
