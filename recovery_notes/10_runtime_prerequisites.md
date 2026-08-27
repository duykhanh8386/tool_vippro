# 10 — Runtime Prerequisites

## Scope and safety

This step completed and verified the local runtime prerequisites without starting the recovered application.

- `app.py` and `ui.run()` were not executed.
- Selenium and ChromeDriver were not started.
- No application network API was called.
- No upload, deletion, updater, database, or media-processing operation was run.
- No Python/PYD/DLL file was copied or patched from the PyInstaller bundle.
- Recovered application source was not modified.

## 1. Full CPython 3.12 and Tkinter

The former `recovered_project/.venv` was based on the CPython 3.12.10 embeddable distribution. That distribution had no `venv` module or usable `tkinter` package.

A workspace-local full CPython runtime was installed with Conda `defaults` at:

```text
work/tools/python312_full
```

The initial request for the exact patch `python=3.12.10` could not be solved because that build is no longer present in the configured `defaults` channel. No dependency pin was changed. Conda was then constrained to the requested minor series `python=3.12` and resolved:

| Runtime component | Resolved version |
|---|---:|
| CPython | `3.12.14` |
| Tcl/Tk | `8.6.15` package / `TkVersion 8.6` |
| pip in final venv | `26.2.1` |

The main environment was recreated at its original path from this full runtime:

```text
recovered_project/.venv
```

The previous embeddable-based environment was preserved, rather than deleted, at:

```text
recovered_project/.venv_embeddable_backup
```

The exact nine pinned requirements were reinstalled into the new `.venv`; no requirement was edited.

Final Tkinter check:

```powershell
recovered_project/.venv/Scripts/python.exe -c "import tkinter; print(tkinter.TkVersion)"
```

Result:

```text
8.6
```

**tkinter: PASS.**

## 2. FFmpeg and FFprobe

Because the Windows `winget` App Installer alias was unavailable and Chocolatey/Scoop were not installed, FFmpeg was installed workspace-locally through the same Conda runtime prefix.

Resolved files:

```text
work/tools/python312_full/Library/bin/ffmpeg.exe
work/tools/python312_full/Library/bin/ffprobe.exe
```

Both tools are version `8.1.2`.

To make the venv and media tools available together without changing application source or global user/system `PATH`, this activation helper was added:

```text
recovered_project/activate_runtime.ps1
```

Usage for a future separately authorized startup session:

```powershell
. .\recovered_project\activate_runtime.ps1
```

The script activates `recovered_project/.venv` and prepends the workspace-local FFmpeg directory to that shell's `PATH`.

### FFmpeg verification

After activating the runtime environment:

```text
path=C:\Users\DucHieu\Documents\mmo\work\tools\python312_full\Library\bin\ffmpeg.exe
ffmpeg version 8.1.2
built with clang version 22.1.2
```

**ffmpeg: PASS.**

### FFprobe verification

After activating the runtime environment:

```text
path=C:\Users\DucHieu\Documents\mmo\work\tools\python312_full\Library\bin\ffprobe.exe
ffprobe version 8.1.2
built with clang version 22.1.2
```

**ffprobe: PASS.**

The version commands only queried tool metadata; no input media was opened or processed.

## 3. Chrome

Chrome was reconfirmed by reading the installed executable's Windows version metadata. Chrome was not launched.

```text
Path: C:\Program Files\Google\Chrome\Application\chrome.exe
ProductVersion: 151.0.7922.174
```

The Windows App Paths registration points to the same executable.

**Chrome: PASS / FOUND.**

ChromeDriver remains intentionally unstarted. The recovered code delegates driver resolution to `ChromeDriverManager().install()` when Selenium is actually invoked; that network/cache/browser step is outside this prerequisite-only audit.

## 4. Python dependency consistency

Final environment:

```text
Python 3.12.14
Executable: recovered_project/.venv/Scripts/python.exe
Base prefix: work/tools/python312_full
```

`pip check` result:

```text
No broken requirements found.
```

The nine approved third-party import roots were also rechecked in the final `.venv`:

```text
nicegui, fastapi, loguru, requests, getmac, psutil,
selenium, webdriver_manager, certifi
```

Result: **9 / 9 imports passed** at the manifest-pinned versions.

**pip check: PASS.**

## 5. Runtime readiness

All prerequisites requested in this step are now present and verified:

- full CPython 3.12 runtime: present;
- Tkinter/Tcl/Tk: import succeeds;
- FFmpeg: resolves and reports its version after runtime activation;
- FFprobe: resolves and reports its version after runtime activation;
- Chrome: installed and version confirmed;
- Python dependencies: internally consistent and importable.

This establishes prerequisite readiness only. Application startup, route registration behavior, UI behavior, Selenium/ChromeDriver operation, external services, and media workflows remain untested by design.

## Final summary

```text
tkinter: PASS — Tk 8.6 under full CPython 3.12.14
ffmpeg: PASS — 8.1.2 at work/tools/python312_full/Library/bin/ffmpeg.exe
ffprobe: PASS — 8.1.2 at work/tools/python312_full/Library/bin/ffprobe.exe
Chrome: PASS — 151.0.7922.174 at C:\Program Files\Google\Chrome\Application\chrome.exe
pip check: PASS — No broken requirements found
Runtime status: READY FOR A SEPARATELY AUTHORIZED CONTROLLED STARTUP TEST — full application not started in this step
```
