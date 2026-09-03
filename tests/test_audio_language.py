import asyncio
import unittest

from src.audio_language import (
    call_audio_update_with_retry,
    invalid_language_codes,
    parse_language_codes,
)


class AudioLanguageTests(unittest.TestCase):
    def test_parses_full_requested_language_list(self):
        value = (
            "en en-AU en-CA en-US pt de de-CH ru ru-Latn es es-US "
            "nl nl-BE nl-NL it ja fr th km my"
        )
        self.assertEqual(len(parse_language_codes(value)), 20)
        self.assertEqual(parse_language_codes(value)[4:7], ["pt", "de", "de-CH"])
        self.assertEqual(parse_language_codes(value)[-3:], ["th", "km", "my"])

    def test_accepts_commas_normalizes_case_and_deduplicates(self):
        self.assertEqual(
            parse_language_codes("EN-us, en-US; PT  ru-latn"),
            ["en-US", "pt", "ru-Latn"],
        )

    def test_rejects_malformed_codes(self):
        codes = parse_language_codes("en vi! english_name")
        self.assertEqual(invalid_language_codes(codes), ["vi!", "english_name"])

    def test_retries_retryable_error_with_exponential_backoff(self):
        calls = []
        delays = []

        class RetryableError(Exception):
            retryable = True

        def operation():
            calls.append(1)
            if len(calls) < 3:
                raise RetryableError("limited")
            return 200

        async def fake_sleep(delay):
            delays.append(delay)

        status = asyncio.run(
            call_audio_update_with_retry(operation, sleep=fake_sleep)
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(calls), 3)
        self.assertEqual(delays, [2.0, 4.0])

    def test_non_retryable_error_does_not_block_caller_from_continuing(self):
        attempted = []
        failures = []

        async def run_batch():
            for language in ["en", "pt", "de", "ja"]:
                def operation(language=language):
                    attempted.append(language)
                    if language == "pt":
                        raise ValueError("invalid language")
                    return 200

                try:
                    await call_audio_update_with_retry(operation)
                except ValueError:
                    failures.append(language)

        asyncio.run(run_batch())
        self.assertEqual(attempted, ["en", "pt", "de", "ja"])
        self.assertEqual(failures, ["pt"])


if __name__ == "__main__":
    unittest.main()
