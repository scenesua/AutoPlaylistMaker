"""트랜지션 엔진: 크로스페이드, BPM 매칭, 코드 전환"""

import numpy as np
import librosa
import soundfile as sf
from pydub import AudioSegment


def load_audio_pydub(filepath, target_sr=22050):
    audio = AudioSegment.from_file(filepath)
    audio = audio.set_frame_rate(target_sr).set_channels(1)
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    samples = samples / (np.iinfo(np.int16).max + 1)
    return samples, target_sr


def pydub_to_segment(samples, sr):
    int_samples = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    return AudioSegment(
        int_samples.tobytes(),
        frame_rate=sr,
        sample_width=2,
        channels=1,
    )


def equal_power_crossfade(fade_out, fade_in, crossfade_samples):
    if crossfade_samples <= 0:
        return np.concatenate([fade_out, fade_in])

    fade_out_overlap = fade_out[-crossfade_samples:]
    fade_in_overlap = fade_in[:crossfade_samples]

    t = np.linspace(0, np.pi / 2, crossfade_samples)
    gain_out = np.cos(t)
    gain_in = np.sin(t)

    faded_out = fade_out_overlap * gain_out
    faded_in = fade_in_overlap * gain_in

    mixed = faded_out + faded_in

    result = np.concatenate([
        fade_out[:-crossfade_samples],
        mixed,
        fade_in[crossfade_samples:],
    ])
    return result


def beat_matched_transition(analysis_a, analysis_b, samples_a, samples_b, sr,
                             crossfade_duration=4.0):
    beat_duration_a = 60.0 / analysis_a.bpm
    beat_duration_b = 60.0 / analysis_b.bpm

    crossfade_beats = max(4, int(round(crossfade_duration / beat_duration_a)))
    actual_crossfade_duration = crossfade_beats * beat_duration_a
    crossfade_samples = int(actual_crossfade_duration * sr)

    if crossfade_samples >= len(samples_a) // 2:
        crossfade_samples = len(samples_a) // 4
    if crossfade_samples >= len(samples_b) // 2:
        crossfade_samples = len(samples_b) // 4

    if crossfade_samples <= 0:
        return np.concatenate([samples_a, samples_b]), 0.0

    a_end = samples_a[-crossfade_samples:]
    b_start = samples_b[:crossfade_samples]

    min_len = min(len(a_end), len(b_start))
    a_end = a_end[-min_len:]
    b_start = b_start[:min_len]

    t = np.linspace(0, np.pi / 2, min_len)
    mixed = a_end * np.cos(t) + b_start * np.sin(t)

    result = np.concatenate([
        samples_a[:-crossfade_samples],
        mixed,
        samples_b[crossfade_samples:],
    ])
    return result, actual_crossfade_duration


def find_best_mix_point(analysis, position='end', window_beats=4):
    energy = analysis.energy_profile
    if len(energy) < 2:
        return int(len(analysis.rms) * 0.9)

    bpm = analysis.bpm
    sr = 22050
    hop_length = 512
    frames_per_segment = int(len(analysis.rms) / len(energy))

    if position == 'end':
        search_start = max(0, len(energy) - int(energy.shape[0] * 0.25))
        search_energy = energy[search_start:]
        if len(search_energy) == 0:
            return len(analysis.rms) - 1
        quietest_idx = search_start + np.argmin(search_energy)
    else:
        search_end = min(len(energy), int(energy.shape[0] * 0.25))
        search_energy = energy[:search_end]
        if len(search_energy) == 0:
            return 0
        quietest_idx = np.argmin(search_energy)

    frame_idx = quietest_idx * frames_per_segment
    frame_idx = min(frame_idx, len(analysis.rms) - 1)
    return frame_idx


def simple_mix(samples_a, samples_b, sr, crossfade_duration=4.0, bpm_a=120, bpm_b=120):
    crossfade_samples = int(crossfade_duration * sr)

    if crossfade_samples > len(samples_a) // 2:
        crossfade_samples = len(samples_a) // 3
    if crossfade_samples > len(samples_b) // 2:
        crossfade_samples = len(samples_b) // 3

    if crossfade_samples <= 0:
        # crossfade_samples가 0이면 samples_a[:-0]이 빈 배열이 되어
        # 누적된 오디오 전체가 사라지는 버그가 있었음. 크로스페이드 없이 이어붙임.
        return np.concatenate([samples_a, samples_b]), 0.0

    a_end = samples_a[-crossfade_samples:]
    b_start = samples_b[:crossfade_samples]

    min_len = min(len(a_end), len(b_start))
    a_end = a_end[-min_len:]
    b_start = b_start[:min_len]

    t = np.linspace(0, np.pi / 2, min_len)
    mixed = a_end * np.cos(t) + b_start * np.sin(t)

    result = np.concatenate([
        samples_a[:-crossfade_samples],
        mixed,
        samples_b[crossfade_samples:],
    ])
    return result, crossfade_duration


def create_mixed_audio(analyses, tracks_data, output_path, crossfade_duration=4.0):
    sr = 22050

    print("\n트랜지션 계산 중...")
    total_transition_time = 0
    timestamps = []

    if not tracks_data:
        silence = np.zeros(sr)
        sf.write(output_path, silence, sr)
        return output_path, 0.0, []

    accumulated, _ = tracks_data[0]
    acc_duration = len(accumulated) / sr
    current_time = acc_duration

    timestamps.append({
        'track_num': 1,
        'filename': analyses[0].filename,
        'start_time': 0.0,
        'end_time': acc_duration,
        'bpm': analyses[0].bpm,
        'key': analyses[0].key,
        'mode': analyses[0].mode,
        'camelot': analyses[0].camelot,
    })
    print(f"  [1] {analyses[0].filename} (시작: 00:00:00)")

    for i in range(1, len(tracks_data)):
        samples, _ = tracks_data[i]

        mix_duration = min(crossfade_duration,
                           len(accumulated) / sr / 3,
                           len(samples) / sr / 3)

        accumulated, transition_time = simple_mix(
            accumulated, samples, sr,
            crossfade_duration=mix_duration,
            bpm_a=analyses[i-1].bpm,
            bpm_b=analyses[i].bpm,
        )

        track_duration = len(samples) / sr
        transition_start = current_time - mix_duration
        current_time = current_time + track_duration - mix_duration

        timestamps.append({
            'track_num': i + 1,
            'filename': analyses[i].filename,
            'start_time': transition_start,
            'end_time': current_time,
            'bpm': analyses[i].bpm,
            'key': analyses[i].key,
            'mode': analyses[i].mode,
            'camelot': analyses[i].camelot,
            'transition_from': analyses[i-1].filename,
            'transition_at': transition_start,
        })

        total_transition_time += transition_time
        t_m = int(transition_start // 60)
        t_s = int(transition_start % 60)
        print(f"  [{i+1}] {analyses[i].filename} (전환: {t_m:02d}:{t_s:02d})")

    print(f"\n최종 오디오 정규화 중...")
    accumulated = accumulated / (np.max(np.abs(accumulated)) + 1e-8)
    accumulated = np.clip(accumulated, -1, 1)

    print(f"저장 중: {output_path}")
    sf.write(output_path, accumulated, sr)

    total_duration = len(accumulated) / sr
    print(f"완료! 총 길이: {total_duration:.1f}s ({total_duration/60:.1f}분)")

    return output_path, total_duration, timestamps
