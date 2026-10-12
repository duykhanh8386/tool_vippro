import tempfile
import unittest
from pathlib import Path

from src.utils import (
    AUDIO_EXTENSIONS,
    AUDIO_INPUT_EXTENSIONS,
    list_media_files,
    validate_path_text,
)


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

    def test_manual_audio_paths_preserve_filesystem_unicode(self):
        filenames = (
            "Christmas \U0001f636\u200d\U0001f32b\ufe0f.mp3",
            "Family \U0001f468\u200d\U0001f469\u200d\U0001f467.mp3",
            "Runner \U0001f3c3\U0001f3fd\u200d\u2640\ufe0f.mp3",
            "Flag \U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f.mp3",
            "Nhac gia\u0301ng sinh.mp3",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            for filename in filenames:
                with self.subTest(filename=filename):
                    audio_file = Path(temp_dir) / filename
                    audio_file.write_bytes(b"audio")
                    self.assertEqual(validate_path_text(str(audio_file)), (True, None))

    def test_media_folder_scan_preserves_joined_emoji_and_combining_accents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir) / "Gia\u0301ng sinh \U0001f636\u200d\U0001f32b\ufe0f"
            folder.mkdir()
            audio_file = folder / "Family \U0001f468\u200d\U0001f469.mp3"
            audio_file.write_bytes(b"audio")

            self.assertEqual(list_media_files(str(folder), AUDIO_EXTENSIONS), [audio_file])
            self.assertEqual(validate_path_text(str(audio_file)), (True, None))

    def test_unknown_extension_is_rejected_with_supported_list(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as unknown_file:
            valid, message = validate_path_text(unknown_file.name)

        self.assertFalse(valid)
        self.assertIn(".m4a", message)
        self.assertIn(".flac", message)


if __name__ == "__main__":
    unittest.main()
