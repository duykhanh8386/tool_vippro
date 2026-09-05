"""Ownership-aware runtime resources for cancellable application jobs.

Every UI job gets its own :class:`TaskRunContext`.  Child processes, temporary
files and Selenium sessions are registered against that context, so stopping a
job can only touch resources created by that exact job.  No process-name based
discovery or global task killing is used here.
"""

from __future__ import annotations

import atexit
import contextvars
import subprocess
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import requests
from loguru import logger


class TaskStopped(RuntimeError):
    """Raised inside a worker when its owning UI job has been stopped."""

    def __init__(self, message: str = "Tác vụ đã dừng"):
        super().__init__(message)


_CURRENT_CONTEXT: contextvars.ContextVar[TaskRunContext | None] = (
    contextvars.ContextVar("tuat_videos_task_context", default=None)
)
_ACTIVE_CONTEXTS: dict[str, TaskRunContext] = {}
_ACTIVE_LOCK = threading.RLock()


class TaskRunContext:
    """Own all cancellable resources created by one run of one feature."""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.run_id = uuid.uuid4().hex
        self.stop_event = threading.Event()
        self._lock = threading.RLock()
        self._processes: dict[int, subprocess.Popen] = {}
        self._drivers: dict[int, Any] = {}
        self._cleanup_paths: set[Path] = set()
        self._closed = False
        with _ACTIVE_LOCK:
            _ACTIVE_CONTEXTS[self.run_id] = self

    @property
    def stopped(self) -> bool:
        return self.stop_event.is_set()

    def checkpoint(self) -> None:
        if self.stopped:
            raise TaskStopped()

    def wait(self, seconds: float) -> None:
        """Wait interruptibly; raise immediately when stop is requested."""
        if self.stop_event.wait(max(0.0, seconds)):
            raise TaskStopped()

    def register_process(self, process: subprocess.Popen) -> None:
        with self._lock:
            if self._closed:
                raise TaskStopped()
            self._processes[process.pid] = process
        if self.stopped:
            self._terminate_process(process)
            raise TaskStopped()

    def unregister_process(self, process: subprocess.Popen) -> None:
        with self._lock:
            self._processes.pop(process.pid, None)

    def register_driver(self, driver: Any) -> None:
        with self._lock:
            if self._closed:
                raise TaskStopped()
            self._drivers[id(driver)] = driver
        if self.stopped:
            self._quit_driver(driver)
            raise TaskStopped()

    def unregister_driver(self, driver: Any) -> None:
        with self._lock:
            self._drivers.pop(id(driver), None)

    def register_cleanup_path(self, path: str | Path) -> Path:
        cleanup_path = Path(path)
        with self._lock:
            self._cleanup_paths.add(cleanup_path)
        return cleanup_path

    def keep_path(self, path: str | Path) -> None:
        """Mark an output as complete so normal context cleanup preserves it."""
        with self._lock:
            self._cleanup_paths.discard(Path(path))

    @staticmethod
    def _terminate_process(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
                process.wait(timeout=2.0)
            except (OSError, subprocess.SubprocessError):
                pass
        except (OSError, subprocess.SubprocessError):
            pass

    @staticmethod
    def _quit_driver(driver: Any) -> None:
        try:
            driver.quit()
        except Exception:
            # The browser may already have closed itself; ownership is still
            # correct and no other browser session is touched.
            pass

    def request_stop(self) -> None:
        """Stop only processes and browser sessions owned by this run."""
        self.stop_event.set()
        with self._lock:
            processes = list(self._processes.values())
            drivers = list(self._drivers.values())
            self._processes.clear()
            self._drivers.clear()
        for process in processes:
            self._terminate_process(process)
        for driver in drivers:
            self._quit_driver(driver)

    def cleanup(self) -> None:
        """Release this run and remove only paths registered by this run."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            paths = list(self._cleanup_paths)
            self._cleanup_paths.clear()
            drivers = list(self._drivers.values())
            self._drivers.clear()
            processes = list(self._processes.values())
            self._processes.clear()
        for process in processes:
            self._terminate_process(process)
        for driver in drivers:
            self._quit_driver(driver)
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Không thể dọn file tạm {}: {}", path, exc)
        with _ACTIVE_LOCK:
            _ACTIVE_CONTEXTS.pop(self.run_id, None)


_APPLICATION_CONTEXT = TaskRunContext("application")


def create_run_context(task_name: str) -> TaskRunContext:
    return TaskRunContext(task_name)


@contextmanager
def bind_run_context(context: TaskRunContext) -> Iterator[TaskRunContext]:
    token = _CURRENT_CONTEXT.set(context)
    try:
        yield context
    finally:
        _CURRENT_CONTEXT.reset(token)


def current_run_context() -> TaskRunContext | None:
    return _CURRENT_CONTEXT.get()


def activate_run_context(context: TaskRunContext) -> contextvars.Token:
    """Bind a context until the returned token is passed to reset_run_context."""
    return _CURRENT_CONTEXT.set(context)


def reset_run_context(token: contextvars.Token) -> None:
    _CURRENT_CONTEXT.reset(token)


def check_stopped() -> None:
    context = current_run_context()
    if context is not None:
        context.checkpoint()


def wait_interruptibly(seconds: float) -> None:
    context = current_run_context()
    if context is None:
        threading.Event().wait(max(0.0, seconds))
        return
    context.wait(seconds)


def register_driver(driver: Any) -> Any:
    context = current_run_context() or _APPLICATION_CONTEXT
    context.register_driver(driver)
    return driver


def unregister_driver(driver: Any) -> None:
    context = current_run_context() or _APPLICATION_CONTEXT
    context.unregister_driver(driver)


def run_owned_process(
    command: Sequence[str | Path],
    *,
    check: bool = True,
    stdout: Any = None,
    stderr: Any = None,
    text: bool = False,
) -> subprocess.CompletedProcess:
    """Run one child process and retain its exact handle until it exits."""
    context = current_run_context() or _APPLICATION_CONTEXT
    context.checkpoint()
    args = [str(part) for part in command]
    process = subprocess.Popen(args, stdout=stdout, stderr=stderr, text=text)
    context.register_process(process)
    try:
        output, error = process.communicate()
    finally:
        context.unregister_process(process)
    context.checkpoint()
    completed = subprocess.CompletedProcess(args, process.returncode, output, error)
    if check and process.returncode:
        raise subprocess.CalledProcessError(
            process.returncode,
            args,
            output=output,
            stderr=error,
        )
    return completed


def post_with_stop(url: str, **kwargs: Any) -> requests.Response:
    """Perform a bounded HTTP POST with cooperative stop checks."""
    check_stopped()
    kwargs.setdefault("timeout", (15, 60))
    response = requests.post(url, **kwargs)
    check_stopped()
    return response


def stop_all_runs() -> None:
    """Application shutdown hook; touches only contexts created in this app."""
    with _ACTIVE_LOCK:
        contexts = list(_ACTIVE_CONTEXTS.values())
    for context in contexts:
        context.request_stop()
    for context in contexts:
        context.cleanup()


def active_run_count() -> int:
    """Return the number of feature runs that would be interrupted by shutdown."""
    with _ACTIVE_LOCK:
        return sum(
            1
            for context in _ACTIVE_CONTEXTS.values()
            if context is not _APPLICATION_CONTEXT and not context._closed
        )


atexit.register(stop_all_runs)
