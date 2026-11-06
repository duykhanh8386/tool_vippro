"""Language parsing and retry helpers for YouTube audio tracks."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable

import requests


_LANGUAGE_SEPARATOR_RE = re.compile(r"[\s,;]+")
_LANGUAGE_CODE_RE = re.compile(
    r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$"
)


def audio_error_message(error: BaseException | str, *, max_length: int = 280) -> str:
    """Keep UI/checkpoint errors concise without exposing upload session URLs."""
    message = " ".join(str(error).split())
    if isinstance(error, requests.exceptions.SSLError) or "SSLError(" in message:
        return "Kết nối bảo mật tới YouTube bị gián đoạn. Hãy thử lại phần audio lỗi."
    if isinstance(error, requests.exceptions.Timeout):
        return "Hết thời gian chờ YouTube phản hồi. Hãy thử lại phần audio lỗi."
    if isinstance(error, (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError)) or "HTTPSConnectionPool(" in message:
        return "Kết nối tới YouTube bị gián đoạn. Hãy thử lại phần audio lỗi."
    message = re.sub(r"https?://\S+", "[địa chỉ tải lên]", message)
    return message if len(message) <= max_length else message[:max_length - 1] + "…"


def summarize_audio_errors(errors: list[str]) -> str:
    """Show one actionable error; keep per-language details in their own rows."""
    if not errors:
        return ""
    first = audio_error_message(errors[0], max_length=160)
    return first + (f" (+{len(errors) - 1} lỗi khác; xem chi tiết từng ngôn ngữ)." if len(errors) > 1 else "")


def normalize_language_code(code: str) -> str:
    """Return a consistently cased BCP-47-style language code."""
    parts = code.strip().split("-")
    normalized = []
    for index, part in enumerate(parts):
        if index == 0:
            normalized.append(part.lower())
        elif len(part) == 4 and part.isalpha():
            normalized.append(part.title())
        elif (len(part) == 2 and part.isalpha()) or (
            len(part) == 3 and part.isdigit()
        ):
            normalized.append(part.upper())
        else:
            normalized.append(part.lower())
    return "-".join(normalized)


def parse_language_codes(text: str | None) -> list[str]:
    """Parse whitespace/comma-separated codes and deduplicate them."""
    seen = set()
    result = []
    for token in _LANGUAGE_SEPARATOR_RE.split((text or "").strip()):
        if not token:
            continue
        language = normalize_language_code(token)
        if language in seen:
            continue
        seen.add(language)
        result.append(language)
    return result


def invalid_language_codes(codes: list[str]) -> list[str]:
    """Return malformed codes; availability is still decided by YouTube."""
    return [code for code in codes if not _LANGUAGE_CODE_RE.fullmatch(code)]


async def call_audio_update_with_retry(
    operation: Callable[[], int],
    *,
    max_retries: int = 3,
    base_delay: float = 2.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    on_retry: Callable[[int, float, BaseException], None] | None = None,
    run_blocking: Callable[[Callable[[], int]], Awaitable[int]] | None = None,
) -> int:
    """Run one blocking audio update with exponential backoff.

    Only errors explicitly marked ``retryable`` (or retryable HTTP status
    values returned directly) are retried. Other failures are returned to the
    caller immediately so the caller can record them and continue with the
    next language.
    """
    for attempt in range(max_retries + 1):
        try:
            status = await (run_blocking or asyncio.to_thread)(operation)
            if status in (200, 409):
                return status
            error = RuntimeError(f"YouTube returned HTTP {status}")
            error.retryable = status == 429 or status >= 500  # type: ignore[attr-defined]
            raise error
        except Exception as exc:
            retryable = bool(getattr(exc, "retryable", False)) or isinstance(
                exc,
                (
                    requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.SSLError,
                    requests.exceptions.ChunkedEncodingError,
                ),
            )
            if not retryable or attempt >= max_retries:
                raise
            delay = base_delay * (2**attempt)
            if on_retry is not None:
                on_retry(attempt + 1, delay, exc)
            await sleep(delay)

    raise RuntimeError("Audio update retry loop ended unexpectedly")
