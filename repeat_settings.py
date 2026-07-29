"""Pure repeat planning shared by UI, persistence, and rendering."""

from dataclasses import dataclass
import math
from i18n import t


MODE_COUNT = "count"
MODE_TARGET = "target"


@dataclass(frozen=True)
class RepeatPlan:
    enabled: bool
    mode: str
    base_seconds: float
    repeat_count: int
    target_seconds: float
    output_seconds: float
    overflow_seconds: float


def build_repeat_plan(
    base_seconds,
    enabled=True,
    mode=MODE_COUNT,
    repeat_count=1,
    target_seconds=0,
):
    """Return a whole-playlist repeat plan; target mode never truncates."""
    base = max(0.0, float(base_seconds))
    if not enabled or base <= 0:
        return RepeatPlan(False, mode, base, 1, 0.0, base, 0.0)

    if mode == MODE_TARGET:
        target = max(0.0, float(target_seconds))
        count = max(1, math.ceil(target / base)) if target > 0 else 1
    else:
        target = 0.0
        count = max(1, int(repeat_count))

    output = base * count
    overflow = max(0.0, output - target) if mode == MODE_TARGET else 0.0
    return RepeatPlan(True, mode, base, count, target, output, overflow)


def hms_to_seconds(hours=0, minutes=0, seconds=0):
    return (
        max(0, int(hours)) * 3600
        + max(0, int(minutes)) * 60
        + max(0, int(seconds))
    )


def format_duration(seconds):
    total = max(0, round(float(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(t("time.hours", count=hours))
    if minutes or hours:
        parts.append(t("time.minutes", count=minutes))
    parts.append(t("time.seconds", count=secs))
    return " ".join(parts)


def estimate_group_duration(group, crossfade_duration=4.0):
    """Estimate the same sequential crossfade timeline used by the mixer."""
    durations = []
    for track in group.get("tracks", []):
        analysis = track.get("analysis")
        source_duration = (
            float(analysis.duration)
            if analysis is not None
            else float(track.get("duration", 0))
        )
        start = max(0.0, float(track.get("trim_start", 0)))
        end = float(track.get("trim_end", 0))
        if end <= 0:
            end = source_duration
        durations.append(max(0.0, min(end, source_duration) - start))
    if not durations:
        return 0.0
    elapsed = durations[0]
    for duration in durations[1:]:
        fade = min(float(crossfade_duration), elapsed / 3, duration / 3)
        elapsed += duration - fade
    return elapsed
