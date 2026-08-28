"""Keygen-backed licensing for TV Automation.

Only public Keygen resource identifiers are embedded here. Administrative,
environment, and product tokens must never be shipped with the application.
"""

from __future__ import annotations

import hashlib
import json
import platform
import time
from typing import Optional

import requests
from getmac import get_mac_address
from loguru import logger

from src.paths import get_data_dir


KEYGEN_ACCOUNT_ID = "fe587f43-390a-4e00-a8b2-0c69d2f3629c"
KEYGEN_PRODUCT_ID = "f30b2ff1-6393-418a-8473-6ddf46eb227f"
KEYGEN_POLICY_ID = "a4ab8481-7144-4ba2-92a0-9e854544eb67"
KEYGEN_API_URL = f"https://api.keygen.sh/v1/accounts/{KEYGEN_ACCOUNT_ID}"

_LICENSE_FILE = get_data_dir() / "license.json"
_REQUEST_TIMEOUT = 15
_ONLINE_CACHE_SECONDS = 300
_JSON_HEADERS = {
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
}


def _windows_machine_guid() -> Optional[str]:
    if platform.system() != "Windows":
        return None
    try:
        import winreg

        access = winreg.KEY_READ
        if hasattr(winreg, "KEY_WOW64_64KEY"):
            access |= winreg.KEY_WOW64_64KEY
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            access,
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value)
    except (OSError, ValueError):
        return None


def _device_fingerprint() -> str:
    """Return a stable, anonymized fingerprint for the current machine."""
    source = _windows_machine_guid()
    if not source:
        mac = get_mac_address()
        source = mac if mac and mac != "00:00:00:00:00:00" else platform.node()
    material = f"tv-automation:{source}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _device_name() -> str:
    return platform.node() or "Unknown device"


def _load_license() -> Optional[dict]:
    if not _LICENSE_FILE.exists():
        return None
    try:
        data = json.loads(_LICENSE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        logger.warning("Stored license data is unreadable")
        return None


def _save_license(license_key: str, license_data: dict, **extra: object) -> None:
    attributes = license_data.get("attributes") or {}
    machines = (license_data.get("relationships") or {}).get("machines") or {}
    machine_items = machines.get("data")
    devices_used = len(machine_items) if isinstance(machine_items, list) else None
    previous = _load_license() or {}
    payload = {
        "license_key": license_key,
        "license_id": license_data.get("id") or previous.get("license_id"),
        "machine_id": extra.get("machine_id") or previous.get("machine_id"),
        "fingerprint": _device_fingerprint(),
        "expires_at": attributes.get("expiry"),
        "status": attributes.get("status"),
        "devices_used": devices_used,
        "max_devices": attributes.get("maxMachines"),
        "last_verified_at": int(time.time()),
        "validation_code": extra.get("validation_code", "VALID"),
    }
    _LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LICENSE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _response_json(response: requests.Response) -> dict:
    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Keygen returned HTTP {response.status_code}") from exc
    if not isinstance(body, dict):
        raise RuntimeError("Keygen returned an invalid response")
    return body


def _error_message(body: dict, fallback: str) -> str:
    errors = body.get("errors") or []
    if errors and isinstance(errors[0], dict):
        return errors[0].get("detail") or errors[0].get("title") or fallback
    return fallback


def _validate(license_key: str) -> tuple[bool, str, dict, str]:
    response = requests.post(
        f"{KEYGEN_API_URL}/licenses/actions/validate-key",
        headers=_JSON_HEADERS,
        json={
            "meta": {
                "key": license_key,
                "scope": {
                    "product": KEYGEN_PRODUCT_ID,
                    "policy": KEYGEN_POLICY_ID,
                    "fingerprint": _device_fingerprint(),
                },
            }
        },
        timeout=_REQUEST_TIMEOUT,
    )
    body = _response_json(response)
    meta = body.get("meta") or {}
    code = str(meta.get("code") or "UNKNOWN")
    detail = str(meta.get("detail") or _error_message(body, "License is invalid"))
    data = body.get("data") or {}
    return bool(meta.get("valid")), code, data, detail


def _activate_machine(license_key: str, license_id: str) -> str:
    response = requests.post(
        f"{KEYGEN_API_URL}/machines",
        headers={**_JSON_HEADERS, "Authorization": f"License {license_key}"},
        json={
            "data": {
                "type": "machines",
                "attributes": {
                    "fingerprint": _device_fingerprint(),
                    "name": _device_name(),
                    "platform": platform.system(),
                },
                "relationships": {
                    "license": {
                        "data": {"type": "licenses", "id": license_id}
                    }
                },
            }
        },
        timeout=_REQUEST_TIMEOUT,
    )
    body = _response_json(response)
    if not response.ok:
        raise RuntimeError(_error_message(body, "Could not activate this device"))
    machine = body.get("data") or {}
    machine_id = machine.get("id")
    if not machine_id:
        raise RuntimeError("Keygen did not return a machine ID")
    return str(machine_id)


def verify_license(license_key: str) -> tuple[bool, str]:
    """Validate a key and activate this machine when necessary."""
    license_key = (license_key or "").strip()
    if not license_key:
        return False, "Vui lòng nhập license key."

    try:
        valid, code, data, detail = _validate(license_key)
        machine_id = None
        if not valid and code in {"NO_MACHINES", "FINGERPRINT_SCOPE_MISMATCH"}:
            license_id = data.get("id")
            if not license_id:
                return False, "Keygen không trả về license ID."
            machine_id = _activate_machine(license_key, str(license_id))
            valid, code, data, detail = _validate(license_key)

        if valid:
            _save_license(
                license_key,
                data,
                machine_id=machine_id,
                validation_code=code,
            )
            logger.info("Keygen license activated for this device")
            return True, "Kích hoạt license thành công!"

        logger.warning("Keygen license rejected: {} - {}", code, detail)
        return False, f"License không hợp lệ: {detail} ({code})"
    except requests.ConnectionError:
        return False, "Không thể kết nối tới máy chủ license."
    except requests.Timeout:
        return False, "Máy chủ license phản hồi quá chậm."
    except Exception as exc:
        logger.exception("Keygen activation failed")
        return False, f"Lỗi kích hoạt license: {exc}"


def is_licensed() -> bool:
    """Return whether the cached key is currently valid for this machine."""
    stored = _load_license()
    if not stored or not stored.get("license_key"):
        return False
    if stored.get("fingerprint") != _device_fingerprint():
        return False

    last_verified = stored.get("last_verified_at")
    if isinstance(last_verified, int):
        if time.time() - last_verified < _ONLINE_CACHE_SECONDS:
            return True

    try:
        valid, code, data, detail = _validate(stored["license_key"])
        if valid:
            _save_license(stored["license_key"], data, validation_code=code)
            return True
        logger.warning("Stored Keygen license rejected: {} - {}", code, detail)
        return False
    except (requests.ConnectionError, requests.Timeout):
        logger.warning("Keygen is unreachable; online validation is required")
        return False
    except Exception:
        logger.exception("Keygen license validation failed")
        return False


def get_license_info() -> Optional[dict]:
    """Return locally cached license information for the existing UI."""
    return _load_license()


def _find_current_machine_id(license_key: str) -> Optional[str]:
    response = requests.get(
        f"{KEYGEN_API_URL}/machines",
        headers={**_JSON_HEADERS, "Authorization": f"License {license_key}"},
        timeout=_REQUEST_TIMEOUT,
    )
    body = _response_json(response)
    if not response.ok:
        return None
    fingerprint = _device_fingerprint()
    for machine in body.get("data") or []:
        if (machine.get("attributes") or {}).get("fingerprint") == fingerprint:
            return machine.get("id")
    return None


def deactivate() -> None:
    """Deactivate this machine and remove the locally stored key."""
    stored = _load_license()
    if not stored:
        return
    license_key = stored.get("license_key")
    machine_id = stored.get("machine_id")
    try:
        if license_key and not machine_id:
            machine_id = _find_current_machine_id(license_key)
        if license_key and machine_id:
            response = requests.delete(
                f"{KEYGEN_API_URL}/machines/{machine_id}",
                headers={**_JSON_HEADERS, "Authorization": f"License {license_key}"},
                timeout=_REQUEST_TIMEOUT,
            )
            if response.status_code not in {204, 404}:
                body = _response_json(response)
                raise RuntimeError(_error_message(body, "Could not deactivate device"))
    finally:
        _LICENSE_FILE.unlink(missing_ok=True)
