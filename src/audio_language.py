"""Language parsing and retry helpers for YouTube audio tracks."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable


_LANGUAGE_SEPARATOR_RE = re.compile(r"[\s,;]+")
_LANGUAGE_CODE_RE = re.compile(
    r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$"
)


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
) -> int:
    """Run one blocking audio update with exponential backoff.

    Only errors explicitly marked ``retryable`` (or retryable HTTP status
    values returned directly) are retried. Other failures are returned to the
    caller immediately so the caller can record them and continue with the
    next language.
    """
    for attempt in range(max_retries + 1):
        try:
            status = await asyncio.to_thread(operation)
            if status in (200, 409):
                return status
            error = RuntimeError(f"YouTube returned HTTP {status}")
            error.retryable = status == 429 or status >= 500  # type: ignore[attr-defined]
            raise error
        except Exception as exc:
            retryable = bool(getattr(exc, "retryable", False))
            if not retryable or attempt >= max_retries:
                raise
            delay = base_delay * (2**attempt)
            if on_retry is not None:
                on_retry(attempt + 1, delay, exc)
            await sleep(delay)

    raise RuntimeError("Audio update retry loop ended unexpectedly")
