"""Durable YouTube-to-MP3 download queue backed by yt-dlp and FFmpeg."""

from __future__ import annotations

import asyncio
import re
import shutil
import sys
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from src.paths import get_history_dir
from src.state_manager import state_manager

try:  # Kept optional only so a source checkout can show a useful error.
    from yt_dlp import YoutubeDL
except ImportError:  # pragma: no cover - production requirements include it
    YoutubeDL = None


STATE_KEY = "youtube_mp3_download"
DEFAULT_OUTPUT_DIR = get_history_dir() / "youtube_mp3"
_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


class DownloadStopped(Exception):
    """Raised from a yt-dlp progress hook after the user requests a stop."""


def parse_youtube_urls(text: str | None) -> tuple[list[str], list[str]]:
    """Split, normalize, and validate one YouTube video URL per line."""
    urls: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for raw in (text or "").replace(",", "\n").splitlines():
        url = raw.strip()
        if not url:
            continue
        parsed = urlparse(url)
        host = parsed.netloc.lower().split(":", 1)[0]
        if parsed.scheme not in {"http", "https"} or host not in _YOUTUBE_HOSTS:
            invalid.append(url)
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls, invalid


def resolve_ffmpeg_location() -> str | None:
    """Find FFmpeg both in a packaged app and in a local developer checkout."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.append(bundle_dir / "tools" / "ffmpeg")

    project_root = Path(__file__).resolve().parents[1]
    candidates.extend(
        (
            project_root / "vendor" / "ffmpeg" / "bin",
            # Supports this repository's existing portable downloader while
            # developing from source. Packaged builds use tools/ffmpeg above.
            project_root / "YouTubeDownloadMusic" / "_internal",
        )
    )
    for directory in candidates:
        executable = directory / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        if executable.is_file():
            return str(directory)

    located = shutil.which("ffmpeg")
    return str(Path(located).parent) if located else None


def resolve_js_runtime() -> tuple[str, str] | None:
    """Use an installed JS runtime when available for newer YouTube players."""
    # yt-dlp enables Deno by default. Node and Bun are also supported when
    # passed explicitly, which lets the tool use an existing local runtime
    # without adding another large binary to the application package.
    for name in ("deno", "node", "bun"):
        executable = shutil.which(name)
        if executable:
            return name, executable
    return None


def _safe_error_message(exc: BaseException) -> str:
    detail = str(exc).replace("\n", " ").strip()
    lowered = detail.lower()
    if "sign in to confirm" in lowered or "not a bot" in lowered:
        return (
            "YouTube yêu cầu xác minh phiên truy cập. Hãy thử lại sau hoặc dùng URL "
            "video công khai không giới hạn độ tuổi."
        )
    if "ffmpeg" in lowered and ("not found" in lowered or "not installed" in lowered):
        return "Không tìm thấy FFmpeg để chuyển đổi sang MP3. Hãy cài lại tool."
    return detail[:600] or exc.__class__.__name__


class YoutubeMp3DownloadController:
    """One durable, background download queue shared by all browser pages."""

    def __init__(self) -> None:
        self.urls: list[str] = []
        self.items: dict[str, dict[str, Any]] = {}
        self.output_dir = DEFAULT_OUTPUT_DIR
        self.audio_quality = "192"
        self.running = False
        self.status_text = "Dán link YouTube rồi bấm Tải MP3."
        self.version = 0
        self._task: asyncio.Task | None = None
        self._stop_event = threading.Event()
        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._last_saved_progress: dict[str, int] = {}
        self._restore_state()

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def _default_item(self, url: str) -> dict[str, Any]:
        return {
            "url": url,
            "title": "",
            "output_path": "",
            "status": "pending",
            "progress": 0,
            "error": "",
        }

    def _restore_state(self) -> None:
        try:
            state = state_manager.load_state(STATE_KEY) or {}
            saved_urls = state.get("urls") or []
            self.urls = [url for url in saved_urls if isinstance(url, str)]
            saved_items = state.get("items") or {}
            self.items = {
                url: {**self._default_item(url), **dict(saved_items.get(url) or {})}
                for url in self.urls
            }
            output_dir = state.get("output_dir")
            if output_dir:
                self.output_dir = Path(output_dir)
            self.audio_quality = str(state.get("audio_quality") or "192")

            recovered = False
            for item in self.items.values():
                if item.get("status") == "downloading":
                    item["status"] = "pending"
                    item["progress"] = 0
                    item["error"] = "Đã khôi phục sau khi ứng dụng bị dừng."
                    recovered = True
            if self.urls:
                self.status_text = "Đã khôi phục danh sách trước đó. Bấm Tải MP3 để tiếp tục."
            if recovered:
                self._save_state()
        except Exception as exc:
            logger.error("Failed to restore YouTube MP3 download state: {}", exc)

    def _save_state(self) -> bool:
        try:
            serializable_items = {
                url: {key: value for key, value in item.items() if not key.startswith("_")}
                for url, item in self.items.items()
            }
            return state_manager.save_state(
                STATE_KEY,
                {
                    "urls": list(self.urls),
                    "items": serializable_items,
                    "output_dir": str(self.output_dir),
                    "audio_quality": self.audio_quality,
                },
            )
        except Exception as exc:
            logger.error("Failed to save YouTube MP3 download state: {}", exc)
            return False

    def _bump(self, *, persist: bool = True) -> None:
        self.version += 1
        if persist:
            self._save_state()

    def update_urls(self, urls: list[str]) -> None:
        """Replace the queue, preserving existing results for unchanged URLs."""
        if self.is_running():
            raise RuntimeError("Đang tải MP3; hãy bấm Dừng trước khi đổi danh sách.")
        deduplicated: list[str] = []
        seen: set[str] = set()
        for url in urls:
            if url not in seen:
                seen.add(url)
                deduplicated.append(url)
        previous = self.items
        self.urls = deduplicated
        self.items = {
            url: {**self._default_item(url), **dict(previous.get(url) or {})}
            for url in self.urls
        }
        self.status_text = (
            f"Đã lưu {len(self.urls)} link."
            if self.urls
            else "Dán ít nhất một link YouTube để bắt đầu."
        )
        self._bump()

    def set_output_dir(self, path: str | Path) -> None:
        if self.is_running():
            raise RuntimeError("Đang tải MP3; chưa thể đổi thư mục lưu.")
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        self.output_dir = target
        self._bump()

    def start(self) -> None:
        if self.is_running():
            return
        if not self.urls:
            raise RuntimeError("Chưa có link YouTube hợp lệ.")
        if YoutubeDL is None:
            raise RuntimeError("Thiếu yt-dlp. Hãy cài lại phiên bản mới của tool.")
        ffmpeg_location = resolve_ffmpeg_location()
        if not ffmpeg_location:
            raise RuntimeError("Không tìm thấy FFmpeg để chuyển đổi sang MP3. Hãy cài lại tool.")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._stop_event.clear()
        self.running = True
        self.status_text = "Đang chuẩn bị tải MP3..."
        self._event_loop = asyncio.get_running_loop()
        self._bump()
        self._task = asyncio.create_task(self._run_loop(ffmpeg_location))

    async def stop(self) -> None:
        if not self.is_running():
            return
        self.status_text = "Đang dừng sau phần dữ liệu hiện tại..."
        self._stop_event.set()
        self._bump()
        task = self._task
        if task is not None:
            await task

    async def _run_loop(self, ffmpeg_location: str) -> None:
        stopped = False
        try:
            for url in self.urls:
                if self._stop_event.is_set():
                    stopped = True
                    break
                item = self.items[url]
                if item.get("status") == "successful":
                    continue
                item.update(status="downloading", progress=0, error="")
                self.status_text = f"Đang tải: {url}"
                self._bump()
                try:
                    result = await asyncio.to_thread(
                        self._download_one, url, ffmpeg_location
                    )
                except Exception as exc:
                    if self._stop_event.is_set():
                        item["status"] = "stopped"
                        item["error"] = "Đã dừng theo yêu cầu."
                        stopped = True
                        self._bump()
                        break
                    item["status"] = "error"
                    item["error"] = _safe_error_message(exc)
                    logger.warning("YouTube MP3 download failed for {}: {}", url, exc)
                    self._bump()
                    continue

                item.update(
                    status="successful",
                    progress=100,
                    title=result.get("title") or "",
                    output_path=result.get("output_path") or "",
                    error="",
                )
                self._bump()
        except asyncio.CancelledError:
            self._stop_event.set()
            stopped = True
            raise
        finally:
            if self._stop_event.is_set():
                stopped = True
            self.running = False
            self._event_loop = None
            if stopped:
                self.status_text = "Đã dừng. Bấm Tải MP3 để tiếp tục các link còn lại."
            elif all(
                self.items[url].get("status") == "successful" for url in self.urls
            ):
                self.status_text = "Đã tải xong tất cả MP3."
            else:
                self.status_text = "Đã hoàn tất; các link lỗi có thể tải lại."
            self._bump()

    def _record_progress(self, url: str, downloaded: int, total: int) -> None:
        item = self.items.get(url)
        if item is None or item.get("status") != "downloading":
            return
        percent = min(99, int(downloaded * 100 / total)) if total else 0
        item["progress"] = percent
        last_saved = self._last_saved_progress.get(url, -5)
        self._last_saved_progress[url] = percent
        # Progress is only cosmetic. Persist every 5% so sudden power loss
        # keeps a useful checkpoint without turning SQLite into the bottleneck.
        self._bump(persist=percent >= last_saved + 5)

    def _schedule_progress(self, url: str, data: dict[str, Any]) -> None:
        if self._stop_event.is_set():
            raise DownloadStopped()
        if data.get("status") != "downloading":
            return
        downloaded = int(data.get("downloaded_bytes") or 0)
        total = int(
            data.get("total_bytes") or data.get("total_bytes_estimate") or 0
        )
        loop = self._event_loop
        if loop is not None:
            try:
                loop.call_soon_threadsafe(self._record_progress, url, downloaded, total)
            except RuntimeError:
                pass

    def _download_one(self, url: str, ffmpeg_location: str) -> dict[str, str]:
        if YoutubeDL is None:  # pragma: no cover - guarded by start()
            raise RuntimeError("yt-dlp is not installed")

        options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "outtmpl": str(self.output_dir / "%(title).180B [%(id)s].%(ext)s"),
            "windowsfilenames": True,
            "continuedl": True,
            "overwrites": False,
            "retries": 3,
            "fragment_retries": 3,
            "extractor_retries": 3,
            "socket_timeout": 30,
            "quiet": True,
            "no_warnings": True,
            "ffmpeg_location": ffmpeg_location,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": self.audio_quality,
                }
            ],
            "progress_hooks": [lambda data: self._schedule_progress(url, data)],
        }
        js_runtime = resolve_js_runtime()
        if js_runtime:
            runtime_name, runtime_path = js_runtime
            options["js_runtimes"] = {runtime_name: {"path": runtime_path}}
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if self._stop_event.is_set():
                raise DownloadStopped()
            if not info:
                raise RuntimeError("yt-dlp không trả về thông tin video.")
            source_path = Path(ydl.prepare_filename(info))
            return {
                "title": str(info.get("title") or ""),
                "output_path": str(source_path.with_suffix(".mp3")),
            }


youtube_mp3_controller = YoutubeMp3DownloadController()
