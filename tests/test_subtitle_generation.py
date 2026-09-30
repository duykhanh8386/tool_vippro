import unittest

from src.subtitle_generation import SubtitleCue, cues_to_srt, repeat_cues_to_duration


class SubtitleGenerationTests(unittest.TestCase):
    def test_repeats_lyrics_to_video_duration_and_clips_last_cue(self):
        cues = (SubtitleCue(1.0, 3.0, "hello"),)

        repeated = repeat_cues_to_duration(
            cues,
            source_duration=5.0,
            target_duration=12.0,
        )

        self.assertEqual(
            repeated,
            (
                SubtitleCue(1.0, 3.0, "hello"),
                SubtitleCue(6.0, 8.0, "hello"),
                SubtitleCue(11.0, 12.0, "hello"),
            ),
        )

    def test_renders_valid_srt_timestamps(self):
        rendered = cues_to_srt(
            (
                SubtitleCue(0.25, 1.5, "First line"),
                SubtitleCue(61.0, 62.125, "Second line"),
            )
        )

        self.assertIn("00:00:00,250 --> 00:00:01,500", rendered)
        self.assertIn("00:01:01,000 --> 00:01:02,125", rendered)
        self.assertTrue(rendered.endswith("\n"))
