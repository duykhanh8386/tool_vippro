# RECOVERED: reconstructed from CPython 3.12 bytecode
import base64
import hashlib
import hmac
import json
import os
import pickle
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import psutil
from getmac import get_mac_address
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


@dataclass
class ChannelInfo:
    """Typed container for a YouTube channel's credentials and metadata."""

    id: str
    name: str
    sapisidhash: str
    delegated_session_id: str
    role: str
    challenge: str
    botguardResponse: str
    img_src: str
    cookies: list = field(default_factory=list)
    cookies_expires_at: Optional[int] = None
    overlay_png: str = ""

    def cookie_string(self) -> str:
        """Return cookies formatted as a single header string."""
        return "; ".join(f"{c['name']}={c['value']}" for c in self.cookies)

    def cookie_dict(self) -> dict:
        """Return cookies as a name→value dict."""
        return {c["name"]: c["value"] for c in self.cookies}


@dataclass
class Video:
    id: str
    channel_id: str
    title: str
    description: str
    thumbnail: str
    duration_ms: int
    privacy: str = ""
    video_status: str = ""
    copyright_check_status: str = ""


class AuthSignal(Enum):
    ACTIVATED = "Key kích hoạt thành công!!!"
    KEY_EXPIRED = "Key đã hết thời gian kích hoạt!!!"
    APP_EXPIRED = "Tool đã hết thời gian sử dụng!!!"
    INVALID = "Key không chính xác!!!"
    ERROR = "Key không hợp lệ!!!"
    NO_INTERNET = "Không có kết nối internet!!! Vui lòng kiểm tra lại kết nối của bạn!"
    USED = "Key đã được sử dụng!!!"


class VideoType(Enum):
    PRIVATE = "VIDEO_PRIVACY_PRIVATE"
    PUBLIC = "VIDEO_PRIVACY_PUBLIC"
    UNLISTED = "VIDEO_PRIVACY_UNLISTED"


@dataclass
class AuthKey:
    key: str
    expiration_time: int
    app_expiration_time: int
    auth_signal: AuthSignal
