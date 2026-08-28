# RECOVERED: reconstructed from CPython 3.12 bytecode
"""GitHub Release auto-updater for TV Automation (NiceGUI / asyncio).

Adapted from the Qt/PySide6 updater pattern to NiceGUI's single asyncio event
loop. Instead of QThreads + signals, the blocking network work runs in worker
threads via ``asyncio.to_thread`` and the UI polls this singleton's in-memory
state with a ``ui.timer`` (same approach as ``delete_video_controller``).

────────────────────────────────────────────────────────────────────────────
CONFIG — set these before building a release:
  * REPO_OWNER / REPO_NAME → the GitHub repo that publishes the Release assets.
  * FALLBACK_DOWNLOAD_URL  → optional direct installer URL used when a release
                             has no platform-matching asset.
The current version is read from the bundled ``VERSION`` file.
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import asyncio, json, os, platform, re, ssl, subprocess, sys, tempfile
from pathlib import Path
from typing import Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from loguru import logger

REPO_OWNER = "duykhanh8386"
REPO_NAME = "tool_vippro"
DEFAULT_INSTALLER_NAME = "TVAutomation_Isolated_Setup.exe"
FALLBACK_DOWNLOAD_URL: str | None = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/latest/download/{DEFAULT_INSTALLER_NAME}"
_USER_AGENT = "TV-Automation-Updater"


def get_current_version() -> str:
    """Read the bundled VERSION file (works both frozen and from source)."""
    try:
        if getattr(sys, "frozen", False):
            base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        else:
            base = Path(__file__).resolve().parent.parent
        version_file = base / "VERSION"
        if version_file.exists():
            text = version_file.read_text(encoding="utf-8").strip()
            if text:
                return text
    except Exception as exc:
        logger.error(f"Failed to read VERSION file: {exc}")
    return "v0.0.0"


def _get_ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _version_key(v: str) -> tuple[int, ...]:
    text = str(v or "").strip().lower().lstrip("v")
    if not text:
        return (0, 0, 0)
    core = text.split("-", 1)[0].split("+", 1)[0]
    parts = []
    for tok in core.split("."):
        m = re.search(r"\d+", tok)
        parts.append(int(m.group()) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _version_newer(latest: str, current: str) -> bool:
    return _version_key(latest) > _version_key(current)


def _find_platform_asset(assets: list[dict]) -> dict | None:
    system = platform.system().lower()
    if system == "windows":
        expected = DEFAULT_INSTALLER_NAME.lower()
        for asset in assets:
            if (
                isinstance(asset, dict)
                and str(asset.get("name") or "").lower() == expected
            ):
                return asset
        # Never install another Windows executable from this release: it may
        # belong to the legacy tool with a different AppId and data namespace.
        return None
    patterns = {
        "darwin": [".dmg", ".pkg", "macos", "mac", "darwin"],
        "linux": [".appimage", ".deb", ".rpm", ".tar.gz", "linux"],
    }
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").lower()
        if name and any(p in name for p in patterns.get(system, [])):
            return asset
    for asset in assets:
        if isinstance(asset, dict):
            return asset
    return None


def _check_latest_release(
    owner: str,
    repo: str,
    current_version: str,
    fallback_url: str | None,
) -> dict | None:
    """Blocking GitHub API call — run inside a worker thread.

    Returns the release info dict if a newer version exists, else None.
    Raises RuntimeError on network/API problems.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    req = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"})
    try:
        with urlopen(req, timeout=15, context=_get_ssl_context()) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        raise RuntimeError(f"GitHub API error: HTTP {e.code}") from e
    except URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e
    tag = str(data.get("tag_name") or "").strip()
    if not tag:
        raise RuntimeError("Missing tag_name in release")
    latest = tag.lstrip("v")
    if not _version_newer(latest, current_version):
        return None
    assets = data.get("assets") or []
    asset = _find_platform_asset(assets)
    dl_url = ""
    filename = ""
    if asset:
        dl_url = str(asset.get("browser_download_url") or "").strip()
        filename = str(asset.get("name") or "").strip()
    if not dl_url and fallback_url:
        dl_url = fallback_url
        filename = Path(dl_url).name or DEFAULT_INSTALLER_NAME
    if not dl_url:
        raise RuntimeError("No downloadable asset for this platform")
    return {
        "version": latest, "tag_name": tag, "name": str(data.get("name") or tag),
        "body": str(data.get("body") or ""), "published_at": str(data.get("published_at") or ""),
        "download_url": dl_url, "filename": filename or DEFAULT_INSTALLER_NAME,
        "html_url": str(data.get("html_url") or ""),
    }


def _download_installer(
    url: str,
    filename: str,
    progress_cb: Callable[[int], None],
    should_stop: Callable[[], bool],
) -> str:
    """Blocking download — run inside a worker thread. Returns the file path."""
    tmp = tempfile.mkdtemp(prefix="tv_update_")
    path = os.path.join(tmp, filename)
    req = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "*/*"})
    with urlopen(req, timeout=60, context=_get_ssl_context()) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(path, "wb") as f:
            while True:
                if should_stop():
                    raise RuntimeError("Đã hủy tải xuống")
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    progress_cb(max(0, min(100, int(downloaded / total * 100))))
    if total <= 0:
        progress_cb(100)
    return path


class UpdaterService:
    """Singleton holding update state; mutated by async tasks, polled by the UI.

    Phases: ``idle`` → ``checking`` → ``available`` / ``up_to_date`` / ``error``
            → ``downloading`` → ``ready`` (installer downloaded).
    """
    _instance: 'UpdaterService | None' = None

    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        *,
        current_version: str,
        fallback_download_url: str | None = None,
    ):
        self._owner = repo_owner
        self._repo = repo_name
        self._version = current_version
        self._fallback = fallback_download_url
        self.phase = "idle"
        self.status_text = ""
        self.progress = 0
        self.release_info = None
        self.installer_path = None
        self.error = None
        self.version = 0
        self._check_task = None
        self._dl_task = None
        self._stop_download = False
        self._auto_checked = False

    @classmethod
    def instance(cls) -> 'UpdaterService | None':
        return cls._instance

    @classmethod
    def create(
        cls,
        repo_owner: str,
        repo_name: str,
        *,
        current_version: str,
        fallback_download_url: str | None = None,
    ) -> 'UpdaterService':
        cls._instance = cls(repo_owner, repo_name, current_version=current_version, fallback_download_url=fallback_download_url)
        return cls._instance

    def _bump(self):
        self.version += 1

    @property
    def current_version(self) -> str:
        return self._version

    def is_configured(self) -> bool:
        return bool(self._owner) and bool(self._repo) and "REPLACE_ME" not in self._owner and "REPLACE_ME" not in self._repo

    def is_busy(self) -> bool:
        return self.phase in ("checking", "downloading")

    def update_available(self) -> bool:
        return self.phase == "available" and bool(self.release_info)

    def auto_check_once(self):
        """Run a single background check per app session (called by the sidebar)."""
        if self._auto_checked:
            return
        self._auto_checked = True
        if self.is_configured():
            self.check_for_updates()

    def check_for_updates(self):
        if self.is_busy():
            return
        if not self.is_configured():
            self.phase = "error"
            self.error = "Chưa cấu hình repo cập nhật (REPO_OWNER/REPO_NAME trong src/updater.py)."
            self.status_text = self.error
            self._bump()
            return
        self.phase = "checking"
        self.error = None
        self.status_text = "Đang kiểm tra cập nhật..."
        self._bump()
        self._check_task = asyncio.create_task(self._run_check())

    async def _run_check(self):
        try:
            result = await asyncio.to_thread(_check_latest_release, self._owner, self._repo, self._version, self._fallback)
            if result:
                self.release_info = result
                self.phase = "available"
                self.status_text = f"Đã có phiên bản mới: v{result['version']}"
            else:
                self.release_info = None
                self.phase = "up_to_date"
                self.status_text = "Bạn đang dùng phiên bản mới nhất."
        except Exception as exc:
            self.phase = "error"
            self.error = str(exc)
            self.status_text = f"Kiểm tra thất bại: {exc}"
            logger.error(f"Update check failed: {exc}")
        finally:
            self._bump()

    def download_update(self):
        if self.is_busy() or not self.release_info:
            return
        url = str(self.release_info.get("download_url") or "").strip()
        filename = str(self.release_info.get("filename") or DEFAULT_INSTALLER_NAME).strip()
        if not url:
            self.phase = "error"
            self.error = "Không tìm thấy URL tải xuống"
            self.status_text = self.error
            self._bump()
            return
        self._stop_download = False
        self.phase = "downloading"
        self.progress = 0
        self.error = None
        self.status_text = f"Đang tải {filename}..."
        self._bump()
        self._dl_task = asyncio.create_task(self._run_download(url, filename))

    async def _run_download(self, url: str, filename: str):
        loop = asyncio.get_running_loop()

        def _progress(pct: int):
            loop.call_soon_threadsafe(self._set_progress, pct)

        try:
            path = await asyncio.to_thread(_download_installer, url, filename, _progress, lambda: self._stop_download)
            self.installer_path = path
            self.progress = 100
            self.phase = "ready"
            self.status_text = "Tải xuống hoàn tất. Sẵn sàng cài đặt."
        except Exception as exc:
            self.phase = "error"
            self.error = str(exc)
            self.status_text = f"Tải xuống thất bại: {exc}"
            logger.error(f"Update download failed: {exc}")
        finally:
            self._bump()

    def _set_progress(self, pct: int):
        self.progress = pct

    def cancel_download(self):
        if self.phase == "downloading":
            self._stop_download = True
            self.status_text = "Đang hủy tải xuống..."
            self._bump()

    def install_update(self) -> tuple[bool, str]:
        """Launch the downloaded installer. Returns (ok, message).

        On success the caller should close the app so the installer can replace
        the running files.
        """
        path = str(self.installer_path or "").strip()
        if not path or not os.path.exists(path):
            return False, "File cài đặt không tồn tại"
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(path)
            elif system == "Darwin":
                subprocess.Popen(["open", path])
            else:
                try:
                    subprocess.Popen(["xdg-open", path])
                except Exception:
                    os.chmod(path, 0o755)
                    subprocess.Popen([path])
            return True, "Đang mở trình cài đặt..."
        except Exception as exc:
            logger.error(f"Install launch failed: {exc}")
            return False, f"Cài đặt thất bại: {exc}"


updater_service = UpdaterService.create(
    REPO_OWNER, REPO_NAME, current_version=get_current_version(), fallback_download_url=FALLBACK_DOWNLOAD_URL,
)
