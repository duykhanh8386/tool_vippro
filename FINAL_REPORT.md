# TV Automation Python source recovery — final report

## Outcome

Static recovery is complete for every application-owned Python module found under the extracted `src/` and `web/` namespaces.

| Result | Count |
|---|---:|
| Scoped application modules processed | 39 / 39 |
| Exact | 26 |
| Partial | 13 |
| Failed | 0 |
| Python files in `recovered_project/`, including `app.py` | 40 |
| CPython 3.12.10 syntax/compile failures | 0 |

Recovered source is stored in `recovered_project/`. Per-file status is recorded in `recovery_notes/STATUS.md`.

## Pipeline used

```text
existing extracted .pyc
→ xdis static code-object/disassembly analysis
→ depyo raw source
→ reconstruction or explicitly marked partial promotion
→ CPython 3.12.10 py_compile
→ code-object round-trip comparison
```

The executable and recovered application were not run. The executable was not extracted again. No Wine invocation, DLL/PYD execution, application import, license bypass, authentication bypass, or patching was performed.

## Exact results

Twenty-two non-empty scoped modules passed the complete comparison criteria:

- identical code-object tree and qualnames;
- identical `co_code`;
- identical `co_exceptiontable`;
- identical non-code constants;
- identical `co_names`, `co_varnames`, free variables and cell variables;
- identical signatures and relevant code flags.

Four empty package markers are also classified `Exact`: `src/__init__.py`, `src/module/__init__.py`, `web/__init__.py`, and `web/components/__init__.py`. Their archive entries contain only a 16-byte `.pyc` header, so there is no code object to deserialize; the recovered files intentionally represent the corresponding empty packages.

Notable exact recoveries include the core state/database/routing modules, channel scanning, audio/upload API modules, `license_manager.py` unchanged, NiceGUI patches, and every `web/views/` module.

## Partial results

The following 13 files compile but do not satisfy the exact round-trip criteria:

- `src/updater.py`
- `src/utils.py`
- `web/components/add_audio_flow.py`
- `web/components/audio.py`
- `web/components/auth.py`
- `web/components/common.py`
- `web/components/delete_back_flow.py`
- `web/components/delete_video.py`
- `web/components/delete_video_controller.py`
- `web/components/drawer.py`
- `web/components/remove_audio.py`
- `web/components/settings.py`
- `web/components/studio.py`

For these files, depyo recovered substantial readable source but did not reliably reconstruct complex NiceGUI context managers, closures, async regions, or control flow. Invalid placeholders were converted into valid, conspicuously marked recovery identifiers/TODO regions rather than guessed logic. Vietnamese strings were repaired from reversible UTF-8 mojibake without executing the modules.

These files are useful for inspection and further manual recovery, but are not claimed to be behaviorally equivalent and should not be run as an application in their current state.

## Verification artifacts

- `recovery_notes/STATUS.md`: authoritative per-file status.
- `recovery_notes/03_import_graph.md`: verified imports from the initial pipeline proof.
- `recovery_notes/04_bytecode_probe.md`: code-object metadata probe.
- `recovery_notes/05_decompile_quality.md`: initial five-module quality report.
- `recovery_notes/disassembly/`: retained static disassembly evidence.
- `work/decompiler_full_stage/decompiled/`: raw depyo source and `.pyasm` output.
- `work/roundtrip_final/`: final CPython 3.12.10 compilation output.
- `recovery_tools/compare_recovered_metadata.py`: exact comparison checker.
- `recovery_tools/promote_partial_components.py`: deterministic partial-source promotion and mojibake repair.

## Final validation

- All 40 `.py` files under `recovered_project/` compiled successfully with CPython 3.12.10.
- All 22 non-empty modules classified `Exact` passed a fresh round-trip comparison from the final tree.
- No unprocessed application-owned `.pyc` remains under the extracted `src/` or `web/` namespaces.
- No file is classified `Failed`.

Recovery stops here as requested. The next decision is whether the 13 `Partial` modules justify function-by-function manual reconstruction from their retained disassembly.
