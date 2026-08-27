# 14 — Final Regression Audit and PyInstaller Build Plan

## Scope and safety

This audit re-ran compilation, static compatibility, clean-room functional
tests, and a controlled startup test before preparing a PyInstaller packaging
plan.

- The original executable was not run or extracted again.
- No protected browser route, Selenium operation, upload/delete operation,
  media operation, updater operation, or license API was invoked.
- No Bytecode Exact application module was modified.
- No PyInstaller build was started.

## 1. CPython compilation

Compilation used the full runtime from the final environment:

```text
CPython 3.12.14, 64-bit
```

`recovery_tools/compile_tree.py` was updated to exclude `.venv*` directories;
otherwise it would recursively compile dependency source instead of the 40
application files. The corrected application-only run produced:

```text
SUMMARY total=40 passed=40 failed=0
```

The mirrored regression bytecode is under `work/regression14_pyc/`.

**Compile: PASS — 40/40.**

## 2. Static compatibility and exact-module regression

### AST/import compatibility

`recovery_tools/audit_project_completeness.py` was likewise scoped to exclude
`.venv*`. Its final result was:

| Check | Result |
|---|---:|
| Python application files | 40 |
| Missing local modules | 0 |
| Missing explicitly imported local symbols | 0 |
| Circular-import components | 0 |
| Optional imports | 3 |
| Third-party import roots | 9 |

Third-party roots remain:

```text
certifi, fastapi, getmac, loguru, nicegui, psutil, requests,
selenium, webdriver_manager
```

`pip check` also returned:

```text
No broken requirements found.
```

### Bytecode Exact modules

The recursive code-object audit was re-run against the original extracted
CPython 3.12 bytecode. The comparator was corrected to compare immutable
constant values directly instead of comparing `repr(frozenset)`, whose display
order caused an intermittent false mismatch in `src/utils.py`.

Final result:

```text
Scoped src/web modules: 39
Verified Bytecode Exact: 36
Expected clean-room mismatches: 3
Compile errors: 0
Missing: 0
```

The three mismatches are exactly the documented clean-room modules. All 36
Bytecode Exact modules remain exact; there is no exact-module regression.

**Static compatibility: PASS.**

## 3. Clean-room functional regression

Command:

```powershell
recovered_project/.venv/Scripts/python.exe recovery_tools/functional_smoke_cleanroom.py
```

Result, exit code `0`:

```text
delete_video.py: PASS
remove_audio.py: PASS
delete_back_flow.py: PASS
Overall: 3 PASS / 0 FAIL
```

The harness continued to mock NiceGUI, network, scanning, Selenium, upload,
delete, media, polling, dialogs, persistent state, and audit-log writes.

**Functional smoke: PASS — 3/3.**

## 4. Controlled startup regression

Startup used `recovered_project/activate_runtime.ps1` and the isolated launch
harness with these smoke-only settings:

```text
show=False
reload=False
host=127.0.0.2
port=8081
```

Server outbound HTTP/HTTPS was directed to a closed loopback proxy. This
prevented external/license calls even if an unintended code path were reached.

Results:

| Check | Result |
|---|---|
| NiceGUI startup | PASS |
| `GET /` | 200, 13,428-byte HTML document |
| `GET /auth` | 200, 15,029-byte HTML document |
| Local NiceGUI assets | 11/11 returned 200 |
| Server stderr | Empty |
| Traceback/NiceGUI exception | None |
| Cleanup | PASS; port 8081 clear |

Logs:

```text
work/regression14_startup/stdout.log
work/regression14_startup/stderr.log
```

As in step 12, no browser-control instance was available, so this is a
server/HTTP startup regression rather than a browser-console or pixel-render
test.

**Startup: PASS.**

## 5. PyInstaller build model

Static evidence from the original payload establishes the intended build
shape:

| Setting | Required plan |
|---|---|
| Platform/architecture | Windows x86-64 |
| Python ABI | CPython 3.12 x64 |
| Original exact Python | 3.12.11 |
| Available recovered runtime | 3.12.14 |
| PyInstaller generation | 6.x, at least 6.10; exact version unknown |
| Packaging mode | `onedir` |
| Contents directory | `_internal` |
| Executable name | `TV Automation` |
| PE subsystem | Console, matching the original inner executable |
| Entrypoint | `recovered_project/app.py` |

PyInstaller is not installed in the recovered venv. No version was downloaded
or guessed during this audit.

## 6. Required data files and metadata

### Application data

The spec must include:

```text
recovered_project/VERSION -> VERSION
```

For PyInstaller 6 onedir with `_internal`, this places the file under the
runtime `sys._MEIPASS` root, which is exactly where `src/updater.py` looks for
it when frozen. The installed value is evidence-confirmed `v1.0.0`.

No application template/static directory is referenced. Databases, license
state, CSV logs, overlay PNGs, user media, downloaded installers, and output
media are runtime-generated or user-supplied and must not be build inputs.

### NiceGUI package data

NiceGUI reads resources relative to its installed package path. The current
2.23.3 package contains at least:

| Data subtree | Files | Bytes |
|---|---:|---:|
| `nicegui/static` | 136 | 5,355,332 |
| `nicegui/templates` | 1 | 2,982 |
| `nicegui/elements/lib` | 216 | 43,715,290 |

The spec should use `collect_data_files('nicegui')`, rather than manually
listing only these three directories, so element resources used by this
version are not omitted.

NiceGUI obtains its version through `importlib.metadata.version('nicegui')`.
The spec must therefore retain distribution metadata with
`copy_metadata('nicegui')`.

`certifi`'s CA bundle should also be collected explicitly with
`collect_data_files('certifi')` for deterministic updater/TLS behavior, even
if the installed PyInstaller hook already supplies it.

### Tcl/Tk

`web/components/common.py` statically imports `tkinter` and `filedialog`. The
build must be made from the full CPython environment, not the embeddable
runtime. PyInstaller's Tcl/Tk hook must collect and the build inventory must
confirm:

```text
_tkinter.pyd
tcl86t.dll
tk86t.dll
_tcl_data/
_tk_data/
```

These were all present in the original payload. They must be verified in the
new dist tree after the future build.

### Icon

The original payload contains:

```text
recovery_staging/installer_payload/_internal/logo.ico
```

It can be used as the executable `icon=` input if preservation of the original
icon is desired. It is a build-time PE resource, not application runtime data.
The app's page favicon is a separate optional remote GitHub URL.

## 7. Hidden imports

All project-local modules, including `web.views.*`, are statically reachable;
no local hidden import is required.

Uvicorn selects protocol/loop/lifespan implementations from strings, and
python-engineio selects its async driver with `importlib.import_module`.
The deterministic Windows/NiceGUI hidden-import set should include:

```text
engineio.async_drivers.asgi
uvicorn.lifespan.on
uvicorn.loops.auto
uvicorn.loops.asyncio
uvicorn.protocols.http.auto
uvicorn.protocols.http.h11_impl
uvicorn.protocols.http.httptools_impl
uvicorn.protocols.websockets.auto
uvicorn.protocols.websockets.websockets_impl
uvicorn.protocols.websockets.websockets_sansio_impl
uvicorn.protocols.websockets.wsproto_impl
```

PyInstaller hooks may discover some or all of these, but listing them in the
spec makes the runtime choice explicit and avoids dependency on hook-version
behavior.

No hidden import should be added for optional NiceGUI integrations such as
NumPy, pandas, or polars; the recovered application does not depend on them.
`tkinter`, Selenium, webdriver-manager, and the nine direct dependency roots
are statically imported and should be handled by normal analysis/hooks.

## 8. External runtime resources

The original PyInstaller distribution did not contain `ffmpeg.exe`,
`ffprobe.exe`, or ChromeDriver.

| Resource | Packaging decision |
|---|---|
| FFmpeg/FFprobe | Keep as documented external `PATH` prerequisites to match original behavior, or design a separate explicit bundling/path-resolution change before build |
| Chrome | External installed application; do not bundle |
| ChromeDriver | Resolved by `webdriver-manager` cache/download at runtime; do not silently bundle an arbitrary driver |
| Network | Required at runtime for licensing, updater, YouTube/Google operations, remote favicon, and potentially driver download |
| Port 8081 | Must be available |
| Writable paths | Application-data, temporary, download, and user-selected output directories |

The current activation helper exposes workspace-local FFmpeg 8.1.2 and
FFprobe 8.1.2 for source runs. A built executable launched outside that shell
will still require those commands on `PATH` unless a future distribution
launcher or application path-resolution design is approved.

## 9. Proposed spec structure

The future spec should be based on this structure; it was not created or run
in this step:

```python
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = [
    ('VERSION', '.'),
    *collect_data_files('nicegui'),
    *collect_data_files('certifi'),
    *copy_metadata('nicegui'),
]

hiddenimports = [
    'engineio.async_drivers.asgi',
    'uvicorn.lifespan.on',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.protocols.websockets.websockets_sansio_impl',
    'uvicorn.protocols.websockets.wsproto_impl',
]

# Analysis(['app.py'], datas=datas, hiddenimports=hiddenimports, ...)
# EXE(..., name='TV Automation', console=True, icon=<reviewed logo.ico>)
# COLLECT(..., name='TV Automation')  # onedir / _internal
```

The actual spec should use paths relative to `recovered_project/`, and should
only be finalized after a PyInstaller version is explicitly selected and
pinned.

## 10. Build gate

Regression is clean, and the required hidden imports/data/runtime resources
are now identified. The project is not yet reproducibly ready to build because:

1. PyInstaller is absent from the venv;
2. the artifact only proves `PyInstaller >= 6.10`, not an exact original
   version, so a build-tool version must be selected and recorded;
3. no final `.spec` has yet been generated and subjected to PyInstaller
   Analysis/warnings review;
4. Tcl/Tk collection and NiceGUI data inclusion can only be confirmed against
   the produced dist inventory;
5. the rebuilt environment uses CPython 3.12.14 and compatible current
   transitive packages, not an exact lock of the original CPython 3.12.11
   transitive environment;
6. FFmpeg/FFprobe distribution policy must remain explicitly external or be
   redesigned before shipping a self-contained package.

These are packaging/reproducibility gates, not source regressions.

## Final conclusion

```text
Compile: PASS — 40/40 application Python files
Static compatibility: PASS — 0 missing local modules/symbols, 0 cycles, pip check clean, 36/36 Bytecode Exact unchanged
Functional smoke: PASS — 3/3 clean-room modules
Startup: PASS — isolated NiceGUI startup, / and /auth HTTP 200, 11/11 local assets, stderr empty, server stopped
Build prerequisites: PARTIALLY READY — hidden imports/data/runtime resources identified; PyInstaller version/spec/dist inventory still pending
Ready to build: NO — select/install/pin PyInstaller >=6.10, finalize spec, and confirm external FFmpeg policy first
```
