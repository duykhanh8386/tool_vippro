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

    def __call__(self):
        check_stopped()
        if self.reader is None:
            from src.module.video_publishing_module import video_publishing_module
            self.reader = video_publishing_module.read_video
        video = self.reader(self.channel_id, self.video_id)
        if video.id != self.video_id or video.channel_id != self.channel_id:
            raise ValueError("Video đọc lại không thuộc đúng kênh; chưa xác nhận thumbnail.")
        thumbnails = (getattr(video, "thumbnail_details", {}) or {}).get("thumbnails") or []
        url = max(thumbnails, key=lambda item: item.get("width", 0)).get("url", "") if thumbnails else video.thumbnail
        parsed = urlparse(url)
        if parsed.scheme != "https" or not (parsed.hostname == "ytimg.com" or (parsed.hostname or "").endswith(".ytimg.com")):
            return False
        source = None
        try:
            with requests.get(url, timeout=(10, 20), stream=True, allow_redirects=False,
                              headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}) as response:
                if response.status_code != 200 or not response.headers.get("Content-Type", "").startswith("image/"):
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
                return same_thumbnail(self.expected, thumbnail_pixels(source))
            except ValueError:
                return False
        except requests.RequestException:
            return False
        finally:
            if source is not None:
                source.unlink(missing_ok=True)
