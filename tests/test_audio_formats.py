import tempfile
import unittest
from pathlib import Path

from src.utils import AUDIO_EXTENSIONS, AUDIO_INPUT_EXTENSIONS, validate_path_text


class AudioFormatTests(unittest.TestCase):
    def test_manual_audio_path_accepts_all_supported_audio_extensions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for extension in sorted(AUDIO_EXTENSIONS):
                with self.subTest(extension=extension):
                    audio_file = Path(temp_dir) / f"audio{extension.upper()}"
                    audio_file.write_bytes(b"audio")
                    self.assertEqual(validate_path_text(str(audio_file)), (True, None))

    def test_m4a_and_common_audio_formats_are_supported(self):
        self.assertTrue(
            {".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}
            <= AUDIO_INPUT_EXTENSIONS
        )

    def test_unknown_extension_is_rejected_with_supported_list(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as unknown_file:
            valid, message = validate_path_text(unknown_file.name)

        self.assertFalse(valid)
        self.assertIn(".m4a", message)
        self.assertIn(".flac", message)


if __name__ == "__main__":
    unittest.main()
