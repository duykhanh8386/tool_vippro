"""Exercise browser save acknowledgements with synthetic DOM/network events."""
import base64
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.publishing_browser import ChatGPTImageBrowser, PublishingBrowserError, StudioThumbnailBrowser

VIDEO = "Abc123_-XYZ"
CHANNEL = "UC" + "a" * 22


def immediate_wait(callback, **_kwargs):
    result = callback()
    if not result:
        raise PublishingBrowserError("not confirmed")
    return result


def event(method, **params):
    return {"message": json.dumps({"message": {"method": method, "params": params}})}


class ThumbnailSaveTests(unittest.TestCase):
    def setup_browser(self, *, status=200, body=None, identifier=VIDEO, has_thumbnail=True):
        driver, button, upload = Mock(), Mock(), Mock()
        state = {"saved": False}
        driver.current_url = f"https://studio.youtube.com/video/{VIDEO}/edit?hl=en"
        button.is_displayed.return_value = True
        button.is_enabled.side_effect = lambda: not state["saved"]
        button.get_attribute.return_value = None
        request = {"encryptedVideoId": identifier}
        if has_thumbnail:
            request["thumbnail"] = {"thumbnailSource": "custom"}
        events = [event("Network.requestWillBeSent", requestId="save-1", request={
                       "url": "https://studio.youtube.com/youtubei/v1/video_manager/metadata_update?alt=json", "postData": json.dumps(request)}),
                  event("Network.responseReceived", requestId="save-1", response={"status": status}),
                  event("Network.loadingFinished", requestId="save-1")]
        driver.get_log.side_effect = [[], [], events]

        def response(*_args):
            state["saved"] = True
            return {"body": json.dumps({} if body is None else body)}

        driver.execute_cdp_cmd.side_effect = response

        def find(_by, selector):
            if selector == "ytcp-video-metadata-editor":
                return [Mock()]
            if selector == "#save":
                return [button]
            if "input[type=file]" in selector:
                return [upload]
            return []

        driver.find_elements.side_effect = find
        return driver, upload

    def upload(self, driver):
        channel = SimpleNamespace(id=CHANNEL, cookies=[])
        with tempfile.TemporaryDirectory() as folder, patch("src.publishing_browser._new_driver", return_value=driver), \
                patch("src.publishing_browser.get_channels_info", return_value=channel), \
                patch("src.publishing_browser.inject_cookies_via_cdp"), \
                patch("src.publishing_browser.wait_for", side_effect=immediate_wait):
            path = Path(folder) / "thumbnail.jpg"
            path.write_bytes(b"fake-image")
            StudioThumbnailBrowser().upload(CHANNEL, VIDEO, path)

    def test_thumbnail_success_requires_own_metadata_request_and_response(self):
        driver, upload = self.setup_browser()
        self.upload(driver)
        upload.send_keys.assert_called_once()
        driver.execute_cdp_cmd.assert_called_once_with("Network.getResponseBody", {"requestId": "save-1"})
        driver.quit.assert_called_once()

    def test_rejected_response_or_api_error_does_not_count_as_saved(self):
        for status, body in ((403, None), (200, {"error": {"code": 403}}), (200, {"success": False})):
            with self.subTest(status=status, body=body):
                driver, _ = self.setup_browser(status=status, body=body)
                with self.assertRaises(PublishingBrowserError):
                    self.upload(driver)
                driver.quit.assert_called_once()

    def test_unrelated_video_and_non_thumbnail_save_are_not_accepted(self):
        for kwargs in ({"identifier": "Def123_-XYZ"}, {"has_thumbnail": False}):
            with self.subTest(kwargs=kwargs):
                driver, _ = self.setup_browser(**kwargs)
                with self.assertRaises(PublishingBrowserError):
                    self.upload(driver)
                driver.execute_cdp_cmd.assert_not_called()


class ChatGPTResumeTests(unittest.TestCase):
    def test_existing_conversation_downloads_image_without_new_prompt(self):
        driver, message, image, editor = Mock(), Mock(), Mock(), Mock()
        editor.is_displayed.return_value = True
        image.get_attribute.return_value = "blob:https://chatgpt.com/generated-image"
        message.find_elements.return_value = [image]
        message.text = "Image created"

        def find(_by, selector):
            if selector == "#prompt-textarea":
                return [editor]
            if selector == "article[data-turn='assistant']":
                return [message]
            return []

        driver.find_elements.side_effect = find
        driver.execute_script.return_value = True
        driver.execute_async_script.return_value = {"data": "data:image/png;base64," + base64.b64encode(b"generated-bytes").decode()}
        browser = ChatGPTImageBrowser("session=secret")
        browser.driver = driver
        with tempfile.TemporaryDirectory() as folder, patch("src.publishing_browser.wait_for", side_effect=immediate_wait):
            result = Path(folder) / "generated.png"
            browser.generate("reference.jpg", "draw thumbnail", {"title": "Song", "description": "Desc"}, result,
                             conversation_url="https://chatgpt.com/c/abc-123")
            self.assertEqual(result.read_bytes(), b"generated-bytes")
        driver.get.assert_called_once_with("https://chatgpt.com/c/abc-123")
        # The only script is the natural-size image check, never prompt insertion.
        self.assertEqual(driver.execute_script.call_count, 1)


if __name__ == "__main__":
    unittest.main()
