import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.task_runtime import TaskStopped
from src.utils import get_video_duration, mux_audio_into_video
from src.video_loop_transition import create_dissolve_loop_playlist


class VideoLoopTransitionTests(unittest.TestCase):
    def test_no_transition_is_prepared_without_a_repeat(self):
        with patch("src.video_loop_transition.run_owned_process") as run:
            playlist = create_dissolve_loop_playlist(
                "clip.mp4", video_duration=5, target_duration=4,
                work_dir="unused", quality_args=[],
            )
        self.assertIsNone(playlist)
        run.assert_not_called()

    def test_default_mux_keeps_legacy_stream_loop_and_skips_transition_render(self):
        with (
            patch("src.utils.run_owned_process") as run,
            patch("src.utils.has_working_h264_qsv", return_value=False),
            patch("src.utils.create_dissolve_loop_playlist") as prepare,
        ):
            mux_audio_into_video("clip.mp4", "music.mp3", "out.mp4", duration=20)
        prepare.assert_not_called()
        final_command = run.call_args.args[0]
        self.assertIn("-stream_loop", final_command)
        self.assertIn("copy", final_command)

    def test_stopped_transition_render_cleans_temporary_files(self):
        folders = []
        def stop(_clip, **kwargs):
            folders.append(Path(kwargs["work_dir"]))
            (folders[0] / "partial.mp4").touch()
            raise TaskStopped()
        with (
            patch("src.utils.run_owned_process"),
            patch("src.utils.has_working_h264_qsv", return_value=False),
            patch("src.utils.get_video_duration", return_value=3),
            patch("src.utils.create_dissolve_loop_playlist", side_effect=stop),
        ):
            with self.assertRaises(TaskStopped):
                mux_audio_into_video(
                    "clip.mp4", "music.mp3", "out.mp4", duration=20,
                    loop_transition=True,
                )
        self.assertEqual(len(folders), 1)
        self.assertFalse(folders[0].exists())


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "Requires FFmpeg")
class RealDissolveLoopTests(unittest.TestCase):
    @staticmethod
    def media(*args):
        return subprocess.run(
            list(args), check=True, capture_output=True,
        )

    def create_inputs(self, folder, *, fps="30", clip_duration=3, music_duration=8.5):
        video, audio = folder / "video.mp4", folder / "music.mp3"
        # The head is red; the tail is blue. Neither contains a black frame.
        self.media(
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
            f"color=red:s=64x64:r={fps}:d={clip_duration / 2}",
            "-f", "lavfi", "-i",
            f"color=blue:s=64x64:r={fps}:d={clip_duration / 2}",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
        )
        self.media(
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
            f"sine=frequency=440:duration={music_duration}",
            "-c:a", "libmp3lame", str(audio),
        )
        return video, audio

    def frames(self, video):
        raw = self.media(
            "ffmpeg", "-v", "error", "-i", str(video), "-an",
            "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
        ).stdout
        return [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]

    def audio_packets(self, path):
        data = self.media(
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_packets", "-show_data_hash", "sha256",
            "-show_entries", "packet=data_hash", "-of", "json", str(path),
        )
        return [entry["data_hash"] for entry in json.loads(data.stdout)["packets"]]

    def render(self, video, audio, output, *, transition):
        with patch("src.utils.has_working_h264_qsv", return_value=False):
            mux_audio_into_video(
                str(video), str(audio), str(output),
                duration=get_video_duration(audio), loop_transition=transition,
            )

    def test_all_joins_dissolve_without_black_ends_and_music_is_unchanged(self):
        with tempfile.TemporaryDirectory(prefix="tuat-transition-test-") as directory:
            folder = Path(directory)
            video, audio = self.create_inputs(folder)
            output = folder / "dissolve.mp4"
            self.render(video, audio, output, transition=True)
            frames = self.frames(output)
            self.assertGreater(len(frames), 240)
            self.assertGreater(frames[0][0], 180)  # Original red head, no fade-in.
            self.assertTrue(all(max(rgb) > 70 for rgb in frames))  # No black frames anywhere.
            # L=3s, dissolve=1s, repeat period=2s: joins at 2..3, 4..5, 6..7, 8..9.
            for time in (2.5, 4.5, 6.5, 8.25):
                r, _g, b = frames[round(time * 30)]
                self.assertGreater(r, 30, (time, r, b))
                self.assertGreater(b, 30, (time, r, b))
            self.assertAlmostEqual(get_video_duration(output), get_video_duration(audio), delta=0.1)
            self.assertEqual(self.audio_packets(output), self.audio_packets(audio))

    def test_default_mode_has_hard_cuts_instead_of_dissolves(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            video, audio = self.create_inputs(folder)
            output = folder / "legacy.mp4"
            self.render(video, audio, output, transition=False)
            r, _g, b = self.frames(output)[75]
            self.assertLess(r, 20)
            self.assertGreater(b, 180)

    def test_short_clip_fractional_fps_and_shorter_audio_have_no_black_edges(self):
        for fps, clip_duration, audio_duration in (("30000/1001", 0.6, 3), ("24", 3, 1)):
            with self.subTest(fps=fps, audio_duration=audio_duration):
                with tempfile.TemporaryDirectory() as directory:
                    folder = Path(directory)
                    video, audio = self.create_inputs(
                        folder, fps=fps, clip_duration=clip_duration, music_duration=audio_duration,
                    )
                    output = folder / "out.mp4"
                    self.render(video, audio, output, transition=True)
                    frames = self.frames(output)
                    self.assertTrue(all(max(rgb) > 70 for rgb in frames))
                    self.assertGreater(frames[0][0], 180)
                    self.assertAlmostEqual(get_video_duration(output), get_video_duration(audio), delta=0.15)


if __name__ == "__main__":
    unittest.main()
