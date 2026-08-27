# Application module recovery status

Updated from static analysis of the existing `work/extracted/` tree. The executable has not been re-extracted or run.

Status meanings:

- `Exact`: CPython 3.12.10 compilation succeeded and the original/recompiled code-object tree, `co_code`, `co_exceptiontable`, constants, names and varnames match.
- `Partial`: readable, syntax-valid recovery exists, but at least one exact round-trip criterion does not match.
- `Failed`: no syntax-valid readable recovery could be produced.
- `Pending`: not yet completed in the current full-project pass.

## Completion summary

| Scope | Processed | Exact | Partial | Failed |
|---|---:|---:|---:|---:|
| Application-owned modules under `src/` and `web/` | 39 / 39 | 35 | 4 | 0 |

All 39 scoped files, plus the previously recovered `app.py`, compile successfully with CPython 3.12.10. The 31 non-empty modules marked `Exact` passed the complete round-trip criteria; the four additional `Exact` entries are empty package markers whose extracted files contain only the 16-byte `.pyc` header and therefore have no loadable code object to compare.

The four remaining `Partial` files are syntax-valid and readable, but must not yet be treated as runnable equivalents. Unresolved depyo closure/control-flow regions are retained with a `# RECOVERED` header and, where applicable, `# TODO: bytecode recovery incomplete`. Raw decompiler output remains under `work/decompiler_full_stage/decompiled/`.

## Current function-by-function reconstruction pass

- `web/components/delete_video_controller.py`: **Exact**. The final mismatches in `_load_output_dir`, `set_output_dir`, and `_process_channel` were reconstructed and verified.
- `web/components/add_audio_flow.py`: **Exact**. CPython 3.12.10 compilation succeeds and the complete code-object tree, `co_code`, `co_exceptiontable`, constants, names and varnames match.
- `web/components/audio.py`: **Partial**, compilation succeeds. All recovered code objects now match except:
  - `create_add_audio_page`
  - `create_add_audio_page.<locals>.handle_add_audio`
  - `create_add_audio_page.<locals>.handle_add_audio.<locals>.run_upload`
  - `create_add_audio_page.<locals>.handle_add_audio.<locals>.<genexpr>`
- Not yet revisited in this pass: `delete_back_flow.py`, `delete_video.py`, and `remove_audio.py`.

The executable and recovered application have not been run, and the executable has not been extracted again.

## Previously verified seed modules

| Module | Status | Notes |
|---|---|---|
| `app.py` | Exact | Initial pipeline proof; outside the requested `src/` and `web/` directories. |
| `src/channel_store.py` | Exact | Initial pipeline proof. |
| `src/paths.py` | Exact | Initial pipeline proof. |
| `src/route_manager.py` | Exact | Initial pipeline proof. |
| `src/state_manager.py` | Exact | Initial pipeline proof. |

## Batch 1 — model, runtime patch and views

| Module | Status | Notes |
|---|---|---|
| `src/module/model.py` | Exact | Full round-trip match. |
| `web/nicegui_patches.py` | Exact | Full round-trip match. |
| `web/views/__init__.py` | Exact | Full round-trip match; six relative star imports restored. |
| `web/views/audio.py` | Exact | Full round-trip match. |
| `web/views/auth.py` | Exact | Full round-trip match. |
| `web/views/delete_back_flow.py` | Exact | Full round-trip match. |
| `web/views/delete_video.py` | Exact | Full round-trip match. |
| `web/views/settings.py` | Exact | Full round-trip match. |
| `web/views/studio.py` | Exact | Full round-trip match. |

## Package markers

| Module | Status | Notes |
|---|---|---|
| `src/__init__.py` | Exact | Empty archive/package marker; extracted entry contains only a 16-byte `.pyc` header. |
| `src/module/__init__.py` | Exact | Empty archive/package marker; extracted entry contains only a 16-byte `.pyc` header. |
| `web/__init__.py` | Exact | Empty archive/package marker; extracted entry contains only a 16-byte `.pyc` header. |
| `web/components/__init__.py` | Exact | Empty archive/package marker; extracted entry contains only a 16-byte `.pyc` header. |

## Batch 2 — core helpers and API modules

| Module | Status |
|---|---|
| `src/channel_refresh.py` | Exact |
| `src/cookie_utils.py` | Exact |
| `src/license_manager.py` | Exact — recovered unchanged; no bypass/patch |
| `src/module/base.py` | Exact |
| `src/module/delete_video_module.py` | Exact |
| `src/module/list_videos_module.py` | Exact |

## Batch 3 — scanner, upload/audio modules and utilities

| Module | Status |
|---|---|
| `src/channel_scanner.py` | Exact |
| `src/module/audio_module.py` | Exact |
| `src/module/upload_video_module.py` | Exact |
| `src/updater.py` | Exact |
| `src/utils.py` | Exact |

## Batch 4 — primary UI components

| Module | Status |
|---|---|
| `web/components/auth.py` | Exact |
| `web/components/common.py` | Exact |
| `web/components/drawer.py` | Exact |
| `web/components/settings.py` | Exact |
| `web/components/studio.py` | Exact |

## Batch 5 — workflow UI components

| Module | Status |
|---|---|
| `web/components/add_audio_flow.py` | Exact — full round-trip match after function-by-function reconstruction |
| `web/components/audio.py` | Partial — only the four code objects listed above still mismatch |
| `web/components/delete_back_flow.py` | Partial — syntax valid; unresolved closure/control-flow regions marked |
| `web/components/delete_video.py` | Partial — syntax valid; unresolved closure/control-flow regions marked |
| `web/components/delete_video_controller.py` | Exact — full round-trip match after targeted reconstruction |
| `web/components/remove_audio.py` | Partial — syntax valid; unresolved async/closure regions marked |
