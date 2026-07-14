"""자동 분배: 목표 영상 길이에 맞춰 BPM/키 밸런스 조절"""

import random
import numpy as np
from itertools import combinations


def bpm_range_label(bpm):
    if bpm < 90:
        return "slow"
    elif bpm < 115:
        return "mid"
    elif bpm < 140:
        return "up"
    else:
        return "fast"


def diversity_score(group):
    if len(group) < 2:
        return 0

    bpms = [t['analysis'].bpm for t in group]
    keys = [t['analysis'].key for t in group]
    modes = [t['analysis'].mode for t in group]

    bpm_std = np.std(bpms) if len(bpms) > 1 else 0
    bpm_spread = max(bpms) - min(bpms) if len(bpms) > 1 else 0

    unique_keys = len(set(keys))
    unique_modes = len(set(modes))
    key_variety = unique_keys / max(len(keys), 1)

    ranges = set(bpm_range_label(b) for b in bpms)
    range_variety = len(ranges) / max(len(bpms), 1)

    score = 0
    score += min(bpm_std, 20) * 2
    score += min(bpm_spread, 40) * 0.5
    score += key_variety * 30
    score += range_variety * 25
    score += min(unique_keys, 6) * 5

    return score


def check_harmony_flow(group):
    if len(group) < 2:
        return 0

    score = 0
    for i in range(len(group) - 1):
        a1 = group[i]['analysis']
        a2 = group[i + 1]['analysis']

        bpm_diff = abs(a1.bpm - a2.bpm)
        if bpm_diff < 5:
            score += 10
        elif bpm_diff < 15:
            score += 5
        elif bpm_diff > 30:
            score -= 5

        c1 = a1.camelot
        c2 = a2.camelot
        try:
            n1 = int(c1[:-1])
            n2 = int(c2[:-1])
            key_dist = min(abs(n1 - n2), 12 - abs(n1 - n2))
            if key_dist <= 1:
                score += 15
            elif key_dist <= 2:
                score += 8
            elif key_dist >= 5:
                score -= 5
        except (ValueError, IndexError):
            pass

    return score


def distribute_tracks(tracks, target_seconds=3600.0, tolerance=0.10,
                      max_videos=10, seed=None, progress_callback=None):
    if seed is not None:
        random.seed(seed)

    audio_tracks = [t for t in tracks if hasattr(t, 'analysis') and t.analysis is not None]
    if not audio_tracks:
        return []

    track_infos = []
    for t in audio_tracks:
        has_trim = t.trim_end > t.trim_start
        duration = t.trim_end - t.trim_start if has_trim else t.duration
        track_infos.append({
            'track': t,
            'analysis': t.analysis,
            'duration': duration,
            'filename': t.filename,
            'filepath': t.filepath,
            'trim_start': t.trim_start if has_trim else 0.0,
            'trim_end': t.trim_end if has_trim else t.duration,
        })

    track_infos.sort(key=lambda x: x['analysis'].bpm)

    min_total = target_seconds * (1 - tolerance)
    max_total = target_seconds * (1 + tolerance)

    best_groups = None
    best_score = -999999

    total_attempts = min(200, max(50, len(track_infos) * 5))
    for attempt in range(total_attempts):
        if progress_callback:
            progress_callback(attempt, total_attempts, "최적 분배 탐색 중...")
        shuffled = track_infos[:]
        if attempt == 0:
            pass
        else:
            random.shuffle(shuffled)

        groups = _greedy_fill(shuffled, target_seconds, min_total, max_total, max_videos)

        total_score = 0
        for g in groups:
            dur = sum(t['duration'] for t in g)
            dur_fit = 1.0 - abs(dur - target_seconds) / target_seconds
            dur_fit = max(0, dur_fit)

            div = diversity_score(g)
            harmony = check_harmony_flow(g)

            g_score = dur_fit * 40 + div + harmony * 0.5
            total_score += g_score

        penalty = abs(len(groups) - max(1, len(track_infos) * 60 / target_seconds)) * 5
        total_score -= penalty

        if total_score > best_score:
            best_score = total_score
            best_groups = groups

    if progress_callback:
        progress_callback(total_attempts, total_attempts, "결과 정리 중...")

    result = []
    for i, group in enumerate(best_groups):
        result.append({
            'name': f"Mix {i + 1}",
            'tracks': group,
            'total_duration': sum(t['duration'] for t in group),
            'diversity_score': diversity_score(group),
        })

    result.sort(key=lambda x: x['total_duration'], reverse=True)

    return result


def _greedy_fill(remaining_tracks, target, min_total, max_total, max_videos):
    groups = []
    current_group = []
    current_duration = 0

    tracks_left = remaining_tracks[:]

    total_available = sum(t['duration'] for t in tracks_left)
    if total_available <= target:
        return [tracks_left[:]]

    while tracks_left and len(groups) < max_videos:
        best_track = None
        best_idx = -1
        best_fit = -999

        for i, t in enumerate(tracks_left):
            new_dur = current_duration + t['duration']

            if new_dur <= max_total:
                dur_fit = 1.0 - abs(new_dur - target) / target

                temp_group = current_group + [t]
                div = diversity_score(temp_group)
                harmony = check_harmony_flow(temp_group)

                score = dur_fit * 30 + div * 0.3 + harmony * 0.2

                if best_track is None or score > best_fit:
                    best_track = t
                    best_idx = i
                    best_fit = score

        if best_track is None:
            if current_group:
                groups.append(current_group)
            current_group = []
            current_duration = 0
            if tracks_left:
                current_group.append(tracks_left.pop(0))
                current_duration = current_group[0]['duration']
            if len(groups) >= max_videos:
                if current_group:
                    groups[-1].extend(current_group)
                    current_group = []
                break
            continue

        current_group.append(best_track)
        current_duration += best_track['duration']
        tracks_left.pop(best_idx)

        if current_duration >= min_total:
            remaining_smallest = min((t['duration'] for t in tracks_left), default=0)
            if current_duration + remaining_smallest > max_total or not tracks_left:
                groups.append(current_group)
                current_group = []
                current_duration = 0

    if current_group:
        groups.append(current_group)

    if len(groups) >= 2:
        last = groups[-1]
        last_dur = sum(t['duration'] for t in last)
        if last_dur < min_total * 0.5:
            groups[-2].extend(last)
            groups.pop()

    return groups


def redistribute_for_video(video_tracks, target_seconds, tolerance=0.10):
    min_t = target_seconds * (1 - tolerance)
    max_t = target_seconds * (1 + tolerance)

    total = sum(t['duration'] for t in video_tracks)

    if min_t <= total <= max_t:
        return video_tracks, total

    if total > max_t:
        video_tracks.sort(key=lambda x: x['analysis'].bpm)
        while total > max_t and len(video_tracks) > 2:
            removed = video_tracks.pop()
            total -= removed['duration']

    return video_tracks, total


def get_distribution_summary(groups):
    lines = []
    for i, g in enumerate(groups):
        dur = g['total_duration']
        dur_m = int(dur // 60)
        dur_s = int(dur % 60)
        n = len(g['tracks'])
        bpms = [t['analysis'].bpm for t in g['tracks']]
        keys = [t['analysis'].key for t in g['tracks']]
        bpm_range = f"{min(bpms):.0f}-{max(bpms):.0f}" if bpms else "N/A"
        unique_keys = len(set(keys))

        lines.append({
            'index': i + 1,
            'name': g['name'],
            'duration': f"{int(dur)}초 ({dur_m}분 {dur_s:02d}초)",
            'duration_sec': dur,
            'track_count': n,
            'bpm_range': bpm_range,
            'unique_keys': unique_keys,
            'diversity': g.get('diversity_score', 0),
            'tracks': g['tracks'],
        })

    return lines
