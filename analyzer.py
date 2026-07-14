"""음악 분석 모듈: BPM, 키(코드), 에너지, 스펙트럼 감지"""

import librosa
import numpy as np
from dataclasses import dataclass, field


NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

CAMELOT = {
    'C': '8B', 'C#': '3B', 'D': '10B', 'D#': '5B', 'E': '12B', 'F': '7B',
    'F#': '2B', 'G': '9B', 'G#': '4B', 'A': '11B', 'A#': '6B', 'B': '1B',
    'Cm': '5A', 'C#m': '12A', 'Dm': '7A', 'D#m': '2A', 'Em': '9A', 'Fm': '4A',
    'F#m': '11A', 'Gm': '6A', 'G#m': '1A', 'Am': '8A', 'A#m': '3A', 'Bm': '10A',
}

MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


@dataclass
class TrackAnalysis:
    filepath: str
    filename: str
    bpm: float
    key: str
    mode: str
    camelot: str
    duration: float
    energy_profile: np.ndarray
    beat_times: np.ndarray
    chroma: np.ndarray
    rms: np.ndarray
    stft_magnitudes: np.ndarray = field(default_factory=lambda: np.array([]))
    stft_times: np.ndarray = field(default_factory=lambda: np.array([]))
    sr: int = 22050
    hop_length: int = 512
    waveform: np.ndarray = field(default_factory=lambda: np.array([]))


def detect_bpm(y, sr):
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    if hasattr(tempo, '__len__'):
        tempo = float(tempo[0])
    else:
        tempo = float(tempo)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return tempo, beat_times


def detect_key(y, sr):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)

    best_corr = -2
    best_key = 'C'
    best_mode = 'major'

    for i in range(12):
        rolled = np.roll(chroma_mean, -i)
        corr_major = np.corrcoef(rolled, MAJOR_PROFILE)[0, 1]
        corr_minor = np.corrcoef(rolled, MINOR_PROFILE)[0, 1]

        if corr_major > best_corr:
            best_corr = corr_major
            best_key = NOTE_NAMES[i]
            best_mode = 'major'
        if corr_minor > best_corr:
            best_corr = corr_minor
            best_key = NOTE_NAMES[i]
            best_mode = 'minor'

    return best_key, best_mode


def detect_chords_segments(y, sr, hop_length=512):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=hop_length)

    threshold = np.mean(onset_env) + np.std(onset_env)
    onset_frames = librosa.onset.onset_detect(
        y=y, sr=sr, hop_length=hop_length, onset_envelope=onset_env, backtrack=True
    )

    chords = []
    prev_idx = 0
    for frame in onset_frames:
        if frame - prev_idx < 4:
            continue
        segment_chroma = np.mean(chroma[:, prev_idx:frame], axis=1)
        chord = classify_chord(segment_chroma)
        chords.append({
            'time': float(times[prev_idx]),
            'chord': chord,
            'duration': float(times[frame] - times[prev_idx]),
        })
        prev_idx = frame

    if prev_idx < chroma.shape[1]:
        segment_chroma = np.mean(chroma[:, prev_idx:], axis=1)
        chord = classify_chord(segment_chroma)
        chords.append({
            'time': float(times[prev_idx]),
            'chord': chord,
            'duration': float(times[-1] - times[prev_idx]),
        })

    return chords


def classify_chord(chroma_vec):
    notes_present = np.argsort(chroma_vec)[::-1][:3]
    root = NOTE_NAMES[notes_present[0]]

    major_third = (notes_present[0] + 4) % 12
    minor_third = (notes_present[0] + 3) % 12

    if major_third in notes_present:
        return root
    elif minor_third in notes_present:
        return root + 'm'
    else:
        return root


def compute_energy_profile(y, sr, segment_duration=1.0):
    hop_length = 512
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    frame_duration = librosa.frames_to_time(1, sr=sr, hop_length=hop_length)

    segment_frames = int(segment_duration / frame_duration)
    n_segments = len(rms) // segment_frames

    energy = np.zeros(n_segments)
    for i in range(n_segments):
        start = i * segment_frames
        end = min((i + 1) * segment_frames, len(rms))
        energy[i] = np.mean(rms[start:end])

    return energy


def analyze_track(filepath):
    print(f"  분석 중: {filepath}")
    y, sr = librosa.load(filepath, sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    bpm, beat_times = detect_bpm(y, sr)
    key, mode = detect_key(y, sr)
    camelot = CAMELOT.get(key + ('m' if mode == 'minor' else ''), '8B')
    chords = detect_chords_segments(y, sr)
    energy = compute_energy_profile(y, sr)
    hop_length = 512
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    S = np.abs(librosa.stft(y, hop_length=hop_length))
    stft_times = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=hop_length)

    import os
    filename = os.path.basename(filepath)

    analysis = TrackAnalysis(
        filepath=filepath,
        filename=filename,
        bpm=bpm,
        key=key,
        mode=mode,
        camelot=camelot,
        duration=duration,
        energy_profile=energy,
        beat_times=beat_times,
        chroma=chroma,
        rms=rms,
        stft_magnitudes=S,
        stft_times=stft_times,
        sr=sr,
        hop_length=hop_length,
        waveform=y,
    )

    print(f"  -> BPM: {bpm:.1f} | 키: {key} {'메이저' if mode == 'major' else '마이너'} | 캠롯: {camelot} | 길이: {duration:.1f}s")

    return analysis


def find_compatible_transition(analysis_a, analysis_b):
    bpm_diff = abs(analysis_a.bpm - analysis_b.bpm)
    bpm_compatible = bpm_diff < 10

    camelot_a = analysis_a.camelot
    camelot_b = analysis_b.camelot

    num_a = int(camelot_a[:-1])
    letter_a = camelot_a[-1]
    num_b = int(camelot_b[:-1])
    letter_b = camelot_b[-1]

    key_distance = min(abs(num_a - num_b), 12 - abs(num_a - num_b))
    same_mode = letter_a == letter_b
    camelot_compatible = key_distance <= 2

    score = 0
    if bpm_compatible:
        score += 30
    score += max(0, 30 - bpm_diff * 3)

    if key_distance == 0 and same_mode:
        score += 40
    elif key_distance == 0:
        score += 30
    elif key_distance == 1:
        score += 20
    elif key_distance == 2:
        score += 10

    return {
        'bpm_diff': bpm_diff,
        'bpm_compatible': bpm_compatible,
        'key_distance': key_distance,
        'camelot_compatible': camelot_compatible,
        'score': score,
        'suggested_crossfade': max(2.0, min(8.0, 30.0 / max(bpm_diff if bpm_compatible else 5, 1) * 3)),
    }
