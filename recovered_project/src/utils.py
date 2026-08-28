# RECOVERED: reconstructed from CPython 3.12 bytecode
import json, math, os, re, subprocess, sys, tempfile, time, unicodedata
from pathlib import Path
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from src.module.model import ChannelInfo


def get_video_duration(input_file):
    """Get duration of video file in seconds using ffprobe"""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", input_file]
        result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8")
        data = json.loads(result)
        duration = float(data["format"]["duration"])
        if duration <= 0:
            logger.warning(f"Invalid duration for {input_file}: {duration}")
            return None
        return duration
    except FileNotFoundError:
        logger.error("FFprobe not found. Please install FFmpeg to use video processing features.")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"FFprobe failed for {input_file}: {e}")
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse FFprobe output for {input_file}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting duration for {input_file}: {e}")
        return None


def calculate_total_seconds(iso_duration):
    if not iso_duration:
        logger.error("Video chưa được public!!!")
        return 0
    pattern = re.compile(r"P(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)")
    match = pattern.match(iso_duration)
    if not match:
        return "Invalid ISO 8601 duration format"
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds


pass
pass
def multiply_audio(input_file: str, output_file: str, times: int, extra_minutes=0, video_duration_seconds=None) -> None:
    """
    Super-fast version: no filters, no temp files.
    - Computes total target duration.
    - Uses -stream_loop to repeat input and -t to trim exactly.
    - Tries stream copy first; on failure, re-encodes audio.
    - If video_duration_seconds is provided, trims the final audio to match video duration.
    """
    if times < 1:
        raise ValueError("Times must be >= 1")
    if extra_minutes < 0:
        raise ValueError("Extra minutes must be >= 0")
    src = input_file
    dst = output_file
    dur = get_video_duration(src)
    if dur <= 0:
        raise RuntimeError("Input duration is zero or could not be read.")
    extra_seconds = extra_minutes * 60
    if video_duration_seconds is not None and video_duration_seconds > 0:
        total_seconds = video_duration_seconds
    else:
        total_seconds = times * (dur + extra_seconds)
    needed_copies = math.ceil(total_seconds / dur)
    stream_loop = max(0, needed_copies - 1)
    base_cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y", "-stream_loop", str(stream_loop), "-i", src, "-t", f"{total_seconds:.6f}"]
    try:
        cmd_copy = base_cmd + ["-c", "copy", dst]
        subprocess.run(cmd_copy, check=True)
        return
    except subprocess.CalledProcessError:
        pass
    cmd_reencode = base_cmd + ["-c:a", "libmp3lame", "-q:a", "2", dst]
    subprocess.run(cmd_reencode, check=True)


VIDEO_EXTENSIONS = {".avi", ".flv", ".m4v", ".mkv", ".mov", ".webm", ".mp4"}
AUDIO_EXTENSIONS = {".aac", ".m4a", ".ogg", ".flac", ".opus", ".mp3", ".wav"}


def list_media_files(folder: str, extensions: set[str]) -> list[Path]:
    """Return sorted media files (by name) directly inside `folder`."""
    folder_path = Path(normalize_path(folder))
    if not folder_path.exists() or not folder_path.is_dir():
        return []
    files = [
        p
        for p in folder_path.iterdir()
        if p.is_file() and p.suffix.lower() in extensions
    ]
    return sorted(files, key=lambda p: p.name.lower())


pass
pass
def build_intermittent_audio(music_file: str, audio_out: str, play_sec: float = 3.0, mute_sec: float = 7.0) -> float:
    """
    Build a gated (intermittent) audio track spanning the whole music length.

    The music is audible for `play_sec` seconds, silent for `mute_sec` seconds,
    repeating for the whole music length; the final `play_sec` seconds are
    always audible.

    Returns the music duration in seconds (dùng làm thời lượng đích khi mux —
    video gốc sẽ được loop cho bằng thời lượng này).
    """
    dur = get_video_duration(music_file)
    if not dur or dur <= 0:
        raise RuntimeError(f"Could not read music duration: {music_file}")
    cycle = play_sec + mute_sec
    tail_start = max(0.0, dur - play_sec)
    volume_expr = f"if(lt(mod(t,{cycle}),{play_sec}),1,if(gte(t,{tail_start}),1,0))"
    filter_complex = f"[0:a]volume=volume='{volume_expr}':eval=frame[aud]"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y", "-stream_loop", "-1", "-i", music_file,
        "-filter_complex", filter_complex, "-map", "[aud]", "-t", f"{dur:.6f}",
        "-c:a", "aac", "-b:a", "192k", audio_out,
    ]
    subprocess.run(cmd, check=True)
    return dur


pass
pass
pass
def mux_audio_into_video(video_file: str, audio_file: str, video_out: str, duration: float | None = None, video_bitrate: str = "1M", overlay_png: str | None = None) -> None:
    """
    Nén clip gốc 1 lần rồi loop cho bằng `duration` và ghép `audio_file`.

    Vì clip gốc được lặp lại để phủ 2-3 tiếng, dung lượng file (do đó thời gian
    upload) tỉ lệ với bitrate của clip. Ở đây clip ngắn được nén xuống
    `video_bitrate` (giữ nguyên độ phân giải) MỘT lần — rất nhanh vì clip ngắn —
    sau đó loop-copy nên file dài 2-3 tiếng vẫn nhỏ và tạo nhanh.

    Audio thay thế hoàn toàn tiếng gốc.
    """
    dur = duration or get_video_duration(audio_file)
    if not dur or dur <= 0:
        raise RuntimeError(f"Could not determine target duration for {video_file}")
    use_overlay = bool(overlay_png and Path(normalize_path(overlay_png)).is_file())
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        compressed_clip = tf.name
    try:
        compress_cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y", "-i", video_file]
        if use_overlay:
            compress_cmd += ["-loop", "1", "-i", normalize_path(overlay_png)]
            compress_cmd += ["-filter_complex", "[1:v][0:v]scale2ref[ovl][base];[base][ovl]overlay=0:0[outv]", "-map", "[outv]", "-shortest"]
        compress_cmd += [
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-b:v", video_bitrate,
            "-maxrate", "1400k", "-bufsize", "2M", "-pix_fmt", "yuv420p", compressed_clip,
        ]
        subprocess.run(compress_cmd, check=True)
        base_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y", "-stream_loop", "-1", "-i", compressed_clip,
            "-i", audio_file, "-map", "0:v:0", "-map", "1:a:0", "-t", f"{dur:.6f}",
        ]
        try:
            subprocess.run(base_cmd + ["-c:v", "copy", "-c:a", "copy", video_out], check=True)
            return
        except subprocess.CalledProcessError:
            pass
        subprocess.run(base_cmd + ["-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-b:a", "192k", video_out], check=True)
    finally:
        try:
            if Path(compressed_clip).exists():
                Path(compressed_clip).unlink()
        except Exception as exc:
            logger.warning(f"Không xóa được clip tạm {compressed_clip}: {exc}")


pass
def get_channels_info(channel_id: str | None = None) -> list[ChannelInfo] | ChannelInfo | None:
    """
    Retrieve channel info from SQLite database.

    Args:
        channel_id: Specific channel ID to fetch. If None, fetch all channels.

    Returns:
        - list[ChannelInfo]: when channel_id is None (may be empty)
        - ChannelInfo: for a specific channel_id
        - None: if the specific channel doesn't exist
    """
    from src.channel_store import channel_store
    channel_store.init_db()
    if channel_id:
        rec = channel_store.get_channel(channel_id)
        if not rec:
            logger.error("Channel ID '%s' not found in database", channel_id)
            return None
        return ChannelInfo(
            id=rec["id"], name=rec.get("name", ""), img_src=rec.get("img_src", ""),
            sapisidhash=rec.get("sapisidhash", ""), delegated_session_id=rec.get("delegated_session_id", ""),
            cookies=rec.get("cookies", []), cookies_expires_at=rec.get("cookies_expires_at"), role=rec.get("role", ""),
            challenge=rec.get("challenge", ""), botguardResponse=rec.get("botguardResponse", ""),
            overlay_png=rec.get("overlay_png", ""),
        )
    rows = channel_store.list_channels()
    channels = []
    for r in rows:
        if not r.get("id"):
            continue
        channels.append(ChannelInfo(
            id=r["id"], name=r.get("name", ""), img_src=r.get("img_src", ""),
            sapisidhash=r.get("sapisidhash", ""), delegated_session_id=r.get("delegated_session_id", ""),
            cookies=r.get("cookies", []), cookies_expires_at=r.get("cookies_expires_at"), role=r.get("role", ""),
            challenge=r.get("challenge", ""), botguardResponse=r.get("botguardResponse", ""),
            overlay_png=r.get("overlay_png", ""),
        ))
    logger.info(f"Total channels loaded: {len(channels)}")
    return channels


def _bundled_chromedriver() -> Path | None:
    if getattr(sys, "frozen", False):
        candidate = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "tools" / "chromedriver.exe"
    else:
        candidate = Path(__file__).resolve().parent.parent / "vendor" / "chromedriver" / "chromedriver.exe"
    return candidate if candidate.is_file() else None


def _chrome_major_version() -> int | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        locations = (
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Google\Chrome\BLBeacon"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Chrome\BLBeacon"),
        )
        for hive, key_path in locations:
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    version, _ = winreg.QueryValueEx(key, "version")
                return int(str(version).split(".", 1)[0])
            except OSError:
                continue
    except (ImportError, ValueError):
        pass
    return None


def _driver_major_version(driver_path: Path) -> int | None:
    try:
        output = subprocess.check_output(
            [str(driver_path), "--version"], stderr=subprocess.STDOUT, text=True
        )
        match = re.search(r"ChromeDriver\s+(\d+)", output)
        return int(match.group(1)) if match else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


pass
def create_driver(enable_performance_log: bool = False, *, start_offscreen: bool = False):
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--log-level=3")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-notifications")
    if start_offscreen:
        options.add_argument("--no-first-run")
        options.add_argument("--disable-infobars")
        options.add_argument("--window-position=-32000,-32000")
    if enable_performance_log:
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    bundled_driver = _bundled_chromedriver()
    chrome_major = _chrome_major_version()
    driver_major = _driver_major_version(bundled_driver) if bundled_driver else None
    if bundled_driver and (chrome_major is None or driver_major == chrome_major):
        try:
            logger.info("Using bundled ChromeDriver {}", bundled_driver)
            return webdriver.Chrome(service=Service(str(bundled_driver)), options=options)
        except Exception as exc:
            logger.warning("Bundled ChromeDriver failed; trying managed driver: {}", exc)
    elif bundled_driver:
        logger.warning(
            "Bundled ChromeDriver major {} does not match Chrome {}; downloading a compatible driver.",
            driver_major,
            chrome_major,
        )
    try:
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
    except Exception as exc:
        raise RuntimeError(
            "Không thể khởi động ChromeDriver. Hãy cập nhật Chrome hoặc kết nối "
            "Internet để ứng dụng tải driver tương thích."
        ) from exc


def normalize_path(path_text: str) -> str:
    cleaned = unicodedata.normalize("NFC", path_text.strip())
    return "".join(ch for ch in cleaned if unicodedata.category(ch)[0] != "C")


def validate_path_text(path_text: str) -> tuple[(bool, str | None)]:
    """Validate an absolute file path for allowed audio types."""
    if not path_text:
        return False, "Vui lòng nhập đường dẫn tuyệt đối tới file âm thanh"
    path_text = normalize_path(path_text)
    p = Path(path_text)
    if not p.exists() or not p.is_file():
        return False, f"File không tồn tại hoặc không phải là file hợp lệ: {path_text}"
    allowed_extensions = [".mp4", ".wav", ".mp3"]
    if p.suffix.lower() not in allowed_extensions:
        return False, f"Định dạng không hợp lệ. Chỉ chấp nhận {', '.join(allowed_extensions)}"
    return True, None


pass
def get_request_payload_from_performance_log(driver, url_substring: str, timeout: float = 15.0, poll_interval: float = 0.5):
    """
    Đọc performance log của Chrome, tìm request có URL chứa `url_substring`,
    trả về payload (postData) của request đó.

    Returns:
        - str: postData nếu request có body
        - None: nếu request match nhưng không có body (GET/empty)
    Raises:
        - TimeoutError: nếu hết timeout vẫn không thấy request
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for entry in driver.get_log("performance"):
            try:
                msg = json.loads(entry["message"])
                method = msg.get("message", {}).get("method")
                if method != "Network.requestWillBeSent":
                    continue
                params = msg.get("message", {}).get("params", {})
                request = params.get("request", {})
                if url_substring not in request.get("url", ""):
                    continue
                return request.get("postData")
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        time.sleep(poll_interval)
    raise TimeoutError(f"Không tìm thấy request chứa '{url_substring}' sau {timeout}s")
