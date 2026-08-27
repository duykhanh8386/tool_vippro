"""Launch the recovered app with smoke-test-only NiceGUI run settings.

This harness does not modify application source. It prevents browser auto-open,
disables the reload subprocess, and binds an isolated loopback address so a
stale browser tab on localhost:8081 cannot reconnect to protected routes.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

from nicegui import ui


_original_run = ui.run


def _controlled_run(**kwargs):
    kwargs["show"] = False
    kwargs["reload"] = False
    kwargs["host"] = "127.0.0.2"
    return _original_run(**kwargs)


ui.run = _controlled_run

project_dir = Path(__file__).resolve().parents[1] / "recovered_project"
sys.path.insert(0, str(project_dir))
runpy.run_path(str(project_dir / "app.py"), run_name="__main__")
