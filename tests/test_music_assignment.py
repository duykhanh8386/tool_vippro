import random
import unittest
import unicodedata
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


class NameMatchedMusicPlanTests(unittest.TestCase):
    def plan(self, tracks, items):
        return build_balanced_music_plan(
            tracks, items, randomize=True, match_by_name=True
        )

    def test_matches_stems_instead_of_position_with_mixed_extensions(self):
        tracks = [Path("music/b.m4a"), Path("music/a.mp3")]
        items = [{"name": "a.mp4"}, {"name": "B.mov"}]
        self.assertEqual(self.plan(tracks, items), {0: tracks[1], 1: tracks[0]})

    def test_unicode_names_and_case_insensitive_matching(self):
        track = Path("music/Bài Hát.mp3")
        name = unicodedata.normalize("NFD", "BÀI HÁT.MP4")
        self.assertEqual(self.plan([track], [{"name": name}]), {0: track})

    def test_full_stem_is_used_without_prefix_or_substring_matching(self):
        tracks = [Path("music/clip.mp3"), Path("music/clip.2.flac")]
        self.assertEqual(self.plan(tracks, [{"name": "clip.2.mp4"}]), {0: tracks[1]})
        with self.assertRaisesRegex(ValueError, "clip 2.mp4"):
            self.plan(tracks, [{"name": "clip 2.mp4"}])

    def test_missing_track_blocks_batch_and_never_falls_back_to_random(self):
        items = [{"name": "a.mp4"}, {"name": "missing.mp4"}]
        with self.assertRaisesRegex(ValueError, "missing.mp4"):
            self.plan([Path("music/a.mp3")], items)
        self.assertNotIn("music_path", items[0])

    def test_duplicate_stem_blocks_only_videos_with_ambiguous_matches(self):
        tracks = [Path("music/a.mp3"), Path("music/A.wav"), Path("music/b.mp3")]
        with self.assertRaisesRegex(ValueError, "a.mp3, A.wav"):
            self.plan(tracks, [{"name": "a.mp4"}])
        self.assertEqual(self.plan(tracks, [{"name": "b.mp4"}]), {0: tracks[2]})

    def test_completed_merges_keep_saved_music_even_if_source_folder_changed(self):
        saved = Path("old-music/original.mp3")
        items = [
            {"name": "done.mp4", "steps": {"merge": "successful"},
             "music_path": str(saved)},
            {"name": "todo.mp4", "steps": {"merge": "unsuccessful"},
             "music_path": "old-music/wrong.mp3"},
        ]
        track = Path("music/todo.mp3")
        self.assertEqual(self.plan([track], items), {0: saved, 1: track})

    def test_empty_folder_reports_the_video_with_missing_music(self):
        with self.assertRaisesRegex(ValueError, "video.mp4"):
            self.plan([], [{"name": "video.mp4"}])

    def test_matching_can_use_video_path_when_name_is_not_supplied(self):
        track = Path("music/video.ogg")
        self.assertEqual(self.plan([track], [{"path": "videos/video.mkv"}]), {0: track})


if __name__ == "__main__":
    unittest.main()
