"""Exercise browser save acknowledgements with synthetic DOM/network events."""
import base64
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.publishing_browser import ChatGPTImageBrowser, PublishingBrowserError, StudioThumbnailBrowser, YouTubeReferenceBrowser, loaded_search_results, search_result_duration, wait_for
from src.task_runtime import TaskStopped

VIDEO = "Abc123_-XYZ"
CHANNEL = "UC" + "a" * 22


def immediate_wait(callback, **_kwargs):
    result = callback()
    if not result:
        raise PublishingBrowserError("not confirmed")
    return result


def event(method, **params):
    return {"message": json.dumps({"message": {"method": method, "params": params}})}


def source(identifier, seconds=60):
    return {"video_id": identifier, "url": "https://www.youtube.com/watch?v=" + identifier,
            "title": "Title " + identifier, "description": "Exact description\nSecond line", "duration_seconds": seconds,
            "thumbnail": f"https://i.ytimg.com/vi/{identifier}/hqdefault.jpg"}


def result(identifier, duration=None):
    renderer = {"videoId": identifier}
    if duration is not None:
        renderer["lengthSeconds"] = duration
    return {"videoRenderer": renderer}


class ReferencePriorityTests(unittest.TestCase):
    def setUp(self):
        self.browser = YouTubeReferenceBrowser()
        self.driver = Mock()
        self.driver.execute_script.return_value = {"contents": [result(VIDEO, 90), result("Def123_-XYZ", 60)]}
        self.patches = [patch.object(self.browser, "_browser", return_value=self.driver),
                        patch("src.publishing_browser.wait_for", side_effect=immediate_wait)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_filename_id_bypasses_search_and_duration_filter(self):
        with patch.object(self.browser, "_read_reference", return_value=source("ZoHtnOPSE80", 900)) as read:
            found = self.browser.find("Different song", source_title="เพลงไทย [ZoHtnOPSE80].mp4", duration_seconds=60)
        self.assertEqual(found["selection"], "id")
        self.assertEqual(found["video_id"], "ZoHtnOPSE80")
        read.assert_called_once_with("ZoHtnOPSE80", "Different song")
        self.driver.get.assert_not_called()

    def test_explicit_id_outranks_general_search_exclusions(self):
        with patch.object(self.browser, "_read_reference", return_value=source("ZoHtnOPSE80")):
            found = self.browser.find("Song [ZoHtnOPSE80]", duration_seconds=60, exclude_ids=["ZoHtnOPSE80"])
        self.assertEqual(found["selection"], "id")
        self.driver.get.assert_not_called()

    def test_original_title_id_outranks_id_in_search_query(self):
        with patch.object(self.browser, "_read_reference", return_value=source("ZoHtnOPSE80")) as read:
            self.browser.find("Song [Def123_-XYZ]", source_title="Original [ZoHtnOPSE80]", duration_seconds=60)
        read.assert_called_once_with("ZoHtnOPSE80", "Song")

    def test_unavailable_filename_id_falls_back_to_duration_match(self):
        def read(identifier, _query):
            if identifier == "ZoHtnOPSE80":
                raise PublishingBrowserError("unavailable")
            return source(identifier)

        with patch.object(self.browser, "_read_reference", side_effect=read):
            found = self.browser.find("Song [ZoHtnOPSE80].mp4", duration_seconds=60)
        self.assertEqual(found["video_id"], "Def123_-XYZ")
        self.assertEqual(found["selection"], "duration")
        self.driver.get.assert_called_once_with("https://www.youtube.com/results?search_query=Song")

    def test_later_duration_match_outranks_first_result(self):
        with patch.object(self.browser, "_read_reference", return_value=source("Def123_-XYZ", 60)) as read:
            found = self.browser.find("Song", duration_seconds=60)
        self.assertEqual(found["video_id"], "Def123_-XYZ")
        self.assertEqual(found["selection"], "duration")
        self.assertEqual(found["duration_delta_seconds"], 0)
        read.assert_called_once_with("Def123_-XYZ", "Song")

    def test_smallest_delta_wins_with_search_order_breaking_ties(self):
        self.driver.execute_script.return_value = {"contents": [result(VIDEO, 61.5), result("Def123_-XYZ", 60), result("Ghi123_-XYZ", 60)]}
        with patch.object(self.browser, "_read_reference", side_effect=lambda identifier, query: source(identifier, 60)):
            found = self.browser.find("Song", duration_seconds=60)
        self.assertEqual(found["video_id"], "Def123_-XYZ")

    def test_strict_two_second_boundary_with_fractional_target(self):
        for duration, method in ((58, "first"), (58.001, "duration"), (61.999, "duration"), (62, "first")):
            with self.subTest(duration=duration):
                self.driver.execute_script.return_value = {"contents": [result(VIDEO, 90), result("Def123_-XYZ", duration)]}
                with patch.object(self.browser, "_read_reference", side_effect=lambda identifier, query: source(identifier, duration if identifier == "Def123_-XYZ" else 90)):
                    found = self.browser.find("Song", duration_seconds=60)
                self.assertEqual(found["selection"], method)

    def test_missing_target_duration_falls_back_to_first(self):
        for duration in (None, 0, -1, float("nan"), float("inf")):
            with self.subTest(duration=duration), patch.object(self.browser, "_read_reference", return_value=source(VIDEO, 90)) as read:
                found = self.browser.find("Song", duration_seconds=duration)
                self.assertEqual(found["selection"], "first")
                read.assert_called_once_with(VIDEO, "Song")

    def test_search_duration_is_verified_against_selected_video(self):
        self.driver.execute_script.return_value = {"contents": [result(VIDEO, 60), result("Def123_-XYZ", 61)]}
        with patch.object(self.browser, "_read_reference", side_effect=lambda identifier, query: source(identifier, 500 if identifier == VIDEO else 61)):
            found = self.browser.find("Song", duration_seconds=60)
        self.assertEqual(found["video_id"], "Def123_-XYZ")
        self.assertEqual(found["duration_delta_seconds"], 1)

    def test_missing_badge_uses_video_details_before_falling_back(self):
        self.driver.execute_script.return_value = {"contents": [result(VIDEO, 90), result("Def123_-XYZ")]}
        with patch.object(self.browser, "_read_reference", return_value=source("Def123_-XYZ", 60)):
            found = self.browser.find("Song", duration_seconds=60)
        self.assertEqual(found["video_id"], "Def123_-XYZ")
        self.assertEqual(found["selection"], "duration")

    def test_unreadable_match_falls_back_to_first_search_result(self):
        def read(identifier, query):
            if identifier == "Def123_-XYZ":
                raise PublishingBrowserError("unavailable")
            return source(identifier, 90)

        with patch.object(self.browser, "_read_reference", side_effect=read):
            found = self.browser.find("Song", duration_seconds=60)
        self.assertEqual(found["video_id"], VIDEO)
        self.assertEqual(found["selection"], "first")

    def test_excluded_search_result_is_not_used_for_duration_or_fallback(self):
        with patch.object(self.browser, "_read_reference", return_value=source(VIDEO, 90)) as read:
            found = self.browser.find("Song", duration_seconds=60, exclude_ids=["Def123_-XYZ"])
        self.assertEqual(found["video_id"], VIDEO)
        self.assertEqual(found["selection"], "first")
        read.assert_called_once_with(VIDEO, "Song")

    def test_no_readable_first_result_raises_instead_of_choosing_random_video(self):
        with patch.object(self.browser, "_read_reference", side_effect=PublishingBrowserError("unavailable")), self.assertRaises(PublishingBrowserError):
            self.browser.find("Song", duration_seconds=60)

    def test_stop_is_not_swallowed_by_fallback(self):
        with patch.object(self.browser, "_read_reference", side_effect=TaskStopped), self.assertRaises(TaskStopped):
            self.browser.find("Song [ZoHtnOPSE80]", duration_seconds=60)
        self.driver.get.assert_not_called()

    def test_read_reference_preserves_exact_metadata_and_duration(self):
        data = {"videoId": VIDEO, "title": "เพลงไทย 🎵", "shortDescription": "Line 1\n\nLine 3", "lengthSeconds": "123",
                "thumbnail": {"thumbnails": [{"url": "small", "width": 320}, {"url": "large", "width": 1280}]}}
        self.driver.execute_script.return_value = {"videoDetails": data}
        found = self.browser._read_reference(VIDEO, "Song")
        self.assertEqual(found["title"], data["title"])
        self.assertEqual(found["description"], data["shortDescription"])
        self.assertEqual(found["thumbnail"], "large")
        self.assertEqual(found["duration_seconds"], 123)
        self.driver.get.assert_called_once_with("https://www.youtube.com/watch?v=" + VIDEO)

    def test_partial_initial_data_is_polled_until_video_results_are_ready(self):
        self.driver.execute_script.side_effect = [{"responseContext": {}}, {"candidates": [], "empty": False},
                                                  {"contents": [result(VIDEO, 90), result("Def123_-XYZ", 60)]}]
        with patch("src.publishing_browser.wait_for", side_effect=wait_for), \
                patch("src.publishing_browser.wait_interruptibly") as pause, \
                patch.object(self.browser, "_read_reference", return_value=source("Def123_-XYZ", 60)):
            found = self.browser.find("0805939256", duration_seconds=60)
        self.assertEqual(found["selection"], "duration")
        self.assertEqual(found["video_id"], "Def123_-XYZ")
        pause.assert_called_once_with(0.5)

    def test_rendered_search_rows_work_when_initial_data_has_no_video_renderers(self):
        self.driver.execute_script.side_effect = [{"responseContext": {}},
                                                  {"candidates": [{"videoId": VIDEO, "lengthText": {"simpleText": "1:00"}}]}]
        with patch.object(self.browser, "_read_reference", return_value=source(VIDEO, 60)):
            found = self.browser.find("0805939256", duration_seconds=60)
        self.assertEqual(found["selection"], "duration")
        self.assertEqual(found["video_id"], VIDEO)

    def test_loading_search_does_not_count_as_empty_results(self):
        self.driver.execute_script.side_effect = [{"responseContext": {}}, {"candidates": [], "empty": False}]
        self.assertIsNone(loaded_search_results(self.driver))

    def test_explicit_empty_search_and_consent_are_reported_separately(self):
        self.driver.execute_script.side_effect = [{}, {"candidates": [], "empty": True}]
        with self.assertRaisesRegex(PublishingBrowserError, "Kết quả YouTube không có"):
            self.browser.find("0805939256")
        self.driver.execute_script.side_effect = [{}, {"candidates": [], "blocked": True}]
        with self.assertRaisesRegex(PublishingBrowserError, "đồng ý cookie hoặc xác minh"):
            self.browser.find("0805939256")

    def test_wrong_video_details_and_unavailable_player_are_rejected(self):
        for player in ({"videoDetails": {"videoId": "Def123_-XYZ"}}, {"playabilityStatus": {"status": "ERROR"}}):
            self.driver.execute_script.return_value = player
            with self.subTest(player=player), self.assertRaises(PublishingBrowserError):
                self.browser._read_reference(VIDEO, "Song")

    def test_duration_badges_support_hours_minutes_and_runs(self):
        for renderer, expected in (({"lengthText": {"simpleText": "1:02:03"}}, 3723),
                                   ({"lengthText": {"runs": [{"text": "12:34"}]}}, 754),
                                   ({"lengthSeconds": "61.234"}, 61.234), ({"lengthText": {"simpleText": "LIVE"}}, None),
                                   ({"lengthText": {"simpleText": "01:99"}}, None), ({}, None)):
            self.assertEqual(search_result_duration(renderer), expected)


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
        driver.verify_saved = lambda: state["saved"]

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
            StudioThumbnailBrowser(verify_saved=driver.verify_saved).upload(CHANNEL, VIDEO, path)

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

    def test_readback_confirms_save_when_network_event_is_missing(self):
        driver, _ = self.setup_browser()
        driver.get_log.side_effect = [[], [], []]
        driver.verify_saved = Mock(side_effect=[False, True])
        self.upload(driver)
        driver.execute_cdp_cmd.assert_not_called()

    def test_success_acknowledgement_without_saved_image_does_not_confirm(self):
        driver, _ = self.setup_browser()
        driver.verify_saved = lambda: False
        with self.assertRaises(PublishingBrowserError):
            self.upload(driver)

    def test_already_saved_image_is_not_uploaded_twice(self):
        driver, upload = self.setup_browser()
        driver.verify_saved = lambda: True
        self.upload(driver)
        upload.send_keys.assert_not_called()
        driver.get.assert_not_called()

    def test_auto_saved_thumbnail_does_not_require_an_enabled_save_button(self):
        driver, _ = self.setup_browser()
        driver.verify_saved = Mock(side_effect=[False, True])
        driver.get_log.side_effect = [[], []]
        old_find = driver.find_elements.side_effect
        def find(by, selector):
            if selector == "#save":
                return []
            return old_find(by, selector)
        driver.find_elements.side_effect = find
        self.upload(driver)


class ChatGPTResumeTests(unittest.TestCase):
    def test_modern_gallery_downloads_with_hidden_composer_and_no_assistant_article(self):
        driver, image, hidden_stop = Mock(), Mock(), Mock()
        driver.window_handles = ["chatgpt-window"]
        driver.title = "Thumbnail conversation"
        driver.current_url = "https://chatgpt.com/c/abc-123"
        image.is_displayed.return_value = True
        image.get_attribute.return_value = "blob:https://chatgpt.com/generated-image"
        hidden_stop.is_displayed.return_value = False
        def find(_by, selector):
            if "generated-image-preview" in selector:
                return [image]
            if "stop-button" in selector:
                return [hidden_stop]
            return []
        driver.find_elements.side_effect = find
        driver.execute_script.return_value = True
        driver.execute_async_script.return_value = {"data": "data:image/png;base64," + base64.b64encode(b"generated-bytes").decode()}
        browser = ChatGPTImageBrowser()
        browser.driver = driver
        self.addCleanup(browser.close)
        progress = Mock()
        with tempfile.TemporaryDirectory() as folder, patch("src.publishing_browser.wait_for", side_effect=immediate_wait):
            output = Path(folder) / "generated.png"
            browser.generate("unused.jpg", "draw", {}, output, conversation_url=driver.current_url, on_progress=progress)
            self.assertEqual(output.read_bytes(), b"generated-bytes")
        driver.get.assert_not_called()
        self.assertTrue(any("đang tải ảnh" in call.args[0] for call in progress.call_args_list))
        self.assertFalse(any("execCommand" in call.args[0] for call in driver.execute_script.call_args_list))

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
        browser._cookies_pending = False
        with tempfile.TemporaryDirectory() as folder, patch("src.publishing_browser.wait_for", side_effect=immediate_wait), \
                patch.object(browser, "ensure_ready", return_value=driver):
            result = Path(folder) / "generated.png"
            browser.generate("reference.jpg", "draw thumbnail", {"title": "Song", "description": "Desc"}, result,
                             conversation_url="https://chatgpt.com/c/abc-123")
            self.assertEqual(result.read_bytes(), b"generated-bytes")
        driver.get.assert_called_once_with("https://chatgpt.com/c/abc-123")
        # The only script is the natural-size image check, never prompt insertion.
        self.assertEqual(driver.execute_script.call_count, 2)


if __name__ == "__main__":
    unittest.main()
