"""Stage an existing video's edits in Studio and activate its final Save once."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from src.cookie_utils import inject_cookies_via_cdp
from src.module.video_publishing_module import VideoPublishingModule
from src.publishing_browser import PublishingBrowserError, _new_driver, close_driver, wait_for
from src.publishing_thumbnails import ThumbnailReadback
from src.task_runtime import check_stopped, wait_interruptibly
from src.utils import get_channels_info
from src.video_scan_dates import VIETNAM_TIMEZONE

TITLE = "#title-textarea [contenteditable='true'], #title-textarea textarea"
DESCRIPTION = "#description-textarea [contenteditable='true'], #description-textarea textarea"


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
    def __init__(self, controls):
        self.controls = controls

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
            self.controls._click_control(driver, lambda: visible(driver, "ytcp-video-metadata-visibility #select-button"),
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
        match = re.search(r"(?:GMT|UTC)\s*([+-])(\d{1,2}):?(\d{2})\b", state.get("timezoneNote") or "", re.I)
        if state.get("timezoneIndex") == 0 and match and state.get("date") is not None and state.get("seconds") is not None:
            offset = (int(match[2]) * 60 + int(match[3])) * (1 if match[1] == "+" else -1)
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
                if option.is_displayed() and re.search(r"GMT\+0?7:?00", option.text):
                    return option
            return None
        self.controls._click_control(driver, local_option, message="Không tìm thấy múi giờ địa phương UTC+7; chưa bấm Lưu.")
        wait_for(lambda:self._state(driver, select).get("offset")==420 and self._state(driver, select).get("timezoneIndex")==0,
                 timeout=10, message="Studio chưa nhận múi giờ UTC+7.")

    def _draft_edit_button(self, driver):
        return self.controls._button_control(driver, "ytcp-banner.entity-banner #action-1")

    def _editor_mode(self, driver):
        if visible(driver, "ytcp-video-metadata-visibility #container") is not None:
            return "standard"
        if self._draft_edit_button(driver) is None:
            return None
        is_draft = driver.execute_script("""
            if (document.querySelector('ytcp-video-metadata-visibility #container')) return false;
            const editor = document.querySelector('ytcp-video-metadata-editor');
            const draft = String(editor?.video?.draftStatus ?? editor?.isDraft ?? '').toUpperCase();
            if (draft && !/UNSPECIFIED|NOT_DRAFT/.test(draft)) return true;
            return !!document.querySelector('ytcp-video-metadata-editor-sidepanel ytcp-video-info');
        """)
        return "draft" if is_draft else None

    def _wait_editor_mode(self, driver, timeout=30):
        return wait_for(
            lambda: self._editor_mode(driver),
            timeout=timeout,
            message="Chưa tải được trạng thái hiển thị video trong Studio.",
        )

    def _open_draft_dialog(self, driver, video_id):
        self.controls._click_control(
            driver,
            lambda: self._draft_edit_button(driver),
            timeout=30,
            message="Chưa mở được hộp thoại Chỉnh sửa bản nháp trong Studio.",
        )
        dialog = wait_for(
            lambda: visible(driver, "ytcp-uploads-dialog"),
            timeout=30,
            message="Chưa tải được hộp thoại Chỉnh sửa bản nháp trong Studio.",
        )
        dialog_video = dialog.get_attribute("video-id")
        if dialog_video and dialog_video != video_id:
            raise PublishingBrowserError("Hộp thoại bản nháp Studio không khớp đúng video; chưa bấm Lưu.")
        if visible(dialog, TITLE) is None or visible(dialog, DESCRIPTION) is None:
            self.controls._click_control(
                driver,
                lambda: visible(dialog, "#step-badge-0, [test-id='DETAILS']"),
                timeout=30,
                message="Chưa mở được bước Chi tiết trong hộp thoại bản nháp Studio.",
            )
            wait_for(
                lambda: visible(dialog, TITLE) and visible(dialog, DESCRIPTION),
                timeout=30,
                message="Chưa tải được ô title/description trong hộp thoại bản nháp Studio.",
            )
        return dialog

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
                const [field,target,current]=arguments, locale=document.documentElement.lang||'en-US';
                const value=field.value.replace(/\s/g,''), date=new Date(Date.UTC(current.year,current.month,current.day,12));
                for(const month of ['numeric','2-digit','short','long'])for(const day of ['numeric','2-digit']){
                    const format=new Intl.DateTimeFormat(locale,{year:'numeric',month,day,timeZone:'UTC'});
                    if(format.format(date).replace(/\s/g,'')===value)
                        return format.format(new Date(Date.UTC(target.year,target.month,target.day,12)));
                }
                return new Intl.DateTimeFormat(locale,{year:'numeric',month:'short',day:'numeric',timeZone:'UTC'})
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
            text = target.strftime("%I:%M %p").lstrip("0") if re.search(r"\b[AP]M\b", current_time, re.I) else target.strftime("%H:%M")
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

    def _stage_draft_schedule(self, driver, dialog, publish_at):
        self.controls._click_control(
            driver,
            lambda: visible(dialog, "#step-badge-3, [test-id='REVIEW']"),
            timeout=30,
            message="Chưa mở được bước Chế độ hiển thị trong hộp thoại bản nháp Studio.",
        )
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
            scope = self._open_draft_dialog(driver, video_id) if mode == "draft" else driver
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
            on_progress("schedule_video", "Đang chọn Lên lịch công khai và nhập ngày/giờ UTC+7…")
            if mode == "draft":
                changed = self._stage_draft_schedule(driver, scope, publish_at) or changed
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
