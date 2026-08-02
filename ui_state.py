"""Capture and restore page state independently from Tk widget construction."""

import copy
import tkinter as tk


_PLAIN_STATE_FIELDS = {
    "selected_group", "manual_group_idx", "distribute_mode",
    "tl_sel", "tl_px_per_sec", "playhead_sec", "clip_preview_ratio",
    "active_effect_ids", "effect_enabled_states", "effect_card_states",
    "ambience_sources", "_legacy_ambient_tracks",
    "_last_render_dir",
}


def capture_pages(pages):
    result = []
    for page in pages:
        variables = {}
        plain = {}
        if hasattr(page, "effect_cards"):
            page.effect_card_states = {
                effect_id: {
                    "expanded": card.expanded,
                    "sections": [
                        section.expanded for section in card.sections
                    ],
                }
                for effect_id, card in page.effect_cards.items()
            }
        for name, value in vars(page).items():
            if isinstance(value, tk.Variable):
                if (
                    type(page).__name__ == "Stage4DesignEffects"
                    and name in {
                        "loop_video_var", "loop_mode_var", "loop_count_var",
                        "loop_target_h_var", "loop_target_m_var",
                        "loop_target_s_var",
                    }
                ):
                    continue
                try:
                    variables[name] = value.get()
                except tk.TclError:
                    pass
            elif name in _PLAIN_STATE_FIELDS:
                plain[name] = copy.deepcopy(value)
        result.append({
            "class": type(page).__name__,
            "variables": variables,
            "plain": plain,
        })
    return result


def restore_pages(pages, states):
    by_class = {state["class"]: state for state in states}
    for page in pages:
        state = by_class.get(type(page).__name__)
        if not state:
            continue
        for name, value in state["variables"].items():
            variable = getattr(page, name, None)
            if isinstance(variable, tk.Variable):
                try:
                    variable.set(value)
                except (tk.TclError, ValueError):
                    pass
        for name, value in state["plain"].items():
            if hasattr(page, name):
                setattr(page, name, value)
        if hasattr(page, "_restore_effect_card_state"):
            page._restore_effect_card_state()
