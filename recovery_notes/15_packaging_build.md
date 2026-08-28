# 15 — Windows EXE and Installer Packaging

## Outcome

The recovered application was packaged as a Windows x86-64 PyInstaller
`onedir` distribution and wrapped in an Inno Setup installer.

```text
PyInstaller: 6.22.2
Python: CPython 3.12.14 x64
Inno Setup: 6.7.3
Application version: v1.0.0
```

Final installer:

```text
recovered_project/installer_dist/TVAutomation_Setup_v1.0.0.exe
Size: 55,699,554 bytes
SHA-256: 2098226561EDD9211DEFA6BC2E5A0E7EABE50DE661E145F00DE5B615755F019D
```

The installer is not code-signed. Windows may therefore display an Unknown
Publisher or SmartScreen warning until it is signed with a trusted Authenticode
certificate.

## Build inputs

- `recovered_project/TV Automation.spec`
- `recovered_project/TV Automation.iss`
- `recovered_project/build_hooks/runtime_path.py`
- `recovered_project/assets/logo.ico`
- `recovered_project/requirements-build.txt`

The PyInstaller specification includes NiceGUI data and metadata, certifi's CA
bundle, Tcl/Tk, the required Uvicorn/Engine.IO hidden imports, `VERSION`, and a
workspace-local FFmpeg/FFprobe binary dependency closure.

## Rebuild commands

From the workspace root in PowerShell:

```powershell
recovered_project\.venv\Scripts\python.exe -m pip install -r recovered_project\requirements-build.txt
recovered_project\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean "recovered_project\TV Automation.spec"
work\tools\inno_setup_6\ISCC.exe "recovered_project\TV Automation.iss"
```

The resulting unpacked application is under:

```text
recovered_project/dist/TV Automation/
```

## Verification

The unpacked distribution contains 1,575 files and approximately 177.5 MiB.
Its controlled startup test passed with browser auto-opening disabled:

- NiceGUI started on the configured loopback address and port;
- `/auth` returned HTTP 200;
- all five sampled NiceGUI assets returned HTTP 200;
- bundled `ffmpeg.exe` and `ffprobe.exe` both reported version 8.1.2;
- the server process was stopped after the test.

The final installer was then tested outside the restricted sandbox using a
workspace-local destination:

```text
Install exit code: 0
Installed files: 1,577
Main executable: present
FFmpeg: present
FFprobe: present
VERSION: v1.0.0
Uninstall exit code: 0
Install directory remaining after uninstall: no
```

No Selenium, upload, deletion, updater, or media workflow was invoked during
packaging verification. Keygen network access was deliberately blocked during
the packaged startup smoke test, so a real end-user key activation remains a
separate acceptance test.

## Distribution notes

- Publish the setup executable as a GitHub Release asset rather than committing
  generated `dist/`, `build/`, or `installer_dist/` trees to source control.
- Code-sign the setup executable before broad distribution.
- This build uses `console=True` to retain diagnostic logs. Switch to
  `console=False` in the spec only after a separately verified release build.
- Inno Setup 6.7.3 reports non-commercial-use licensing terms; obtain the
  appropriate license if this installer is distributed commercially.
