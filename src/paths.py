# RECOVERED: reconstructed from CPython 3.12 bytecode
"""Platform-specific data directory for TV Automation."""

import os
import platform
from pathlib import Path


def get_data_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    data_dir = base / "TVAutomation"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
