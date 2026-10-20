"""Local Chrome checks; opt in with TVAUTOMATION_TEST_CHROMEDRIVER.

Uses fresh browser profiles, a localhost menu and mocked channel reads.
It never signs into Google or changes a saved channel.
"""

import html
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from src.channel_scanner import ChannelFetcher


DRIVER_PATH = os.environ.get("TVAUTOMATION_TEST_CHROMEDRIVER", "")
CHANNEL_IDS = [f"UC{i:022d}" for i in range(23)]
AMBIGUOUS_ROWS = {10, 18}


@unittest.skipUnless(DRIVER_PATH and Path(DRIVER_PATH).is_file(), "Set TVAUTOMATION_TEST_CHROMEDRIVER for local Chrome checks")
class ChannelScannerBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        options = webdriver.ChromeOptions()
        for argument in ("--headless=new", "--window-size=800,650", "--disable-gpu", "--disable-background-networking"):
            options.add_argument(argument)
        cls.driver = webdriver.Chrome(service=Service(DRIVER_PATH), options=options)
        cls.driver.set_page_load_timeout(8)
        cls.addClassCleanup(cls.driver.quit)
        cls.fixture = {"copies": False}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                active = self.path.rsplit("/", 1)[-1]
                values = list(enumerate(CHANNEL_IDS))
                if cls.fixture["copies"]:
                    values = [(10, CHANNEL_IDS[10]), (10, CHANNEL_IDS[10])]
                rows = []
                for index, channel_id in values:
                    title = "🎧 เพลงเพราะไทยแลนด์" if index in AMBIGUOUS_ROWS else f"Existing {index}"
                    selected = 'active="true"' if channel_id == active else ""
                    rows.append(
                        f'<ytd-account-item-renderer {selected} data-channel-id="{active}" '
                        f'onclick="location.href=\'/channel/{channel_id}\'">'
                        f'<yt-formatted-string id="channel-title">{html.escape(title)}</yt-formatted-string>'
                        '<span id="account-name">Same account label</span></ytd-account-item-renderer>'
                    )
                content = (
                    '<!doctype html><meta charset="utf-8"><style>'
                    'ytd-account-item-renderer{display:block;height:45px;padding:4px;cursor:pointer}'
                    '#account-name{display:block;font-size:10px}</style>' + "".join(rows)
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

        class Server(ThreadingHTTPServer):
            def handle_error(self, *_args):
                pass  # Chrome can close speculative sockets during teardown.

        cls.server = Server(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

        def close_server():
            cls.server.shutdown()
            cls.server.server_close()
            cls.thread.join(timeout=2)

        cls.addClassCleanup(close_server)

    def scan(self, start_id, *, excluded_ids=(), excluded_names=()):
        self.driver.get(f"http://127.0.0.1:{self.server.server_port}/channel/{start_id}")
        fetcher = ChannelFetcher()
        fetcher.driver = self.driver
        saved = []

        def read_channel():
            channel_id = fetcher._current_channel_id()
            saved.append(channel_id)
            return {"id": channel_id, "name": "Fixture channel"}

        with patch.object(fetcher, "_get_channel_info", side_effect=read_channel), patch(
            "src.channel_scanner.STUDIO_LOAD_TIMEOUT_SECONDS", 5,
        ):
            report = fetcher._scan_filtered_channels(
                include_channel_ids=None, exclude_channel_ids=set(excluded_ids),
                include_channel_names={}, exclude_channel_names=set(excluded_names),
            )
        self.assertEqual(report.failures, [])
        self.assertEqual(report.unidentified_channel_count, 0)
        return saved

    def test_identical_names_on_rows_11_and_19_resolve_to_distinct_ids(self):
        self.fixture["copies"] = False
        saved = self.scan(
            CHANNEL_IDS[0],
            excluded_ids={channel_id for index, channel_id in enumerate(CHANNEL_IDS) if index not in AMBIGUOUS_ROWS},
            excluded_names={f"existing {index}" for index in range(23) if index not in AMBIGUOUS_ROWS},
        )
        self.assertEqual(saved, [CHANNEL_IDS[10], CHANNEL_IDS[18]])

    def test_current_channel_dom_copies_are_saved_once(self):
        self.fixture["copies"] = True
        self.assertEqual(self.scan(CHANNEL_IDS[10]), [CHANNEL_IDS[10]])

    def test_active_row_javascript_handles_root_and_child_markers(self):
        self.fixture["copies"] = False
        self.driver.get(f"http://127.0.0.1:{self.server.server_port}/channel/{CHANNEL_IDS[0]}")
        fetcher = ChannelFetcher()
        fetcher.driver = self.driver
        rows = self.driver.find_elements(By.XPATH, fetcher.CHANNEL_SELECTION_XPATH)
        self.assertTrue(fetcher._account_item_is_active(rows[0]))
        self.assertFalse(fetcher._account_item_is_active(rows[1]))
        self.driver.execute_script(
            "arguments[0].removeAttribute('active'); arguments[0].firstElementChild.setAttribute('aria-selected','true');",
            rows[0],
        )
        self.assertTrue(fetcher._account_item_is_active(rows[0]))


if __name__ == "__main__":
    unittest.main()
