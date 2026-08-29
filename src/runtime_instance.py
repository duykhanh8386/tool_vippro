"""Single-instance and local-port helpers for the desktop-packaged app."""

from __future__ import annotations

import atexit
import json
import os
import socket
import threading
import time
import webbrowser
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from loguru import logger

from src.paths import APP_NAMESPACE_ID, get_data_dir


APP_INSTANCE_ID = APP_NAMESPACE_ID
_MUTEX_NAME = f"Local\\TVAutomation-Isolated-{APP_INSTANCE_ID}"
_RUNTIME_FILE = get_data_dir() / f"runtime-{APP_INSTANCE_ID.lower()}.json"
_mutex_handle = None

APP_PORT_START = 18081
APP_PORT_END = 18100
RUNTIME_HEALTH_PATH = f"/__tvautomation_{APP_INSTANCE_ID.lower()}_health"


def acquire_single_instance() -> bool:
    """Return False when another packaged application instance is running."""
    global _mutex_handle
    if os.name != "nt":
        return True

    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_bool
    handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if not handle:
        logger.warning("Không thể tạo mutex single-instance; tiếp tục khởi động.")
        return True
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return False

    _mutex_handle = handle
    # We own the mutex, so an existing file can only be stale runtime state.
    clear_runtime_file()

    def _release_mutex() -> None:
        global _mutex_handle
        if _mutex_handle:
            kernel32.CloseHandle(_mutex_handle)
            _mutex_handle = None

    atexit.register(_release_mutex)
    return True


def _can_bind(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind((host, port))
        return True
    except OSError:
        return False


def choose_available_port(
    host: str,
    preferred: int = APP_PORT_START,
    max_port: int = APP_PORT_END,
) -> int:
    """Use only the dedicated Tuất Videos port range."""
    if not APP_PORT_START <= preferred <= APP_PORT_END:
        preferred = APP_PORT_START
    max_port = min(max(max_port, preferred), APP_PORT_END)
    for port in range(preferred, max_port + 1):
        if _can_bind(host, port):
            return port
    raise RuntimeError(
        f"No free Tuất Videos port in range {preferred}-{max_port}."
    )


def save_runtime_url(host: str, port: int) -> str:
    """Persist the URL used by a later second-instance launch."""
    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{browser_host}:{port}"
    try:
        runtime_tmp = _RUNTIME_FILE.with_suffix(".tmp")
        runtime_tmp.write_text(
            json.dumps(
                {
                    "instance_id": APP_INSTANCE_ID,
                    "pid": os.getpid(),
                    "url": url,
                }
            ),
            encoding="utf-8",
        )
        runtime_tmp.replace(_RUNTIME_FILE)
    except OSError as exc:
        logger.warning("Không lưu được runtime URL: {}", exc)
    return url


def runtime_health_payload() -> dict:
    return {"instance_id": APP_INSTANCE_ID, "pid": os.getpid()}


def _runtime_url_is_ready(url: str, timeout: float = 0.5) -> bool:
    try:
        request = Request(
            f"{url}{RUNTIME_HEALTH_PATH}",
            headers={"Cache-Control": "no-cache"},
        )
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("instance_id") == APP_INSTANCE_ID
    except (OSError, ValueError, AttributeError, TypeError):
        return False


def _wait_for_runtime_url(url: str, wait_seconds: float) -> bool:
    deadline = time.monotonic() + max(0.0, wait_seconds)
    while True:
        if _runtime_url_is_ready(url):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.1)


def start_runtime_publisher(
    host: str,
    port: int,
    *,
    show_browser: bool,
    persist_runtime: bool,
    wait_seconds: float = 30.0,
) -> threading.Thread:
    """Publish/open the URL only after this exact server responds successfully."""
    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{browser_host}:{port}"

    def _publish() -> None:
        if not _wait_for_runtime_url(url, wait_seconds):
            logger.error(
                "Tuất Videos server failed to become ready at {}; browser not opened.",
                url,
            )
            return
        if persist_runtime:
            save_runtime_url(browser_host, port)
        if show_browser:
            webbrowser.open(url)

    thread = threading.Thread(
        target=_publish,
        name="tuat-videos-runtime-publisher",
        daemon=True,
    )
    thread.start()
    return thread


def _read_runtime_url() -> str | None:
    try:
        data = json.loads(_RUNTIME_FILE.read_text(encoding="utf-8"))
        if data.get("instance_id") != APP_INSTANCE_ID:
            return None
        candidate = str(data.get("url") or "")
        parsed = urlsplit(candidate)
        if (
            parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost"}
            and parsed.port is not None
            and APP_PORT_START <= parsed.port <= APP_PORT_END
        ):
            return candidate
    except (OSError, ValueError, AttributeError, TypeError):
        return None
    return None


def open_running_instance(
    default_port: int = APP_PORT_START,
    *,
    wait_seconds: float = 15.0,
) -> bool:
    """Open only a verified URL published by this application's first instance."""
    del default_port  # Never guess a URL belonging to an unknown process.
    deadline = time.monotonic() + max(0.0, wait_seconds)
    url = _read_runtime_url()
    while (
        url is None or not _runtime_url_is_ready(url)
    ) and time.monotonic() < deadline:
        time.sleep(0.1)
        url = _read_runtime_url()
    if url is None or not _runtime_url_is_ready(url):
        logger.warning("No verified runtime URL found for instance {}", APP_INSTANCE_ID)
        return False
    if os.environ.get("TVAUTOMATION_SHOW_BROWSER", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }:
        webbrowser.open(url)
    return True


def clear_runtime_file() -> None:
    try:
        _RUNTIME_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def register_runtime_cleanup() -> None:
    atexit.register(clear_runtime_file)
