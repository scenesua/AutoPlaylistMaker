"""Shared FFmpeg discovery and MoviePy configuration."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from i18n import t


logger = logging.getLogger(__name__)
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
_lock = threading.Lock()
_cached_path = None
_cached_probe_path = None
_cache_initialized = False


def _is_executable(path):
    if not path:
        return False
    candidate = os.path.abspath(os.path.expanduser(str(path)))
    if not os.path.isfile(candidate):
        return False
    try:
        result = subprocess.run(
            [candidate, "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            creationflags=_NO_WINDOW,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        logger.exception("FFmpeg executable check failed: %s", candidate)
        return False


def _bundled_candidates():
    roots = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent / "_internal")
    names = (
        "ffmpeg.exe" if os.name == "nt" else "ffmpeg",
        "ffmpeg-win-x86_64-v7.1.exe",
    )
    for root in roots:
        for relative in (
            Path("imageio_ffmpeg") / "binaries",
            Path("imageio_ffmpeg") / "binaries" / names[1],
            Path("ffmpeg"),
            Path("."),
        ):
            location = root / relative
            if location.is_file():
                yield str(location)
            elif location.is_dir():
                for name in names:
                    yield str(location / name)
                for match in location.glob("ffmpeg*"):
                    if match.is_file():
                        yield str(match)


def _common_install_candidates():
    if os.name != "nt":
        return []
    return [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Microsoft", "WinGet", "Links", "ffmpeg.exe",
        ),
    ]


def resolve_ffmpeg_executable(force_refresh=False):
    """Return a verified FFmpeg path using one process-wide shared cache."""
    global _cached_path, _cache_initialized
    with _lock:
        if _cache_initialized and not force_refresh:
            return _cached_path

        candidates = []
        candidates.extend(_bundled_candidates())
        candidates.append(os.environ.get("AUTOPLAYLIST_FFMPEG", ""))
        env_binary = os.environ.get("FFMPEG_BINARY", "")
        if env_binary not in ("ffmpeg-imageio", "auto-detect"):
            candidates.append(env_binary)
        candidates.extend((shutil.which("ffmpeg"), shutil.which("ffmpeg.exe")))
        try:
            import imageio_ffmpeg
            candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
        except (ImportError, OSError):
            logger.exception("imageio-ffmpeg discovery failed")
        candidates.extend(_common_install_candidates())

        checked = []
        seen = set()
        for raw_path in candidates:
            if not raw_path:
                continue
            path = os.path.abspath(os.path.expanduser(str(raw_path)))
            normalized = os.path.normcase(path)
            if normalized in seen:
                continue
            seen.add(normalized)
            checked.append(path)
            if _is_executable(path):
                _cached_path = path
                _cache_initialized = True
                os.environ["FFMPEG_BINARY"] = path
                logger.info(
                    "FFmpeg selected: %s; checked=%s", path, checked
                )
                return path

        _cached_path = None
        _cache_initialized = True
        logger.error("FFmpeg not found; checked=%s", checked)
        return None


def ensure_ffmpeg_available(force_refresh=False):
    path = resolve_ffmpeg_executable(force_refresh=force_refresh)
    if not path:
        raise RuntimeError(t("errors.ffmpegNotFound"))
    return path


def resolve_ffprobe_executable():
    """Return FFprobe beside FFmpeg, from PATH, or a common Windows install."""
    global _cached_probe_path
    if _cached_probe_path and _is_executable(_cached_probe_path):
        return _cached_probe_path
    ffmpeg = resolve_ffmpeg_executable()
    candidates = []
    probe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, probe_name))
    if getattr(sys, "frozen", False):
        bundle_root = os.path.dirname(sys.executable)
        candidates.extend((
            os.path.join(bundle_root, probe_name),
            os.path.join(bundle_root, "_internal", probe_name),
        ))
    if ffmpeg:
        candidates.append(os.path.join(
            os.path.dirname(ffmpeg), probe_name,
        ))
    candidates.extend((shutil.which("ffprobe"), shutil.which("ffprobe.exe")))
    if os.name == "nt":
        candidates.extend((
            r"C:\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
        ))
    for candidate in candidates:
        if _is_executable(candidate):
            _cached_probe_path = os.path.abspath(candidate)
            return _cached_probe_path
    return None


def ensure_ffprobe_available():
    path = resolve_ffprobe_executable()
    if not path:
        raise RuntimeError("FFprobe is required to validate rendered output.")
    return path


def configure_moviepy_ffmpeg():
    """Configure all MoviePy FFmpeg entry points from the shared resolver."""
    path = ensure_ffmpeg_available()
    import moviepy.config as moviepy_config
    moviepy_config.FFMPEG_BINARY = path
    try:
        import moviepy.video.io.ffmpeg_writer as writer
        writer.FFMPEG_BINARY = path
    except ImportError:
        logger.exception("MoviePy video writer module unavailable")
    try:
        import moviepy.audio.io.ffmpeg_audiowriter as audio_writer
        audio_writer.FFMPEG_BINARY = path
    except ImportError:
        logger.exception("MoviePy audio writer module unavailable")
    return path
