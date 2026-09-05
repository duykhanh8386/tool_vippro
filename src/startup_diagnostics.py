"""Persistent diagnostics for failures before the NiceGUI page is available."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from loguru import logger

from src.paths import get_data_dir


_LOG_PATH: Path | None = None


def configure_startup_diagnostics() -> Path | None:
    """Write startup errors to AppData, including errors hidden by a frozen EXE."""
    global _LOG_PATH
    if _LOG_PATH is not None:
        return _LOG_PATH
    try:
        log_dir = get_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        _LOG_PATH = log_dir / "startup.log"
        if getattr(sys, "frozen", False):
            logger.remove(0)  # Do not leave a black console window for the user.
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
    except Exception:
        # Diagnostics must never prevent the app from starting.
        _LOG_PATH = None
    return _LOG_PATH


def startup_log_path() -> Path | None:
    return _LOG_PATH


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
    logger.opt(exception=exc).critical("Tuất Videos failed during startup")
    log_path = startup_log_path()
    detail = f"{type(exc).__name__}: {exc}".strip()
    message = "Tool không thể khởi động."
    if detail:
        message += f"\n\nLỗi: {detail}"
    if log_path:
        message += f"\n\nGửi file log này để kiểm tra:\n{log_path}"
    show_startup_error(message)
