import unittest
from unittest.mock import patch

import requests
from selenium.common.exceptions import InvalidSessionIdException, TimeoutException

from src.channel_scanner import (
    CHANNEL_SCAN_MAX_ATTEMPTS,
    ChannelFetcher,
    ChannelScanError,
    ChannelScanErrorCategory,
)
from src.task_runtime import TaskStopped, bind_run_context, create_run_context, current_run_context


class FakeDriver:
    def __init__(self, channel_id: str):
        self.current_url = f"https://studio.youtube.com/channel/{channel_id}"
        self.quit_calls = 0

    def quit(self):
        self.quit_calls += 1


class FakeChannelFetcher(ChannelFetcher):
    def __init__(
        self,
        channel_ids,
        *,
        info_outcomes=None,
        menu_failures=0,
        initial_error=None,
        fatal_switch_at=None,
        fatal_next_check_at=None,
        stop_during_channel=None,
    ):
        super().__init__()
        self.channel_ids = list(channel_ids)
        self.position = 0
        self.info_outcomes = {
            key: list(values) for key, values in (info_outcomes or {}).items()
        }
        self.menu_failures = menu_failures
        self.initial_error = initial_error
        self.fatal_switch_at = fatal_switch_at
        self.fatal_next_check_at = fatal_next_check_at
        self.stop_during_channel = stop_during_channel
        self.info_calls = []
        self.menu_calls = 0
        self.switch_calls = 0
        self.retry_waits = []
        self.persisted = []

    def _login(self, email, password):
        return None

    def _wait_for_initial_state(self):
        if self.initial_error is not None:
            raise self.initial_error
        return "channel"

    def _get_channel_info(self):
        channel_id = self.channel_ids[self.position]
        self.info_calls.append(channel_id)
        if self.stop_during_channel == channel_id:
            current_run_context().request_stop()
            self._checkpoint()
        outcomes = self.info_outcomes.get(channel_id)
        if outcomes:
            outcome = outcomes.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            result = outcome
        else:
            result = {"id": channel_id, "name": channel_id}
        self.persisted.append(channel_id)
        return result

    def _open_channel_switcher_once(self):
        self.menu_calls += 1
        if self.menu_calls <= self.menu_failures:
            raise TimeoutException("account menu did not become ready")

    def _has_next_channel(self):
        if self.fatal_next_check_at == self.position:
            raise InvalidSessionIdException("invalid session id")
        return self.position + 1 < len(self.channel_ids)

    def _switch_to_next_channel_once(self, previous_channel_id):
        self.switch_calls += 1
        if self.fatal_switch_at == self.position:
            raise InvalidSessionIdException("invalid session id")
        self.position += 1
        self.driver.current_url = (
            f"https://studio.youtube.com/channel/{self.channel_ids[self.position]}"
        )

    def _wait_interruptibly(self, seconds):
        self._checkpoint()
        self.retry_waits.append(seconds)


class ChannelScannerHardeningTests(unittest.TestCase):
    def run_fetcher(self, fetcher):
        driver = FakeDriver(fetcher.channel_ids[0])
        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run("user@example.com", "not-logged")
        return report, driver

    def test_multiple_channels_happy_path(self):
        fetcher = FakeChannelFetcher(["A", "B", "C"])

        report, driver = self.run_fetcher(fetcher)

        self.assertTrue(report.completed)
        self.assertEqual([item["id"] for item in report.channels], ["A", "B", "C"])
        self.assertEqual(report.failures, [])
        self.assertEqual(driver.quit_calls, 1)

    def test_one_channel_error_is_skipped_and_scan_continues(self):
        channel_error = ChannelScanError(
            ChannelScanErrorCategory.CHANNEL_ERROR,
            step="channel_info",
            detail="channel metadata unavailable",
        )
        fetcher = FakeChannelFetcher(
            ["A", "B", "C"],
            info_outcomes={"B": [channel_error]},
        )

        report, _ = self.run_fetcher(fetcher)

        self.assertEqual([item["id"] for item in report.channels], ["A", "C"])
        self.assertEqual(len(report.failures), 1)
        self.assertEqual(report.failures[0].channel_id, "B")
        self.assertEqual(fetcher.persisted, ["A", "C"])

    def test_transient_ui_timeout_retries_then_recovers(self):
        fetcher = FakeChannelFetcher(["A"], menu_failures=1)

        report, _ = self.run_fetcher(fetcher)

        self.assertTrue(report.completed)
        self.assertEqual(fetcher.menu_calls, 2)
        self.assertEqual(len(fetcher.retry_waits), 1)

    def test_account_menu_timeout_is_not_scan_end(self):
        fetcher = FakeChannelFetcher(
            ["A", "B"],
            menu_failures=CHANNEL_SCAN_MAX_ATTEMPTS,
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            with self.assertRaises(ChannelScanError) as raised:
                fetcher.run("user@example.com", "not-logged")

        self.assertEqual(
            raised.exception.category,
            ChannelScanErrorCategory.TRANSIENT_UI_ERROR,
        )
        self.assertFalse(fetcher.last_report.completed)
        self.assertEqual(fetcher.menu_calls, CHANNEL_SCAN_MAX_ATTEMPTS)
        self.assertEqual(driver.quit_calls, 1)

    def test_scan_end_requires_successful_menu_and_explicit_no_next_channel(self):
        fetcher = FakeChannelFetcher(["A"])

        report, _ = self.run_fetcher(fetcher)

        self.assertTrue(report.completed)
        self.assertEqual(report.end_category, ChannelScanErrorCategory.SCAN_END)
        self.assertEqual(fetcher.menu_calls, 1)
        self.assertEqual(fetcher.switch_calls, 0)

    def test_authentication_failure_stops_without_retry(self):
        auth_error = ChannelScanError(
            ChannelScanErrorCategory.AUTH_ERROR,
            step="authentication",
            detail="browser session redirected to login",
        )
        fetcher = FakeChannelFetcher(["A", "B"], initial_error=auth_error)
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            with self.assertRaises(ChannelScanError) as raised:
                fetcher.run("user@example.com", "not-logged")

        self.assertEqual(raised.exception.category, ChannelScanErrorCategory.AUTH_ERROR)
        self.assertEqual(fetcher.info_calls, [])
        self.assertEqual(driver.quit_calls, 1)

    def test_unknown_auth_timeout_is_not_mislabeled_as_channel_error(self):
        unknown_auth = ChannelScanError(
            ChannelScanErrorCategory.UNKNOWN_AUTH_STATE,
            step="authentication",
            detail="no recognized authentication state",
        )
        fetcher = FakeChannelFetcher(["A"], initial_error=unknown_auth)
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            with self.assertRaises(ChannelScanError) as raised:
                fetcher.run("user@example.com", "not-logged")

        self.assertEqual(
            raised.exception.category,
            ChannelScanErrorCategory.UNKNOWN_AUTH_STATE,
        )
        self.assertEqual(driver.quit_calls, 1)

    def test_fatal_webdriver_error_during_authentication_is_classified(self):
        fetcher = FakeChannelFetcher(
            ["A"],
            initial_error=InvalidSessionIdException("invalid session id"),
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            with self.assertRaises(ChannelScanError) as raised:
                fetcher.run("user@example.com", "not-logged")

        self.assertEqual(raised.exception.category, ChannelScanErrorCategory.FATAL_ERROR)
        self.assertEqual(raised.exception.step, "authentication")
        self.assertEqual(driver.quit_calls, 1)

    def test_network_timeout_retries_then_succeeds(self):
        fetcher = FakeChannelFetcher(
            ["A"],
            info_outcomes={
                "A": [requests.Timeout("read timed out"), {"id": "A", "name": "A"}]
            },
        )

        report, _ = self.run_fetcher(fetcher)

        self.assertEqual([item["id"] for item in report.channels], ["A"])
        self.assertEqual(fetcher.info_calls, ["A", "A"])
        self.assertEqual(len(fetcher.retry_waits), 1)

    def test_exhausted_channel_network_retry_skips_only_that_channel(self):
        fetcher = FakeChannelFetcher(
            ["A", "B", "C"],
            info_outcomes={
                "B": [
                    requests.Timeout("read timed out")
                    for _ in range(CHANNEL_SCAN_MAX_ATTEMPTS)
                ]
            },
        )

        report, _ = self.run_fetcher(fetcher)

        self.assertEqual([item["id"] for item in report.channels], ["A", "C"])
        self.assertEqual(fetcher.info_calls.count("B"), CHANNEL_SCAN_MAX_ATTEMPTS)
        self.assertEqual(report.failures[0].category, ChannelScanErrorCategory.NETWORK_ERROR)

    def test_fatal_webdriver_error_cleans_up_and_preserves_partial_result(self):
        fetcher = FakeChannelFetcher(["A", "B"], fatal_switch_at=0)
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            with self.assertRaises(ChannelScanError) as raised:
                fetcher.run("user@example.com", "not-logged")

        self.assertEqual(raised.exception.category, ChannelScanErrorCategory.FATAL_ERROR)
        self.assertEqual(fetcher.persisted, ["A"])
        self.assertEqual([item["id"] for item in fetcher.last_report.channels], ["A"])
        self.assertEqual(driver.quit_calls, 1)

    def test_fatal_next_channel_check_is_classified_and_preserves_partial_result(self):
        fetcher = FakeChannelFetcher(["A", "B"], fatal_next_check_at=0)
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            with self.assertRaises(ChannelScanError) as raised:
                fetcher.run("user@example.com", "not-logged")

        self.assertEqual(raised.exception.category, ChannelScanErrorCategory.FATAL_ERROR)
        self.assertEqual(raised.exception.step, "detect_next_channel")
        self.assertEqual(fetcher.persisted, ["A"])
        self.assertEqual([item["id"] for item in fetcher.last_report.channels], ["A"])
        self.assertEqual(driver.quit_calls, 1)

    def test_user_stop_does_not_start_next_channel_and_cleans_up(self):
        fetcher = FakeChannelFetcher(
            ["A", "B", "C"],
            stop_during_channel="A",
        )
        driver = FakeDriver("A")
        run_context = create_run_context("channel_scanner_test")
        try:
            with bind_run_context(run_context), patch(
                "src.channel_scanner.create_driver", return_value=driver
            ):
                with self.assertRaises(TaskStopped):
                    fetcher.run("user@example.com", "not-logged")
        finally:
            run_context.cleanup()

        self.assertEqual(fetcher.info_calls, ["A"])
        self.assertEqual(fetcher.switch_calls, 0)
        self.assertEqual(driver.quit_calls, 1)

    def test_fifty_channels_complete_without_false_early_end(self):
        channel_ids = [f"channel-{index:02d}" for index in range(50)]
        fetcher = FakeChannelFetcher(channel_ids)

        report, _ = self.run_fetcher(fetcher)

        self.assertTrue(report.completed)
        self.assertEqual(len(report.channels), 50)
        self.assertEqual(len(fetcher.persisted), 50)
        self.assertEqual(fetcher.switch_calls, 49)
        self.assertEqual(report.failures, [])


if __name__ == "__main__":
    unittest.main()
