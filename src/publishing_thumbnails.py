"""Confirm a saved Studio thumbnail by reading its image back from YouTube."""
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlparse

import requests

from src.task_runtime import check_stopped, run_owned_process


def thumbnail_pixels(path):
    try:
        result = run_owned_process([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
            "-vf", "scale=160:90:force_original_aspect_ratio=increase,crop=160:90,format=rgb24",
            "-frames:v", "1", "-f", "rawvideo", "pipe:1",
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError):
        raise ValueError("Không đọc được ảnh để đối chiếu thumbnail đã lưu.") from None
    if len(result.stdout) != 160 * 90 * 3:
        raise ValueError("Dữ liệu ảnh đối chiếu thumbnail không hợp lệ.")
    return result.stdout


def same_thumbnail(expected, actual):
    if not expected or len(expected) != len(actual):
        return False
    differences = [abs(left - right) for left, right in zip(expected, actual)]
    # YouTube can resize/recompress an upload. Require both a small average
    # difference and very few strongly different samples, including text areas.
    return sum(differences) / len(differences) <= 8 and sum(value > 40 for value in differences) / len(differences) <= 0.01


class ThumbnailReadback:
    def __init__(self, channel_id, video_id, path, *, reader=None):
        self.channel_id, self.video_id = channel_id, video_id
        self.expected = thumbnail_pixels(path)
        self.reader = reader
        self.last_reason = "Chưa đọc được ảnh thumbnail đã lưu."
        self.confirmed_asset_id = ""
        self.initial_asset_id = None
        self.expected_asset_id = ""

    def expect_upload_asset(self, asset_ids):
        if len(asset_ids) == 1:
            asset_id = next(iter(asset_ids))
            if asset_id and asset_id != self.initial_asset_id:
                self.expected_asset_id = asset_id

    @staticmethod
    def _selected_custom_asset(state, asset_id):
        return (bool(asset_id) and (state.get("customThumbnail") or {}).get("externalImageId") == asset_id
                and state.get("defaultStill") is not True and state.get("stillId", 0) == 0)

    def observe_save_response(self, response, asset_ids):
        """Accept a server-saved image identity tied to this upload request."""
        if len(asset_ids) != 1:
            return False
        candidates = [response.get("video")] + (response.get("videos") if isinstance(response.get("videos"), list) else [])
        for video in candidates:
            if not isinstance(video, dict) or video.get("videoId") != self.video_id or video.get("channelId") != self.channel_id:
                continue
            state = video.get("thumbnailEditorState") or {}
            asset_id = (state.get("customThumbnail") or {}).get("externalImageId")
            if (asset_id and asset_id != self.initial_asset_id and asset_id in asset_ids
                    and state.get("defaultStill") is not True and state.get("stillId", 0) == 0):
                self.confirmed_asset_id = asset_id
                self.last_reason = "Máy chủ đã xác nhận đúng mã ảnh tùy chỉnh của lần tải này."
                return True
        return False

    def __call__(self):
        check_stopped()
        if self.confirmed_asset_id:
            return True
        if self.reader is None:
            from src.module.video_publishing_module import video_publishing_module
            self.reader = video_publishing_module.read_video
        video = self.reader(self.channel_id, self.video_id)
        if video.id != self.video_id or video.channel_id != self.channel_id:
            raise ValueError("Video đọc lại không thuộc đúng kênh; chưa xác nhận thumbnail.")
        if self.initial_asset_id is None:
            self.initial_asset_id = ((getattr(video, "thumbnail_editor_state", {}) or {}).get("customThumbnail") or {}).get("externalImageId", "")
        if self._selected_custom_asset(getattr(video, "thumbnail_editor_state", {}) or {}, self.expected_asset_id):
            self.confirmed_asset_id = self.expected_asset_id
            self.last_reason = "Đã đọc lại đúng mã ảnh của lần tải này từ Studio."
            return True
        thumbnails = (getattr(video, "thumbnail_details", {}) or {}).get("thumbnails") or []
        url = max(thumbnails, key=lambda item: item.get("width", 0)).get("url", "") if thumbnails else video.thumbnail
        parsed = urlparse(url)
        if parsed.scheme != "https" or not (parsed.hostname == "ytimg.com" or (parsed.hostname or "").endswith(".ytimg.com")):
            self.last_reason = "Chưa có đường dẫn thumbnail YouTube hợp lệ để đối chiếu."
            return False
        source = None
        try:
            with requests.get(url, timeout=(10, 20), stream=True, allow_redirects=False,
                              headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}) as response:
                if response.status_code != 200 or not response.headers.get("Content-Type", "").startswith("image/"):
                    self.last_reason = "Máy chủ ảnh chưa trả ảnh hợp lệ (HTTP " + str(response.status_code) + ")."
                    return False
                with tempfile.NamedTemporaryFile(suffix=".image", delete=False) as stream:
                    source = Path(stream.name)
                    size = 0
                    for chunk in response.iter_content(65536):
                        check_stopped()
                        size += len(chunk)
                        if size > 10 * 1024 * 1024:
                            return False
                        stream.write(chunk)
            try:
                actual = thumbnail_pixels(source)
                matched = same_thumbnail(self.expected, actual)
                if not matched:
                    difference = sum(abs(left-right) for left,right in zip(self.expected, actual))/len(actual)
                    self.last_reason = "Ảnh máy chủ đọc lại còn khác ảnh đã gửi (độ lệch trung bình " + format(difference, ".1f") + "/255); có thể đang trả ảnh cũ hoặc ảnh chưa được lưu."
                return matched
            except ValueError:
                self.last_reason = "Không giải mã được ảnh thumbnail máy chủ trả về."
                return False
        except requests.RequestException:
            self.last_reason = "Không tải được thumbnail máy chủ để đối chiếu."
            return False
        finally:
            if source is not None:
                source.unlink(missing_ok=True)
