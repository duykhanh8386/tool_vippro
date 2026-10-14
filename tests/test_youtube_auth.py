import hashlib
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.channel_validation import validate_reloaded_channel_session
from src.module.base import IModule, YouTubeRequestError, validate_channel_session_token
from src.task_runtime import TaskStopped
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


class StudioSessionRefreshTests(unittest.TestCase):
    def setUp(self):
        self.channel_id = "session-refresh-test"
        self.addCleanup(IModule.invalidate_session_token_cache, self.channel_id)
        self.module = IModule()
        self.old = self.channel("old")
        self.fresh = self.channel("fresh")

    def channel(self, version):
        return SimpleNamespace(
            id=self.channel_id, role="CREATOR_CHANNEL_ROLE_TYPE_MANAGER",
            delegated_session_id=f"delegate-{version}", challenge=f"challenge-{version}",
            botguardResponse=f"guard-{version}",
            cookies=[{"name": "SAPISID", "value": f"cookie-{version}"}],
            cookie_string=lambda: f"SAPISID=cookie-{version}",
            studio_context={
                "client": {"clientName": 62, "clientVersion": f"browser-{version}", "userAgent": "browser-agent"},
                "user": {"onBehalfOfUser": f"delegate-{version}", "serializedDelegationContext": "browser-delegation",
                         "delegationContext": {"externalChannelId": self.channel_id, "roleType": {"channelRoleType": "CREATOR_CHANNEL_ROLE_TYPE_MANAGER"}}},
                "request": {"eats": "browser-eats", "sessionInfo": {"token": "stale"}, "reauthRequestInfo": {"encodedReauthProofToken": "stale"}},
            },
        )

    def response(self, status, body):
        return SimpleNamespace(status_code=status, json=lambda: body)

    def test_reauth_http400_refreshes_all_session_data_and_retries_once(self):
        responses = [
            self.response(200, {"ctx": "old-attestation"}),
            self.response(400, {"error": {"message": "invalid argument"}}),
            self.response(200, {"ctx": "fresh-attestation"}),
            self.response(200, {"encodedReauthProofToken": "fresh-proof", "sessionRiskCtx": "fresh-risk"}),
            self.response(200, {"sessionToken": "new-session-token"}),
        ]
        with (
            patch("src.module.base.post_with_stop", side_effect=responses) as post,
            patch("src.channel_refresh.refresh_challenge_and_botguard") as refresh,
            patch("src.module.base.get_channels_info", return_value=self.fresh),
        ):
            self.assertEqual(self.module._get_session_token(self.old), "new-session-token")
        refresh.assert_called_once_with(self.channel_id)
        self.assertEqual(post.call_count, 5)
        fresh_attestation = post.call_args_list[2].kwargs
        self.assertEqual(fresh_attestation["json"]["challenge"], "challenge-fresh")
        self.assertEqual(fresh_attestation["headers"]["cookie"], "SAPISID=cookie-fresh")
        self.assertEqual(fresh_attestation["headers"]["user-agent"], "browser-agent")
        self.assertEqual(fresh_attestation["json"]["context"]["client"]["clientVersion"], "browser-fresh")
        self.assertEqual(post.call_args_list[3].kwargs["json"]["ivctx"], "fresh-attestation")
        final_context = post.call_args_list[4].kwargs["json"]["context"]
        expected_user = dict(self.fresh.studio_context["user"])
        expected_user.pop("onBehalfOfUser")
        self.assertEqual(final_context["user"], expected_user)
        self.assertEqual(final_context["request"]["reauthRequestInfo"], {"encodedReauthProofToken": "fresh-proof"})
        self.assertNotIn("sessionInfo", final_context["request"])
        self.assertEqual(self.fresh.studio_context["request"]["sessionInfo"], {"token": "stale"})

    def test_persistent_http400_does_not_keep_reopening_the_browser(self):
        responses = [
            self.response(200, {"ctx": "first"}), self.response(400, {}),
            self.response(200, {"ctx": "second"}), self.response(400, {}),
        ]
        with (
            patch("src.module.base.post_with_stop", side_effect=responses) as post,
            patch("src.channel_refresh.refresh_challenge_and_botguard") as refresh,
            patch("src.module.base.get_channels_info", return_value=self.fresh),
        ):
            with self.assertRaises(YouTubeRequestError) as raised:
                self.module._get_session_token(self.old)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(post.call_count, 4)
        refresh.assert_called_once()

    def test_permission_rate_limit_and_server_errors_are_not_retried_as_bad_context(self):
        for status in (401, 403, 429, 500):
            with self.subTest(status=status), patch(
                "src.module.base.post_with_stop",
                side_effect=[self.response(200, {"ctx": "attestation"}), self.response(status, {})],
            ) as post, patch("src.channel_refresh.refresh_challenge_and_botguard") as refresh:
                with self.assertRaises(YouTubeRequestError) as raised:
                    self.module._get_session_token(self.old)
                self.assertEqual(raised.exception.status_code, status)
                self.assertEqual(post.call_count, 2)
                refresh.assert_not_called()

    def test_missing_reauth_fields_are_refreshed_before_session_token_request(self):
        with (
            patch("src.module.base.post_with_stop", side_effect=[
                self.response(200, {"ctx": "first"}), self.response(200, {}),
                self.response(200, {"ctx": "second"}), self.response(200, {}),
            ]) as post,
            patch("src.channel_refresh.refresh_challenge_and_botguard") as refresh,
            patch("src.module.base.get_channels_info", return_value=self.fresh),
        ):
            with self.assertRaisesRegex(YouTubeRequestError, "encodedReauthProofToken or sessionRiskCtx"):
                self.module._get_session_token(self.old)
        refresh.assert_called_once()
        self.assertEqual(post.call_count, 4)

    def test_stop_during_reauth_does_not_refresh_or_continue(self):
        with patch("src.module.base.post_with_stop", side_effect=TaskStopped()), patch(
            "src.channel_refresh.refresh_challenge_and_botguard"
        ) as refresh:
            with self.assertRaises(TaskStopped):
                self.module._get_session_token(self.old)
        refresh.assert_not_called()

    def test_changed_delegation_cannot_reuse_another_sessions_cached_token(self):
        self.fresh.challenge = self.old.challenge
        self.fresh.botguardResponse = self.old.botguardResponse
        self.fresh.cookies = self.old.cookies

        def post(url, **kwargs):
            if "/att/esr" in url:
                return self.response(200, {"ctx": "attestation"})
            if "get_web_reauth_url" in url:
                return self.response(200, {"encodedReauthProofToken": "proof", "sessionRiskCtx": "risk"})
            return self.response(200, {"sessionToken": kwargs["json"]["context"]["client"]["clientVersion"]})

        with patch("src.module.base.post_with_stop", side_effect=post) as request:
            self.assertEqual(self.module._get_session_token(self.old), "browser-old")
            self.assertEqual(self.module._get_session_token(self.fresh), "browser-fresh")
            self.assertEqual(self.module._get_session_token(self.fresh), "browser-fresh")
        self.assertEqual(request.call_count, 6)


class BrowserChannelRefreshTests(unittest.TestCase):
    def test_refresh_saves_cookies_and_delegation_from_current_browser(self):
        import json
        from src.channel_refresh import refresh_challenge_and_botguard

        driver = Mock()
        driver.current_url = "https://studio.youtube.com/channel/channel/analytics"
        driver.get_cookies.return_value = [{"name": "SAPISID", "value": "new-cookie"}]
        context = {
            "client": {"clientVersion": "fresh"},
            "user": {"onBehalfOfUser": "fresh-delegate", "delegationContext": {
                "externalChannelId": "channel", "roleType": {"channelRoleType": "MANAGER"}
            }},
        }
        with (
            patch("src.channel_refresh.create_driver", return_value=driver),
            patch("src.channel_refresh.inject_cookies_via_cdp"),
            patch("src.channel_refresh.unregister_driver") as unregister,
            patch("src.channel_refresh.channel_store") as store,
            patch("src.channel_refresh.get_request_payload_from_performance_log", return_value=json.dumps({
                "challenge": "fresh", "botguardResponse": "fresh-guard", "context": context,
            })),
        ):
            store.get_channel.return_value = {"id": "channel", "cookies": SAPISID_COOKIES, "role": "OWNER"}
            refresh_challenge_and_botguard("channel")
        saved = store.upsert_channel.call_args.args[0]
        self.assertEqual(saved["cookies"][0]["value"], "new-cookie")
        self.assertEqual(saved["delegated_session_id"], "fresh-delegate")
        self.assertEqual(saved["role"], "MANAGER")
        self.assertEqual(saved["studio_context"], context)
        driver.get_log.assert_called_once_with("performance")
        driver.quit.assert_called_once()
        unregister.assert_called_once_with(driver)

    def test_wrong_channel_attestation_is_rejected_without_overwriting_storage(self):
        import json
        from src.channel_refresh import refresh_challenge_and_botguard

        driver = Mock(current_url="https://studio.youtube.com/channel/channel")
        with (
            patch("src.channel_refresh.create_driver", return_value=driver),
            patch("src.channel_refresh.inject_cookies_via_cdp"),
            patch("src.channel_refresh.unregister_driver"),
            patch("src.channel_refresh.channel_store") as store,
            patch("src.channel_refresh.get_request_payload_from_performance_log", return_value=json.dumps({
                "challenge": "fresh", "botguardResponse": "fresh", "context": {
                    "user": {"delegationContext": {"externalChannelId": "different-channel"}}
                },
            })),
        ):
            store.get_channel.return_value = {"cookies": SAPISID_COOKIES}
            with self.assertRaisesRegex(RuntimeError, "kênh khác"):
                refresh_challenge_and_botguard("channel")
        store.upsert_channel.assert_not_called()
        driver.quit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
