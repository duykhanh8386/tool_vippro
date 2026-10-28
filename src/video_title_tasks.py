"""Durable, cancellable title jobs shared by page refreshes and browser tabs."""
from __future__ import annotations

import copy
import threading

from src.module.base import YouTubeRequestError
from src.module.video_title_module import video_title_module
from src.state_manager import state_manager
from src.task_runtime import TaskStopped, bind_run_context, create_run_context
from src.video_title_matching import build_title_matches, default_title_settings, parse_manual_title_ids, scan_title_videos

STATE_KEY = "video_titles"
ELIGIBLE = {"ready", "error", "stopped"}


class VideoTitleController:
    def __init__(self, *, storage=None, module=None):
        self.storage = storage or state_manager
        self.module = module or video_title_module
        self.lock = threading.RLock()
        saved = self.storage.load_state(STATE_KEY) or {}
        self.settings = {**default_title_settings(), **saved.get("settings", {})}
        self.rows = saved.get("rows", [])
        for row in self.rows:
            if row.get("status") == "processing":
                row.update(status="ready", detail="Phiên trước bị ngắt; sẽ đọc lại YouTube trước khi đổi tiếp.")
        self.message = saved.get("message", "Chọn kênh, quét video rồi ghép theo thời lượng.")
        self.busy = False
        self.phase = ""
        self.run = None
        self.thread = None
        self.revision = 0

    def _save(self):
        if not self.storage.save_state(STATE_KEY, {"settings": self.settings, "rows": self.rows, "message": self.message}):
            raise ValueError("Không lưu được tiến độ vào dữ liệu của tool. Đã dừng trước bước tiếp theo.")

    def snapshot(self):
        with self.lock:
            return copy.deepcopy({"settings": self.settings, "rows": self.rows, "message": self.message,
                                  "busy": self.busy, "phase": self.phase, "revision": self.revision})

    def change_settings(self, **changes):
        with self.lock:
            if self.busy:
                raise ValueError("Dừng tác vụ hiện tại trước khi đổi thiết lập.")
            if all(self.settings.get(key) == value for key, value in changes.items()):
                return
            self.settings.update(changes)
            # A preview always belongs to its exact channel/folder/filter settings.
            if set(changes) & {"channel_id", "mode", "scope", "limit", "start_date", "end_date", "date_type"}:
                self.rows = []
                self.message = "Phạm vi đã đổi. Quét lại video để tạo danh sách mới."
            elif set(changes) & {"folder", "recursive", "tolerance"}:
                for row in self.rows:
                    if row["status"] == "successful":
                        row["old_title"] = row["new_title"]
                    row.update(status="scanned", audio_path="", audio_duration=None, delta=None,
                               new_title="", candidates=[], selected=False, detail="Ghép lại theo thiết lập nhạc mới.")
                self.message = "Thiết lập nhạc đã đổi. Bấm Ghép theo thời lượng để tạo lại tiêu đề."
            self.revision += 1
            self._save()

    def select(self, video_ids):
        with self.lock:
            if self.busy:
                return
            selected = set(video_ids)
            for row in self.rows:
                row["selected"] = row["video_id"] in selected and bool(row.get("new_title")) and row["status"] in ELIGIBLE
            self.revision += 1
            self._save()

    def select_candidate(self, video_id, path):
        with self.lock:
            if self.busy:
                raise ValueError("Dừng tác vụ trước khi chọn lại file nhạc.")
            row = next(row for row in self.rows if row["video_id"] == video_id)
            candidate = next((item for item in row.get("candidates", []) if item["path"] == path), None)
            if not candidate:
                raise ValueError("File đã chọn không nằm trong các bài nhạc khớp thời lượng.")
            same = candidate["title"] == row["old_title"]
            row.update(audio_path=path, audio_duration=candidate["seconds"], delta=candidate["delta"],
                       new_title=candidate["title"], status="unchanged" if same else "ready", selected=not same,
                       detail=f"Đã chọn file · lệch {candidate['delta']:.2f}s.")
            self.revision += 1
            self._save()

    def start(self, action):
        if action not in {"scan", "scan_part", "scan_manual", "match", "update"}:
            raise ValueError("Tác vụ tiêu đề không hợp lệ.")
        with self.lock:
            if self.busy:
                raise ValueError("Tác vụ đang chạy. Chờ hoàn tất hoặc bấm Dừng.")
            if not self.settings["channel_id"]:
                raise ValueError("Chọn một kênh YouTube trước.")
            if action == "scan_manual":
                parse_manual_title_ids(self.settings["manual_ids"])
            if action in {"match", "update"} and not self.rows:
                raise ValueError("Quét video trước khi ghép và đổi tiêu đề.")
            if action == "match" and not self.settings["folder"]:
                raise ValueError("Chọn thư mục nhạc trước khi ghép.")
            if action == "update" and not any(row.get("selected") and row["status"] in ELIGIBLE and row.get("new_title") for row in self.rows):
                raise ValueError("Chọn ít nhất một video đã ghép để đổi tiêu đề.")
            self.busy, self.phase = True, action
            self.revision += 1
            self.message = {"scan": "Đang quét video trên kênh…", "scan_part": "Đang quét video có chữ “part” trong tiêu đề…",
                            "scan_manual": "Đang đọc các Video ID nhập thủ công…",
                            "match": "Đang đọc thời lượng nhạc…", "update": "Đang kiểm tra và đổi tiêu đề…"}[action]
            self.run = create_run_context("video_titles")
            self.thread = threading.Thread(target=self._worker, args=(action, self.run), daemon=True, name="video-titles")
            self.thread.start()

    def stop(self):
        with self.lock:
            run = self.run
            if self.busy:
                self.message = "Đang dừng; chờ yêu cầu hiện tại kết thúc. Chạy lại sẽ đọc kết quả thực tế trước."
        if run:
            run.request_stop()

    def _progress(self, message):
        with self.lock:
            self.message = message

    @staticmethod
    def _error(exc):
        return str(exc) if isinstance(exc, (ValueError, YouTubeRequestError)) else "Tác vụ chưa hoàn tất do lỗi kết nối hoặc dữ liệu. Kiểm tra phiên kênh và thử lại."

    def _worker(self, action, run):
        try:
            with bind_run_context(run):
                settings = dict(self.settings)
                if action in {"scan", "scan_part", "scan_manual"}:
                    if action == "scan_manual":
                        identifiers = parse_manual_title_ids(settings["manual_ids"])
                        videos = []
                        for index, identifier in enumerate(identifiers, 1):
                            run.checkpoint()
                            self._progress(f"Đọc Video ID {index}/{len(identifiers)} · {identifier}")
                            try:
                                videos.append(self.module.read_video(settings["channel_id"], identifier))
                            except (ValueError, YouTubeRequestError) as exc:
                                raise ValueError(f"Video {identifier}: {self._error(exc)}") from None
                    else:
                        videos = scan_title_videos(settings["channel_id"], mode=settings["mode"], scope=settings["scope"],
                                                   limit=settings["limit"], start_date=settings["start_date"], end_date=settings["end_date"],
                                                   date_type=settings["date_type"], title_contains="part" if action == "scan_part" else "",
                                                   progress=self._progress)
                    run.checkpoint()
                    with self.lock:
                        self.rows = [dict(video_id=v.id, channel_id=v.channel_id, old_title=v.title,
                                          duration_seconds=float(v.duration_ms or 0) / 1000, status="scanned",
                                          audio_path="", new_title="", selected=False, detail="Chưa ghép nhạc.") for v in videos]
                        source = {"scan": "Đã quét", "scan_part": "Đã quét", "scan_manual": "Đã đọc"}[action]
                        criterion = " có chữ “part” trong tiêu đề" if action == "scan_part" else " nhập thủ công" if action == "scan_manual" else ""
                        self.message = f"{source} {len(self.rows)} video{criterion}. Chọn thư mục nhạc rồi bấm Ghép theo thời lượng."
                        self.revision += 1
                        self._save()
                elif action == "match":
                    rows, counts = build_title_matches(self.rows, settings["folder"], recursive=settings["recursive"],
                                                        tolerance=settings["tolerance"], progress=self._progress)
                    run.checkpoint()
                    with self.lock:
                        self.rows = rows
                        ready = sum(row["status"] == "ready" for row in rows)
                        same = sum(row["status"] == "unchanged" for row in rows)
                        ambiguous = sum(row["status"] == "ambiguous" for row in rows)
                        self.message = (f"Đọc {counts['files']} file nhạc · {ready} video sẵn sàng đổi · {same} đã đúng tên · "
                                        f"{ambiguous} cần chọn lại file · {counts['unreadable']} file không đọc được.")
                        self.revision += 1
                        self._save()
                else:
                    self._update_rows(settings, run)
        except TaskStopped:
            self._progress("Đã dừng tác vụ. Có thể tiếp tục các dòng chưa xong; tool sẽ đọc lại YouTube trước khi gửi.")
        except Exception as exc:
            self._progress(self._error(exc))
        finally:
            with self.lock:
                for row in self.rows:
                    if row["status"] == "processing":
                        row.update(status="stopped", detail="Chưa xác nhận kết quả. Chạy lại để đọc tiêu đề thực tế.")
                self.busy = False
                self.phase = ""
                self.run = None
                self.revision += 1
                try:
                    self._save()
                except ValueError as exc:
                    self.message = str(exc)
            run.cleanup()

    def _update_rows(self, settings, run):
        selected = [row for row in self.rows if row.get("selected") and row["status"] in ELIGIBLE and row.get("new_title")]
        successful = failed = 0
        for index, row in enumerate(selected, 1):
            run.checkpoint()
            with self.lock:
                if row["channel_id"] != settings["channel_id"]:
                    raise ValueError("Danh sách xem trước thuộc kênh khác. Quét lại trước khi đổi.")
                row.update(status="processing", detail="Đang đọc và cập nhật tiêu đề trên YouTube…")
                self.message = f"Đổi tiêu đề {index}/{len(selected)} · Video {row['video_id']}"
                self.revision += 1
                self._save()
            try:
                result = self.module.update_title(settings["channel_id"], row["video_id"], row["new_title"], expected_title=row["old_title"],
                                                   audio_duration=row.get("audio_duration"), tolerance=settings["tolerance"])
                if result.get("title") != row["new_title"]:
                    raise ValueError("Chưa đọc được đúng tiêu đề đã yêu cầu; chưa ghi nhận thành công.")
                with self.lock:
                    row.update(status="successful", selected=False,
                               detail="Đã đọc lại và xác nhận tiêu đề mới trên YouTube." if result["changed"] else "YouTube đã có đúng tiêu đề này; đã xác nhận lại.")
                    successful += 1
            except TaskStopped:
                raise
            except Exception as exc:
                with self.lock:
                    row.update(status="error", detail=self._error(exc))
                    failed += 1
                if isinstance(exc, YouTubeRequestError) and exc.status_code in {401, 403}:
                    raise ValueError("Phiên kênh không còn quyền cập nhật. Load lại đúng kênh; các dòng chưa xong được giữ để tiếp tục.") from None
            finally:
                with self.lock:
                    self.revision += 1
                    self._save()
        self._progress(f"Đã kết thúc lượt đổi tiêu đề · xác nhận thành công {successful} · lỗi {failed}.")


_controller = None
_controller_lock = threading.Lock()


def get_video_title_controller():
    global _controller
    with _controller_lock:
        if _controller is None:
            _controller = VideoTitleController()
        return _controller
