"""Inspect YouTube Studio video streams for complete vs intermittent 3s/7s audio."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import math
import shutil
import struct
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlparse

import requests
from loguru import logger

from src.task_runtime import TaskStopped, bind_run_context, check_stopped, current_run_context
from src.utils import get_channels_info

SAMPLE_RATE = 8000
SAMPLE_SECONDS = 25.0
WINDOW_SECONDS = 0.25
SILENCE_DB_THRESHOLD = -65.0
AUDIBLE_DB_THRESHOLD = -50.0
MIN_MUTE_GAP_SECONDS = 4.5
MAX_AUDIBLE_BURST_SECONDS = 5.5
MIN_AUDIBLE_BURST_SECONDS = 0.75
MAX_STREAM_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_WORKERS = 4
STREAM_TIMEOUT_SECONDS = 25.0

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class AudioIntegrityResult:
    status: str  # "complete" | "intermittent" | "silent" | "unreadable"
    reason: str = ""
    silent_gaps: tuple[tuple[float, float], ...] = ()
    sample_seconds: float = 0.0
    audible_ratio: float = 0.0


def analyze_pcm_audio(
    pcm_bytes: bytes,
    *,
    sample_rate: int = SAMPLE_RATE,
    total_duration_seconds: float | None = None,
) -> AudioIntegrityResult:
    """Classify signed 16-bit LE mono PCM into complete/intermittent/silent/unreadable."""
    window_samples = max(1, int(round(sample_rate * WINDOW_SECONDS)))
    window_bytes = window_samples * 2
    window_count = len(pcm_bytes) // window_bytes
    sample_seconds = round(window_count * WINDOW_SECONDS, 4)

    if window_count == 0 or (
        sample_seconds < 3.0 and (total_duration_seconds is None or total_duration_seconds >= 5.0)
    ):
        return AudioIntegrityResult(
            status="unreadable",
            reason="Không đọc đủ dữ liệu âm thanh gốc để kiểm tra.",
            sample_seconds=sample_seconds,
        )

    unpack_fmt = f"<{window_samples}h"
    window_dbs: list[float] = []
    for index in range(window_count):
        start = index * window_bytes
        samples = struct.unpack(unpack_fmt, pcm_bytes[start : start + window_bytes])
        mean_square = sum(sample * sample for sample in samples) / window_samples
        rms = math.sqrt(mean_square) / 32768.0
        window_dbs.append(20.0 * math.log10(rms) if rms > 1e-9 else -120.0)

    audible_count = sum(1 for db in window_dbs if db >= AUDIBLE_DB_THRESHOLD)
    hard_silent_count = sum(1 for db in window_dbs if db <= SILENCE_DB_THRESHOLD)
    audible_ratio = audible_count / window_count

    if audible_count == 0 and (hard_silent_count / window_count) >= 0.95:
        return AudioIntegrityResult(
            status="silent",
            reason="Âm thanh gốc mất tiếng hoàn toàn trong đoạn kiểm tra.",
            silent_gaps=((0.0, sample_seconds),),
            sample_seconds=sample_seconds,
            audible_ratio=0.0,
        )

    if sample_seconds < 10.0:
        return AudioIntegrityResult(
            status="complete",
            sample_seconds=sample_seconds,
            audible_ratio=audible_ratio,
        )

    silent_runs: list[tuple[float, float]] = []
    run_start: int | None = None
    for index, db in enumerate(window_dbs):
        if db <= SILENCE_DB_THRESHOLD:
            if run_start is None:
                run_start = index
        elif run_start is not None:
            silent_runs.append((round(run_start * WINDOW_SECONDS, 4), round(index * WINDOW_SECONDS, 4)))
            run_start = None
    if run_start is not None:
        silent_runs.append((round(run_start * WINDOW_SECONDS, 4), round(window_count * WINDOW_SECONDS, 4)))

    long_gaps = tuple(run for run in silent_runs if (run[1] - run[0]) >= MIN_MUTE_GAP_SECONDS)
    min_audible_windows = max(1, int(math.ceil(MIN_AUDIBLE_BURST_SECONDS / WINDOW_SECONDS)))

    def _has_audible_in_range(start_s: float, end_s: float) -> bool:
        start_idx = max(0, int(round(start_s / WINDOW_SECONDS)))
        end_idx = min(window_count, int(round(end_s / WINDOW_SECONDS)))
        if end_idx <= start_idx:
            return False
        hits = sum(1 for db in window_dbs[start_idx:end_idx] if db >= AUDIBLE_DB_THRESHOLD)
        return hits >= min_audible_windows

    if sample_seconds >= 18.0 and len(long_gaps) >= 2:
        for g1, g2 in zip(long_gaps, long_gaps[1:]):
            burst_span = g2[0] - g1[1]
            if 0.0 < burst_span <= MAX_AUDIBLE_BURST_SECONDS and _has_audible_in_range(g1[1], g2[0]):
                return AudioIntegrityResult(
                    status="intermittent",
                    reason="Phát hiện âm thanh gốc ngắt quãng (kiểu 3s nghe / 7s mất tiếng).",
                    silent_gaps=long_gaps,
                    sample_seconds=sample_seconds,
                    audible_ratio=audible_ratio,
                )

    if 10.0 <= sample_seconds < 18.0 and long_gaps:
        for g_start, g_end in long_gaps:
            if (
                MIN_AUDIBLE_BURST_SECONDS <= g_start <= MAX_AUDIBLE_BURST_SECONDS
                and _has_audible_in_range(0.0, g_start)
                and _has_audible_in_range(g_end, sample_seconds)
            ):
                return AudioIntegrityResult(
                    status="intermittent",
                    reason="Phát hiện âm thanh gốc ngắt quãng (kiểu 3s nghe / 7s mất tiếng).",
                    silent_gaps=long_gaps,
                    sample_seconds=sample_seconds,
                    audible_ratio=audible_ratio,
                )

    return AudioIntegrityResult(
        status="complete",
        silent_gaps=long_gaps,
        sample_seconds=sample_seconds,
        audible_ratio=audible_ratio,
    )


def _is_allowed_youtube_media_url(url: str) -> bool:
    parsed = urlparse(str(url or "").strip())
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (
        host == "youtube.com"
        or host.endswith(".youtube.com")
        or host == "googlevideo.com"
        or host.endswith(".googlevideo.com")
    )


def _build_channel_media_session(channel_info) -> tuple[requests.Session, dict[str, str]]:
    session = requests.Session()
    for cookie in getattr(channel_info, "cookies", None) or []:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "").strip()
        value = cookie.get("value")
        if not name or value is None:
            continue
        domain = str(cookie.get("domain") or "").lstrip(".").lower()
        if domain and not (domain == "youtube.com" or domain.endswith(".youtube.com")):
            continue
        session.cookies.set(name, str(value), domain=".youtube.com", path="/")

    studio_context = getattr(channel_info, "studio_context", None) or {}
    client = studio_context.get("client") if isinstance(studio_context, dict) else {}
    user_agent = (client.get("userAgent") if isinstance(client, dict) else None) or _DEFAULT_USER_AGENT
    headers = {
        "User-Agent": str(user_agent),
        "Referer": "https://studio.youtube.com/",
        "Origin": "https://studio.youtube.com",
    }
    return session, headers


def _ensure_ffmpeg_available() -> str:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise ValueError("Không tìm thấy FFmpeg để kiểm tra âm thanh gốc của video.")
    return ffmpeg_bin


def _validate_media_url(stream_url: str, *, allow_local_http: bool = False) -> None:
    if _is_allowed_youtube_media_url(stream_url):
        return
    if allow_local_http:
        parsed = urlparse(str(stream_url or "").strip())
        if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}:
            return
    raise ValueError("URL luồng phát video không hợp lệ để kiểm tra âm thanh gốc.")


def decode_audio_sample_from_stream(
    stream_url: str,
    *,
    session: requests.Session,
    headers: dict[str, str],
    sample_seconds: float = SAMPLE_SECONDS,
    sample_rate: int = SAMPLE_RATE,
    max_bytes: int = MAX_STREAM_BYTES,
    timeout: float = STREAM_TIMEOUT_SECONDS,
    allow_local_http: bool = False,
) -> bytes:
    check_stopped()
    _validate_media_url(stream_url, allow_local_http=allow_local_http)
    ffmpeg_bin = _ensure_ffmpeg_available()
    run_context = current_run_context()

    with session.get(stream_url, headers=headers, stream=True, timeout=(15, timeout)) as resp:
        if resp.status_code not in (200, 206):
            raise RuntimeError(f"Luồng phát trả về HTTP {resp.status_code}.")

        proc = subprocess.Popen(
            [
                ffmpeg_bin,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-vn",
                "-t",
                f"{sample_seconds:g}",
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-f",
                "s16le",
                "pipe:1",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if run_context is not None:
            run_context.register_process(proc)

        timed_out = [False]

        def abort():
            timed_out[0] = True
            try:
                resp.close()
            except Exception:
                pass
            try:
                proc.terminate()
            except OSError:
                pass

        timer = threading.Timer(timeout, abort)
        timer.daemon = True
        timer.start()

        stderr_chunks: list[bytes] = []

        def drain_stderr():
            try:
                while True:
                    chunk = proc.stderr.read(4096)
                    if not chunk:
                        break
                    stderr_chunks.append(chunk)
            except OSError:
                pass

        def feed_stdin():
            bytes_sent = 0
            try:
                for chunk in resp.iter_content(65536):
                    if not chunk or proc.poll() is not None:
                        break
                    if run_context is not None and run_context.stopped:
                        break
                    proc.stdin.write(chunk)
                    bytes_sent += len(chunk)
                    if bytes_sent >= max_bytes:
                        break
            except (BrokenPipeError, OSError, ValueError):
                pass
            finally:
                try:
                    proc.stdin.close()
                except OSError:
                    pass

        stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        feeder_thread = threading.Thread(target=feed_stdin, daemon=True)
        stderr_thread.start()
        feeder_thread.start()

        try:
            pcm = proc.stdout.read()
            proc.wait(timeout=5)
        finally:
            timer.cancel()
            try:
                resp.close()
            except Exception:
                pass
            if run_context is not None:
                run_context.unregister_process(proc)
            feeder_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
            for stream in (proc.stdout, proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass

    check_stopped()
    if timed_out[0]:
        raise RuntimeError("Hết thời gian chờ khi đọc luồng âm thanh gốc.")
    if proc.returncode != 0 and not pcm:
        raise RuntimeError(f"FFmpeg trả về mã lỗi {proc.returncode} khi giải mã âm thanh.")
    return pcm


def decode_audio_sample_from_file(
    path: str | Path,
    *,
    sample_seconds: float = SAMPLE_SECONDS,
    sample_rate: int = SAMPLE_RATE,
    timeout: float = STREAM_TIMEOUT_SECONDS,
) -> bytes:
    check_stopped()
    ffmpeg_bin = _ensure_ffmpeg_available()
    run_context = current_run_context()
    proc = subprocess.Popen(
        [
            ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vn",
            "-t",
            f"{sample_seconds:g}",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if run_context is not None:
        run_context.register_process(proc)
    try:
        pcm, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        try:
            proc.kill()
        except OSError:
            pass
        raise RuntimeError("Hết thời gian chờ khi giải mã file âm thanh.") from exc
    finally:
        if run_context is not None:
            run_context.unregister_process(proc)
    check_stopped()
    if proc.returncode != 0 and not pcm:
        raise RuntimeError(f"FFmpeg trả về mã lỗi {proc.returncode} khi giải mã file.")
    return pcm


def inspect_channel_videos_audio(
    channel_id: str,
    videos,
    *,
    on_progress=lambda done, total, video_id: None,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> dict[str, AudioIntegrityResult]:
    target_videos = list(videos)
    if not target_videos:
        return {}
    _ensure_ffmpeg_available()
    channel_info = get_channels_info(channel_id)
    if not channel_info or getattr(channel_info, "id", None) != channel_id:
        raise ValueError("Chưa có phiên đăng nhập đúng kênh để kiểm tra âm thanh gốc.")

    run_context = current_run_context()
    thread_local = threading.local()
    sessions: list[requests.Session] = []
    sessions_lock = threading.Lock()

    def get_worker_session() -> tuple[requests.Session, dict[str, str]]:
        cached = getattr(thread_local, "media", None)
        if cached is None:
            session, headers = _build_channel_media_session(channel_info)
            with sessions_lock:
                sessions.append(session)
            cached = (session, headers)
            thread_local.media = cached
        return cached

    def inspect_one(video) -> AudioIntegrityResult:
        ctx_manager = bind_run_context(run_context) if run_context is not None else None
        if ctx_manager is not None:
            ctx_manager.__enter__()
        try:
            check_stopped()
            stream_url = str(getattr(video, "video_stream_url", "") or "").strip()
            if not stream_url:
                return AudioIntegrityResult(
                    status="unreadable",
                    reason="Video chưa có luồng xem trước để kiểm tra âm thanh gốc.",
                )
            session, headers = get_worker_session()
            pcm = decode_audio_sample_from_stream(
                stream_url,
                session=session,
                headers=headers,
            )
            duration_ms = getattr(video, "duration_ms", 0) or 0
            total_seconds = float(duration_ms) / 1000.0 if duration_ms > 0 else None
            return analyze_pcm_audio(pcm, total_duration_seconds=total_seconds)
        except TaskStopped:
            raise
        except Exception as exc:
            logger.warning(
                "Audio integrity check failed for video={}: {}",
                getattr(video, "id", ""),
                type(exc).__name__,
            )
            return AudioIntegrityResult(
                status="unreadable",
                reason="Chưa đọc được luồng âm thanh gốc của video để kiểm tra.",
            )
        finally:
            if ctx_manager is not None:
                ctx_manager.__exit__(None, None, None)

    results: dict[str, AudioIntegrityResult] = {}
    total = len(target_videos)
    try:
        if total == 1:
            check_stopped()
            video = target_videos[0]
            results[video.id] = inspect_one(video)
            on_progress(1, total, video.id)
            return results

        worker_count = max(1, min(int(max_workers), total))
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            future_map = {pool.submit(inspect_one, video): video for video in target_videos}
            done = 0
            for future in as_completed(future_map):
                check_stopped()
                video = future_map[future]
                results[video.id] = future.result()
                done += 1
                on_progress(done, total, video.id)
        return results
    finally:
        with sessions_lock:
            for session in sessions:
                try:
                    session.close()
                except Exception:
                    pass
