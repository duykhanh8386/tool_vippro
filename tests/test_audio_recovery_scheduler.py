import asyncio
import time
import unittest
from collections import Counter
from unittest.mock import Mock, patch

from src.audio_recovery import _schedule_recovery_channels


class AudioRecoverySchedulerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.state = {"enabled": True, "entries": {}}
        self.results = {}
        self.stop = asyncio.Event()
        self.saved = Mock()
        for target, value in (
            ("get_audio_recovery_state", self.state),
            ("_update_runtime_status", None),
        ):
            patcher = patch(f"src.audio_recovery.{target}", return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def add_channels(self, *channels):
        for channel in channels:
            self.state["entries"][channel] = {f"{channel}-video": {"languages": ["en"]}}

    def schedule(self, process):
        return asyncio.create_task(_schedule_recovery_channels(
            process, dict(self.state["entries"]), self.results,
            stop_event=self.stop, should_stop=self.stop.is_set, on_complete=self.saved,
        ))

    async def test_pending_channels_get_one_turn_before_any_channel_repeats(self):
        self.add_channels("a", "b", "c", "d", "e")
        release_slow = asyncio.Event()
        all_started = asyncio.Event()
        calls = Counter()
        active = set()
        max_active = 0

        async def process(_index, channel, _entries, **_kwargs):
            nonlocal max_active
            self.assertNotIn(channel, active)
            active.add(channel)
            max_active = max(max_active, len(active))
            calls[channel] += 1
            if len(calls) == 5:
                all_started.set()
            await asyncio.sleep(0)
            if channel == "a":
                await release_slow.wait()
            self.results[channel] = {"scan_performed": True}
            active.remove(channel)

        task = self.schedule(process)
        try:
            await asyncio.wait_for(all_started.wait(), timeout=1)
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.assertEqual(calls, dict.fromkeys("abcde", 1))
            self.assertEqual(max_active, 3)
        finally:
            release_slow.set()
            await asyncio.wait_for(task, timeout=1)
        self.assertEqual(self.saved.call_count, 5)

        # The next round uses the refreshed registry, including a new channel.
        self.add_channels("f")
        await asyncio.wait_for(self.schedule(process), timeout=1)
        self.assertEqual(calls, {**dict.fromkeys("abcde", 2), "f": 1})

    async def test_new_channels_take_priority_over_repeating_finished_channel(self):
        self.add_channels("a", "b")
        release_slow = asyncio.Event()
        all_started = asyncio.Event()
        calls = Counter()

        async def process(_index, channel, entries, *, current_state, current_total):
            calls[channel] += 1
            self.assertIs(entries, current_state["entries"][channel])
            if channel == "a":
                self.add_channels("c", "d", "e")
            if len(calls) == 5:
                all_started.set()
            if channel == "b":
                await release_slow.wait()
            if channel in "cde":
                self.assertEqual(current_total, 5)
            self.results[channel] = {"scan_performed": True}

        task = self.schedule(process)
        try:
            await asyncio.wait_for(all_started.wait(), timeout=1)
            self.assertEqual(calls, dict.fromkeys("abcde", 1))
            self.assertFalse(task.done())
        finally:
            release_slow.set()
            await asyncio.wait_for(task, timeout=1)
        self.assertEqual(calls, dict.fromkeys("abcde", 1))

    async def test_repeat_uses_fresh_registration_and_deactivation_stops_it(self):
        self.add_channels("a")
        calls = 0

        async def process(_index, channel, entries, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.state["entries"][channel] = {"new-video": {"languages": ["fr"]}}
            else:
                self.assertEqual(entries, {"new-video": {"languages": ["fr"]}})
                self.state["disabled_channel_ids"] = [channel]
            self.results[channel] = {"scan_performed": True}

        await asyncio.wait_for(self.schedule(process), timeout=1)
        self.assertEqual(calls, 2)
        self.assertEqual(self.saved.call_count, 2)

    async def test_failed_or_blocked_pass_yields_before_retry(self):
        self.add_channels("a")
        for report in ({"errors": 1, "scan_performed": True}, {"scan_performed": False}):
            with self.subTest(report=report):
                self.stop.clear()
                calls = []

                async def process(_index, channel, _entries, **_kwargs):
                    calls.append(time.monotonic())
                    self.results[channel] = report
                    if len(calls) == 2:
                        self.stop.set()

                with patch("src.audio_recovery.MONITOR_IDLE_POLL_SECONDS", 0.03):
                    await asyncio.wait_for(self.schedule(process), timeout=1)
                self.assertEqual(len(calls), 2)
                self.assertGreaterEqual(calls[1] - calls[0], 0.025)

    async def test_stop_drains_current_pass_without_starting_queued_channels(self):
        self.add_channels("a", "b", "c", "d")
        started = asyncio.Event()
        release = asyncio.Event()
        calls = []

        async def process(_index, channel, _entries, **_kwargs):
            calls.append(channel)
            if len(calls) == 3:
                started.set()
            await release.wait()
            self.results[channel] = {"scan_performed": True}

        task = self.schedule(process)
        try:
            await asyncio.wait_for(started.wait(), timeout=1)
            self.stop.set()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
        finally:
            release.set()
            await asyncio.wait_for(task, timeout=1)
        self.assertEqual(calls, ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
