"""Streaming FFmpeg audio pipeline for long playlist renders."""

import os
import json
import subprocess
import sys

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


def _run(command, cancel_event=None):
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        creationflags=_NO_WINDOW,
    )
    while process.poll() is None:
        if cancel_event is not None and cancel_event.wait(0.1):
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            raise RuntimeError("사용자가 오디오 작업을 취소했습니다.")
    stdout, stderr = process.communicate()
    if process.returncode:
        raise RuntimeError((stderr or stdout or "FFmpeg 오디오 처리 실패").strip())


def mix_tracks_streaming(
    ffmpeg_exe, analyses, track_specs, output_path,
    crossfade_duration=4.0, cancel_event=None,
):
    """Mix trimmed tracks without loading complete audio files into Python RAM."""
    usable = [
        (analysis, spec) for analysis, spec in zip(analyses, track_specs)
        if spec.get("filepath")
    ]
    if not usable:
        raise ValueError("믹싱할 트랙이 없습니다.")

    command = [ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y"]
    durations = []
    for analysis, spec in usable:
        start = max(0.0, float(spec.get("trim_start", 0.0)))
        end = float(spec.get("trim_end", 0.0))
        if end <= 0:
            end = float(analysis.duration)
        duration = max(0.1, min(end, analysis.duration) - start)
        durations.append(duration)
        command += ["-ss", f"{start:.6f}", "-t", f"{duration:.6f}", "-i", spec["filepath"]]

    filters = []
    for index, (_analysis, spec) in enumerate(usable):
        volume = max(0.0, min(4.0, float(spec.get("volume", 1.0))))
        fade_in = max(0.0, min(
            float(spec.get("fade_in", 0.01)), durations[index] / 2
        ))
        fade_out = max(0.0, min(
            float(spec.get("fade_out", 0.01)), durations[index] / 2
        ))
        chain = (
            f"[{index}:a]aresample=44100,"
            "aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={volume:.6f}"
        )
        if fade_in > 0:
            chain += f",afade=t=in:st=0:d={fade_in:.6f}"
        if fade_out > 0:
            chain += (
                f",afade=t=out:st="
                f"{max(0, durations[index] - fade_out):.6f}:d={fade_out:.6f}"
            )
        filters.append(
            f"{chain}[a{index}]"
        )

    current = "a0"
    elapsed = durations[0]
    timestamps = [{
        "track_num": 1, "filename": usable[0][0].filename,
        "start_time": 0.0, "end_time": durations[0],
        "bpm": usable[0][0].bpm, "key": usable[0][0].key,
        "mode": usable[0][0].mode, "camelot": usable[0][0].camelot,
    }]
    for index in range(1, len(usable)):
        fade = min(crossfade_duration, elapsed / 3, durations[index] / 3)
        output_label = f"mix{index}"
        filters.append(
            f"[{current}][a{index}]acrossfade=d={fade:.6f}:c1=tri:c2=tri"
            f"[{output_label}]"
        )
        start_time = elapsed - fade
        elapsed += durations[index] - fade
        analysis = usable[index][0]
        timestamps.append({
            "track_num": index + 1, "filename": analysis.filename,
            "start_time": start_time, "end_time": elapsed,
            "bpm": analysis.bpm, "key": analysis.key,
            "mode": analysis.mode, "camelot": analysis.camelot,
            "transition_from": usable[index - 1][0].filename,
            "transition_at": start_time,
        })
        current = output_label

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    command += [
        "-filter_complex", ";".join(filters), "-map", f"[{current}]",
        "-c:a", "pcm_s16le", output_path,
    ]
    _run(command, cancel_event)
    return output_path, elapsed, timestamps


def normalize_loudness(
    ffmpeg_exe, input_path, output_path, target_lufs=-14.0,
    true_peak=-1.5, cancel_event=None,
):
    """2-pass EBU R128 loudness normalization using ffmpeg loudnorm.

    Pass 1 measures the input loudness/true-peak/LRA/threshold.
    Pass 2 applies correction using measured_* params for accurate output.
    """
    measure_cmd = [
        ffmpeg_exe, "-hide_banner", "-i", input_path,
        "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    result = subprocess.run(
        measure_cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace",
        creationflags=_NO_WINDOW,
    )
    stderr_text = result.stderr
    json_start = stderr_text.rfind("{")
    json_end = stderr_text.rfind("}") + 1
    if json_start == -1 or json_end <= json_start:
        raise RuntimeError(
            "loudnorm 측정 실패: ffmpeg 출력에서 JSON을 찾을 수 없음\n"
            + stderr_text[-2000:]
        )
    measured = json.loads(stderr_text[json_start:json_end])

    correct_cmd = [
        ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y",
        "-i", input_path,
        "-af", (
            f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:"
            f"measured_I={measured['input_i']}:"
            f"measured_TP={measured['input_tp']}:"
            f"measured_LRA={measured['input_lra']}:"
            f"measured_thresh={measured['input_thresh']}:"
            f"offset={measured['target_offset']}"
        ),
        "-c:a", "pcm_s16le", output_path,
    ]
    _run(correct_cmd, cancel_event)
    return output_path
