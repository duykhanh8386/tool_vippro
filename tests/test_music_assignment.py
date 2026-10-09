import random
import unittest
from collections import Counter
from pathlib import Path

from src.music_assignment import build_balanced_music_plan


def _items(count: int) -> list[dict]:
    return [{"steps": {"merge": "pending"}} for _ in range(count)]


class BalancedMusicPlanTests(unittest.TestCase):
    def setUp(self):
        self.musics = [Path("music") / name for name in ("a.mp3", "b.mp3", "c.mp3")]

    def test_three_songs_for_six_videos_uses_each_song_twice(self):
        plan = build_balanced_music_plan(
            self.musics,
            _items(6),
            randomize=True,
            rng=random.Random(42),
        )

        self.assertEqual(Counter(plan.values()), Counter({music: 2 for music in self.musics}))

    def test_non_divisible_batch_differs_by_at_most_one(self):
        plan = build_balanced_music_plan(
            self.musics,
            _items(8),
            randomize=True,
            rng=random.Random(7),
        )

        counts = Counter(plan.values())
        self.assertEqual(sum(counts.values()), 8)
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)

    def test_completed_merge_keeps_music_and_pending_items_rebalance(self):
        items = _items(6)
        for index in (0, 1):
            items[index] = {
                "steps": {"merge": "successful"},
                "music": self.musics[0].name,
                "music_path": str(self.musics[0]),
            }

        plan = build_balanced_music_plan(
            self.musics,
            items,
            randomize=True,
            rng=random.Random(1),
        )

        self.assertEqual(plan[0], self.musics[0])
        self.assertEqual(plan[1], self.musics[0])
        self.assertEqual(Counter(plan.values()), Counter({music: 2 for music in self.musics}))

    def test_failed_merge_old_choice_is_not_locked(self):
        items = _items(6)
        for item in items:
            item["music"] = self.musics[0].name
            item["music_path"] = str(self.musics[0])

        plan = build_balanced_music_plan(
            self.musics,
            items,
            randomize=True,
            rng=random.Random(2),
        )

        self.assertEqual(Counter(plan.values()), Counter({music: 2 for music in self.musics}))

    def test_non_random_mode_keeps_round_robin_order(self):
        plan = build_balanced_music_plan(
            self.musics,
            _items(5),
            randomize=False,
        )

        self.assertEqual(
            list(plan.values()),
            [
                self.musics[0],
                self.musics[1],
                self.musics[2],
                self.musics[0],
                self.musics[1],
            ],
        )

    def test_requires_at_least_one_song(self):
        with self.assertRaises(ValueError):
            build_balanced_music_plan([], _items(1), randomize=True)


if __name__ == "__main__":
    unittest.main()
