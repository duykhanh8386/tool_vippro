"""Stage an existing video's edits in Studio and activate its final Save once."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import time
from urllib.parse import urlparse

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from src.cookie_utils import inject_cookies_via_cdp
from src.module.video_publishing_module import VideoPublishingModule
from src.publishing_browser import PublishingBrowserError, _new_driver, close_driver, wait_for
from src.publishing_thumbnails import ThumbnailReadback
from src.task_runtime import TaskStopped, check_stopped, wait_interruptibly
from src.utils import get_channels_info
from src.video_scan_dates import VIETNAM_TIMEZONE

_BIDI_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
_DIGIT_TRANS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹−", "01234567890123456789-")
_ASCII_TO_ARABIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _normalize_locale_text(text) -> str:
    return _BIDI_RE.sub("", str(text or "")).translate(_DIGIT_TRANS)


def _parse_timezone_offset(note) -> int | None:
    clean = _normalize_locale_text(note)
    match = (
        re.search(r"(?:GMT|UTC|غرينتش)\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?\b", clean, re.I)
        or re.search(r"([+-])\s*(\d{1,2}):(\d{2})\b", clean)
        or re.search(r"([+-])\s*(\d{2})(\d{2})\b", clean)
    )
    if not match:
        return None
    sign = 1 if match[1] == "+" else -1
    return (int(match[2]) * 60 + int(match[3] or 0)) * sign

TITLE = "#title-textarea [contenteditable='true'], #title-textarea textarea"
DESCRIPTION = "#description-textarea [contenteditable='true'], #description-textarea textarea"
RIGHTS_POLICY_NAME = "Monetize in all countries"
DEFAULT_RIGHTS_ARTIST = "1"
PRE_REVIEW_DRAFT_STEPS = ("RIGHTS_MANAGEMENT", "MONETIZATION", "CONTENT_RATINGS")


def visible(scope, selector):
    return next((node for node in scope.find_elements(By.CSS_SELECTOR, selector) if node.is_displayed()), None)


def field_text(driver, node):
    return driver.execute_script("""
        const node=arguments[0];
        if('value' in node)return node.value;
        if(node.childNodes.length===1 && node.firstChild.nodeType===Node.TEXT_NODE)return node.textContent;
        if(node.childNodes.length===1 && node.firstChild.nodeName==='BR')return '';
        return node.innerText;
    """, node) or ""


def set_text(driver, node, text, *, commit=Keys.TAB, force=False):
    if not force and VideoPublishingModule._same_text(field_text(driver, node), text):
        return
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", node)
    node.click()
    node.send_keys(Keys.CONTROL, "a")
    node.send_keys(Keys.BACKSPACE)
    # CDP's native text insertion supports emoji outside ChromeDriver's BMP
    # send_keys limit and dispatches the editor's normal input events.
    plain = text.replace("\r\n", "\n").replace("\r", "\n")
    for index, line in enumerate(plain.split("\n")):
        if index:
            # Plain Enter makes block divs whose blank lines can gain an extra
            # newline. Shift+Enter inserts the editor's explicit line break.
            node.send_keys(Keys.SHIFT, Keys.ENTER, Keys.NULL)
        if line:
            driver.execute_cdp_cmd("Input.insertText", {"text": line})
    actual = field_text(driver, node)
    if (
        node.get_attribute("contenteditable") == "true"
        and actual.endswith("\n")
        and VideoPublishingModule._same_text(actual[:-1], plain)
    ):
        # Chrome keeps an extra caret sentinel newline at the end of pre-wrap
        # contenteditable fields after line breaks even when plain has no
        # trailing newline. Replace that DOM representation with plain text
        # and notify the editor; no HTML from the reference is interpreted.
        driver.execute_script("""
            arguments[0].textContent=arguments[1];
            arguments[0].dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:arguments[1]}));
        """, node, plain)
    if not VideoPublishingModule._same_text(field_text(driver, node), text):
        raise PublishingBrowserError("Studio chưa nhận đúng nội dung vừa nhập; chưa bấm Lưu.")
    if isinstance(commit, (tuple, list)):
        for key in commit:
            node.send_keys(key)
    elif commit:
        node.send_keys(commit)


def validate_metadata(title, description, reference, expected_title, expected_description):
    new_title, new_description = reference.get("title"), reference.get("description")
    if not isinstance(new_title, str) or not new_title or not isinstance(new_description, str):
        raise PublishingBrowserError("Thiếu title hoặc description của video tham chiếu.")
    if len(new_title.encode("utf-16-le")) > 200 or len(new_description.encode("utf-16-le")) > 10000:
        raise PublishingBrowserError("Metadata tham chiếu vượt giới hạn YouTube; không cắt ngắn dữ liệu nguồn.")
    same = VideoPublishingModule._same_text
    if (not any(same(title, value) for value in (expected_title, new_title))
            or not any(same(description, value) for value in (expected_description, new_description))):
        raise PublishingBrowserError("Title/description đã được sửa khác sau khi quét; chưa bấm Lưu để giữ thay đổi đó.")


def _image_ids(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"externalImageId", "imageId"} and isinstance(child, str):
                yield child
            elif isinstance(child, (dict, list)):
                yield from _image_ids(child)
    elif isinstance(value, list):
        for child in value:
            yield from _image_ids(child)


def _video_edits(value, video_id):
    if isinstance(value, dict):
        if (value.get("encryptedVideoId") or value.get("videoId")) == video_id:
            fields = {key: child for key, child in value.items() if key not in {"context", "videoReadMask", "mask", "delegationContext"}}
            if any(key in fields for key in ("thumbnail", "title", "description", "privacyState", "scheduledPublishing", "draftState")):
                yield fields
        for key, child in value.items():
            if key not in {"context", "videoReadMask", "mask", "delegationContext"}:
                yield from _video_edits(child, video_id)
    elif isinstance(value, list):
        for child in value:
            yield from _video_edits(child, video_id)


class NativeSave:
    """Observe the native save's completion, bound to this video and upload."""
    def __init__(self, driver, channel_id, video_id, thumbnail):
        self.driver, self.channel_id, self.video_id, self.thumbnail = driver, channel_id, video_id, thumbnail
        self.requests, self.responses, self.finished = {}, set(), False

    def __call__(self):
        for entry in self.driver.get_log("performance"):
            event = json.loads(entry["message"])["message"]
            params = event.get("params", {})
            identifier = params.get("requestId")
            if event["method"] == "Network.requestWillBeSent":
                request = params.get("request", {})
                url = urlparse(request.get("url", ""))
                if url.hostname != "studio.youtube.com" or "/youtubei/" not in url.path:
                    continue
                try:
                    data = json.loads(request.get("postData", ""))
                except ValueError:
                    continue
                edits = list(_video_edits(data, self.video_id))
                if edits:
                    ids = {item for edit in edits for key, child in edit.items() if "thumbnail" in key.lower() for item in _image_ids(child)}
                    self.requests[identifier] = ids
                    expect = getattr(self.thumbnail, "expect_upload_asset", None)
                    if callable(expect):
                        expect(ids)
            elif event["method"] == "Network.responseReceived" and identifier in self.requests:
                if int(params.get("response", {}).get("status", 0)) != 200:
                    raise PublishingBrowserError("YouTube từ chối lần Lưu cuối; giữ ảnh và tiến độ để kiểm tra lại.")
                self.responses.add(identifier)
            elif event["method"] == "Network.loadingFinished" and identifier in self.responses:
                self.finished = True
                try:
                    result = self.driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": identifier})
                    body = result.get("body", "")
                    if result.get("base64Encoded"):
                        body = base64.b64decode(body).decode("utf-8")
                    saved = json.loads(body.removeprefix(")]}'\n"))
                except (ValueError, WebDriverException):
                    continue
                if not isinstance(saved, dict) or saved.get("error") or saved.get("success") is False:
                    raise PublishingBrowserError("YouTube báo lỗi trong lần Lưu cuối; chưa xác nhận video đã lên lịch.")
                observe = getattr(self.thumbnail, "observe_save_response", None)
                if callable(observe):
                    observe(saved, self.requests[identifier])
        return self.finished


class StudioPublishingEditor:
    MONETIZATION_CONTROLS_GRACE_SECONDS = 3.0
    DRAFT_FALLBACK_GRACE_SECONDS = 5.0

    def __init__(self, controls):
        self.controls = controls

    @staticmethod
    def _is_control_disabled(node):
        return (
            not node.is_enabled()
            or node.get_attribute("disabled") is not None
            or node.get_attribute("aria-disabled") == "true"
        )

    def _open(self, driver, video_id):
        try:
            driver.get(f"https://studio.youtube.com/video/{video_id}/edit?hl=en")
        except TimeoutException:
            # Analytics/video frames can load after the editor. Continue only
            # when the expected URL and actual editable fields are present.
            pass
        if urlparse(driver.current_url).hostname != "studio.youtube.com" or urlparse(driver.current_url).path != f"/video/{video_id}/edit":
            raise PublishingBrowserError("Studio không mở đúng video; chưa bấm Lưu.")
        wait_for(lambda: visible(driver, TITLE) and visible(driver, DESCRIPTION), timeout=90,
                 message="Chưa tải được ô title/description trong Studio; kiểm tra phiên kênh.")

    def _visibility(self, driver):
        select = visible(driver, "ytcp-video-visibility-edit-popup ytcp-video-visibility-select")
        if select is None:
            def locate_trigger():
                for selector in (
                    "ytcp-video-metadata-visibility #select-button",
                    "ytcp-video-metadata-visibility ytcp-dropdown-trigger",
                    "ytcp-video-metadata-visibility #container",
                ):
                    for node in driver.find_elements(By.CSS_SELECTOR, selector):
                        if node.is_displayed():
                            return node
                        try:
                            driver.execute_script(
                                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                                node,
                            )
                        except WebDriverException:
                            continue
                        if node.is_displayed():
                            return node
                return None

            self.controls._click_control(driver, locate_trigger,
                                         message="Chưa mở được phần Chế độ hiển thị trong Studio.")
        return wait_for(lambda: visible(driver, "ytcp-video-visibility-edit-popup ytcp-video-visibility-select"),
                        timeout=30, message="Chưa tải được phần Lên lịch trong Studio.")

    @staticmethod
    def _state(driver, select):
        state = driver.execute_script("""
            const select=arguments[0], shown=e=>!!e && !!e.getClientRects().length && getComputedStyle(e).visibility!=='hidden';
            const scheduler=Array.from(select.querySelectorAll('ytcp-visibility-scheduler')).find(shown);
            let model=scheduler?.model;
            if(!model && scheduler?.getAttribute('model'))try{model=JSON.parse(scheduler.getAttribute('model'))}catch{}
            const picker=scheduler?.querySelector('ytcp-datetime-picker');
            const note=Array.from(picker?.querySelectorAll('.timezone-trigger [aria-label]')||[]).map(e=>e.getAttribute('aria-label')).join(' ');
            return {scheduled:select.getAttribute('second-container-style')==='selected',
              date:model?.date,seconds:model?.selectedTimeOfDayValue,timezoneIndex:model?.selectedTimezoneIndex,timezoneNote:note};
        """, select)
        state["timestamp"] = None
        offset = _parse_timezone_offset(state.get("timezoneNote"))
        if state.get("timezoneIndex") == 0 and offset is not None and state.get("date") is not None and state.get("seconds") is not None:
            try:
                day = state["date"]
                seconds = int(state["seconds"])
                if 0 <= seconds < 86400 and abs(offset) <= 840:
                    moment = datetime(int(day["year"]), int(day["month"]) + 1, int(day["day"]),
                                      tzinfo=timezone(timedelta(minutes=offset))) + timedelta(seconds=seconds)
                    state.update(timestamp=int(moment.timestamp()), offset=offset)
            except (ValueError, TypeError, KeyError, OverflowError):
                pass
        return state

    def _close_visibility(self, driver):
        driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        wait_for(lambda: visible(driver, "ytcp-video-visibility-edit-popup ytcp-video-visibility-select") is None,
                 timeout=15, message="Popup hiển thị chưa đóng; chưa bấm Lưu cuối.")

    def _local_timezone(self, driver, select):
        state = self._state(driver, select)
        if state.get("timezoneIndex") == 0 and state.get("offset") == 420:
            return
        self.controls._click_control(driver, lambda:self.controls._button_control(select, "#timezone-select-button"),
                                     message="Chưa mở được danh sách múi giờ.")
        def local_option():
            for option in driver.find_elements(By.CSS_SELECTOR, 'ytcp-text-menu tp-yt-paper-item[test-id="0"]'):
                clean = _normalize_locale_text(option.text)
                if option.is_displayed() and (
                    re.search(r"(?:GMT|UTC|غرينتش)\s*\+\s*0?7(?::?00)?\b", clean, re.I)
                    or re.search(r"\+\s*0?7:?00\b", clean)
                ):
                    return option
            return None
        self.controls._click_control(driver, local_option, message="Không tìm thấy múi giờ địa phương UTC+7; chưa bấm Lưu.")
        wait_for(lambda:self._state(driver, select).get("offset")==420 and self._state(driver, select).get("timezoneIndex")==0,
                 timeout=10, message="Studio chưa nhận múi giờ UTC+7.")

    @staticmethod
    def _visibility_host_visible(driver):
        if visible(driver, "ytcp-video-metadata-visibility #container") is not None:
            return True
        for selector in (
            "ytcp-video-metadata-visibility #container",
            "ytcp-video-metadata-visibility #select-button",
            "ytcp-video-metadata-visibility ytcp-dropdown-trigger",
        ):
            for node in driver.find_elements(By.CSS_SELECTOR, selector):
                if node.is_displayed():
                    return True
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                        node,
                    )
                except WebDriverException:
                    continue
                if node.is_displayed():
                    return True
        return False

    def _draft_edit_button(self, driver):
        for selector in (
            "ytcp-banner.entity-banner.opened #action-1",
            "ytcp-banner.entity-banner #action-1",
            "ytcp-top-banner ytcp-banner.opened #action-1",
            "ytcp-banner.entity-banner.opened .action-button",
        ):
            button = self.controls._button_control(driver, selector)
            if button is not None:
                return button
        return None

    def _editor_mode(self, driver, *, allow_bannerless_draft=False):
        if visible(driver, "ytcp-uploads-dialog") is not None:
            return "draft"
        if self._visibility_host_visible(driver):
            return "standard"
        state = driver.execute_script("""
            if (document.querySelector('ytcp-video-metadata-visibility #container, ytcp-video-metadata-visibility #select-button')) {
                return {hasVisibility: true, draftStatus: '', isDraft: false, hasSidepanel: false};
            }
            const editor = document.querySelector('ytcp-video-metadata-editor');
            const draftStatus = String(editor?.video?.draftStatus ?? '').trim().toUpperCase();
            const isDraft = editor?.isDraft === true;
            const hasSidepanel = !!document.querySelector('ytcp-video-metadata-editor-sidepanel ytcp-video-info');
            return {hasVisibility: false, draftStatus, isDraft, hasSidepanel};
        """)
        if not isinstance(state, dict) or state.get("hasVisibility"):
            return None
        draft_status = str(state.get("draftStatus") or "").upper()
        explicit_non_draft = bool(draft_status) and bool(
            re.search(r"UNSPECIFIED|NOT_DRAFT|DRAFT_STATUS_NONE|^NONE$", draft_status)
        )
        explicit_draft = bool(state.get("isDraft")) or (bool(draft_status) and not explicit_non_draft)
        if explicit_draft:
            return "draft"
        if explicit_non_draft:
            return None
        if self._draft_edit_button(driver) is not None and state.get("hasSidepanel"):
            return "draft"
        if allow_bannerless_draft and state.get("hasSidepanel"):
            return "draft"
        return None

    def _wait_editor_mode(self, driver, timeout=45):
        started = time.monotonic()
        return wait_for(
            lambda: self._editor_mode(
                driver,
                allow_bannerless_draft=(time.monotonic() - started >= self.DRAFT_FALLBACK_GRACE_SECONDS),
            ),
            timeout=timeout,
            message="Chưa tải được trạng thái hiển thị video trong Studio.",
        )

    @staticmethod
    def _draft_dialog_video_id(driver, dialog):
        dialog_video = str(dialog.get_attribute("video-id") or "").strip()
        if dialog_video:
            return dialog_video
        resolved = driver.execute_script("""
            const dlg = arguments[0];
            if (!dlg) return '';
            const direct = dlg.videoId || dlg.video?.videoId || dlg.video?.encryptedVideoId;
            if (direct) return String(direct);
            const link = dlg.querySelector('a#video-link[href]');
            const m = link ? String(link.href || '').match(/(?:youtu\\.be\\/|v=)([A-Za-z0-9_-]{11})/) : null;
            return m ? m[1] : '';
        """, dialog)
        return str(resolved or "").strip()

    @staticmethod
    def _draft_dialog_ready(driver):
        dialog = visible(driver, "ytcp-uploads-dialog")
        if dialog is None:
            return None
        if any(
            visible(dialog, selector) is not None
            for selector in (
                TITLE,
                "[test-id='DETAILS']",
                "#step-badge-0",
                "ytcp-uploads-review",
                "ytcp-video-visibility-select",
            )
        ):
            return dialog
        return None

    def _open_draft_dialog_via_url(self, driver, channel_id, video_id):
        if not channel_id:
            return None
        try:
            driver.get(f"https://studio.youtube.com/channel/{channel_id}/videos/upload?d=ud&udvid={video_id}&hl=en")
        except TimeoutException:
            pass
        if urlparse(driver.current_url).hostname != "studio.youtube.com":
            raise PublishingBrowserError("Studio không mở đúng trang bản nháp; chưa bấm Lưu.")
        return wait_for(
            lambda: self._draft_dialog_ready(driver),
            timeout=45,
            message="Chưa tải được hộp thoại Chỉnh sửa bản nháp trong Studio.",
        )

    def _open_draft_dialog(self, driver, video_id, *, channel_id=None):
        dialog = self._draft_dialog_ready(driver)
        if dialog is None and self._draft_edit_button(driver) is not None:
            try:
                click_timeout = 15 if channel_id else 30
                self.controls._click_control(
                    driver,
                    lambda: self._draft_edit_button(driver),
                    timeout=click_timeout,
                    message="Chưa mở được hộp thoại Chỉnh sửa bản nháp trong Studio.",
                )
                dialog = wait_for(
                    lambda: self._draft_dialog_ready(driver),
                    timeout=click_timeout,
                    message="Chưa tải được hộp thoại Chỉnh sửa bản nháp trong Studio.",
                )
            except PublishingBrowserError:
                if not channel_id:
                    raise
                dialog = None
        if dialog is None:
            dialog = self._open_draft_dialog_via_url(driver, channel_id, video_id)
        if dialog is None:
            raise PublishingBrowserError("Chưa mở được hộp thoại Chỉnh sửa bản nháp trong Studio.")
        dialog_video = self._draft_dialog_video_id(driver, dialog)
        if dialog_video and dialog_video != video_id:
            raise PublishingBrowserError("Hộp thoại bản nháp Studio không khớp đúng video; chưa bấm Lưu.")
        if visible(dialog, TITLE) is None or visible(dialog, DESCRIPTION) is None:
            self.controls._click_control(
                driver,
                lambda: visible(dialog, "[test-id='DETAILS']") or visible(dialog, "#step-badge-0"),
                timeout=30,
                message="Chưa mở được bước Chi tiết trong hộp thoại bản nháp Studio.",
            )
            wait_for(
                lambda: visible(dialog, TITLE) and visible(dialog, DESCRIPTION),
                timeout=30,
                message="Chưa tải được ô title/description trong hộp thoại bản nháp Studio.",
            )
        return dialog

    @staticmethod
    def _draft_step_tab(dialog, test_id):
        return visible(dialog, f"ytcp-stepper [test-id='{test_id}'], [role='tab'][test-id='{test_id}'], [test-id='{test_id}']")

    @classmethod
    def _draft_step_state(cls, dialog, test_id):
        tab = cls._draft_step_tab(dialog, test_id)
        if tab is None:
            return ""
        return str(tab.get_attribute("state") or "").strip().lower()

    @staticmethod
    def _active_draft_step(dialog):
        for tab in dialog.find_elements(By.CSS_SELECTOR, "ytcp-stepper [test-id], [role='tab'][test-id]"):
            if not tab.is_displayed():
                continue
            if tab.get_attribute("aria-selected") == "true" or tab.get_attribute("active") is not None:
                step_id = str(tab.get_attribute("test-id") or "").strip()
                if step_id:
                    return step_id
        for selector, step_id in (
            ("ytcp-video-visibility-select", "REVIEW"),
            ("ytcms-video-rights-management-settings", "RIGHTS_MANAGEMENT"),
            ("ytcp-uploads-monetization", "MONETIZATION"),
            ("ytcp-uploads-content-ratings, ytpp-self-certification-questionnaire", "CONTENT_RATINGS"),
            (TITLE, "DETAILS"),
        ):
            if visible(dialog, selector) is not None:
                return step_id
        return ""

    @staticmethod
    def _wait_draft_idle(dialog, timeout=15):
        wait_for(
            lambda: visible(dialog, "tp-yt-paper-progress") is None,
            timeout=timeout,
            message="Hộp thoại bản nháp Studio vẫn đang tải; chưa tiếp tục.",
        )

    def _click_draft_next(self, driver, dialog, previous_step):
        self.controls._click_control(
            driver,
            lambda: self.controls._button_control(dialog, "#next-button"),
            timeout=30,
            message="Studio chưa bật nút Tiếp trong hộp thoại bản nháp.",
        )
        wait_for(
            lambda: (
                (self._active_draft_step(dialog) not in {"", previous_step})
                or visible(dialog, "ytcp-video-visibility-select") is not None
            ),
            timeout=20,
            message="Studio chưa chuyển sang bước tiếp theo trong hộp thoại bản nháp.",
        )

    def _complete_rights_management(self, driver, dialog, reference):
        panel = wait_for(
            lambda: visible(dialog, "ytcms-video-rights-management-settings"),
            timeout=20,
            message="Chưa tải được phần Quản lý quyền trong hộp thoại bản nháp Studio.",
        )

        def current_policy_text():
            node = (
                visible(panel, "ytcms-policy-select.upload-policy-select .dropdown-trigger-text")
                or visible(panel, "ytcms-policy-select .dropdown-trigger-text")
            )
            return " ".join(field_text(driver, node).split()) if node is not None else ""

        if current_policy_text().casefold() != RIGHTS_POLICY_NAME.casefold():
            self.controls._click_control(
                driver,
                lambda: (
                    visible(panel, "ytcms-policy-select.upload-policy-select ytcp-dropdown-trigger")
                    or visible(panel, "ytcms-policy-select ytcp-dropdown-trigger")
                ),
                timeout=20,
                message="Chưa mở được danh sách chính sách tải lên trong Quản lý quyền.",
            )
            policy_dialog = wait_for(
                lambda: visible(driver, "tp-yt-paper-dialog[aria-label='policy-dialog']"),
                timeout=20,
                message="Chưa tải được hộp thoại chọn chính sách trong Quản lý quyền.",
            )
            filter_input = visible(policy_dialog, "input#policy-filter-input")
            if filter_input is not None:
                set_text(driver, filter_input, RIGHTS_POLICY_NAME, commit=None, force=True)

            def matching_policy_option():
                for item in policy_dialog.find_elements(By.CSS_SELECTOR, "tp-yt-paper-item[role='option'], tp-yt-paper-item"):
                    if not item.is_displayed():
                        continue
                    title_el = next(iter(item.find_elements(By.CSS_SELECTOR, ".title")), None)
                    label = " ".join((title_el.text if title_el is not None else item.text).split())
                    if label.casefold() == RIGHTS_POLICY_NAME.casefold():
                        return item
                return None

            option = wait_for(
                matching_policy_option,
                timeout=15,
                message=f"Không tìm thấy chính sách '{RIGHTS_POLICY_NAME}' trong Quản lý quyền.",
            )
            self.controls._click_control(
                driver,
                lambda option=option: option,
                selected=lambda el: el.get_attribute("aria-selected") == "true" or el.get_attribute("selected") is not None,
                timeout=15,
                message=f"Chưa chọn được chính sách '{RIGHTS_POLICY_NAME}' trong Quản lý quyền.",
            )
            self.controls._click_control(
                driver,
                lambda: self.controls._button_control(policy_dialog, "#apply-policy"),
                timeout=15,
                message="Chưa bấm được nút Áp dụng chính sách trong Quản lý quyền.",
            )
            wait_for(
                lambda: (
                    visible(driver, "tp-yt-paper-dialog[aria-label='policy-dialog']") is None
                    and current_policy_text().casefold() == RIGHTS_POLICY_NAME.casefold()
                ),
                timeout=20,
                message=f"Studio chưa áp dụng chính sách '{RIGHTS_POLICY_NAME}' trong Quản lý quyền.",
            )

        global_radio = (
            visible(panel, "ytcms-asset-ownership-territory #global-radio-button")
            or visible(panel, "ytcms-asset-ownership-territory tp-yt-paper-radio-button[name='GLOBAL']")
        )
        if global_radio is not None and global_radio.get_attribute("aria-checked") != "true":
            self.controls._click_control(
                driver,
                lambda: (
                    visible(panel, "ytcms-asset-ownership-territory #global-radio-button")
                    or visible(panel, "ytcms-asset-ownership-territory tp-yt-paper-radio-button[name='GLOBAL']")
                ),
                selected=lambda el: el.get_attribute("aria-checked") == "true",
                timeout=15,
                message="Chưa chọn được quyền sở hữu Toàn cầu trong Quản lý quyền.",
            )
            wait_for(
                lambda: (
                    (node := (
                        visible(panel, "ytcms-asset-ownership-territory #global-radio-button")
                        or visible(panel, "ytcms-asset-ownership-territory tp-yt-paper-radio-button[name='GLOBAL']")
                    )) is not None
                    and node.get_attribute("aria-checked") == "true"
                ),
                timeout=10,
                message="Studio chưa xác nhận quyền sở hữu Toàn cầu trong Quản lý quyền.",
            )

        song_field = visible(panel, "#metadata-music-video-song-input textarea")
        if song_field is not None and not field_text(driver, song_field).strip():
            set_text(driver, song_field, reference["title"])

        artist_editor = visible(panel, "ytcms-identified-people-editor")
        if artist_editor is not None:
            def has_artist_chip():
                return any(
                    chip.is_displayed()
                    for chip in artist_editor.find_elements(By.CSS_SELECTOR, "ytcp-chip")
                )

            def find_artist_dialog():
                return (
                    visible(driver, "tp-yt-paper-dialog[aria-labelledby='cms-identified-people-edit-dialog-title']")
                    or visible(driver, "ytcp-dialog[aria-labelledby='cms-identified-people-edit-dialog-title']")
                )

            if not has_artist_chip():
                artist_input = wait_for(
                    lambda: visible(artist_editor, "ytcp-chip-bar input#text-input, input#text-input"),
                    timeout=15,
                    message="Không tìm thấy ô nhập Nghệ sĩ trong Quản lý quyền.",
                )
                set_text(driver, artist_input, DEFAULT_RIGHTS_ARTIST, commit=Keys.ENTER, force=True)
                wait_for(
                    lambda: find_artist_dialog() is not None or has_artist_chip(),
                    timeout=15,
                    message="Studio không mở hộp thoại nghệ sĩ hoặc không thêm được nghệ sĩ.",
                )
                artist_dialog = find_artist_dialog()
                if artist_dialog is not None:
                    name_area = visible(artist_dialog, "#name-input textarea")
                    if name_area is not None and field_text(driver, name_area).strip() != DEFAULT_RIGHTS_ARTIST:
                        set_text(driver, name_area, DEFAULT_RIGHTS_ARTIST, commit=None, force=True)
                    self.controls._click_control(
                        driver,
                        lambda: self.controls._button_control(find_artist_dialog() or driver, "#save"),
                        timeout=15,
                        message="Chưa bấm được nút Lưu thông tin nghệ sĩ trong Quản lý quyền.",
                    )
                    wait_for(
                        lambda: find_artist_dialog() is None,
                        timeout=15,
                        message="Hộp thoại chỉnh sửa nghệ sĩ chưa đóng sau khi bấm Lưu.",
                    )
                wait_for(
                    has_artist_chip,
                    timeout=15,
                    message="Studio chưa lưu thẻ Nghệ sĩ trong Quản lý quyền.",
                )

        self._wait_draft_idle(dialog)

    def _ensure_audience_selected(self, driver, scope, *, on_progress=lambda step, message: None):
        host = visible(scope, "ytkc-made-for-kids-select")
        if host is None:
            for candidate in scope.find_elements(By.CSS_SELECTOR, "ytkc-made-for-kids-select"):
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                        candidate,
                    )
                except WebDriverException:
                    continue
                if candidate.is_displayed():
                    host = candidate
                    break
        if host is None:
            return False
        radios = [r for r in host.find_elements(By.CSS_SELECTOR, "tp-yt-paper-radio-button") if r.is_displayed()]
        if not radios:
            return False
        if any(r.get_attribute("aria-checked") == "true" for r in radios):
            return False
        on_progress("audience", "Đang chọn 'Không, nội dung này không dành cho trẻ em' trong mục Đối tượng người xem…")

        def locate_not_mfk():
            return visible(
                scope,
                "ytkc-made-for-kids-select tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']",
            )

        self.controls._click_control(
            driver,
            locate_not_mfk,
            selected=lambda el: el.get_attribute("aria-checked") == "true",
            timeout=15,
            message="Chưa chọn được 'Không, nội dung này không dành cho trẻ em' trong mục Đối tượng người xem.",
        )
        wait_for(
            lambda: (node := locate_not_mfk()) is not None and node.get_attribute("aria-checked") == "true",
            timeout=10,
            message="Studio chưa xác nhận lựa chọn 'Không, nội dung này không dành cho trẻ em'.",
        )
        return True

    def _complete_monetization(self, driver, dialog):
        panel = wait_for(
            lambda: visible(dialog, "ytcp-uploads-monetization"),
            timeout=20,
            message="Chưa tải được bước Kiếm tiền trong hộp thoại bản nháp Studio.",
        )
        self._wait_draft_idle(dialog)
        started = time.monotonic()
        wait_for(
            lambda: (
                visible(driver, "ytcp-video-monetization-edit-dialog") is not None
                or visible(panel, "ytcp-dropdown-trigger") is not None
                or visible(panel, "ytpp-ad-options-settings, ytpp-ad-breaks-settings") is not None
                or (
                    time.monotonic() - started >= self.MONETIZATION_CONTROLS_GRACE_SECONDS
                    and visible(dialog, "tp-yt-paper-progress") is None
                    and self.controls._button_control(dialog, "#next-button") is not None
                    and bool((panel.text or "").strip())
                )
            ),
            timeout=15,
            message="Chưa tải được điều khiển Kiếm tiền trong Studio.",
        )

        edit_dialog = visible(driver, "ytcp-video-monetization-edit-dialog")
        if edit_dialog is None:
            trigger = visible(panel, "ytcp-dropdown-trigger")
            trigger_enabled = trigger is not None and not self._is_control_disabled(trigger)
            ad_options_ready = visible(panel, "ytpp-ad-options-settings, ytpp-ad-breaks-settings") is not None
            next_ready = self.controls._button_control(dialog, "#next-button") is not None
            if trigger_enabled and (not ad_options_ready or not next_ready):
                self.controls._click_control(
                    driver,
                    lambda: visible(panel, "ytcp-dropdown-trigger"),
                    timeout=15,
                    message="Chưa mở được hộp thoại bật Kiếm tiền trong Studio.",
                )
                edit_dialog = wait_for(
                    lambda: visible(driver, "ytcp-video-monetization-edit-dialog"),
                    timeout=15,
                    message="Chưa tải được hộp thoại chọn Bật/Tắt kiếm tiền.",
                )

        if edit_dialog is not None:
            radio_on = wait_for(
                lambda: (
                    visible(edit_dialog, "tp-yt-paper-radio-button#radio-on")
                    or visible(edit_dialog, "tp-yt-paper-radio-button[name='ON']")
                ),
                timeout=15,
                message="Chưa tìm thấy tùy chọn Bật kiếm tiền.",
            )
            if radio_on.get_attribute("aria-checked") != "true":
                self.controls._click_control(
                    driver,
                    lambda: (
                        visible(edit_dialog, "tp-yt-paper-radio-button#radio-on")
                        or visible(edit_dialog, "tp-yt-paper-radio-button[name='ON']")
                    ),
                    selected=lambda el: el.get_attribute("aria-checked") == "true",
                    timeout=15,
                    message="Chưa chọn được Bật trong hộp thoại Kiếm tiền.",
                )
                wait_for(
                    lambda: (
                        (node := (
                            visible(edit_dialog, "tp-yt-paper-radio-button#radio-on")
                            or visible(edit_dialog, "tp-yt-paper-radio-button[name='ON']")
                        )) is not None
                        and node.get_attribute("aria-checked") == "true"
                    ),
                    timeout=10,
                    message="Studio chưa xác nhận chọn Bật kiếm tiền.",
                )
            self.controls._click_control(
                driver,
                lambda: self.controls._button_control(edit_dialog, "#save-button"),
                timeout=15,
                message="Chưa bấm được nút Xong khi bật Kiếm tiền.",
            )
            wait_for(
                lambda: visible(driver, "ytcp-video-monetization-edit-dialog") is None,
                timeout=15,
                message="Hộp thoại Kiếm tiền chưa đóng sau khi bấm Xong.",
            )

        self._wait_draft_idle(dialog)
        wait_for(
            lambda: (
                visible(panel, "ytpp-ad-options-settings, ytpp-ad-breaks-settings") is not None
                or self.controls._button_control(dialog, "#next-button") is not None
            ),
            timeout=15,
            message="Studio chưa sẵn sàng chuyển tiếp sau khi bật Kiếm tiền.",
        )

    def _complete_content_ratings(self, driver, dialog):
        if self._draft_step_state(dialog, "CONTENT_RATINGS") == "completed":
            return
        panel = wait_for(
            lambda: visible(dialog, "ytcp-uploads-content-ratings, ytpp-self-certification-questionnaire"),
            timeout=20,
            message="Chưa tải được bước Mức độ phù hợp với quảng cáo trong Studio.",
        )

        def find_none_checkbox():
            direct = visible(panel, "ytcp-checkbox-lit.all-none-checkbox, ytcp-checkbox-lit#all-none-checkbox")
            if direct is not None:
                return direct
            outside_question = driver.execute_script("""
                const panel = arguments[0];
                for (const box of panel.querySelectorAll('ytcp-checkbox-lit')) {
                    if (!box.getClientRects().length || getComputedStyle(box).visibility === 'hidden') continue;
                    if (!box.closest('ytpp-self-certification-question')) return box;
                }
                return null;
            """, panel)
            if outside_question is not None:
                return outside_question
            for box in panel.find_elements(By.CSS_SELECTOR, "ytcp-checkbox-lit"):
                if not box.is_displayed():
                    continue
                if re.search(r"none of the above|không có nội dung nào ở trên|không có mục nào ở trên", box.text or "", re.I):
                    return box
            return None

        def checkbox_checked(host):
            role = next(iter(host.find_elements(By.CSS_SELECTOR, "[role='checkbox']")), None)
            target = role or host
            return target.get_attribute("aria-checked") == "true" or host.get_attribute("checked") is not None

        checkbox = wait_for(
            find_none_checkbox,
            timeout=20,
            message="Không tìm thấy ô 'Không có nội dung nào ở trên' trong bước Đánh giá quảng cáo.",
        )
        if not checkbox_checked(checkbox):
            self.controls._click_control(
                driver,
                find_none_checkbox,
                selected=checkbox_checked,
                timeout=15,
                message="Chưa tích được 'Không có nội dung nào ở trên' trong bước Đánh giá quảng cáo.",
            )
            wait_for(
                lambda: (box := find_none_checkbox()) is not None and checkbox_checked(box),
                timeout=10,
                message="Studio chưa xác nhận tích 'Không có nội dung nào ở trên'.",
            )

        def find_submit_button():
            explicit = self.controls._button_control(panel, "#submit-questionnaire-button")
            if explicit is not None:
                return explicit
            return driver.execute_script("""
                const panel = arguments[0];
                const re = /submit\\s*rating|gửi\\s*đánh\\s*giá|\\bsubmit\\b|^gửi\\b/i;
                for (const host of panel.querySelectorAll('ytcp-button')) {
                    if (host.closest('ytcp-banner')) continue;
                    if (host.getAttribute('aria-disabled') === 'true') continue;
                    const btn = host.querySelector('button');
                    if (!btn || btn.disabled || btn.getAttribute('aria-disabled') === 'true') continue;
                    if (!btn.getClientRects().length || getComputedStyle(btn).visibility === 'hidden') continue;
                    const label = ((btn.innerText || '') + ' ' + (btn.getAttribute('aria-label') || '')).trim();
                    if (re.test(label)) return btn;
                }
                return null;
            """, panel)

        submit_btn = wait_for(
            find_submit_button,
            timeout=15,
            message="Chưa tìm thấy nút Gửi đánh giá trong bước Mức độ phù hợp với quảng cáo.",
        )
        if submit_btn is not None:
            self.controls._click_control(
                driver,
                find_submit_button,
                timeout=15,
                message="Chưa bấm được nút Gửi đánh giá quảng cáo.",
            )
            wait_for(
                lambda: (
                    self._draft_step_state(dialog, "CONTENT_RATINGS") == "completed"
                    or (find_submit_button() is None and self.controls._button_control(dialog, "#next-button") is not None)
                ),
                timeout=30,
                message="Studio chưa xác nhận Gửi đánh giá mức độ phù hợp với quảng cáo.",
            )

        self._wait_draft_idle(dialog)

    def _open_review_step(self, driver, dialog):
        self.controls._click_control(
            driver,
            lambda: visible(dialog, "[test-id='REVIEW']") or visible(dialog, "#step-badge-3"),
            timeout=30,
            message="Chưa mở được bước Chế độ hiển thị trong hộp thoại bản nháp Studio.",
        )

    def _advance_draft_to_review(self, driver, dialog, *, reference, on_progress):
        handled_steps = set()

        def next_unhandled_pre_review():
            for step_id in PRE_REVIEW_DRAFT_STEPS:
                if self._draft_step_tab(dialog, step_id) is None:
                    continue
                if step_id not in handled_steps and self._draft_step_state(dialog, step_id) != "completed":
                    return step_id
            return None

        for _ in range(12):
            check_stopped()
            step = self._active_draft_step(dialog)
            if step == "REVIEW" and visible(dialog, "ytcp-video-visibility-select") is not None:
                pending = next_unhandled_pre_review()
                if pending is None:
                    return
                self.controls._click_control(
                    driver,
                    lambda pending=pending: self._draft_step_tab(dialog, pending),
                    timeout=15,
                    message=f"Chưa chuyển được tới bước {pending} trong hộp thoại bản nháp Studio.",
                )
                wait_for(
                    lambda pending=pending: self._active_draft_step(dialog) == pending,
                    timeout=15,
                    message=f"Studio chưa mở bước {pending}.",
                )
                continue

            if step == "RIGHTS_MANAGEMENT":
                on_progress("rights_management", "Đang thiết lập Quản lý quyền (chính sách, quyền sở hữu, nghệ sĩ)…")
                self._complete_rights_management(driver, dialog, reference)
                handled_steps.add("RIGHTS_MANAGEMENT")
                self._click_draft_next(driver, dialog, "RIGHTS_MANAGEMENT")
            elif step == "MONETIZATION":
                on_progress("monetization", "Đang bật Kiếm tiền trong hộp thoại bản nháp Studio…")
                self._complete_monetization(driver, dialog)
                handled_steps.add("MONETIZATION")
                self._click_draft_next(driver, dialog, "MONETIZATION")
            elif step == "CONTENT_RATINGS":
                on_progress("content_ratings", "Đang xác nhận Mức độ phù hợp với quảng cáo…")
                self._complete_content_ratings(driver, dialog)
                handled_steps.add("CONTENT_RATINGS")
                self._click_draft_next(driver, dialog, "CONTENT_RATINGS")
            elif step == "DETAILS":
                has_mandatory_pre_review = any(
                    self._draft_step_tab(dialog, step_id) is not None
                    for step_id in PRE_REVIEW_DRAFT_STEPS
                )
                if has_mandatory_pre_review:
                    self._click_draft_next(driver, dialog, "DETAILS")
                else:
                    self._open_review_step(driver, dialog)
                    return
            else:
                if self.controls._button_control(dialog, "#next-button") is not None:
                    self._click_draft_next(driver, dialog, step)
                else:
                    self._open_review_step(driver, dialog)
                    return

        if visible(dialog, "ytcp-video-visibility-select") is None:
            raise PublishingBrowserError("Chưa chuyển được tới bước Chế độ hiển thị trong hộp thoại bản nháp Studio.")

    def _fill_schedule(self, driver, select, publish_at, *, original=None):
        current_state = original if original is not None else self._state(driver, select)
        if not current_state.get("scheduled"):
            self.controls._click_control(driver, lambda:visible(select, "#second-container-expand-button"),
                                         message="Chưa chọn được mục Lên lịch công khai.")
            wait_for(lambda:self._state(driver, select).get("scheduled") and visible(select, "ytcp-datetime-picker input"),
                     timeout=20, message="Studio chưa mở các ô ngày/giờ Lên lịch.")
        self._local_timezone(driver, select)
        target = datetime.fromtimestamp(publish_at, VIETNAM_TIMEZONE)
        state = self._state(driver, select)
        expected_date = {"year":target.year,"month":target.month-1,"day":target.day}
        if state.get("date") != expected_date:
            self.controls._click_control(driver, lambda:visible(select, "#datepicker-trigger ytcp-dropdown-trigger"),
                                         message="Chưa mở được ô ngày đăng.")
            field = wait_for(lambda:visible(driver, "ytcp-date-picker input"), timeout=15, message="Chưa tải được ô nhập ngày đăng.")
            date_text = driver.execute_script(r"""
                const [field,target,current]=arguments, baseLocale=document.documentElement.lang||'en-US';
                const clean=v=>String(v||'').replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069\s]/g,'');
                const value=clean(field.value), date=new Date(Date.UTC(current.year,current.month,current.day,12));
                const locales=[baseLocale, baseLocale+'-u-nu-latn', baseLocale+'-u-nu-arab', 'en-US'];
                for(const locale of locales)for(const month of ['numeric','2-digit','short','long'])for(const day of ['numeric','2-digit']){
                    try{
                        const format=new Intl.DateTimeFormat(locale,{year:'numeric',month,day,timeZone:'UTC'});
                        if(clean(format.format(date))===value)
                            return format.format(new Date(Date.UTC(target.year,target.month,target.day,12)));
                    }catch{}
                }
                return new Intl.DateTimeFormat(baseLocale,{year:'numeric',month:'short',day:'numeric',timeZone:'UTC'})
                    .format(new Date(Date.UTC(target.year,target.month,target.day,12)));
            """, field, expected_date, state["date"])
            set_text(driver, field, date_text, commit=Keys.ENTER, force=True)
            wait_for(lambda:self._state(driver, select).get("date")==expected_date, timeout=10,
                     message="Studio chưa nhận đúng ngày đăng; chưa bấm Lưu.")
            wait_for(lambda:visible(driver, "ytcp-date-picker input") is None, timeout=10,
                     message="Ô chọn ngày chưa đóng sau khi nhập; chưa bấm Lưu.")
        expected_seconds = target.hour * 3600 + target.minute * 60
        state = self._state(driver, select)
        if state.get("seconds") != expected_seconds:
            field = wait_for(lambda:visible(select, "ytcp-datetime-picker #time-of-day-container input"),
                             timeout=10, message="Chưa tìm thấy ô giờ đăng.")
            current_time = field_text(driver, field)
            clean_time = _normalize_locale_text(current_time)
            if re.search(r"\b[AP]M\b", clean_time, re.I):
                text = target.strftime("%I:%M %p").lstrip("0")
            elif any(marker in clean_time for marker in ("ص", "م")):
                suffix = "ص" if target.hour < 12 else "م"
                text = f"{target.strftime('%I:%M').lstrip('0')} {suffix}"
            elif re.search(r"\b(?:SA|CH)\b", clean_time, re.I):
                suffix = "SA" if target.hour < 12 else "CH"
                text = f"{target.strftime('%I:%M').lstrip('0')} {suffix}"
            else:
                text = target.strftime("%H:%M")
            if re.search(r"[\u0660-\u0669]", str(current_time)):
                text = text.translate(_ASCII_TO_ARABIC_DIGITS)
            set_text(driver, field, text, commit=(Keys.ENTER, Keys.TAB), force=True)
            wait_for(lambda:self._state(driver, select).get("seconds")==expected_seconds, timeout=10,
                     message="Studio chưa nhận đúng giờ đăng; chưa bấm Lưu.")
        state = self._state(driver, select)
        if not state.get("scheduled") or state.get("timestamp") != int(publish_at) or state.get("offset") != 420:
            raise PublishingBrowserError("Ngày/giờ công khai Studio nhận còn khác lịch UTC+7 đã chọn; chưa bấm Lưu.")

    def _stage_schedule(self, driver, publish_at):
        select = self._visibility(driver)
        original = self._state(driver, select)
        was_scheduled = self._scheduled_badge(driver)
        if was_scheduled:
            if original.get("timestamp") != int(publish_at):
                raise PublishingBrowserError("Studio đang có lịch khác ngày/giờ đã chọn; giữ nguyên lịch hiện tại.")
        self._fill_schedule(driver, select, publish_at, original=original)
        popup = visible(driver, "ytcp-video-visibility-edit-popup")
        if self.controls._button_control(popup, "#save-button") is not None:
            self.controls._click_control(driver, lambda:self.controls._button_control(popup, "#save-button"),
                                         message="Chưa áp dụng được lịch vào trang chi tiết video.")
            wait_for(lambda:visible(driver, "ytcp-video-visibility-edit-popup ytcp-video-visibility-select") is None,
                     timeout=15, message="Popup lịch chưa đóng sau khi áp dụng.")
        else:
            self._close_visibility(driver)
        return not was_scheduled or original.get("timestamp") != publish_at

    def _stage_draft_schedule(self, driver, dialog, publish_at, *, reference, on_progress=lambda step, message: None):
        self._advance_draft_to_review(driver, dialog, reference=reference, on_progress=on_progress)
        select = wait_for(
            lambda: visible(dialog, "ytcp-video-visibility-select"),
            timeout=30,
            message="Chưa tải được phần Lên lịch trong hộp thoại bản nháp Studio.",
        )
        self._fill_schedule(driver, select, publish_at)
        return True

    @staticmethod
    def _scheduled_badge(driver):
        return bool(driver.execute_script("return document.querySelector('ytcp-video-metadata-visibility #container')?.classList.contains('schedule-icon') || false;"))

    def _read_saved(self, driver, reference, publish_at, playlist_id):
        same = VideoPublishingModule._same_text
        if not same(field_text(driver, visible(driver, TITLE)), reference["title"]) or not same(field_text(driver, visible(driver, DESCRIPTION)), reference["description"]):
            return "title/description"
        if not self._scheduled_badge(driver):
            return "trạng thái Đã lên lịch trong Studio"
        select = self._visibility(driver)
        state = self._state(driver, select)
        self._close_visibility(driver)
        if not state.get("scheduled") or state.get("timestamp") != int(publish_at):
            return "ngày/giờ công khai"
        self.controls._playlist_dialog(driver)
        checkbox = self.controls._playlist_checkbox(driver, playlist_id)
        checked = checkbox is not None and checkbox.get_attribute("aria-checked") == "true"
        self.controls._playlist_done(driver)
        return "" if checked else "danh sách phát"

    def _inspect_schedule_in_driver(self, driver, channel_id, video_id):
        """Read persisted visibility/date in an already authenticated Studio driver."""
        self._open(driver, video_id)
        mode = self._wait_editor_mode(driver)
        if mode == "draft":
            return {"source":"studio_ui","channel_id":channel_id,"video_id":video_id,"scheduled":False,"publish_at":None}
        proof = {"source":"studio_ui","channel_id":channel_id,"video_id":video_id,
                 "scheduled":self._scheduled_badge(driver),"publish_at":None}
        if proof["scheduled"]:
            select = self._visibility(driver)
            state = self._state(driver, select)
            self._close_visibility(driver)
            if not state.get("scheduled") or state.get("timestamp") is None:
                raise PublishingBrowserError("Studio có lịch nhưng chưa đọc được ngày/giờ của video " + video_id + ".")
            proof["publish_at"] = state["timestamp"]
        return proof

    def inspect_schedule(self, channel_id, video_id):
        """Read persisted visibility/date without selecting or saving anything."""
        channel = get_channels_info(channel_id)
        if not channel or channel.id != channel_id:
            raise PublishingBrowserError("Chưa có phiên kênh để đọc lại lịch trong Studio.")
        driver = _new_driver()
        try:
            driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId":"Asia/Bangkok"})
            inject_cookies_via_cdp(driver, channel.cookies)
            return self._inspect_schedule_in_driver(driver, channel_id, video_id)
        finally:
            close_driver(driver)

    def inspect_schedules(self, channel_id, video_ids, *, on_progress=lambda index, total, video_id: None):
        """Read persisted visibility/date across multiple videos in one shared Chrome session."""
        unique_ids = []
        seen = set()
        for raw_id in video_ids:
            vid = str(raw_id or "").strip()
            if vid and vid not in seen:
                seen.add(vid)
                unique_ids.append(vid)
        if not unique_ids:
            return {}
        channel = get_channels_info(channel_id)
        if not channel or channel.id != channel_id:
            raise PublishingBrowserError("Chưa có phiên kênh để đọc lại lịch trong Studio.")
        results = {}
        driver = _new_driver()
        try:
            driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId":"Asia/Bangkok"})
            inject_cookies_via_cdp(driver, channel.cookies)
            total = len(unique_ids)
            for index, video_id in enumerate(unique_ids, 1):
                check_stopped()
                on_progress(index, total, video_id)
                try:
                    results[video_id] = self._inspect_schedule_in_driver(driver, channel_id, video_id)
                except TaskStopped:
                    raise
                except Exception as exc:
                    results[video_id] = exc
                    if isinstance(exc, WebDriverException):
                        try:
                            alive = bool(driver.window_handles)
                        except WebDriverException:
                            alive = False
                        if not alive:
                            for remaining_id in unique_ids[index:]:
                                results[remaining_id] = exc
                            break
            return results
        finally:
            close_driver(driver)

    def publish(self, channel_id, video_id, path, reference, publish_at, *, expected_title, expected_description,
                thumbnail_uploaded=False, on_saved=lambda:None, on_submit=lambda receipt:None,
                on_progress=lambda step,message:None, before_save=lambda:None):
        if publish_at <= datetime.now(timezone.utc).timestamp() or int(publish_at) % 60:
            raise PublishingBrowserError("Ngày/giờ đăng đã qua hoặc không đúng phút; chọn lại lịch trước khi lưu.")
        channel = get_channels_info(channel_id)
        if not channel or channel.id != channel_id:
            raise PublishingBrowserError("Chưa có phiên đăng nhập đúng kênh để cập nhật video.")
        verify = self.controls.verify_saved or ThumbnailReadback(channel_id, video_id, path)
        saved_thumbnail = bool(thumbnail_uploaded) or verify()
        driver = _new_driver(network_events=True)
        try:
            driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId":"Asia/Bangkok"})
            inject_cookies_via_cdp(driver, channel.cookies)
            self._open(driver, video_id)
            mode = self._wait_editor_mode(driver)
            scope = self._open_draft_dialog(driver, video_id, channel_id=channel_id) if mode == "draft" else driver
            title, description = visible(scope, TITLE), visible(scope, DESCRIPTION)
            validate_metadata(field_text(driver, title), field_text(driver, description), reference, expected_title, expected_description)
            pre_observer = NativeSave(driver, channel_id, video_id, verify)
            driver.get_log("performance")
            changed = not saved_thumbnail
            if not saved_thumbnail:
                on_progress("upload_thumbnail", "Đang đưa thumbnail vào trang Studio; sẽ lưu cùng metadata và lịch…")
                field = wait_for(lambda:next(iter(scope.find_elements(By.CSS_SELECTOR,"ytcp-thumbnail-editor input[type=file],ytcp-thumbnail-uploader input[type=file]")),None),
                                 timeout=30, message="Chưa tìm được ô tải thumbnail trong Studio.")
                field.send_keys(str(Path(path).resolve()))
            on_progress("copy_metadata", "Đang nhập title và description nguyên văn vào cùng trang Studio…")
            for selector, text in ((TITLE, reference["title"]), (DESCRIPTION, reference["description"])):
                field = visible(scope, selector)
                if not VideoPublishingModule._same_text(field_text(driver, field), text):
                    set_text(driver, field, text)
                    changed = True
            on_progress("assign_playlist", "Đang chọn playlist đầu tiên và bấm Xong; chưa bấm Lưu trang…")
            playlist, playlist_changed = self.controls._stage_first_playlist(driver, scope=scope)
            changed = changed or playlist_changed
            changed = self._ensure_audience_selected(driver, scope, on_progress=on_progress) or changed
            on_progress("schedule_video", "Đang chọn Lên lịch công khai và nhập ngày/giờ UTC+7…")
            if mode == "draft":
                changed = self._stage_draft_schedule(driver, scope, publish_at, reference=reference, on_progress=on_progress) or changed
            else:
                changed = self._stage_schedule(driver, publish_at) or changed
            if changed:
                pre_observer()
                current = before_save()
                if current is not None:
                    validate_metadata(current.title, current.description, reference, expected_title, expected_description)
                check_stopped()
                on_progress("final_save", "Thumbnail, title/description, playlist và lịch đã sẵn sàng. Đang bấm Lưu cuối…")
                observer = NativeSave(driver, channel_id, video_id, verify)
                driver.get_log("performance")
                if mode == "draft":
                    save_locate = lambda:self.controls._button_control(scope, "#done-button")
                    save_message = "Studio chưa cho bấm Lên lịch bản nháp; kiểm tra lỗi ở các bước Chi tiết/Chế độ hiển thị."
                else:
                    save_locate = lambda:self.controls._save_button(driver)
                    save_message = "Studio chưa cho bấm Lưu cuối; kiểm tra lỗi ở các ô video."
                self.controls._click_control(driver, save_locate, timeout=90, message=save_message)
                on_submit({"video_id":video_id,"channel_id":channel_id,"publish_at":int(publish_at),"save_clicked":True})
                try:
                    wait_for(observer, timeout=45, message="Chưa nhận phản hồi Lưu cuối.")
                except PublishingBrowserError as exc:
                    if str(exc) != "Chưa nhận phản hồi Lưu cuối.":
                        raise
                if not saved_thumbnail and verify():
                    on_saved()
                    saved_thumbnail = True
            on_progress("verify_saved", "Đang mở lại video để kiểm tra thumbnail, metadata, playlist và lịch đã lưu…")
            # Keep the saving tab alive if its response was lost; a verification
            # tab must not cancel an in-flight final Save by refreshing it.
            driver.switch_to.new_window("tab")
            remaining = "kết quả đã lưu"
            for attempt in range(4):
                self._open(driver, video_id)
                remaining = self._read_saved(driver, reference, publish_at, playlist["playlist_id"])
                if not saved_thumbnail and verify():
                    on_saved()
                    saved_thumbnail = True
                if not remaining and saved_thumbnail:
                    return {**playlist,"verified":True,"video_id":video_id,"channel_id":channel_id,
                            "publish_at":int(publish_at),"thumbnail_asset_id":getattr(verify,"confirmed_asset_id","")}
                if attempt < 3:
                    wait_interruptibly((2, 4, 8)[attempt])
            raise PublishingBrowserError("Đã bấm Lưu cuối nhưng Studio đọc lại còn khác " + (remaining or "thumbnail") + ". Ảnh và tiến độ được giữ; chạy tiếp sẽ mở lại video để kiểm tra trước khi lưu thêm.")
        finally:
            close_driver(driver)
