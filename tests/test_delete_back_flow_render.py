import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.task_runtime import TaskStopped, bind_run_context, create_run_context
from src.utils import get_video_duration
from web.components.delete_back_flow import (
    ORIGINAL_AUDIO_RENDER_MODE,
    _render_delete_back_output,
)


class DeleteBackFlowRenderTests(unittest.IsolatedAsyncioTestCase):
    async def test_render_uses_original_music_and_its_full_duration(self):
        item = {"path": "video.mp4"}
        music = Path("music") / "bài nhạc gốc.mp3"
        output_folder = str(Path("output"))
        video_out = str(Path(output_folder) / "output_2_processed.mp4")
        run_context = Mock()
        with patch(
            "web.components.delete_back_flow.get_video_duration", return_value=125.5
        ) as duration, patch(
            "web.components.delete_back_flow.mux_audio_into_video"
        ) as mux, patch(
            "web.components.delete_back_flow.current_run_context",
            return_value=run_context,
        ):
            await _render_delete_back_output(item, output_folder, music, 2, "logo.png")

        duration.assert_called_once_with(str(music))
        mux.assert_called_once_with(
            video_file="video.mp4",
            audio_file=str(music),
            video_out=video_out,
            duration=125.5,
            overlay_png="logo.png",
        )
        self.assertEqual(item["audio_path"], str(music))
        self.assertEqual(item["music_path"], str(music))
        self.assertEqual(item["render_audio_mode"], ORIGINAL_AUDIO_RENDER_MODE)
        run_context.register_cleanup_path.assert_called_once_with(video_out)
        run_context.keep_path.assert_called_once_with(video_out)

    async def test_failed_or_stopped_render_never_deletes_source_music(self):
        for error in (RuntimeError("render failed"), TaskStopped()):
            with self.subTest(error=type(error).__name__):
                item = {"path": "video.mp4"}
                run_context = Mock()
                with patch(
                    "web.components.delete_back_flow.get_video_duration",
                    return_value=12.5,
                ), patch(
                    "web.components.delete_back_flow.mux_audio_into_video",
                    side_effect=error,
                ), patch(
                    "web.components.delete_back_flow.current_run_context",
                    return_value=run_context,
                ):
                    with self.assertRaises(type(error)):
                        await _render_delete_back_output(
                            item, "output", Path("music.mp3"), 1, ""
                        )

                run_context.register_cleanup_path.assert_called_once_with(
                    str(Path("output") / "output_1_processed.mp4")
                )
                run_context.keep_path.assert_not_called()
                self.assertNotIn("render_audio_mode", item)

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg integration test"
    )
    async def test_real_mp3_render_preserves_audio_packets_without_silent_gaps(self):
        def run_media(*args):
            return subprocess.run(
                list(args), check=True, capture_output=True, text=True
            )

        def audio_packets(path):
            result = run_media(
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_packets", "-show_data_hash", "sha256",
                "-show_entries", "packet=data_hash", "-of", "json", str(path),
            )
            return [packet["data_hash"] for packet in json.loads(result.stdout)["packets"]]

        with tempfile.TemporaryDirectory() as temporary_dir:
            directory = Path(temporary_dir)
            music = directory / "nhạc gốc.mp3"
            video = directory / "video.mp4"
            run_media(
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                "sine=frequency=440:duration=12", "-c:a", "libmp3lame", str(music),
            )
            run_media(
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                "color=size=64x64:rate=10:duration=1", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", str(video),
            )
            original_hash = hashlib.sha256(music.read_bytes()).hexdigest()
            item = {"path": str(video)}
            run_context = create_run_context("delete_back_render_test")
            try:
                with bind_run_context(run_context), patch(
                    "src.utils.has_working_h264_qsv", return_value=False
                ):
                    await _render_delete_back_output(item, str(directory), music, 1, "")
            finally:
                run_context.cleanup()

            output = Path(item["output_path"])
            self.assertTrue(output.is_file())
            self.assertEqual(hashlib.sha256(music.read_bytes()).hexdigest(), original_hash)
            self.assertEqual(audio_packets(output), audio_packets(music))
            # Video stream-copy may retain a final frame/GOP past the audio end.
            # Packet equality above verifies that the complete MP3 is unchanged.
            self.assertAlmostEqual(
                get_video_duration(output), get_video_duration(music), delta=0.25
            )
            silence = run_media(
                "ffmpeg", "-hide_banner", "-i", str(output), "-map", "0:a:0",
                "-af", "silencedetect=noise=-45dB:d=1", "-f", "null", "-",
            )
            self.assertNotIn("silence_start", silence.stderr)


if __name__ == "__main__":
    unittest.main()
