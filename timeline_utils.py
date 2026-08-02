import math


def normalize_visibility_settings(settings=None):
    settings = dict(settings or {})
    off_after = settings.get("turn_off_after", settings.get("initial_visible", 0))
    restore_before = settings.get(
        "restore_before_end", settings.get("ending_visible", 0)
    )
    return {
        "enabled": bool(settings.get("enabled", False)),
        "turn_off_after": max(0.0, float(off_after or 0)),
        "restore_before_end": max(0.0, float(restore_before or 0)),
        "restore": bool(settings.get(
            "restore", float(restore_before or 0) > 0
        )),
        "black_color": settings.get("black_color", "#000000"),
    }


def build_repeat_plan(base_seconds, enabled=False, mode='count',
                      repeat_count=1, target_seconds=3600.0):
    if not enabled:
        return RepeatPlan(enabled=False, mode=mode, base_seconds=base_seconds,
                          repeat_count=1, output_seconds=base_seconds,
                          overflow_seconds=0.0)
    if mode == 'count':
        count = max(1, int(repeat_count))
        total = base_seconds * count
        return RepeatPlan(enabled=True, mode='count', base_seconds=base_seconds,
                          repeat_count=count, output_seconds=total,
                          overflow_seconds=0.0)
    else:
        count = max(1, math.ceil(target_seconds / base_seconds)) if base_seconds > 0 else 1
        total = base_seconds * count
        return RepeatPlan(enabled=True, mode='target', base_seconds=base_seconds,
                          repeat_count=count, output_seconds=total,
                          overflow_seconds=total - target_seconds)


class RepeatPlan:
    def __init__(self, enabled=False, mode='count', base_seconds=0.0,
                 repeat_count=1, output_seconds=0.0, overflow_seconds=0.0):
        self.enabled = enabled
        self.mode = mode
        self.base_seconds = base_seconds
        self.repeat_count = repeat_count
        self.output_seconds = output_seconds
        self.overflow_seconds = overflow_seconds

    def __repr__(self):
        return (f"RepeatPlan(enabled={self.enabled}, mode={self.mode}, "
                f"base={self.base_seconds:.1f}s, count={self.repeat_count}, "
                f"output={self.output_seconds:.1f}s, overflow={self.overflow_seconds:.1f}s)")


def should_render_visuals(current_output_time, total_output_duration,
                          initial_visible_duration=0.0,
                          ending_visible_duration=0.0,
                          visibility_enabled=False,
                          restore_before_end=True):
    if not visibility_enabled or total_output_duration <= 0:
        return True
    ivd = max(0.0, initial_visible_duration)
    evd = max(0.0, ending_visible_duration) if restore_before_end else 0.0
    t = max(0.0, current_output_time)
    total = max(0.0, total_output_duration)
    if ivd >= total:
        return True
    if restore_before_end and ivd + evd >= total:
        return True
    if t < ivd:
        return True
    if evd > 0 and t >= total - evd:
        return True
    return ivd <= 0 and evd <= 0


def resolve_output_time(global_time, repeat_plan):
    if not repeat_plan or not repeat_plan.enabled:
        return global_time
    return global_time


def resolve_repeat_info(global_time, repeat_plan):
    if not repeat_plan or not repeat_plan.enabled or repeat_plan.base_seconds <= 0:
        return 0, global_time
    rep = int(global_time // repeat_plan.base_seconds)
    if rep >= repeat_plan.repeat_count:
        rep = repeat_plan.repeat_count - 1
    local_t = global_time - rep * repeat_plan.base_seconds
    return rep, local_t


def resolve_track_at_time(global_time, track_boundaries):
    if not track_boundaries:
        return None
    lo, hi = 0, len(track_boundaries) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        tb = track_boundaries[mid]
        if global_time < tb['start']:
            hi = mid - 1
        elif global_time >= tb['end']:
            lo = mid + 1
        else:
            return tb
    if track_boundaries:
        return track_boundaries[-1]
    return None


def compute_two_track_window(selected_track_index, track_boundaries, repeat_plan=None):
    if not track_boundaries:
        return None, None
    if selected_track_index < 0 or selected_track_index >= len(track_boundaries):
        return None, None
    first = track_boundaries[selected_track_index]
    next_idx = selected_track_index + 1
    if next_idx < len(track_boundaries):
        second = track_boundaries[next_idx]
    elif repeat_plan and repeat_plan.enabled and track_boundaries:
        second = track_boundaries[0]
        second_start = first['end']
        second_end = second_start + (second['end'] - second['start'])
        second = dict(second, start=second_start, end=second_end)
    else:
        second = None
    return first, second


def estimate_group_duration(analyses, crossfade=4.0):
    from repeat_settings import estimate_group_duration as estimate
    return estimate(
        {"tracks": [
            {"analysis": analysis} for analysis in (analyses or [])
        ]},
        crossfade_duration=crossfade,
    )


def build_track_boundaries(analyses, timestamps=None, crossfade=4.0):
    if timestamps:
        return [
            {
                'start': ts.get('start_time', 0),
                'end': ts.get('end_time', 0),
                'analysis': analyses[i] if i < len(analyses) else None,
                'filename': ts.get('filename', f'track_{i}'),
            }
            for i, ts in enumerate(timestamps)
        ]
    boundaries = []
    t = 0.0
    for i, a in enumerate(analyses):
        dur = getattr(a, 'duration', 0)
        fade = min(crossfade, t / 3 if i > 0 else 0, dur / 3)
        boundaries.append({
            'start': t,
            'end': t + dur - fade,
            'analysis': a,
            'filename': getattr(a, 'filename', f'track_{i}'),
        })
        t += dur - fade
    return boundaries
