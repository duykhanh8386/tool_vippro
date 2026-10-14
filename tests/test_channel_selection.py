import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nicegui import Client, ui
from nicegui.page import page

from src.channel_groups import ALL_GMAILS, UNKNOWN_GMAIL
from web.components.common import create_channel_selection


class ChannelSelectionTests(unittest.TestCase):
    def setUp(self):
        self.client = Client(page("/test-channel-selection"), request=None)
        self.addCleanup(self.client.delete)
        self.channels = [
            SimpleNamespace(id="channel-a", name="Channel A", img_src="", owner_email="a@gmail.com"),
            SimpleNamespace(id="channel-b", name="Channel B", img_src="", owner_email="b@gmail.com"),
            SimpleNamespace(id="channel-old", name="Channel Old", img_src="", owner_email=""),
        ]
        self.changed = Mock(return_value=None)

    def create(self, **kwargs):
        with self.client:
            self.state, self.refresh = create_channel_selection(self.channels, self.changed, **kwargs)
        self.gmail = next(element for element in self.client.elements.values() if isinstance(element, ui.select))

    def cards(self):
        return [element for element in self.client.elements.values()
                if isinstance(element, ui.card) and "app-channel-card" in element._classes]

    def visible_names(self):
        return [label.text for card in self.cards() for label in card.descendants()
                if isinstance(label, ui.label) and label.text.startswith("Channel ")]

    def click_channel(self, name):
        card = next(card for card in self.cards() if any(
            isinstance(element, ui.label) and element.text == name for element in card.descendants()
        ))
        listener = next(listener for listener in card._event_listeners.values() if listener.type == "click")
        with self.client:
            listener.handler()

    def test_gmail_filter_and_unknown_account_show_only_their_channels(self):
        self.create()
        self.assertEqual(set(self.gmail.options), {ALL_GMAILS, "a@gmail.com", "b@gmail.com", UNKNOWN_GMAIL})
        with self.client:
            self.gmail.set_value("a@gmail.com")
        self.assertEqual(self.visible_names(), ["Channel A"])
        self.click_channel("Channel A")
        self.assertEqual(self.state["id"], "channel-a")
        with self.client:
            self.gmail.set_value(UNKNOWN_GMAIL)
        self.assertEqual(self.visible_names(), ["Channel Old"])
        self.assertIsNone(self.state["id"])
        self.changed.assert_called_with(None)

    def test_switching_account_clears_the_previous_channel_in_shared_state(self):
        shared = {"id": "channel-a"}
        self.create(selection_state=shared)
        with self.client:
            self.gmail.set_value("b@gmail.com")
        self.assertIs(self.state, shared)
        self.assertIsNone(shared["id"])
        self.assertEqual(self.visible_names(), ["Channel B"])
        self.changed.assert_called_once_with(None)

    def test_channel_and_gmail_cannot_change_while_work_is_running(self):
        self.create(initial_selected_ids="channel-a", can_change_selection=lambda: False)
        self.click_channel("Channel B")
        with self.client:
            self.gmail.set_value("b@gmail.com")
        self.assertEqual(self.state["id"], "channel-a")
        self.assertEqual(self.gmail.value, ALL_GMAILS)
        self.assertEqual(len(self.cards()), 3)
        self.changed.assert_not_called()

    def test_callback_can_decline_account_or_channel_changes(self):
        self.create(initial_selected_ids="channel-a")
        self.changed.return_value = False
        self.click_channel("Channel B")
        with self.client:
            self.gmail.set_value("b@gmail.com")
        self.assertEqual(self.state["id"], "channel-a")
        self.assertEqual(self.gmail.value, ALL_GMAILS)

    def test_restored_selection_is_rendered_from_shared_state(self):
        shared = {"id": None}
        self.create(selection_state=shared)
        shared["id"] = "channel-b"
        with self.client:
            self.refresh()
        selected = [card for card in self.cards() if "app-channel-card--selected" in card._classes]
        self.assertEqual(len(selected), 1)
        self.assertTrue(any(isinstance(element, ui.label) and element.text == "Channel B"
                            for element in selected[0].descendants()))

    def test_multi_select_all_respects_gmail_and_drops_other_account_selections(self):
        self.create(multi_select=True, initial_selected_ids=["channel-b"])
        with self.client:
            self.gmail.set_value("a@gmail.com")
        self.assertEqual(self.state["ids"], [])
        button = next(element for element in self.client.elements.values()
                      if isinstance(element, ui.button) and element.text == "Tất cả")
        listener = next(listener for listener in button._event_listeners.values() if listener.type == "click")
        with self.client:
            listener.handler(None)
        self.assertEqual(self.state["ids"], ["channel-a"])
        self.changed.assert_called_with(["channel-a"])


class TaskPageGmailFilterTests(unittest.TestCase):
    def test_all_three_task_pages_render_and_apply_the_gmail_filter(self):
        from web.components import add_audio_flow, delete_back_flow, remove_audio

        channels = [
            SimpleNamespace(id="channel-a", name="Channel A", img_src="", owner_email="a@gmail.com"),
            SimpleNamespace(id="channel-b", name="Channel B", img_src="", owner_email="b@gmail.com"),
        ]
        for module, create in (
            (remove_audio, remove_audio.create_remove_audio_page),
            (add_audio_flow, add_audio_flow.create_add_audio_flow_page),
            (delete_back_flow, delete_back_flow.create_delete_back_flow_page),
        ):
            with self.subTest(page=module.__name__):
                client = Client(page("/test-task-gmail"), request=None)
                try:
                    with patch.object(module, "get_channels_info", return_value=channels), patch.object(
                        module, "state_manager"
                    ) as state, patch.object(module.ui, "notify"), client:
                        state.load_state.return_value = None
                        create()
                        gmail = next(element for element in client.elements.values()
                                     if isinstance(element, ui.select)
                                     and element._props.get("label") == "Lọc kênh theo Gmail đã quét")
                        gmail.set_value("b@gmail.com")
                        names = [element.text for element in client.elements.values()
                                 if isinstance(element, ui.label) and element.text in {"Channel A", "Channel B"}]
                        self.assertEqual(names, ["Channel B"])
                finally:
                    client.delete()

