# RECOVERED: reconstructed from CPython 3.12 bytecode
"""
Refresh challenge & botguardResponse for a channel.

Opens a headless Chrome, injects stored cookies, navigates to YouTube Studio
analytics page, and captures the fresh tokens from the performance log.
"""

import json

from loguru import logger

from src.channel_store import channel_store
from src.cookie_utils import inject_cookies_via_cdp
from src.utils import create_driver, get_request_payload_from_performance_log
from src.task_runtime import unregister_driver


def refresh_challenge_and_botguard(
    channel_id: str, *, timeout: float = 20.0
) -> dict:
    """
    Refresh ``challenge`` and ``botguardResponse`` for *channel_id*.

    Returns a dict ``{"challenge": ..., "botguardResponse": ...}`` on success.
    Raises ``ValueError`` if the channel is not found in the database.
    """
    channel_store.init_db()
    rec = channel_store.get_channel(channel_id)
    if not rec:
        raise ValueError(f"Channel not found: {channel_id}")

    cookies = rec.get("cookies", []) or []
    driver = create_driver(enable_performance_log=True, start_offscreen=True)

    try:
        driver.get("https://studio.youtube.com/")
        inject_cookies_via_cdp(driver, cookies)

        target_url = (
            f"https://studio.youtube.com/channel/{channel_id}"
            "/analytics/tab-overview/period-default"
        )
        driver.get(target_url)

        payload = get_request_payload_from_performance_log(
            driver, "youtubei/v1/att/esr?alt=json", timeout=timeout
        )
        payload_json = json.loads(payload)
        challenge = payload_json.get("challenge")
        botguardResponse = payload_json.get("botguardResponse")

        channel_store.upsert_channel(
            {
                "id": channel_id,
                "name": rec.get("name", ""),
                "img_src": rec.get("img_src", ""),
                "delegated_session_id": rec.get("delegated_session_id", ""),
                "sapisidhash": rec.get("sapisidhash", ""),
                "role": rec.get("role", ""),
                "challenge": challenge,
                "botguardResponse": botguardResponse,
                "cookies": rec.get("cookies", []),
            }
        )
        logger.info(f"Refreshed challenge/botguard for {channel_id}")
        return {"challenge": challenge, "botguardResponse": botguardResponse}
    finally:
        try:
            driver.quit()
        finally:
            unregister_driver(driver)
