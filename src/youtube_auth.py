"""Helpers for short-lived YouTube Studio cookie authentication headers."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Iterable, Mapping


STUDIO_ORIGIN = "https://studio.youtube.com"


class MissingSapisidCookieError(RuntimeError):
    """Raised when stored channel cookies cannot authenticate Studio calls."""


def _sapisid_cookie_value(cookies: Iterable[Mapping] | None) -> str:
    for cookie in cookies or ():
        if not isinstance(cookie, Mapping):
            continue
        if str(cookie.get("name") or "") != "SAPISID":
            continue
        value = str(cookie.get("value") or "")
        if value:
            return value
    raise MissingSapisidCookieError(
        "Phiên đăng nhập không có cookie SAPISID; hãy đăng nhập và load lại kênh."
    )


def generate_sapisidhash(
    cookies: Iterable[Mapping] | None,
    *,
    origin: str = STUDIO_ORIGIN,
    timestamp: int | None = None,
) -> str:
    """Create a fresh timestamped SAPISIDHASH from the current cookie set."""
    sapisid = _sapisid_cookie_value(cookies)
    issued_at = int(time.time()) if timestamp is None else int(timestamp)
    digest = hashlib.sha1(
        f"{issued_at} {sapisid} {origin}".encode("utf-8")
    ).hexdigest()
    return f"{issued_at}_{digest}"


def sapisid_cookie_fingerprint(cookies: Iterable[Mapping] | None) -> str:
    """Return a non-secret stable cache discriminator for current cookies."""
    try:
        sapisid = _sapisid_cookie_value(cookies)
    except MissingSapisidCookieError:
        return ""
    return hashlib.sha256(sapisid.encode("utf-8")).hexdigest()


def studio_authorization_header(cookies: Iterable[Mapping] | None) -> str:
    """Return a fresh complete Authorization header value for one request."""
    return f"SAPISIDHASH {generate_sapisidhash(cookies)}"
