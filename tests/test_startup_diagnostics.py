import sys
import types
import unittest
from unittest.mock import patch

from src.startup_diagnostics import quarantine_invalid_brotlicffi


class BrotlicffiStartupTests(unittest.TestCase):
    def test_quarantines_incomplete_brotlicffi(self):
        incomplete = types.ModuleType("brotlicffi")
        with patch.dict(sys.modules, {"brotlicffi": incomplete}):
            self.assertTrue(quarantine_invalid_brotlicffi())
            self.assertIsNone(sys.modules["brotlicffi"])

    def test_keeps_valid_brotlicffi(self):
        valid = types.ModuleType("brotlicffi")
        valid.error = type("BrotliError", (Exception,), {})
        valid.Decompressor = type("Decompressor", (), {})
        with patch.dict(sys.modules, {"brotlicffi": valid}):
            self.assertFalse(quarantine_invalid_brotlicffi())
            self.assertIs(sys.modules["brotlicffi"], valid)


if __name__ == "__main__":
    unittest.main()
