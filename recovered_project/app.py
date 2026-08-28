# RECOVERED: reconstructed from CPython 3.12 bytecode
import os
import sys
from pathlib import Path

from src.paths import initialize_first_run
from src.runtime_instance import (
    APP_PORT_END,
    APP_PORT_START,
    acquire_single_instance,
    choose_available_port,
    open_running_instance,
    register_runtime_cleanup,
    RUNTIME_HEALTH_PATH,
    runtime_health_payload,
    start_runtime_publisher,
)

_is_frozen = getattr(sys, "frozen", False)
try:
    _requested_port = int(os.environ.get("TVAUTOMATION_PORT", str(APP_PORT_START)))
except ValueError:
    _requested_port = APP_PORT_START
if not APP_PORT_START <= _requested_port <= APP_PORT_END:
    print(
        f"Ignoring port {_requested_port}; this app only uses "
        f"{APP_PORT_START}-{APP_PORT_END}.",
        flush=True,
    )
    _requested_port = APP_PORT_START
if _is_frozen:
    if not acquire_single_instance():
        if not open_running_instance(_requested_port):
            print(
                "Another instance is running, but its verified URL is not ready.",
                flush=True,
            )
        raise SystemExit(0)

_is_first_run = initialize_first_run()
if _is_first_run:
    print(
        "First run initialized. Sign in and add channels for this app.",
        flush=True,
    )

from nicegui import app, ui

from src.route_manager import router
from src.task_runtime import stop_all_runs
from web.nicegui_patches import apply_patches
from web.theme import install_theme
from web.views import *

apply_patches()
install_theme()
_resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
_brand_assets = _resource_root / "assets"
_brand_icon = _brand_assets / "logo.png"
if _brand_assets.is_dir():
    app.add_static_files("/tuat-videos-assets", str(_brand_assets))
router.setup_routes()
app.on_shutdown(stop_all_runs)


@app.get(RUNTIME_HEALTH_PATH, include_in_schema=False)
def runtime_health():
    return runtime_health_payload()

_show_browser = os.environ.get("TVAUTOMATION_SHOW_BROWSER", "1").lower() not in {
    "0",
    "false",
    "no",
}
_host = os.environ.get("TVAUTOMATION_HOST", "127.0.0.1")
try:
    _port = choose_available_port(_host, _requested_port, APP_PORT_END)
except RuntimeError as exc:
    print(str(exc), flush=True)
    raise SystemExit(1) from exc
if _is_frozen:
    register_runtime_cleanup()
if _port != _requested_port:
    _browser_host = "127.0.0.1" if _host in {"0.0.0.0", "::"} else _host
    print(
        f"Port {_requested_port} is busy; Tuất Videos will use "
        f"http://{_browser_host}:{_port}",
        flush=True,
    )

if _is_frozen:
    start_runtime_publisher(
        _host,
        _port,
        show_browser=_show_browser,
        persist_runtime=True,
    )

try:
    ui.run(
        title="Tuất Videos",
        favicon=_brand_icon if _brand_icon.is_file() else "🐶",
        host=_host,
        port=_port,
        show=False if _is_frozen else _show_browser,
        reconnect_timeout=120,
        reload=not _is_frozen,
    )
except Exception as exc:
    if _is_frozen:
        from src.runtime_instance import clear_runtime_file

        clear_runtime_file()
    print(f"Tuất Videos server failed to start: {exc}", flush=True)
    raise
