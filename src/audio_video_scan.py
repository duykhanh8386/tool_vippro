"""Shared channel-video scopes for manual audio tasks."""

from src.audio_recovery import _is_currently_public_video, _is_currently_scheduled_video
from src.module.list_videos_module import list_videos_module
from src.video_scan_dates import DEFAULT_SCAN_DATE_TYPE, scan_date_bounds, video_matches_scan_dates


DEFAULT_RECENT_VIDEO_LIMIT = 50
MAX_RECENT_VIDEO_LIMIT = 10_000
VIDEO_SCAN_SCOPE_OPTIONS = {
    "all": "Tất cả video",
    "public": "Chỉ công khai",
    "scheduled": "Đã lên lịch",
    "draft": "Bản nháp",
    "recent": "Đăng gần nhất",
}
VIDEO_SCAN_SCOPES = set(VIDEO_SCAN_SCOPE_OPTIONS)
VIDEO_SCAN_SCOPE_LABELS = {
    "all": "tất cả video",
    "public": "video công khai",
    "scheduled": "video đã lên lịch",
    "draft": "video bản nháp",
    "recent": "video đăng gần nhất",
}


def _normalize_recent_video_limit(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_RECENT_VIDEO_LIMIT
    return max(1, min(MAX_RECENT_VIDEO_LIMIT, parsed))


def _fetch_channel_videos(
    channel_id: str,
    *,
    scope: str = "all",
    recent_limit: int = DEFAULT_RECENT_VIDEO_LIMIT,
    start_date: str = "",
    date_type: str = DEFAULT_SCAN_DATE_TYPE,
):
    """Apply scope and upload dates before counting a recent/draft limit."""
    normalized_scope = scope if scope in VIDEO_SCAN_SCOPES else "all"
    normalized_limit = _normalize_recent_video_limit(recent_limit)
    date_bounds = scan_date_bounds(start_date)
    videos = []
    seen_ids = set()
    seen_tokens = set()
    page_token = None
    while True:
        page_size = 50
        if normalized_scope in {"recent", "draft"}:
            page_size = min(50, normalized_limit - len(videos))
        list_kwargs = {"limit": page_size, "page_token": page_token}
        if normalized_scope == "draft":
            list_kwargs["draft_only"] = True
        page, next_token = list_videos_module.list_all_videos(channel_id, **list_kwargs)
        for video in page:
            if not video.id or video.id in seen_ids:
                continue
            seen_ids.add(video.id)
            if normalized_scope == "public" and not _is_currently_public_video(video):
                continue
            if normalized_scope == "scheduled" and not _is_currently_scheduled_video(video):
                continue
            if not video_matches_scan_dates(video, date_bounds, date_type=date_type):
                continue
            videos.append(video)
            if normalized_scope in {"recent", "draft"} and len(videos) >= normalized_limit:
                return videos
        if not next_token:
            return videos
        if next_token in seen_tokens:
            raise RuntimeError("YouTube trả về mã phân trang bị lặp; đã dừng quét để tránh treo.")
        seen_tokens.add(next_token)
        page_token = next_token


def _fetch_all_channel_videos(channel_id: str):
    """Backward-compatible all-video scan used by manual audio tasks."""
    return _fetch_channel_videos(channel_id, scope="all")
