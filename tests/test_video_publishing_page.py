"""Exercise real NiceGUI table selection callbacks without external accounts."""
import copy
import unittest
from unittest.mock import patch

from nicegui import Client, ui
from nicegui.events import GenericEventArguments, handle_event
from nicegui.page import page

from src.video_publishing import COPYRIGHT_LABELS, VIDEO_TYPE_LABELS, publishing_row_disabled_reason
from src.video_publishing_tasks import VideoPublishingController
from web.components import video_publishing as publishing_page


class MemoryState:
    def __init__(self):
        self.value = None

    def load_state(self, _key):
        return copy.deepcopy(self.value)

    def save_state(self, _key, value):
        self.value = copy.deepcopy(value)
        return True


def row(index, kind="private", copyright="clear"):
    item = {"video_id": f"v{index:010d}", "channel_id": "UC" + "a" * 22, "old_title": f"Song {index}",
            "old_description": "", "song": f"Song {index}", "copyright": copyright,
            "copyright_label": COPYRIGHT_LABELS[copyright], "visibility_type": kind, "visibility_label": VIDEO_TYPE_LABELS[kind],
            "selected": False, "status": "scanned", "detail": "", "duration_seconds": 60}
    reason = publishing_row_disabled_reason(item)
    if reason:
        item.update(availability_reason=reason, status="skipped", detail=reason)
    return item


class PublishingPageSelectionTests(unittest.TestCase):
    def setUp(self):
        self.client = Client(page("/test-publishing-selection"), request=None)
        self.addCleanup(self.client.delete)
        self.controller = VideoPublishingController(storage=MemoryState())
        self.controller.rows = [row(1), row(2, "draft", "partial"), row(3, "public"), row(4, "private", "unknown")]
        with patch.object(publishing_page, "get_video_publishing_controller", return_value=self.controller), \
                patch.object(publishing_page, "get_channels_info", return_value=[]), \
                patch.object(publishing_page.ui, "timer") as timer, self.client:
            publishing_page.create_video_publishing_page()
        self.refresh = timer.call_args.args[1]
        self.table = next(element for element in self.client.elements.values() if isinstance(element, ui.table))
        self.scope = next(element for element in self.client.elements.values() if isinstance(element, ui.select) and element.label == "Lọc loại video đã quét")
        self.categories = next(element for element in self.client.elements.values() if isinstance(element, ui.select) and element.label.startswith("Lọc trạng thái bản quyền"))

    def button(self, text):
        return next(element for element in self.client.elements.values() if isinstance(element, ui.button) and element.text == text)

    def click(self, text):
        button = self.button(text)
        self.assertTrue(button.enabled)
        listener = next(listener for listener in button._event_listeners.values() if listener.type == "click")
        with self.client:
            handle_event(listener.handler, GenericEventArguments(sender=button, client=self.client, args={}))

    def checkbox(self, identifier, checked=True):
        item = next(item for item in self.table.rows if item["video_id"] == identifier)
        listener = next(listener for listener in self.table._event_listeners.values() if listener.type == "selection")
        with self.client:
            listener.handler(GenericEventArguments(sender=self.table, client=self.client,
                             args={"added": checked, "rows": [item], "keys": [identifier]}))

    def filter(self, scope, categories):
        with self.client:
            self.scope.set_value(scope)
            self.categories.set_value(categories)

    def test_checkbox_selection_survives_timer_refresh_and_can_be_unchecked(self):
        identifier = self.controller.rows[0]["video_id"]
        self.checkbox(identifier)
        for _ in range(4):
            with self.client:
                self.refresh()
        self.assertTrue(self.controller.rows[0]["selected"])
        self.assertEqual([item["video_id"] for item in self.table.selected], [identifier])
        self.assertTrue(self.button("Tự động SEO, tạo thumbnail & lên lịch").enabled)
        self.checkbox(identifier, checked=False)
        self.assertFalse(self.controller.rows[0]["selected"])
        self.assertFalse(self.button("Tự động SEO, tạo thumbnail & lên lịch").enabled)

    def test_filter_changes_and_checkbox_events_preserve_other_selected_types(self):
        first, second = (item["video_id"] for item in self.controller.rows[:2])
        self.checkbox(first)
        self.filter("draft", ["partial"])
        self.assertEqual([item["video_id"] for item in self.table.rows], [second])
        self.checkbox(second)
        self.assertTrue(all(item["selected"] for item in self.controller.rows[:2]))
        self.click("Bỏ chọn trong bộ lọc")
        self.assertTrue(self.controller.rows[0]["selected"])
        self.assertFalse(self.controller.rows[1]["selected"])
        self.filter("private", ["clear"])
        self.assertEqual([item["video_id"] for item in self.table.selected], [first])

    def test_bulk_selection_chooses_only_current_filter_and_only_enabled_rows(self):
        self.filter("all", [])
        self.assertEqual(len(self.table.rows), 4)
        self.assertEqual([item["can_select"] for item in self.table.rows], [True, True, False, False])
        self.assertTrue(all(item["disabled_reason"] for item in self.table.rows[2:]))
        self.click("Chọn tất cả trong bộ lọc")
        self.assertEqual(len(self.table.selected), 2)
        self.click("Bỏ chọn tất cả")
        self.assertEqual(len(self.table.selected), 0)

    def test_disabled_checkbox_event_is_rejected_and_reason_is_visible(self):
        self.filter("public", ["clear"])
        self.assertFalse(self.button("Chọn tất cả trong bộ lọc").enabled)
        self.checkbox(self.controller.rows[2]["video_id"])
        self.assertFalse(self.controller.rows[2]["selected"])
        self.assertEqual(self.table.selected, [])
        self.assertIn("công khai", self.table.rows[0]["disabled_reason"])

    def test_filters_show_type_counts_even_when_current_result_is_empty(self):
        self.filter("draft", ["clear"])
        self.assertEqual(self.table.rows, [])
        self.assertIn("(1)", self.scope.options["draft"])
        self.assertIn("(2)", self.scope.options["private"])
        self.assertIn("(1)", self.categories.options["partial"])
        self.assertEqual(len(self.controller.rows), 4)

    def test_running_task_disables_selection_without_losing_checked_rows(self):
        self.checkbox(self.controller.rows[0]["video_id"])
        self.controller.busy = True
        self.controller.revision += 1
        with self.client:
            self.refresh()
        self.assertIsNone(self.table.selection)
        self.assertFalse(self.table.rows[0]["can_select"])
        self.controller.busy = False
        self.controller.revision += 1
        with self.client:
            self.refresh()
        self.assertEqual(self.table.selection, "multiple")
        self.assertEqual(len(self.table.selected), 1)

    def test_channel_source_mode_controls_which_inputs_are_shown(self):
        toggle = next(element for element in self.client.elements.values() if isinstance(element, ui.toggle))
        links = next(element for element in self.client.elements.values() if isinstance(element, ui.textarea) and element.label == "Link kênh YouTube")
        self.assertFalse(links.visible)
        with self.client:
            toggle.set_value("links")
        self.assertEqual(self.controller.settings["channel_source"], "links")
        self.assertTrue(links.visible)
        self.assertFalse(self.button("Quét video").enabled)

    def test_session_can_be_prepared_before_selecting_any_video(self):
        self.assertTrue(self.button("Kiểm tra tài khoản").enabled)
        self.assertTrue(self.button("Bỏ phiên xử lý").enabled)
        self.assertFalse(self.button("Tự động SEO, tạo thumbnail & lên lịch").enabled)

    def test_session_preparation_disables_actions_but_not_as_a_running_batch(self):
        self.controller.session_busy = True
        with self.client:
            self.refresh()
        self.assertFalse(self.button("Kiểm tra tài khoản").enabled)
        self.assertFalse(self.button("Bỏ phiên xử lý").enabled)
        self.assertFalse(self.button("Dừng").enabled)
        self.assertIsNone(self.table.selection)

    def test_audio_scan_mode_toggle_switches_setting_updates_hint_and_clears_rows(self):
        audio_toggle = next(
            element
            for element in self.client.elements.values()
            if isinstance(element, ui.toggle) and "complete_audio" in (getattr(element, "options", {}) or {})
        )
        self.assertEqual(audio_toggle.value, "normal")
        self.assertEqual(self.controller.settings["audio_scan_mode"], "normal")
        with self.client:
            audio_toggle.set_value("complete_audio")
        self.assertEqual(self.controller.settings["audio_scan_mode"], "complete_audio")
        self.assertEqual(self.controller.rows, [])
        hints = [
            element.text
            for element in self.client.elements.values()
            if isinstance(element, ui.label) and "3s nghe / 7s mất tiếng" in (element.text or "")
        ]
        self.assertTrue(hints)
        self.controller.busy = True
        with self.client:
            self.refresh()
        self.assertFalse(audio_toggle.enabled)


if __name__ == "__main__":
    unittest.main()
