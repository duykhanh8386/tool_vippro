# 05 — Decompile quality report

## Tool assessment

| Tool | Version | CPython 3.12 status in this run |
|---|---|---|
| `depyo` | 1.2.4 | Real source decompiler; advertises Python 1.0–3.15 support. Produced source for all 5 files, but control-flow correction was required in 3 modules. |
| `xdis` / `pydisasm` | 6.3.0 | Correctly loaded and disassembled magic 3531 / CPython 3.12, including nested code objects and exception tables. |
| `pycdc` upstream | not installed | Not selected: upstream Python 3.12 support remains incomplete/open. |
| `decompyle3` / `uncompyle6` | not installed | Not selected: their maintained support does not cover CPython 3.12 reliably. |
| CPython | 3.12.10 embeddable | Used only to compile recovered source and verify it against the original 3.12 bytecode. |

Raw `depyo` output is preserved under `work/decompiler_raw/`. No code object or recovered module was executed.

## Per-file result

| Module | Decompiled | Syntax valid | Functions/classes recovered | Manual reconstruction | Confidence |
|---|:---:|:---:|---|:---:|---|
| `app.py` | Yes | Yes | Module body | Yes, corrected `IMPORT_STAR` and statement structure | Excellent |
| `src/route_manager.py` | Partial raw output | Yes after reconstruction | 2 classes; 7 methods; 4 nested functions | Yes | Excellent |
| `src/paths.py` | Yes | Yes | 1 function | Minimal, restored original import/statement boundaries | Excellent |
| `src/state_manager.py` | Partial raw output | Yes after reconstruction | 1 class; 6 methods | Yes | Excellent |
| `src/channel_store.py` | Partial raw output | Yes after reconstruction | 5 module functions; 1 class; 8 methods/properties | Yes | Excellent |

## Why the final confidence is Excellent

The confidence rating is based on verification, not on visual plausibility:

1. Every original `.pyc` loaded successfully as CPython 3.12 bytecode.
2. Every recovered file passes `python -m py_compile` under CPython 3.12.10.
3. Recompiled and original code-object trees have identical qualnames, signatures, `co_names`, `co_varnames`, free/cell variables and non-code constants.
4. Every corresponding code object has identical `co_code` bytes.
5. Every corresponding code object has an identical exception table.

Filename and line-table bytes are intentionally excluded from equality because recovered files include the required `# RECOVERED` marker and use readable formatting; comments/line placement cannot be recovered exactly from bytecode.

## Raw decompiler defects corrected from disassembly

### `app.py`

- `depyo` rendered `from web.views import *` as `import web.views`; `IMPORT_STAR` was restored from bytecode.

### `route_manager.py`

- Removed invalid `##FREEVAR_0##` and restored closure access through `self`.
- Restored `params or {}`.
- Restored `route.view_func(**kwargs)` for sync and async handlers.
- Restored the authentication condition and the exact boundary of the async `try/except` block.
- Restored exception logging, notification and `/error` navigation.

### `state_manager.py`

- Corrected `_conn is None` initialization logic.
- Corrected `row is None` handling.
- Restored `except Exception as e`, log messages and true/false return values for all CRUD methods.

### `channel_store.py`

- Restored `cookies or []`, cookie expiry selection and `or` fallbacks.
- Restored two independent schema migration `if` statements.
- Restored SQLite-row field mapping and optional `overlay_png` handling.
- Corrected lazy connection initialization and lock context managers.
- Restored `(cur.rowcount or 0) > 0` and the conditional-expression form of `get_channel`.

## Scope boundary

Exactly five requested application modules were recovered. The remaining extracted `.pyc` files, including `src/license_manager.pyc`, were not decompiled in this step.
