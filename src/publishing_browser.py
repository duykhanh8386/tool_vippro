"""Browser adapters for YouTube references, ChatGPT images and Studio thumbnails.

ChatGPT uses its visible UI and a dedicated saved Chrome profile. Manual
cookies are imported before navigation; no private conversation API is used.
Reference: https://www.selenium.dev/documentation/webdriver/interactions/cookies/
"""
from __future__ import annotations

import base64
import atexit
import json
import hashlib
import re
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import quote, urlparse

from selenium.common.exceptions import (
    ElementClickInterceptedException, ElementNotInteractableException,
    StaleElementReferenceException, WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from src.cookie_utils import inject_cookies_via_cdp
from src.paths import get_data_dir
from src.publishing_thumbnails import ThumbnailReadback
from src.task_runtime import TaskStopped, check_stopped, run_owned_process, unregister_driver, wait_interruptibly
from src.utils import create_driver, get_channels_info
from src.video_publishing import (
    REFERENCE_SELECTION_VERSION, parse_chatgpt_cookies, positive_seconds,
    reference_search_query, reference_video_id,
)


class PublishingBrowserError(ValueError):
    pass


class ChatGPTSessionNeedsAction(PublishingBrowserError):
    """End the batch when this browser session cannot be restored in time."""

    def __init__(self, message, *, reason="session"):
        super().__init__(message)
        self.reason = reason


def wait_for(callback, timeout=60, message="Trang chưa sẵn sàng; kiểm tra Chrome và thử lại."):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        check_stopped()
        try:
            result = callback()
            if result:
                return result
        except StaleElementReferenceException:
            pass
        wait_interruptibly(0.5)
    raise PublishingBrowserError(message)


def close_driver(driver):
    if driver is not None:
        try:
            driver.quit()
        except WebDriverException:
            pass
        finally:
            unregister_driver(driver)


def _new_driver(*, network_events=False, profile_dir=None):
    options = {"enable_performance_log": network_events}
    if profile_dir is not None:
        options["user_data_dir"] = profile_dir
    driver = create_driver(**options)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)
    return driver


def video_search_candidates(data):
    """Read ordinary search results in display order; exclude ads and Shorts."""
    if isinstance(data, dict):
        if "videoRenderer" in data:
            renderer = data["videoRenderer"]
            identifier = renderer.get("videoId", "")
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", identifier):
                yield renderer
            return
        for key, child in data.items():
            if key not in {"adSlotRenderer", "adPlacements", "promotedSparklesWebRenderer", "reelShelfRenderer", "shortsLockupViewModel"}:
                yield from video_search_candidates(child)
    elif isinstance(data, list):
        for child in data:
            yield from video_search_candidates(child)


def video_search_results(data):
    for renderer in video_search_candidates(data):
        yield renderer["videoId"]


def search_result_duration(renderer):
    seconds = positive_seconds(renderer.get("lengthSeconds"))
    if seconds is not None:
        return seconds
    text = renderer.get("lengthText") or {}
    if isinstance(text, dict):
        text = text.get("simpleText") or "".join(item.get("text", "") for item in text.get("runs", []))
    if not re.fullmatch(r"\d+(?::[0-5]\d){1,2}", str(text).strip()):
        return None
    seconds = 0
    for component in str(text).strip().split(":"):
        seconds = seconds * 60 + int(component)
    return positive_seconds(seconds)


def loaded_search_results(driver):
    """Wait for actual search rows, not just YouTube's early response object."""
    data = driver.execute_script("return window.ytInitialData")
    candidates = list(video_search_candidates(data))
    if candidates:
        return {"candidates": candidates}
    # ytInitialData can exist before results arrive. Also read rendered rows
    # when the visible UI is available but the initial response is incomplete.
    page = driver.execute_script("""
        const videos = [];
        for (const row of document.querySelectorAll('ytd-search ytd-video-renderer')) {
            if (row.closest('ytd-ad-slot-renderer, ytd-in-feed-ad-layout-renderer, ytd-promoted-sparkles-web-renderer, ytd-reel-shelf-renderer')) continue;
            const anchor = row.querySelector('a#video-title[href], a#thumbnail[href]');
            if (!anchor) continue;
            const url = new URL(anchor.href, location.href);
            if (url.origin !== location.origin || url.pathname !== '/watch') continue;
            const videoId = url.searchParams.get('v');
            if (!/^[A-Za-z0-9_-]{11}$/.test(videoId || '')) continue;
            const badge = row.querySelector('ytd-thumbnail-overlay-time-status-renderer');
            videos.push({videoId, lengthText: {simpleText: badge?.textContent?.trim() || ''}});
        }
        const empty = Array.from(document.querySelectorAll('ytd-search ytd-message-renderer'))
            .some(node => node.getClientRects().length && node.textContent.trim());
        const blocked = location.hostname === 'consent.youtube.com' || location.pathname.startsWith('/sorry')
            || Array.from(document.querySelectorAll('form[action*="consent.youtube.com"], iframe[src*="recaptcha"]'))
                .some(node => node.getClientRects().length && getComputedStyle(node).visibility !== 'hidden');
        return {candidates: videos, empty, blocked};
    """)
    if not isinstance(page, dict):
        return None
    if page.get("blocked"):
        raise PublishingBrowserError("YouTube đang yêu cầu đồng ý cookie hoặc xác minh trong cửa sổ tìm kiếm; chưa đọc được kết quả tham chiếu.")
    rows = page.get("candidates")
    if isinstance(rows, list):
        rows = [row for row in rows if isinstance(row, dict) and re.fullmatch(r"[A-Za-z0-9_-]{11}", str(row.get("videoId", "")))]
        if rows:
            return {"candidates": rows}
    return {"candidates": []} if page.get("empty") else None


class YouTubeReferenceBrowser:
    def __init__(self):
        self.driver = None

    def _browser(self):
        if self.driver is None:
            self.driver = _new_driver()
        return self.driver

    def resolve_channels(self, text):
        identifiers = []
        for value in re.split(r"[\s,;]+", text.strip()):
            if not value:
                continue
            if re.fullmatch(r"UC[A-Za-z0-9_-]{22}", value):
                identifiers.append(value)
                continue
            url = urlparse(value if "://" in value else "https://" + value)
            if url.scheme not in {"http", "https"} or url.hostname not in {"youtube.com", "www.youtube.com", "m.youtube.com", "studio.youtube.com"}:
                raise PublishingBrowserError("Link kênh phải thuộc youtube.com.")
            match = re.match(r"/channel/(UC[A-Za-z0-9_-]{22})(?:/|$)", url.path)
            if match:
                identifiers.append(match[1])
                continue
            if not re.match(r"/(?:@[^/]+|c/[^/]+|user/[^/]+)(?:/|$)", url.path):
                raise PublishingBrowserError("Nhập link kênh /channel/UC… hoặc /@tenkenh; link video dùng ô Video ID.")
            driver = self._browser()
            driver.get("https://www.youtube.com" + url.path)
            identifier = wait_for(lambda: driver.execute_script(
                "return window.ytInitialData?.metadata?.channelMetadataRenderer?.externalId || document.querySelector('meta[itemprop=channelId]')?.content"
            ), message="Không đọc được Channel ID từ link kênh.")
            if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", str(identifier)):
                raise PublishingBrowserError("Channel ID trả về không hợp lệ.")
            identifiers.append(identifier)
        return list(dict.fromkeys(identifiers))

    def _read_reference(self, identifier, query):
        driver = self._browser()
        driver.get("https://www.youtube.com/watch?v=" + identifier)
        player = wait_for(lambda: driver.execute_script("return window.ytInitialPlayerResponse"),
                          message="Không đọc được title/description của video tham chiếu.")
        data = player.get("videoDetails") or {}
        if data.get("videoId") != identifier:
            raise PublishingBrowserError("Không đọc được đúng video tham chiếu; video có thể không còn khả dụng.")
        title, description = data.get("title"), data.get("shortDescription")
        thumbnails = data.get("thumbnail", {}).get("thumbnails") or []
        if not isinstance(title, str) or not title or not isinstance(description, str) or not thumbnails:
            raise PublishingBrowserError("Video tham chiếu thiếu title, description hoặc thumbnail.")
        if len(title.encode("utf-16-le")) > 200 or len(description.encode("utf-16-le")) > 10000:
            raise PublishingBrowserError("Metadata nguồn vượt giới hạn YouTube; không thể chép nguyên văn.")
        return {"video_id": identifier, "url": "https://www.youtube.com/watch?v=" + identifier,
                "title": title, "description": description,
                "thumbnail": max(thumbnails, key=lambda item: item.get("width", 0))["url"], "query": query,
                "duration_seconds": positive_seconds(data.get("lengthSeconds"))}

    def find(self, query, *, source_title="", duration_seconds=None, exclude_ids=()):
        """Prefer a filename ID, then a duration match (<2s), then rank one."""
        excluded = set(exclude_ids)
        preferred_id = reference_video_id(source_title) or reference_video_id(query)
        query = reference_search_query(query) or reference_search_query(source_title)
        target = positive_seconds(duration_seconds)
        cache = {}

        def read(identifier):
            if identifier not in cache:
                check_stopped()
                try:
                    cache[identifier] = self._read_reference(identifier, query)
                except (PublishingBrowserError, WebDriverException):
                    check_stopped()
                    cache[identifier] = None
            return cache[identifier]

        def selected(found, method, label, seconds=None):
            return {**found, "selection_version": REFERENCE_SELECTION_VERSION, "selection": method,
                    "selection_label": label, "preferred_id": preferred_id,
                    "target_duration_seconds": target,
                    "duration_seconds": seconds if seconds is not None else found.get("duration_seconds"),
                    "duration_delta_seconds": abs(seconds - target) if seconds is not None and target is not None else None}

        # An explicit source ID outranks the general search exclusions too.
        if preferred_id:
            found = read(preferred_id)
            if found:
                return selected(found, "id", "ID cuối tên: " + preferred_id, found.get("duration_seconds"))
        if not query:
            raise PublishingBrowserError("Không có tên bài nhạc để tìm kiếm sau khi đọc ID cuối tên.")
        driver = self._browser()
        driver.get("https://www.youtube.com/results?search_query=" + quote(query))
        results = wait_for(lambda: loaded_search_results(driver), timeout=45,
                           message="YouTube chưa tải xong danh sách kết quả tìm kiếm. Chưa thể kết luận không có video; kiểm tra cửa sổ YouTube rồi tìm lại tham chiếu.")
        candidates, seen = [], set(excluded)
        for renderer in results["candidates"]:
            identifier = renderer["videoId"]
            if identifier not in seen:
                seen.add(identifier)
                candidates.append((identifier, search_result_duration(renderer)))
        if not candidates:
            raise PublishingBrowserError("Kết quả YouTube không có video tham chiếu ngoài danh sách đang xử lý. Kiểm tra lại bài nhạc tìm kiếm.")
        if target is not None:
            matching = [(identifier, seconds) for identifier, seconds in candidates if seconds is not None and abs(seconds - target) < 2]
            matching.sort(key=lambda candidate: abs(candidate[1] - target))
            # An absent duration badge can still be resolved from videoDetails.
            matching.extend((identifier, None) for identifier, seconds in candidates if seconds is None)
            for identifier, seconds in matching:
                found = read(identifier)
                if not found:
                    continue
                seconds = positive_seconds(found.get("duration_seconds")) or seconds
                if seconds is not None and abs(seconds - target) < 2:
                    delta = abs(seconds - target)
                    return selected(found, "duration", f"Khớp thời lượng (lệch {delta:.3f} giây)", seconds)
        first_id, first_seconds = candidates[0]
        found = read(first_id)
        if not found:
            raise PublishingBrowserError("Không đọc được metadata của kết quả tìm kiếm đầu tiên; chưa chọn video thay thế.")
        return selected(found, "first", "Kết quả tìm kiếm đầu tiên", positive_seconds(found.get("duration_seconds")) or first_seconds)

    def close(self):
        close_driver(self.driver)
        self.driver = None


def download_reference_image(url, destination):
    """Decode YouTube's response into a real JPEG before attaching it to chat."""
    import requests

    host = (urlparse(url).hostname or "").lower()
    if urlparse(url).scheme != "https" or not (host == "ytimg.com" or host.endswith(".ytimg.com")):
        raise PublishingBrowserError("Thumbnail tham chiếu không phải URL ảnh YouTube hợp lệ.")
    check_stopped()
    destination = Path(destination)
    source = None
    try:
        with requests.get(url, timeout=(15, 45), stream=True, allow_redirects=False) as response:
            if response.status_code != 200 or not response.headers.get("Content-Type", "").startswith("image/"):
                raise PublishingBrowserError("Không tải được ảnh thumbnail tham chiếu.")
            # A .jpg URL can return AVIF or WebP. Renaming those bytes to .jpg
            # does not make them a JPEG and causes ChatGPT upload errors.
            with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".download", delete=False) as stream:
                source = Path(stream.name)
                size = 0
                for chunk in response.iter_content(65536):
                    check_stopped()
                    size += len(chunk)
                    if size > 20 * 1024 * 1024:
                        raise PublishingBrowserError("Ảnh tham chiếu lớn hơn 20 MB.")
                    stream.write(chunk)
        return normalize_thumbnail(source, destination)
    finally:
        if source is not None:
            source.unlink(missing_ok=True)


def normalize_thumbnail(source, destination):
    """Use the tool's existing FFmpeg dependency to create a 1280x720 JPEG."""
    try:
        run_owned_process(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                           "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1",
                           "-frames:v", "1", "-pix_fmt", "yuvj420p", "-q:v", "3", "-update", "1", str(destination)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError):
        raise PublishingBrowserError("Không chuyển được ảnh sang JPEG 1280×720. Kiểm tra FFmpeg của tool.") from None
    path = Path(destination)
    if not path.is_file() or not 0 < path.stat().st_size <= 2 * 1024 * 1024 or not path.read_bytes().startswith(b"\xff\xd8\xff"):
        raise PublishingBrowserError("Thumbnail đầu ra phải là JPEG hợp lệ và nhỏ hơn 2 MB.")
    return str(path)


class ChatGPTImageBrowser:
    EDITOR_SELECTORS = (
        "#prompt-textarea",
        "form [contenteditable='true'][role='textbox'], form textarea, [contenteditable='true'][role='textbox'][aria-label='Ask ChatGPT']",
    )

    def __init__(self, cookie_text="", *, profile_dir=None):
        self.cookies = parse_chatgpt_cookies(cookie_text) if str(cookie_text or "").strip() else []
        self._cookies_pending = bool(self.cookies)
        self.profile_dir = Path(profile_dir) if profile_dir is not None else None
        self.driver = None
        self.lock = threading.RLock()
        atexit.register(self.close)

    def update_cookies(self, cookie_text):
        with self.lock:
            cookies = parse_chatgpt_cookies(cookie_text) if str(cookie_text or "").strip() else []
            if cookies != self.cookies:
                self.cookies = cookies
                self._cookies_pending = bool(cookies)

    def _seed_cookies(self, driver):
        # CDP can set origin cookies on about:blank, before the first request.
        # Navigating first exposed a new unauthenticated browser to a challenge.
        try:
            driver.execute_cdp_cmd("Network.enable", {})
            for cookie in self.cookies:
                check_stopped()
                fields = {key: value for key, value in cookie.items() if key != "expiry"}
                fields["url"] = "https://chatgpt.com/"
                if "expiry" in cookie:
                    fields["expires"] = cookie["expiry"]
                result = driver.execute_cdp_cmd("Network.setCookie", fields)
                if isinstance(result, dict) and result.get("success") is False:
                    raise ChatGPTSessionNeedsAction("Không nạp được cookie ChatGPT. Dán lại cookie từ chatgpt.com hoặc đăng nhập trong phiên đã mở.", reason="cookie")
        except WebDriverException:
            raise ChatGPTSessionNeedsAction("Không nạp được cookie ChatGPT. Kiểm tra lại cookie hoặc đăng nhập trong phiên đã mở.", reason="cookie") from None
        self._cookies_pending = False

    def _browser(self):
        if self.driver is not None:
            try:
                if not self.driver.window_handles:
                    close_driver(self.driver)
                    self.driver = None
            except WebDriverException:
                close_driver(self.driver)
                self.driver = None
        created = self.driver is None
        if self.driver is None:
            profile = self.profile_dir or get_data_dir() / "chatgpt-browser-profile"
            try:
                driver = self.driver = _new_driver(profile_dir=profile)
                # This is an app-owned session, not a batch-owned browser. Job
                # cleanup/Stop must leave it available for manual verification.
                unregister_driver(driver)
            except Exception:
                check_stopped()
                raise ChatGPTSessionNeedsAction("Không mở được phiên ChatGPT đã lưu. Kiểm tra Chrome; nếu một bản tool khác đang giữ phiên này, đóng phiên của bản đó rồi thử lại.", reason="browser") from None
        driver = self.driver
        imported = self._cookies_pending
        if imported:
            self._seed_cookies(driver)
        if created or imported:
            try:
                driver.get("https://chatgpt.com/")
            except WebDriverException:
                raise ChatGPTSessionNeedsAction("Chrome chưa mở được ChatGPT. Giữ cửa sổ này để kiểm tra kết nối rồi bấm Mở / kiểm tra phiên.", reason="browser") from None
        return self.driver

    @classmethod
    def _editor(cls, driver):
        # The current Chat/Work composer has no prompt-textarea id. Keep the
        # older selector, then look within the composer instead of sidebar UI.
        for selector in cls.EDITOR_SELECTORS:
            for node in driver.find_elements(By.CSS_SELECTOR, selector):
                if node.is_displayed() and node.is_enabled():
                    return node
        return None

    @classmethod
    def _state(cls, driver):
        try:
            title = str(driver.title or "").lower()
            if any(marker in title for marker in ("just a moment", "verify you are human", "security verification")):
                return "verification"
            challenges = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='challenges.cloudflare.com'], #challenge-running, #challenge-stage, #cf-challenge-running")
            if any(node.is_displayed() for node in challenges):
                return "verification"
            editor = cls._editor(driver)
            account = driver.find_elements(By.CSS_SELECTOR, "[data-testid='accounts-profile-button'], [data-testid='profile-button'], button[aria-label*='profile'], button[aria-label*='Profile']")
            if editor is not None and any(node.is_displayed() for node in account):
                return "ready"
            if driver.find_elements(By.CSS_SELECTOR, "[data-testid='login-button'], [data-testid='signup-button']") or "/auth/login" in str(driver.current_url):
                return "login"
            return "loading"
        except StaleElementReferenceException:
            return "loading"
        except WebDriverException:
            return "closed"

    @staticmethod
    def _raise_for_state(state):
        if state == "verification":
            raise ChatGPTSessionNeedsAction("ChatGPT đang yêu cầu xác minh Cloudflare. Hoàn tất xác minh thủ công trong cửa sổ phiên đã mở, rồi bấm Mở / kiểm tra phiên và chạy tiếp. Tool giữ nguyên phiên này.", reason=state)
        if state == "login":
            raise ChatGPTSessionNeedsAction("Phiên ChatGPT cần đăng nhập. Đăng nhập trong cửa sổ phiên đã mở hoặc nạp cookie mới, rồi kiểm tra phiên và chạy tiếp.", reason=state)
        if state == "closed":
            raise ChatGPTSessionNeedsAction("Cửa sổ phiên ChatGPT đã đóng. Bấm Mở / kiểm tra phiên để mở lại phiên đã lưu.", reason=state)

    @staticmethod
    def _image_matches_request(driver, node, marker, baseline):
        source = node.get_attribute("src") or ""
        if not source or hashlib.sha256(source.encode()).hexdigest() in baseline:
            return False
        if not marker:
            return False
        return driver.execute_script("""
            const image=arguments[0], marker=arguments[1];
            const walker=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let anchor=null, node;
            while ((node=walker.nextNode())) {
                if (node.parentElement?.closest('form, [contenteditable="true"], textarea, aside, nav, header, button, a')) continue;
                const text=node.nodeValue || '';
                if (!anchor && text.includes(marker)) anchor=node;
                else if (anchor && text.includes('[TV-VIDEO ') && !text.includes(marker)
                         && (node.compareDocumentPosition(image) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
            }
            return !!anchor && !!(anchor.compareDocumentPosition(image) & Node.DOCUMENT_POSITION_FOLLOWING);
        """, node, marker)

    @classmethod
    def _completed_gallery_image(cls, driver, *, marker="", baseline=(), require_prompt=False):
        # Chat/Work no longer wraps image turns in article/author-role nodes.
        # These markers identify generated results, excluding user attachments.
        images = driver.find_elements(By.CSS_SELECTOR, "[data-testid='generated-image-preview'] img, [data-testid='generated-image-gallery'] img")
        for node in reversed(images):
            if require_prompt and not cls._image_matches_request(driver, node, marker, baseline):
                continue
            if node.is_displayed() and driver.execute_script(
                "return arguments[0].complete && arguments[0].naturalWidth >= 512 && arguments[0].naturalHeight >= 256", node
            ):
                return node.get_attribute("src")
        return None

    def ensure_ready(self, *, on_status=lambda message: None, timeout=None,
                     wait_for_user=False, on_state=lambda state, message: None, allow_image_result=False):
        with self.lock:
            on_status("Đang kiểm tra phiên ChatGPT đã lưu…")
            driver = self._browser()
            deadline = time.monotonic() + (timeout if timeout is not None else (600 if wait_for_user else 30))
            previous_state = None
            state = "loading"
            while time.monotonic() < deadline:
                check_stopped()
                state = self._state(driver)
                if state == "loading" and allow_image_result and self._completed_gallery_image(driver):
                    # Opening the generated-image viewer hides the composer.
                    # That must not prevent a saved result from being retrieved.
                    state = "ready"
                check_stopped()
                if not wait_for_user or state == "closed":
                    self._raise_for_state(state)
                messages = {
                    "ready": "Phiên ChatGPT đã đăng nhập và sẵn sàng.",
                    "verification": "Đang chờ bạn xác minh Cloudflare trong cửa sổ ChatGPT đã mở. Xác minh xong tool tự tiếp tục gửi prompt; bấm Dừng để hủy chờ.",
                    "login": "Đang chờ bạn đăng nhập trong cửa sổ ChatGPT đã mở. Đăng nhập xong tool tự tiếp tục; bấm Dừng để hủy chờ.",
                    "loading": "Đang chờ ô nhập và tài khoản ChatGPT sẵn sàng; tool tự tiếp tục khi tải xong. Bấm Dừng để hủy chờ.",
                }
                if state != previous_state:
                    message = messages[state]
                    on_status(message)
                    on_state(state, message)
                    previous_state = state
                if state == "ready":
                    return driver
                wait_interruptibly(0.5)
            raise ChatGPTSessionNeedsAction("Hết thời gian chờ phiên ChatGPT sẵn sàng. Tool đã dừng lượt xử lý và giữ cửa sổ; hoàn tất đăng nhập/xác minh rồi bấm Tự động SEO, tạo thumbnail & lên lịch để tiếp tục.", reason=state)

    def generate(self, reference_image, prompt, reference, destination, *, conversation_url="",
                 on_conversation=lambda url: None, on_state=lambda state, message: None, on_progress=lambda message: None,
                 video_id="", request=None, on_request=lambda request: None):
        with self.lock:
            self._submission_started = False
            self._active_request = None
            try:
                self.ensure_ready(wait_for_user=True, on_state=on_state, allow_image_result=True)
                return self._generate(reference_image, prompt, reference, destination,
                                      conversation_url=conversation_url, on_conversation=on_conversation, on_state=on_state, on_progress=on_progress,
                                      video_id=video_id, request=request, on_request=on_request)
            except (ChatGPTSessionNeedsAction, TaskStopped):
                if self._active_request is not None and not self._submission_started:
                    on_request({**self._active_request, "status": "not_sent"})
                self._remember_submitted_conversation(on_conversation)
                raise
            except (PublishingBrowserError, WebDriverException) as exc:
                self._remember_submitted_conversation(on_conversation)
                check_stopped()
                message = str(exc) if isinstance(exc, PublishingBrowserError) else "Mất kết nối với cửa sổ ChatGPT. Kiểm tra phiên đã mở rồi chạy tiếp."
                raise ChatGPTSessionNeedsAction(message, reason="browser") from None

    def _remember_submitted_conversation(self, on_conversation):
        if not self._submission_started or self.driver is None:
            return
        try:
            url = self.driver.current_url
        except WebDriverException:
            return
        if re.fullmatch(r"https://chatgpt\.com/c/[A-Za-z0-9-]+", str(url or "")):
            on_conversation(url)

    def _generate(self, reference_image, prompt, reference, destination, *, conversation_url="",
                  on_conversation=lambda url: None, on_state=lambda state, message: None, on_progress=lambda message: None,
                  video_id="", request=None, on_request=lambda request: None):
        driver = self._browser()
        request = dict(request or {})
        if request and (request.get("video_id") != video_id or request.get("title") != reference.get("title")):
            raise PublishingBrowserError("Yêu cầu tạo ảnh đã lưu không khớp video/title hiện tại; chưa lấy ảnh để tránh gán nhầm.")
        if request.get("status") == "not_sent":
            request, conversation_url = {}, ""
        else:
            conversation_url = request.get("conversation_url") or conversation_url
        # Resume an already submitted image request without creating it twice.
        valid_conversation = bool(re.fullmatch(r"https://chatgpt\.com/c/[A-Za-z0-9-]+", conversation_url or ""))
        resume = bool(request.get("marker")) or valid_conversation
        current = urlparse(str(driver.current_url))
        if valid_conversation and str(driver.current_url).rstrip("/") != conversation_url.rstrip("/"):
            driver.get(conversation_url)
        elif not valid_conversation and (current.hostname != "chatgpt.com" or not (current.path == "/" or current.path.startswith("/c/"))):
            driver.get("https://chatgpt.com/")
        if not resume and self._editor(driver) is None and self._completed_gallery_image(driver):
            driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        self.ensure_ready(wait_for_user=True, on_state=on_state, allow_image_result=resume)
        marker = request.get("marker") or ("Title video: " + str(reference.get("title") or "") if resume else "")
        baseline = set(request.get("baseline_images") or [])
        if not resume:
            marker = "[TV-VIDEO " + (video_id or "video") + " " + uuid.uuid4().hex + "]"
            baseline = {hashlib.sha256(str(node.get_attribute("src") or "").encode()).hexdigest()
                        for node in driver.find_elements(By.CSS_SELECTOR, "[data-testid='generated-image-preview'] img, [data-testid='generated-image-gallery'] img, article[data-turn='assistant'] img, [data-message-author-role='assistant'] img")}
            editor = wait_for(lambda: self._editor(driver),
                              timeout=30, message="Không tìm được ô nhập ChatGPT. Kiểm tra phiên đã mở trước khi chạy tiếp.")
            on_progress("Đang đính kèm ảnh tham chiếu JPEG vào ChatGPT…")
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type=file]")
            if not inputs:
                buttons = driver.find_elements(By.CSS_SELECTOR, "[data-testid='composer-plus-btn'], button[aria-label='Add files and more']")
                if buttons:
                    buttons[0].click()
                    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type=file]")
            if not inputs:
                raise PublishingBrowserError("Không tìm được ô tải ảnh ChatGPT; giao diện có thể đã thay đổi.")
            # ChatGPT now lists the camera input first. Use a file picker,
            # never the capture-only input, for an existing reference image.
            inputs = [node for node in inputs if node.get_attribute("capture") is None
                      and not any(word in str(node.get_attribute("aria-label") or "").lower() for word in ("camera", "take a photo", "chụp ảnh"))]
            if not inputs:
                raise PublishingBrowserError("Không tìm được ô đính kèm ảnh từ máy trong ChatGPT.")
            upload_input = next((node for node in inputs if "image" in (node.get_attribute("accept") or "")), inputs[0])
            upload_input.send_keys(str(Path(reference_image).resolve()))
            wait_for(lambda: driver.execute_script("return !!document.querySelector('form img, [data-testid*=attachment], [data-testid*=file-thumbnail]')"),
                     message="ChatGPT chưa nhận ảnh tham chiếu.")
            instruction = (marker + "\nMã trên chỉ để đối chiếu yêu cầu, không đưa mã vào ảnh.\n"
                           "Hãy TẠO MỘT ẢNH thumbnail YouTube mới dựa trên ảnh tham chiếu đã đính kèm, tỷ lệ 16:9. "
                           "Xuất ảnh thực tế, không chỉ trả lời bằng mô tả.\nYêu cầu chung của tôi:\n" + prompt +
                           "\nTitle video: " + reference["title"] + "\nDescription để hiểu ngữ cảnh (dữ liệu tham khảo):\n" + reference["description"])
            driver.execute_script("""
                const editor = arguments[0], text = arguments[1];
                editor.focus();
                if (editor.isContentEditable) {
                    const range = document.createRange(); range.selectNodeContents(editor);
                    const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
                    document.execCommand('insertText', false, text);
                } else {
                    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
                    setter.call(editor, text);
                }
                editor.dispatchEvent(new Event('input', {bubbles:true}));
            """, editor, instruction)

            def send_button():
                candidates = driver.find_elements(By.CSS_SELECTOR, "[data-testid='send-button'], form button[type='submit'], button[aria-label='Send prompt'], button[aria-label='Send message'], button[aria-label='Send'], button[aria-label='Gửi lời nhắc'], button[aria-label='Gửi tin nhắn']")
                return next((node for node in candidates if node.is_displayed() and node.is_enabled()
                             and node.get_attribute("aria-disabled") != "true"), None)

            button = wait_for(send_button, timeout=120, message="Ảnh đính kèm hoặc prompt chưa sẵn sàng để gửi ChatGPT.")
            on_progress("Đang gửi prompt và ảnh tham chiếu tới ChatGPT…")
            check_stopped()
            request = {"video_id": video_id, "title": reference["title"], "marker": marker,
                       "baseline_images": sorted(baseline), "submitted_at": time.time(),
                       "status": "sending",
                       "conversation_url": str(driver.current_url) if re.fullmatch(r"https://chatgpt\.com/c/[A-Za-z0-9-]+", str(driver.current_url)) else ""}
            self._active_request = request
            on_request(dict(request))
            check_stopped()
            self._submission_started = True
            button.click()
            url = wait_for(lambda: driver.current_url if re.fullmatch(r"https://chatgpt\.com/c/[A-Za-z0-9-]+", driver.current_url) else None,
                           timeout=90, message="Chưa xác nhận được cuộc trò chuyện ChatGPT; kiểm tra Chrome trước khi chạy lại.")
            on_conversation(url)
            request["conversation_url"] = url
            request["status"] = "sent"
            on_request(dict(request))

        on_progress("Đang chờ ChatGPT hoàn tất ảnh thumbnail (tối đa 10 phút)…")
        def generated_image():
            state = self._state(driver)
            if state in {"verification", "login", "closed"}:
                self.ensure_ready(wait_for_user=True, on_state=on_state, allow_image_result=True)
            stops = driver.find_elements(By.CSS_SELECTOR, "[data-testid='stop-button'], button[aria-label='Stop generating'], button[aria-label='Stop streaming'], button[aria-label='Stop'], button[aria-label='Dừng tạo']")
            if any(node.is_displayed() and node.is_enabled() for node in stops):
                return None
            image_url = self._completed_gallery_image(driver, marker=marker, baseline=baseline, require_prompt=True)
            if image_url:
                return image_url
            messages = driver.find_elements(By.CSS_SELECTOR, "article[data-turn='assistant']")
            if not messages:
                messages = driver.find_elements(By.CSS_SELECTOR, "[data-message-author-role='assistant']")
            if not messages:
                return None
            message = messages[-1]
            text = message.text.lower()
            if any(marker in text for marker in ("image generation limit", "reached your limit", "hết lượt tạo ảnh")):
                raise ChatGPTSessionNeedsAction("Tài khoản ChatGPT đã hết lượt tạo ảnh. Lượt xử lý đã dừng; tiếp tục khi tài khoản có thể tạo ảnh lại.", reason="quota")
            if any(marker in text for marker in ("unable to generate", "không thể tạo ảnh")):
                raise PublishingBrowserError("ChatGPT chưa tạo được ảnh hoặc đã hết lượt. Kiểm tra cuộc trò chuyện trước khi tiếp tục.")
            images = message.find_elements(By.CSS_SELECTOR, "img")
            for node in reversed(images):
                if not self._image_matches_request(driver, node, marker, baseline):
                    continue
                if driver.execute_script("return arguments[0].complete && arguments[0].naturalWidth >= 512 && arguments[0].naturalHeight >= 256", node):
                    return node.get_attribute("src")
            return None

        image_url = wait_for(generated_image, timeout=600,
                             message="Chưa nhận được ảnh từ ChatGPT sau 10 phút. Giữ lại link hội thoại để thử lấy ảnh tiếp.")
        on_progress("Đã tìm thấy ảnh thumbnail; đang tải ảnh từ ChatGPT về máy…")
        parsed = urlparse(image_url)
        host = (parsed.hostname or "").lower()
        if not image_url.startswith(("blob:https://chatgpt.com/", "data:image/")) and not (
            parsed.scheme == "https" and (host == "chatgpt.com" or host.endswith(".oaiusercontent.com") or host.endswith(".oaistatic.com"))
        ):
            raise PublishingBrowserError("Ảnh trả về không thuộc máy chủ ảnh ChatGPT.")
        payload = driver.execute_async_script("""
            const url = arguments[0], done = arguments[arguments.length - 1];
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 45000);
            fetch(url, {credentials: 'include', signal: controller.signal}).then(r => {
                if (!r.ok) throw new Error('download'); return r.blob();
            }).then(blob => {
                if (!blob.type.startsWith('image/') || blob.size > 20 * 1024 * 1024) throw new Error('image');
                const reader = new FileReader(); reader.onload = () => done({data: reader.result});
                reader.onerror = () => done({error: true}); reader.readAsDataURL(blob);
            }).catch(() => done({error: true})).finally(() => clearTimeout(timeout));
        """, image_url)
        if not isinstance(payload, dict) or not payload.get("data"):
            raise PublishingBrowserError("Không tải được ảnh đã tạo từ ChatGPT. Mở hội thoại để kiểm tra rồi thử lại.")
        try:
            content = base64.b64decode(payload["data"].split(",", 1)[1], validate=True)
        except (ValueError, IndexError):
            raise PublishingBrowserError("ChatGPT trả về dữ liệu ảnh không hợp lệ.") from None
        if not 0 < len(content) <= 20 * 1024 * 1024:
            raise PublishingBrowserError("Kích thước ảnh ChatGPT không hợp lệ.")
        Path(destination).write_bytes(content)
        return str(destination)

    def close(self):
        close_driver(self.driver)
        self.driver = None
        self.cookies.clear()
        self._cookies_pending = False


class StudioThumbnailBrowser:
    def __init__(self, *, verify_saved=None):
        self.verify_saved = verify_saved

    @staticmethod
    def _save_button(driver):
        return next((node for node in driver.find_elements(By.CSS_SELECTOR,"#save") if node.is_displayed() and node.is_enabled()
                     and node.get_attribute("disabled") is None and node.get_attribute("aria-disabled") != "true"),None)

    @staticmethod
    def _open_editor(driver, video_id):
        wait_for(lambda:driver.find_elements(By.CSS_SELECTOR,"ytcp-video-metadata-editor"),timeout=90,
                 message="Không mở được trang chi tiết video trong Studio.")
        if urlparse(driver.current_url).path != f"/video/{video_id}/edit":
            raise PublishingBrowserError("Studio chuyển sang video khác; chưa lưu thay đổi.")

    @staticmethod
    def _click_control(driver, locate, *, message, selected=None, timeout=30):
        def click_when_ready():
            node = locate()
            if node is None or not node.is_displayed():
                return False
            if selected is not None and selected(node):
                return True
            if not node.is_enabled() or node.get_attribute("disabled") is not None or node.get_attribute("aria-disabled") == "true":
                return False
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", node)
            try:
                node.click()
            except (ElementClickInterceptedException, ElementNotInteractableException):
                # These failures occur before a click is delivered. Re-find the
                # element after Studio finishes its dialog/upload animation.
                return False
            return True
        wait_for(click_when_ready, timeout=timeout, message=message)

    @staticmethod
    def _playlist_dialog(driver):
        StudioThumbnailBrowser._click_control(driver,
            lambda: next((node for node in driver.find_elements(By.CSS_SELECTOR,"ytcp-video-metadata-playlists ytcp-dropdown-trigger") if node.is_displayed()),None),
            timeout=45, message="Chưa mở được ô Danh sách phát; kiểm tra hộp thoại đang che trong Studio.")
        return wait_for(lambda:next((node for node in driver.find_elements(By.CSS_SELECTOR,"ytcp-playlist-dialog") if node.is_displayed()),None),
                        timeout=30,message="Chưa mở được danh sách phát của kênh.")

    @staticmethod
    def _playlist_done(driver):
        def locate():
            for dialog in driver.find_elements(By.CSS_SELECTOR,"ytcp-playlist-dialog"):
                if dialog.is_displayed():
                    return next((node for node in dialog.find_elements(By.CSS_SELECTOR,".done-button") if node.is_displayed()),None)
            return None
        StudioThumbnailBrowser._click_control(driver, locate, message="Chưa bấm được nút Xong của danh sách phát.")
        wait_for(lambda: not any(node.is_displayed() for node in driver.find_elements(By.CSS_SELECTOR,"ytcp-playlist-dialog")),
                 timeout=30, message="Hộp thoại danh sách phát chưa đóng; chưa bấm Lưu.")

    @staticmethod
    def _playlist_checkbox(driver, playlist_id):
        for dialog in driver.find_elements(By.CSS_SELECTOR,"ytcp-playlist-dialog"):
            if not dialog.is_displayed():
                continue
            for option in dialog.find_elements(By.CSS_SELECTOR,"#playlists-list ytcp-checkbox-lit"):
                if option.get_attribute("test-id") == playlist_id:
                    return next(iter(option.find_elements(By.CSS_SELECTOR,"[role=checkbox]")),None)
        return None

    def _assign_playlist(self, driver, video_id):
        self._playlist_dialog(driver)
        options=wait_for(lambda:[node for node in driver.find_elements(By.CSS_SELECTOR,"ytcp-playlist-dialog #playlists-list ytcp-checkbox-lit") if node.is_displayed()],
                         timeout=30,message="Kênh chưa có danh sách phát để tự chọn mục đầu tiên.")
        first=options[0]
        playlist_id=first.get_attribute("test-id")
        if not playlist_id:
            raise PublishingBrowserError("Chưa đọc được mã danh sách phát đầu tiên; chưa chọn mục khác thay thế.")
        checkbox=wait_for(lambda:self._playlist_checkbox(driver,playlist_id),timeout=30,
                          message="Chưa đọc được ô chọn danh sách phát đầu tiên.")
        title=driver.execute_script("return arguments[0].closest('label')?.querySelector('.label-text')?.textContent || '';",checkbox)
        info={"playlist_id":playlist_id,"playlist_title":str(title or "").strip()}
        changed=checkbox.get_attribute("aria-checked") != "true"
        if changed:
            if checkbox.get_attribute("aria-disabled") == "true":
                raise PublishingBrowserError("Danh sách phát đầu tiên đang bị khóa; chưa chọn mục khác thay thế.")
            self._click_control(driver,lambda:self._playlist_checkbox(driver,playlist_id),
                                selected=lambda node:node.get_attribute("aria-checked")=="true",
                                message="Chưa tích được danh sách phát đầu tiên; kiểm tra hộp thoại trong Studio.")
            wait_for(lambda:(node:=self._playlist_checkbox(driver,playlist_id)) is not None and node.get_attribute("aria-checked")=="true",
                     timeout=10,message="Chưa tích được danh sách phát đầu tiên.")
        self._playlist_done(driver)
        if not changed:
            return info
        try:
            button=wait_for(lambda:self._save_button(driver),timeout=6,message="Danh sách phát đã tự lưu hoặc Studio chưa bật nút Lưu.")
        except PublishingBrowserError:
            button=None
        if button is not None:
            check_stopped()
            self._click_control(driver,lambda:self._save_button(driver),message="Chưa bấm được Lưu danh sách phát trong Studio.")
            try:
                wait_for(lambda:not self._save_button(driver),timeout=45,message="Studio vẫn hiển thị thay đổi chưa lưu.")
            except PublishingBrowserError:
                pass
        check_stopped()
        driver.refresh()
        self._open_editor(driver,video_id)
        self._playlist_dialog(driver)
        wait_for(lambda:(node:=self._playlist_checkbox(driver,playlist_id)) is not None and node.get_attribute("aria-checked")=="true",
                 timeout=30,message="Studio chưa lưu video vào danh sách phát đầu tiên; giữ tiến độ để thử tiếp.")
        self._playlist_done(driver)
        return info

    def assign_first_playlist(self, channel_id, video_id):
        channel=get_channels_info(channel_id)
        if not channel or channel.id != channel_id:
            raise PublishingBrowserError("Chưa có phiên đăng nhập đúng kênh để chọn danh sách phát.")
        driver=_new_driver()
        try:
            inject_cookies_via_cdp(driver,channel.cookies)
            driver.get(f"https://studio.youtube.com/video/{video_id}/edit?hl=en")
            self._open_editor(driver,video_id)
            return self._assign_playlist(driver,video_id)
        finally:
            close_driver(driver)

    def upload(self, channel_id, video_id, path, *, ensure_playlist=False, on_saved=lambda:None):
        channel = get_channels_info(channel_id)
        if not channel or channel.id != channel_id:
            raise PublishingBrowserError("Chưa có phiên đăng nhập của kênh cần tải thumbnail.")
        verify_saved = self.verify_saved or ThumbnailReadback(channel_id, video_id, path)
        if verify_saved():
            on_saved()
            check_stopped()
            return self.assign_first_playlist(channel_id,video_id) if ensure_playlist else None
        driver = _new_driver(network_events=True)
        try:
            inject_cookies_via_cdp(driver, channel.cookies)
            driver.get(f"https://studio.youtube.com/video/{video_id}/edit?hl=en")
            title = wait_for(lambda: driver.find_elements(By.CSS_SELECTOR, "ytcp-video-metadata-editor"),
                             timeout=90, message="Không mở được trang chỉnh sửa video trong Studio. Load lại phiên kênh.")
            del title
            # The expected video URL and editor are both required before upload.
            if urlparse(driver.current_url).path != f"/video/{video_id}/edit":
                raise PublishingBrowserError("Studio chuyển sang video khác; chưa tải thumbnail.")
            inputs = driver.find_elements(By.CSS_SELECTOR, "ytcp-thumbnail-editor input[type=file], input[type=file][accept*='image']")
            if not inputs:
                raise PublishingBrowserError("Không tìm được ô tải thumbnail. Kênh có thể chưa bật thumbnail tùy chỉnh.")
            # Drain network events to distinguish this save from earlier reads.
            driver.get_log("performance")
            inputs[0].send_keys(str(Path(path).resolve()))

            def save_button():
                nodes = driver.find_elements(By.CSS_SELECTOR, "#save")
                return next((node for node in nodes if node.is_displayed() and node.is_enabled() and node.get_attribute("disabled") is None and node.get_attribute("aria-disabled") != "true"), None)

            last_check = [0.0]
            def save_or_already_saved():
                button = save_button()
                if button:
                    return button
                if time.monotonic() - last_check[0] >= 3:
                    last_check[0] = time.monotonic()
                    if verify_saved():
                        return "saved"
                return None

            button = wait_for(save_or_already_saved, timeout=90, message="Studio chưa cho lưu thumbnail và chưa đọc lại được ảnh mới; kiểm tra quyền kênh và ảnh.")
            if button == "saved":
                on_saved()
                check_stopped()
                return self._assign_playlist(driver,video_id) if ensure_playlist else None
            driver.get_log("performance")
            self._click_control(driver,save_button,message="Chưa bấm được Lưu thumbnail; kiểm tra hộp thoại đang che trong Studio.")
            saves = set()
            response_ids = set()
            save_asset_ids = {}

            def image_ids(value):
                if isinstance(value, dict):
                    for key, child in value.items():
                        if key in {"externalImageId", "imageId"} and isinstance(child, str):
                            yield child
                        elif isinstance(child, (dict, list)):
                            yield from image_ids(child)
                elif isinstance(value, list):
                    for child in value:
                        yield from image_ids(child)

            def thumbnail_mutations(value):
                if isinstance(value, dict):
                    fields = [child for key, child in value.items() if "thumbnail" in key.lower() and key != "videoReadMask"]
                    if (value.get("encryptedVideoId") or value.get("videoId")) == video_id and fields:
                        yield set(identifier for field in fields for identifier in image_ids(field))
                    for key, child in value.items():
                        if key not in {"context", "videoReadMask", "mask", "delegationContext"}:
                            yield from thumbnail_mutations(child)
                elif isinstance(value, list):
                    for child in value:
                        yield from thumbnail_mutations(child)

            def confirmed_save():
                for entry in driver.get_log("performance"):
                    event = json.loads(entry["message"])["message"]
                    params = event.get("params", {})
                    request_id = params.get("requestId")
                    if event.get("method") == "Network.requestWillBeSent":
                        request = params.get("request", {})
                        request_url = urlparse(request.get("url", ""))
                        if request_url.hostname == "studio.youtube.com" and "/youtubei/" in request_url.path:
                            body = request.get("postData", "")
                            try:
                                update = json.loads(body)
                            except ValueError:
                                continue
                            mutations = list(thumbnail_mutations(update))
                            if mutations:
                                saves.add(request_id)
                                save_asset_ids[request_id] = set().union(*mutations)
                                expect_asset = getattr(verify_saved, "expect_upload_asset", None)
                                if callable(expect_asset):
                                    expect_asset(save_asset_ids[request_id])
                    elif event.get("method") == "Network.responseReceived" and request_id in saves:
                        if int(params.get("response", {}).get("status", 0)) != 200:
                            raise PublishingBrowserError("YouTube từ chối lưu thumbnail; chưa lên lịch video.")
                        response_ids.add(request_id)
                    elif event.get("method") == "Network.loadingFinished" and request_id in response_ids:
                        try:
                            result = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                            payload = result.get("body", "")
                            if result.get("base64Encoded"):
                                payload = base64.b64decode(payload).decode("utf-8")
                            payload = payload.removeprefix(")]}'\n")
                            saved = json.loads(payload)
                        except (ValueError, WebDriverException):
                            # Missing network acknowledgements are resolved by
                            # reading the persisted thumbnail, not by guessing.
                            continue
                        if not isinstance(saved, dict) or saved.get("error") or saved.get("success") is False:
                            raise PublishingBrowserError("YouTube báo lỗi khi lưu thumbnail; chưa lên lịch video.")
                        observer = getattr(verify_saved, "observe_save_response", None)
                        if callable(observer):
                            observer(saved, save_asset_ids.get(request_id, set()))
                if time.monotonic() - last_check[0] >= 3:
                    last_check[0] = time.monotonic()
                    return verify_saved()
                return False

            try:
                wait_for(confirmed_save, timeout=90, message="Chưa xác nhận thumbnail đã lưu.")
            except PublishingBrowserError as exc:
                if str(exc) != "Chưa xác nhận thumbnail đã lưu.":
                    raise
                reason = getattr(verify_saved, "last_reason", "Chưa có bằng chứng máy chủ lưu đúng ảnh đã gửi.")
                raise PublishingBrowserError(str(reason) + " Ảnh đã tạo được giữ; chưa đặt lịch video này.") from None
            errors = driver.find_elements(By.CSS_SELECTOR, "ytcp-thumbnail-editor [role=alert], ytcp-video-metadata-editor .error-message:not([hidden])")
            if any(node.is_displayed() and node.text.strip() for node in errors):
                raise PublishingBrowserError("Studio báo lỗi khi lưu thumbnail; chưa lên lịch video này.")
            on_saved()
            check_stopped()
            return self._assign_playlist(driver,video_id) if ensure_playlist else None
        finally:
            close_driver(driver)
