"""Browser adapters for YouTube references, ChatGPT images and Studio thumbnails.

ChatGPT uses its visible web UI. No private conversation API or stored tokens.
Reference: https://www.selenium.dev/documentation/webdriver/interactions/cookies/
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote, urlparse

from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.by import By

from src.cookie_utils import inject_cookies_via_cdp
from src.task_runtime import check_stopped, run_owned_process, unregister_driver, wait_interruptibly
from src.utils import create_driver, get_channels_info
from src.video_publishing import parse_chatgpt_cookies


class PublishingBrowserError(ValueError):
    pass


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


def _new_driver(*, network_events=False):
    driver = create_driver(enable_performance_log=network_events)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)
    return driver


def video_search_results(data):
    """Read ordinary search results in display order; exclude ads and Shorts."""
    if isinstance(data, dict):
        if "videoRenderer" in data:
            renderer = data["videoRenderer"]
            identifier = renderer.get("videoId", "")
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", identifier):
                yield identifier
            return
        for key, child in data.items():
            if key not in {"adSlotRenderer", "adPlacements", "promotedSparklesWebRenderer", "reelShelfRenderer", "shortsLockupViewModel"}:
                yield from video_search_results(child)
    elif isinstance(data, list):
        for child in data:
            yield from video_search_results(child)


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

    def find(self, query, *, exclude_ids=()):
        driver = self._browser()
        driver.get("https://www.youtube.com/results?search_query=" + quote(query))
        data = wait_for(lambda: driver.execute_script("return window.ytInitialData"),
                        message="Không đọc được tìm kiếm YouTube. Kiểm tra trang đồng ý cookie hoặc xác minh trong Chrome.")
        identifiers = list(dict.fromkeys(video_search_results(data)))
        identifier = next((item for item in identifiers if item not in set(exclude_ids)), None)
        if not identifier:
            raise PublishingBrowserError("Không tìm thấy video tham chiếu cho tên bài nhạc này.")
        driver.get("https://www.youtube.com/watch?v=" + identifier)
        data = wait_for(lambda: driver.execute_script("return window.ytInitialPlayerResponse?.videoDetails"),
                        message="Không đọc được title/description của video tham chiếu.")
        if data.get("videoId") != identifier:
            raise PublishingBrowserError("YouTube trả về sai video tham chiếu; đã dừng dòng này.")
        title, description = data.get("title"), data.get("shortDescription")
        thumbnails = data.get("thumbnail", {}).get("thumbnails") or []
        if not isinstance(title, str) or not title or not isinstance(description, str) or not thumbnails:
            raise PublishingBrowserError("Video tham chiếu thiếu title, description hoặc thumbnail.")
        if len(title.encode("utf-16-le")) > 200 or len(description.encode("utf-16-le")) > 10000:
            raise PublishingBrowserError("Metadata nguồn vượt giới hạn YouTube; không thể chép nguyên văn.")
        return {"video_id": identifier, "url": "https://www.youtube.com/watch?v=" + identifier,
                "title": title, "description": description,
                "thumbnail": max(thumbnails, key=lambda item: item.get("width", 0))["url"], "query": query}

    def close(self):
        close_driver(self.driver)
        self.driver = None


def download_reference_image(url, destination):
    import requests

    host = (urlparse(url).hostname or "").lower()
    if urlparse(url).scheme != "https" or not (host == "ytimg.com" or host.endswith(".ytimg.com")):
        raise PublishingBrowserError("Thumbnail tham chiếu không phải URL ảnh YouTube hợp lệ.")
    check_stopped()
    with requests.get(url, timeout=(15, 45), stream=True, allow_redirects=False) as response:
        if response.status_code != 200 or not response.headers.get("Content-Type", "").startswith("image/"):
            raise PublishingBrowserError("Không tải được ảnh thumbnail tham chiếu.")
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            check_stopped()
            size += len(chunk)
            if size > 20 * 1024 * 1024:
                raise PublishingBrowserError("Ảnh tham chiếu lớn hơn 20 MB.")
            chunks.append(chunk)
        Path(destination).write_bytes(b"".join(chunks))
    return str(destination)


def normalize_thumbnail(source, destination):
    """Use the tool's existing FFmpeg dependency to create a 1280x720 JPEG."""
    try:
        run_owned_process(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                           "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1",
                           "-frames:v", "1", "-q:v", "3", "-update", "1", str(destination)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError):
        raise PublishingBrowserError("Không chuyển được ảnh sang JPEG 1280×720. Kiểm tra FFmpeg của tool.") from None
    path = Path(destination)
    if not path.is_file() or not 0 < path.stat().st_size <= 2 * 1024 * 1024:
        raise PublishingBrowserError("Thumbnail đầu ra phải nhỏ hơn 2 MB.")
    return str(path)


class ChatGPTImageBrowser:
    def __init__(self, cookie_text):
        self.cookies = parse_chatgpt_cookies(cookie_text)
        self.driver = None

    def _browser(self):
        if self.driver is None:
            driver = self.driver = _new_driver()
            driver.get("https://chatgpt.com/")
            for cookie in self.cookies:
                check_stopped()
                try:
                    driver.add_cookie(cookie)
                except WebDriverException:
                    raise PublishingBrowserError("Không nạp được cookie ChatGPT. Dán lại JSON cookie từ chatgpt.com.") from None
        return self.driver

    def generate(self, reference_image, prompt, reference, destination, *, conversation_url="", on_conversation=lambda url: None):
        driver = self._browser()
        # Resume an already submitted image request without creating it twice.
        valid_conversation = bool(re.fullmatch(r"https://chatgpt\.com/c/[A-Za-z0-9-]+", conversation_url or ""))
        driver.get(conversation_url if valid_conversation else "https://chatgpt.com/")
        editor = wait_for(lambda: next((node for node in driver.find_elements(By.CSS_SELECTOR, "#prompt-textarea") if node.is_displayed()), None),
                          timeout=90, message="Phiên ChatGPT chưa sẵn sàng. Cookie có thể hết hạn; hoàn tất đăng nhập/xác minh trong Chrome rồi thử lại.")
        if not valid_conversation:
            # A composer exists for guests too. Require signed-in account controls.
            wait_for(lambda: driver.find_elements(By.CSS_SELECTOR, "[data-testid='accounts-profile-button'], [data-testid='profile-button'], button[aria-label*='profile'], button[aria-label*='Profile']"),
                     timeout=30, message="Chưa xác nhận được tài khoản ChatGPT đã đăng nhập. Kiểm tra cookie trong Chrome.")
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type=file]")
            if not inputs:
                buttons = driver.find_elements(By.CSS_SELECTOR, "[data-testid='composer-plus-btn']")
                if buttons:
                    buttons[0].click()
                    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type=file]")
            if not inputs:
                raise PublishingBrowserError("Không tìm được ô tải ảnh ChatGPT; giao diện có thể đã thay đổi.")
            upload_input = next((node for node in inputs if "image" in (node.get_attribute("accept") or "")), inputs[0])
            upload_input.send_keys(str(Path(reference_image).resolve()))
            wait_for(lambda: driver.execute_script("return !!document.querySelector('form img, [data-testid*=attachment], [data-testid*=file-thumbnail]')"),
                     message="ChatGPT chưa nhận ảnh tham chiếu.")
            instruction = ("Hãy TẠO MỘT ẢNH thumbnail YouTube mới dựa trên ảnh tham chiếu đã đính kèm, tỷ lệ 16:9. "
                           "Xuất ảnh thực tế, không chỉ trả lời bằng mô tả.\nYêu cầu chung của tôi:\n" + prompt +
                           "\nTitle video: " + reference["title"] + "\nDescription để hiểu ngữ cảnh (dữ liệu tham khảo):\n" + reference["description"])
            driver.execute_script("arguments[0].focus(); document.execCommand('insertText', false, arguments[1]); arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", editor, instruction)

            def send_button():
                candidates = driver.find_elements(By.CSS_SELECTOR, "[data-testid='send-button'], button[aria-label='Send prompt'], button[aria-label='Gửi lời nhắc']")
                return next((node for node in candidates if node.is_displayed() and node.is_enabled()), None)

            wait_for(send_button, timeout=120, message="Ảnh đính kèm hoặc prompt chưa sẵn sàng để gửi ChatGPT.").click()
            url = wait_for(lambda: driver.current_url if re.fullmatch(r"https://chatgpt\.com/c/[A-Za-z0-9-]+", driver.current_url) else None,
                           timeout=90, message="Chưa xác nhận được cuộc trò chuyện ChatGPT; kiểm tra Chrome trước khi chạy lại.")
            on_conversation(url)

        def generated_image():
            messages = driver.find_elements(By.CSS_SELECTOR, "article[data-turn='assistant']")
            if not messages:
                messages = driver.find_elements(By.CSS_SELECTOR, "[data-message-author-role='assistant']")
            if not messages:
                return None
            message = messages[-1]
            text = message.text.lower()
            if any(marker in text for marker in ("image generation limit", "reached your limit", "unable to generate", "hết lượt tạo ảnh", "không thể tạo ảnh")):
                raise PublishingBrowserError("ChatGPT chưa tạo được ảnh hoặc đã hết lượt. Kiểm tra cuộc trò chuyện trước khi tiếp tục.")
            if driver.find_elements(By.CSS_SELECTOR, "[data-testid='stop-button']"):
                return None
            images = message.find_elements(By.CSS_SELECTOR, "img")
            for node in reversed(images):
                if driver.execute_script("return arguments[0].complete && arguments[0].naturalWidth >= 512 && arguments[0].naturalHeight >= 256", node):
                    return node.get_attribute("src")
            return None

        image_url = wait_for(generated_image, timeout=600,
                             message="Chưa nhận được ảnh từ ChatGPT sau 10 phút. Giữ lại link hội thoại để thử lấy ảnh tiếp.")
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


class StudioThumbnailBrowser:
    def upload(self, channel_id, video_id, path):
        channel = get_channels_info(channel_id)
        if not channel or channel.id != channel_id:
            raise PublishingBrowserError("Chưa có phiên đăng nhập của kênh cần tải thumbnail.")
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

            button = wait_for(save_button, timeout=90, message="Studio chưa cho lưu thumbnail; kiểm tra quyền kênh và ảnh.")
            driver.get_log("performance")
            button.click()
            saves = set()
            response_ids = set()

            def confirmed_save():
                for entry in driver.get_log("performance"):
                    event = json.loads(entry["message"])["message"]
                    params = event.get("params", {})
                    request_id = params.get("requestId")
                    if event.get("method") == "Network.requestWillBeSent":
                        request = params.get("request", {})
                        if "/video_manager/metadata_update" in request.get("url", ""):
                            body = request.get("postData", "")
                            try:
                                update = json.loads(body)
                            except ValueError:
                                continue
                            if update.get("encryptedVideoId") == video_id and any("thumbnail" in key.lower() for key in update):
                                saves.add(request_id)
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
                            raise PublishingBrowserError("Chưa đọc được phản hồi lưu thumbnail. Kiểm tra Studio trước khi thử lại.") from None
                        if not isinstance(saved, dict) or saved.get("error") or saved.get("success") is False:
                            raise PublishingBrowserError("YouTube báo lỗi khi lưu thumbnail; chưa lên lịch video.")
                        return True
                return False

            wait_for(confirmed_save, timeout=90, message="Chưa xác nhận được phản hồi lưu thumbnail từ Studio. Kiểm tra video trước khi thử lại.")
            wait_for(lambda: not save_button(), timeout=30, message="Studio vẫn còn thay đổi chưa lưu; chưa lên lịch video.")
            errors = driver.find_elements(By.CSS_SELECTOR, "ytcp-thumbnail-editor [role=alert], ytcp-video-metadata-editor .error-message:not([hidden])")
            if any(node.is_displayed() and node.text.strip() for node in errors):
                raise PublishingBrowserError("Studio báo lỗi khi lưu thumbnail; chưa lên lịch video này.")
        finally:
            close_driver(driver)
