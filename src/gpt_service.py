import atexit
import json
import subprocess
import sys
import threading
from pathlib import Path

from src.paths import get_data_dir


_resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
_worker_path = _resource_root / "gpt_backend" / "worker.js"
_node = str(_resource_root / "tools" / "node" / "node.exe") if getattr(sys, "frozen", False) else "node"
_lock = threading.Lock()
_process = None


class GPTServiceError(ValueError):
    def __init__(self, message, code="unknown"):
        super().__init__(message)
        self.code = code


def _stop():
    global _process
    with _lock:
        if _process and _process.poll() is None:
            _process.stdin.close()
            try:
                _process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _process.terminate()
        _process = None


atexit.register(_stop)


def call(action, **arguments):
    global _process
    import os

    with _lock:
        if _process is None or _process.poll() is not None:
            env = os.environ.copy()
            env["TVA_GPT_DATA_ROOT"] = str(get_data_dir() / "gpt_runtime")
            try:
                _process = subprocess.Popen(
                    [_node, str(_worker_path)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    encoding="utf-8",
                    env=env,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except FileNotFoundError as error:
                raise GPTServiceError("Cần cài Node.js 22 trở lên để sử dụng GPT.", "runtime") from error
        try:
            _process.stdin.write(json.dumps({"action": action, **arguments}, ensure_ascii=True) + "\n")
            _process.stdin.flush()
            response = _process.stdout.readline()
        except (BrokenPipeError, OSError) as error:
            raise GPTServiceError("Bộ xử lý GPT đã dừng. Kiểm tra Node.js và dependencies.", "runtime") from error
        if not response:
            raise GPTServiceError("Bộ xử lý GPT đã dừng. Kiểm tra Node.js và dependencies.", "runtime")
        try:
            data = json.loads(response)
        except json.JSONDecodeError as error:
            raise GPTServiceError("Bộ xử lý GPT trả dữ liệu không hợp lệ.", "runtime") from error
        if "error" in data:
            raise GPTServiceError(data["error"], data.get("code", "unknown"))
        return data["result"]
