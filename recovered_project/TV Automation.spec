from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata


project_root = Path(SPECPATH).resolve()
media_bin = project_root / "vendor" / "ffmpeg" / "bin"
chromedriver_bin = project_root / "vendor" / "chromedriver" / "chromedriver.exe"


def collect_media_binaries():
    """Collect the project-vendored static FFmpeg tools."""
    roots = [media_bin / "ffmpeg.exe", media_bin / "ffprobe.exe"]
    missing = [str(path) for path in roots if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing media tools; expected workspace-local files: " + ", ".join(missing)
        )

    return [(str(path), "tools/ffmpeg") for path in roots]


def collect_chromedriver():
    if not chromedriver_bin.is_file():
        raise FileNotFoundError(f"Missing bundled ChromeDriver: {chromedriver_bin}")
    return [(str(chromedriver_bin), "tools")]


datas = [
    (str(project_root / "VERSION"), "."),
    (str(project_root / "vendor" / "ffmpeg" / "LICENSE"), "licenses/ffmpeg"),
    (str(project_root / "vendor" / "ffmpeg" / "README.txt"), "licenses/ffmpeg"),
    (str(project_root / "vendor" / "chromedriver" / "LICENSE.chromedriver"), "licenses/chromedriver"),
    (str(project_root / "vendor" / "chromedriver" / "THIRD_PARTY_NOTICES.chromedriver"), "licenses/chromedriver"),
    *collect_data_files("nicegui"),
    *collect_data_files("certifi"),
    *copy_metadata("nicegui"),
]

hiddenimports = [
    "engineio.async_drivers.asgi",
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.websockets_sansio_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
]

a = Analysis(
    [str(project_root / "app.py")],
    pathex=[str(project_root)],
    binaries=collect_media_binaries() + collect_chromedriver(),
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_root / "build_hooks" / "runtime_path.py")],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TV Automation",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "logo.ico"),
    contents_directory="_internal",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TV Automation",
)
