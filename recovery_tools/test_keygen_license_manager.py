import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "recovered_project"))

from src import license_manager


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body or {}
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._body


LICENSE_DATA = {
    "id": "license-id",
    "type": "licenses",
    "attributes": {
        "expiry": "2030-01-01T00:00:00.000Z",
        "status": "ACTIVE",
        "maxMachines": 10,
    },
}


class KeygenLicenseManagerTests(unittest.TestCase):
    def setUp(self):
        workspace_tmp = Path(__file__).resolve().parents[1] / "work"
        self.license_path = workspace_tmp / f"keygen_test_license_{os.getpid()}.json"
        self.license_path.unlink(missing_ok=True)
        self.path_patch = patch.object(
            license_manager, "_LICENSE_FILE", self.license_path
        )
        self.fingerprint_patch = patch.object(
            license_manager, "_device_fingerprint", return_value="fingerprint"
        )
        self.path_patch.start()
        self.fingerprint_patch.start()

    def tearDown(self):
        self.fingerprint_patch.stop()
        self.path_patch.stop()
        self.license_path.unlink(missing_ok=True)

    def test_validate_activate_revalidate_cache_and_deactivate(self):
        validation_missing = FakeResponse(
            200,
            {
                "meta": {
                    "valid": False,
                    "code": "NO_MACHINES",
                    "detail": "No machines",
                },
                "data": LICENSE_DATA,
            },
        )
        activation = FakeResponse(201, {"data": {"id": "machine-id"}})
        validation_valid = FakeResponse(
            200,
            {
                "meta": {"valid": True, "code": "VALID", "detail": "Valid"},
                "data": LICENSE_DATA,
            },
        )
        with patch.object(
            license_manager.requests,
            "post",
            side_effect=[validation_missing, activation, validation_valid],
        ) as mocked_post:
            valid, message = license_manager.verify_license("test-key")

        self.assertTrue(valid, message)
        self.assertEqual(mocked_post.call_count, 3)
        self.assertEqual(license_manager.get_license_info()["machine_id"], "machine-id")

        with patch.object(license_manager.requests, "post") as mocked_post:
            self.assertTrue(license_manager.is_licensed())
            mocked_post.assert_not_called()

        with patch.object(
            license_manager.requests, "delete", return_value=FakeResponse(204)
        ) as mocked_delete:
            license_manager.deactivate()
            mocked_delete.assert_called_once()
        self.assertFalse(self.license_path.exists())

    def test_invalid_key_is_not_saved(self):
        invalid = FakeResponse(
            200,
            {
                "meta": {
                    "valid": False,
                    "code": "NOT_FOUND",
                    "detail": "License not found",
                },
                "data": {},
            },
        )
        with patch.object(license_manager.requests, "post", return_value=invalid):
            valid, _ = license_manager.verify_license("invalid")
        self.assertFalse(valid)
        self.assertFalse(self.license_path.exists())


if __name__ == "__main__":
    unittest.main()
