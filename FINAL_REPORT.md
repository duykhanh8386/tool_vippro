# TV Automation Python Source Recovery — Final Report

## Outcome

Static recovery and static compatibility audit are complete for all 39 application-owned Python modules found under the `src/` and `web/` namespaces (plus `app.py`).

| Classification | Count |
|---|---:|
| **Bytecode Exact** | **36** |
| **Clean-room / Compile Valid** | **3** |
| **Failed** | **0** |
| **Total Scoped Modules** | **39 / 39** |
| **Total `.py` files in `recovered_project/`** | **40** |
| **CPython 3.12.10 Compile / AST Errors** | **0** |

Recovered source files are located in `recovered_project/`. Detailed status per file is recorded in `recovery_notes/STATUS.md`.

---

## Classifications

### 1. Bytecode Exact (36 Modules)
36 modules (including 32 code modules and 4 empty package markers) passed 100% of recursive bytecode round-trip verification criteria against the original extracted `.pyc` files:
- Identical code-object tree structure and qualnames
- Identical `co_code` byte-for-byte
- Identical `co_exceptiontable` byte-for-byte
- Identical non-code constants, `co_names`, `co_varnames`, `co_freevars`, `co_cellvars`
- Identical signatures, argument counts, and code flags

Notable exact recoveries: `web/components/audio.py`, `web/components/add_audio_flow.py`, `web/components/delete_video_controller.py`, `src/license_manager.py` (unchanged), core state/database/routing modules, scanner, upload/audio API modules, and all `web/views/` modules.

### 2. Clean-room / Compile Valid (3 Modules)
Per clean-room workflow directives, the following 3 UI component modules were reconstructed as clean-room Python code:
- `web/components/delete_video.py`
- `web/components/remove_audio.py`
- `web/components/delete_back_flow.py`

All 3 modules have been statically verified across the entire workspace for:
- 100% CPython 3.12.10 compilation (`py_compile`) and AST parsing without errors
- Function & callback signatures and parameter types
- Positional & keyword argument matching
- Expected return values and state keys (`"delete_video_settings"`, `"audio_remove"`, `"delete_back_flow"`)
- Sync/async compatibility across all NiceGUI handlers and background threads
- Exact API calls to controller, `state_manager`, `channel_store`, `src.module.*`, and common UI helpers

---

## Static Incompatibilities Found and Resolved

During static compatibility auditing of the clean-room modules against exact project APIs, the following 5 parameter/import mismatches were identified and fixed in the clean-room modules:

1. **`web/components/delete_back_flow.py` — `create_channel_selection` keyword argument name**:
   - *Incompatibility*: Called `create_channel_selection(..., initial_selected_id=...)`.
   - *Exact API signature*: `create_channel_selection(channels, on_channel_select, multi_select=False, initial_selected_ids=None)`.
   - *Fix*: Changed keyword argument name from `initial_selected_id` to `initial_selected_ids`.

2. **`web/components/delete_back_flow.py` — `build_intermittent_audio` call parameters**:
   - *Incompatibility*: Called `build_intermittent_audio(..., times=1, extra_minutes=0, video_duration_seconds=...)`.
   - *Exact API signature*: `build_intermittent_audio(music_file, audio_out, play_sec=3.0, mute_sec=7.0)`.
   - *Fix*: Removed invalid keyword arguments `times`, `extra_minutes`, and `video_duration_seconds`.

3. **`web/components/delete_back_flow.py` — `mux_audio_into_video` output argument name**:
   - *Incompatibility*: Called `mux_audio_into_video(..., output_file=video_out)`.
   - *Exact API signature*: `mux_audio_into_video(video_file, audio_file, video_out, duration=None, video_bitrate='1M', overlay_png=None)`.
   - *Fix*: Changed keyword argument name from `output_file` to `video_out`.

4. **`web/components/delete_back_flow.py` — Copyright status polling method**:
   - *Incompatibility*: Called nonexistent method `list_videos_module.get_video_by_id`.
   - *Exact API signature*: `list_videos_module.get_copyright_statuses(channel_id, video_ids)`.
   - *Fix*: Updated `step_wait_processed` to call `list_videos_module.get_copyright_statuses(channel_id, {video_id})`.

5. **`web/components/remove_audio.py` — Import module path**:
   - *Incompatibility*: Imported `from src.module.update_audio_module import update_audio_module`.
   - *Exact API signature*: `update_audio_module` is defined and exported in `src.module.audio_module`.
   - *Fix*: Updated import statement to `from src.module.audio_module import update_audio_module`.

---

## Final Verification Summary

- **Project-wide Compilation**: 39 / 39 scoped modules compiled with 0 errors on CPython 3.12.10.
- **AST Validation**: 39 / 39 scoped modules parsed with 0 syntax or structure errors.
- **Static Import & API Checks**: 100% pass across all call sites and exact API modules.
- **Safety**: The executable and recovered application were NOT run. No original executable was executed.
