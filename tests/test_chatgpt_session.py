"""Own-profile session reuse and manual-auth pauses; no real ChatGPT requests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from selenium.common.exceptions import WebDriverException

from src.publishing_browser import ChatGPTImageBrowser, ChatGPTSessionNeedsAction
from src.task_runtime import TaskStopped, bind_run_context, create_run_context, register_driver


class ChatGPTSessionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.driver = Mock()
        self.driver.window_handles = ["chatgpt-window"]
        self.driver.title = "ChatGPT"
        self.driver.current_url = "https://chatgpt.com/"
        self.driver.execute_cdp_cmd.return_value = {"success": True}
        self.driver.find_elements.return_value = []
        self.browser = ChatGPTImageBrowser("session=secret", profile_dir=Path(self.folder.name) / "chatgpt-profile")
        self.addCleanup(self.browser.close)
        self.factory = patch("src.publishing_browser._new_driver", return_value=self.driver).start()
        self.addCleanup(patch.stopall)

    def test_cookie_is_loaded_before_first_navigation_and_not_reapplied_on_reuse(self):
        self.browser._browser()
        methods = self.driver.method_calls
        cookie_position = next(index for index, call in enumerate(methods) if call[0] == "execute_cdp_cmd" and call.args[0] == "Network.setCookie")
        navigation_position = next(index for index, call in enumerate(methods) if call[0] == "get")
        self.assertLess(cookie_position, navigation_position)
        self.assertEqual(methods[cookie_position].args[1]["url"], "https://chatgpt.com/")
        self.browser._browser()
        self.factory.assert_called_once_with(profile_dir=Path(self.folder.name) / "chatgpt-profile")
        self.driver.get.assert_called_once_with("https://chatgpt.com/")
        self.assertEqual(sum(call.args[0] == "Network.setCookie" for call in self.driver.execute_cdp_cmd.call_args_list), 1)
        self.driver.add_cookie.assert_not_called()

    def test_profile_can_open_without_pasting_a_cookie(self):
        browser = ChatGPTImageBrowser(profile_dir=Path(self.folder.name) / "other-profile")
        self.addCleanup(browser.close)
        browser._browser()
        self.driver.get.assert_called_once_with("https://chatgpt.com/")
        self.driver.execute_cdp_cmd.assert_not_called()

    def test_cookie_rejection_pauses_without_leaking_value(self):
        self.driver.execute_cdp_cmd.return_value = {"success": False}
        with self.assertRaises(ChatGPTSessionNeedsAction) as error:
            self.browser._browser()
        self.assertNotIn("secret", str(error.exception))
        self.driver.get.assert_not_called()
        self.driver.quit.assert_not_called()

    def test_loaded_cookie_updates_same_browser_instead_of_opening_another(self):
        self.browser._browser()
        self.browser.update_cookies("session=new-secret")
        self.browser._browser()
        self.assertEqual(self.factory.call_count, 1)
        self.assertEqual(self.driver.get.call_count, 2)
        self.assertEqual(self.driver.execute_cdp_cmd.call_args.args[1]["value"], "new-secret")

    def test_clear_import_does_not_clear_browser_login(self):
        self.browser._browser()
        calls = self.driver.execute_cdp_cmd.call_count
        self.browser.update_cookies("")
        self.browser._browser()
        self.assertEqual(self.driver.execute_cdp_cmd.call_count, calls)
        self.driver.delete_all_cookies.assert_not_called()

    def test_cloudflare_pauses_and_keeps_the_same_window_available(self):
        self.driver.title = "Just a moment..."
        with self.assertRaises(ChatGPTSessionNeedsAction) as error:
            self.browser.ensure_ready()
        self.assertEqual(error.exception.reason, "verification")
        self.assertIs(self.browser.driver, self.driver)
        self.driver.quit.assert_not_called()
        self.driver.find_elements.assert_not_called()

    def test_manual_verification_can_make_same_session_ready_on_next_check(self):
        self.driver.title = "Just a moment..."
        with self.assertRaises(ChatGPTSessionNeedsAction):
            self.browser.ensure_ready()
        self.driver.title = "ChatGPT"
        editor, account = Mock(), Mock()
        editor.is_displayed.return_value = account.is_displayed.return_value = True
        def elements(_by, selector):
            if selector == "#prompt-textarea":
                return [editor]
            if "accounts-profile-button" in selector:
                return [account]
            return []
        self.driver.find_elements.side_effect = elements
        self.assertIs(self.browser.ensure_ready(), self.driver)
        self.factory.assert_called_once()
        self.driver.get.assert_called_once()
        self.driver.quit.assert_not_called()

    def test_guest_composer_does_not_count_as_an_authenticated_session(self):
        editor = Mock()
        editor.is_displayed.return_value = True
        def elements(_by, selector):
            if selector == "#prompt-textarea":
                return [editor]
            if "login-button" in selector:
                return [Mock()]
            return []
        self.driver.find_elements.side_effect = elements
        with self.assertRaises(ChatGPTSessionNeedsAction) as error:
            self.browser.ensure_ready()
        self.assertEqual(error.exception.reason, "login")
        self.driver.quit.assert_not_called()

    def test_hidden_background_challenge_frame_does_not_block_ready_account(self):
        editor, account, background = Mock(), Mock(), Mock()
        editor.is_displayed.return_value = account.is_displayed.return_value = True
        background.is_displayed.return_value = False
        def elements(_by, selector):
            if "challenges.cloudflare.com" in selector:
                return [background]
            if selector == "#prompt-textarea":
                return [editor]
            if "accounts-profile-button" in selector:
                return [account]
            return []
        self.driver.find_elements.side_effect = elements
        self.assertIs(self.browser.ensure_ready(), self.driver)

    def test_stopped_submitted_request_keeps_receipt_without_sending_again(self):
        self.browser.driver = self.driver
        self.driver.current_url = "https://chatgpt.com/c/new-request"
        receipt = Mock()
        def stopped(*_args, **_kwargs):
            self.browser._submission_started = True
            raise TaskStopped()
        with patch.object(self.browser, "ensure_ready"), patch.object(self.browser, "_generate", side_effect=stopped), self.assertRaises(TaskStopped):
            self.browser.generate("ref.jpg", "prompt", {}, "output.jpg", on_conversation=receipt)
        receipt.assert_called_once_with("https://chatgpt.com/c/new-request")
        self.driver.quit.assert_not_called()

    def test_stop_before_submission_does_not_attribute_old_conversation_to_new_video(self):
        self.browser.driver = self.driver
        self.driver.current_url = "https://chatgpt.com/c/old-request"
        receipt = Mock()
        with patch.object(self.browser, "ensure_ready", side_effect=TaskStopped()), self.assertRaises(TaskStopped):
            self.browser.generate("ref.jpg", "prompt", {}, "output.jpg", on_conversation=receipt)
        receipt.assert_not_called()

    def test_batch_stop_cannot_close_app_owned_chatgpt_driver(self):
        run = create_run_context("chatgpt-session-ownership-test")
        self.addCleanup(run.cleanup)
        with bind_run_context(run):
            self.factory.side_effect = lambda **kwargs: register_driver(self.driver)
            self.browser._browser()
            run.request_stop()
        self.driver.quit.assert_not_called()
        self.browser.close()
        self.driver.quit.assert_called_once()

    def test_closing_window_allows_profile_reopen_without_old_cookie_reinjection(self):
        self.browser._browser()
        self.browser.close()
        self.browser._browser()
        self.assertEqual(self.factory.call_count, 2)
        self.assertEqual(sum(call.args[0] == "Network.setCookie" for call in self.driver.execute_cdp_cmd.call_args_list), 1)

    def test_closed_browser_can_be_recovered_on_next_preparation(self):
        self.browser._browser()
        replacement = Mock(window_handles=["new-window"])
        self.factory.return_value = replacement
        type(self.driver).window_handles = property(lambda _self: (_ for _ in ()).throw(WebDriverException("closed")))
        self.assertIs(self.browser._browser(), replacement)
        self.assertEqual(self.factory.call_count, 2)
        replacement.get.assert_called_once_with("https://chatgpt.com/")


if __name__ == "__main__":
    unittest.main()
