import time
import unittest
from unittest.mock import Mock, patch

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


class StatusMenuRow(MenuRow):
    def __init__(self, channel_id, driver, *, title=None, status="", active=False):
        super().__init__(channel_id, active=active)
        self.driver = driver
        self.title = title or channel_id
        self.text = "\n".join(part for part in (self.title, status) if part)

    def click(self):
        for row in self.driver.rows:
            row.active = False
        self.active = True
        self.driver.current_url = f"https://studio.youtube.com/channel/{self.channel_id}"


class StatusMenuDriver(MenuDriver):
    def __init__(self, rows, current_url):
        super().__init__(rows)
        self.current_url = current_url


class TitledMenuRow(StatusMenuRow):
    def __init__(self, channel_id, driver, *, title, account_name, rendered_title=None):
        super().__init__(channel_id, driver, title=title)
        self.account_name = account_name
        self.rendered_title = title if rendered_title is None else rendered_title

    def find_elements(self, _by, selector):
        if "channel-title" in selector:
            return [self.Label(self.rendered_title, self.title)]
        if "account-name" in selector:
            return [self.Label(self.account_name, self.account_name)]
        return []

    class Label:
        def __init__(self, rendered_text, dom_text):
            self.text = rendered_text
            self.dom_text = dom_text

        def get_attribute(self, name):
            return self.dom_text if name == "textContent" else None


class PredicateWait:
    def __init__(self, driver, *args, **kwargs):
        self.driver = driver

    def until(self, predicate):
        result = predicate(self.driver)
        if not result:
            raise TimeoutException("condition was not satisfied")
        return result


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
        deleted_channel_ids=(),
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
        self.deleted_channel_ids = set(deleted_channel_ids)
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
                "menu_index": index + 1,
                "deleted": channel_id in self.deleted_channel_ids,
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

    def _switch_to_chooser_row_once(self, target):
        position = next(
            index for index, entry in enumerate(self._read_visible_channel_menu_entries_once())
            if entry["row_signature"] == target["row_signature"]
        )
        resolved_id = self.channel_ids[position]
        if self._current_channel_id() == resolved_id:
            return
        self.filtered_switches.append(resolved_id)
        self.position = position
        self.driver.current_url = f"https://studio.youtube.com/channel/{resolved_id}"

    def _wait_interruptibly(self, seconds):
        self._checkpoint()
        self.retry_waits.append(seconds)


class ChannelScannerHardeningTests(unittest.TestCase):
    def scan_dom_menu(self, driver, *, excluded_ids=(), excluded_names=(), on_open=None):
        fetcher = ChannelFetcher()
        fetcher.driver = driver
        read_ids = []

        def read_channel():
            channel_id = fetcher._current_channel_id()
            read_ids.append(channel_id)
            row = next(row for row in driver.rows if row.channel_id == channel_id)
            return {"id": channel_id, "name": row.title}

        with (
            patch.object(fetcher, "_open_channel_switcher_once", side_effect=on_open),
            patch.object(fetcher, "_wait_interruptibly"),
            patch.object(fetcher, "_get_channel_info", side_effect=read_channel),
            patch("src.channel_scanner.WebDriverWait", PredicateWait),
        ):
            report = fetcher._scan_filtered_channels(
                include_channel_ids=None, exclude_channel_ids=set(excluded_ids),
                include_channel_names={}, exclude_channel_names=set(excluded_names),
            )
        return report, read_ids

    def test_add_new_resolves_rows_11_and_19_by_real_ids_in_a_23_row_menu(self):
        ids = [f"UC{i:022d}" for i in range(23)]
        driver = StatusMenuDriver([], f"https://studio.youtube.com/channel/{ids[0]}")
        new_rows = {10, 18}
        driver.rows = [
            TitledMenuRow(channel_id, driver,
                          title="🎧 เพลงเพราะไทยแลนด์" if i in new_rows else f"Existing {i}",
                          account_name="Account")
            for i, channel_id in enumerate(ids)
        ]
        driver.rows[0].active = True

        report, read_ids = self.scan_dom_menu(
            driver, excluded_ids={channel_id for i, channel_id in enumerate(ids) if i not in new_rows},
            excluded_names={f"existing {i}" for i in range(23) if i not in new_rows},
        )

        self.assertEqual(read_ids, [ids[10], ids[18]])
        self.assertEqual([channel["id"] for channel in report.channels], [ids[10], ids[18]])
        self.assertEqual(report.unidentified_channel_count, 0)
        self.assertEqual(report.failures, [])

    def test_same_name_rows_match_full_text_even_when_the_menu_reorders(self):
        driver = StatusMenuDriver([], "https://studio.youtube.com/channel/OTHER")
        for channel_id in ("A", "B"):
            row = TitledMenuRow(channel_id, driver, title="🎧 เพลงเพราะไทยแลนด์", account_name="Account")
            row.text += f"\n@handle-{channel_id}"
            driver.rows.append(row)
        reordered = {"done": False}

        def reopen_menu():
            if driver.current_url.endswith("/A") and not reordered["done"]:
                driver.rows.reverse()
                reordered["done"] = True

        report, read_ids = self.scan_dom_menu(driver, on_open=reopen_menu)

        self.assertTrue(reordered["done"])
        self.assertEqual(read_ids, ["A", "B"])
        self.assertEqual(report.failures, [])

    def test_duplicate_menu_rows_for_one_verified_id_are_only_loaded_once(self):
        driver = StatusMenuDriver([], "https://studio.youtube.com/channel/A")
        driver.rows = [
            TitledMenuRow("A", driver, title="🎧 เพลงเพราะไทยแลนด์", account_name="Account")
            for _ in range(2)
        ]
        for row in driver.rows:
            row.active = True

        report, read_ids = self.scan_dom_menu(driver)

        self.assertEqual(read_ids, ["A"])
        self.assertEqual([channel["id"] for channel in report.channels], ["A"])
        self.assertEqual(report.failures, [])

    def test_identical_title_rows_still_skip_existing_ids_before_saving(self):
        driver = StatusMenuDriver([], "https://studio.youtube.com/channel/A")
        driver.rows = [TitledMenuRow(channel_id, driver, title="Same title", account_name="Account")
                       for channel_id in ("A", "B")]
        driver.rows[0].active = True

        report, read_ids = self.scan_dom_menu(driver, excluded_ids={"A"}, excluded_names={"same title"})

        self.assertEqual(read_ids, ["B"])
        self.assertEqual(report.skipped_channel_ids, ["A"])
        self.assertEqual([channel["id"] for channel in report.channels], ["B"])

    def test_changed_ambiguous_row_count_does_not_click_a_stale_position(self):
        fetcher = ChannelFetcher()
        fetcher.driver = FakeDriver("OTHER")
        elements = [Mock() for _ in range(3)]
        entries = [{"normalized_name": "same", "row_signature": "same-row", "element": element}
                   for element in elements]
        target = {"normalized_name": "same", "row_signature": "same-row", "row_match_count": 2,
                  "row_occurrence": 1}
        with patch.object(fetcher, "_wait_for_channel_menu_entries_ready", return_value=entries):
            with self.assertRaises(ChannelScanError) as caught:
                fetcher._switch_to_chooser_row_once(target)

        self.assertEqual(caught.exception.category, ChannelScanErrorCategory.TRANSIENT_UI_ERROR)
        for element in elements:
            element.click.assert_not_called()

    def test_previously_active_snapshot_row_is_reopened_after_switching_away(self):
        driver = StatusMenuDriver([], "https://studio.youtube.com/channel/B")
        driver.rows = [TitledMenuRow(channel_id, driver, title=channel_id, account_name="Account")
                       for channel_id in ("A", "B")]
        driver.rows[1].active = True

        report, read_ids = self.scan_dom_menu(driver)

        self.assertEqual(read_ids, ["A", "B"])
        self.assertEqual(report.failures, [])

    def test_channel_title_is_used_instead_of_shared_account_label(self):
        driver = StatusMenuDriver([], "")
        fetcher = ChannelFetcher()
        first = TitledMenuRow("A", driver, title="🎧 เพลงเพราะ A", account_name="Shared account")
        second = TitledMenuRow("B", driver, title="🎧 เพลงเพราะ B", account_name="Shared account")

        self.assertEqual(fetcher._channel_name_from_account_item(first), "🎧 เพลงเพราะ A")
        self.assertEqual(fetcher._channel_name_from_account_item(second), "🎧 เพลงเพราะ B")

    def test_full_dom_title_is_preserved_when_selenium_only_sees_an_icon(self):
        driver = StatusMenuDriver([], "")
        row = TitledMenuRow("A", driver, title="🎧 เพลงเพราะ A", account_name="Shared account",
                           rendered_title="🎧")
        self.assertEqual(ChannelFetcher()._channel_name_from_account_item(row), "🎧 เพลงเพราะ A")

    def test_empty_title_waits_for_loading_instead_of_using_account_label(self):
        driver = StatusMenuDriver([], "")
        row = TitledMenuRow("A", driver, title="", account_name="Shared account", rendered_title="")
        row.title = ""
        self.assertEqual(ChannelFetcher()._channel_name_from_account_item(row), "")

    def test_add_new_reads_23_rows_and_loads_two_distinct_titles_with_shared_account_label(self):
        ids = [f"UC{i:022d}" for i in range(23)]
        driver = StatusMenuDriver([], f"https://studio.youtube.com/channel/{ids[0]}")
        rows = [StatusMenuRow(channel_id, driver, title=f"Existing {i}", active=(i == 0))
                for i, channel_id in enumerate(ids[:21])]
        rows.extend([
            TitledMenuRow(ids[21], driver, title="🎧 เพลงเพราะ A", account_name="Shared account",
                          rendered_title="🎧"),
            TitledMenuRow(ids[22], driver, title="🎧 เพลงเพราะ B", account_name="Shared account",
                          rendered_title="🎧"),
        ])
        driver.rows = rows
        fetcher = ChannelFetcher()
        fetcher.driver = driver

        def read_channel():
            channel_id = fetcher._current_channel_id()
            row = next(row for row in rows if row.channel_id == channel_id)
            return {"id": channel_id, "name": row.title}

        with (
            patch.object(fetcher, "_open_channel_switcher_once"),
            patch.object(fetcher, "_wait_interruptibly"),
            patch.object(fetcher, "_get_channel_info", side_effect=read_channel) as read_info,
            patch("src.channel_scanner.WebDriverWait", PredicateWait),
        ):
            report = fetcher._scan_filtered_channels(
                include_channel_ids=None,
                exclude_channel_ids=set(ids[:21]),
                include_channel_names={},
                exclude_channel_names={f"existing {i}" for i in range(21)},
            )

        self.assertEqual([channel["id"] for channel in report.channels], ids[21:])
        self.assertEqual([channel["name"] for channel in report.channels], ["🎧 เพลงเพราะ A", "🎧 เพลงเพราะ B"])
        self.assertEqual(read_info.call_count, 2)
        self.assertEqual(report.unidentified_channel_count, 0)
        self.assertEqual(report.unidentified_channels, [])

    def test_ambiguous_parsed_names_report_each_row_and_reason(self):
        fetcher = FakeChannelFetcher(["A", "B"], channel_names={"A": "Parsed label", "B": "PARSED LABEL"})
        with (
            patch("src.channel_scanner.create_driver", return_value=FakeDriver("A")),
            patch("src.channel_scanner.logger") as log,
        ):
            report = fetcher.run("user@example.test", "test-only", include_channel_ids={"A"},
                                 include_channel_names={"A": "Parsed label"})

        self.assertEqual(report.unidentified_channel_count, 2)
        self.assertEqual([entry["menu_index"] for entry in report.unidentified_channels], [1, 2])
        self.assertEqual([entry["reason"] for entry in report.unidentified_channels], ["ambiguous_name"] * 2)
        self.assertEqual([entry["channel_name"] for entry in report.unidentified_channels],
                         ["Parsed label", "PARSED LABEL"])
        self.assertEqual(log.warning.call_count, 2)

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
        self.assertEqual(fetcher._owner_email, "user@example.com")

    def test_deleted_channel_status_is_read_from_row_status_not_title(self):
        fetcher = ChannelFetcher()
        driver = StatusMenuDriver([], "https://studio.youtube.com/channel/A")
        deleted = StatusMenuRow(
            "B", driver, title="Lo Mejor Bandas Románticas", status="Đã xoá kênh"
        )
        english = StatusMenuRow("C", driver, status="Deleted channel")
        title_only = StatusMenuRow(
            "D", driver, title="Deleted channel", status="100 subscribers"
        )

        self.assertTrue(fetcher._account_item_is_deleted(deleted))
        self.assertTrue(fetcher._account_item_is_deleted(english))
        self.assertFalse(fetcher._account_item_is_deleted(title_only))

    def test_full_scan_skips_deleted_middle_row_and_loads_channel_below(self):
        driver = StatusMenuDriver([], "https://studio.youtube.com/channel/A")
        driver.rows = [
            StatusMenuRow("A", driver, active=True),
            StatusMenuRow("B", driver, status="Đã xóa kênh"),
            StatusMenuRow("C", driver),
        ]
        fetcher = ChannelFetcher()
        fetcher.driver = driver

        with (
            patch("src.channel_scanner.WebDriverWait", PredicateWait),
            patch.object(
                fetcher,
                "_get_channel_info",
                side_effect=lambda: {
                    "id": fetcher._current_channel_id(),
                    "name": fetcher._current_channel_id(),
                },
            ),
        ):
            report = fetcher._scan_authenticated_channels()

        self.assertTrue(report.completed)
        self.assertEqual([item["id"] for item in report.channels], ["A", "C"])
        self.assertEqual(report.deleted_channel_count, 1)
        self.assertEqual(fetcher._current_channel_id(), "C")

    def test_initial_chooser_skips_deleted_first_row(self):
        driver = StatusMenuDriver([], "https://www.youtube.com/account_switcher")
        driver.rows = [
            StatusMenuRow("A", driver, status="Đã xoá kênh"),
            StatusMenuRow("B", driver),
        ]
        fetcher = ChannelFetcher()
        fetcher.driver = driver

        with (
            patch("src.channel_scanner.WebDriverWait", PredicateWait),
            patch.object(
                fetcher,
                "_wait_for_channel_menu_entries_ready",
                side_effect=fetcher._read_visible_channel_menu_entries_once,
            ),
        ):
            selected = fetcher._select_initial_channel_once()

        self.assertTrue(selected)
        self.assertEqual(fetcher._current_channel_id(), "B")
        self.assertEqual(fetcher.last_report.deleted_channel_count, 1)

    def test_initial_chooser_with_only_deleted_channels_has_clean_end(self):
        driver = StatusMenuDriver([], "https://www.youtube.com/account_switcher")
        driver.rows = [StatusMenuRow("A", driver, status="Đã xoá kênh")]
        fetcher = ChannelFetcher()
        fetcher.driver = driver

        with patch.object(
            fetcher,
            "_wait_for_channel_menu_entries_ready",
            side_effect=fetcher._read_visible_channel_menu_entries_once,
        ):
            selected = fetcher._select_initial_channel_once()

        self.assertFalse(selected)
        self.assertEqual(fetcher.last_report.deleted_channel_count, 1)

    def test_selected_reload_skips_deleted_channel_and_continues(self):
        fetcher = FakeChannelFetcher(
            ["A", "B", "C"], deleted_channel_ids={"B"}
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                include_channel_ids={"B", "C"},
                include_channel_names={"B": "B", "C": "C"},
            )

        self.assertTrue(report.completed)
        self.assertEqual([item["id"] for item in report.channels], ["C"])
        self.assertEqual(report.deleted_channel_count, 1)
        self.assertEqual(report.missing_channel_ids, [])
        self.assertEqual(fetcher.filtered_switches, ["C"])

    def test_add_new_skips_deleted_channel_and_finds_later_one(self):
        fetcher = FakeChannelFetcher(
            ["A", "B", "C"], deleted_channel_ids={"B"}
        )
        driver = FakeDriver("A")

        with patch("src.channel_scanner.create_driver", return_value=driver):
            report = fetcher.run(
                "user@example.com",
                "not-logged",
                exclude_channel_ids={"A"},
                exclude_channel_names={"A"},
            )

        self.assertTrue(report.completed)
        self.assertEqual([item["id"] for item in report.channels], ["C"])
        self.assertEqual(report.deleted_channel_count, 1)
        self.assertEqual(fetcher.filtered_switches, ["C"])

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

    def test_add_new_verifies_ids_when_a_new_channel_has_an_existing_name(self):
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

        self.assertEqual(fetcher.info_calls, ["B", "C"])
        self.assertEqual(fetcher.filtered_switches, ["B", "C"])
        self.assertEqual(fetcher.switch_calls, 0)
        self.assertEqual([item["id"] for item in report.channels], ["B", "C"])
        self.assertEqual(report.skipped_channel_ids, ["A"])

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
