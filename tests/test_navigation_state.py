import unittest

from web.components.drawer import NavigationState


class NavigationStateTests(unittest.TestCase):
    def test_running_flow_blocks_its_own_exit_but_allows_return_from_other_page(self):
        navigation = NavigationState()
        navigation.lock("/audio/flow", "Audio is running")

        self.assertEqual(
            navigation.blocking_message("/audio/flow", "/studio"),
            "Audio is running",
        )
        self.assertIsNone(navigation.blocking_message("/studio", "/audio/flow"))
        self.assertIsNone(navigation.blocking_message("/audio/flow", "/audio/flow"))

        navigation.unlock("/audio/flow")
        self.assertIsNone(navigation.blocking_message("/audio/flow", "/studio"))

    def test_finishing_another_job_does_not_unlock_running_audio_flow(self):
        navigation = NavigationState()
        navigation.lock("/audio/flow", "Audio is running")
        navigation.lock("/reup/delete-video", "Delete is running")
        navigation.unlock("/reup/delete-video")

        self.assertEqual(
            navigation.blocking_message("/audio/flow", "/studio"),
            "Audio is running",
        )
        self.assertIsNone(
            navigation.blocking_message("/reup/delete-video", "/studio")
        )


if __name__ == "__main__":
    unittest.main()
