"""Render/extract four aspect ratios and compare preview source to MP4 output."""

import json
import os
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_gen import LiveFrameRenderer, _find_ffmpeg_exe, generate_video


RESOLUTIONS = {
    "1920x1080": (1920, 1080),
    "1280x720": (1280, 720),
    "1080x1920": (1080, 1920),
    "1080x1080": (1080, 1080),
}


def main():
    ffmpeg = _find_ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")
    root = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "test_artifacts", "layout_fidelity"
    ))
    os.makedirs(root, exist_ok=True)
    audio = os.path.join(root, "tone.wav")
    subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1.1",
        "-c:a", "pcm_s16le", audio,
    ], check=True)
    config = {
        "visualizer": {"type": "none"},
        "text": {
            "show_title": True, "show_bpm": True, "show_key": True,
            "show_camelot": True, "show_time": False,
            "font_size": 42, "sub_font_size": 28,
            "custom_text": "좌표계 검증 ABC 123",
            "custom_x": .25, "custom_y": .18,
            "custom_font_size": 36, "custom_color": "#ffffff",
        },
        "progress_bar": {"show": True},
        "fade": {"fade_in_duration": 0, "fade_out_duration": 0},
    }
    config_path = os.path.join(root, "config.json")
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)

    analysis = SimpleNamespace(
        filepath=audio, filename="Layout Test.wav", duration=1.1,
        bpm=123, key="C", mode="major", camelot="8B",
        waveform=np.zeros(5513, dtype=np.float32),
        stft_magnitudes=np.empty((0, 0), dtype=np.float32),
        beat_times=np.array([], dtype=np.float32),
        rms=np.array([], dtype=np.float32),
        sr=22050, hop_length=512,
    )
    results = {}
    cards = []
    for label, (width, height) in RESOLUTIONS.items():
        renderer = LiveFrameRenderer(
            [analysis], width, height, 1.1,
            timestamps=None, config_dict=config,
        )
        preview = Image.fromarray(renderer.render_frame(0))
        preview_path = os.path.join(root, f"{label}_preview.png")
        preview.save(preview_path)
        video_path = os.path.join(root, f"{label}_output.mp4")
        generate_video(
            [analysis], audio, video_path,
            width=width, height=height, visual_config_path=config_path,
            fps=1, video_codec="libx264", video_bitrate="8000k",
        )
        output_path = os.path.join(root, f"{label}_output.png")
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-i", video_path, "-frames:v", "1", output_path,
        ], check=True)
        output = Image.open(output_path).convert("RGB")
        preview_rgb = preview.convert("RGB")
        delta = np.abs(
            np.asarray(preview_rgb, dtype=np.int16)
            - np.asarray(output, dtype=np.int16)
        )
        mean_error = float(delta.mean())
        p99_error = float(np.percentile(delta, 99))
        results[label] = {
            "size": [width, height],
            "mean_absolute_error": mean_error,
            "p99_absolute_error": p99_error,
            "passed": mean_error < 5.0,
        }
        diff = ImageChops.difference(preview_rgb, output)
        diff.save(os.path.join(root, f"{label}_difference.png"))

        thumb_size = (320, 180 if width >= height else 320)
        left = preview_rgb.copy()
        left.thumbnail(thumb_size)
        right = output.copy()
        right.thumbnail(thumb_size)
        card = Image.new(
            "RGB", (660, max(left.height, right.height) + 35), "#202225"
        )
        card.paste(left, (5, 30))
        card.paste(right, (335, 30))
        draw = ImageDraw.Draw(card)
        draw.text((5, 7), f"{label} PREVIEW", fill="white")
        draw.text(
            (335, 7), f"MP4 FRAME · MAE {mean_error:.3f}", fill="white"
        )
        cards.append(card)

    contact = Image.new(
        "RGB", (660, sum(card.height for card in cards)), "#111214"
    )
    y = 0
    for card in cards:
        contact.paste(card, (0, y))
        y += card.height
    contact.save(os.path.join(root, "comparison_contact_sheet.png"))
    report_path = os.path.join(root, "report.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)
    if not all(item["passed"] for item in results.values()):
        raise AssertionError(results)
    print(report_path)


if __name__ == "__main__":
    main()
