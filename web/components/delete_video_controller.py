# RECOVERED: reconstructed from CPython 3.12 bytecode
"""
Background controller for the "Xóa - Back" page.

The processing state and the scan/delete loop live here, at module scope, so
they are independent of any browser connection. NiceGUI re-runs a @ui.page
builder on every (re)connect — including a browser refresh — which would
otherwise reset all per-client closures and kill the polling ui.timer.

By running the loop as a background asyncio task and keeping the state on this
singleton, a refresh simply re-attaches the UI to the still-running job:
the table, counters and countdown are rebuilt from `all_videos` and processing
continues uninterrupted.

The loop only mutates plain in-memory state (no `ui.*` calls). The page polls
this state via a client-bound ui.timer and renders the diff. Everything runs on
NiceGUI's single event loop, so no locking is needed for the in-memory state;
only blocking HTTP work is offloaded with asyncio.to_thread.
"""

import asyncio
import csv
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.module.delete_video_module import delete_video_module
from src.module.list_videos_module import list_videos_module
from src.paths import get_history_dir
from src.state_manager import state_manager
from src.utils import get_channels_info
from src.task_runtime import (
    TaskStopped,
    bind_run_context,
    create_run_context,
)


COPYRIGHT_STARTED = "UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_STARTED"
COPYRIGHT_NOT_STARTED = "UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_NOT_STARTED"
COPYRIGHT_COMPLETED = "UPLOAD_CHECKS_DATA_COPYRIGHT_STATUS_COMPLETED"
POLL_INTERVAL = 10
CSV_FILENAME = "deleted_videos.csv"
DEFAULT_OUTPUT_DIR = get_history_dir() / "delete_video"
_SETTINGS_KEY = "delete_video_settings"
_TERMINAL = ("deleted", "deleting", "error")


def _load_output_dir() -> Path:
    """Return the persisted output folder, falling back to the default."""
    try:
        saved = (state_manager.load_state(_SETTINGS_KEY) or {}).get("output_dir")
        if saved:
            return Path(saved)
    except Exception as exc:
        logger.error(f"Failed to load output_dir setting: {exc}")
    return DEFAULT_OUTPUT_DIR


def copyright_to_row_status(cs: str) -> str:
    if cs in (COPYRIGHT_STARTED, COPYRIGHT_COMPLETED):
        return "ready"
    if cs == COPYRIGHT_NOT_STARTED:
        return "waiting"
    return "skipped"


class DeleteVideoController:
    """Singleton holding the deletion job's state and background loop."""

    def __init__(self):
        self.all_videos = []
        self.selected_channel_ids = []
        self.max_workers = 5
        self.running = False
        self.polling = False
        self.next_poll_at = 0.0
        self.status_text = "Chọn kênh và nhấn Quét & Xóa để bắt đầu."
        self.version = 0
        self._task = None
        self._run_context = None
        self._channel_name_map = {}
        self._channel_avatar_map = {}
        self.output_dir = _load_output_dir()

    def _bump(self):
        self.version += 1

    @property
    def log_file(self) -> Path:
        return self.output_dir / CSV_FILENAME

    def set_output_dir(self, path) -> None:
        """Change and persist the folder where the delete log is saved."""
        self.output_dir = Path(path)
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.error(f"Cannot create output dir {self.output_dir}: {exc}")
        state_manager.save_state(
            _SETTINGS_KEY, {"output_dir": str(self.output_dir)}
        )
        self._bump()

    def refresh_channel_maps(self):
        channels = get_channels_info() or []
        self._channel_name_map = {ch.id: ch.name for ch in channels}
        self._channel_avatar_map = {ch.id: ch.img_src for ch in channels}

    def is_running(self) -> bool:
        # Keep the UI locked during the short "stopping" phase as well, so a
        # second run cannot overlap resources owned by the first run.
        return self._task is not None and not self._task.done()

    def counts(self, status_keys) -> dict[str, int]:
        c = {k: 0 for k in status_keys}
        for v in self.all_videos:
            if v["row_status"] in c:
                c[v["row_status"]] += 1
        return c

    def start(self, channel_ids: list[str], max_workers: int = 5):
        """Begin (or restart) processing the given channels."""
        if self.is_running():
            return
        self.refresh_channel_maps()
        self.selected_channel_ids = list(channel_ids)
        self.max_workers = max(1, int(max_workers))
        self.all_videos = []
        self.running = True
        self.polling = False
        self.next_poll_at = 0.0
        self.status_text = (
            f"Đang theo dõi & xóa {len(channel_ids)} kênh ({self.max_workers} luồng)..."
        )
        self._bump()
        self._run_context = create_run_context("delete_video_scan")
        self._task = asyncio.create_task(self._run_loop(self._run_context))

    async def stop(self):
        """Stop this controller's own scan and wait for its loop to settle."""
        task = self._task
        if task is None or task.done():
            return
        self.running = False
        self.status_text = "Đang dừng tác vụ quét hiện tại..."
        self._bump()
        if self._run_context is not None:
            self._run_context.request_stop()
        try:
            await task
        except (TaskStopped, asyncio.CancelledError):
            pass

    async def _run_loop(self, run_context):
        try:
            with bind_run_context(run_context):
                while self.running:
                    run_context.checkpoint()
                    self.polling = True
                    self._bump()

                    sem = asyncio.Semaphore(self.max_workers)
                    results = await asyncio.gather(
                        *[
                            self._process_channel(cid, sem)
                            for cid in self.selected_channel_ids
                        ],
                        return_exceptions=True,
                    )
                    for result in results:
                        if isinstance(result, TaskStopped):
                            raise result

                    run_context.checkpoint()
                    self.polling = False
                    self.next_poll_at = time.time() + POLL_INTERVAL
                    self._bump()

                    for _ in range(POLL_INTERVAL * 10):
                        if not self.running:
                            break
                        run_context.checkpoint()
                        await asyncio.sleep(0.1)
        except TaskStopped:
            pass
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(f"Delete loop crashed: {exc}")
        finally:
            self.polling = False
            self.running = False
            self.next_poll_at = 0.0
            self.status_text = "Đã dừng theo dõi."
            run_context.cleanup()
            if self._run_context is run_context:
                self._run_context = None
            self._bump()

    def _video_dict(self, v, channel_id: str) -> dict:
        return {
            "id": v.id,
            "channel_id": channel_id,
            "channel_name": self._channel_name_map.get(channel_id, channel_id),
            "channel_avatar": self._channel_avatar_map.get(channel_id, ""),
            "title": v.title,
            "thumbnail": v.thumbnail,
            "privacy": v.privacy,
            "copyright_check_status": v.copyright_check_status,
            "row_status": copyright_to_row_status(v.copyright_check_status),
        }

    def _set_row_status(self, video_id: str, new_status: str):
        for v in self.all_videos:
            if v["id"] == video_id:
                if v["row_status"] != new_status:
                    v["row_status"] = new_status
                    self._bump()
                return

    def _log_deleted(self, video: dict):
        """Append one row to deleted_videos.csv on a successful delete."""
        log_file = self.log_file
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_exists = log_file.exists()
            with log_file.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(
                        ["video_id", "channel_id", "channel_name", "deleted_at"]
                    )
                writer.writerow(
                    [
                        video["id"],
                        video["channel_id"],
                        video.get("channel_name", ""),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )
        except Exception as exc:
            logger.error(f"Failed to write deleted_videos.csv: {exc}")

    async def _scan_channel(self, channel_id: str) -> list[dict]:
        result = []
        page_token = None

        tracked_ids = {x["id"] for x in self.all_videos}
        while self.running:
            fetched, next_token = await asyncio.to_thread(
                list_videos_module.list_all_videos,
                channel_id,
                50,
                page_token,
            )
            for v in fetched:
                cs = v.copyright_check_status
                if cs in (COPYRIGHT_STARTED, COPYRIGHT_NOT_STARTED):
                    result.append(self._video_dict(v, channel_id))
                elif cs == COPYRIGHT_COMPLETED and v.id in tracked_ids:
                    result.append(self._video_dict(v, channel_id))
            if not next_token:
                break
            page_token = next_token
        return result

    async def _delete_video(self, video: dict):
        vid_id = video["id"]
        self._set_row_status(vid_id, "deleting")
        try:
            code = await asyncio.to_thread(
                delete_video_module.delete,
                vid_id,
                video["channel_id"],
            )
            self._set_row_status(vid_id, "deleted" if code == 200 else "error")
            if code != 200:
                logger.warning(f"Delete {vid_id} → HTTP {code}")
                return
            logger.info(f"Deleted {vid_id} ✓")
            self._log_deleted(video)
        except TaskStopped:
            self._set_row_status(vid_id, "stopped")
            raise
        except Exception as exc:
            if self._run_context is not None and self._run_context.stopped:
                self._set_row_status(vid_id, "stopped")
                raise TaskStopped() from exc
            self._set_row_status(vid_id, "error")
            logger.error(f"Delete error {vid_id}: {exc}")

    async def _process_channel(self, cid: str, sem: asyncio.Semaphore):
        if not self.running:
            return
        try:
            videos = await self._scan_channel(cid)
        except TaskStopped:
            raise
        except Exception as exc:
            if self._run_context is not None and self._run_context.stopped:
                raise TaskStopped() from exc
            logger.error(f"Scan error {cid}: {exc}")
            return

        to_delete = []
        by_id = {x["id"]: x for x in self.all_videos}

        for v in videos:
            vid_id = v["id"]
            existing = by_id.get(vid_id)

            if existing is None:
                if v["copyright_check_status"] == COPYRIGHT_COMPLETED:
                    continue
                self.all_videos.append(v)
                by_id[vid_id] = v
                self._bump()
                if v["row_status"] == "ready":
                    to_delete.append(v)
            elif existing["row_status"] in _TERMINAL:
                continue
            else:
                new_cs = v["copyright_check_status"]
                new_status = copyright_to_row_status(new_cs)
                if new_status != existing["row_status"]:
                    existing["copyright_check_status"] = new_cs
                    self._set_row_status(vid_id, new_status)
                if new_status == "ready":
                    to_delete.append(existing)

        if to_delete and self.running:

            async def _bounded(video: dict):
                async with sem:
                    if self.running:
                        await self._delete_video(video)

            await asyncio.gather(*[_bounded(v) for v in to_delete])


delete_controller = DeleteVideoController()
