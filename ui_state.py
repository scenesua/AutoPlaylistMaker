"""Capture and restore page state independently from Tk widget construction."""

import tkinter as tk


_PLAIN_STATE_FIELDS = {
    "selected_group", "manual_group_idx", "distribute_mode",
    "tl_sel", "tl_px_per_sec", "playhead_sec",
}


def capture_pages(pages):
    result = []
    for page in pages:
        variables = {}
        plain = {}
        for name, value in vars(page).items():
            if isinstance(value, tk.Variable):
                try:
                    variables[name] = value.get()
                except tk.TclError:
                    pass
            elif name in _PLAIN_STATE_FIELDS:
                plain[name] = value
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
