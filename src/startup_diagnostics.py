"""Persistent diagnostics for failures before the NiceGUI page is available."""

from __future__ import annotations

import importlib
import os
import sys
import threading
import traceback
from pathlib import Path

from loguru import logger

from src.paths import get_data_dir


_LOG_PATH: Path | None = None
_NULL_STREAMS: list[object] = []


def _append_raw_log(message: str) -> None:
    """Record bootstrap failures even when Loguru itself cannot initialize."""
    global _LOG_PATH
    try:
        if _LOG_PATH is None:
            log_dir = get_data_dir() / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            _LOG_PATH = log_dir / "startup.log"
        with _LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(message.rstrip() + "\n")
    except Exception:
        pass


def configure_startup_diagnostics() -> Path | None:
    """Write startup errors to AppData, including errors hidden by a frozen EXE."""
    global _LOG_PATH
    if _LOG_PATH is not None:
        return _LOG_PATH
    try:
        _append_raw_log("[bootstrap] Initializing startup diagnostics")
        if (
            getattr(sys, "frozen", False)
            and (sys.stdout is None or sys.stderr is None)
        ):
            try:
                logger.remove(0)
            except ValueError:
                pass
        logger.add(
            _LOG_PATH,
            level="DEBUG",
            rotation="2 MB",
            retention=3,
            encoding="utf-8",
            backtrace=True,
            diagnose=False,
        )
        sys.excepthook = _log_unhandled_exception
        threading.excepthook = _log_unhandled_thread_exception
        logger.info("Startup diagnostics initialized: {}", _LOG_PATH)
    except Exception as exc:
        # Diagnostics must never prevent the app from starting.
        _append_raw_log(
            f"[bootstrap] Could not configure Loguru: {type(exc).__name__}: {exc}"
        )
    return _LOG_PATH


def startup_log_path() -> Path | None:
    return _LOG_PATH


def ensure_standard_streams() -> None:
    """Give Uvicorn valid streams when PyInstaller hides the console window.

    With ``console=False`` PyInstaller sets ``sys.stdout`` and ``sys.stderr``
    to ``None``. Uvicorn calls ``.isatty()`` while configuring its formatter,
    which otherwise makes the application exit before its local web server
    starts.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is not None:
            continue
        stream = open(os.devnull, "w", encoding="utf-8")
        _NULL_STREAMS.append(stream)
        setattr(sys, name, stream)


def quarantine_invalid_brotlicffi() -> bool:
    """Ignore a stale or incomplete optional Brotli backend.

    ``urllib3`` imports ``brotlicffi`` before its alternative backends and
    assumes that a successful import exposes ``error`` and ``Decompressor``.
    An old installation can leave an empty ``brotlicffi`` package in the
    PyInstaller runtime directory, causing NiceGUI to fail during import.
    Marking only that invalid optional module as unavailable lets urllib3 use
    another backend or continue without Brotli support.
    """
    try:
        module = importlib.import_module("brotlicffi")
    except ImportError:
        return False
    except Exception as exc:
        sys.modules["brotlicffi"] = None
        logger.warning("Disabled broken optional brotlicffi backend: {}", exc)
        return True

    error_type = getattr(module, "error", None)
    decompressor = getattr(module, "Decompressor", None)
    valid_error = isinstance(error_type, type) and issubclass(error_type, BaseException)
    if valid_error and callable(decompressor):
        return False

    sys.modules["brotlicffi"] = None
    logger.warning(
        "Disabled incomplete optional brotlicffi backend from {}",
        getattr(module, "__file__", "unknown location"),
    )
    return True


def _log_unhandled_exception(exc_type, exc_value, traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        return
    logger.opt(exception=(exc_type, exc_value, traceback)).critical(
        "Unhandled startup exception"
    )


def _log_unhandled_thread_exception(args: threading.ExceptHookArgs) -> None:
    if args.exc_type and issubclass(args.exc_type, KeyboardInterrupt):
        return
    logger.opt(
        exception=(args.exc_type, args.exc_value, args.exc_traceback)
    ).critical("Unhandled exception in thread {}", args.thread.name if args.thread else "unknown")


def show_startup_error(message: str) -> None:
    """Show an actionable Windows error only for the installed executable."""
    logger.error("{}", message)
    if not getattr(sys, "frozen", False) or os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            message,
            "Tuất Videos - không thể khởi động",
            0x10,
        )
    except Exception:
        # The detailed error remains in startup.log even if the dialog cannot open.
        pass


def report_startup_failure(exc: BaseException) -> None:
    """Log and display the final error when the server cannot be initialized."""
    _append_raw_log(
        "[bootstrap] Startup failed:\n"
        + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    )
    logger.opt(exception=exc).critical("Tuất Videos failed during startup")
    log_path = startup_log_path()
    detail = f"{type(exc).__name__}: {exc}".strip()
    message = "Tool không thể khởi động."
    if detail:
        message += f"\n\nLỗi: {detail}"
    if log_path:
        message += f"\n\nGửi file log này để kiểm tra:\n{log_path}"
    show_startup_error(message)
