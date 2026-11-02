import asyncio
import copy
import unittest

from src import audio_recovery as recovery
from test_registry_descriptions import RegistryAudioFixture
from web.components.add_audio_flow import _acquire_audio_mutation_guard


class VideoGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_registry_and_manual_can_reserve_different_videos_of_the_same_channel(self):
        parent = recovery.get_audio_mutation_guard("guard-parallel")
        auto = recovery.get_audio_mutation_guard("guard-parallel", "auto")
        manual = recovery.get_audio_mutation_guard("guard-parallel", "manual")
        token = recovery._RUNTIME_CHANNEL_CONTEXT.set((1, "guard-parallel"))
        try:
            self.assertTrue(auto.acquire(blocking=False))
        finally:
            recovery._RUNTIME_CHANNEL_CONTEXT.reset(token)
        try:
            self.assertTrue(parent.locked())
            self.assertFalse(parent.is_manually_locked())
            self.assertFalse(auto.acquire(blocking=False))
            self.assertTrue(manual.acquire(blocking=False))
            try:
                self.assertTrue(manual.is_manually_locked())
                self.assertFalse(auto.is_manually_locked())
                self.assertFalse(parent.acquire(blocking=False))
            finally:
                manual.release()
            self.assertTrue(auto.locked())
        finally:
            auto.release()
        self.assertFalse(parent.locked())

    async def test_two_registry_workers_cannot_mutate_the_same_video(self):
        first = recovery.get_audio_mutation_guard("guard-registry", "video")
        other = recovery.get_audio_mutation_guard("guard-registry", "other")
        token = recovery._RUNTIME_CHANNEL_CONTEXT.set((1, "guard-registry"))
        try:
            self.assertTrue(first.acquire(blocking=False))
            try:
                second_token = recovery._RUNTIME_CHANNEL_CONTEXT.set((2, "guard-registry"))
                try:
                    self.assertFalse(recovery.get_audio_mutation_guard("guard-registry", "video").acquire(blocking=False))
                    self.assertTrue(other.acquire(blocking=False))
                    other.release()
                finally:
                    recovery._RUNTIME_CHANNEL_CONTEXT.reset(second_token)
            finally:
                first.release()
        finally:
            recovery._RUNTIME_CHANNEL_CONTEXT.reset(token)

    async def test_flow_waits_only_for_its_video_and_cancellation_does_not_release_auto(self):
        auto = recovery.get_audio_mutation_guard("guard-flow", "auto")
        self.assertTrue(auto.acquire(blocking=False))
        pending = asyncio.create_task(_acquire_audio_mutation_guard("guard-flow", "auto"))
        try:
            distinct = await asyncio.wait_for(_acquire_audio_mutation_guard("guard-flow", "other"), 1)
            distinct.release()
            await asyncio.sleep(0.03)
            self.assertFalse(pending.done())
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            self.assertTrue(auto.locked())
        finally:
            auto.release()
        acquired = await asyncio.wait_for(_acquire_audio_mutation_guard("guard-flow", "auto"), 1)
        acquired.release()

    async def test_channel_and_video_ids_define_the_lock_not_music_path(self):
        one = recovery.get_audio_mutation_guard("guard-one", "same-video-id")
        self.assertIs(one, recovery.get_audio_mutation_guard(" guard-one ", " same-video-id "))
        other = recovery.get_audio_mutation_guard("guard-two", "same-video-id")
        self.assertTrue(one.acquire(blocking=False))
        try:
            self.assertTrue(other.acquire(blocking=False))
            other.release()
            with self.assertRaises(ValueError):
                recovery.get_audio_mutation_guard("guard-one", " ")
        finally:
            one.release()


class RegistryPerVideoGuardTests(RegistryAudioFixture, unittest.IsolatedAsyncioTestCase):
    async def test_manual_video_is_deferred_while_another_video_on_same_channel_is_repaired(self):
        state = recovery.get_audio_recovery_state()
        state["entries"]["channel"]["other"] = copy.deepcopy(self.entry)
        self.manager.save_state("audio_recovery", state)
        self.payload = {"videoTranslations": [{"videoId": vid, "translations": []} for vid in ("video", "other")],
                        "audioTracks": []}
        manual = recovery.get_audio_mutation_guard("channel", "video")
        self.assertTrue(manual.acquire(blocking=False))
        seen = []

        def upload(**kwargs):
            seen.append(kwargs["id_video"])
            self.assertEqual(kwargs["id_video"], "other")
            self.assertTrue(recovery.get_audio_mutation_guard("channel", "other").locked())
            self.assertTrue(manual.locked())
            return 200

        self.add.side_effect = upload
        try:
            result = await recovery.run_audio_recovery_cycle(now=2000)
            self.assertEqual(seen, ["other", "other"])
            self.assertEqual(result["repaired"], 2)
            self.assertEqual(result["deferred_busy"], 2)
            self.assertEqual(self.metadata.call_count, 1)
            self.assertTrue(manual.locked())
        finally:
            manual.release()
        self.assertFalse(recovery.get_audio_mutation_guard("channel").locked())


if __name__ == "__main__":
    unittest.main()
