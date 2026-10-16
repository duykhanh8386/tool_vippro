import asyncio
import json
import sqlite3
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from nicegui import Client, ui
from nicegui.page import page

from src.channel_scanner import ChannelScanReport
from src.state_manager import StateManager
from web.components import studio


class LoginStatePrivacyTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.db_path = self.folder / "app_state.db"
        path_patch = patch("src.state_manager.get_data_dir", return_value=self.folder)
        path_patch.start()
        self.addCleanup(path_patch.stop)
        self.manager = StateManager()
        self.addCleanup(self.close_manager)

    def close_manager(self):
        if self.manager._conn is not None:
            self.manager._conn.close()

    def test_legacy_login_is_erased_from_database_and_wal_only(self):
        legacy = sqlite3.connect(self.db_path)
        self.addCleanup(legacy.close)
        legacy.execute("PRAGMA journal_mode = WAL")
        legacy.execute("PRAGMA secure_delete = OFF")
        legacy.execute(
            "CREATE TABLE app_state (page_name TEXT PRIMARY KEY, state_json TEXT NOT NULL)"
        )
        secret = "legacy-test-password-should-disappear"
        legacy.executemany(
            "INSERT INTO app_state VALUES (?, ?)",
            [
                ("studio_credentials", json.dumps({
                    "email": "legacy@example.test", "password": secret, "remember_me": True,
                })),
                ("audio", json.dumps({"selected_channel": "keep-channel"})),
            ],
        )
        legacy.commit()
        self.assertIn(secret.encode(), Path(str(self.db_path) + "-wal").read_bytes())

        self.assertTrue(self.manager.clear_state("studio_credentials"))

        self.assertEqual(self.manager.load_state("audio"), {"selected_channel": "keep-channel"})
        self.assertIsNone(legacy.execute(
            "SELECT state_json FROM app_state WHERE page_name = 'studio_credentials'"
        ).fetchone())
        for database_file in self.folder.glob("app_state.db*"):
            with self.subTest(file=database_file.name):
                self.assertNotIn(secret.encode(), database_file.read_bytes())
                self.assertNotIn(b"legacy@example.test", database_file.read_bytes())

    def test_login_cannot_be_saved_again(self):
        self.assertFalse(self.manager.save_state("studio_credentials", {
            "email": "user@example.test", "password": "new-test-password", "remember_me": True,
        }))
        self.assertTrue(self.manager.save_state("audio", {"saved": True}))
        self.assertIsNone(self.manager._get_conn().execute(
            "SELECT state_json FROM app_state WHERE page_name = 'studio_credentials'"
        ).fetchone())
        self.assertEqual(self.manager.load_state("audio"), {"saved": True})

    def test_stale_writer_cannot_make_login_readable(self):
        conn = self.manager._get_conn()
        conn.execute("INSERT INTO app_state VALUES (?, ?)", (
            "studio_credentials", json.dumps({"password": "stale-test-password"}),
        ))
        conn.commit()
        self.assertIsNone(self.manager.load_state("studio_credentials"))


class StudioLoginPrivacyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        patches = ExitStack()
        self.addCleanup(patches.close)
        for name, value in (
            ("get_channels_info", []),
            ("get_license_info", None),
            ("get_audio_recovery_state", {}),
            ("get_audio_recovery_registry_items", ([], [])),
            ("get_audio_recovery_scan_preferences", {
                "scan_mode": studio.RECOVERY_SCAN_MODE_SELECTED,
                "video_scan_scope": studio.RECOVERY_VIDEO_SCOPE_PUBLIC,
                "selected_channel_ids": ["channel-a"],
            }),
            ("create_auto_registry_content", lambda: None),
            ("acknowledge_channel_refresh", False),
        ):
            patches.enter_context(patch.object(studio, name, return_value=value))
        self.timer = patches.enter_context(patch.object(studio.ui, "timer"))
        self.client = Client(page("/test-studio-login-privacy"), request=None)
        self.addCleanup(self.client.delete)
        with self.client:
            studio.create_studio_content()
        self.email, self.password = [
            element for element in self.client.elements.values() if isinstance(element, ui.input)
        ]
        self.dialog = next(
            element for element in self.client.elements.values()
            if isinstance(element, ui.dialog) and self.password in list(element.descendants())
        )

    def click(self, text):
        button = next(element for element in self.client.elements.values()
                      if isinstance(element, ui.button) and element.text == text)
        listener = next(listener for listener in button._event_listeners.values()
                        if listener.type == "click")
        with self.client:
            listener.handler(None)

    def fill_login(self):
        with self.client:
            self.email.value = "user@example.test"
            self.password.value = "typed-test-password"

    def assert_login_empty(self):
        self.assertEqual(self.email.value, "")
        self.assertEqual(self.password.value, "")

    async def test_all_three_forms_require_fresh_input_on_every_open(self):
        for text in ("Load lại kênh", "Thêm kênh", "Quét Gmail") * 2:
            with self.subTest(button=text):
                self.fill_login()
                self.click(text)
                self.assertTrue(self.dialog.value)
                self.assert_login_empty()
                self.assertFalse(any(isinstance(element, ui.checkbox)
                                     for element in self.dialog.descendants()))
                self.assertEqual(self.email._props["autocomplete"], "off")
                self.assertEqual(self.password._props["autocomplete"], "new-password")

    async def test_close_and_browser_dismiss_clear_both_fields(self):
        for close in (lambda: self.click("Đóng"), lambda: self.dialog.set_value(False)):
            self.click("Thêm kênh")
            self.fill_login()
            with self.client:
                self.password.props("type=text")
                close()
            self.assert_login_empty()
            self.assertEqual(self.password._props["type"], "password")

    async def test_submit_passes_typed_login_to_scan_and_immediately_clears_form(self):
        create_task = asyncio.create_task
        for opener, submit, operation in (
            ("Load lại kênh", "Load lại", "reload_selected"),
            ("Thêm kênh", "Tìm kênh mới", "add_new"),
            ("Quét Gmail", "Quét Gmail", "sync_gmail"),
        ):
            with self.subTest(operation=operation):
                self.click(opener)
                self.fill_login()
                tasks = []

                def schedule(coroutine):
                    task = create_task(coroutine)
                    tasks.append(task)
                    return task

                with patch.object(studio, "ChannelFetcher") as fetcher:
                    fetcher.return_value.run.return_value = ChannelScanReport(completed=True)
                    with patch.object(studio.asyncio, "create_task", side_effect=schedule):
                        # The Gmail opener and submit have the same label.
                        button = next(element for element in self.dialog.descendants()
                                      if isinstance(element, ui.button) and element.text == submit)
                        listener = next(listener for listener in button._event_listeners.values()
                                        if listener.type == "click")
                        with self.client:
                            listener.handler(None)
                    self.assert_login_empty()
                    self.assertFalse(self.dialog.value)
                    self.assertEqual(len(tasks), 1)
                    await asyncio.wait_for(tasks[0], timeout=5)
                    fetcher.return_value.run.assert_called_once()
                    self.assertEqual(fetcher.return_value.run.call_args.kwargs["email"],
                                     "user@example.test")
                    self.assertEqual(fetcher.return_value.run.call_args.kwargs["password"],
                                     "typed-test-password")

    async def test_missing_login_does_not_start_scan(self):
        self.click("Thêm kênh")
        for email, password in (("", ""), ("user@example.test", ""), ("", "password")):
            with self.subTest(email_present=bool(email), password_present=bool(password)):
                with self.client, patch.object(studio, "ChannelFetcher") as fetcher:
                    self.email.value = email
                    self.password.value = password
                    self.click("Tìm kênh mới")
                    self.assertTrue(self.dialog.value)
                    fetcher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
