# 09 — Clean Python 3.12 Environment Setup

## Scope and safety

This step created and tested a clean dependency environment without starting the recovered application.

- `app.py` was not imported or executed.
- `ui.run()` was not called.
- No Selenium browser or ChromeDriver was started.
- No application network API, upload, deletion, updater, database, or media operation was invoked.
- The original executable and recovered application were not run.
- `requirements.txt` was not changed in response to installation behavior.

## 1. Confirmed inputs

The existing `recovered_project/requirements.txt` contained nine evidenced pins:

```text
nicegui==2.23.3
fastapi==0.116.1
loguru==0.7.3
requests==2.32.5
getmac==0.9.2
psutil==7.0.0
selenium==4.35.0
webdriver-manager==4.0.2
certifi==2025.8.3
```

No pin was edited, relaxed, or replaced.

The `VERSION` evidence was reconfirmed before copying:

- original payload resource: six bytes, `v1.0.0`;
- original SHA-256: `2485f4d55aae6c5b073114bc4c4b1907c0abae14166281beee7d93f76ebf41fc`;
- proposal text after whitespace stripping: `v1.0.0`.

## 2. Virtual environment creation

Target:

```text
recovered_project/.venv
```

The first standard-library attempt was:

```powershell
work/tools/python312/python.exe -m venv recovered_project/.venv
```

It failed before creating the environment because the available CPython 3.12.10 distribution is the Windows embeddable build and does not include the `venv` module:

```text
No module named venv
```

The Windows Python launcher had only Python 3.11 and 3.14 registered; no separate full Python 3.12 installation was available. A workspace-local `virtualenv 21.7.5` bootstrap was therefore installed with explicit approval and used with the existing CPython 3.12.10 executable. It created a standard isolated environment successfully:

```text
creator CPython3Windows
CPython 3.12.10 final, 64-bit
destination: recovered_project/.venv
```

The environment seeded pip 26.2.1. Running the requested upgrade command reported it was already current:

```text
Requirement already satisfied: pip ... (26.2.1)
```

Final interpreter checks:

```text
Python 3.12.10
pip 26.2.1 from recovered_project/.venv/Lib/site-packages/pip (python 3.12)
```

## 3. Requirements installation

Command executed:

```powershell
recovered_project/.venv/Scripts/python.exe -m pip install -r recovered_project/requirements.txt
```

Outcome:

| Check | Result |
|---|---|
| Manifest entries requested | 9 |
| Manifest entries installed | **9 / 9** |
| Direct package failures | **0** |
| Transitive package failures | **0** |
| Resolver failure | **No** |
| Requirements pins changed | **No** |

All requested packages installed at their exact pins. Pip resolved 57 additional transitive distributions, for 66 frozen distributions excluding pip itself.

### Resolved direct versions

| Distribution | Resolved version | Install |
|---|---:|:---:|
| `nicegui` | `2.23.3` | OK |
| `fastapi` | `0.116.1` | OK |
| `loguru` | `0.7.3` | OK |
| `requests` | `2.32.5` | OK |
| `getmac` | `0.9.2` | OK |
| `psutil` | `7.0.0` | OK |
| `selenium` | `4.35.0` | OK |
| `webdriver-manager` | `4.0.2` | OK |
| `certifi` | `2025.8.3` | OK |

### Complete resolved environment

Static result of `pip freeze`:

```text
aiofiles==25.1.0
aiohappyeyeballs==2.7.1
aiohttp==3.14.3
aiosignal==1.4.0
annotated-types==0.8.0
anyio==4.14.2
attrs==26.1.0
bidict==0.24.1
certifi==2025.8.3
cffi==2.1.1
charset-normalizer==3.5.1
click==8.5.0
colorama==0.4.6
docutils==0.23
fastapi==0.116.1
frozenlist==1.8.0
getmac==0.9.2
h11==0.16.0
httpcore==1.0.9
httptools==0.8.0
httpx==0.28.1
idna==3.19
ifaddr==0.2.0
itsdangerous==2.2.0
Jinja2==3.1.6
loguru==0.7.3
markdown2==2.5.5
MarkupSafe==3.0.3
multidict==6.7.1
nicegui==2.23.3
orjson==3.12.0
outcome==1.3.0.post0
packaging==26.3
propcache==0.5.2
pscript==0.7.7
psutil==7.0.0
pycparser==3.0
pydantic==2.13.4
pydantic_core==2.46.4
Pygments==2.21.0
PySocks==1.7.1
python-dotenv==1.2.3
python-engineio==4.13.5
python-multipart==0.0.32
python-socketio==5.16.4
PyYAML==6.0.3
requests==2.32.5
selenium==4.35.0
simple-websocket==1.1.0
sniffio==1.3.1
sortedcontainers==2.4.0
starlette==0.47.3
trio==0.30.0
trio-websocket==0.12.2
typing-inspection==0.4.2
typing_extensions==4.14.1
urllib3==2.7.0
uvicorn==0.52.4
vbuild==0.8.2
watchfiles==1.2.0
webdriver-manager==4.0.2
websocket-client==1.8.0
websockets==17.1
win32_setctime==1.2.0
wsproto==1.3.2
yarl==1.24.5
```

The direct requirements are reproduced exactly, but this is not an exact lock of the original PyInstaller transitive environment. For example, pip selected compatible current versions such as `attrs 26.1.0`, `click 8.5.0`, `MarkupSafe 3.0.3`, and `websockets 17.1`, whereas retained payload metadata evidenced `25.3.0`, `8.2.1`, `3.0.2`, and `15.0.1` respectively. No conflict was reported, but behavioral identity of all transitive dependencies is not claimed.

## 4. Dependency consistency

Command:

```powershell
recovered_project/.venv/Scripts/python.exe -m pip check
```

Result:

```text
No broken requirements found.
```

**Dependency conflicts: none reported by pip.**

## 5. Third-party import smoke test

The smoke test imported only the nine approved third-party roots. It did not import any recovered module or invoke package functionality beyond import/version metadata lookup.

| Import root | Resolved distribution/version | Result |
|---|---|:---:|
| `nicegui` | `nicegui 2.23.3` | PASS |
| `fastapi` | `fastapi 0.116.1` | PASS |
| `loguru` | `loguru 0.7.3` | PASS |
| `requests` | `requests 2.32.5` | PASS |
| `getmac` | `getmac 0.9.2` | PASS |
| `psutil` | `psutil 7.0.0` | PASS |
| `selenium` | `selenium 4.35.0` | PASS |
| `webdriver_manager` | `webdriver-manager 4.0.2` | PASS |
| `certifi` | `certifi 2025.8.3` | PASS |

Result: **9 / 9 imports passed**.

## 6. Project-local static and safe-import checks

The prior full AST audit remains authoritative:

- 40 Python files parsed and compiled;
- zero missing local modules;
- zero missing explicitly imported local symbols;
- zero circular-import strongly connected components.

Most local modules were intentionally not imported because their top-level imports or initialization can register NiceGUI routes, create managers, touch application state, or lead toward runtime behavior. In particular, `app.py`, `web.views.*`, routing/UI components, database/state managers, license manager, updater, scanner, and API-operation modules were excluded.

Three modules were selected after source/AST inspection showed no startup, network, database, subprocess, browser-launch, or filesystem-mutating operation at import time:

| Local module | Top-level behavior considered | Import result |
|---|---|:---:|
| `src.paths` | Imports and function definition only; `get_data_dir()` was not called | PASS |
| `src.cookie_utils` | Logger import, constant dictionaries, function definitions | PASS |
| `src.module.model` | Imports plus class/enum/dataclass definitions; no driver/service method called | PASS |

Result: **3 / 3 selected safe local imports passed**.

## 7. Runtime tools

### FFmpeg

`ffmpeg` was checked without installation:

```text
NOT_FOUND_IN_PATH
```

Status: **MISSING**. Media-processing functions are not ready.

### FFprobe

`ffprobe` was checked without installation:

```text
NOT_FOUND_IN_PATH
```

Status: **MISSING**. Media-duration probing is not ready.

### Chrome/Chromium

Chrome was not exposed through a simple `Get-Command chrome`, but static inspection of common Windows install locations and App Paths found:

```text
Path: C:\Program Files\Google\Chrome\Application\chrome.exe
ProductVersion: 151.0.7922.174
FileVersion: 151.0.7922.174
```

The matching Windows App Paths registry entry points to the same file. Chrome was not launched.

Status: **FOUND**.

### ChromeDriver / webdriver-manager

No pre-provisioned `chromedriver` was found in `PATH`. The recovered code calls `ChromeDriverManager().install()` when constructing a driver, so a driver would be resolved from cache or downloaded at runtime. That code was not called and no browser session was created.

Status: **DEFERRED TO RUNTIME; NOT TESTED**.

## 8. Tkinter

Requested check:

```powershell
recovered_project/.venv/Scripts/python.exe -c "import tkinter; print(tkinter.TkVersion)"
```

Result:

```text
ModuleNotFoundError: No module named 'tkinter'
```

The original installed PyInstaller payload contains `_tkinter.pyd`, `tcl86t.dll`, and `tk86t.dll`, but the clean venv is based on the CPython embeddable distribution and does not expose a usable standard-library `tkinter` package. File-dialog functionality in `web/components/common.py` is therefore not ready in this environment.

Status: **MISSING**.

## 9. VERSION installation

After reconfirming the original payload evidence, `recovery_notes/VERSION.proposed` was copied logically to:

```text
recovered_project/VERSION
```

Installed text after whitespace stripping:

```text
v1.0.0
```

The updater logic was not modified.

Status: **PRESENT / EVIDENCE-CONFIRMED**.

## 10. Environment conclusion

Python package readiness is successful: the CPython 3.12.10 venv exists, all nine pinned requirements and their transitives installed, `pip check` is clean, and all nine third-party imports pass.

The environment is not yet ready for a full application startup because `ffmpeg`, `ffprobe`, and `tkinter` are missing. Chrome is present, but ChromeDriver/browser startup remains intentionally untested. Transitive dependencies are compatible according to pip but are not fully locked to original PyInstaller versions.

## Final summary

```text
Python version: CPython 3.12.10 (64-bit)
venv created: YES — recovered_project/.venv
requirements installed: YES — 9/9 direct pins, 0 failures; 66 frozen distributions excluding pip
pip check: PASS — No broken requirements found
dependency imports: PASS — 9/9 approved third-party imports
ffmpeg: MISSING — not found in PATH
ffprobe: MISSING — not found in PATH
Chrome: FOUND — 151.0.7922.174 at C:\Program Files\Google\Chrome\Application\chrome.exe
tkinter: FAIL — ModuleNotFoundError in the clean venv
VERSION: PRESENT — recovered_project/VERSION = v1.0.0
Environment status: DEPENDENCY-READY / RUNTIME-INCOMPLETE — do not start full application until ffmpeg, ffprobe, and tkinter are resolved
```
