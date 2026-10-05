import time
import unittest
from unittest.mock import patch

import requests
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    InvalidSessionIdException,
    TimeoutException,
)

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


class InterceptingElement:
    def __init__(self, interceptions: int):
        self.interceptions = interceptions
        self.click_calls = 0

    def click(self):
        self.click_calls += 1
        if self.click_calls <= self.interceptions:
            raise ElementClickInterceptedException("overlay is still open")


class ImmediateWait:
    """Test double that returns a supplied target without real wall-clock waits."""

    target = None

    def __init__(self, *args, **kwargs):
        pass

    def until(self, condition):
        return self.target


class AccountItemWithoutAttributes:
    def get_attribute(self, _name):
        return None

    def find_elements(self, _by, _selector):
        return []


class AccountItemDriver:
    def __init__(self, candidates):
        self.candidates = candidates

    def execute_script(self, _script, _element):
        return self.candidates


class MenuRow:
    def __init__(self, channel_id, *, active=False):
        self.channel_id = channel_id
        self.active = active

    def get_attribute(self, name):
        if name == "href":
            return f"https://www.youtube.com/channel/{self.channel_id}"
        return None

    def find_elements(self, _by, _value):
        return []


class MenuDriver:
    def __init__(self, rows):
        self.rows = rows

    def find_elements(self, _by, _value):
        return self.rows

    def execute_script(self, script, row):
        if "truthyAttribute" in script:
            return row.active
        return []


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
        menu_ids_available=True,
        channel_names=None,
        initial_state="channel",
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
        self.menu_ids_available = menu_ids_available
        self.initial_state = initial_state
        self.channel_names = {
            channel_id: str((channel_names or {}).get(channel_id) or channel_id)
            for channel_id in self.channel_ids
        }
        self.info_calls = []
        self.menu_calls = 0
        self.switch_calls = 0
        self.filtered_switches = []
        self.initial_select_calls = 0
        self.retry_waits = []
        self.persisted = []

    def _login(self, email, password):
        return None

    def _wait_for_initial_state(self):
        if self.initial_error is not None:
            raise self.initial_error
        return self.initial_state

    def _select_initial_channel_once(self):
        self.initial_select_calls += 1

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
            result = {"id": channel_id, "name": self.channel_names[channel_id]}
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

    def _read_visible_channel_menu_entries_once(self):
        return [
            {
                "channel_id": channel_id if self.menu_ids_available else None,
                "channel_name": self.channel_names[channel_id],
                "normalized_name": self._normalize_channel_name(
                    self.channel_names[channel_id]
                ),
                "row_signature": channel_id,
                "active": index == self.position,
                "element": object(),
            }
            for index, channel_id in enumerate(self.channel_ids)
        ]

    def _list_channel_menu_entries_once(self):
        return self._read_visible_channel_menu_entries_once()

    def _switch_to_channel_match_once(
        self,
        *,
        channel_id,
        channel_name,
        expected_channel_id,
    ):
        resolved_id = expected_channel_id or channel_id
        if not resolved_id:
            normalized_name = self._normalize_channel_name(channel_name)
            resolved_id = next(
                item_id
                for item_id, item_name in self.channel_names.items()
                if self._normalize_channel_name(item_name) == normalized_name
            )
        self.filtered_switches.append(resolved_id)
        self.position = self.channel_ids.index(resolved_id)
        self.driver.current_url = f"https://studio.youtube.com/channel/{resolved_id}"

    def _switch_to_channel_id_once(self, channel_id):
        self._switch_to_channel_match_once(
            channel_id=channel_id,
            channel_name="",
            expected_channel_id=channel_id,
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

    def test_selected_reload_clicks_only_matching_channel_names(self):
        fetcher = FakeChannelFetcher(["A", "B", "C"])
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                include_channel_ids={"B", "missing"},
                include_channel_names={"B": "B", "missing": "Missing"},
            )

        self.assertEqual(fetcher.info_calls, ["B"])
        self.assertEqual(fetcher.filtered_switches, ["B"])
        self.assertEqual(report.available_channel_ids, ["B"])
        self.assertEqual(report.skipped_channel_ids, [])
        self.assertEqual(report.missing_channel_ids, ["missing"])
        self.assertEqual(driver.quit_calls, 1)

    def test_channel_id_is_read_from_account_item_data_without_clicking(self):
        fetcher = ChannelFetcher()
        expected = "UC1234567890123456789012"
        fetcher.driver = AccountItemDriver(
            [f"https://www.youtube.com/channel/{expected}"]
        )

        channel_id = fetcher._channel_id_from_account_item(
            AccountItemWithoutAttributes()
        )

        self.assertEqual(channel_id, expected)

    def test_next_channel_uses_row_position_instead_of_exact_class_string(self):
        fetcher = ChannelFetcher()
        first = MenuRow("A", active=True)
        second = MenuRow("B")
        fetcher.driver = MenuDriver([first, second])

        next_row = fetcher._next_channel_menu_element_once("A")

        self.assertIs(next_row, second)

    def test_unresolved_active_row_is_not_mistaken_for_scan_end(self):
        fetcher = ChannelFetcher()
        fetcher.driver = MenuDriver([MenuRow("A"), MenuRow("B")])

        with self.assertRaises(ChannelScanError) as raised:
            fetcher._next_channel_menu_element_once("missing")

        self.assertEqual(
            raised.exception.category,
            ChannelScanErrorCategory.TRANSIENT_UI_ERROR,
        )

    def test_selected_reload_falls_back_to_unique_channel_name(self):
        fetcher = FakeChannelFetcher(
            ["A", "B", "C"],
            menu_ids_available=False,
            channel_names={"A": "Alpha", "B": "Healing Peace", "C": "Charlie"},
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                include_channel_ids={"B"},
                include_channel_names={"B": "Healing Peace"},
            )

        self.assertEqual(fetcher.info_calls, ["B"])
        self.assertEqual(fetcher.filtered_switches, ["B"])
        self.assertEqual(report.missing_channel_ids, [])

    def test_selected_reload_uses_name_when_menu_id_does_not_match(self):
        fetcher = FakeChannelFetcher(
            ["A", "B"],
            channel_names={"A": "Alpha", "B": "Healing Peace"},
        )
        original_list_entries = fetcher._list_channel_menu_entries_once

        def list_entries_with_stale_id():
            entries = original_list_entries()
            entries[1]["channel_id"] = "stale-menu-id"
            return entries

        fetcher._list_channel_menu_entries_once = list_entries_with_stale_id
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                include_channel_ids={"B"},
                include_channel_names={"B": "Healing Peace"},
            )

        self.assertEqual(fetcher.info_calls, ["B"])
        self.assertEqual(fetcher.filtered_switches, ["B"])
        self.assertEqual(report.missing_channel_ids, [])

    def test_selected_reload_does_not_click_when_channel_name_is_duplicated(self):
        fetcher = FakeChannelFetcher(
            ["A", "B"],
            menu_ids_available=False,
            channel_names={"A": "Same Name", "B": "Same Name"},
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                include_channel_ids={"B"},
                include_channel_names={"B": "Same Name"},
            )

        self.assertEqual(fetcher.info_calls, [])
        self.assertEqual(fetcher.filtered_switches, [])
        self.assertEqual(report.missing_channel_ids, ["B"])

    def test_add_new_does_not_depend_on_ids_from_the_account_menu(self):
        fetcher = FakeChannelFetcher(
            ["A", "B", "C"],
            menu_ids_available=False,
            channel_names={"A": "Alpha", "B": "Brand New", "C": "Charlie"},
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                exclude_channel_ids={"A", "C"},
                exclude_channel_names={"Alpha", "Charlie"},
            )

        self.assertEqual(fetcher.info_calls, ["B"])
        self.assertEqual(fetcher.filtered_switches, ["B"])
        self.assertEqual(fetcher.switch_calls, 0)
        self.assertEqual([item["id"] for item in report.channels], ["B"])

    def test_add_new_treats_an_existing_normalized_name_as_already_added(self):
        fetcher = FakeChannelFetcher(
            ["A", "B", "C"],
            channel_names={
                "A": "Healing Peace",
                "B": "  HEALING   PEACE ",
                "C": "Brand New",
            },
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                exclude_channel_ids={"A"},
                exclude_channel_names={"Healing Peace"},
            )

        self.assertEqual(fetcher.info_calls, ["C"])
        self.assertEqual(fetcher.filtered_switches, ["C"])
        self.assertEqual(fetcher.switch_calls, 0)
        self.assertEqual([item["id"] for item in report.channels], ["C"])
        self.assertEqual(report.skipped_channel_ids, [])

    def test_selected_reload_uses_all_dom_names_when_internal_ids_repeat(self):
        class RepeatedMenuIdFetcher(FakeChannelFetcher):
            def _read_visible_channel_menu_entries_once(self):
                entries = super()._read_visible_channel_menu_entries_once()
                for entry in entries:
                    entry["channel_id"] = "A"
                return entries

        fetcher = RepeatedMenuIdFetcher(
            ["A", "B"],
            channel_names={"A": "Existing", "B": "Brand New"},
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                include_channel_ids={"B"},
                include_channel_names={"B": "Brand New"},
            )

        self.assertEqual(fetcher.info_calls, ["B"])
        self.assertEqual(fetcher.filtered_switches, ["B"])
        self.assertEqual([item["id"] for item in report.channels], ["B"])

    def test_add_new_uses_all_dom_names_when_internal_ids_repeat(self):
        class RepeatedMenuIdFetcher(FakeChannelFetcher):
            def _read_visible_channel_menu_entries_once(self):
                entries = super()._read_visible_channel_menu_entries_once()
                for entry in entries:
                    entry["channel_id"] = "A"
                return entries

        fetcher = RepeatedMenuIdFetcher(
            ["A", "B", "C"],
            channel_names={"A": "Existing A", "B": "Brand New", "C": "Existing C"},
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                exclude_channel_ids={"A", "C"},
                exclude_channel_names={"Existing A", "Existing C"},
            )

        self.assertEqual(fetcher.info_calls, ["B"])
        self.assertEqual(fetcher.filtered_switches, ["B"])
        self.assertEqual([item["id"] for item in report.channels], ["B"])

    def test_selected_reload_retries_when_open_menu_temporarily_has_no_profiles(self):
        class TemporarilyEmptyMenuFetcher(FakeChannelFetcher):
            def _read_visible_channel_menu_entries_once(self):
                if self.menu_calls == 1:
                    return []
                return super()._read_visible_channel_menu_entries_once()

        fetcher = TemporarilyEmptyMenuFetcher(
            ["A", "B"],
            channel_names={"A": "Existing", "B": "Brand New"},
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                include_channel_ids={"B"},
                include_channel_names={"B": "Brand New"},
            )

        self.assertGreaterEqual(fetcher.menu_calls, 2)
        self.assertEqual(fetcher.info_calls, ["B"])
        self.assertEqual([item["id"] for item in report.channels], ["B"])

    def test_add_new_clicks_only_new_ids(self):
        fetcher = FakeChannelFetcher(["A", "B", "C"])
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                exclude_channel_ids={"A", "C"},
                exclude_channel_names={"A", "C"},
            )

        self.assertEqual(fetcher.info_calls, ["B"])
        self.assertEqual(fetcher.filtered_switches, ["B"])
        self.assertEqual(fetcher.switch_calls, 0)
        self.assertEqual(report.skipped_channel_ids, [])
        self.assertEqual(report.missing_channel_ids, [])
        self.assertEqual(driver.quit_calls, 1)

    def test_add_new_with_empty_local_list_bootstraps_from_first_chooser_row(self):
        fetcher = FakeChannelFetcher(
            ["A", "B", "C"],
            initial_state="chooser",
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                exclude_channel_ids=set(),
                exclude_channel_names=set(),
            )

        self.assertEqual(fetcher.initial_select_calls, 0)
        self.assertEqual(fetcher.info_calls, ["A", "B", "C"])
        self.assertEqual(fetcher.filtered_switches, ["B", "C"])
        self.assertEqual(fetcher.switch_calls, 0)
        self.assertEqual([item["id"] for item in report.channels], ["A", "B", "C"])
        self.assertEqual(driver.quit_calls, 1)

    def test_add_new_with_stored_data_still_starts_at_first_chooser_row(self):
        fetcher = FakeChannelFetcher(
            ["NEW", "OLD"],
            initial_state="chooser",
            channel_names={"NEW": "Brand New", "OLD": "Existing"},
        )
        driver = FakeDriver("NEW")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                exclude_channel_ids={"OLD"},
                exclude_channel_names={"Existing"},
            )

        self.assertEqual(fetcher.initial_select_calls, 0)
        self.assertEqual(fetcher.info_calls, ["NEW"])
        self.assertEqual(fetcher.filtered_switches, [])
        self.assertEqual(fetcher.switch_calls, 0)
        self.assertEqual([item["id"] for item in report.channels], ["NEW"])
        self.assertEqual(report.skipped_channel_ids, [])

    def test_empty_selected_reload_does_not_click_or_scan_any_channel(self):
        fetcher = FakeChannelFetcher(["A", "B"])
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                include_channel_ids=set(),
            )

        self.assertTrue(report.completed)
        self.assertEqual(fetcher.info_calls, [])
        self.assertEqual(fetcher.filtered_switches, [])
        self.assertEqual(report.skipped_channel_ids, [])
        self.assertEqual(driver.quit_calls, 1)

    def test_overlay_intercept_retries_click_until_it_succeeds(self):
        fetcher = ChannelFetcher()
        fetcher.driver = object()
        target = InterceptingElement(interceptions=2)
        ImmediateWait.target = target

        with (
            patch("src.channel_scanner.WebDriverWait", ImmediateWait),
            patch.object(
                fetcher,
                "_wait_until_click_target_is_unobstructed",
                return_value=True,
            ) as wait_for_overlay,
        ):
            fetcher._click_with_overlay_retry(
                ("xpath", "avatar"),
                action="nút menu tài khoản",
                deadline=time.monotonic() + 180,
            )

        self.assertEqual(target.click_calls, 3)
        self.assertEqual(wait_for_overlay.call_count, 2)

    def test_persistent_overlay_stops_after_three_clicks_without_outer_retry(self):
        fetcher = ChannelFetcher()
        fetcher.driver = object()
        target = InterceptingElement(interceptions=3)
        ImmediateWait.target = target

        with (
            patch("src.channel_scanner.WebDriverWait", ImmediateWait),
            patch.object(
                fetcher,
                "_wait_until_click_target_is_unobstructed",
                return_value=False,
            ),
        ):
            with self.assertRaises(ChannelScanError) as raised:
                fetcher._click_with_overlay_retry(
                    ("xpath", "avatar"),
                    action="nút menu tài khoản",
                    deadline=time.monotonic() + 180,
                )

        self.assertEqual(target.click_calls, 3)
        self.assertEqual(
            raised.exception.category,
            ChannelScanErrorCategory.TRANSIENT_UI_ERROR,
        )
        self.assertFalse(raised.exception.retryable)

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
