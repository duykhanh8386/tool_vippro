# RECOVERED: reconstructed from CPython 3.12 bytecode
import hashlib
import json
import re
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable, Mapping, TypeVar

import requests
from loguru import logger
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    InvalidSessionIdException,
    NoSuchElementException,
    NoSuchWindowException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.channel_store import channel_store
from src.cookie_utils import normalize_cookies_for_storage
from src.utils import create_driver, get_request_payload_from_performance_log
from src.task_runtime import TaskStopped, current_run_context, unregister_driver


AUTHENTICATION_TIMEOUT_SECONDS = 10 * 60
LOGIN_FIELD_TIMEOUT_SECONDS = 30
STUDIO_LOAD_TIMEOUT_SECONDS = 60
ACCOUNT_MENU_TIMEOUT_SECONDS = 20
OVERLAY_CLICK_MAX_ATTEMPTS = 3
OVERLAY_DISMISS_TIMEOUT_SECONDS = 3 * 60
OVERLAY_POLL_INTERVAL_SECONDS = 0.5
BOTGUARD_TIMEOUT_SECONDS = 20
CHANNEL_HTTP_CONNECT_TIMEOUT_SECONDS = 10
CHANNEL_HTTP_READ_TIMEOUT_SECONDS = 30
CHANNEL_SCAN_MAX_ATTEMPTS = 3
CHANNEL_SCAN_RETRY_DELAY_SECONDS = 0.5
CHANNEL_SCAN_DIAGNOSTIC_LIMIT = 500


class ChannelScanErrorCategory(str, Enum):
    TRANSIENT_UI_ERROR = "TRANSIENT_UI_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    UNKNOWN_AUTH_STATE = "UNKNOWN_AUTH_STATE"
    CHANNEL_ERROR = "CHANNEL_ERROR"
    SCAN_END = "SCAN_END"
    FATAL_ERROR = "FATAL_ERROR"


class ChannelScanError(RuntimeError):
    def __init__(
        self,
        category: ChannelScanErrorCategory,
        *,
        step: str,
        detail: str,
        channel_index: int | None = None,
        channel_id: str | None = None,
        attempt: int = 1,
        exception_type: str = "",
        retryable: bool | None = None,
    ) -> None:
        self.category = category
        self.step = step
        self.detail = detail
        self.channel_index = channel_index
        self.channel_id = channel_id
        self.attempt = attempt
        self.exception_type = exception_type
        # Some transient-looking errors have already exhausted a more specific
        # retry policy. Do not restart that whole policy from the outer wrapper.
        self.retryable = retryable
        super().__init__(
            f"Channel scan error: category={category.value} step={step} "
            f"channel_index={channel_index} channel_id={channel_id or '<unknown>'} "
            f"attempt={attempt} exception={exception_type or '<none>'} "
            f"detail={detail!r}"
        )


@dataclass(frozen=True)
class ChannelScanFailure:
    channel_index: int
    channel_id: str | None
    category: ChannelScanErrorCategory
    step: str
    message: str


@dataclass
class ChannelScanReport:
    channels: list[dict] = field(default_factory=list)
    failures: list[ChannelScanFailure] = field(default_factory=list)
    available_channel_ids: list[str] = field(default_factory=list)
    skipped_channel_ids: list[str] = field(default_factory=list)
    missing_channel_ids: list[str] = field(default_factory=list)
    unidentified_channel_count: int = 0
    completed: bool = False
    end_category: ChannelScanErrorCategory | None = None


_T = TypeVar("_T")
_RETRYABLE_SCAN_ERRORS = {
    ChannelScanErrorCategory.TRANSIENT_UI_ERROR,
    ChannelScanErrorCategory.NETWORK_ERROR,
}
_TRANSIENT_UI_EXCEPTIONS = (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
)
_FATAL_WEBDRIVER_MARKERS = (
    "invalid session",
    "session deleted",
    "no such window",
    "browser has closed",
    "chrome not reachable",
    "disconnected",
)
_SCAN_SECRET_RE = re.compile(
    r"(?i)\b(password|cookie|authorization|sapisidhash|sessiontoken|token|2fa)\b"
    r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|\S+)"
)


class ChannelFetcher:
    LOGIN_URL = "https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fwww.youtube.com%2Fsignin%3Faction_handle_signin%3Dtrue%26app%3Ddesktop%26hl%3Den%26next%3Dhttps%253A%252F%252Fstudio.youtube.com%252F%26feature%3Dredirect_login&hl=en&ifkv=AcMMx-d4fvrPkXxfIg8o7ivlOtaYz55VcK2EWUx6zTt7iSx9wGyBkzr1KUqgfL5C0oMsTMQ6Zd0U7g&passive=true&service=youtube&uilel=3&flowName=GlifWebSignIn&flowEntry=ServiceLogin&dsh=S-1405244270%3A1731600052448568&ddm=1"
    EMAIL_XPATH = "//input[@name='identifier' and @id='identifierId']"
    PASSWORD_XPATH = "//input[@type='password' and @name='Passwd']"
    NEXT_BUTTON_XPATH = "//span[(text()='Next') or (text()='Tiếp theo')]"
    CHANNEL_SELECTION_XPATH = (
        "//ytd-account-item-renderer["
        "contains(concat(' ', normalize-space(@class), ' '), "
        "' ytd-account-item-section-renderer ')"
        "]"
    )
    NEXT_CHANNEL_SELECTION_XPATH = "//ytd-account-item-renderer[@class='style-scope ytd-account-item-section-renderer' and @enable-ring-for-active-account]/following-sibling::ytd-account-item-renderer[1]"
    AVATAR_BUTTON_XPATH = "//*[@id='avatar-btn'] | //ytcp-topbar-menu-button-renderer[contains(concat(' ', normalize-space(@class), ' '), ' ytcpAppHeaderAccountButton ')]"
    SWTICH_ACCOUNT_BUTTON_XPATH = "//ytd-compact-link-renderer[@class='style-scope yt-multi-page-menu-section-renderer' and @has-secondary]"
    ROLE_MANAGER_XPATH = "//div[@class='sublabel style-scope ytcp-topbar-menu-button-renderer']"

    def __init__(self):
        self.driver = None
        self.last_report = ChannelScanReport()

    def run(
        self,
        email,
        password,
        on_authenticated=None,
        *,
        include_channel_ids: Iterable[str] | None = None,
        exclude_channel_ids: Iterable[str] | None = None,
        include_channel_names: Mapping[str, str] | None = None,
        exclude_channel_names: Iterable[str] | None = None,
    ):
        run_context = current_run_context()
        try:
            return self._run(
                email,
                password,
                on_authenticated=on_authenticated,
                include_channel_ids=include_channel_ids,
                exclude_channel_ids=exclude_channel_ids,
                include_channel_names=include_channel_names,
                exclude_channel_names=exclude_channel_names,
            )
        except Exception as exc:
            if run_context is not None and run_context.stopped:
                raise TaskStopped() from exc
            raise
        finally:
            if self.driver is not None:
                driver = self.driver
                self.driver = None
                try:
                    driver.quit()
                except Exception as exc:
                    logger.warning(
                        "Channel scanner WebDriver cleanup failed: type={} detail={}",
                        type(exc).__name__,
                        self._sanitize_detail(exc),
                    )
                finally:
                    unregister_driver(driver)

    def _run(
        self,
        email,
        password,
        on_authenticated=None,
        *,
        include_channel_ids: Iterable[str] | None = None,
        exclude_channel_ids: Iterable[str] | None = None,
        include_channel_names: Mapping[str, str] | None = None,
        exclude_channel_names: Iterable[str] | None = None,
    ):
        logger.info("*** Fetching channel info ***")
        if include_channel_ids is not None and exclude_channel_ids is not None:
            raise ValueError(
                "include_channel_ids and exclude_channel_ids are mutually exclusive"
            )
        included = self._normalize_channel_ids(include_channel_ids)
        excluded = self._normalize_channel_ids(exclude_channel_ids)
        included_names = {
            str(channel_id).strip(): str(name or "").strip()
            for channel_id, name in (include_channel_names or {}).items()
            if str(channel_id).strip() and str(name or "").strip()
        }
        excluded_names = {
            self._normalize_channel_name(name)
            for name in (exclude_channel_names or ())
            if self._normalize_channel_name(name)
        }
        self.last_report = ChannelScanReport()
        self.driver = create_driver(enable_performance_log=True)
        self._run_step_with_retry(
            lambda: self._login(email, password),
            step="login",
            max_attempts=1,
            timeout_category=ChannelScanErrorCategory.UNKNOWN_AUTH_STATE,
            default_category=ChannelScanErrorCategory.UNKNOWN_AUTH_STATE,
        )
        initial_state = self._run_step_with_retry(
            self._wait_for_initial_state,
            step="authentication",
            max_attempts=1,
            timeout_category=ChannelScanErrorCategory.UNKNOWN_AUTH_STATE,
            default_category=ChannelScanErrorCategory.UNKNOWN_AUTH_STATE,
        )
        if on_authenticated is not None:
            on_authenticated()
        if include_channel_ids is not None or exclude_channel_ids is not None:
            return self._scan_filtered_channels(
                include_channel_ids=(
                    included if include_channel_ids is not None else None
                ),
                exclude_channel_ids=(
                    excluded if exclude_channel_ids is not None else None
                ),
                include_channel_names=included_names,
                exclude_channel_names=excluded_names,
            )
        if initial_state == "chooser":
            self._run_step_with_retry(
                self._select_initial_channel_once,
                step="select_initial_channel",
            )
        return self._scan_authenticated_channels()

    @staticmethod
    def _normalize_channel_ids(values: Iterable[str] | None) -> set[str]:
        return {
            str(value).strip()
            for value in (values or ())
            if str(value).strip()
        }

    @staticmethod
    def _normalize_channel_name(value: str | None) -> str:
        return " ".join(
            unicodedata.normalize("NFKC", str(value or "")).split()
        ).casefold()

    def _wait_for_initial_state(self) -> str:
        def detect_initial_state(driver):
            self._checkpoint()
            if self._extract_channel_id(driver.current_url):
                return "channel"
            if driver.find_elements(By.XPATH, self.CHANNEL_SELECTION_XPATH):
                return "chooser"
            return False

        try:
            return WebDriverWait(
                self.driver,
                AUTHENTICATION_TIMEOUT_SECONDS,
                poll_frequency=0.5,
            ).until(detect_initial_state)
        except TimeoutException as exc:
            raise ChannelScanError(
                ChannelScanErrorCategory.UNKNOWN_AUTH_STATE,
                step="authentication",
                detail=(
                    "Authentication did not reach a known Studio channel or "
                    "channel chooser state before the deadline"
                ),
                exception_type=type(exc).__name__,
            ) from exc

    def _select_initial_channel_once(self) -> None:
        if self._extract_channel_id(self.driver.current_url):
            return
        channel_selection_button = WebDriverWait(
            self.driver, LOGIN_FIELD_TIMEOUT_SECONDS
        ).until(
            EC.element_to_be_clickable((By.XPATH, self.CHANNEL_SELECTION_XPATH))
        )
        channel_selection_button.click()
        WebDriverWait(self.driver, STUDIO_LOAD_TIMEOUT_SECONDS).until(
            lambda driver: self._checkpoint_and_get(
                lambda: self._extract_channel_id(driver.current_url) is not None
            )
        )

    def _scan_filtered_channels(
        self,
        *,
        include_channel_ids: set[str] | None,
        exclude_channel_ids: set[str] | None,
        include_channel_names: Mapping[str, str],
        exclude_channel_names: set[str],
    ) -> ChannelScanReport:
        """Scan only explicitly allowed account rows, never probing skipped rows."""
        report = self.last_report
        entries = self._run_step_with_retry(
            self._list_channel_menu_entries_once,
            step="read_channel_menu",
        )
        menu_name_counts = Counter(
            entry.get("normalized_name")
            for entry in entries
            if entry.get("normalized_name")
        )
        report.unidentified_channel_count = sum(
            1
            for entry in entries
            if not entry.get("channel_id") and not entry.get("normalized_name")
        )
        available_ids = list(
            dict.fromkeys(
                entry["channel_id"]
                for entry in entries
                if entry.get("channel_id")
            )
        )
        selected_targets: list[dict] = []

        if include_channel_ids is not None:
            selected_ids_by_name: dict[str, list[str]] = defaultdict(list)
            for channel_id in include_channel_ids:
                normalized_name = self._normalize_channel_name(
                    include_channel_names.get(channel_id)
                )
                if normalized_name:
                    selected_ids_by_name[normalized_name].append(channel_id)

            matched_ids: set[str] = set()
            for entry in entries:
                menu_channel_id = entry.get("channel_id")
                expected_channel_id = None
                if menu_channel_id in include_channel_ids:
                    expected_channel_id = menu_channel_id
                if expected_channel_id is None:
                    normalized_name = entry.get("normalized_name") or ""
                    name_matches = selected_ids_by_name.get(normalized_name, [])
                    if (
                        normalized_name
                        and menu_name_counts[normalized_name] == 1
                        and len(name_matches) == 1
                    ):
                        expected_channel_id = name_matches[0]

                if expected_channel_id and expected_channel_id not in matched_ids:
                    target = dict(entry)
                    target["expected_channel_id"] = expected_channel_id
                    selected_targets.append(target)
                    matched_ids.add(expected_channel_id)

            report.available_channel_ids = list(
                dict.fromkeys([*available_ids, *matched_ids])
            )
            report.missing_channel_ids = sorted(include_channel_ids - matched_ids)
            report.skipped_channel_ids = [
                channel_id
                for channel_id in available_ids
                if channel_id not in include_channel_ids
            ]
        else:
            excluded = exclude_channel_ids or set()
            report.available_channel_ids = available_ids
            report.skipped_channel_ids = [
                channel_id for channel_id in available_ids if channel_id in excluded
            ]
            for entry in entries:
                menu_channel_id = entry.get("channel_id")
                normalized_name = entry.get("normalized_name") or ""
                if menu_channel_id:
                    if menu_channel_id in excluded:
                        continue
                elif not normalized_name:
                    continue
                elif normalized_name in exclude_channel_names:
                    continue
                elif menu_name_counts[normalized_name] != 1:
                    report.unidentified_channel_count += 1
                    continue
                target = dict(entry)
                target["expected_channel_id"] = menu_channel_id
                selected_targets.append(target)

        logger.info(
            "Filtered channel scan: available={} selected={} skipped={} missing={} unidentified={}",
            len(report.available_channel_ids),
            len(selected_targets),
            len(report.skipped_channel_ids),
            len(report.missing_channel_ids),
            report.unidentified_channel_count,
        )
        for channel_index, target in enumerate(selected_targets, start=1):
            self._checkpoint()
            expected_channel_id = target.get("expected_channel_id")
            menu_channel_id = target.get("channel_id")
            channel_name = str(target.get("channel_name") or "")
            current_channel_id = self._current_channel_id()
            target_is_current = bool(
                (expected_channel_id and current_channel_id == expected_channel_id)
                or (menu_channel_id and current_channel_id == menu_channel_id)
                or (target.get("active") and current_channel_id)
            )
            if not target_is_current:
                try:
                    self._run_step_with_retry(
                        lambda: self._switch_to_channel_match_once(
                            channel_id=menu_channel_id,
                            channel_name=channel_name,
                            expected_channel_id=expected_channel_id,
                        ),
                        step="switch_channel",
                        channel_index=channel_index,
                        channel_id=expected_channel_id or menu_channel_id,
                    )
                except ChannelScanError as exc:
                    if exc.category in {
                        ChannelScanErrorCategory.AUTH_ERROR,
                        ChannelScanErrorCategory.UNKNOWN_AUTH_STATE,
                        ChannelScanErrorCategory.FATAL_ERROR,
                    }:
                        raise
                    self._record_channel_failure(
                        report,
                        exc,
                        channel_index,
                        expected_channel_id or menu_channel_id,
                    )
                    continue

            actual_channel_id = self._current_channel_id()
            if expected_channel_id and actual_channel_id != expected_channel_id:
                error = ChannelScanError(
                    ChannelScanErrorCategory.CHANNEL_ERROR,
                    step="verify_channel_identity",
                    detail=(
                        "Channel name matched but the Studio URL returned a different "
                        "Channel ID; skipped to avoid updating the wrong channel"
                    ),
                    channel_index=channel_index,
                    channel_id=expected_channel_id,
                    retryable=False,
                )
                self._record_channel_failure(
                    report, error, channel_index, expected_channel_id
                )
                continue
            if exclude_channel_ids is not None and actual_channel_id in (
                exclude_channel_ids or set()
            ):
                if actual_channel_id not in report.skipped_channel_ids:
                    report.skipped_channel_ids.append(actual_channel_id)
                continue
            self._scan_current_channel(
                report,
                channel_index,
                expected_channel_id=actual_channel_id or expected_channel_id,
            )

        report.completed = True
        report.end_category = ChannelScanErrorCategory.SCAN_END
        return report

    def _list_channel_menu_entries_once(self) -> list[dict]:
        self._open_channel_switcher_once()
        self._checkpoint()
        elements = self.driver.find_elements(By.XPATH, self.CHANNEL_SELECTION_XPATH)
        entries = []
        for element in elements:
            channel_name = self._channel_name_from_account_item(element)
            entries.append(
                {
                    "channel_id": self._channel_id_from_account_item(element),
                    "channel_name": channel_name,
                    "normalized_name": self._normalize_channel_name(channel_name),
                    "active": self._account_item_is_active(element),
                    "element": element,
                }
            )
        return entries

    def _channel_name_from_account_item(self, element) -> str:
        for xpath in (
            ".//*[@id='account-name']",
            ".//*[contains(concat(' ', normalize-space(@class), ' '), ' account-name ')]",
            ".//yt-formatted-string[@id='channel-title']",
        ):
            try:
                for candidate in element.find_elements(By.XPATH, xpath):
                    text = " ".join(str(getattr(candidate, "text", "") or "").split())
                    if text:
                        return text
            except (StaleElementReferenceException, WebDriverException):
                continue
        try:
            lines = [
                " ".join(line.split())
                for line in str(getattr(element, "text", "") or "").splitlines()
                if " ".join(line.split())
            ]
            return lines[0] if lines else ""
        except (StaleElementReferenceException, WebDriverException):
            return ""

    def _account_item_is_active(self, element) -> bool:
        try:
            return bool(
                self.driver.execute_script(
                    "return arguments[0].hasAttribute('enable-ring-for-active-account');",
                    element,
                )
            )
        except (StaleElementReferenceException, WebDriverException):
            return False

    def _channel_id_from_account_item(self, element) -> str | None:
        """Read a switcher row ID without clicking the row."""
        candidates: list[str] = []
        for attribute in (
            "href",
            "data-channel-id",
            "channel-id",
            "external-id",
            "data-external-id",
            "data-channel-external-id",
            "data-ytid",
            "outerHTML",
        ):
            try:
                value = element.get_attribute(attribute)
            except (StaleElementReferenceException, WebDriverException):
                value = None
            if value:
                candidates.append(str(value))

        try:
            for anchor in element.find_elements(By.XPATH, ".//*[@href]"):
                href = anchor.get_attribute("href")
                if href:
                    candidates.append(str(href))
        except (StaleElementReferenceException, WebDriverException):
            pass

        try:
            javascript_candidates = self.driver.execute_script(
                """
                const row = arguments[0];
                const found = [];
                const seen = new WeakSet();
                let visited = 0;
                function visit(value, key, depth) {
                    if (visited++ > 4000 || depth > 12 || value == null) return;
                    if (typeof value === 'string') {
                        if (
                            value.includes('/channel/') ||
                            /^UC[A-Za-z0-9_-]{22}$/.test(value) ||
                            /channel.*id|external.*id|browseid/i.test(key || '')
                        ) found.push(value);
                        return;
                    }
                    if (typeof value !== 'object' || seen.has(value)) return;
                    seen.add(value);
                    if (Array.isArray(value)) {
                        for (const item of value) visit(item, key, depth + 1);
                    } else {
                        for (const [childKey, child] of Object.entries(value)) {
                            visit(child, childKey, depth + 1);
                        }
                    }
                }
                visit(row.data, 'data', 0);
                visit(row.__data, '__data', 0);
                for (const node of row.querySelectorAll('[href]')) {
                    if (node.href) found.push(node.href);
                }
                return [...new Set(found)].slice(0, 100);
                """,
                element,
            )
            if isinstance(javascript_candidates, list):
                candidates.extend(str(value) for value in javascript_candidates)
        except (StaleElementReferenceException, WebDriverException):
            pass

        for candidate in candidates:
            channel_id = self._extract_channel_id(candidate)
            if channel_id:
                return channel_id
            exact_match = re.fullmatch(r"UC[A-Za-z0-9_-]{22}", candidate.strip())
            if exact_match:
                return exact_match.group(0)
        return None

    def _switch_to_channel_match_once(
        self,
        *,
        channel_id: str | None,
        channel_name: str,
        expected_channel_id: str | None,
    ) -> None:
        self._checkpoint()
        if expected_channel_id and self._current_channel_id() == expected_channel_id:
            return
        entries = self._list_channel_menu_entries_once()
        matching_entries = []
        if channel_id:
            matching_entries = [
                entry for entry in entries if entry.get("channel_id") == channel_id
            ]
        if not matching_entries and channel_name:
            normalized_name = self._normalize_channel_name(channel_name)
            matching_entries = [
                entry
                for entry in entries
                if entry.get("normalized_name") == normalized_name
            ]
        target = (
            matching_entries[0].get("element")
            if len(matching_entries) == 1
            else None
        )
        if target is None:
            raise ChannelScanError(
                ChannelScanErrorCategory.CHANNEL_ERROR,
                step="switch_channel",
                detail=(
                    "Selected channel was missing or its name was not unique in the "
                    "account menu"
                ),
                channel_id=expected_channel_id or channel_id,
                retryable=False,
            )
        previous_channel_id = self._current_channel_id()
        target.click()

        def channel_switch_finished(driver) -> bool:
            current_url = str(getattr(driver, "current_url", ""))
            if "channel-appeal" in current_url:
                return True
            actual_channel_id = self._extract_channel_id(current_url)
            if expected_channel_id:
                return actual_channel_id == expected_channel_id
            return bool(
                actual_channel_id and actual_channel_id != previous_channel_id
            )

        WebDriverWait(self.driver, STUDIO_LOAD_TIMEOUT_SECONDS).until(
            lambda driver: self._checkpoint_and_get(
                lambda: channel_switch_finished(driver)
            )
        )

    def _switch_to_channel_id_once(self, channel_id: str) -> None:
        self._switch_to_channel_match_once(
            channel_id=channel_id,
            channel_name="",
            expected_channel_id=channel_id,
        )

    def _scan_authenticated_channels(self) -> ChannelScanReport:
        report = self.last_report
        channel_index = 1

        while True:
            self._checkpoint()
            self._scan_current_channel(report, channel_index)
            self._checkpoint()

            current_channel_id = self._run_step_with_retry(
                self._current_channel_id,
                step="read_channel_state",
                channel_index=channel_index,
            )
            self._run_step_with_retry(
                self._open_channel_switcher_once,
                step="open_channel_switcher",
                channel_index=channel_index,
                channel_id=current_channel_id,
            )
            self._checkpoint()
            has_next_channel = self._run_step_with_retry(
                self._has_next_channel,
                step="detect_next_channel",
                channel_index=channel_index,
                channel_id=current_channel_id,
            )
            if not has_next_channel:
                report.completed = True
                report.end_category = ChannelScanErrorCategory.SCAN_END
                logger.info(
                    "Channel scan end confirmed: scanned={} saved={} failed={}",
                    channel_index,
                    len(report.channels),
                    len(report.failures),
                )
                return report

            previous_channel_id = self._run_step_with_retry(
                self._current_channel_id,
                step="read_channel_state",
                channel_index=channel_index,
            )
            self._run_step_with_retry(
                lambda: self._switch_to_next_channel_once(previous_channel_id),
                step="switch_channel",
                channel_index=channel_index + 1,
                channel_id=previous_channel_id,
            )
            channel_index += 1

    def _scan_current_channel(
        self,
        report: ChannelScanReport,
        channel_index: int,
        expected_channel_id: str | None = None,
    ) -> None:
        current_url = self._run_step_with_retry(
            lambda: str(getattr(self.driver, "current_url", "")),
            step="read_channel_state",
            channel_index=channel_index,
        )
        channel_id = self._extract_channel_id(current_url) or expected_channel_id
        if "channel-appeal" in current_url:
            error = ChannelScanError(
                ChannelScanErrorCategory.CHANNEL_ERROR,
                step="channel_state",
                detail="YouTube reports that this channel is unavailable or removed",
                channel_index=channel_index,
                channel_id=channel_id,
            )
            self._record_channel_failure(report, error, channel_index, channel_id)
            return

        try:
            channel = self._run_step_with_retry(
                self._get_channel_info,
                step="channel_info",
                channel_index=channel_index,
                channel_id=channel_id,
                default_category=ChannelScanErrorCategory.CHANNEL_ERROR,
            )
        except ChannelScanError as exc:
            if exc.category in {
                ChannelScanErrorCategory.AUTH_ERROR,
                ChannelScanErrorCategory.UNKNOWN_AUTH_STATE,
                ChannelScanErrorCategory.FATAL_ERROR,
            }:
                raise
            self._record_channel_failure(report, exc, channel_index, channel_id)
            return
        report.channels.append(channel)

    def _record_channel_failure(
        self,
        report: ChannelScanReport,
        error: ChannelScanError,
        channel_index: int,
        channel_id: str | None,
    ) -> None:
        report.failures.append(
            ChannelScanFailure(
                channel_index=channel_index,
                channel_id=channel_id,
                category=error.category,
                step=error.step,
                message=str(error),
            )
        )
        logger.error("Skipping channel after bounded failure: {}", error)

    def _open_channel_switcher_once(self) -> None:
        self._checkpoint()
        if self.driver.find_elements(By.XPATH, self.CHANNEL_SELECTION_XPATH):
            return
        deadline = time.monotonic() + OVERLAY_DISMISS_TIMEOUT_SECONDS
        self._click_with_overlay_retry(
            (By.XPATH, self.AVATAR_BUTTON_XPATH),
            action="nút menu tài khoản",
            deadline=deadline,
        )
        self._click_with_overlay_retry(
            (By.XPATH, self.SWTICH_ACCOUNT_BUTTON_XPATH),
            action="nút chuyển kênh",
            deadline=deadline,
        )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ChannelScanError(
                ChannelScanErrorCategory.TRANSIENT_UI_ERROR,
                step="open_channel_switcher",
                detail="Account menu did not open before the 180s overlay deadline",
                retryable=False,
            )
        WebDriverWait(self.driver, min(ACCOUNT_MENU_TIMEOUT_SECONDS, remaining)).until(
            lambda driver: self._checkpoint_and_get(
                lambda: bool(
                    driver.find_elements(By.XPATH, self.CHANNEL_SELECTION_XPATH)
                )
            )
        )

    def _click_with_overlay_retry(
        self,
        locator: tuple[str, str],
        *,
        action: str,
        deadline: float,
    ) -> None:
        """Click a Studio control without giving an overlay an immediate win.

        YouTube occasionally leaves a ``tp-yt-paper-dialog-backdrop`` above the
        account avatar. Selenium's normal ``element_to_be_clickable`` does not
        detect that overlap. This makes at most three click attempts and gives
        an obstructing overlay a total of three minutes to disappear.
        """
        last_intercept: ElementClickInterceptedException | None = None

        for attempt in range(1, OVERLAY_CLICK_MAX_ATTEMPTS + 1):
            self._checkpoint()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            target = WebDriverWait(
                self.driver,
                min(ACCOUNT_MENU_TIMEOUT_SECONDS, remaining),
                poll_frequency=OVERLAY_POLL_INTERVAL_SECONDS,
            ).until(EC.element_to_be_clickable(locator))
            try:
                target.click()
                return
            except ElementClickInterceptedException as exc:
                last_intercept = exc
                remaining = max(0.0, deadline - time.monotonic())
                attempts_left = OVERLAY_CLICK_MAX_ATTEMPTS - attempt + 1
                wait_deadline = min(
                    deadline,
                    time.monotonic() + remaining / max(1, attempts_left),
                )
                logger.warning(
                    "Studio {} is covered by an overlay; click attempt {}/{}. "
                    "Waiting up to {:.1f}s before retrying.",
                    action,
                    attempt,
                    OVERLAY_CLICK_MAX_ATTEMPTS,
                    max(0.0, wait_deadline - time.monotonic()),
                )
                self._wait_until_click_target_is_unobstructed(target, wait_deadline)

        elapsed = max(
            0.0,
            OVERLAY_DISMISS_TIMEOUT_SECONDS - max(0.0, deadline - time.monotonic()),
        )
        error = ChannelScanError(
            ChannelScanErrorCategory.TRANSIENT_UI_ERROR,
            step="open_channel_switcher",
            detail=(
                f"Studio {action} remained covered after "
                f"{OVERLAY_CLICK_MAX_ATTEMPTS} click attempts and {elapsed:.1f}s"
            ),
            exception_type=(
                type(last_intercept).__name__
                if last_intercept is not None
                else "TimeoutException"
            ),
            retryable=False,
        )
        raise error from last_intercept

    def _wait_until_click_target_is_unobstructed(
        self, target, deadline: float
    ) -> bool:
        """Return once the target centre is no longer covered by another element."""
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False

        def target_is_unobstructed(driver) -> bool:
            self._checkpoint()
            try:
                return bool(
                    driver.execute_script(
                        """
                        const target = arguments[0];
                        if (!target || !target.isConnected) return false;
                        target.scrollIntoView({block: 'center', inline: 'center'});
                        const box = target.getBoundingClientRect();
                        const x = box.left + box.width / 2;
                        const y = box.top + box.height / 2;
                        const hit = document.elementFromPoint(x, y);
                        return hit === target || target.contains(hit);
                        """,
                        target,
                    )
                )
            except (StaleElementReferenceException, NoSuchElementException):
                return False

        try:
            WebDriverWait(
                self.driver,
                remaining,
                poll_frequency=OVERLAY_POLL_INTERVAL_SECONDS,
            ).until(target_is_unobstructed)
            return True
        except TimeoutException:
            return False

    def _has_next_channel(self) -> bool:
        self._checkpoint()
        return bool(
            self.driver.find_elements(By.XPATH, self.NEXT_CHANNEL_SELECTION_XPATH)
        )

    def _switch_to_next_channel_once(self, previous_channel_id: str | None) -> None:
        self._checkpoint()
        next_button = WebDriverWait(
            self.driver, ACCOUNT_MENU_TIMEOUT_SECONDS
        ).until(
            EC.element_to_be_clickable(
                (By.XPATH, self.NEXT_CHANNEL_SELECTION_XPATH)
            )
        )
        next_button.click()
        WebDriverWait(self.driver, STUDIO_LOAD_TIMEOUT_SECONDS).until(
            lambda driver: self._checkpoint_and_get(
                lambda: (
                    "channel-appeal" in driver.current_url
                    or (
                        self._extract_channel_id(driver.current_url) is not None
                        and self._extract_channel_id(driver.current_url)
                        != previous_channel_id
                    )
                )
            )
        )

    def _run_step_with_retry(
        self,
        action: Callable[[], _T],
        *,
        step: str,
        channel_index: int | None = None,
        channel_id: str | None = None,
        max_attempts: int = CHANNEL_SCAN_MAX_ATTEMPTS,
        timeout_category: ChannelScanErrorCategory = ChannelScanErrorCategory.TRANSIENT_UI_ERROR,
        default_category: ChannelScanErrorCategory = ChannelScanErrorCategory.FATAL_ERROR,
    ) -> _T:
        attempts = max(1, int(max_attempts))
        started_at = time.monotonic()
        for attempt in range(1, attempts + 1):
            self._checkpoint()
            try:
                return action()
            except TaskStopped:
                raise
            except Exception as exc:
                self._checkpoint()
                error = self._classify_error(
                    exc,
                    step=step,
                    channel_index=channel_index,
                    channel_id=channel_id,
                    attempt=attempt,
                    timeout_category=timeout_category,
                    default_category=default_category,
                )
                elapsed = time.monotonic() - started_at
                if (
                    error.retryable is not False
                    and error.category in _RETRYABLE_SCAN_ERRORS
                    and attempt < attempts
                ):
                    logger.warning(
                        "Channel scan retry: channel_index={} channel_id={} step={} "
                        "attempt={}/{} elapsed={:.1f}s category={} exception={} detail={}",
                        channel_index,
                        channel_id or "<unknown>",
                        step,
                        attempt,
                        attempts,
                        elapsed,
                        error.category.value,
                        error.exception_type or type(exc).__name__,
                        error.detail,
                    )
                    self._wait_interruptibly(CHANNEL_SCAN_RETRY_DELAY_SECONDS)
                    continue
                raise error from exc
        raise AssertionError("unreachable channel scan retry state")

    def _classify_error(
        self,
        exc: Exception,
        *,
        step: str,
        channel_index: int | None,
        channel_id: str | None,
        attempt: int,
        timeout_category: ChannelScanErrorCategory,
        default_category: ChannelScanErrorCategory,
    ) -> ChannelScanError:
        if isinstance(exc, ChannelScanError):
            return ChannelScanError(
                exc.category,
                step=exc.step or step,
                detail=exc.detail,
                channel_index=exc.channel_index or channel_index,
                channel_id=exc.channel_id or channel_id,
                attempt=attempt,
                exception_type=exc.exception_type or type(exc).__name__,
                retryable=exc.retryable,
            )
        if isinstance(exc, TimeoutException):
            category = timeout_category
        elif isinstance(exc, (requests.Timeout, requests.ConnectionError)):
            category = ChannelScanErrorCategory.NETWORK_ERROR
        elif isinstance(exc, requests.HTTPError):
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code in (401, 403):
                category = ChannelScanErrorCategory.AUTH_ERROR
            elif status_code in (408, 425, 429) or (
                status_code is not None and status_code >= 500
            ):
                category = ChannelScanErrorCategory.NETWORK_ERROR
            else:
                category = ChannelScanErrorCategory.CHANNEL_ERROR
        elif isinstance(exc, (InvalidSessionIdException, NoSuchWindowException)):
            category = ChannelScanErrorCategory.FATAL_ERROR
        elif isinstance(exc, _TRANSIENT_UI_EXCEPTIONS):
            category = ChannelScanErrorCategory.TRANSIENT_UI_ERROR
        elif isinstance(exc, WebDriverException):
            detail = self._sanitize_detail(exc).lower()
            category = (
                ChannelScanErrorCategory.FATAL_ERROR
                if any(marker in detail for marker in _FATAL_WEBDRIVER_MARKERS)
                else ChannelScanErrorCategory.TRANSIENT_UI_ERROR
            )
        elif isinstance(exc, TimeoutError):
            category = ChannelScanErrorCategory.TRANSIENT_UI_ERROR
        else:
            category = default_category
        return ChannelScanError(
            category,
            step=step,
            detail=self._sanitize_detail(exc),
            channel_index=channel_index,
            channel_id=channel_id,
            attempt=attempt,
            exception_type=type(exc).__name__,
        )

    def _current_channel_id(self) -> str | None:
        return self._extract_channel_id(str(getattr(self.driver, "current_url", "")))

    @staticmethod
    def _sanitize_detail(value) -> str:
        compact = " ".join(str(value or "").split())
        compact = _SCAN_SECRET_RE.sub(
            lambda match: f"{match.group(1)}=<redacted>", compact
        )
        if len(compact) > CHANNEL_SCAN_DIAGNOSTIC_LIMIT:
            return compact[:CHANNEL_SCAN_DIAGNOSTIC_LIMIT] + "..."
        return compact

    def _login(self, email: str, password: str):
        self.driver.get(self.LOGIN_URL)
        email_input = WebDriverWait(
            self.driver, LOGIN_FIELD_TIMEOUT_SECONDS
        ).until(EC.element_to_be_clickable((By.XPATH, self.EMAIL_XPATH)))
        for char in email:
            self._checkpoint()
            email_input.send_keys(char)
            self._wait_interruptibly(0.05)

        next_button = self.driver.find_element(By.XPATH, self.NEXT_BUTTON_XPATH)
        next_button.click()
        password_input = WebDriverWait(
            self.driver, LOGIN_FIELD_TIMEOUT_SECONDS
        ).until(
            EC.element_to_be_clickable((By.XPATH, self.PASSWORD_XPATH))
        )
        for char in password:
            self._checkpoint()
            password_input.send_keys(char)
            self._wait_interruptibly(0.05)

        next_button = self.driver.find_element(By.XPATH, self.NEXT_BUTTON_XPATH)
        next_button.click()

    def _get_channel_info(self):
        img_element_xapth = "//img[@class='thumbnail image-thumbnail style-scope ytcp-navigation-drawer']"
        current_url = str(getattr(self.driver, "current_url", ""))
        if "accounts.google.com" in current_url:
            raise ChannelScanError(
                ChannelScanErrorCategory.AUTH_ERROR,
                step="channel_info",
                detail="Browser session was redirected to Google login",
            )
        WebDriverWait(self.driver, STUDIO_LOAD_TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.XPATH, img_element_xapth))
        )
        id = self._extract_channel_id(self.driver.current_url)
        if not id:
            raise ChannelScanError(
                ChannelScanErrorCategory.CHANNEL_ERROR,
                step="channel_info",
                detail="Studio URL does not contain a channel ID",
            )
        img_element = self.driver.find_element("xpath", img_element_xapth)
        img_src = img_element.get_attribute("src")
        name = img_element.get_attribute("alt")
        cookies_raw = self.driver.get_cookies()
        cookies = normalize_cookies_for_storage(cookies_raw)
        logger.info(f"*** Channel info fetched successfully: {name} ***")

        sapisidhash = None
        for cookie in cookies:
            if cookie["name"] == "SAPISID":
                sapisid = cookie["value"]
                sapisidhash = self._generate_sapisidhash_header(sapisid)
        if not sapisidhash:
            raise ChannelScanError(
                ChannelScanErrorCategory.AUTH_ERROR,
                step="channel_cookies",
                detail="Authenticated browser session is missing the SAPISID cookie",
                channel_id=id,
            )

        next_url = (
            f"https://studio.youtube.com/channel/{id}"
            "/analytics/tab-overview/period-default"
        )
        self.driver.get(next_url)
        if "accounts.google.com" in str(getattr(self.driver, "current_url", "")):
            raise ChannelScanError(
                ChannelScanErrorCategory.AUTH_ERROR,
                step="botguard",
                detail="Studio redirected to Google login while loading channel analytics",
                channel_id=id,
            )
        try:
            payload = get_request_payload_from_performance_log(
                self.driver,
                "youtubei/v1/att/esr?alt=json",
                timeout=BOTGUARD_TIMEOUT_SECONDS,
            )
            payload_json = json.loads(payload)
            challenge = payload_json["challenge"]
            botguardResponse = payload_json["botguardResponse"]
        except TimeoutError:
            raise
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ChannelScanError(
                ChannelScanErrorCategory.CHANNEL_ERROR,
                step="botguard",
                detail=(
                    "BotGuard request payload is missing or malformed: "
                    f"{self._sanitize_detail(exc)}"
                ),
                channel_id=id,
                exception_type=type(exc).__name__,
            ) from exc

        url = f"https://studio.youtube.com/channel/{id}"
        cookie_string = "; ".join(
            [f"{cookie['name']}={cookie['value']}" for cookie in cookies]
        )
        header = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Cookie": cookie_string,
        }
        self._checkpoint()
        res = requests.get(
            url,
            headers=header,
            timeout=(
                CHANNEL_HTTP_CONNECT_TIMEOUT_SECONDS,
                CHANNEL_HTTP_READ_TIMEOUT_SECONDS,
            ),
        )
        res.raise_for_status()
        self._checkpoint()
        if "accounts.google.com" in str(getattr(res, "url", "")):
            raise ChannelScanError(
                ChannelScanErrorCategory.AUTH_ERROR,
                step="channel_http",
                detail="Channel request was redirected to Google login",
                channel_id=id,
            )
        delegated_session_id = self._extract_datasync_id(res.text)
        role = self._get_role_type(res.text)
        if not delegated_session_id or not role:
            raise ChannelScanError(
                ChannelScanErrorCategory.CHANNEL_ERROR,
                step="channel_http",
                detail="Channel response is missing role or delegated session data",
                channel_id=id,
            )
        channel_store.upsert_channel(
            {
                "id": id,
                "name": name,
                "img_src": img_src,
                "delegated_session_id": delegated_session_id,
                "sapisidhash": sapisidhash,
                "role": role,
                "challenge": challenge,
                "botguardResponse": botguardResponse,
                "cookies": cookies,
            }
        )
        return dict(id=id, name=name, img_src=img_src, cookies=cookies)

    @staticmethod
    def _extract_channel_id(url):
        match = re.search("channel/([A-Za-z0-9_-]+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _extract_datasync_id(text):
        pattern = '"datasyncId":"(\\d+\\|\\|\\d*)"'
        match = re.search(pattern, text)
        if match:
            res = match.group(1).split("||")[0]
            return res
        pattern = "\\|\\|(\\d+)"
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    @staticmethod
    def _generate_sapisidhash_header(sapisid, origin="https://studio.youtube.com"):
        time_now = round(time.time())
        sapisidhash = hashlib.sha1(
            f"{time_now} {sapisid} {origin}".encode("utf-8")
        ).hexdigest()
        return f"{time_now}_{sapisidhash}"

    @staticmethod
    def _get_role_type(text):
        pattern = '"channelRoleType":"(CREATOR_CHANNEL_ROLE_TYPE_[A-Z_]+)"'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    @staticmethod
    def _checkpoint():
        run_context = current_run_context()
        if run_context is not None:
            run_context.checkpoint()

    @staticmethod
    def _wait_interruptibly(seconds):
        run_context = current_run_context()
        if run_context is None:
            time.sleep(seconds)
        else:
            run_context.wait(seconds)

    @classmethod
    def _checkpoint_and_get(cls, callback):
        cls._checkpoint()
        return callback()


channel_fetcher = ChannelFetcher()
