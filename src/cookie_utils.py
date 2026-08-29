# RECOVERED: reconstructed from CPython 3.12 bytecode
"""
Cookie utilities: normalise Selenium cookies for storage and inject via CDP.
"""

from loguru import logger


_SAMESITE_SELENIUM_TO_STORAGE = {
    "Lax": "lax",
    "Strict": "strict",
    "None": "unspecified",
}


def normalize_cookies_for_storage(selenium_cookies: list) -> list:
    """Convert Selenium-format cookies to a browser-export-like format."""
    result = []
    for c in selenium_cookies:
        domain = c.get("domain", "")
        cookie = {
            "domain": domain,
            "hostOnly": not str(domain).startswith("."),
            "httpOnly": c.get("httpOnly", False),
            "name": c.get("name", ""),
            "path": c.get("path", "/"),
            "sameSite": _SAMESITE_SELENIUM_TO_STORAGE.get(
                c.get("sameSite", "None"), "unspecified"
            ),
            "secure": c.get("secure", False),
            "session": "expiry" not in c and not c.get("expirationDate"),
            "storeId": "0",
            "value": c.get("value", ""),
        }
        if "expiry" in c:
            cookie["expirationDate"] = float(c["expiry"])
        elif c.get("expirationDate") is not None:
            cookie["expirationDate"] = float(c["expirationDate"])
        result.append(cookie)
    return result


_SAMESITE_STORAGE_TO_CDP = {
    "lax": "Lax",
    "strict": "Strict",
    "unspecified": "None",
    "no_restriction": "None",
}


def inject_cookies_via_cdp(driver, cookies: list) -> int:
    """Inject cookies using Chrome DevTools Protocol. Returns attempted count."""
    driver.execute_cdp_cmd("Network.enable", {})

    attempted = 0
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if not name or value is None:
            continue
        attempted += 1

        domain = cookie.get("domain") or ".youtube.com"
        if "youtube" in domain.lower():
            req_url = "https://studio.youtube.com"
        elif "google" in domain.lower():
            req_url = "https://www.google.com"
        else:
            req_url = "https://studio.youtube.com"

        cdp_params = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": cookie.get("path", "/"),
            "url": req_url,
            "secure": bool(cookie.get("secure", False)),
            "httpOnly": bool(cookie.get("httpOnly", False)),
        }

        expires = cookie.get("expirationDate") or cookie.get("expiry")
        if expires is not None:
            cdp_params["expires"] = float(expires)

        raw_ss = cookie.get("sameSite", "unspecified")
        cdp_params["sameSite"] = _SAMESITE_STORAGE_TO_CDP.get(raw_ss.lower(), "None")

        try:
            driver.execute_cdp_cmd("Network.setCookie", cdp_params)
        except Exception:
            logger.debug(f"Failed to inject cookie: {name}")

    return attempted
