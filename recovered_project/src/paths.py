# RECOVERED: reconstructed from CPython 3.12 bytecode
"""Isolated platform-specific storage for this TV Automation build."""

import os
import platform
import json
import time
from pathlib import Path


APP_NAMESPACE_ID = "7F47B95D-6FD8-4A87-B2F8-9B0CE6A91D42"
APP_DATA_NAMESPACE = "TVAutomation-7F47B95D"
FIRST_RUN_SCHEMA = 1


def get_data_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    # Never migrate from or fall back to the legacy "TVAutomation" folder.
    data_dir = base / APP_DATA_NAMESPACE
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_history_dir() -> Path:
    history_dir = get_data_dir() / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir


def initialize_first_run() -> bool:
    """Initialize only this build's namespace and return True on first launch."""
    data_dir = get_data_dir()
    marker = data_dir / "first_run.json"
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
        if (
            payload.get("namespace_id") == APP_NAMESPACE_ID
            and payload.get("schema") == FIRST_RUN_SCHEMA
        ):
            return False
    except (OSError, ValueError, AttributeError, TypeError):
        pass

    # These exact files are all inside the new namespace. The legacy AppData
    # folder is intentionally never inspected, migrated, modified, or deleted.
    runtime_name = f"runtime-{APP_NAMESPACE_ID.lower()}"
    reset_files = (
        "channels.db",
        "channels.db-wal",
        "channels.db-shm",
        "app_state.db",
        "app_state.db-wal",
        "app_state.db-shm",
        "license.json",
        f"{runtime_name}.json",
        f"{runtime_name}.tmp",
    )
    for filename in reset_files:
        try:
            (data_dir / filename).unlink(missing_ok=True)
        except OSError:
            pass

    marker_tmp = marker.with_suffix(".tmp")
    marker_tmp.write_text(
        json.dumps(
            {
                "namespace_id": APP_NAMESPACE_ID,
                "schema": FIRST_RUN_SCHEMA,
                "initialized_at": int(time.time()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    marker_tmp.replace(marker)
    return True
