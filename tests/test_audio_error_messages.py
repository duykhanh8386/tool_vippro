import unittest

import requests

from src.audio_language import audio_error_message, summarize_audio_errors


class AudioErrorMessageTests(unittest.TestCase):
    def test_network_errors_do_not_expose_signed_urls_or_connection_traces(self):
        for kind in (requests.exceptions.SSLError, requests.exceptions.Timeout,
                     requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError):
            with self.subTest(kind=kind):
                message = audio_error_message(kind("HTTPSConnectionPool https://upload.youtube.com/?secret=private"))
                self.assertLess(len(message), 120)
                self.assertNotIn("private", message)
                self.assertNotIn("ConnectionPool", message)

    def test_saved_error_strings_are_sanitized_without_losing_the_failure_code(self):
        message = audio_error_message("AUDIO_TRACK_STATUS_FAILED\nhttps://upload.youtube.com/?token=private " + "x" * 2000)
        self.assertIn("AUDIO_TRACK_STATUS_FAILED", message)
        self.assertNotIn("private", message)
        self.assertNotIn("\n", message)
        self.assertLessEqual(len(message), 280)

    def test_many_languages_do_not_create_an_unbounded_error_summary(self):
        errors = [f"language-{i}: rejected " + "details " * 500 for i in range(100)]
        message = summarize_audio_errors(errors)
        self.assertIn("language-0: rejected", message)
        self.assertIn("99 lỗi khác", message)
        self.assertLess(len(message), 240)
        self.assertEqual(summarize_audio_errors([]), "")
