"""Prepare short reusable Cross Dissolve clips, without fading to black."""

import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path

from src.task_runtime import run_owned_process


def create_dissolve_loop_playlist(
    video_file: str,
    *,
    video_duration: float,
    target_duration: float,
    work_dir: str,
    quality_args: list[str],
) -> Path | None:
    """Encode only the first pass and a seamless repeat unit, then copy-loop.

    The first pass begins at the source's original first frame. Its tail blends
    into the source head. Repeats skip that already-blended head, so subsequent
    joins continue naturally. The final mux simply trims to the audio duration.
    """
    if target_duration <= video_duration:
        return None

    probe = run_owned_process(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate", "-of", "json", video_file,
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    try:
        frame_rate = Fraction(stream.get("avg_frame_rate") or "30")
    except (ValueError, ZeroDivisionError):
        frame_rate = Fraction(30)
    if frame_rate <= 0:
        frame_rate = Fraction(30)

    frame_count = math.floor(video_duration * float(frame_rate) + 1e-6)
    if frame_count < 3:
        raise ValueError("Video quá ngắn để tạo Cross Dissolve (cần ít nhất 3 frame).")

    # Default to one second, shortened for clips too short to support it.
    fade_frames = min(max(1, round(float(frame_rate))), frame_count // 3)
    fade_duration = float(fade_frames / frame_rate)
    first_duration = float(frame_count / frame_rate)
    offset = first_duration - fade_duration
    rate = f"{frame_rate.numerator}/{frame_rate.denominator}"
    time_base = f"{frame_rate.denominator}/{frame_rate.numerator}"
    folder = Path(work_dir)
    first = folder / "first.mp4"
    repeat = folder / "repeat.mp4"
    filters = (
        f"[0:v]fps={rate},trim=end_frame={frame_count},"
        f"settb={time_base},setpts=PTS-STARTPTS,format=yuv420p,split=2[base][head];"
        f"[head]trim=end_frame={fade_frames},setpts=PTS-STARTPTS[headtrim];"
        f"[base][headtrim]xfade=transition=fade:duration={fade_duration:.9f}:"
        f"offset={offset:.9f},trim=end_frame={frame_count},"
        "format=yuv420p,split=2[first][cycle];"
        f"[cycle]trim=start_frame={fade_frames},setpts=PTS-STARTPTS[repeat]"
    )
    encode_args = [
        "-an", "-c:v", "libx264", "-preset", "veryfast", *quality_args,
        "-pix_fmt", "yuv420p", "-r", rate,
        "-video_track_timescale", str(frame_rate.numerator),
    ]
    run_owned_process(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y",
            "-i", video_file, "-filter_complex_threads", "1",
            "-filter_complex", filters,
            "-map", "[first]", *encode_args, str(first),
            "-map", "[repeat]", *encode_args, str(repeat),
        ],
        check=True,
    )

    repeat_duration = first_duration - fade_duration
    repeat_count = max(1, math.ceil((target_duration - first_duration) / repeat_duration))
    playlist = folder / "loop.ffconcat"
    # Relative fixed filenames keep Unicode paths and quotes out of ffconcat.
    with playlist.open("w", encoding="utf-8", newline="\n") as output:
        output.write("ffconcat version 1.0\nfile first.mp4\n")
        output.write(f"duration {first_duration:.9f}\n")
        for _ in range(repeat_count):
            output.write(f"file repeat.mp4\nduration {repeat_duration:.9f}\n")
    return playlist
