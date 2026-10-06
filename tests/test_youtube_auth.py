import hashlib
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.channel_validation import validate_reloaded_channel_session
from src.module.base import IModule, validate_channel_session_token
from src.youtube_auth import (
    MissingSapisidCookieError,
    generate_sapisidhash,
    studio_authorization_header,
)


SAPISID_COOKIES = [{"name": "SAPISID", "value": "cookie-secret"}]


class YouTubeAuthorizationTests(unittest.TestCase):
    def test_hash_is_generated_from_cookie_and_current_timestamp(self):
        expected = hashlib.sha1(
            b"123 cookie-secret https://studio.youtube.com"
        ).hexdigest()

        self.assertEqual(
            generate_sapisidhash(SAPISID_COOKIES, timestamp=123),
            f"123_{expected}",
        )

    def test_authorization_header_is_fresh_instead_of_using_stored_hash(self):
        with patch("src.youtube_auth.time.time", side_effect=[100, 101]):
            first = studio_authorization_header(SAPISID_COOKIES)
            second = studio_authorization_header(SAPISID_COOKIES)

        self.assertTrue(first.startswith("SAPISIDHASH 100_"))
        self.assertTrue(second.startswith("SAPISIDHASH 101_"))
        self.assertNotEqual(first, second)

    def test_missing_sapisid_cookie_requires_a_real_reload(self):
        with self.assertRaises(MissingSapisidCookieError):
            studio_authorization_header([{"name": "SID", "value": "value"}])


class ChannelSessionValidationTests(unittest.TestCase):
    def _channel(self):
        return SimpleNamespace(
            id="channel-a",
            name="Channel A",
            role="CREATOR_CHANNEL_ROLE_TYPE_OWNER",
            delegated_session_id="delegated",
            challenge="challenge",
            botguardResponse="botguard",
            sapisidhash="old-stored-hash",
            cookies=SAPISID_COOKIES,
            cookie_string=lambda: "SAPISID=cookie-secret",
        )

    def test_real_validation_discards_a_cached_session_token(self):
        channel = self._channel()
        cache_key = IModule._session_token_cache_key(channel)
        with IModule._SESSION_TOKEN_CACHE_LOCK:
            IModule._SESSION_TOKEN_CACHE[cache_key] = (
                "cached-token",
                time.monotonic(),
            )
        try:
            with (
                patch("src.module.base.get_channels_info", return_value=channel),
                patch.object(
                    IModule,
                    "_fetch_session_token_uncached",
                    return_value="new-token",
                ) as fetch,
            ):
                self.assertTrue(validate_channel_session_token("channel-a"))
            fetch.assert_called_once()
        finally:
            with IModule._SESSION_TOKEN_CACHE_LOCK:
                IModule._SESSION_TOKEN_CACHE.pop(cache_key, None)

    def test_failed_validation_keeps_a_red_channel_specific_alert(self):
        with (
            patch(
                "src.channel_validation.validate_channel_session_token",
                side_effect=RuntimeError("token=secret rejected"),
            ),
            patch(
                "src.channel_validation.mark_channel_refresh_required",
                return_value=True,
            ) as mark,
        ):
            result = validate_reloaded_channel_session(
                "channel-a", "Channel A"
            )

        self.assertFalse(result.successful)
        mark.assert_called_once()
        self.assertEqual(mark.call_args.args[:2][0], "channel-a")
        self.assertEqual(mark.call_args.kwargs["channel_name"], "Channel A")
        self.assertTrue(mark.call_args.kwargs["validation_failed"])

    def test_successful_validation_does_not_create_an_alert(self):
        with (
            patch(
                "src.channel_validation.validate_channel_session_token",
                return_value=True,
            ),
            patch(
                "src.channel_validation.mark_channel_refresh_required"
            ) as mark,
        ):
            result = validate_reloaded_channel_session(
                "channel-a", "Channel A"
            )

        self.assertTrue(result.successful)
        mark.assert_not_called()


if __name__ == "__main__":
    unittest.main()
