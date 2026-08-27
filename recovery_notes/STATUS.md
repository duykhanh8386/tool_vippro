# Application module recovery status

Updated from static analysis of the existing `work/extracted/` tree. The executable has not been re-extracted or run.

Status meanings:

- `Bytecode Exact`: CPython 3.12.10 compilation succeeded and the original/recompiled code-object tree, `co_code`, `co_exceptiontable`, constants, names, varnames, freevars, cellvars, and signatures match 100%.
- `Clean-room / Compile Valid`: Functional clean-room Python implementation, fully compiled (`py_compile` & AST validated) and verified statically for project-wide API compatibility, but without claims of 1-to-1 bytecode equivalence.
- `Failed`: No syntax-valid readable recovery could be produced.

## Completion summary

| Scope | Processed | Bytecode Exact | Clean-room / Compile Valid | Failed |
|---|---:|---:|---:|---:|
| Application-owned modules under `src/` and `web/` | 39 / 39 | 36 | 3 | 0 |

All 39 scoped files, plus `app.py`, compile successfully with CPython 3.12.10 and pass AST validation with 0 errors.

## Per-file Status Classification

| Module | Status | Notes |
|---|---|---|
| `app.py` | Bytecode Exact | Initial seed module proof |
| `src/__init__.py` | Bytecode Exact | Empty package marker |
| `src/channel_refresh.py` | Bytecode Exact | Full round-trip match |
| `src/channel_scanner.py` | Bytecode Exact | Full round-trip match |
| `src/channel_store.py` | Bytecode Exact | Full round-trip match |
| `src/cookie_utils.py` | Bytecode Exact | Full round-trip match |
| `src/license_manager.py` | Bytecode Exact | Full round-trip match — unchanged, no bypass |
| `src/paths.py` | Bytecode Exact | Full round-trip match |
| `src/route_manager.py` | Bytecode Exact | Full round-trip match |
| `src/state_manager.py` | Bytecode Exact | Full round-trip match |
| `src/updater.py` | Bytecode Exact | Full round-trip match |
| `src/utils.py` | Bytecode Exact | Full round-trip match |
| `src/module/__init__.py` | Bytecode Exact | Empty package marker |
| `src/module/audio_module.py` | Bytecode Exact | Full round-trip match |
| `src/module/base.py` | Bytecode Exact | Full round-trip match |
| `src/module/delete_video_module.py` | Bytecode Exact | Full round-trip match |
| `src/module/list_videos_module.py` | Bytecode Exact | Full round-trip match |
| `src/module/model.py` | Bytecode Exact | Full round-trip match |
| `src/module/upload_video_module.py` | Bytecode Exact | Full round-trip match |
| `web/__init__.py` | Bytecode Exact | Empty package marker |
| `web/nicegui_patches.py` | Bytecode Exact | Full round-trip match |
| `web/components/__init__.py` | Bytecode Exact | Empty package marker |
| `web/components/add_audio_flow.py` | Bytecode Exact | Full round-trip match |
| `web/components/audio.py` | Bytecode Exact | Reconstructed & verified 100% exact across all 11 code objects |
| `web/components/auth.py` | Bytecode Exact | Full round-trip match |
| `web/components/common.py` | Bytecode Exact | Full round-trip match |
| `web/components/delete_video_controller.py` | Bytecode Exact | Full round-trip match |
| `web/components/drawer.py` | Bytecode Exact | Full round-trip match |
| `web/components/settings.py` | Bytecode Exact | Full round-trip match |
| `web/components/studio.py` | Bytecode Exact | Full round-trip match |
| `web/views/__init__.py` | Bytecode Exact | Full round-trip match |
| `web/views/audio.py` | Bytecode Exact | Full round-trip match |
| `web/views/auth.py` | Bytecode Exact | Full round-trip match |
| `web/views/delete_back_flow.py` | Bytecode Exact | Full round-trip match |
| `web/views/delete_video.py` | Bytecode Exact | Full round-trip match |
| `web/views/settings.py` | Bytecode Exact | Full round-trip match |
| `web/views/studio.py` | Bytecode Exact | Full round-trip match |
| `web/components/delete_video.py` | Clean-room / Compile Valid | Clean-room Python implementation; py_compile & static compatibility verified |
| `web/components/remove_audio.py` | Clean-room / Compile Valid | Clean-room Python implementation; py_compile & static compatibility verified |
| `web/components/delete_back_flow.py` | Clean-room / Compile Valid | Clean-room Python implementation; py_compile & static compatibility verified |
