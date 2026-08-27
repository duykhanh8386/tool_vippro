# 07 — Project Completeness / Buildability Audit

## Scope and safety

This audit covers every Python source file under `recovered_project/`, including `app.py`.

- Static analysis only: AST parsing, import-name resolution, file/reference scanning, and `py_compile`.
- CPython used: **3.12.10** (`work/tools/python312/python.exe`).
- The recovered application was not imported or run.
- `TV Automation.exe`, `TVAutomation_Setup.exe`, DLL/PYD files, and external tools were not executed.
- No recovered source module was modified by this audit.

Machine-readable AST results are retained in `work/project_completeness_ast.json`; compile output is under `work/completeness_compile/`.

## 1. Python inventory and compilation

| Check | Result |
|---|---:|
| Python files found | **40** |
| CPython 3.12.10 `py_compile` passed | **40 / 40** |
| Compile failures | **0** |
| AST parse failures | **0** |

Compilation was performed file-by-file without importing the modules. A successful compile proves syntax and bytecode generation, not runtime behavior or availability of third-party packages/resources.

## 2. Static import graph

The AST scanner examined 255 import records:

| Import category | Records | Resolution result |
|---|---:|---|
| Project-local | 94 records / 93 unique graph edges | **All target modules resolve** |
| Standard library | 106 | Classified against the CPython 3.12 standard library |
| Third-party | 55 | Identified statically; installation was not assumed |

Additional local checks:

- Missing local modules: **0**
- Missing names explicitly imported from local modules: **0**
- Circular-import strongly connected components: **0**
- Notable circular imports: **none found**

### Local graph adjacency list

Modules with no local outgoing edge are omitted.

```text
app -> src.route_manager, web.nicegui_patches, web.views
src.channel_refresh -> src.channel_store, src.cookie_utils, src.utils
src.channel_scanner -> src.channel_store, src.cookie_utils, src.utils
src.channel_store -> src.paths
src.license_manager -> src.paths
src.module.audio_module -> src.module.base, src.module.model, src.utils
src.module.base -> src.channel_refresh, src.module.model, src.utils
src.module.delete_video_module -> src.module.base, src.utils
src.module.list_videos_module -> src.module.base, src.module.model, src.utils
src.module.upload_video_module -> src.module.base, src.utils
src.route_manager -> src.license_manager
src.state_manager -> src.paths
src.utils -> src.channel_store, src.module.model
web.components.add_audio_flow -> src.channel_store, src.module.audio_module, src.module.upload_video_module, src.state_manager, src.utils, web.components.common, web.components.drawer
web.components.audio -> src.module.audio_module, src.state_manager, src.utils
web.components.auth -> src.route_manager
web.components.delete_back_flow -> src.channel_store, src.module.delete_video_module, src.module.list_videos_module, src.module.upload_video_module, src.state_manager, src.utils, web.components.common, web.components.drawer
web.components.delete_video -> src.utils, web.components.common, web.components.delete_video_controller, web.components.drawer
web.components.delete_video_controller -> src.module.delete_video_module, src.module.list_videos_module, src.state_manager, src.utils
web.components.drawer -> src.updater
web.components.remove_audio -> src.module.audio_module, src.state_manager, src.utils, web.components.common
web.components.settings -> src.license_manager, src.route_manager, src.updater
web.components.studio -> src.channel_scanner, src.channel_store, src.license_manager, src.state_manager, src.utils
web.views -> web.views.audio, web.views.auth, web.views.delete_back_flow, web.views.delete_video, web.views.settings, web.views.studio
web.views.audio -> src.route_manager, web.components.add_audio_flow, web.components.audio, web.components.drawer, web.components.remove_audio
web.views.auth -> src.route_manager, web.components.auth
web.views.delete_back_flow -> src.route_manager, web.components.delete_back_flow, web.components.drawer
web.views.delete_video -> src.route_manager, web.components.delete_video, web.components.drawer
web.views.settings -> src.route_manager, web.components.drawer, web.components.settings
web.views.studio -> src.route_manager, web.components.drawer, web.components.studio
```

### Imports inside `try` blocks

| Import | Location | Classification | Observation |
|---|---|---|---|
| `certifi` | `src/updater.py:52` | Third-party | Optional; updater has a fallback SSL context |
| `os` | `web/components/settings.py:78` | Standard library | Scoped inside exception-handling code, not an external dependency |
| `datetime.datetime` | `web/components/studio.py:203` | Standard library | Scoped inside exception-handling code, not an external dependency |

Only `certifi` is an optional external package.

## 3. Entrypoint audit (`app.py`)

`app.py` is a compile-valid top-level entry script. It has **no** `if __name__ == "__main__"` guard. Its module body performs startup actions directly, so importing `app` would also start initialization and eventually call `ui.run(...)`.

### Direct imports and uses

| Import | Classification | Use |
|---|---|---|
| `sys` | Standard library | Reads `sys.frozen` to select NiceGUI reload behavior |
| `nicegui.ui` | Third-party | Calls `ui.run(...)` |
| `src.route_manager.router` | Project-local, resolves | Calls `router.setup_routes()` |
| `web.nicegui_patches.apply_patches` | Project-local, resolves | Calls `apply_patches()` |
| `web.views.*` | Project-local, resolves | Imports view modules whose decorators register routes |

Startup order recovered from the source is:

```text
import view modules / route registrations
-> apply_patches()
-> router.setup_routes()
-> ui.run(title="TV Automation", port=8081, ...)
```

The view package resolves to the auth, audio, delete-back-flow, delete-video, settings, and studio views. Static name checks found no missing local function/class imported by the entrypoint or its direct local imports.

### Entrypoint resources and assumptions

- Favicon: remote GitHub PNG URL; no local icon is required by `app.py`.
- Port: fixed at `8081`; runtime port availability was not tested.
- NiceGUI/FastAPI: must be installed in a source environment.
- Route setup calls license-state functions and indirectly loads the local database/state paths.
- Importing `web.views.*` is behaviorally significant because it registers routes.

**Entrypoint status: STRUCTURALLY COMPLETE / COMPILE VALID / NOT RUNTIME-TESTED.**

## 4. External Python dependencies

The following direct third-party import roots were found. A package is considered required if at least one import occurs outside an optional `try` path.

| Distribution / import root | Required | Imported by |
|---|:---:|---|
| `nicegui` | Yes | `app.py`, `src/route_manager.py`, `web/nicegui_patches.py`, and UI component modules |
| `fastapi` | Yes | `src/route_manager.py` |
| `loguru` | Yes | Core `src` modules and multiple UI components |
| `requests` | Yes | Scanner, license manager, and `src/module/*` API modules |
| `getmac` | Yes | `src/license_manager.py`, `src/module/model.py` |
| `psutil` | Yes | `src/module/model.py` |
| `selenium` | Yes | `src/channel_scanner.py`, `src/module/model.py`, `src/utils.py` |
| `webdriver-manager` / `webdriver_manager` | Yes | `src/module/model.py`, `src/utils.py` |
| `certifi` | No (optional) | `src/updater.py` |

`tkinter` is imported from the standard library by `web/components/common.py`, but a Python installation still needs the platform Tcl/Tk component for those file dialogs.

### Dependency-file reconciliation

No dependency manifest was found in the project/repository source scope:

- no `requirements*.txt`;
- no `pyproject.toml`;
- no `setup.py` or `setup.cfg`;
- no `Pipfile`/`Pipfile.lock`;
- no `poetry.lock`, `uv.lock`, or Conda `environment*.yml`/`.yaml`.

Consequently:

| Reconciliation item | Result |
|---|---:|
| Required direct dependencies declared | **0 / 8** |
| Required direct dependencies missing from declarations | **8** |
| Optional dependency missing from declarations | **1** (`certifi`) |
| Declared but unused dependencies | **0 identifiable** — there is no declaration file to compare |

This is a reproducibility failure, not proof that packages are absent from the machine or from the original PyInstaller bundle. Exact compatible version pins cannot be recovered from imports alone and were not guessed.

## 5. Files, resources, configuration, and tools

### Resource classification

| Resource/reference | Source location | Status | Basis |
|---|---|---|---|
| `VERSION` | `src/updater.py` | **MISSING** | Not present at repository root or `recovered_project/`; updater catches failure and falls back to `v0.0.0` |
| `channels.db` | `src/channel_store.py` | **GENERATED_AT_RUNTIME** | Database path is under the application data directory (or `CHANNEL_DB_PATH` override); schema is created by code |
| `app_state.db` | `src/state_manager.py` | **GENERATED_AT_RUNTIME** | SQLite database/table are initialized by code under the application data directory |
| `license.json` | `src/license_manager.py` | **GENERATED_AT_RUNTIME** | Persistent runtime state under the application data directory; absence is handled as no saved license |
| `deleted_videos.csv` | `web/components/delete_video_controller.py` | **GENERATED_AT_RUNTIME** | Written into the selected output directory after successful operations |
| `deleted_back_videos.csv` | `web/components/delete_back_flow.py` | **GENERATED_AT_RUNTIME** | Written into the selected output directory |
| `output_{i}.m4v`, `output_{i}_processed.mp4`, temporary `.mp4`/audio files | UI flows and `src/utils.py` | **GENERATED_AT_RUNTIME** | Derived media output/temp files |
| `TVAutomation_Setup.exe` download target | `src/updater.py` | **GENERATED_AT_RUNTIME** | Updater downloads a release installer to a temporary path; it is not treated as a source-tree build input |
| Overlay `.png` | UI flows / channel store | **OPTIONAL** | User-selected external input; code checks whether the path exists before use |
| User video/audio inputs (`.mp4`, `.wav`, `.mp3`, etc.) | UI flows / `src/utils.py` | **OPTIONAL / USER INPUT** | Selected at runtime; not bundled source resources |
| Remote favicon PNG | `app.py` | **OPTIONAL / REMOTE** | Loaded from a GitHub URL by NiceGUI/client |
| Templates/static directories | Entire source scan | **NOT REFERENCED** | UI is constructed in Python; no local template/static dependency was found |
| YAML/config/JSON/CSV input files | Entire source scan | **NOT REQUIRED AS BUILD INPUT** | JSON is used for HTTP/state serialization; persistent JSON/CSV files above are runtime state/output |

### External executable/tool paths

| Tool/runtime | Status in current audit environment | Impact |
|---|---|---|
| `ffmpeg` | **MISSING** from `PATH` | Required by audio/video processing functions |
| `ffprobe` | **MISSING** from `PATH` | Required for media-duration probing |
| Chrome/Chromium browser | **NOT DETECTED** by common `PATH` names | Required for Selenium browser workflows; may still be installed outside `PATH` |
| ChromeDriver | **GENERATED/DOWNLOADED AT RUNTIME** | `webdriver_manager.chrome.ChromeDriverManager().install()` supplies the driver; requires network/cache access |
| `open` / `xdg-open` | **OPTIONAL / PLATFORM-SPECIFIC** | Used only by updater launch logic on macOS/Linux; Windows takes a different branch |

The root-level `TVAutomation_Setup.exe` was not inspected or executed during this audit and does not satisfy the missing source dependency manifest or media-tool requirements.

## 6. Other runtime prerequisites visible statically

- Network access is needed for GitHub release/update checks, the remote favicon, webdriver-manager downloads, license-service requests, and YouTube/Google API workflows.
- Write access is needed for the platform application-data directory, selected output directories, and temporary files.
- Chrome/Chromium and a compatible driver are needed for Selenium workflows.
- TCP port `8081` must be available for the default NiceGUI server.
- The clean-room/compile-valid classification of some recovered UI modules is separate from this completeness audit; compile success does not establish behavioral equivalence.

## 7. Buildability conclusion

The recovered tree is **Python-structurally complete**: every file compiles, all project-local module targets and explicitly imported local symbols resolve, and no circular-import component was found.

It is **not reproducibly buildable/runnable as-is** from a clean environment because no Python dependency manifest or version pins exist. Media functionality additionally requires `ffmpeg` and `ffprobe`, both absent from the current `PATH`; browser workflows require Chrome/Chromium; and the expected `VERSION` resource is absent, although that particular absence has a coded fallback.

No runtime test was performed, so this report does not claim successful application startup.

## Final summary

```text
Python files: 40
Compile OK: 40 / 40 (CPython 3.12.10)
Missing local modules: 0
Missing dependencies: 8 required direct packages undeclared; 1 optional package undeclared
Missing resources: 3 confirmed in the audited environment (VERSION, ffmpeg, ffprobe); Chrome/Chromium runtime not detected in PATH
Entrypoint status: STRUCTURALLY COMPLETE / COMPILE VALID / NOT RUNTIME-TESTED
Buildability status: PARTIAL — source compiles, but a clean reproducible build/run is blocked by the absent dependency manifest and external runtime prerequisites
```
