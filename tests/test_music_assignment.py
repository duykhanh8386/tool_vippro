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

    def test_thai_sara_am_matches_its_visually_equivalent_decomposed_form(self):
        track = Path("music/กำ.mp3")
        self.assertEqual(self.plan([track], [{"name": "ก\u0e4dา.mp4"}]), {0: track})

    def test_thai_sara_am_with_tones_matches_either_combining_order(self):
        for tone in ("\u0e48", "\u0e49", "\u0e4a", "\u0e4b"):
            track = Path(f"music/น{tone}ำ.mp3")
            for stem in (f"น\u0e4d{tone}า", f"น{tone}\u0e4dา"):
                with self.subTest(tone=ord(tone), stem=stem):
                    self.assertEqual(self.plan([track], [{"name": stem + ".mp4"}]), {0: track})

    def test_pasted_thai_titles_ignore_invisible_format_characters(self):
        track = Path("music/เพลงไทย [09BPAunBaEE].mp3")
        video = "\ufeffเพลง\u200bไทย\u200e [09BPAunBaEE]\u2060.mp4"
        self.assertEqual(self.plan([track], [{"name": video}]), {0: track})

    def test_unicode_spaces_and_full_width_separators_are_normalized(self):
        track = Path("music/เพลงไทย | Live.mp3")
        video = "  เพลงไทย\u00a0｜\u2009 Live  .mp4"
        self.assertEqual(self.plan([track], [{"name": video}]), {0: track})

    def test_thai_tones_remain_significant(self):
        track = Path("music/น้ำ.mp3")
        for video in ("นำ.mp4", "น่ำ.mp4"):
            with self.subTest(video=video):
                with self.assertRaises(ValueError):
                    self.plan([track], [{"name": video}])

    def test_normalization_never_strips_vietnamese_accents(self):
        with self.assertRaises(ValueError):
            self.plan([Path("music/ma.mp3")], [{"name": "má.mp4"}])

    def test_normalization_collisions_are_reported_instead_of_picking_a_track(self):
        tracks = [Path("music/น้ำ.mp3"), Path("music/น\u0e4d\u0e49า.wav")]
        with self.assertRaisesRegex(ValueError, "có nhiều file nhạc trùng tên"):
            self.plan(tracks, [{"name": "น้ำ.mp4"}])


if __name__ == "__main__":
    unittest.main()
