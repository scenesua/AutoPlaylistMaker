"""영상 생성 모듈: 사용자 이미지 배경 + 비주얼라이저 + 페이드 효과."""

import sys
import numpy as np
import os
import json
import colorsys
import math
import logging
import subprocess
import threading
from i18n import t, choice_id

CLIP_INTERVAL_CHOICES = {
    "seconds": "clip.seconds",
    "beat": "clip.beat",
    "per_track": "clip.perTrack",
}
import shutil
import copy
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from moviepy import AudioFileClip
from timeline_utils import should_render_visuals, normalize_visibility_settings
from ffmpeg_service import (
    configure_moviepy_ffmpeg,
    resolve_ffmpeg_executable,
)

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
logger = logging.getLogger(__name__)


class RenderCancelledError(RuntimeError):
    """Raised by a progress callback to stop encoding without fallback."""


def _find_ffmpeg_exe():
    """Backward-compatible wrapper for the public FFmpeg resolver."""
    return resolve_ffmpeg_executable()


def _ensure_ffmpeg_for_moviepy():
    """moviepy의 ffmpeg 경로를 올바른 값으로 강제 설정."""
    try:
        ffmpeg_path = configure_moviepy_ffmpeg()
        _log_lines = [f"_find_ffmpeg_exe -> {ffmpeg_path!r}"]
        _log_lines.append(f"exists={os.path.isfile(ffmpeg_path)}")
        _log_lines.append(f"moviepy configured: {ffmpeg_path}")
        _write_log(_log_lines)
    except Exception as e:
        try:
            _write_log([f"_ensure_ffmpeg_for_moviepy exception: {e}"])
        except Exception:
            pass


def _write_log(lines):
    try:
        if getattr(sys, 'frozen', False):
            log_dir = os.path.dirname(sys.executable)
        else:
            log_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(log_dir, "ffmpeg_debug.log")
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    except Exception:
        try:
            log_path = os.path.join(os.path.expanduser("~"), "ffmpeg_debug.log")
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
        except Exception:
            pass


def _detect_gpu_encoder():
    """시스템에 GPU 하드웨어 인코더가 있는지 감지하고 코덱 이름 반환.
    없으면 'libx264' (CPU 소프트웨어 인코딩)을 반환한다."""
    def _check(ffmpeg_exe):
        result = subprocess.run(
            [ffmpeg_exe, '-encoders'], capture_output=True, text=True, timeout=10,
            creationflags=_NO_WINDOW,
        )
        encoders = result.stdout
        if 'h264_nvenc' in encoders:
            return 'h264_nvenc'
        if 'h264_qsv' in encoders:
            return 'h264_qsv'
        if 'h264_vaapi' in encoders:
            return 'h264_vaapi'
        if 'h264_amf' in encoders:
            return 'h264_amf'
        return None
    try:
        ffmpeg_exe = resolve_ffmpeg_executable()
        if ffmpeg_exe:
            codec = _check(ffmpeg_exe)
            if codec:
                return codec
    except Exception:
        pass
    try:
        sys_ffmpeg = shutil.which('ffmpeg') or (shutil.which('ffmpeg.exe') if os.name == 'nt' else None)
        if sys_ffmpeg and os.path.isfile(sys_ffmpeg):
            codec = _check(sys_ffmpeg)
            if codec:
                return codec
    except Exception:
        pass
    return 'libx264'


def loop_video_to_duration(input_path, output_path, target_seconds, cancel_event=None):
    """Repeat a completed video up to an exact target duration.

    This uses ffmpeg's native loop path rather than rendering the Python
    visualizer again. The repeated stream is encoded so the final partial loop
    can end exactly at the requested timestamp instead of a keyframe boundary.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(t("video.loopFileNotFound", path=input_path))
    if target_seconds <= 0:
        raise ValueError(t("video.loopDurationError"))
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError(t("video.loopOutputError"))

    ffmpeg_exe = resolve_ffmpeg_executable()
    if not ffmpeg_exe:
        raise RuntimeError(t("video.ffmpegNotFound"))

    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)
    temp_output = os.path.join(
        output_dir, f".{os.path.basename(output_path)}.partial.mp4"
    )
    command = [
        ffmpeg_exe, '-hide_banner', '-loglevel', 'error', '-y',
        '-stream_loop', '-1', '-i', os.path.abspath(input_path),
        '-t', f"{float(target_seconds):.3f}",
        '-map', '0:v:0', '-map', '0:a?',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-c:a', 'aac', '-b:a', '320k',
        '-movflags', '+faststart',
        temp_output,
    ]
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace',
            creationflags=_NO_WINDOW,
        )
        while process.poll() is None:
            if cancel_event is not None and cancel_event.wait(0.1):
                process.terminate()
                process.wait(timeout=5)
                raise RuntimeError(t("video.userCancelled"))
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            detail = (stderr or stdout or t("video.unknownError")).strip()
            raise RuntimeError(t("video.loopFailed", detail=detail))
        os.replace(temp_output, output_path)
    finally:
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except OSError:
                pass

    return output_path


def loop_video_repetitions(
    input_path, output_path, repeat_count, cancel_event=None,
):
    """Repeat a completed video by whole-playlist units without truncation."""
    if not os.path.isfile(input_path):
        raise FileNotFoundError(t("video.loopFileNotFound", path=input_path))
    count = int(repeat_count)
    if count < 1:
        raise ValueError(t("video.repeatCountError"))
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError(t("video.loopOutputError"))

    ffmpeg_exe = resolve_ffmpeg_executable()
    if not ffmpeg_exe:
        raise RuntimeError(t("video.ffmpegNotFound"))
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_output = os.path.join(
        os.path.dirname(os.path.abspath(output_path)),
        f".{os.path.basename(output_path)}.partial.mp4",
    )
    command = [
        ffmpeg_exe, '-hide_banner', '-loglevel', 'error', '-y',
        '-stream_loop', str(count - 1), '-i', os.path.abspath(input_path),
        '-map', '0:v:0', '-map', '0:a?', '-c', 'copy',
        '-movflags', '+faststart', temp_output,
    ]
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace',
            creationflags=_NO_WINDOW,
        )
        while process.poll() is None:
            if cancel_event is not None and cancel_event.wait(0.1):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise RuntimeError(t("video.userCancelled"))
        stdout, stderr = process.communicate()
        if process.returncode:
            detail = (stderr or stdout or t("video.unknownError")).strip()
            raise RuntimeError(t("video.loopFailed", detail=detail))
        os.replace(temp_output, output_path)
    finally:
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except OSError:
                pass
    return output_path


def apply_visibility_window(
    input_path, output_path, total_duration, settings,
    cancel_event=None, video_codec="libx264",
):
    """Apply one black interval against the final, possibly repeated timeline."""
    vis = normalize_visibility_settings(settings)
    if not vis["enabled"] or vis["turn_off_after"] >= total_duration:
        shutil.copy2(input_path, output_path)
        return output_path
    black_start = vis["turn_off_after"]
    black_end = (
        total_duration - vis["restore_before_end"]
        if vis["restore"] else total_duration
    )
    if black_end <= black_start:
        shutil.copy2(input_path, output_path)
        return output_path
    color = str(vis.get("black_color", "#000000")).replace("#", "0x")
    enable = f"between(t\\,{black_start:.6f}\\,{black_end:.6f})"
    command = [
        resolve_ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-y",
        "-i", input_path, "-vf",
        f"drawbox=x=0:y=0:w=iw:h=ih:color={color}:t=fill:enable='{enable}'",
        "-c:v", video_codec if video_codec != "auto" else "libx264",
        "-c:a", "copy", output_path,
    ]
    process = subprocess.Popen(
        command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        creationflags=_NO_WINDOW,
    )
    while process.poll() is None:
        if cancel_event is not None and cancel_event.is_set():
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            process.communicate()
            raise RenderCancelledError(t("render.cancelled"))
        if cancel_event is not None:
            cancel_event.wait(0.05)
        else:
            process.wait()
    _, stderr_bytes = process.communicate()
    stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else ""
    if process.returncode:
        raise RuntimeError(stderr or "FFmpeg visibility filter failed")
    return output_path


FONT_PATH = None
_font_search = [
    "C:/Windows/Fonts/D2Coding-Ver1.3.2-20180524-all.ttc",
    "C:/Windows/Fonts/D2Coding.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/msyh.ttc",
]
for _fp in _font_search:
    if os.path.isfile(_fp):
        FONT_PATH = _fp
        break


DEFAULT_CONFIG = {
    "layout": {
        "version": 2, "reference_width": 1920, "reference_height": 1080,
    },
    "background": {
        "image": None, "opacity": 1.0, "blur": 0,
        "darken": 0.0, "fit": "cover",
    },
    "overlays": {
        "album": {
            "image": None, "x": 80, "y": 80, "width": 360,
            "opacity": 1.0, "corner_radius": 0,
        },
        "logo": {
            "image": None, "x": 1660, "y": 60, "width": 180,
            "opacity": 1.0, "corner_radius": 0,
        },
    },
    "visualizer": {
        "type": "eq_bars", "position": "bottom", "color": "#6f8cff",
        "opacity": 0.9, "bar_count": 48, "height": 104,
        "smoothing": 0.3, "mirror": False, "gradient": True,
        "bar_width": 0, "bar_gap": 4, "min_height": 2,
        "sensitivity": 1.0, "corner_radius": 4, "glow": 3,
        "decay": 0.82,
        "line_width": 2,
        "x": 0, "y": 0, "width": 0, "height_override": 0,
    },
    "text": {
        "show_title": True, "show_bpm": True, "show_key": True,
        "show_camelot": False, "show_time": True, "position": "center",
        "font_size": 42, "sub_font_size": 28, "color": "#ffffff",
        "align": "center", "x": 0.5, "y": 0.5,
        "bold": False, "italic": False, "underline": False,
        "shadow": True, "shadow_color": "#000000", "shadow_offset": 3,
        "custom_text": "",
        "custom_x": 0.5, "custom_y": 0.3,
        "custom_font_size": 36,
        "custom_bold": False, "custom_italic": False, "custom_underline": False,
        "custom_color": "#ffffff",
        "custom_affects_by_effects": True,
        "custom_opacity": 1.0,
        "custom_outline_width": 0,
        "custom_outline_color": "#000000",
        "custom_background": False,
        "custom_background_color": "#000000",
        "custom_background_opacity": 0.5,
        "custom_background_padding": 12,
        "custom_start_seconds": 0.0,
        "custom_end_seconds": 0.0,
        "custom_target_track": 0,
    },
    "progress_bar": {
        "show": True, "position": "bottom", "height": 4,
        "color": "#ffffff", "background_color": "#333333", "margin": 30,
    },
    "fade": {"fade_in_duration": 2.0, "fade_out_duration": 3.0},
    "visibility": {
        "enabled": False, "turn_off_after": 0.0,
        "restore_before_end": 0.0, "restore": False,
        "black_color": "#000000",
    },
}

SUPPORTED_EFFECT_IDS = frozenset({
    "global_audio", "scene_transition", "background", "album", "logo",
    "track_info", "custom_text", "visualizer", "ambience_mixer", "fade",
    "beat", "crt", "visibility",
})


def validate_effect_plan(config):
    unknown = sorted(
        set(config.get("active_effects", ())) - SUPPORTED_EFFECT_IDS
    )
    if unknown:
        raise ValueError("Unsupported active effect(s): " + ", ".join(unknown))
    return config


def scale_visual_config(config_dict, width, height):
    """Map reference-space settings to one render target exactly once.

    Project values remain in the 1920x1080 logical space. Normalized text
    anchors are deliberately untouched; only pixel-valued properties are
    transformed for the target frame.
    """
    config = merge_visual_config(config_dict)
    layout = config.get("layout", {})
    ref_w = max(1.0, float(layout.get("reference_width", 1920) or 1920))
    ref_h = max(1.0, float(layout.get("reference_height", 1080) or 1080))
    sx, sy = float(width) / ref_w, float(height) / ref_h
    uniform = min(sx, sy)

    def scaled(section, key, factor, minimum=0):
        values = config.get(section, {})
        if key in values:
            value = float(values[key]) * factor
            values[key] = max(minimum, int(round(value)))

    scaled("background", "blur", uniform)
    for overlay in config.get("overlays", {}).values():
        for key, factor in (("x", sx), ("y", sy), ("width", uniform),
                            ("corner_radius", uniform)):
            if key in overlay:
                overlay[key] = max(0, int(round(float(overlay[key]) * factor)))
    for key, factor in (
        ("x", sx), ("y", sy), ("width", uniform), ("height", uniform),
        ("height_override", uniform), ("bar_width", uniform),
        ("bar_gap", uniform), ("min_height", uniform),
        ("corner_radius", uniform), ("glow", uniform),
        ("line_width", uniform),
    ):
        scaled("visualizer", key, factor)
    for key in (
        "font_size", "sub_font_size", "custom_font_size", "shadow_offset",
        "custom_outline_width", "custom_background_padding",
    ):
        scaled("text", key, uniform, 1)
    for key in ("height", "margin"):
        scaled("progress_bar", key, uniform, 1)
    config["_layout_scale"] = uniform
    return config


def load_visual_config(config_path=None):
    config = copy.deepcopy(DEFAULT_CONFIG)
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
        for section, values in user_config.items():
            if section.startswith('_'):
                continue
            if section in config and isinstance(config[section], dict):
                config[section].update({k: v for k, v in values.items() if not k.startswith('_')})
            else:
                config[section] = values
    return config


def merge_visual_config(config_dict=None):
    config = copy.deepcopy(DEFAULT_CONFIG)
    for section, values in (config_dict or {}).items():
        if section.startswith('_'):
            continue
        if section in config and isinstance(config[section], dict) and isinstance(values, dict):
            config[section].update({
                key: copy.deepcopy(value) for key, value in values.items()
                if not key.startswith('_')
            })
        else:
            config[section] = copy.deepcopy(values)
    return config


def hex_to_rgb(hex_color, fallback=(255, 255, 255)):
    value = str(hex_color or "").lstrip("#")
    if len(value) != 6:
        return fallback
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback


_FONT_FILE_CACHE = None


def _system_font_files():
    """Map normalized family names to font files once per process."""
    global _FONT_FILE_CACHE
    if _FONT_FILE_CACHE is not None:
        return _FONT_FILE_CACHE
    mapping = {}
    directories = [
        os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts'),
        os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'Microsoft', 'Windows', 'Fonts',
        ),
    ]
    for directory in directories:
        if not directory or not os.path.isdir(directory):
            continue
        for filename in os.listdir(directory):
            if os.path.splitext(filename)[1].lower() not in (
                '.ttf', '.ttc', '.otf'
            ):
                continue
            path = os.path.join(directory, filename)
            stem = os.path.splitext(filename)[0]
            mapping.setdefault(stem.casefold(), path)
            try:
                from fontTools.ttLib import TTFont
                font = TTFont(path, fontNumber=0, lazy=True)
                for record in font['name'].names:
                    if record.nameID not in (1, 4, 6):
                        continue
                    try:
                        name = record.toUnicode().strip()
                    except Exception:
                        continue
                    if name:
                        mapping.setdefault(name.casefold(), path)
                font.close()
            except Exception:
                continue
    if sys.platform == 'win32':
        try:
            import winreg
            for hive, key_name in (
                (
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
                ),
                (
                    winreg.HKEY_CURRENT_USER,
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
                ),
            ):
                try:
                    key = winreg.OpenKey(hive, key_name)
                except OSError:
                    continue
                index = 0
                while True:
                    try:
                        display_name, filename, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    index += 1
                    family = display_name.split(' (')[0].strip()
                    if not os.path.isabs(filename):
                        candidate_dirs = directories
                    else:
                        candidate_dirs = ('',)
                    for directory in candidate_dirs:
                        path = os.path.join(directory, filename)
                        if os.path.isfile(path):
                            mapping.setdefault(family.casefold(), path)
                            break
                winreg.CloseKey(key)
        except (ImportError, OSError):
            pass
    _FONT_FILE_CACHE = mapping
    return mapping


def get_font(size, family=None):
    import sys as _sys

    if family:
        try:
            return ImageFont.truetype(family, size)
        except (OSError, IOError):
            normalized = str(family).strip().casefold()
            mapping = _system_font_files()
            path = mapping.get(normalized)
            if path is None:
                path = next(
                    (
                        value for name, value in mapping.items()
                        if normalized in name or name in normalized
                    ),
                    None,
                )
            if path:
                try:
                    return ImageFont.truetype(path, size)
                except (OSError, IOError):
                    pass

    local_appdata = _sys.platform == 'win32' and _sys.modules.get('os').environ.get('LOCALAPPDATA', '')
    paths = [
        os.path.join(local_appdata, 'Microsoft', 'Windows', 'Fonts', 'D2Coding-Ver1.3.2-20180524-all.ttc') if local_appdata else '',
        "C:/Windows/Fonts/D2Coding-Ver1.3.2-20180524-all.ttc",
        "C:/Windows/Fonts/D2Coding.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        if not p:
            continue
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def load_background_image(image_path, width, height, fit='cover'):
    img = Image.open(image_path).convert('RGB')
    img_ratio = img.width / img.height
    target_ratio = width / height
    if fit == 'contain':
        if img_ratio > target_ratio:
            new_w = width
            new_h = int(width / img_ratio)
        else:
            new_h = height
            new_w = int(height * img_ratio)
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new('RGB', (width, height), (0, 0, 0))
        canvas.paste(resized, ((width - new_w) // 2, (height - new_h) // 2))
        return canvas
    if img_ratio > target_ratio:
        new_h = height
        new_w = int(height * img_ratio)
    else:
        new_w = width
        new_h = int(width / img_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    img = img.crop((left, top, left + width, top + height))
    return img


def create_gradient_bg(width, height, key, mode):
    key_hues = {
        'C': 0.0, 'C#': 0.083, 'D': 0.167, 'D#': 0.25,
        'E': 0.333, 'F': 0.417, 'F#': 0.5, 'G': 0.583,
        'G#': 0.667, 'A': 0.75, 'A#': 0.833, 'B': 0.917,
    }
    hue = key_hues.get(key, 0.5)
    if mode == 'minor':
        hue = (hue + 0.05) % 1.0
    r1, g1, b1 = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.5, 0.35)]
    r2, g2, b2 = [int(c * 255) for c in colorsys.hsv_to_rgb((hue + 0.25) % 1.0, 0.35, 0.12)]
    t = np.linspace(0, 1, height, dtype=np.float32)[:, np.newaxis]
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    arr[:, :, 0] = np.clip(r1 + (r2 - r1) * t, 0, 255).astype(np.uint8)
    arr[:, :, 1] = np.clip(g1 + (g2 - g1) * t, 0, 255).astype(np.uint8)
    arr[:, :, 2] = np.clip(b1 + (b2 - b1) * t, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def prepare_background(width, height, config, key='C', mode='major'):
    bg_cfg = config['background']
    if bg_cfg['image'] and os.path.exists(bg_cfg['image']):
        bg = load_background_image(
            bg_cfg['image'], width, height, bg_cfg.get('fit', 'cover')
        )
    else:
        bg = create_gradient_bg(width, height, key, mode)

    if bg_cfg.get('darken', 0) > 0:
        dark = Image.new('RGB', (width, height), (0, 0, 0))
        alpha = bg_cfg['darken']
        bg = Image.blend(bg, dark, alpha)

    if bg_cfg.get('blur', 0) > 0:
        bg = bg.filter(ImageFilter.GaussianBlur(radius=bg_cfg['blur']))

    return bg


def paste_image_overlay(base, settings):
    path = settings.get('image')
    if not path or not os.path.isfile(path):
        return
    try:
        overlay = Image.open(path).convert('RGBA')
        target_width = max(1, int(settings.get('width', overlay.width)))
        target_height = max(
            1, round(overlay.height * target_width / max(overlay.width, 1))
        )
        overlay = overlay.resize(
            (target_width, target_height), Image.Resampling.LANCZOS
        )
        radius = max(0, int(settings.get('corner_radius', 0)))
        if radius:
            mask = Image.new('L', overlay.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, overlay.width - 1, overlay.height - 1),
                radius=min(radius, min(overlay.size) // 2), fill=255,
            )
            overlay.putalpha(ImageChops.multiply(overlay.getchannel('A'), mask))
        opacity = max(0.0, min(1.0, float(settings.get('opacity', 1.0))))
        if opacity < 1:
            overlay.putalpha(
                overlay.getchannel('A').point(lambda value: int(value * opacity))
            )
        x = max(0, min(
            int(settings.get('x', 0)), max(0, base.width - overlay.width)
        ))
        y = max(0, min(
            int(settings.get('y', 0)), max(0, base.height - overlay.height)
        ))
        base.paste(overlay, (x, y), overlay)
    except (OSError, ValueError):
        return


def track_reference_max(stft_mags, percentile=95):
    """트랙 전체 기준 정규화 값(퍼센타일). 시각화 함수들이 프레임 단위로
    자기 자신의 최댓값에 맞춰 정규화하면 조용한 구간도 항상 풀스케일로
    보이는 문제가 있어, 트랙 전체 기준의 고정값을 한 번 계산해 재사용한다."""
    if stft_mags is None or stft_mags.size == 0:
        return 1e-8
    return float(np.percentile(stft_mags, percentile)) + 1e-8


def get_eq_bars(stft_mags, t, sr, hop_length, n_bars, bar_height, width,
                color_rgb, smoothing, prev_vals=None, track_max=None,
                bar_width_override=0, gap=2, min_height=1,
                sensitivity=1.0, opacity=0.85, corner_radius=0,
                decay=None, mirror=False):
    frame_idx = int(t * sr / hop_length)
    frame_idx = min(frame_idx, stft_mags.shape[1] - 1)
    frame_idx = max(0, frame_idx)

    n_bins = stft_mags.shape[0]
    bins_per_bar = max(1, n_bins // n_bars)

    bars = np.zeros(n_bars)
    for i in range(n_bars):
        start_bin = i * bins_per_bar
        end_bin = min((i + 1) * bins_per_bar, n_bins)
        bars[i] = np.mean(stft_mags[start_bin:end_bin, frame_idx])

    max_val = track_max if track_max is not None else (np.max(bars) + 1e-8)
    bars = bars / max_val
    bars = np.clip(bars * max(0.01, sensitivity), 0, 1)

    if prev_vals is not None and smoothing > 0:
        if decay is None:
            bars = prev_vals * smoothing + bars * (1 - smoothing)
        else:
            rising = bars >= prev_vals
            attack_values = prev_vals * smoothing + bars * (1 - smoothing)
            release_values = prev_vals * decay + bars * (1 - decay)
            bars = np.where(rising, attack_values, release_values)
    if mirror and len(bars) > 1:
        bars = (bars + bars[::-1]) * 0.5

    gap = max(0, int(gap))
    bar_width = (
        max(1, int(bar_width_override))
        if bar_width_override
        else max(1, (width - 40) // n_bars - gap)
    )
    total_width = n_bars * (bar_width + gap)
    start_x = (width - total_width) // 2

    img = Image.new('RGBA', (width, bar_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for i in range(n_bars):
        h = max(int(min_height), int(bars[i] * bar_height * 0.95))
        if h < 1:
            continue
        x = start_x + i * (bar_width + gap)
        y = bar_height - h
        alpha = int(min(255, (255 * bars[i] * 0.85 + 40) * opacity))
        r, g, b = color_rgb
        box = [x, y, x + bar_width, bar_height]
        if corner_radius:
            draw.rounded_rectangle(
                box, radius=min(int(corner_radius), bar_width // 2),
                fill=(r, g, b, alpha),
            )
        else:
            draw.rectangle(box, fill=(r, g, b, alpha))

    return img, bars


def get_waveform_frame(
    waveform, t, sr, width, height, color_rgb, line_width=2
):
    samples_per_pixel = max(1, len(waveform) // width)
    center_y = height // 2
    half_h = height // 2 - 4

    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    start_sample = int(t * sr)
    n_pixels = min(width, (len(waveform) - start_sample) // samples_per_pixel)
    if n_pixels < 2:
        return img

    indices = np.arange(n_pixels) * samples_per_pixel + start_sample
    chunks = np.array([waveform[s:s + samples_per_pixel] for s in indices])
    vals = np.mean(np.abs(chunks), axis=1)
    y_offsets = np.minimum((vals * half_h * 8).astype(int), half_h)

    xs = np.arange(n_pixels)
    ys_top = center_y - y_offsets
    points_top = list(zip(xs.tolist(), ys_top.tolist(), strict=False))
    r, g, b = color_rgb
    draw.line(
        points_top, fill=(r, g, b, 200), width=max(1, int(line_width))
    )

    ys_bot = center_y + y_offsets
    points_bot = list(zip(xs.tolist(), ys_bot.tolist(), strict=False))
    draw.line(
        points_bot, fill=(r, g, b, 120),
        width=max(1, int(line_width) // 2),
    )

    return img


def get_spectrum_frame(
    stft_mags, t, sr, hop_length, width, height, color_rgb,
    track_max=None, smoothing=0, prev_vals=None,
):
    frame_idx = int(t * sr / hop_length)
    frame_idx = min(frame_idx, stft_mags.shape[1] - 1)
    frame_idx = max(0, frame_idx)

    n_bins = min(stft_mags.shape[0], 256)
    mags = stft_mags[:n_bins, frame_idx]
    max_val = track_max if track_max is not None else (np.max(mags) + 1e-8)
    mags = mags / max_val
    mags = np.clip(mags, 0, 1)
    if prev_vals is not None and len(prev_vals) == len(mags):
        mags = prev_vals * smoothing + mags * (1 - smoothing)

    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))

    bar_w = max(1, width // n_bins)
    r, g, b = color_rgb
    for i in range(n_bins):
        x = i * bar_w
        h = int(mags[i] * height * 0.9)
        if h < 1:
            continue
        alpha = int(100 + 155 * mags[i])
        draw = ImageDraw.Draw(img)
        draw.rectangle([x, height - h, x + bar_w - 1, height], fill=(r, g, b, alpha))

    return img, mags


def get_circles_frame(
    stft_mags, t, sr, hop_length, width, height, color_rgb,
    prev_energy=None, track_max=None, smoothing=0, line_width=2,
):
    frame_idx = int(t * sr / hop_length)
    frame_idx = min(frame_idx, stft_mags.shape[1] - 1)
    frame_idx = max(0, frame_idx)

    n_bands = 8
    n_bins = stft_mags.shape[0]
    bins_per = n_bins // n_bands
    energies = np.zeros(n_bands)
    for i in range(n_bands):
        energies[i] = np.mean(stft_mags[i*bins_per:(i+1)*bins_per, frame_idx])
    max_e = track_max if track_max is not None else (np.max(energies) + 1e-8)
    energies = energies / max_e
    energies = np.clip(energies, 0, 1)
    if prev_energy is not None and len(prev_energy) == len(energies):
        energies = (
            prev_energy * smoothing + energies * (1 - smoothing)
        )

    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = width // 2, height // 2
    r, g, b = color_rgb

    for e in energies:
        radius = int(20 + e * min(width, height) * 0.35)
        alpha = int(60 + 195 * e)
        line_w = max(1, int(line_width + e * line_width))
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=(r, g, b, alpha), width=line_w,
        )

    return img, energies


def get_radial_bars(stft_mags, t, sr, hop_length, n_bars, bar_height, width, height,
                    color_rgb, smoothing, prev_vals=None, track_max=None,
                    line_width=2):
    frame_idx = int(t * sr / hop_length)
    frame_idx = min(frame_idx, stft_mags.shape[1] - 1)
    frame_idx = max(0, frame_idx)

    n_bins = stft_mags.shape[0]
    bins_per_bar = max(1, n_bins // n_bars)
    bars = np.zeros(n_bars)
    for i in range(n_bars):
        s = i * bins_per_bar
        e = min((i + 1) * bins_per_bar, n_bins)
        bars[i] = np.mean(stft_mags[s:e, frame_idx])

    max_val = track_max if track_max is not None else (np.max(bars) + 1e-8)
    bars = bars / max_val
    bars = np.clip(bars, 0, 1)

    if prev_vals is not None and smoothing > 0:
        bars = prev_vals * smoothing + bars * (1 - smoothing)

    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = width // 2, height // 2
    base_r = min(width, height) // 4
    r, g, b = color_rgb

    for i in range(n_bars):
        angle = (2 * np.pi * i / n_bars) - np.pi / 2
        h = int(bars[i] * bar_height * 0.8)
        if h < 2:
            continue
        x1 = cx + int(base_r * np.cos(angle))
        y1 = cy + int(base_r * np.sin(angle))
        x2 = cx + int((base_r + h) * np.cos(angle))
        y2 = cy + int((base_r + h) * np.sin(angle))
        alpha = int(100 + 155 * bars[i])
        draw.line(
            [(x1, y1), (x2, y2)], fill=(r, g, b, alpha),
            width=max(1, int(line_width)),
        )

    return img, bars


def apply_fade(frame_array, t, fade_in, fade_out, total_duration):
    alpha = 1.0
    if fade_in > 0 and t < fade_in:
        alpha = t / fade_in
    if fade_out > 0 and t > total_duration - fade_out:
        alpha = (total_duration - t) / fade_out
    alpha = np.clip(alpha, 0, 1)

    if alpha < 1.0:
        black = np.zeros_like(frame_array, dtype=np.float32)
        frame_array = (frame_array.astype(np.float32) * alpha +
                       black * (1 - alpha)).astype(np.uint8)
    return frame_array


def apply_beat_effects(frame_arr, t, beat_times, effects_cfg, width, height):
    if not effects_cfg.get('bounce') and not effects_cfg.get('shake') and \
       not effects_cfg.get('zoom') and not effects_cfg.get('flash'):
        return frame_arr

    if len(beat_times) == 0:
        return frame_arr

    beat_idx = np.searchsorted(beat_times, t, side='right') - 1
    if beat_idx < 0:
        return frame_arr
    beat_time = beat_times[beat_idx]
    since_beat = t - beat_time

    next_idx = beat_idx + 1
    if next_idx < len(beat_times):
        beat_interval = beat_times[next_idx] - beat_time
    else:
        beat_interval = 60.0 / 120.0

    phase = since_beat / max(beat_interval, 0.001)
    pulse = max(0, 1.0 - phase * 2.5)

    img = Image.fromarray(frame_arr)
    orig_w, orig_h = img.size

    scale = width / 1920.0

    if effects_cfg.get('bounce'):
        intensity = effects_cfg.get('bounce_intensity', 1.03)
        shift = int(pulse * 15 * abs(intensity - 1.0) * 10 * scale)
        if shift > 0:
            img = img.transform((orig_w, orig_h), Image.AFFINE,
                                 (1, 0, 0, 0, 1, -shift), resample=Image.BILINEAR)

    if effects_cfg.get('shake'):
        intensity = effects_cfg.get('shake_intensity', 3)
        shake_x = round(
            math.sin((beat_idx + 1) * 17.17 + phase * 23.0)
            * intensity * pulse * scale
        )
        shake_y = round(
            math.cos((beat_idx + 1) * 11.73 + phase * 19.0)
            * intensity * pulse * scale
        )
        img = img.transform((orig_w, orig_h), Image.AFFINE,
                             (1, 0, shake_x, 0, 1, shake_y), resample=Image.BILINEAR)

    if effects_cfg.get('zoom'):
        intensity = effects_cfg.get('zoom_intensity', 1.05)
        scale_f = 1.0 + pulse * (intensity - 1.0)
        new_w = int(orig_w * scale_f)
        new_h = int(orig_h * scale_f)
        img = img.resize((new_w, new_h), Image.BILINEAR)
        left = (new_w - orig_w) // 2
        top = (new_h - orig_h) // 2
        img = img.crop((left, top, left + orig_w, top + orig_h))

    if effects_cfg.get('flash'):
        intensity = effects_cfg.get('flash_intensity', 0.3)
        if pulse > 0.3:
            flash_alpha = pulse * intensity
            flash = Image.new('RGB', img.size, (255, 255, 255))
            img = Image.blend(img, flash, flash_alpha)

    return np.array(img)


def apply_crt_effect(frame_arr, cfg, width, height):
    if not cfg.get('crt'):
        return frame_arr

    img = Image.fromarray(frame_arr)
    intensity = cfg.get('crt_intensity', 1.0)
    scanlines = cfg.get('crt_scanlines', True)
    curvature = cfg.get('crt_curvature', 0.0)
    chromatic = cfg.get('crt_chromatic', 0.0)
    vignette = cfg.get('crt_vignette', 0.0)
    noise = cfg.get('crt_noise', 0.0)
    flicker = cfg.get('crt_flicker', 0.0)

    scale = width / 1920.0

    if scanlines:
        arr = np.array(img).astype(np.float32)
        gap = max(1, int(2 * intensity * scale))
        dark = 1.0 - 0.15 * intensity
        arr[::gap, :, :] *= dark
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

    if chromatic > 0:
        r, g, b = img.split()[:3]
        shift = int(max(1, chromatic * intensity * 3 * scale))
        r = r.transform(r.size, Image.AFFINE, (1, 0, shift, 0, 1, 0), resample=Image.BILINEAR)
        b = b.transform(b.size, Image.AFFINE, (1, 0, -shift, 0, 1, 0), resample=Image.BILINEAR)
        img = Image.merge('RGB', (r, g, b))

    if curvature > 0:
        c = curvature * intensity * 0.1
        cx, cy = width / 2, height / 2
        xs = np.arange(width, dtype=np.float32)
        ys = np.arange(height, dtype=np.float32)
        nx = (xs - cx) / cx
        ny = (ys - cy) / cy
        nxx, nyy = np.meshgrid(nx, ny)
        r2 = nxx * nxx + nyy * nyy
        factor = 1.0 + c * r2
        map_x = (nxx * cx * factor + cx).clip(0, width - 1)
        map_y = (nyy * cy * factor + cy).clip(0, height - 1)
        from scipy.ndimage import map_coordinates
        arr = np.array(img)
        for ch in range(3):
            arr[:, :, ch] = map_coordinates(arr[:, :, ch].astype(np.float32),
                                            [map_y, map_x], order=1, mode='reflect')
        img = Image.fromarray(arr.astype(np.uint8))

    if vignette > 0:
        cx, cy = width / 2, height / 2
        xs = (np.arange(width, dtype=np.float32) - cx) / cx
        ys = (np.arange(height, dtype=np.float32) - cy) / cy
        nxx, nyy = np.meshgrid(xs, ys)
        dist2 = nxx * nxx + nyy * nyy
        factor = np.clip(dist2 * vignette * intensity, 0, 1)
        arr = np.array(img).astype(np.float32)
        arr *= (1.0 - factor[:, :, np.newaxis])
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    if noise > 0:
        arr = np.array(img).astype(np.float32)
        n = np.random.normal(0, noise * intensity * 25, arr.shape).astype(np.float32)
        arr = np.clip(arr + n, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

    if flicker > 0:
        import random
        brightness = 1.0 + (random.random() - 0.5) * flicker * intensity * 0.1
        arr = np.array(img).astype(np.float32)
        arr = np.clip(arr * brightness, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

    return np.array(img)


def draw_text_with_shadow(draw, pos, text, font, fill, shadow=True, shadow_color=(0,0,0), offset=3):
    x, y = pos
    if shadow:
        draw.text((x + offset, y + offset), text, fill=shadow_color, font=font)
    draw.text((x, y), text, fill=fill, font=font)


def build_custom_text_layer(width, height, cfg, layout_scale=1.0):
    text = str(cfg.get('custom_text', ''))
    if not text:
        return None
    font = get_font(
        int(cfg.get('custom_font_size', 36)),
        cfg.get('custom_font_family'),
    )
    opacity = max(0.0, min(1.0, float(cfg.get('custom_opacity', 1.0))))
    outline = max(0, int(cfg.get('custom_outline_width', 0)))
    padding = max(0, int(cfg.get('custom_background_padding', 12)))
    stroke = outline + (
        max(1, round(layout_scale)) if cfg.get('custom_bold') else 0
    )
    spacing = max(1, round(4 * layout_scale))
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    bbox = probe.multiline_textbbox(
        (0, 0), text, font=font, spacing=spacing, stroke_width=stroke,
    )
    shadow_offset = int(cfg.get('shadow_offset', 3))
    extra = max(0, shadow_offset if cfg.get('shadow') else 0)
    local = Image.new('RGBA', (
        max(1, bbox[2] - bbox[0] + padding * 2 + extra),
        max(1, bbox[3] - bbox[1] + padding * 2 + extra),
    ), (0, 0, 0, 0))
    draw = ImageDraw.Draw(local)
    if cfg.get('custom_background', False):
        color = hex_to_rgb(
            cfg.get('custom_background_color', '#000000'), (0, 0, 0)
        )
        alpha = round(255 * opacity * max(0.0, min(
            1.0, float(cfg.get('custom_background_opacity', 0.5))
        )))
        draw.rectangle((0, 0, local.width - extra, local.height - extra),
                       fill=(*color, alpha))
    origin = (padding - bbox[0], padding - bbox[1])
    if cfg.get('shadow', True):
        shadow = hex_to_rgb(
            cfg.get('shadow_color', '#000000'), (0, 0, 0)
        )
        draw.multiline_text(
            (origin[0] + shadow_offset, origin[1] + shadow_offset), text,
            font=font, spacing=spacing, fill=(*shadow, round(150 * opacity)),
            stroke_width=stroke,
            stroke_fill=(*shadow, round(150 * opacity)),
        )
    color = hex_to_rgb(cfg.get('custom_color', '#ffffff'))
    outline_color = hex_to_rgb(
        cfg.get('custom_outline_color', '#000000'), (0, 0, 0)
    )
    draw.multiline_text(
        origin, text, font=font, spacing=spacing,
        fill=(*color, round(255 * opacity)), stroke_width=stroke,
        stroke_fill=(*outline_color, round(255 * opacity)),
    )
    if cfg.get('custom_underline', False):
        y = min(local.height - 1, origin[1] + bbox[3] - bbox[1] + 2)
        draw.line((origin[0], y, origin[0] + bbox[2] - bbox[0], y),
                  fill=(*color, round(255 * opacity)), width=max(1, stroke))
    if cfg.get('custom_italic', False):
        shear = 0.25
        local = local.transform(
            (local.width + int(local.height * shear), local.height),
            Image.AFFINE,
            (1, -shear, local.height * shear, 0, 1, 0),
            resample=Image.BICUBIC,
        )
    x = int(float(cfg.get('custom_x', 0.5)) * width)
    y = int(float(cfg.get('custom_y', 0.3)) * height)
    paste_x = max(0, min(width - local.width, x - local.width // 2))
    paste_y = max(0, min(height - local.height, y - padding))
    layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    layer.paste(local, (paste_x, paste_y), local)
    return layer


class LiveFrameRenderer:
    """generate_video()의 프레임 렌더링 로직을 재사용 가능하게 분리한 클래스.

    moviepy/ffmpeg 인코딩을 거치지 않고 특정 시간 t의 프레임을 바로
    PIL 이미지로 얻을 수 있어서, GUI의 실시간 미리보기(스크러버)에서
    직접 호출해 쓸 수 있다. generate_video()도 내부적으로 이 클래스를
    사용하므로, 실제 렌더링과 미리보기가 항상 동일한 코드로 동작한다
    (미리보기만 따로 랜덤값으로 근사하던 예전 방식과 달리 로직이 갈라지지 않음).
    """

    def __init__(self, analyses, width, height, total_duration,
                 visual_config_path=None, timestamps=None, crossfade_duration=4.0,
                 config_dict=None):
        self.analyses = analyses
        self.width = width
        self.height = height
        self.total_duration = total_duration

        logical_config = (
            merge_visual_config(config_dict)
            if config_dict is not None
            else load_visual_config(visual_config_path)
        )
        self.config = validate_effect_plan(
            scale_visual_config(logical_config, width, height)
        )
        self.layout_scale = self.config.get('_layout_scale', 1.0)
        timeline = self.config.get('timeline', {})
        self.visibility_timeline_duration = float(
            timeline.get('duration', total_duration) or total_duration
        )
        self.visibility_timeline_offset = float(
            timeline.get('offset', 0.0) or 0.0
        )
        self.vcfg = self.config['visualizer']
        self.tcfg = self.config['text']
        self.pcfg = self.config['progress_bar']
        self.fcfg = self.config['fade']
        self.ecfg = self.config.get('effects', {})

        text_font_family = self.tcfg.get('text_font_family', None)
        styled_family = text_font_family
        if styled_family and self.tcfg.get('bold'):
            styled_family += " Bold"
        if styled_family and self.tcfg.get('italic'):
            styled_family += " Italic"
        self.font_title = get_font(self.tcfg['font_size'], styled_family)
        self.font_sub = get_font(self.tcfg['sub_font_size'], styled_family)
        self.font_time = get_font(max(1, round(22 * self.layout_scale)), text_font_family)

        self.text_color = hex_to_rgb(self.tcfg['color'])
        self.shadow_c = hex_to_rgb(self.tcfg['shadow_color'], (0, 0, 0))
        self.viz_color = hex_to_rgb(
            self.vcfg['color'], (111, 140, 255)
        )
        self.bar_color = hex_to_rgb(self.pcfg['color'])
        self.bar_bg = hex_to_rgb(
            self.pcfg['background_color'], (51, 51, 51)
        )

        self.track_viz_max = [
            track_reference_max(a.stft_magnitudes) for a in analyses
        ]

        self.bg_cache = {
            index: prepare_background(
                width, height, self.config, a.key, a.mode
            )
            for index, a in enumerate(analyses)
        }

        self.track_boundaries = []
        if timestamps and len(timestamps) == len(analyses):
            for index, (a, ts) in enumerate(
                zip(analyses, timestamps, strict=False)
            ):
                self.track_boundaries.append({
                    'start': ts['start_time'], 'end': ts['end_time'],
                    'source_start': float(ts.get('source_start', 0.0)),
                    'analysis': a, 'index': index,
                })
        else:
            current_time = 0
            for i, a in enumerate(analyses):
                track_start = 0 if i == 0 else current_time
                track_end = track_start + a.duration
                current_time = track_end
                if i < len(analyses) - 1:
                    current_time -= crossfade_duration
                self.track_boundaries.append({
                    'start': track_start, 'end': track_end,
                    'source_start': 0.0, 'analysis': a, 'index': i,
                })

        self.beat_time_cache = {}
        for track_index, tb in enumerate(self.track_boundaries):
            a = tb['analysis']
            if a.beat_times is not None and len(a.beat_times) > 0:
                source_start = float(tb.get('source_start', 0.0))
                offsets = [
                    float(bt) - source_start + float(tb['start'])
                    for bt in a.beat_times
                    if float(bt) >= source_start
                    and float(bt) - source_start + float(tb['start'])
                    < float(tb['end'])
                ]
                self.beat_time_cache[track_index] = np.array(offsets)
            else:
                self.beat_time_cache[track_index] = np.array([])
        logger.info(
            "Beat timeline prepared: %s",
            ", ".join(
                f"track {index + 1}={len(beats)}"
                for index, beats in self.beat_time_cache.items()
            ),
        )

        self.smooth_cache = {}
        self._smooth_times = {}
        self.effects_active = any(self.ecfg.get(k) for k in ['bounce', 'shake', 'zoom', 'flash'])
        self.crt_active = self.ecfg.get('crt', False)

        vis = normalize_visibility_settings(self.config.get('visibility', {}))
        self.visibility_enabled = vis.get('enabled', False)
        self.initial_visible = vis['turn_off_after']
        self.ending_visible = vis['restore_before_end']
        self.visibility_restore = vis['restore']
        self.visibility_black = vis['black_color']

        self._clip_images = []
        self._clip_enabled = self.config.get('clip_enabled', False)
        self._clip_interval = self.config.get('clip_interval', 1.0)
        self._clip_interval_unit = choice_id(
            self.config.get('clip_interval_unit', 'seconds'),
            CLIP_INTERVAL_CHOICES,
            'seconds',
        )
        self._clip_random = self.config.get('clip_random', False)
        if self._clip_enabled:
            self._load_clips()
        self._static_cache = {}
        self._bg_only_cache = {}
        self._foreground_cache = {}
        self._build_static_layers()
        self._custom_text_layer = build_custom_text_layer(
            self.width, self.height, self.tcfg, self.layout_scale
        )


    def _load_clips(self):
        clips_data = self.config.get('clips', [])
        self._clip_images = []
        for c in clips_data:
            fp = c.get('filepath', '')
            if not fp or not os.path.isfile(fp):
                continue
            try:
                img = Image.open(fp).convert('RGB')
                img = img.resize((self.width, self.height), Image.LANCZOS)
                self._clip_images.append(img)
            except Exception:
                pass

    def _get_clip_frame(self, t):
        if not self._clip_images:
            return None
        n = len(self._clip_images)
        if self._clip_random:
            import hashlib
            idx = int(hashlib.md5(f"{t:.3f}".encode()).hexdigest(), 16) % n
        else:
            if self._clip_interval_unit == 'beat':
                idx = int(t / max(self._clip_interval, 0.1)) % n
            elif self._clip_interval_unit == 'per_track':
                idx = 0
                for i, tb in enumerate(self.track_boundaries):
                    if tb['start'] <= t < tb['end']:
                        idx = i % n
                        break
            else:
                idx = int(t / max(self._clip_interval, 0.1)) % n
        return self._clip_images[idx]

    def reconfigure(self, config_dict):
        """오디오 믹싱/트랙 경계는 그대로 두고 시각 설정만 다시 적용한다."""
        self.config = validate_effect_plan(
            scale_visual_config(config_dict, self.width, self.height)
        )
        self.layout_scale = self.config.get('_layout_scale', 1.0)
        timeline = self.config.get('timeline', {})
        self.visibility_timeline_duration = float(
            timeline.get('duration', self.total_duration)
            or self.total_duration
        )
        self.visibility_timeline_offset = float(
            timeline.get('offset', 0.0) or 0.0
        )
        self.vcfg = self.config['visualizer']
        self.tcfg = self.config['text']
        self.pcfg = self.config['progress_bar']
        self.fcfg = self.config['fade']
        self.ecfg = self.config.get('effects', {})

        text_font_family = self.tcfg.get('text_font_family', None)
        styled_family = text_font_family
        if styled_family and self.tcfg.get('bold'):
            styled_family += " Bold"
        if styled_family and self.tcfg.get('italic'):
            styled_family += " Italic"
        self.font_title = get_font(self.tcfg['font_size'], styled_family)
        self.font_sub = get_font(self.tcfg['sub_font_size'], styled_family)
        self.font_time = get_font(max(1, round(22 * self.layout_scale)), text_font_family)

        self.text_color = hex_to_rgb(self.tcfg['color'])
        self.shadow_c = hex_to_rgb(self.tcfg['shadow_color'], (0, 0, 0))
        self.viz_color = hex_to_rgb(
            self.vcfg['color'], (111, 140, 255)
        )
        self.bar_color = hex_to_rgb(self.pcfg['color'])
        self.bar_bg = hex_to_rgb(
            self.pcfg['background_color'], (51, 51, 51)
        )

        self.bg_cache = {
            index: prepare_background(
                self.width, self.height, self.config, a.key, a.mode
            )
            for index, a in enumerate(self.analyses)
        }
        self.smooth_cache = {}
        self._smooth_times = {}
        self.effects_active = any(self.ecfg.get(k) for k in ['bounce', 'shake', 'zoom', 'flash'])
        self.crt_active = self.ecfg.get('crt', False)

        vis = normalize_visibility_settings(self.config.get('visibility', {}))
        self.visibility_enabled = vis.get('enabled', False)
        self.initial_visible = vis['turn_off_after']
        self.ending_visible = vis['restore_before_end']
        self.visibility_restore = vis['restore']
        self.visibility_black = vis['black_color']

        self._clip_enabled = self.config.get('clip_enabled', False)
        self._clip_interval = self.config.get('clip_interval', 1.0)
        self._clip_interval_unit = choice_id(
            self.config.get('clip_interval_unit', 'seconds'),
            CLIP_INTERVAL_CHOICES,
            'seconds',
        )
        self._clip_random = self.config.get('clip_random', False)
        self._clip_images = []
        if self._clip_enabled:
            self._load_clips()

        self._static_cache = {}
        self._bg_only_cache = {}
        self._foreground_cache = {}
        self._build_static_layers()
        self._custom_text_layer = build_custom_text_layer(
            self.width, self.height, self.tcfg, self.layout_scale
        )

    def _build_static_layers(self):
        """트랙당 배경+텍스트 오버레이를 한 번만 렌더링해서 캐싱.
        매 프레임마다 배경 복사+텍스트 그리는 비용을 제거한다."""
        width, height = self.width, self.height
        tcfg = self.tcfg
        font_title, font_sub = self.font_title, self.font_sub
        text_color, shadow_c = self.text_color, self.shadow_c

        for track_index, tb in enumerate(self.track_boundaries):
            a = tb['analysis']
            if track_index in self._static_cache:
                if track_index not in self._bg_only_cache:
                    bg_only = self.bg_cache[track_index].copy()
                    self._bg_only_cache[track_index] = np.array(bg_only.convert('RGB'))
                continue

            bg = self.bg_cache[track_index].copy()
            foreground = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            overlays = self.config.get('overlays', {})
            overlay_order = [
                effect_id for effect_id in self.config.get(
                    'effect_order', ['album', 'logo']
                )
                if effect_id in ('album', 'logo')
            ]
            for effect_id in ('album', 'logo'):
                if effect_id not in overlay_order:
                    overlay_order.append(effect_id)
            for effect_id in overlay_order:
                paste_image_overlay(foreground, overlays.get(effect_id, {}))
            draw = ImageDraw.Draw(foreground)
            text_x = int(float(tcfg.get('x', 0.5)) * width)
            text_align = tcfg.get('align', 'center')

            def aligned_x(text_width, align=text_align, x=text_x):
                if align == 'left':
                    return x
                if align == 'right':
                    return x - text_width
                return x - text_width // 2

            if tcfg['position'] == 'center':
                base_y = int(float(tcfg.get('y', 0.5)) * height) - round(60 * self.layout_scale)
            else:
                base_y = round(80 * self.layout_scale)

            if tcfg['show_title']:
                title = os.path.splitext(a.filename)[0] if tcfg.get('strip_extension', True) else a.filename
                if len(title) > 40:
                    title = title[:37] + "..."
                bbox = draw.textbbox((0, 0), title, font=font_title)
                tw = bbox[2] - bbox[0]
                tx = aligned_x(tw)
                draw_text_with_shadow(draw, (tx, base_y), title, font_title,
                                      (*text_color, 255), tcfg['shadow'],
                                      (*shadow_c, 200), tcfg['shadow_offset'])
                if tcfg.get('underline'):
                    draw.line(
                        (tx, base_y + bbox[3] - bbox[1] + 3,
                         tx + tw, base_y + bbox[3] - bbox[1] + 3),
                        fill=(*text_color, 255), width=2,
                    )

            info_y = base_y + round(65 * self.layout_scale)
            info_parts = []
            if tcfg['show_bpm']:
                info_parts.append(f"{a.bpm:.0f} BPM")
            if tcfg['show_key']:
                mode_s = 'Major' if a.mode == 'major' else 'Minor'
                info_parts.append(f"{a.key} {mode_s}")
            if tcfg['show_camelot']:
                info_parts.append(f"{a.camelot}")

            if info_parts:
                info_text = "  |  ".join(info_parts)
                bbox = draw.textbbox((0, 0), info_text, font=font_sub)
                tw = bbox[2] - bbox[0]
                tx = aligned_x(tw)
                draw_text_with_shadow(draw, (tx, info_y), info_text, font_sub,
                                      (*text_color, 200), tcfg['shadow'],
                                      (*shadow_c, 150), tcfg['shadow_offset'])
                if tcfg.get('underline'):
                    draw.line(
                        (tx, info_y + bbox[3] - bbox[1] + 2,
                         tx + tw, info_y + bbox[3] - bbox[1] + 2),
                        fill=(*text_color, 200), width=1,
                    )

            composed = bg.convert('RGBA')
            composed.alpha_composite(foreground)
            self._foreground_cache[track_index] = foreground
            self._static_cache[track_index] = np.array(composed.convert('RGB'))

            bg_only = self.bg_cache[track_index].copy()
            self._bg_only_cache[track_index] = np.array(bg_only.convert('RGB'))

    def track_at(self, t):
        idx = 0
        for i, tb in enumerate(self.track_boundaries):
            if tb['start'] <= t < tb['end']:
                idx = i
                break
            if t >= tb['end']:
                idx = min(i + 1, len(self.track_boundaries) - 1)
        return idx

    def render_frame(self, t):
        """전역 시간 t(초)의 프레임을 RGB numpy 배열로 반환."""
        width, height = self.width, self.height
        vcfg, tcfg, pcfg, fcfg, ecfg = self.vcfg, self.tcfg, self.pcfg, self.fcfg, self.ecfg
        font_time = self.font_time
        text_color, shadow_c = self.text_color, self.shadow_c
        viz_color, bar_color, bar_bg = self.viz_color, self.bar_color, self.bar_bg
        track_viz_max = self.track_viz_max
        smooth_cache = self.smooth_cache
        effects_active = self.effects_active
        beat_time_cache = self.beat_time_cache
        total_duration = self.total_duration

        current_track_idx = self.track_at(t)
        tb = self.track_boundaries[current_track_idx]
        a = tb['analysis']
        local_t = t - tb['start'] + tb.get('source_start', 0.0)
        progress = local_t / max(tb['end'] - tb['start'], 0.001)
        progress = np.clip(progress, 0, 1)

        _render_visuals = should_render_visuals(
            t + self.visibility_timeline_offset,
            self.visibility_timeline_duration,
            initial_visible_duration=self.initial_visible,
            ending_visible_duration=self.ending_visible,
            visibility_enabled=self.visibility_enabled,
            restore_before_end=self.visibility_restore,
        )

        if _render_visuals:
            frame = Image.fromarray(
                self._static_cache[current_track_idx].copy()
            )
            if current_track_idx + 1 < len(self.track_boundaries):
                next_tb = self.track_boundaries[current_track_idx + 1]
                overlap_start = float(next_tb['start'])
                overlap_end = float(tb['end'])
                if overlap_start <= t < overlap_end:
                    span = max(0.001, overlap_end - overlap_start)
                    alpha = float(np.clip(
                        (t - overlap_start) / span, 0.0, 1.0
                    ))
                    next_frame = Image.fromarray(
                        self._static_cache[current_track_idx + 1].copy()
                    )
                    frame = Image.blend(frame, next_frame, alpha)
        else:
            frame = Image.new('RGB', (width, height), self.visibility_black)

        if _render_visuals and self._clip_enabled:
            clip_frame = self._get_clip_frame(t)
            if clip_frame is not None:
                frame = clip_frame.convert('RGBA')
                foreground = self._foreground_cache[current_track_idx]
                if current_track_idx + 1 < len(self.track_boundaries):
                    next_tb = self.track_boundaries[current_track_idx + 1]
                    overlap_start = float(next_tb['start'])
                    overlap_end = float(tb['end'])
                    if overlap_start <= t < overlap_end:
                        alpha = float(np.clip(
                            (t - overlap_start)
                            / max(0.001, overlap_end - overlap_start),
                            0.0, 1.0,
                        ))
                        foreground = Image.blend(
                            foreground,
                            self._foreground_cache[current_track_idx + 1],
                            alpha,
                        )
                frame.alpha_composite(foreground)
                frame = frame.convert('RGB')

        if not _render_visuals:
            frame_arr = np.array(frame.convert('RGB'))
            frame_arr = apply_fade(frame_arr, t,
                                   fcfg['fade_in_duration'], fcfg['fade_out_duration'],
                                   total_duration)
            return frame_arr

        custom_start = max(0.0, float(
            tcfg.get('custom_start_seconds', 0.0) or 0.0
        ))
        custom_end = max(0.0, float(
            tcfg.get('custom_end_seconds', 0.0) or 0.0
        ))
        custom_target = max(0, int(
            tcfg.get('custom_target_track', 0) or 0
        ))
        custom_visible = (
            bool(tcfg.get('custom_text'))
            and t >= custom_start
            and (custom_end <= 0 or t < custom_end)
            and (custom_target == 0 or custom_target == current_track_idx + 1)
        )
        custom_layer = (
            self._custom_text_layer
            if custom_visible else None
        )
        if custom_layer is not None and tcfg.get(
            'custom_affects_by_effects', True
        ):
            frame = frame.convert('RGBA')
            frame.alpha_composite(custom_layer)
            frame = frame.convert('RGB')

        # --- Visualizer ---
        if vcfg['type'] != 'none' and a.stft_magnitudes.size > 0:
            viz_layer = None

            if vcfg['type'] == 'eq_bars':
                bar_h = int(vcfg['height'])
                bar_h_actual = bar_h
                vw = int(vcfg.get('width', 0)) or width
                vx = int(vcfg.get('x', 0))
                vy = int(vcfg.get('y', 0))
                if vy == 0:
                    if vcfg['position'] == 'top':
                        vy = 0
                    elif vcfg['position'] == 'center':
                        vy = (height - bar_h_actual) // 2
                    else:
                        vy = height - bar_h_actual

                cached_key = f"{tb['index']}_eq"
                prev = smooth_cache.get(cached_key)
                last_t = self._smooth_times.get(cached_key)
                delta_t = (
                    max(0.0, local_t - last_t)
                    if last_t is not None else 1 / 60
                )
                base_smoothing = float(vcfg.get('smoothing', 0.3))
                time_smoothing = (
                    base_smoothing ** max(0.001, delta_t * 60)
                    if base_smoothing > 0 else 0
                )
                base_decay = float(vcfg.get('decay', 0.82))
                time_decay = (
                    base_decay ** max(0.001, delta_t * 60)
                    if base_decay > 0 else 0
                )

                viz_layer, curr_vals = get_eq_bars(
                    a.stft_magnitudes, local_t, a.sr, a.hop_length,
                    vcfg['bar_count'], bar_h_actual, vw,
                    viz_color, time_smoothing, prev,
                    track_max=track_viz_max[tb['index']],
                    bar_width_override=vcfg.get('bar_width', 0),
                    gap=vcfg.get('bar_gap', 2),
                    min_height=vcfg.get('min_height', 1),
                    sensitivity=vcfg.get('sensitivity', 1.0),
                    opacity=vcfg.get('opacity', 0.85),
                    corner_radius=vcfg.get('corner_radius', 0),
                    decay=time_decay,
                    mirror=vcfg.get('mirror', False),
                )
                smooth_cache[cached_key] = curr_vals
                self._smooth_times[cached_key] = local_t

                if vcfg['gradient']:
                    ramp = Image.linear_gradient('L').resize(
                        (vw, bar_h_actual)
                    )
                    if vcfg['position'] == 'top':
                        ramp = ramp.transpose(Image.FLIP_TOP_BOTTOM)
                    # Keep the quiet end visible while giving each bar a
                    # cleaner luminous edge instead of a muddy black overlay.
                    ramp = ramp.point(lambda value: 128 + value // 2)
                    alpha = ImageChops.multiply(
                        viz_layer.getchannel('A'), ramp
                    )
                    viz_layer.putalpha(alpha)

                if vcfg.get('invert'):
                    viz_layer = viz_layer.transpose(Image.FLIP_TOP_BOTTOM)
                glow_radius = int(vcfg.get('glow', 0))
                if glow_radius > 0:
                    glow = viz_layer.filter(
                        ImageFilter.GaussianBlur(radius=glow_radius)
                    )
                    viz_layer = Image.alpha_composite(glow, viz_layer)

                frame.paste(viz_layer, (int(vx), int(vy)), viz_layer)

            elif vcfg['type'] == 'waveform':
                wh = int(vcfg['height'])
                ww = int(vcfg.get('width', 0)) or width
                wx = int(vcfg.get('x', 0))
                wy = int(vcfg.get('y', 0))
                wf = get_waveform_frame(
                    a.waveform, local_t, a.sr, ww, wh, viz_color,
                    line_width=vcfg.get('line_width', 2),
                )
                if wy == 0:
                    wy = (0 if vcfg['position'] == 'top' else
                          (height - wh) // 2 if vcfg['position'] == 'center'
                          else height - wh)
                frame.paste(wf, (wx, wy), wf)

            elif vcfg['type'] == 'spectrum':
                sh = int(vcfg.get('height_override', 0)) or int(vcfg['height'])
                sw = int(vcfg.get('width', 0)) or width
                sx = int(vcfg.get('x', 0))
                sy = int(vcfg.get('y', 0))
                if sy == 0:
                    if vcfg['position'] == 'top':
                        sy = 0
                    elif vcfg['position'] == 'center':
                        sy = (height - sh) // 2
                    else:
                        sy = height - sh
                spectrum_key = f"{tb['index']}_spectrum"
                previous_spectrum = smooth_cache.get(spectrum_key)
                spectrum_last_t = self._smooth_times.get(spectrum_key)
                spectrum_delta = (
                    max(0.0, local_t - spectrum_last_t)
                    if spectrum_last_t is not None else 1 / 60
                )
                spectrum_smoothing = float(
                    vcfg.get('smoothing', 0.3)
                ) ** max(0.001, spectrum_delta * 60)
                spec, spectrum_values = get_spectrum_frame(
                    a.stft_magnitudes, local_t, a.sr, a.hop_length, sw, sh, viz_color,
                    track_max=track_viz_max[tb['index']],
                    smoothing=spectrum_smoothing,
                    prev_vals=previous_spectrum,
                )
                smooth_cache[spectrum_key] = spectrum_values
                self._smooth_times[spectrum_key] = local_t
                frame.paste(spec, (int(sx), int(sy)), spec)

            elif vcfg['type'] == 'circles':
                ch = int(vcfg['height']) * 2
                cw = int(vcfg.get('width', 0)) or width
                cx = int(vcfg.get('x', 0))
                circle_key = f"{tb['index']}_circles"
                previous_circles = smooth_cache.get(circle_key)
                circle_last_t = self._smooth_times.get(circle_key)
                circle_delta = (
                    max(0.0, local_t - circle_last_t)
                    if circle_last_t is not None else 1 / 60
                )
                circle_smoothing = float(
                    vcfg.get('smoothing', 0.3)
                ) ** max(0.001, circle_delta * 60)
                circles, circle_values = get_circles_frame(
                    a.stft_magnitudes, local_t, a.sr, a.hop_length,
                    cw, ch, viz_color,
                    track_max=track_viz_max[tb['index']],
                    smoothing=circle_smoothing,
                    prev_energy=previous_circles,
                    line_width=vcfg.get('line_width', 2),
                )
                smooth_cache[circle_key] = circle_values
                self._smooth_times[circle_key] = local_t
                cy_pos = int(vcfg.get('y', 0)) or (height - int(ch)) // 2
                frame.paste(circles, (cx, cy_pos), circles)

            elif vcfg['type'] == 'radial':
                rh = int(vcfg['height']) * 2
                rw = int(vcfg.get('width', 0)) or width
                rx = int(vcfg.get('x', 0))
                cached_key_r = f"{tb['index']}_radial"
                prev_r = smooth_cache.get(cached_key_r)
                last_r_t = self._smooth_times.get(cached_key_r)
                delta_r_t = (
                    max(0.0, local_t - last_r_t)
                    if last_r_t is not None else 1 / 60
                )
                base_r_smoothing = float(vcfg.get('smoothing', 0.3))
                radial_smoothing = (
                    base_r_smoothing ** max(0.001, delta_r_t * 60)
                    if base_r_smoothing > 0 else 0
                )

                radial, curr_r = get_radial_bars(
                    a.stft_magnitudes, local_t, a.sr, a.hop_length,
                    vcfg['bar_count'], vcfg['height'],
                    rw, rh, viz_color, radial_smoothing, prev_r,
                    track_max=track_viz_max[tb['index']],
                    line_width=vcfg.get('line_width', 2),
                )
                smooth_cache[cached_key_r] = curr_r
                self._smooth_times[cached_key_r] = local_t
                ry = int(vcfg.get('y', 0)) or (height - int(rh)) // 2
                frame.paste(radial, (rx, ry), radial)

        # --- Progress bar + Time display (동적 요소만) ---
        draw = ImageDraw.Draw(frame)
        bar_h = pcfg['height']
        margin = pcfg['margin']

        if pcfg['show']:
            if pcfg['position'] == 'bottom':
                by = height - margin - bar_h
            else:
                by = margin

            side_inset = max(1, round(40 * self.layout_scale))
            draw.rectangle([(side_inset, by), (width - side_inset, by + bar_h)],
                           fill=(*bar_bg, 180))
            pw = int((width - side_inset * 2) * progress)
            if pw > 0:
                draw.rectangle([(side_inset, by), (side_inset + pw, by + bar_h)],
                               fill=(*bar_color, 230))

        # --- Time display ---
        if tcfg['show_time']:
            dur_m = int(a.duration // 60)
            dur_s = int(a.duration % 60)
            elapsed = progress * a.duration
            el_m = int(elapsed // 60)
            el_s = int(elapsed % 60)
            time_text = f"{el_m:02d}:{el_s:02d} / {dur_m:02d}:{dur_s:02d}"
            bbox = draw.textbbox((0, 0), time_text, font=font_time)
            tw = bbox[2] - bbox[0]
            if pcfg['position'] == 'bottom':
                ty = height - margin - bar_h - round(28 * self.layout_scale)
            else:
                ty = margin + bar_h + round(8 * self.layout_scale)
            draw_text_with_shadow(draw, ((width - tw) // 2, ty), time_text,
                                  font_time, (*text_color, 180), tcfg['shadow'],
                                  (*shadow_c, 100), max(1, round(2 * self.layout_scale)))

        frame_arr = np.array(frame.convert('RGB'))

        frame_arr = apply_fade(frame_arr, t, fcfg['fade_in_duration'],
                               fcfg['fade_out_duration'], total_duration)

        if effects_active:
            beats = beat_time_cache.get(tb['index'], np.array([]))
            frame_arr = apply_beat_effects(frame_arr, t, beats, ecfg, width, height)

        if self.crt_active:
            frame_arr = apply_crt_effect(frame_arr, ecfg, width, height)

        if custom_layer is not None and not tcfg.get(
            'custom_affects_by_effects', True
        ):
            frame = Image.fromarray(frame_arr).convert('RGBA')
            frame.alpha_composite(custom_layer)
            frame_arr = np.array(frame.convert('RGB'))

        return frame_arr





def generate_video(analyses, mixed_audio_path, output_path,
                   width=1920, height=1080, visual_config_path=None,
                   timestamps=None, timestamp_duration=8.0, crossfade_duration=4.0,
                   frame_progress_callback=None, fps=24,
                   video_codec='auto', audio_codec='aac',
                   video_bitrate='5000k', audio_bitrate='320k',
                   process_callback=None, cancel_event=None,
                   log_callback=None):
    message = t("video.renderStarting")
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(
        message.encode(encoding, errors="replace").decode(encoding),
        end="", flush=True,
    )

    if not os.path.isfile(mixed_audio_path):
        raise FileNotFoundError(t("video.mixedAudioNotFound", path=mixed_audio_path))

    try:
        total_duration = float(sf.info(mixed_audio_path).duration)
    except Exception:
        audio_clip = AudioFileClip(mixed_audio_path)
        if audio_clip is None:
            raise RuntimeError(
                t("video.mixedAudioReadError", path=mixed_audio_path)
            ) from None
        total_duration = audio_clip.duration
        audio_clip.close()
    fps = fps if fps else 24

    renderer = LiveFrameRenderer(
        analyses, width, height, total_duration,
        visual_config_path=visual_config_path,
        timestamps=timestamps, crossfade_duration=crossfade_duration,
    )
    vcfg, fcfg, ecfg = renderer.vcfg, renderer.fcfg, renderer.ecfg

    print(f"  비주얼라이저: {vcfg['type']} | 페이드: in={fcfg['fade_in_duration']}s out={fcfg['fade_out_duration']}s")
    if renderer.effects_active or renderer.crt_active:
        active_fx = [k for k in ['bounce', 'shake', 'zoom', 'flash'] if ecfg.get(k)]
        if renderer.crt_active:
            active_fx.append('crt')
        print(f"  효과: {', '.join(active_fx)}")
    print(f"  총 길이: {total_duration:.1f}s | 해상도: {width}x{height} | FPS: {fps}")

    _total_frames = max(1, math.ceil(total_duration * fps))

    # moviepy.config.FFMPEG_BINARY을 올바른 경로로 강제 설정.
    # PyInstaller 번들에서 imageio_ffmpeg의 ffmpeg 바이너리가 번들 안에 있지만
    # moviepy가 import 시점에 기계별 경로를 캐싱해두어 찾지 못하는 문제 해결.
    _ensure_ffmpeg_for_moviepy()

    ffmpeg_path = None
    try:
        ffmpeg_path = resolve_ffmpeg_executable()
    except Exception:
        pass
    if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
        raise RuntimeError(t("video.ffmpegBundle"))

    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    allowed_video_codecs = {
        'auto', 'libx264', 'h264_nvenc', 'h264_qsv', 'h264_amf'
    }
    codec = (
        _detect_gpu_encoder()
        if video_codec not in allowed_video_codecs or video_codec == 'auto'
        else video_codec
    )
    if width < 146 or height < 146:
        codec = 'libx264'
    cpu_count = os.cpu_count() or 4
    gpu_msg = t("video.codecGpu", codec=codec) if codec != 'libx264' else t("video.codecCpu")
    print(f"  {t('video.renderingStatus', msg=gpu_msg, threads=cpu_count)}")

    def _encode(selected_codec, active_renderer):
        temp_output = output_path + ".partial.mp4"
        command = [
            ffmpeg_path, '-hide_banner', '-loglevel', 'error', '-y',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-s', f'{width}x{height}', '-r', str(fps), '-i', '-',
            '-i', mixed_audio_path,
            '-c:v', selected_codec, '-b:v', str(video_bitrate),
        ]
        if selected_codec == 'libx264':
            command += ['-preset', 'medium', '-threads', str(cpu_count)]
        command += [
            '-c:a', audio_codec, '-b:a', str(audio_bitrate), '-shortest',
            '-movflags', '+faststart', temp_output,
        ]
        if log_callback:
            log_callback(
                "encoder command: "
                + subprocess.list2cmdline([os.fspath(arg) for arg in command])
            )
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=_NO_WINDOW,
        )
        logger.info(
            "Video encoder started pid=%s output=%s", process.pid, output_path
        )
        if process_callback:
            process_callback(process.pid)
        stderr_chunks = []
        stderr_lock = threading.Lock()
        def _drain_stderr():
            for line in iter(process.stderr.readline, b''):
                with stderr_lock:
                    stderr_chunks.append(line)
        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()
        try:
            for frame_index in range(_total_frames):
                if cancel_event is not None and cancel_event.is_set():
                    raise RenderCancelledError(t("render.cancelled"))
                frame = active_renderer.render_frame(frame_index / fps)
                process.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())
                if frame_progress_callback:
                    frame_progress_callback(frame_index + 1, _total_frames)
            process.stdin.close()
            return_code = process.wait()
            stderr_thread.join(timeout=5)
            with stderr_lock:
                stderr_text = b''.join(stderr_chunks).decode('utf-8', errors='replace')
            if return_code:
                raise RuntimeError(stderr_text.strip() or t("video.renderFailed"))
            os.replace(temp_output, output_path)
        except Exception:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            if os.path.exists(temp_output):
                try:
                    os.remove(temp_output)
                except OSError:
                    pass
            raise
        finally:
            if stderr_thread.is_alive():
                stderr_thread.join(timeout=2)
            for stream in (process.stdin, process.stderr):
                if stream and not stream.closed:
                    try:
                        stream.close()
                    except OSError:
                        pass

    try:
        _encode(codec, renderer)
    except Exception as gpu_error:
        if isinstance(gpu_error, RenderCancelledError):
            raise
        if codec == 'libx264':
            raise
        print(f"  GPU 인코딩 실패 ({codec}), CPU 인코딩으로 재시도합니다... ({gpu_error})")
        renderer = LiveFrameRenderer(
            analyses, width, height, total_duration,
            visual_config_path=visual_config_path,
            timestamps=timestamps, crossfade_duration=crossfade_duration,
        )
        _encode('libx264', renderer)

    print(f"\n영상 저장 완료: {output_path}")
    return output_path
