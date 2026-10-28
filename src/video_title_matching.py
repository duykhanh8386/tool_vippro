"""Read channel videos and pair their durations with local song filenames."""
from __future__ import annotations

import math
import re
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.audio_batch_matcher import normalize_title, scan_audio_files
from src.audio_recovery import _is_currently_public_video, _is_currently_scheduled_video
from src.module.list_videos_module import list_videos_module
from src.task_runtime import TaskStopped, check_stopped
from src.utils import get_video_duration
from src.video_scan_dates import normalize_scan_date_type, scan_date_bounds, scan_today, video_matches_scan_dates


def clean_video_title(value: str) -> str:
    title = " ".join(str(value or "").replace("<", "").replace(">", "").split())
    # Stay within 100 UTF-16 units, keeping emoji/surrogate pairs whole.
    title = title.encode("utf-16-le")[:200].decode("utf-16-le", errors="ignore").strip()
    if not title:
        raise ValueError("Tên file nhạc không tạo được tiêu đề hợp lệ.")
    return title


def parse_manual_title_ids(text: str) -> list[str]:
    """Accept explicit IDs or YouTube links, preserving order without duplicates."""
    identifiers = []
    seen = set()
    for index, value in enumerate(re.split(r"[\s,;]+", str(text or "").strip()), 1):
        if not value:
            continue
        identifier = value
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", identifier):
            try:
                url = urlparse(value if "://" in value else "https://" + value)
            except ValueError:
                raise ValueError(f"Mục {index} không phải Video ID hoặc link YouTube hợp lệ.") from None
            host = (url.hostname or "").lower()
            parts = url.path.strip("/").split("/")
            identifier = ""
            if url.scheme in {"http", "https"}:
                if host in {"youtu.be", "www.youtu.be"} and len(parts) == 1:
                    identifier = parts[0]
                elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "studio.youtube.com"}:
                    if parts == ["watch"]:
                        identifier = parse_qs(url.query).get("v", [""])[0]
                    elif len(parts) >= 2 and parts[0] in {"video", "shorts", "live", "embed"}:
                        identifier = parts[1]
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", identifier):
                raise ValueError(f"Mục {index} không phải Video ID hoặc link YouTube hợp lệ. Mỗi Video ID có 11 ký tự.")
        if identifier not in seen:
            seen.add(identifier)
            identifiers.append(identifier)
        if len(identifiers) > 10_000:
            raise ValueError("Mỗi lượt chỉ đọc tối đa 10.000 Video ID.")
    if not identifiers:
        raise ValueError("Nhập ít nhất một Video ID hoặc link YouTube.")
    return identifiers


def scan_title_videos(channel_id: str, *, mode="count", scope="all", limit=50,
                      start_date="", end_date="", date_type="auto", title_contains="", progress=lambda message: None):
    if mode not in {"count", "dates"} or scope not in {"all", "public", "scheduled", "draft"}:
        raise ValueError("Chọn phạm vi quét video hợp lệ.")
    try:
        limit = int(limit)
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Số video phải từ 1 đến 10.000.") from None
    if not 1 <= limit <= 10_000:
        raise ValueError("Số video phải từ 1 đến 10.000.")
    bounds = None
    if mode == "dates":
        if not start_date or not end_date:
            raise ValueError("Chọn đủ ngày bắt đầu và ngày kết thúc.")
        try:
            last = date.fromisoformat(end_date)
            bounds = scan_date_bounds(start_date, end_date=last)
        except (ValueError, TypeError):
            raise ValueError("Khoảng ngày không hợp lệ; ngày kết thúc phải từ ngày bắt đầu trở đi.") from None
    videos, seen, tokens = [], set(), set()
    title_filter = str(title_contains or "").casefold()
    token = None
    while True:
        check_stopped()
        size = min(50, limit - len(videos)) if mode == "count" and not title_filter else 50
        kwargs = {"limit": size, "page_token": token, "include_all_origins": True}
        if scope == "draft":
            kwargs["draft_only"] = True
        page, next_token = list_videos_module.list_all_videos(channel_id, **kwargs)
        for video in page:
            check_stopped()
            if not video.id or video.id in seen:
                continue
            seen.add(video.id)
            if video.channel_id != channel_id:
                raise ValueError("YouTube trả về video không thuộc kênh đã chọn; đã dừng quét.")
            if scope == "public" and not _is_currently_public_video(video):
                continue
            if scope == "scheduled" and not _is_currently_scheduled_video(video):
                continue
            if not video_matches_scan_dates(video, bounds, date_type=normalize_scan_date_type(date_type)):
                continue
            if title_filter and title_filter not in str(video.title or "").casefold():
                continue
            videos.append(video)
            if mode == "count" and len(videos) == limit:
                break
        criterion = f' có chữ “{title_contains}”' if title_filter else ""
        progress(f"Đã đọc {len(seen)} video · {len(videos)} video{criterion} trong phạm vi đã chọn.")
        if not next_token or (mode == "count" and len(videos) >= limit):
            return videos
        if next_token in tokens:
            raise RuntimeError("YouTube trả về mã phân trang bị lặp; đã dừng quét.")
        tokens.add(next_token)
        token = next_token


def build_title_matches(rows, folder, *, recursive=True, tolerance=2.0,
                        duration_reader=None, progress=lambda message: None):
    tolerance = float(tolerance)
    if not math.isfinite(tolerance) or not 0 <= tolerance <= 60:
        raise ValueError("Mức lệch thời lượng phải từ 0 đến 60 giây.")
    duration_reader = duration_reader or get_video_duration
    files = scan_audio_files(folder, recursive=recursive)
    durations, unreadable = [], 0
    for index, path in enumerate(files, 1):
        check_stopped()
        try:
            seconds = float(duration_reader(str(path)))
            title = clean_video_title(path.stem)
            if not math.isfinite(seconds) or seconds <= 0:
                raise ValueError()
            durations.append((str(path), seconds, title))
        except TaskStopped:
            raise
        except Exception:
            check_stopped()
            unreadable += 1
        progress(f"Đọc thời lượng nhạc {index}/{len(files)} · không đọc được {unreadable} file.")
    matches = []
    for source in rows:
        check_stopped()
        row = dict(source)
        seconds = float(row.get("duration_seconds") or 0)
        row.update(audio_path="", audio_duration=None, delta=None, new_title="", candidates=[], selected=False)
        if not math.isfinite(seconds) or seconds <= 0:
            row.update(status="unmatched", detail="YouTube chưa trả về thời lượng video.")
            matches.append(row)
            continue
        candidates = [(abs(seconds - length), path, length, title)
                      for path, length, title in durations if abs(seconds - length) <= tolerance + 1e-6]
        if not candidates:
            row.update(status="unmatched", detail=f"Không có bài nhạc lệch tối đa {tolerance:g} giây.")
            matches.append(row)
            continue
        candidates.sort()
        nearest = [candidate for candidate in candidates if abs(candidate[0] - candidates[0][0]) < .01]
        # A duration tie may be resolved by the existing title, but never by
        # alphabetical filename order when the resulting titles would differ.
        hinted = [candidate for candidate in nearest if normalize_title(row["old_title"])
                  and normalize_title(row["old_title"]) in normalize_title(candidate[3])]
        if len(hinted) == 1:
            nearest = hinted
        row["candidates"] = [dict(path=p, seconds=s, title=t, delta=d) for d, p, s, t in candidates]
        if len({candidate[3] for candidate in nearest}) > 1:
            row.update(status="ambiguous", detail=f"Có {len(nearest)} bài khớp ngang nhau. Chọn lại file trước khi đổi.")
        else:
            delta, path, length, title = nearest[0]
            row.update(audio_path=path, audio_duration=length, delta=delta, new_title=title,
                       status="unchanged" if row["old_title"] == title else "ready", selected=row["old_title"] != title,
                       detail=f"Video {seconds:.2f}s · nhạc {length:.2f}s · lệch {delta:.2f}s.")
        matches.append(row)
    return matches, {"files": len(files), "unreadable": unreadable}


def default_title_settings():
    return {"channel_id": "", "mode": "count", "scope": "all", "limit": 50,
            "start_date": scan_today().isoformat(), "end_date": scan_today().isoformat(),
            "date_type": "auto", "folder": "", "recursive": True, "tolerance": 2.0, "manual_ids": ""}
