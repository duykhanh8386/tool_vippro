import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.channel_groups import (
    ALL_GMAILS,
    UNKNOWN_GMAIL,
    filter_channels_by_gmail,
    gmail_filter_options,
)
from src.channel_store import ChannelStore
from src.channel_scanner import ChannelFetcher


class ChannelGmailGroupsTests(unittest.TestCase):
    def test_legacy_channels_are_kept_in_unknown_group(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "channels.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                """CREATE TABLE channels (
                    id TEXT PRIMARY KEY, name TEXT, img_src TEXT,
                    sapisidhash TEXT, delegated_session_id TEXT, role TEXT,
                    challenge TEXT, botguardResponse TEXT,
                    cookies_json TEXT NOT NULL DEFAULT '[]',
                    cookies_expires_at INTEGER,
                    created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
                )"""
            )
            conn.execute(
                "INSERT INTO channels (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                ("old", "Old channel", 1, 1),
            )
            conn.commit()
            conn.close()

            store = ChannelStore(db_path)
            try:
                self.assertEqual(store.get_channel("old")["owner_email"], "")
                store.upsert_channel({"id": "new", "name": "New channel", "owner_email": " User@Example.COM "})
                self.assertEqual(store.get_channel("new")["owner_email"], "user@example.com")
                store.upsert_channel({"id": "new", "name": "Refreshed"})
                self.assertEqual(store.get_channel("new")["owner_email"], "user@example.com")
                self.assertEqual(store.get_channel("old")["name"], "Old channel")
                self.assertEqual(store.get_channel("old")["studio_context"], {})
                browser_context = {
                    "client": {"clientName": 62, "clientVersion": "from-browser"},
                    "user": {"serializedDelegationContext": "delegation"},
                }
                store.upsert_channel({"id": "new", "name": "New channel", "studio_context": browser_context})
                store.upsert_channel({"id": "new", "name": "Partial refresh"})
                self.assertEqual(store.get_channel("new")["studio_context"], browser_context)

                from src.utils import get_channels_info

                with patch("src.channel_store.channel_store", store):
                    self.assertEqual(get_channels_info("new").owner_email, "user@example.com")
                    self.assertEqual(get_channels_info("new").studio_context, browser_context)
                    self.assertEqual(
                        {channel.id: channel.owner_email for channel in get_channels_info()},
                        {"old": "", "new": "user@example.com"},
                    )
            finally:
                store.conn.close()

    def test_filter_shows_only_channels_scanned_by_chosen_gmail(self):
        channels = [
            SimpleNamespace(id="a", owner_email="A@Example.com"),
            SimpleNamespace(id="b", owner_email="b@example.com"),
            SimpleNamespace(id="old", owner_email=""),
        ]
        options = gmail_filter_options(channels)

        self.assertEqual(list(options), [ALL_GMAILS, "a@example.com", "b@example.com", UNKNOWN_GMAIL])
        self.assertEqual(
            [channel.id for channel in filter_channels_by_gmail(channels, "a@example.com")],
            ["a"],
        )
        self.assertEqual(
            [channel.id for channel in filter_channels_by_gmail(channels, UNKNOWN_GMAIL)],
            ["old"],
        )
        self.assertEqual(len(filter_channels_by_gmail(channels, ALL_GMAILS)), 3)

    def test_scanner_saves_login_gmail_with_channel(self):
        class Driver:
            current_url = "https://studio.youtube.com/channel/UC123"

            def find_element(self, *_args):
                return SimpleNamespace(
                    get_attribute=lambda attribute: {
                        "src": "https://example.com/avatar.png",
                        "alt": "Music channel",
                    }.get(attribute)
                )

            def get_cookies(self):
                return [{"name": "SAPISID", "value": "test"}]

            def get(self, url):
                self.current_url = url

        class ImmediateWait:
            def __init__(self, *_args, **_kwargs):
                pass

            def until(self, _condition):
                return True

        response = SimpleNamespace(
            url="https://studio.youtube.com/channel/UC123",
            text='"datasyncId":"123||456","channelRoleType":"CREATOR_CHANNEL_ROLE_TYPE_OWNER"',
            raise_for_status=lambda: None,
        )
        fetcher = ChannelFetcher()
        fetcher.driver = Driver()
        fetcher._owner_email = "user@example.com"
        with (
            patch("src.channel_scanner.WebDriverWait", ImmediateWait),
            patch("src.channel_scanner.generate_sapisidhash", return_value="hash"),
            patch(
                "src.channel_scanner.get_request_payload_from_performance_log",
                return_value='{"challenge":"a","botguardResponse":"b"}',
            ),
            patch("src.channel_scanner.requests.get", return_value=response),
            patch("src.channel_scanner.channel_store.upsert_channel") as upsert,
        ):
            result = fetcher._get_channel_info()

        self.assertEqual(result["id"], "UC123")
        self.assertEqual(upsert.call_args.args[0]["owner_email"], "user@example.com")


if __name__ == "__main__":
    unittest.main()
