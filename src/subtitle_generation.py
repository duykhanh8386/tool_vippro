"""Local lyric transcription and timed subtitle generation.

The heavy speech model is imported lazily so the rest of the application can
start even before the optional model has been installed/downloaded. Generated
source transcripts are cached outside the executable and reused for every
video which uses the same music file.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from loguru import logger

from src.paths import get_data_dir
from src.utils import get_video_duration


DEFAULT_SUBTITLE_MODEL = "small"
_MODEL_CACHE: dict[tuple[str, str, str], object] = {}
_MODEL_LOCK = threading.RLock()


class SubtitleGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SubtitleCue:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class SubtitleTranscript:
    language: str
    source_duration: float
    cues: tuple[SubtitleCue, ...]


def _cache_directory() -> Path:
    path = get_data_dir() / "subtitle_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _audio_fingerprint(audio_path: str | Path, model_name: str) -> str:
    path = Path(audio_path).resolve()
    stat = path.stat()
    digest = hashlib.sha256()
    digest.update(str(path).encode("utf-8", errors="surrogatepass"))
    digest.update(str(stat.st_size).encode("ascii"))
    digest.update(str(stat.st_mtime_ns).encode("ascii"))
    digest.update(model_name.encode("utf-8"))
    # Detect replaced files even when a copier preserves timestamps.
    with path.open("rb") as handle:
        digest.update(handle.read(256 * 1024))
        if stat.st_size > 256 * 1024:
            handle.seek(max(0, stat.st_size - 256 * 1024))
            digest.update(handle.read(256 * 1024))
    return digest.hexdigest()


def _cache_path(audio_path: str | Path, model_name: str) -> Path:
    return _cache_directory() / f"source-{_audio_fingerprint(audio_path, model_name)}.json"


def _load_cached_transcript(path: Path) -> SubtitleTranscript | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cues = tuple(
            SubtitleCue(
                start=max(0.0, float(item["start"])),
                end=max(0.0, float(item["end"])),
                text=str(item["text"]).strip(),
            )
            for item in payload.get("cues") or []
            if isinstance(item, dict) and str(item.get("text") or "").strip()
        )
        if not cues:
            return None
        return SubtitleTranscript(
            language=str(payload.get("language") or "").strip().lower(),
            source_duration=float(payload.get("source_duration") or 0),
            cues=cues,
        )
    except (OSError, ValueError, TypeError, KeyError):
        return None


def _save_cached_transcript(path: Path, transcript: SubtitleTranscript) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {
                "language": transcript.language,
                "source_duration": transcript.source_duration,
                "cues": [asdict(cue) for cue in transcript.cues],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_whisper_model(model_name: str):
    try:
        import ctranslate2  # type: ignore
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:
        raise SubtitleGenerationError(
            "Chưa cài engine tạo phụ đề. Hãy cài lại/cập nhật tool để có "
            "faster-whisper."
        ) from exc

    has_cuda = bool(ctranslate2.get_cuda_device_count())
    device = "cuda" if has_cuda else "cpu"
    compute_type = "float16" if has_cuda else "int8"
    key = (model_name, device, compute_type)
    with _MODEL_LOCK:
        model = _MODEL_CACHE.get(key)
        if model is None:
            logger.info(
                "Loading subtitle transcription model: model={} device={} compute={}",
                model_name,
                device,
                compute_type,
            )
            model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                download_root=str(get_data_dir() / "models" / "faster-whisper"),
            )
            _MODEL_CACHE[key] = model
        return model


def transcribe_lyrics(
    audio_path: str | Path,
    *,
    model_name: str = DEFAULT_SUBTITLE_MODEL,
    language: str | None = None,
) -> SubtitleTranscript:
    """Transcribe one source music file and return timestamped lyric cues."""
    source = Path(audio_path)
    if not source.is_file():
        raise SubtitleGenerationError(f"Không tìm thấy file nhạc: {source}")
    clean_model = str(model_name or DEFAULT_SUBTITLE_MODEL).strip()
    cache_path = _cache_path(source, clean_model)
    cached = _load_cached_transcript(cache_path)
    if cached is not None and (not language or cached.language == language.lower()):
        return cached

    model = _load_whisper_model(clean_model)
    try:
        segments, info = model.transcribe(
            str(source),
            language=(language or None),
            task="transcribe",
            vad_filter=True,
            word_timestamps=True,
            condition_on_previous_text=False,
            beam_size=5,
        )
        cues = []
        for segment in segments:
            text = " ".join(str(getattr(segment, "text", "") or "").split())
            start = max(0.0, float(getattr(segment, "start", 0) or 0))
            end = max(start + 0.05, float(getattr(segment, "end", start) or start))
            if text:
                cues.append(SubtitleCue(start=start, end=end, text=text))
    except Exception as exc:
        raise SubtitleGenerationError(f"Không thể nhận dạng lời bài hát: {exc}") from exc

    if not cues:
        raise SubtitleGenerationError(
            "Không nhận diện được lời hát trong file nhạc. Audio có thể không có "
            "giọng hoặc giọng bị nhạc nền che quá nhiều."
        )
    detected_language = str(getattr(info, "language", "") or language or "").lower()
    if not detected_language:
        raise SubtitleGenerationError("Không xác định được ngôn ngữ lời bài hát.")
    transcript = SubtitleTranscript(
        language=detected_language,
        source_duration=float(get_video_duration(source)),
        cues=tuple(cues),
    )
    _save_cached_transcript(cache_path, transcript)
    return transcript


def repeat_cues_to_duration(
    cues: Iterable[SubtitleCue],
    *,
    source_duration: float,
    target_duration: float,
) -> tuple[SubtitleCue, ...]:
    """Repeat source cues exactly as ``multiply_audio`` repeats the source."""
    source_duration = float(source_duration)
    target_duration = float(target_duration)
    if source_duration <= 0 or target_duration <= 0:
        raise SubtitleGenerationError("Thời lượng audio/video không hợp lệ.")
    source_cues = tuple(cues)
    copies = max(1, math.ceil(target_duration / source_duration))
    repeated: list[SubtitleCue] = []
    for copy_index in range(copies):
        offset = copy_index * source_duration
        for cue in source_cues:
            start = cue.start + offset
            if start >= target_duration:
                break
            end = min(target_duration, cue.end + offset)
            if end > start and cue.text.strip():
                repeated.append(SubtitleCue(start=start, end=end, text=cue.text.strip()))
    return tuple(repeated)


def _format_srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(float(seconds) * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def cues_to_srt(cues: Iterable[SubtitleCue]) -> str:
    blocks = []
    for index, cue in enumerate(cues, 1):
        text = str(cue.text or "").strip()
        if not text or cue.end <= cue.start:
            continue
        blocks.append(
            f"{index}\n{_format_srt_timestamp(cue.start)} --> "
            f"{_format_srt_timestamp(cue.end)}\n{text}"
        )
    if not blocks:
        raise SubtitleGenerationError("Không có câu phụ đề hợp lệ để tạo SRT.")
    return "\n\n".join(blocks) + "\n"


def render_source_srt(
    audio_path: str | Path,
    *,
    target_duration: float,
    model_name: str = DEFAULT_SUBTITLE_MODEL,
) -> tuple[str, str]:
    transcript = transcribe_lyrics(audio_path, model_name=model_name)
    repeated = repeat_cues_to_duration(
        transcript.cues,
        source_duration=transcript.source_duration,
        target_duration=target_duration,
    )
    return transcript.language, cues_to_srt(repeated)


def persist_video_source_srt(
    video_id: str,
    source_language: str,
    srt_text: str,
) -> Path:
    clean_video = "".join(ch for ch in str(video_id) if ch.isalnum() or ch in "-_")
    clean_language = "".join(
        ch for ch in str(source_language) if ch.isalnum() or ch in "-_"
    )
    if not clean_video or not clean_language:
        raise SubtitleGenerationError("Video ID hoặc ngôn ngữ phụ đề không hợp lệ.")
    path = _cache_directory() / f"{clean_video}.{clean_language}.srt"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(srt_text, encoding="utf-8")
    temporary.replace(path)
    return path
