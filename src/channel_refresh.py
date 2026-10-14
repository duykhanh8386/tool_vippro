# RECOVERED: reconstructed from CPython 3.12 bytecode
"""
Refresh challenge & botguardResponse for a channel.

Opens a headless Chrome, injects stored cookies, navigates to YouTube Studio
analytics page, and captures the fresh tokens from the performance log.
"""

import json
from urllib.parse import urlparse

from loguru import logger

from src.channel_store import channel_store
from src.cookie_utils import inject_cookies_via_cdp, normalize_cookies_for_storage
from src.utils import create_driver, get_request_payload_from_performance_log
from src.task_runtime import unregister_driver
from src.youtube_auth import generate_sapisidhash


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
        driver.get_log("performance")

        target_url = (
            f"https://studio.youtube.com/channel/{channel_id}"
            "/analytics/tab-overview/period-default"
        )
        driver.get(target_url)
        if urlparse(str(driver.current_url)).hostname != "studio.youtube.com":
            raise RuntimeError("Phiên đăng nhập đã hết hiệu lực; hãy đăng nhập và load lại đúng kênh.")

        payload = get_request_payload_from_performance_log(
            driver, "youtubei/v1/att/esr?alt=json", timeout=timeout
        )
        payload_json = json.loads(payload)
        challenge = payload_json.get("challenge")
        botguardResponse = payload_json.get("botguardResponse")
        if not challenge or not botguardResponse:
            raise RuntimeError("Không lấy được dữ liệu xác thực mới từ YouTube Studio.")
        studio_context = payload_json.get("context") or {}
        if not isinstance(studio_context, dict):
            raise RuntimeError("YouTube Studio trả về context xác thực không hợp lệ.")
        user = studio_context.get("user") or {}
        delegation = user.get("delegationContext") or {}
        captured_channel_id = delegation.get("externalChannelId")
        if captured_channel_id and captured_channel_id != channel_id:
            raise RuntimeError("Phiên Studio đang ở kênh khác; hãy đăng nhập và chọn đúng kênh.")
        cookies = normalize_cookies_for_storage(driver.get_cookies())
        role = (delegation.get("roleType") or {}).get("channelRoleType") or rec.get("role", "")

        channel_store.upsert_channel(
            {
                "id": channel_id,
                "name": rec.get("name", ""),
                "img_src": rec.get("img_src", ""),
                "delegated_session_id": user.get("onBehalfOfUser") or rec.get("delegated_session_id", ""),
                # Compatibility snapshot only. Callers generate a fresh
                # timestamped hash from these cookies for every request.
                "sapisidhash": generate_sapisidhash(cookies),
                "role": role,
                "challenge": challenge,
                "botguardResponse": botguardResponse,
                "cookies": cookies,
                "studio_context": studio_context,
            }
        )
        logger.info(f"Refreshed challenge/botguard for {channel_id}")
        return {"challenge": challenge, "botguardResponse": botguardResponse}
    finally:
        try:
            driver.quit()
        finally:
            unregister_driver(driver)
