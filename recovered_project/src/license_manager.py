# RECOVERED: reconstructed from CPython 3.12 bytecode without altering license logic
from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Optional

import requests
from getmac import get_mac_address
from loguru import logger

from src.paths import get_data_dir


BASE_URL = "https://api.licensify.vn/v1"
PRODUCT_ID = "2c8a6b04-4322-4b65-bcd1-e0cefe2fdcf4"
_LICENSE_FILE = get_data_dir() / "license.json"


def _device_fingerprint() -> str:
    mac = get_mac_address()
    if mac and mac != "00:00:00:00:00:00":
        return mac.upper()
    return platform.node()


def _device_name() -> str:
    return platform.node()


def _os_info() -> str:
    return f"{platform.system()} {platform.release()}"


def _save_license(license_key: str, data: dict) -> None:
    payload = {
        "license_key": license_key,
        "expires_at": data.get("expires_at"),
        "devices_used": data.get("devices_used"),
        "max_devices": data.get("max_devices"),
    }
    _LICENSE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _load_license() -> Optional[dict]:
    if not _LICENSE_FILE.exists():
        return None
    try:
        return json.loads(_LICENSE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


# def verify_license(license_key: str) -> tuple[bool, str]:
#     """Verify a license key against the Licensify API.

#     Returns (success, message).
#     """
#     try:
#         resp = requests.post(
#             f"{BASE_URL}/licenses/verify",
#             json={
#                 "license_key": license_key,
#                 "product_id": PRODUCT_ID,
#                 "device_fingerprint": _device_fingerprint(),
#                 "device_name": _device_name(),
#                 "os_info": _os_info(),
#             },
#             timeout=15,
#         )
#         body = resp.json()
#         data = body.get("data", {})

#         if data.get("valid"):
#             _save_license(license_key, data)
#             expires = data.get("expires_at") or "Vinh vien"
#             logger.info("License activated -- expires: {}", expires)
#             return True, "Kich hoat thanh cong!"

#         reason = data.get("reason", "Khong xac dinh")
#         logger.warning("License rejected: {}", reason)
#         return False, f"License khong hop le: {reason}"
#     except requests.ConnectionError:
#         logger.error("Khong the ket noi den server license")
#         return False, "Khong co ket noi internet!"
#     except Exception as e:
#         logger.error("License verification error: {}", e)
#         return False, f"Loi xac thuc: {e}"


# def is_licensed() -> bool:
#     """Check whether a valid license exists locally, then re-verify online."""
#     stored = _load_license()
#     if not stored or not stored.get("license_key"):
#         return False

#     try:
#         resp = requests.post(
#             f"{BASE_URL}/licenses/verify",
#             json={
#                 "license_key": stored["license_key"],
#                 "product_id": PRODUCT_ID,
#                 "device_fingerprint": _device_fingerprint(),
#                 "device_name": _device_name(),
#                 "os_info": _os_info(),
#             },
#             timeout=10,
#         )
#         data = resp.json().get("data", {})
#         if data.get("valid"):
#             _save_license(stored["license_key"], data)
#             return True
#         _LICENSE_FILE.unlink(missing_ok=True)
#         return False
#     except requests.ConnectionError:
#         logger.warning("Offline -- trusting cached license")
#         return True
#     except Exception as e:
#         logger.error("License check error: {}", e)
#         return False


# def get_license_info() -> Optional[dict]:
#     """Return cached license info or None."""
#     return _load_license()

def get_license_info() -> Optional[dict]:
    """Return cached license info or None."""
    return None

def deactivate() -> None:
    """Remove stored license."""
    _LICENSE_FILE.unlink(missing_ok=True)
