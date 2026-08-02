"""Deterministic whole-timeline ambience planning."""

from __future__ import annotations

import hashlib
import os
import random

from ambient_library import SoundLibrary


def ambient_elements(audio_settings):
    """Expand the single UI ambience effect into internal bus elements."""
    mixer = audio_settings.get("ambience_mixer")
    if isinstance(mixer, dict):
        if not mixer.get("enabled", False):
            return []
        base_seed = int(mixer.get("random_seed", 12345))
        elements = []
        for index, (category_id, state) in enumerate(
            mixer.get("sources", {}).items()
        ):
            if not isinstance(state, dict) or not state.get("enabled", False):
                continue
            elements.append({
                "element_id": f"ambience_mixer:{category_id}",
                "category_id": category_id,
                "enabled": True,
                "volume_db": float(state.get("volume_db", -24.0)),
                "seed": base_seed + index,
            })
        elements.extend(
            item for item in mixer.get("legacy_sources", [])
            if isinstance(item, dict) and item.get("enabled", True)
        )
        return elements
    return list(audio_settings.get("ambient_tracks", []))


def has_active_ambience(audio_settings):
    return bool(ambient_elements(audio_settings))


def _stable_seed(element):
    explicit = element.get("seed")
    if explicit is not None:
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass
    identity = (
        element.get("element_id")
        or element.get("category_id")
        or element.get("filepath")
        or "ambient"
    )
    return int(hashlib.sha256(str(identity).encode()).hexdigest()[:16], 16)


def _source_records(element, library):
    records = []
    use_builtin = element.get("use_builtin", bool(element.get("category_id")))
    if use_builtin and element.get("category_id"):
        selected = element.get("asset_ids")
        assets = (
            [library.by_id[item] for item in selected if item in library.by_id]
            if isinstance(selected, list) and selected
            else library.available(element["category_id"])
        )
        if not (isinstance(selected, list) and selected):
            processed = [item for item in assets if item.get("processed")]
            if processed:
                assets = processed + [
                    item for item in assets
                    if item.get("playback_type") == "event"
                ]
        for asset in assets:
            path = library.resolve(asset["asset_id"])
            if path:
                records.append({
                    "asset_id": asset["asset_id"],
                    "path": path,
                    "playback_type": asset.get("playback_type", "hybrid"),
                    "duration": float(asset.get("duration_seconds", 0) or 0),
                })
    if element.get("use_user", True):
        user_sources = list(element.get("user_sources", []))
        if element.get("filepath"):
            user_sources.append(element["filepath"])
        for source in user_sources:
            path = (
                source.get("filepath") if isinstance(source, dict) else source
            )
            if path and os.path.isfile(path):
                playback = (
                    source.get("playback_type", "continuous")
                    if isinstance(source, dict) else "continuous"
                )
                records.append({
                    "asset_id": "",
                    "path": path,
                    "playback_type": playback,
                    "duration": float(
                        source.get("duration_seconds", 0)
                        if isinstance(source, dict) else 0
                    ),
                })
    unique = {}
    for record in records:
        unique[(record["asset_id"], os.path.normcase(record["path"]))] = record
    return list(unique.values())


def _not_same_choice(rng, sources, previous):
    if len(sources) == 1:
        return sources[0]
    available = [item for item in sources if item is not previous]
    return rng.choice(available)


def build_ambient_plan(audio_settings, duration, library=None):
    """Return deterministic segments for preview and final rendering."""
    duration = max(.1, float(duration))
    library = library or SoundLibrary()
    elements = [
        item for item in ambient_elements(audio_settings)
        if item.get("enabled", True) and not item.get("mute", False)
    ]
    if any(item.get("solo", False) for item in elements):
        elements = [item for item in elements if item.get("solo", False)]
    plan = []
    for element_index, element in enumerate(elements):
        sources = _source_records(element, library)
        if not sources:
            continue
        rng = random.Random(_stable_seed(element))
        start = max(0.0, float(element.get("start_time", 0) or 0))
        configured_end = float(element.get("end_time", 0) or 0)
        end = min(duration, configured_end) if configured_end > 0 else duration
        if end <= start:
            continue
        density = max(1.0, min(100.0, float(
            element.get("density", 50)
        )))
        variation = max(0.0, min(100.0, float(
            element.get("variation", 35)
        )))
        crossfade = max(.05, min(20.0, float(
            element.get("crossfade", 5.0)
        )))
        continuous = [
            item for item in sources
            if item["playback_type"] in {"continuous", "hybrid"}
        ]
        events = [
            item for item in sources
            if item["playback_type"] in {"event", "hybrid"}
        ]
        previous = None
        cursor = start
        while continuous and cursor < end:
            source = _not_same_choice(rng, continuous, previous)
            previous = source
            known_duration = float(source["duration"] or 0)
            source_duration = max(.25, known_duration or 45.0)
            nominal = min(
                90.0,
                max(2.0 if known_duration > 0 else 15.0,
                    source_duration * .8),
            )
            segment_duration = min(
                end - cursor,
                nominal * rng.uniform(
                    1 - variation / 250, 1 + variation / 250
                ),
            )
            if segment_duration <= .05:
                break
            source_offset = rng.uniform(
                0, max(0.0, source_duration - min(
                    source_duration, segment_duration
                ))
            )
            fade_in = min(
                segment_duration / 2,
                float(element.get("fade_in", crossfade))
                if cursor == start else crossfade,
            )
            fade_out = min(
                segment_duration / 2,
                float(element.get("fade_out", crossfade))
                if cursor + segment_duration >= end else crossfade,
            )
            plan.append(_segment(
                element, element_index, source, "continuous", cursor,
                segment_duration, source_offset, fade_in, fade_out, rng,
                variation,
            ))
            if cursor + segment_duration >= end - .001:
                break
            step = max(.05, segment_duration - crossfade)
            cursor += step

        if events:
            minimum = max(.5, float(
                element.get("event_min_interval", 8.0)
            ))
            maximum = max(minimum, float(
                element.get("event_max_interval", 40.0)
            ))
            interval_scale = 50.0 / density
            event_cursor = start + rng.uniform(
                minimum, maximum
            ) * interval_scale
            previous = None
            while event_cursor < end:
                source = _not_same_choice(rng, events, previous)
                previous = source
                event_duration = min(
                    max(.25, source["duration"] or 4.0),
                    end - event_cursor,
                )
                plan.append(_segment(
                    element, element_index, source, "event", event_cursor,
                    event_duration, 0.0, min(.03, event_duration / 4),
                    min(.08, event_duration / 4), rng, variation,
                ))
                event_cursor += rng.uniform(
                    minimum, maximum
                ) * interval_scale
    return sorted(plan, key=lambda item: (item["start"], item["element_index"]))


def _segment(
    element, element_index, source, kind, start, duration, source_offset,
    fade_in, fade_out, rng, variation,
):
    base_gain = float(element.get("volume_db", -18.0))
    gain_variation = (variation / 100) * (2.5 if kind == "event" else 1.0)
    base_pan = max(-1.0, min(1.0, float(element.get("pan", 0.0))))
    pan_variation = (variation / 100) * (.5 if kind == "event" else .12)
    return {
        "element_id": element.get("element_id", f"ambient_{element_index + 1}"),
        "element_index": element_index,
        "category_id": element.get("category_id", ""),
        "asset_id": source["asset_id"],
        "path": source["path"],
        "kind": kind,
        "start": round(start, 6),
        "duration": round(duration, 6),
        "source_offset": round(source_offset, 6),
        "fade_in": round(fade_in, 6),
        "fade_out": round(fade_out, 6),
        "gain_db": round(
            base_gain + rng.uniform(-gain_variation, gain_variation), 6
        ),
        "pan": round(max(
            -1.0, min(1.0, base_pan + rng.uniform(
                -pan_variation, pan_variation
            ))
        ), 6),
        "width": max(0.0, min(2.0, float(element.get("width", 1.0)))),
        # Known-duration continuous clips are always planned wholly inside the
        # source, so FFmpeg must not hard-wrap at the physical file boundary.
        # Unknown custom assets retain the defensive input loop fallback.
        "loop_input": (
            kind == "continuous"
            and (
                float(source.get("duration", 0) or 0) <= 0
                or source_offset + duration
                > float(source.get("duration", 0) or 0) + .001
            )
        ),
    }
