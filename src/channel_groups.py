"""Gmail grouping shared by channel views."""

from collections import Counter


ALL_GMAILS = "__all_gmails__"
UNKNOWN_GMAIL = "__unknown_gmail__"


def channel_gmail(channel) -> str:
    return str(getattr(channel, "owner_email", "") or "").strip().casefold()


def gmail_filter_options(channels) -> dict[str, str]:
    counts = Counter(channel_gmail(channel) for channel in channels)
    options = {ALL_GMAILS: f"Tất cả Gmail ({len(channels)} kênh)"}
    for gmail in sorted(email for email in counts if email):
        options[gmail] = f"{gmail} ({counts[gmail]} kênh)"
    if counts[""]:
        options[UNKNOWN_GMAIL] = f"Chưa xác định Gmail ({counts['']} kênh)"
    return options


def filter_channels_by_gmail(channels, selected_gmail: str):
    if selected_gmail == ALL_GMAILS:
        return list(channels)
    if selected_gmail == UNKNOWN_GMAIL:
        return [channel for channel in channels if not channel_gmail(channel)]
    return [
        channel for channel in channels
        if channel_gmail(channel) == selected_gmail
    ]
