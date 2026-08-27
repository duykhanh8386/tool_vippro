# 08 — Dependency Manifest and Source Runtime Reconstruction

## Scope and safety

This audit continues from the existing recovered source and extraction outputs.

- No executable, DLL/PYD, recovered module, or recovered application was run.
- No package, browser, driver, or media tool was downloaded or installed.
- Package bytecode was only deserialized/disassembled statically; recovered code objects were never executed.
- No recovered Python module or updater logic was changed.

Outputs:

- `recovered_project/requirements.txt`
- `recovery_notes/VERSION.proposed`
- this evidence report

## 1. Manifest reconstruction result

Nine distributions are included in `requirements.txt`: eight required by unconditional application imports, plus `certifi`. The application treats `certifi` as optional in the updater, but NiceGUI 2.23.3 declares it as a dependency and the original bundle contains it, so retaining its evidenced version best reconstructs the source environment.

All nine manifest versions have static evidence. No version was guessed.

| Package name in manifest | Import root | Version | Evidence |
|---|---|---:|---|
| `nicegui` | `nicegui` | `2.23.3` | `nicegui-2.23.3.dist-info/METADATA`: `Name: nicegui`, `Version: 2.23.3` |
| `fastapi` | `fastapi` | `0.116.1` | Static `fastapi/__init__.pyc` assignment: `__version__ = "0.116.1"` |
| `loguru` | `loguru` | `0.7.3` | Static `loguru/__init__.pyc` assignment |
| `requests` | `requests` | `2.32.5` | Static `requests/__version__.pyc` assignment |
| `getmac` | `getmac` | `0.9.2` | Static `getmac/getmac.pyc` assignment |
| `psutil` | `psutil` | `7.0.0` | Static `psutil/__init__.pyc` assignment |
| `selenium` | `selenium` | `4.35.0` | Static `selenium/__init__.pyc` assignment |
| `webdriver-manager` | `webdriver_manager` | `4.0.2` | Static `webdriver_manager/__init__.pyc` assignment |
| `certifi` | `certifi` | `2025.8.3` | Static value is `2025.08.03`; `2025.8.3` is its PEP 440 canonical spelling |

### Why two evidence types were used

The installed payload retains distribution metadata selectively, not universally. NiceGUI itself obtains `__version__` through `importlib.metadata.version("nicegui")`, and its retained `dist-info/METADATA` provides the authoritative value. The other direct distributions have no retained `dist-info` directory, but their package-owned bytecode contains an explicit static `__version__` assignment. Those assignments are direct evidence from the bundled package code, not inferred from current releases.

## 2. Application usage by dependency

The locations below come from the complete recovered-project AST import graph.

### `nicegui`

Used by:

```text
app.py
src/route_manager.py
web/nicegui_patches.py
web/components/add_audio_flow.py
web/components/audio.py
web/components/auth.py
web/components/common.py
web/components/delete_back_flow.py
web/components/delete_video.py
web/components/drawer.py
web/components/remove_audio.py
web/components/settings.py
web/components/studio.py
```

### `fastapi`

Used by `src/route_manager.py` for `Request`.

### `loguru`

Used by:

```text
src/channel_refresh.py
src/channel_scanner.py
src/cookie_utils.py
src/license_manager.py
src/module/audio_module.py
src/module/base.py
src/module/delete_video_module.py
src/module/list_videos_module.py
src/module/model.py
src/module/upload_video_module.py
src/route_manager.py
src/state_manager.py
src/updater.py
src/utils.py
web/components/add_audio_flow.py
web/components/audio.py
web/components/common.py
web/components/delete_back_flow.py
web/components/delete_video_controller.py
web/components/remove_audio.py
web/components/studio.py
```

### `requests`

Used by:

```text
src/channel_scanner.py
src/license_manager.py
src/module/audio_module.py
src/module/base.py
src/module/delete_video_module.py
src/module/list_videos_module.py
src/module/upload_video_module.py
```

### `getmac`

Used by `src/license_manager.py` and `src/module/model.py`.

### `psutil`

Used by `src/module/model.py`.

### `selenium`

Used by `src/channel_scanner.py`, `src/module/model.py`, and `src/utils.py`.

### `webdriver-manager`

Imported by `src/module/model.py` and `src/utils.py`. The evidenced active call is in `src/utils.py`:

```python
Service(ChromeDriverManager().install())
```

### `certifi`

Imported inside a `try` block by `src/updater.py` to provide a CA bundle. The updater falls back to `ssl.create_default_context()` if it is unavailable. It is nevertheless retained in the manifest because:

1. the extracted package tree contains `certifi` and `certifi/cacert.pem`; and
2. NiceGUI 2.23.3 metadata declares `certifi >=2024.07.04`.

## 3. PyInstaller metadata inventory

### Retained `dist-info`

The installed PyInstaller payload at `recovery_staging/installer_payload/_internal/` contains these nine metadata directories:

| Distribution | Version | `METADATA` | `RECORD` |
|---|---:|:---:|:---:|
| `attrs` | `25.3.0` | Yes | Yes |
| `click` | `8.2.1` | Yes | Yes |
| `itsdangerous` | `2.2.0` | Yes | Yes |
| `MarkupSafe` | `3.0.2` | Yes | Yes |
| `nicegui` | `2.23.3` | Yes | Yes |
| `prompt_toolkit` | `3.0.52` | Yes | Yes |
| `trio` | `0.30.0` | Yes | Yes |
| `websockets` | `15.0.1` | Yes | Yes |
| `importlib_metadata` (vendored under setuptools) | `8.7.1` | Yes | Yes |

Only `nicegui` is directly imported by application source. The other eight are transitive, tooling, or vendored packages, so they were not promoted to top-level requirements merely because PyInstaller bundled them. `pip` should resolve NiceGUI's declared dependency set from the pinned top-level version.

### NiceGUI dependency evidence

The retained NiceGUI metadata declares Python `>=3.8,<4.0` and dependencies including FastAPI, aiofiles, aiohttp, certifi, docutils, h11, httpx, itsdangerous, Jinja2, markdown2, orjson on supported machines, python-engineio, python-multipart, python-socketio, Starlette, typing-extensions, Uvicorn, vbuild, watchfiles, and others behind optional extras.

The reconstructed manifest pins application-direct imports. It is intentionally not presented as a complete hash-locked copy of every transitive wheel: most bundled distributions do not retain `dist-info`, so their exact versions cannot all be proven from standardized metadata without a much broader package-by-package bytecode audit.

## 4. External runtime tools

| Runtime/tool | Source behavior | Audit result |
|---|---|---|
| `ffmpeg` | Called by `src/utils.py` for audio/video generation, muxing, overlay, copy, and re-encode paths | **Required for media features; not found in current `PATH`; not bundled** |
| `ffprobe` | Called by `src/utils.py` to read media duration | **Required for media probing; not found in current `PATH`; not bundled** |
| Chrome/Chromium | Selenium creates a Chrome WebDriver | **Required for browser/scanner workflows; not detected under common `PATH` names** |
| ChromeDriver | Passed to Selenium via `Service(...)` | **Not bundled; `webdriver-manager` installs/downloads or reuses a cached compatible driver at runtime** |
| Tcl/Tk | `tkinter` file dialogs are used by `web/components/common.py` | **Python/platform runtime component; present in the original payload, but a clean Python installation must provide it** |

### `webdriver-manager` behavior

The recovered code does not point to a fixed local `chromedriver` executable. Each driver construction in `src/utils.py` evaluates `ChromeDriverManager().install()` and passes the returned path into Selenium's `Service`.

Operational consequences:

- first use normally requires network access unless a compatible driver already exists in webdriver-manager's cache;
- a Chrome/Chromium browser must still be installed separately;
- browser/driver compatibility is a runtime concern;
- offline readiness is not established by `pip install -r requirements.txt` alone.

No download or driver installation was attempted in this audit.

## 5. `VERSION` resource reconstruction

`recovered_project/VERSION` is absent, but the installed PyInstaller payload retains the original resource:

```text
recovery_staging/installer_payload/_internal/VERSION
```

Static evidence:

| Property | Value |
|---|---|
| Length | 6 bytes |
| Hex | `76 31 2e 30 2e 30` |
| Text | `v1.0.0` |
| SHA-256 | `2485f4d55aae6c5b073114bc4c4b1907c0abae14166281beee7d93f76ebf41fc` |

The updater expects UTF-8 text, calls `.strip()`, accepts an optional leading `v`, extracts numeric components separated by dots, and pads missing components to three parts. The evidenced `v1.0.0` therefore exactly matches the expected format.

The proposal is stored separately as `recovery_notes/VERSION.proposed`; it was deliberately not installed as `recovered_project/VERSION`, and updater logic was not changed. If approved later, its intended destination is:

```text
recovered_project/VERSION
```

## 6. Clean environment checklist

The following is a proposed setup sequence, **not executed during this audit**:

```powershell
cd recovered_project
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Before any startup test:

- [ ] Confirm CPython 3.12 is being used.
- [ ] Install `ffmpeg` and `ffprobe` and confirm both resolve from `PATH`.
- [ ] Install Chrome/Chromium and record its version/path.
- [ ] Allow webdriver-manager network/cache access, or pre-provision a compatible driver through a separately approved process.
- [ ] Confirm `tkinter`/Tcl/Tk is available.
- [ ] Review and, if approved, copy `VERSION.proposed` to `recovered_project/VERSION`.
- [ ] Confirm write access to application-data, temporary, and chosen output directories.
- [ ] Confirm port `8081` is available.
- [ ] Only then perform a separately authorized import/startup smoke test.

## 7. Readiness conclusion

The Python dependency manifest is now reconstructable with evidenced pins for all nine entries. It is suitable for a future clean-environment installation attempt, but this step has not validated wheel availability, transitive resolution, binary compatibility, browser integration, network services, or application startup.

Environment readiness remains **PARTIAL** because the virtual environment has not been created, dependencies have not been installed, required media tools are missing from `PATH`, Chrome/Chromium is not detected, and ChromeDriver availability is deferred to webdriver-manager runtime behavior.

## Final summary

```text
Python dependencies found: 9 manifest entries (8 unconditional application dependencies + certifi)
Versions recovered: 9 / 9 manifest entries
Versions unknown: 0 manifest entries; exact full transitive lock remains unknown
External tools required: ffmpeg, ffprobe, Chrome/Chromium, ChromeDriver (managed at runtime); Tcl/Tk platform support for file dialogs
Missing runtime prerequisites: ffmpeg, ffprobe, Chrome/Chromium not detected; ChromeDriver not pre-provisioned; venv/dependencies not installed
Environment readiness: PARTIAL — manifest and VERSION evidence recovered, installation and startup intentionally not performed
```
