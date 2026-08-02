"""Streaming FFmpeg audio pipeline for long playlist renders."""

import os
import json
import math
import subprocess
import sys
import logging
import tempfile
from pathlib import Path
from i18n import t

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
logger = logging.getLogger(__name__)

def measure_loudness(filepath, ffmpeg_exe=None):
    """Measure BS.1770 loudness with FFmpeg; never label RMS as LUFS."""
    if ffmpeg_exe is None:
        from ffmpeg_service import ensure_ffmpeg_available
        ffmpeg_exe = ensure_ffmpeg_available()
    result = subprocess.run(
        [
            ffmpeg_exe, "-hide_banner", "-nostats", "-i", filepath,
            "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
            "-f", "null", "-",
        ],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", creationflags=_NO_WINDOW, check=False,
    )
    output = result.stderr or result.stdout
    start, end = output.rfind("{"), output.rfind("}") + 1
    if start < 0 or end <= start:
        raise RuntimeError(t("errors.loudnormFailed", output=output[-2000:]))
    measured = json.loads(output[start:end])
    values = {
        "integrated_lufs": float(measured["input_i"]),
        "true_peak_dbtp": float(measured["input_tp"]),
        "loudness_range": float(measured["input_lra"]),
    }
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("non-finite loudness measurement")
    return values


def _run(command, cancel_event=None):
    logger.debug(
        "FFmpeg audio command: chars=%d args=%d command=%r",
        sum(len(str(item)) + 1 for item in command), len(command), command,
    )
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
            raise RuntimeError(t("audio.cancelledUser"))
    stdout, stderr = process.communicate()
    if process.returncode:
        logger.error(
            "FFmpeg audio command failed: returncode=%s command=%r "
            "stdout=%s stderr=%s",
            process.returncode, command, stdout, stderr,
        )
        raise RuntimeError((stderr or stdout or t("errors.ffmpegAudioFailed")).strip())


def _filter_script(directory, name, filters):
    path = Path(directory) / f"{name}.txt"
    graph = ";".join(filters)
    path.write_text(graph, encoding="utf-8")
    logger.debug("FFmpeg filter script %s: %s", path, graph)
    return str(path)


def _mix_audio_files(
    ffmpeg_exe, inputs, output, duration, directory, name,
    cancel_event=None,
):
    command = [ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y"]
    for path in inputs:
        command += ["-i", str(path)]
    labels = "".join(f"[{index}:a]" for index in range(len(inputs)))
    script = _filter_script(directory, name, [
        f"{labels}amix=inputs={len(inputs)}:normalize=0:"
        f"duration=longest:dropout_transition=0,"
        f"atrim=duration={duration:.6f}[out]"
    ])
    command += [
        "-filter_complex_script", script, "-map", "[out]",
        "-ar", "44100", "-ac", "2", "-c:a", "pcm_f32le", str(output),
    ]
    _run(command, cancel_event)


def _render_ambient_batch(
    ffmpeg_exe, segments, chunk_start, chunk_duration, output,
    directory, name, cancel_event=None,
):
    command = [ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y"]
    filters = []
    labels = []
    chunk_end = chunk_start + chunk_duration
    for index, segment in enumerate(segments):
        segment_start = float(segment["start"])
        segment_end = segment_start + float(segment["duration"])
        clip_start = max(chunk_start, segment_start)
        clip_end = min(chunk_end, segment_end)
        clip_duration = clip_end - clip_start
        if segment["loop_input"]:
            command += ["-stream_loop", "-1"]
        source_offset = float(segment["source_offset"]) + (
            clip_start - segment_start
        )
        if source_offset > 0:
            command += ["-ss", f"{source_offset:.6f}"]
        command += ["-i", segment["path"]]
        gain = 10 ** (float(segment["gain_db"]) / 20)
        pan = float(segment["pan"])
        left = 1.0 if pan <= 0 else 1.0 - pan
        right = 1.0 if pan >= 0 else 1.0 + pan
        chain = (
            f"[{index}:a]atrim=duration={clip_duration:.6f},"
            "asetpts=PTS-STARTPTS,aresample=44100,"
            "aformat=sample_fmts=fltp:channel_layouts=stereo,highpass=f=20,"
            f"volume={gain:.9f},"
            f"pan=stereo|c0={left:.6f}*c0|c1={right:.6f}*c1,"
            f"extrastereo=m={float(segment['width']):.6f}"
        )
        if clip_start == segment_start and segment["fade_in"] > 0:
            chain += (
                f",afade=t=in:st=0:d={min(segment['fade_in'], clip_duration / 2):.6f}:"
                "curve=qsin"
            )
        if clip_end == segment_end and segment["fade_out"] > 0:
            fade = min(float(segment["fade_out"]), clip_duration / 2)
            chain += (
                f",afade=t=out:st={max(0, clip_duration - fade):.6f}:"
                f"d={fade:.6f}:curve=qsin"
            )
        delay_ms = max(0, round((clip_start - chunk_start) * 1000))
        label = f"s{index}"
        filters.append(f"{chain},adelay={delay_ms}:all=1[{label}]")
        labels.append(label)
    joined = "".join(f"[{label}]" for label in labels)
    filters.append(
        f"{joined}amix=inputs={len(labels)}:normalize=0:"
        "duration=longest:dropout_transition=0,"
        f"atrim=duration={chunk_duration:.6f}[out]"
    )
    script = _filter_script(directory, name, filters)
    command += [
        "-filter_complex_script", script, "-map", "[out]",
        "-ar", "44100", "-ac", "2", "-c:a", "pcm_f32le", str(output),
    ]
    _run(command, cancel_event)


def render_ambient_bus(
    ffmpeg_exe, audio_settings, duration, output_path, cancel_event=None,
):
    """Render ambience in bounded chunks so Windows commands stay short."""
    from ambient_engine import build_ambient_plan

    plan = build_ambient_plan(audio_settings, duration)
    if not plan:
        return False
    chunk_seconds = 120.0
    batch_size = 8
    with tempfile.TemporaryDirectory(prefix="apmamb_") as directory:
        chunks = []
        chunk_start = 0.0
        chunk_index = 0
        while chunk_start < duration:
            chunk_duration = min(chunk_seconds, duration - chunk_start)
            chunk_end = chunk_start + chunk_duration
            segments = [
                segment for segment in plan
                if float(segment["start"]) < chunk_end
                and float(segment["start"]) + float(segment["duration"])
                > chunk_start
            ]
            layers = []
            for batch_index in range(0, len(segments), batch_size):
                layer = Path(directory) / (
                    f"l{chunk_index:04d}_{batch_index // batch_size:03d}.wav"
                )
                _render_ambient_batch(
                    ffmpeg_exe, segments[batch_index:batch_index + batch_size],
                    chunk_start, chunk_duration, layer, directory,
                    f"f{chunk_index:04d}_{batch_index // batch_size:03d}",
                    cancel_event,
                )
                layers.append(layer)
            mix_level = 0
            while len(layers) > 1:
                combined = []
                for batch_index in range(0, len(layers), batch_size):
                    inputs = layers[batch_index:batch_index + batch_size]
                    target = Path(directory) / (
                        f"m{chunk_index:04d}_{mix_level:02d}_"
                        f"{len(combined):03d}.wav"
                    )
                    _mix_audio_files(
                        ffmpeg_exe, inputs, target, chunk_duration,
                        directory,
                        f"mf{chunk_index:04d}_{mix_level:02d}_"
                        f"{len(combined):03d}",
                        cancel_event,
                    )
                    combined.append(target)
                layers = combined
                mix_level += 1
            chunk = Path(directory) / f"c{chunk_index:04d}.wav"
            if layers:
                os.replace(layers[0], chunk)
            else:
                _run([
                    ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", f"{chunk_duration:.6f}",
                    "-c:a", "pcm_f32le", str(chunk),
                ], cancel_event)
            chunks.append(chunk)
            chunk_start = chunk_end
            chunk_index += 1
        concat_file = Path(directory) / "list.ffconcat"
        concat_file.write_text(
            "ffconcat version 1.0\n" + "".join(
                f"file '{chunk.name}'\n" for chunk in chunks
            ),
            encoding="utf-8",
        )
        _run([
            ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-af", f"apad,atrim=duration={float(duration):.6f}",
            "-ar", "44100", "-ac", "2", "-c:a", "pcm_f32le",
            str(output_path),
        ], cancel_event)
    return True


def mix_tracks_streaming(
    ffmpeg_exe, analyses, track_specs, output_path,
    crossfade_duration=4.0, cancel_event=None, audio_settings=None,
    stem_output_paths=None,
):
    """Mix trimmed tracks without loading complete audio files into Python RAM."""
    usable = [
        (analysis, spec)
        for analysis, spec in zip(analyses, track_specs, strict=False)
        if spec.get("filepath")
    ]
    if not usable:
        raise ValueError(t("errors.noTracksToMix"))

    command = [ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y"]
    starts = []
    durations = []
    for analysis, spec in usable:
        start = max(0.0, float(spec.get("trim_start", 0.0)))
        end = float(spec.get("trim_end", 0.0))
        if end <= 0:
            end = float(analysis.duration)
        duration = max(0.1, min(end, analysis.duration) - start)
        starts.append(start)
        durations.append(duration)
        # Trim in the filter graph. FFmpeg 8 can produce severely truncated
        # output when input-side -ss/-t is combined with afade + acrossfade.
        command += ["-i", spec["filepath"]]

    audio_settings = audio_settings or {}
    normalize_tracks = bool(audio_settings.get("normalize_tracks", False))
    target_lufs = float(audio_settings.get("target_lufs", -14.0))
    true_peak = float(audio_settings.get("true_peak_dbtp", -1.0))
    max_gain = max(0.0, float(
        audio_settings.get("max_auto_gain_db", 12.0)
    ))
    music_master_db = float(audio_settings.get("music_master_db", 0.0))
    filters = []
    for index, (_analysis, spec) in enumerate(usable):
        volume = max(0.0, min(4.0, float(spec.get("volume", 1.0))))
        normalize_gain = 0.0
        measured_lufs = getattr(_analysis, "integrated_lufs", None)
        measured_peak = getattr(_analysis, "true_peak_dbtp", None)
        if normalize_tracks and measured_lufs is not None:
            normalize_gain = max(-24.0, min(
                max_gain, target_lufs - float(measured_lufs)
            ))
            if measured_peak is not None:
                normalize_gain = min(
                    normalize_gain, true_peak - float(measured_peak)
                )
        total_gain_db = normalize_gain + music_master_db
        gain = volume * (10 ** (total_gain_db / 20))
        fade_in = max(0.0, min(
            float(spec.get("fade_in", 0.0)), durations[index] / 2
        ))
        fade_out = max(0.0, min(
            float(spec.get("fade_out", 0.0)), durations[index] / 2
        ))
        chain = (
            f"[{index}:a]atrim=start={starts[index]:.6f}:"
            f"duration={durations[index]:.6f},"
            "asetpts=PTS-STARTPTS,"
            "aresample=44100,"
            "aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={gain:.9f}"
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
        "source_start": starts[0],
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
            "source_start": starts[index],
            "bpm": analysis.bpm, "key": analysis.key,
            "mode": analysis.mode, "camelot": analysis.camelot,
            "transition_from": usable[index - 1][0].filename,
            "transition_at": start_time,
        })
        current = output_label

    stem_output_paths = stem_output_paths or {}
    stem_labels = {}
    music_bus = current
    if stem_output_paths.get("music"):
        filters.append(
            f"[{music_bus}]asplit=2[music_bus_main][music_stem]"
        )
        music_bus = "music_bus_main"
        current = music_bus
        stem_labels["music"] = "music_stem"
    ambient_path = None
    from ambient_engine import has_active_ambience
    if has_active_ambience(audio_settings):
        fd, ambient_path = tempfile.mkstemp(
            prefix="apmamb_", suffix=".wav"
        )
        os.close(fd)
        os.unlink(ambient_path)
        ambient_rendered = render_ambient_bus(
            ffmpeg_exe, audio_settings, elapsed, ambient_path, cancel_event
        )
        if ambient_rendered:
            ambient_input = len(usable)
            command += ["-i", ambient_path]
            filters.append(
                f"[{ambient_input}:a]atrim=duration={elapsed:.6f},"
                "asetpts=PTS-STARTPTS[ambient_bus]"
            )
            ambient_bus = "ambient_bus"
            if stem_output_paths.get("ambient"):
                filters.append(
                    "[ambient_bus]asplit=2[ambient_bus_main][ambient_stem]"
                )
                ambient_bus = "ambient_bus_main"
                stem_labels["ambient"] = "ambient_stem"
            filters.append(
                f"[{music_bus}][{ambient_bus}]amix=inputs=2:"
                "normalize=0:duration=first:dropout_transition=0[master_sum]"
            )
            current = "master_sum"

    ceiling = min(-0.1, float(
        audio_settings.get("true_peak_dbtp", -1.0)
    ))
    limit = 10 ** (ceiling / 20)
    filters.append(
        f"[{current}]alimiter=limit={limit:.9f}:level=false[master]"
    )
    current = "master"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    command += [
        "-filter_complex", ";".join(filters), "-map", f"[{current}]",
        "-c:a", "pcm_s16le", output_path,
    ]
    for stem_name, stem_label in stem_labels.items():
        stem_path = stem_output_paths.get(stem_name)
        if not stem_path:
            continue
        os.makedirs(
            os.path.dirname(os.path.abspath(stem_path)), exist_ok=True
        )
        command += [
            "-map", f"[{stem_label}]", "-c:a", "pcm_s16le", stem_path,
        ]
    try:
        _run(command, cancel_event)
    finally:
        if ambient_path:
            try:
                os.unlink(ambient_path)
            except OSError:
                pass
    return output_path, elapsed, timestamps


def mix_ambient_over_media(
    ffmpeg_exe, input_path, output_path, duration, audio_settings,
    audio_codec="aac", audio_bitrate="320k", cancel_event=None,
):
    """Add one continuous ambience timeline after a video has been repeated."""
    from ambient_engine import has_active_ambience
    if not has_active_ambience(audio_settings):
        raise ValueError("no active ambience tracks")

    duration = max(0.1, float(duration))
    fd, ambient_path = tempfile.mkstemp(prefix="apmamb_", suffix=".wav")
    os.close(fd)
    os.unlink(ambient_path)
    if not render_ambient_bus(
        ffmpeg_exe, audio_settings, duration, ambient_path, cancel_event
    ):
        raise ValueError("no resolvable active ambience sources")
    command = [
        ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y",
        "-i", input_path, "-i", ambient_path,
    ]
    filters = [
        f"[0:a]aresample=44100,"
        "aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"atrim=duration={duration:.6f},asetpts=PTS-STARTPTS[music_bus]",
        f"[1:a]atrim=duration={duration:.6f},"
        "asetpts=PTS-STARTPTS[ambient_bus]",
    ]
    filters.append(
        "[music_bus][ambient_bus]amix=inputs=2:"
        "normalize=0:duration=first:dropout_transition=0[master_sum]"
    )
    ceiling = min(
        -0.1, float(audio_settings.get("true_peak_dbtp", -1.0))
    )
    filters.append(
        f"[master_sum]alimiter=limit={10 ** (ceiling / 20):.9f}:"
        "level=false[master]"
    )
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    command += [
        "-filter_complex", ";".join(filters),
        "-map", "0:v:0", "-map", "[master]",
        "-c:v", "copy", "-c:a", audio_codec, "-b:a", str(audio_bitrate),
        "-t", f"{duration:.6f}", "-movflags", "+faststart", output_path,
    ]
    try:
        _run(command, cancel_event)
    finally:
        try:
            os.unlink(ambient_path)
        except OSError:
            pass
    return output_path


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
            t("errors.loudnormFailed", output=stderr_text[-2000:])
        )
    measured = json.loads(stderr_text[json_start:json_end])
    measured_fields = (
        "input_i", "input_tp", "input_lra", "input_thresh", "target_offset"
    )
    try:
        measurements_are_finite = all(
            math.isfinite(float(measured[field])) for field in measured_fields
        )
    except (KeyError, TypeError, ValueError):
        measurements_are_finite = False

    # Silence and extremely short clips can legitimately report -inf. FFmpeg
    # rejects those values in measured_* options, so use a safe single-pass
    # loudnorm invocation instead of failing the whole render.
    if not measurements_are_finite:
        fallback_cmd = [
            ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y",
            "-i", input_path,
            "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11",
            "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2", output_path,
        ]
        _run(fallback_cmd, cancel_event)
        return output_path

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
        "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2", output_path,
    ]
    _run(correct_cmd, cancel_event)
    return output_path
