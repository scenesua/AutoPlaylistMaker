"""영상 생성 모듈: 유저 이미지 배경 + 비주얼라이저 + 페이드 이펙트"""

import numpy as np
import os
import json
import colorsys
import subprocess
import shutil
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import AudioFileClip, VideoClip


def _find_ffmpeg_exe():
    """imageio_ffmpeg 또는 시스템 PATH에서 ffmpeg 실행 파일 경로를 찾는다.
    찾으면 절대 경로 문자열, 없으면 None."""
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.isfile(p):
            return p
    except Exception:
        pass
    p = shutil.which('ffmpeg')
    if p:
        return p
    if os.name == 'nt':
        p = shutil.which('ffmpeg.exe')
        if p:
            return p
    return None


def _ensure_ffmpeg_for_moviepy():
    """moviepy의 ffmpeg 경로를 올바른 값으로 강제 설정."""
    try:
        ffmpeg_path = _find_ffmpeg_exe()
        _log_lines = [f"_find_ffmpeg_exe -> {ffmpeg_path!r}"]
        if not ffmpeg_path:
            _log_lines.append("ffmpeg not found!")
            _write_log(_log_lines)
            return
        _log_lines.append(f"exists={os.path.isfile(ffmpeg_path)}")
        os.environ["FFMPEG_BINARY"] = ffmpeg_path
        import moviepy.config as _mc
        _mc.FFMPEG_BINARY = ffmpeg_path
        _log_lines.append(f"moviepy.config.FFMPEG_BINARY = {ffmpeg_path}")
        try:
            import moviepy.video.io.ffmpeg_writer as _fw
            old = getattr(_fw, 'FFMPEG_BINARY', '?')
            _fw.FFMPEG_BINARY = ffmpeg_path
            _log_lines.append(f"ffmpeg_writer.FFMPEG_BINARY: {old!r} -> {ffmpeg_path}")
        except Exception as e:
            _log_lines.append(f"ffmpeg_writer patch error: {e}")
        try:
            import moviepy.audio.io.ffmpeg_audiowriter as _aw
            old_a = getattr(_aw, 'FFMPEG_BINARY', '?')
            _aw.FFMPEG_BINARY = ffmpeg_path
            _log_lines.append(f"ffmpeg_audiowriter.FFMPEG_BINARY: {old_a!r} -> {ffmpeg_path}")
        except Exception as e:
            _log_lines.append(f"ffmpeg_audiowriter patch error: {e}")
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
    try:
        ffmpeg_exe = _find_ffmpeg_exe()
        if not ffmpeg_exe:
            return 'libx264'

        result = subprocess.run(
            [ffmpeg_exe, '-encoders'], capture_output=True, text=True, timeout=10,
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
    except Exception:
        pass
    return 'libx264'


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
    "background": {"image": None, "opacity": 1.0, "blur": 0, "darken": 0.0},
    "visualizer": {
        "type": "eq_bars", "position": "bottom", "color": "#ffffff",
        "opacity": 0.85, "bar_count": 64, "height": 120,
        "smoothing": 0.3, "mirror": False, "gradient": True,
        "x": 0, "y": 0, "width": 0, "height_override": 0,
    },
    "text": {
        "show_title": True, "show_bpm": True, "show_key": True,
        "show_camelot": False, "show_time": True, "position": "center",
        "font_size": 42, "sub_font_size": 28, "color": "#ffffff",
        "shadow": True, "shadow_color": "#000000", "shadow_offset": 3,
        "custom_text": "",
        "custom_x": 0.5, "custom_y": 0.3,
        "custom_font_size": 36,
        "custom_bold": False, "custom_italic": False, "custom_underline": False,
        "custom_color": "#ffffff",
        "custom_affects_by_effects": True,
    },
    "progress_bar": {
        "show": True, "position": "bottom", "height": 4,
        "color": "#ffffff", "background_color": "#333333", "margin": 30,
    },
    "fade": {"fade_in_duration": 2.0, "fade_out_duration": 3.0},
}


def load_visual_config(config_path=None):
    config = DEFAULT_CONFIG.copy()
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


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_font(size, family=None):
    import sys as _sys

    if family:
        try:
            return ImageFont.truetype(family, size)
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


def load_background_image(image_path, width, height):
    img = Image.open(image_path).convert('RGB')
    img_ratio = img.width / img.height
    target_ratio = width / height
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
        bg = load_background_image(bg_cfg['image'], width, height)
    else:
        bg = create_gradient_bg(width, height, key, mode)

    if bg_cfg.get('darken', 0) > 0:
        dark = Image.new('RGB', (width, height), (0, 0, 0))
        alpha = bg_cfg['darken']
        bg = Image.blend(bg, dark, alpha)

    if bg_cfg.get('blur', 0) > 0:
        bg = bg.filter(ImageFilter.GaussianBlur(radius=bg_cfg['blur']))

    return bg


def track_reference_max(stft_mags, percentile=95):
    """트랙 전체 기준 정규화 값(퍼센타일). 시각화 함수들이 프레임 단위로
    자기 자신의 최댓값에 맞춰 정규화하면 조용한 구간도 항상 풀스케일로
    보이는 문제가 있어, 트랙 전체 기준의 고정값을 한 번 계산해 재사용한다."""
    if stft_mags is None or stft_mags.size == 0:
        return 1e-8
    return float(np.percentile(stft_mags, percentile)) + 1e-8


def get_eq_bars(stft_mags, t, sr, hop_length, n_bars, bar_height, width,
                color_rgb, smoothing, prev_vals=None, track_max=None):
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
    bars = np.clip(bars, 0, 1)

    if prev_vals is not None and smoothing > 0:
        bars = prev_vals * smoothing + bars * (1 - smoothing)

    bar_width = max(1, (width - 40) // n_bars - 2)
    gap = 2
    total_width = n_bars * (bar_width + gap)
    start_x = (width - total_width) // 2

    img = Image.new('RGBA', (width, bar_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for i in range(n_bars):
        h = int(bars[i] * bar_height * 0.95)
        if h < 1:
            continue
        x = start_x + i * (bar_width + gap)
        y = bar_height - h
        alpha = int(255 * bars[i] * 0.85 + 40)
        r, g, b = color_rgb
        draw.rectangle([x, y, x + bar_width, bar_height], fill=(r, g, b, alpha))

    return img, bars


def get_waveform_frame(waveform, t, sr, width, height, color_rgb):
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
    points_top = list(zip(xs.tolist(), ys_top.tolist()))
    r, g, b = color_rgb
    draw.line(points_top, fill=(r, g, b, 200), width=2)

    ys_bot = center_y + y_offsets
    points_bot = list(zip(xs.tolist(), ys_bot.tolist()))
    draw.line(points_bot, fill=(r, g, b, 120), width=1)

    return img


def get_spectrum_frame(stft_mags, t, sr, hop_length, width, height, color_rgb, track_max=None):
    frame_idx = int(t * sr / hop_length)
    frame_idx = min(frame_idx, stft_mags.shape[1] - 1)
    frame_idx = max(0, frame_idx)

    n_bins = min(stft_mags.shape[0], 256)
    mags = stft_mags[:n_bins, frame_idx]
    max_val = track_max if track_max is not None else (np.max(mags) + 1e-8)
    mags = mags / max_val
    mags = np.clip(mags, 0, 1)

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

    return img


def get_circles_frame(stft_mags, t, sr, hop_length, width, height, color_rgb, prev_energy=0, track_max=None):
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

    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = width // 2, height // 2
    r, g, b = color_rgb

    for i, e in enumerate(energies):
        radius = int(20 + e * min(width, height) * 0.35)
        alpha = int(60 + 195 * e)
        line_w = max(1, int(2 + e * 4))
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=(r, g, b, alpha), width=line_w,
        )

    return img


def get_radial_bars(stft_mags, t, sr, hop_length, n_bars, bar_height, width, height,
                    color_rgb, smoothing, prev_vals=None, track_max=None):
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
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, alpha), width=3)

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
        import random
        shake_x = int((random.random() - 0.5) * 2 * intensity * pulse * scale)
        shake_y = int((random.random() - 0.5) * 2 * intensity * pulse * scale)
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

        self.config = config_dict if config_dict is not None else load_visual_config(visual_config_path)
        self.vcfg = self.config['visualizer']
        self.tcfg = self.config['text']
        self.pcfg = self.config['progress_bar']
        self.fcfg = self.config['fade']
        self.ecfg = self.config.get('effects', {})

        custom_font_family = self.tcfg.get('custom_font_family', None)
        self.font_title = get_font(self.tcfg['font_size'], custom_font_family)
        self.font_sub = get_font(self.tcfg['sub_font_size'], custom_font_family)
        self.font_time = get_font(22, custom_font_family)

        self.text_color = hex_to_rgb(self.tcfg['color'])
        self.shadow_c = hex_to_rgb(self.tcfg['shadow_color'])
        self.viz_color = hex_to_rgb(self.vcfg['color'])
        self.bar_color = hex_to_rgb(self.pcfg['color'])
        self.bar_bg = hex_to_rgb(self.pcfg['background_color'])

        self.track_viz_max = {a.filename: track_reference_max(a.stft_magnitudes) for a in analyses}

        self.bg_cache = {
            a.filename: prepare_background(width, height, self.config, a.key, a.mode)
            for a in analyses
        }

        self.track_boundaries = []
        if timestamps and len(timestamps) == len(analyses):
            for a, ts in zip(analyses, timestamps):
                self.track_boundaries.append({
                    'start': ts['start_time'], 'end': ts['end_time'], 'analysis': a
                })
        else:
            current_time = 0
            for i, a in enumerate(analyses):
                track_start = 0 if i == 0 else current_time
                track_end = track_start + a.duration
                current_time = track_end
                if i < len(analyses) - 1:
                    current_time -= crossfade_duration
                self.track_boundaries.append({'start': track_start, 'end': track_end, 'analysis': a})

        self.beat_time_cache = {}
        for a in analyses:
            if a.beat_times is not None and len(a.beat_times) > 0:
                offsets = []
                for tb in self.track_boundaries:
                    if tb['analysis'].filename == a.filename:
                        offset = tb['start']
                        offsets = [(bt + offset) for bt in a.beat_times
                                   if (bt + offset) >= tb['start'] and (bt + offset) < tb['end']]
                        break
                self.beat_time_cache[a.filename] = np.array(offsets)
            else:
                self.beat_time_cache[a.filename] = np.array([])

        self.smooth_cache = {}
        self.effects_active = any(self.ecfg.get(k) for k in ['bounce', 'shake', 'zoom', 'flash'])
        self.crt_active = self.ecfg.get('crt', False)

        self._clip_images = []
        self._clip_enabled = self.config.get('clip_enabled', False)
        self._clip_interval = self.config.get('clip_interval', 1.0)
        self._clip_interval_unit = self.config.get('clip_interval_unit', '초')
        self._clip_random = self.config.get('clip_random', False)
        if self._clip_enabled:
            self._load_clips()

        self._static_cache = {}
        self._build_static_layers()

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
            if self._clip_interval_unit == '박자':
                idx = int(t / max(self._clip_interval, 0.1)) % n
            elif self._clip_interval_unit == '곡별':
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
        self.config = config_dict
        self.vcfg = self.config['visualizer']
        self.tcfg = self.config['text']
        self.pcfg = self.config['progress_bar']
        self.fcfg = self.config['fade']
        self.ecfg = self.config.get('effects', {})

        custom_font_family = self.tcfg.get('custom_font_family', None)
        self.font_title = get_font(self.tcfg['font_size'], custom_font_family)
        self.font_sub = get_font(self.tcfg['sub_font_size'], custom_font_family)
        self.font_time = get_font(22, custom_font_family)

        self.text_color = hex_to_rgb(self.tcfg['color'])
        self.shadow_c = hex_to_rgb(self.tcfg['shadow_color'])
        self.viz_color = hex_to_rgb(self.vcfg['color'])
        self.bar_color = hex_to_rgb(self.pcfg['color'])
        self.bar_bg = hex_to_rgb(self.pcfg['background_color'])

        self.bg_cache = {
            a.filename: prepare_background(self.width, self.height, self.config, a.key, a.mode)
            for a in self.analyses
        }
        self.smooth_cache = {}
        self.effects_active = any(self.ecfg.get(k) for k in ['bounce', 'shake', 'zoom', 'flash'])
        self.crt_active = self.ecfg.get('crt', False)

        self._clip_enabled = self.config.get('clip_enabled', False)
        self._clip_interval = self.config.get('clip_interval', 1.0)
        self._clip_interval_unit = self.config.get('clip_interval_unit', '초')
        self._clip_random = self.config.get('clip_random', False)
        self._clip_images = []
        if self._clip_enabled:
            self._load_clips()

        self._static_cache = {}
        self._build_static_layers()

    def _build_static_layers(self):
        """트랙당 배경+텍스트 오버레이를 한 번만 렌더링해서 캐싱.
        매 프레임마다 배경 복사+텍스트 그리는 비용을 제거한다."""
        width, height = self.width, self.height
        vcfg, tcfg = self.vcfg, self.tcfg
        font_title, font_sub = self.font_title, self.font_sub
        text_color, shadow_c = self.text_color, self.shadow_c

        for tb in self.track_boundaries:
            a = tb['analysis']
            if a.filename in self._static_cache:
                continue

            bg = self.bg_cache[a.filename].copy()
            draw = ImageDraw.Draw(bg)
            center_x = width // 2

            if tcfg['position'] == 'center':
                base_y = height // 2 - 60
            else:
                base_y = 80

            if tcfg['show_title']:
                title = a.filename
                if len(title) > 40:
                    title = title[:37] + "..."
                bbox = draw.textbbox((0, 0), title, font=font_title)
                tw = bbox[2] - bbox[0]
                tx = (width - tw) // 2
                draw_text_with_shadow(draw, (tx, base_y), title, font_title,
                                      (*text_color, 255), tcfg['shadow'],
                                      (*shadow_c, 200), tcfg['shadow_offset'])

            info_y = base_y + 65
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
                tx = (width - tw) // 2
                draw_text_with_shadow(draw, (tx, info_y), info_text, font_sub,
                                      (*text_color, 200), tcfg['shadow'],
                                      (*shadow_c, 150), tcfg['shadow_offset'])

            custom_text = tcfg.get('custom_text', '')
            if custom_text:
                custom_font_size = tcfg.get('custom_font_size', 36)
                custom_bold = tcfg.get('custom_bold', False)
                custom_italic = tcfg.get('custom_italic', False)
                custom_font = get_font(custom_font_size)
                custom_color = hex_to_rgb(tcfg.get('custom_color', '#ffffff'))
                cx_pos = int(tcfg.get('custom_x', 0.5) * width)
                cy_pos = int(tcfg.get('custom_y', 0.3) * height)

                pad = 20 + (4 if custom_bold else 0)
                bbox0 = draw.textbbox((0, 0), custom_text, font=custom_font)
                layer_w = (bbox0[2] - bbox0[0]) + pad * 2
                layer_h = (bbox0[3] - bbox0[1]) + pad * 2
                text_layer = Image.new('RGBA', (layer_w, layer_h), (0, 0, 0, 0))
                tdraw = ImageDraw.Draw(text_layer)
                origin = (pad - bbox0[0], pad - bbox0[1])

                if tcfg['shadow']:
                    soff = tcfg['shadow_offset']
                    shadow_pos = (origin[0] + soff, origin[1] + soff)
                    if custom_bold:
                        for dx in range(-1, 2):
                            for dy in range(-1, 2):
                                tdraw.text((shadow_pos[0]+dx, shadow_pos[1]+dy), custom_text,
                                          fill=(*shadow_c, 150), font=custom_font)
                    else:
                        tdraw.text(shadow_pos, custom_text, fill=(*shadow_c, 150), font=custom_font)

                if custom_bold:
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            tdraw.text((origin[0]+dx, origin[1]+dy), custom_text,
                                      fill=(*custom_color, 255), font=custom_font)
                else:
                    tdraw.text(origin, custom_text, fill=(*custom_color, 255), font=custom_font)

                if tcfg.get('custom_underline', False):
                    ux0, uy1 = origin[0], origin[1] + (bbox0[3] - bbox0[1]) + 2
                    ux1 = origin[0] + (bbox0[2] - bbox0[0])
                    tdraw.line([(ux0, uy1), (ux1, uy1)], fill=(*custom_color, 255), width=2)

                if custom_italic:
                    shear = 0.25
                    new_w = layer_w + int(layer_h * shear)
                    text_layer = text_layer.transform(
                        (new_w, layer_h), Image.AFFINE,
                        (1, -shear, layer_h * shear, 0, 1, 0),
                        resample=Image.BICUBIC,
                    )

                paste_x = cx_pos - text_layer.width // 2
                paste_y = cy_pos - pad
                bg.paste(text_layer, (paste_x, paste_y), text_layer)

            self._static_cache[a.filename] = np.array(bg.convert('RGB'))

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
        local_t = t - tb['start']
        progress = local_t / max(tb['end'] - tb['start'], 0.001)
        progress = np.clip(progress, 0, 1)

        # 캐시된 정적 레이어(배경+텍스트)를 복사 — 배경생성+텍스트 그리기 비용 0
        frame = Image.fromarray(self._static_cache[a.filename].copy())

        if self._clip_enabled:
            clip_frame = self._get_clip_frame(t)
            if clip_frame is not None:
                frame.paste(clip_frame, (0, 0))

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
                    vy = 0 if vcfg['position'] == 'top' else height - bar_h_actual

                cached_key = f"{a.filename}_eq"
                prev = smooth_cache.get(cached_key)

                viz_layer, curr_vals = get_eq_bars(
                    a.stft_magnitudes, local_t, a.sr, a.hop_length,
                    vcfg['bar_count'], bar_h_actual, vw,
                    viz_color, vcfg['smoothing'], prev,
                    track_max=track_viz_max.get(a.filename),
                )
                smooth_cache[cached_key] = curr_vals

                if vcfg['gradient']:
                    grad = Image.new('RGBA', (vw, bar_h_actual), (0, 0, 0, 0))
                    gd = ImageDraw.Draw(grad)
                    for y in range(bar_h_actual):
                        alpha = int(255 * (1 - y / bar_h_actual) * 0.6)
                        gd.line([(0, y), (vw, y)], fill=(0, 0, 0, alpha))
                    if vcfg['position'] == 'top':
                        viz_layer = Image.alpha_composite(viz_layer, grad)
                    else:
                        flipped = grad.transpose(Image.FLIP_TOP_BOTTOM)
                        viz_layer = Image.alpha_composite(viz_layer, flipped)

                frame.paste(viz_layer, (int(vx), int(vy)), viz_layer)

            elif vcfg['type'] == 'waveform':
                wh = int(vcfg['height'])
                wf = get_waveform_frame(a.waveform, local_t, a.sr, width, wh, viz_color)
                if vcfg['position'] == 'top':
                    frame.paste(wf, (0, 0), wf)
                else:
                    frame.paste(wf, (0, height - wh), wf)

            elif vcfg['type'] == 'spectrum':
                sh = int(vcfg.get('height_override', 0)) or int(vcfg['height'])
                sw = int(vcfg.get('width', 0)) or width
                sx = int(vcfg.get('x', 0))
                sy = int(vcfg.get('y', 0))
                if sy == 0:
                    sy = 0 if vcfg['position'] == 'top' else height - sh
                spec = get_spectrum_frame(
                    a.stft_magnitudes, local_t, a.sr, a.hop_length, sw, sh, viz_color,
                    track_max=track_viz_max.get(a.filename),
                )
                frame.paste(spec, (int(sx), int(sy)), spec)

            elif vcfg['type'] == 'circles':
                ch = int(vcfg['height']) * 2
                circles = get_circles_frame(
                    a.stft_magnitudes, local_t, a.sr, a.hop_length,
                    width, ch, viz_color,
                    track_max=track_viz_max.get(a.filename),
                )
                cy_pos = (height - int(ch)) // 2
                frame.paste(circles, (0, cy_pos), circles)

            elif vcfg['type'] == 'radial':
                rh = int(vcfg['height']) * 2
                cached_key_r = f"{a.filename}_radial"
                prev_r = smooth_cache.get(cached_key_r)

                radial, curr_r = get_radial_bars(
                    a.stft_magnitudes, local_t, a.sr, a.hop_length,
                    vcfg['bar_count'], vcfg['height'],
                    width, rh, viz_color, vcfg['smoothing'], prev_r,
                    track_max=track_viz_max.get(a.filename),
                )
                smooth_cache[cached_key_r] = curr_r
                ry = (height - int(rh)) // 2
                frame.paste(radial, (0, ry), radial)

        # --- Progress bar + Time display (동적 요소만) ---
        draw = ImageDraw.Draw(frame)
        bar_h = pcfg['height']
        margin = pcfg['margin']

        if pcfg['show']:
            if pcfg['position'] == 'bottom':
                by = height - margin - bar_h
            else:
                by = margin

            draw.rectangle([(40, by), (width - 40, by + bar_h)],
                           fill=(*bar_bg, 180))
            pw = int((width - 80) * progress)
            if pw > 0:
                draw.rectangle([(40, by), (40 + pw, by + bar_h)],
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
                ty = height - margin - bar_h - 28
            else:
                ty = margin + bar_h + 8
            draw_text_with_shadow(draw, ((width - tw) // 2, ty), time_text,
                                  font_time, (*text_color, 180), tcfg['shadow'],
                                  (*shadow_c, 100), 2)

        frame_arr = np.array(frame.convert('RGB'))

        frame_arr = apply_fade(frame_arr, t, fcfg['fade_in_duration'],
                               fcfg['fade_out_duration'], total_duration)

        if effects_active:
            beats = beat_time_cache.get(a.filename, np.array([]))
            frame_arr = apply_beat_effects(frame_arr, t, beats, ecfg, width, height)

        if self.crt_active:
            frame_arr = apply_crt_effect(frame_arr, ecfg, width, height)

        return frame_arr





def generate_video(analyses, mixed_audio_path, output_path,
                   width=1920, height=1080, visual_config_path=None,
                   timestamps=None, timestamp_duration=8.0, crossfade_duration=4.0,
                   frame_progress_callback=None, fps=24):
    print("\n영상 생성 시작...")

    if not os.path.isfile(mixed_audio_path):
        raise FileNotFoundError(f"믹스 오디오 파일을 찾을 수 없습니다: {mixed_audio_path}")

    audio_clip = AudioFileClip(mixed_audio_path)
    if audio_clip is None:
        raise RuntimeError(f"오디오 파일을 열 수 없습니다: {mixed_audio_path}")
    total_duration = audio_clip.duration
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
        print(f"  이펙트: {', '.join(active_fx)}")
    print(f"  총 길이: {total_duration:.1f}s | 해상도: {width}x{height} | FPS: {fps}")

    _raw_make_frame = renderer.render_frame

    _total_frames = max(1, int(total_duration * fps))
    _frame_counter = [0]

    def _make_frame_with_progress(t):
        frame = _raw_make_frame(t)
        _frame_counter[0] += 1
        if frame_progress_callback:
            try:
                frame_progress_callback(_frame_counter[0], _total_frames)
            except Exception:
                pass
        return frame

    make_frame = _make_frame_with_progress

    main_video = VideoClip(make_frame, duration=total_duration)
    main_video = main_video.with_audio(audio_clip)

    final_video = main_video

    if final_video is None:
        raise RuntimeError("영상 합치기 실패: 최종 영상 객체가 None입니다.")

    # moviepy.config.FFMPEG_BINARY을 올바른 경로로 강제 설정.
    # PyInstaller 번들에서 imageio_ffmpeg의 ffmpeg 바이너리가 번들 안에 있지만
    # moviepy가 import 시점에 기계별 경로를 캐싱해두어 찾지 못하는 문제 해결.
    _ensure_ffmpeg_for_moviepy()

    ffmpeg_path = None
    try:
        ffmpeg_path = _find_ffmpeg_exe()
    except Exception:
        pass
    if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
        raise RuntimeError(
            "ffmpeg 실행 파일을 찾을 수 없습니다.\n"
            "PyInstaller 번들에서 빌드했다면 "
            "'--collect-all imageio_ffmpeg' 옵션으로 다시 빌드하세요.\n"
            "또는 시스템 PATH에 ffmpeg를 설치하세요."
        )

    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    codec = _detect_gpu_encoder()
    cpu_count = os.cpu_count() or 4
    gpu_msg = f"GPU 인코딩 ({codec})" if codec != 'libx264' else "CPU 인코딩 (libx264)"
    print(f"  렌더링 중... | {gpu_msg} | 스레드: {cpu_count} | (시간이 걸릴 수 있습니다)")

    def _friendly_ffmpeg_error(e):
        return RuntimeError(
            "영상 인코딩 실패: ffmpeg 프로세스가 시작되지 못했습니다.\n"
            "가능한 원인:\n"
            "  1) ffmpeg 실행 파일이 exe 번들에 빠져 있음 "
            "(--collect-all imageio_ffmpeg 옵션으로 다시 빌드)\n"
            "  2) 출력 경로에 쓰기 권한이 없거나 디스크 공간 부족\n"
            f"  3) 출력 경로 문제: {output_path}\n"
            f"원본 오류: {e}"
        )

    try:
        final_video.write_videofile(
            output_path, fps=fps, codec=codec, audio_codec='aac',
            bitrate='5000k', preset='medium', threads=cpu_count,
            logger=None,
        )
    except Exception as e_gpu:
        if codec == 'libx264':
            # CPU 인코딩으로 이미 시도한 것이었으면 더 재시도할 게 없음
            if "'NoneType' object has no attribute 'write'" in str(e_gpu):
                raise _friendly_ffmpeg_error(e_gpu) from e_gpu
            raise

        print(f"  GPU 인코딩 실패 ({codec}), CPU 인코딩으로 재시도합니다... ({e_gpu})")
        try:
            final_video.write_videofile(
                output_path, fps=fps, codec='libx264', audio_codec='aac',
                bitrate='5000k', preset='medium', threads=cpu_count, logger=None,
            )
        except Exception as e_cpu:
            # GPU도 실패하고 CPU 재시도도 실패한 경우 — 예전엔 이 재시도에
            # try/except가 없어서 NoneType 에러가 그대로 새어나갔음
            if "'NoneType' object has no attribute 'write'" in str(e_cpu):
                raise _friendly_ffmpeg_error(e_cpu) from e_cpu
            raise

    print(f"\n영상 저장 완료: {output_path}")
    return output_path
