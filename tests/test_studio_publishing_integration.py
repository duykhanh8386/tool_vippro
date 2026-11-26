"""Opt-in Chrome/HTTP round trip against local Studio fixtures only."""
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from src.module.base import studio_video_from_payload
from src.module.video_publishing_module import VideoPublishingModule
from src.publishing_browser import StudioThumbnailBrowser
from src.publishing_thumbnails import ThumbnailReadback

VIDEO = "Abc123_-XYZ"
CHANNEL = "UC" + "a" * 22
STAMP = 4070998800
PAGE = '''<!doctype html><ytcp-video-metadata-editor><ytcp-thumbnail-editor>
<input type="file" accept="image/jpeg" hidden></ytcp-thumbnail-editor>
<button id="save" disabled>Save</button></ytcp-video-metadata-editor><script>
const file=document.querySelector('input'),save=document.querySelector('#save');
file.onchange=()=>save.disabled=false;
save.onclick=async()=>{
 await fetch('/youtubei/v1/video_manager/metadata_update',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({encryptedVideoId:'Abc123_-XYZ',thumbnail:{customThumbnail:{externalImageId:'IM-upload'}}})});
 save.disabled=true;
};</script>'''


class StudioFixture(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        state = self.server.video
        if "thumbnail" in data:
            self.server.steps.append("thumbnail")
            state["thumbnailEditorState"] = {"customThumbnail":{"externalImageId":"IM-upload"},"defaultStill":False,"stillId":0}
        if "title" in data:
            self.server.steps.append("metadata")
            state["title"] = data["title"]["newTitle"]
            state["description"] = data["description"]["newDescription"]
        if "scheduledPublishing" in data:
            self.server.steps.append("schedule")
            state["scheduledPublishingDetails"] = {"publishTimeSeconds":data["scheduledPublishing"]["set"]["timeSec"]}
            state["draftStatus"] = "DRAFT_STATUS_NONE"
        payload = json.dumps({"video":state}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


class LocalStudioDriver:
    def __init__(self, driver, origin):
        self.driver, self.origin = driver, origin

    def __getattr__(self, key):
        return getattr(self.driver, key)

    @property
    def current_url(self):
        return self.driver.current_url.replace(self.origin, "https://studio.youtube.com", 1)

    def get(self, url):
        if urlsplit(url).hostname != "studio.youtube.com":
            raise AssertionError("External navigation is disabled in this fixture")
        self.driver.get(url.replace("https://studio.youtube.com", self.origin, 1))

    def get_log(self, name):
        return [{**entry,"message":entry["message"].replace(self.origin,"https://studio.youtube.com")} for entry in self.driver.get_log(name)]


@unittest.skipUnless(os.environ.get("TV_PUBLISHING_BROWSER_TESTS") == "1", "opt-in local Chrome test")
class StudioPublishingBrowserTests(unittest.TestCase):
    def test_saved_asset_then_metadata_and_schedule_complete_while_cdn_stays_old(self):
        root = Path(__file__).resolve().parents[1] / "build"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="studio-publishing-test-",dir=root) as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to(root.resolve()))
            server = ThreadingHTTPServer(("127.0.0.1",0),StudioFixture)
            server.video = {"videoId":VIDEO,"channelId":CHANNEL,"title":"Original","description":"Old description",
                            "privacy":"VIDEO_PRIVACY_PRIVATE","draftStatus":"DRAFT_STATUS_PUBLIC",
                            "thumbnailDetails":{"thumbnails":[{"url":"https://i9.ytimg.com/old.jpg","width":1280}]},
                            "thumbnailEditorState":{"customThumbnail":{"externalImageId":"IM-old"},"defaultStill":False},
                            "videoPrechecks":{"videoUploadChecksNotMonetized":{"copyrightCheck":{"checkStatus":"COPYRIGHT_CHECK_NO_ISSUES"}}}}
            server.steps = []
            worker = threading.Thread(target=server.serve_forever,daemon=True)
            worker.start()
            origin = f"http://127.0.0.1:{server.server_port}"
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--user-data-dir=" + str(Path(folder)/"profile"))
            options.set_capability("goog:loggingPrefs",{"performance":"ALL"})
            driver = webdriver.Chrome(service=Service(os.environ["CHROMEDRIVER"]), options=options)
            adapter = LocalStudioDriver(driver,origin)
            image = Path(folder)/("Song ["+VIDEO+"].jpg")
            image.write_bytes(b"JPEG upload fixture")
            channel = SimpleNamespace(id=CHANNEL,role="OWNER",delegated_session_id="delegate",cookies=[],cookie_string=lambda:"fixture")
            response = SimpleNamespace(status_code=200,headers={"Content-Type":"image/jpeg"},iter_content=lambda size:[b"old CDN bytes"])
            pixel_reads = []
            def cached_pixels(path):
                pixel_reads.append(str(path))
                return bytes([100 if len(pixel_reads)==1 else 200]*43200)
            try:
                with patch("src.publishing_thumbnails.thumbnail_pixels",side_effect=cached_pixels), \
                        patch("requests.get") as get:
                    get.return_value.__enter__.return_value=response
                    verifier = ThumbnailReadback(CHANNEL,VIDEO,image,reader=lambda *_args:studio_video_from_payload(server.video))
                    with patch("src.publishing_browser._new_driver",return_value=adapter), \
                            patch("src.publishing_browser.get_channels_info",return_value=channel), \
                            patch("src.publishing_browser.inject_cookies_via_cdp"):
                        StudioThumbnailBrowser(verify_saved=verifier).upload(CHANNEL,VIDEO,image)
                    self.assertEqual(verifier.confirmed_asset_id,"IM-upload")
                module = VideoPublishingModule()
                reference={"title":"New song title","description":"Line one\nLine two"}
                def local_post(url, **kwargs):
                    if urlsplit(url).path!="/youtubei/v1/video_manager/metadata_update":
                        raise AssertionError("Fixture supports only its local metadata endpoint")
                    return requests.post(origin+urlsplit(url).path,**kwargs)
                with patch("src.module.video_publishing_module.get_channels_info",return_value=channel), \
                        patch("src.module.video_publishing_module.studio_authorization_header",return_value="fixture"), \
                        patch("src.module.video_publishing_module.post_with_stop",side_effect=local_post), \
                        patch.object(module,"_get_session_token",return_value="fixture"), \
                        patch.object(module,"_get_video_info",side_effect=lambda *_args:studio_video_from_payload(server.video)):
                    module.copy_metadata(CHANNEL,VIDEO,reference,expected_title="Original",expected_description="Old description",categories=["clear"])
                    module.schedule(CHANNEL,VIDEO,STAMP,reference,categories=["clear"])
                self.assertEqual(server.steps,["thumbnail","metadata","schedule"])
                self.assertEqual(server.video["title"],reference["title"])
                self.assertEqual(server.video["description"],reference["description"])
                self.assertEqual(server.video["scheduledPublishingDetails"]["publishTimeSeconds"],str(STAMP))
            finally:
                driver.quit()
                server.shutdown()
                server.server_close()
                worker.join(5)


if __name__ == "__main__":
    unittest.main()
