"""
Auto Playlist Maker GUI v1.3.0 - Dark theme, D2Coding font, dark/light toggle
"""

import os
import sys
import threading
import time
import webbrowser
import traceback
import datetime
import logging
import subprocess
import queue
from logging.handlers import RotatingFileHandler

_STARTUP_T0 = time.perf_counter()

import i18n as _i18n_mod
t = _i18n_mod.t

_log_dir = os.path.join(os.path.expanduser("~"), "AutoPlaylistMaker_logs")
os.makedirs(_log_dir, exist_ok=True)
_application_log = os.path.join(_log_dir, "application.log")
if not logging.getLogger().handlers:
    _handler = RotatingFileHandler(
        _application_log, maxBytes=2_000_000, backupCount=3,
        encoding="utf-8",
    )
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))
    logging.getLogger().addHandler(_handler)
    logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


def _startup_mark(stage):
    logger.info("STARTUP %.3fs %s", time.perf_counter() - _STARTUP_T0, stage)

_log_lock = threading.Lock()
def _log_error(context, exc=None):
    logger.error(context, exc_info=(
        type(exc), exc, exc.__traceback__
    ) if exc is not None else None)
    try:
        log_dir = os.path.join(os.path.expanduser("~"), "AutoPlaylistMaker_logs")
        os.makedirs(log_dir, exist_ok=True)
        with _log_lock:
            with open(os.path.join(log_dir, "error.log"), "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.datetime.now().isoformat()}] {context}\n")
                if exc:
                    f.write("".join(traceback.format_exception(
                        type(exc), exc, exc.__traceback__
                    )))
    except Exception:
        pass

if sys.platform == "win32" and getattr(sys, "frozen", False):
    import subprocess as _sp
    _orig_popen = _sp.Popen.__init__
    def _silent_popen(self, *args, **kwargs):
        kwargs.setdefault('creationflags', 0)
        kwargs['creationflags'] |= _sp.CREATE_NO_WINDOW
        _orig_popen(self, *args, **kwargs)
    _sp.Popen.__init__ = _silent_popen

    _exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    _dll_dir = os.path.join(_exe_dir, "_internal")
    if os.path.isdir(_dll_dir) and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(_dll_dir)
        os.add_dll_directory(_exe_dir)
    _path = os.environ.get("PATH", "")
    if _exe_dir not in _path:
        os.environ["PATH"] = _exe_dir + os.pathsep + _dll_dir + os.pathsep + _path
    _tcl_dir = os.path.join(_dll_dir, "_tcl_data")
    _tk_dir = os.path.join(_dll_dir, "_tk_data")
    if os.path.isdir(_tcl_dir) and "TCL_LIBRARY" not in os.environ:
        os.environ["TCL_LIBRARY"] = _tcl_dir
    if os.path.isdir(_tk_dir) and "TK_LIBRARY" not in os.environ:
        os.environ["TK_LIBRARY"] = _tk_dir

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stage4_design_effects import Stage4DesignEffects
from stage5_render import Stage5Render

_loaded = False
_analyze_track = None
_load_audio_pydub = None
_generate_video = None
_load_visual_config = None
_Project = None
_distribute_tracks = None
_get_distribution_summary = None
_np = None
_PIL_Image = None
_PIL_ImageTk = None
_PIL_ImageDraw = None
_PIL_ImageFont = None
video_gen = None
APP_VERSION = "1.3.0"
DONATION_URL = "https://toon.at/donate/scenesua"


def resource_path(filename):
    """Return a bundled resource path in source and PyInstaller builds."""
    base_dir = getattr(
        sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
    )
    return os.path.join(base_dir, filename)


def apply_window_icon(window):
    """Apply both taskbar/EXE-style and Tk window icons consistently."""
    try:
        icon_image = tk.PhotoImage(file=resource_path("app_icon.png"))
        window.iconphoto(True, icon_image)
        window._app_icon_image = icon_image
    except (OSError, tk.TclError):
        pass
    if sys.platform == "win32":
        try:
            window.iconbitmap(default=resource_path("app_icon.ico"))
        except (OSError, tk.TclError):
            pass


def _load_heavy_modules():
    global _loaded, _analyze_track, _load_audio_pydub
    global _generate_video, _load_visual_config, _Project
    global _distribute_tracks, _get_distribution_summary
    global _np, _PIL_Image, _PIL_ImageTk, _PIL_ImageDraw, _PIL_ImageFont
    global video_gen
    import numpy as _numpy
    from PIL import Image as PILImage, ImageTk as PILImageTk, ImageDraw as PILImageDraw, ImageFont as PILImageFont
    from analyzer import analyze_track as _at
    from transition import load_audio_pydub as _lap
    import video_gen as _video_gen_mod
    from video_gen import generate_video as _gv, load_visual_config as _lvc
    from project import Project as _Proj
    from distributor import distribute_tracks as _dt, get_distribution_summary as _gs
    _np = _numpy
    _PIL_Image = PILImage
    _PIL_ImageTk = PILImageTk
    _PIL_ImageDraw = PILImageDraw
    _PIL_ImageFont = PILImageFont
    _analyze_track = _at
    _load_audio_pydub = _lap
    _generate_video = _gv
    video_gen = _video_gen_mod
    _load_visual_config = _lvc
    _Project = _Proj
    _distribute_tracks = _dt
    _get_distribution_summary = _gs
    _loaded = True


def _ensure_project_module():
    global _Project
    if _Project is None:
        from project import Project
        _Project = Project


def _ensure_analysis_modules():
    global _analyze_track, _load_audio_pydub, _np
    if _analyze_track is None:
        from analyzer import analyze_track
        _analyze_track = analyze_track
    if _load_audio_pydub is None:
        from transition import load_audio_pydub
        _load_audio_pydub = load_audio_pydub
    if _np is None:
        import numpy
        _np = numpy


def _ensure_distribution_modules():
    global _distribute_tracks, _get_distribution_summary
    if _distribute_tracks is None:
        from distributor import distribute_tracks, get_distribution_summary
        _distribute_tracks = distribute_tracks
        _get_distribution_summary = get_distribution_summary

AUDIO_EXTS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus', '.aiff'}
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

FONT_PATH = None
_FONT_SEARCH = [
    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts', 'D2Coding-Ver1.3.2-20180524-all.ttc'),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts', 'D2Coding.ttf'),
    'C:/Windows/Fonts/D2Coding-Ver1.3.2-20180524-all.ttc',
    'C:/Windows/Fonts/D2Coding.ttf',
    'C:/Windows/Fonts/NSMSEUD.ttf',
]
for _fp in _FONT_SEARCH:
    if os.path.isfile(_fp):
        FONT_PATH = _fp
        break

FONT_FAMILY = "Noto Sans KR" if sys.platform == "win32" else "TkDefaultFont"

DARK = {
    'bg':        '#0b0e14',
    'bg_mid':    '#121721',
    'bg_main':   '#0f141c',
    'bg_input':  '#1b2330',
    'bg_hover':  '#263142',
    'bg_card':   '#151b25',
    'fg':        '#f0f3f8',
    'fg_dim':    '#aab4c3',
    'fg_dimmer': '#6f7b8d',
    'accent':    '#6c7cff',
    'accent_h':  '#8190ff',
    'success':   '#47c98b',
    'danger':    '#f05d6f',
    'warning':   '#e8b95a',
    'scroll_bg': '#111721',
    'scroll_fg': '#3a4658',
    'select':    '#4354d8',
    'tree_sel':  '#3446be',
    'border':    '#283244',
    'wave_bg':   '#0b0f16',
    'wave_line': '#7c8cff',
    'wave_trim': '#47c98b',
    'separator': '#252f3e',
    'border_strong': '#3a4659',
    'pressed':    '#5362d6',
    'disabled':   '#111721',
    'button':     '#1b2330',
    'slider_track': '#273244',
    'slider_fill': '#6c7cff',
    'slider_thumb': '#eef1ff',
    'panel_sash': '#3a4659',
    'media_audio': '#70c7f2',
    'media_image': '#76d49b',
    'timeline_lane': '#141b26',
    'timeline_lane_alt': '#182130',
    'timeline_grid': '#344054',
    'timeline_grid_minor': '#222c3b',
    'timeline_playhead': '#ffcc66',
    'timeline_selection': '#8b9aff',
}

LIGHT = {
    'bg':        '#eef1f6',
    'bg_mid':    '#ffffff',
    'bg_main':   '#f5f7fa',
    'bg_input':  '#ffffff',
    'bg_hover':  '#e8ecf3',
    'bg_card':   '#ffffff',
    'fg':        '#172033',
    'fg_dim':    '#566176',
    'fg_dimmer': '#8490a3',
    'accent':    '#5367e8',
    'accent_h':  '#4055d5',
    'success':   '#16865b',
    'danger':    '#d84458',
    'warning':   '#9d6b09',
    'scroll_bg': '#edf0f5',
    'scroll_fg': '#bcc4d1',
    'select':    '#5367e8',
    'tree_sel':  '#4055d5',
    'border':    '#d7dde7',
    'wave_bg':   '#edf1f6',
    'wave_line': '#5367e8',
    'wave_trim': '#16865b',
    'separator': '#e1e5ec',
    'border_strong': '#aeb8c7',
    'pressed':    '#3448bd',
    'disabled':   '#edf0f5',
    'button':     '#eef1f6',
    'slider_track': '#c7ceda',
    'slider_fill': '#5367e8',
    'slider_thumb': '#ffffff',
    'panel_sash': '#aeb8c7',
    'media_audio': '#087eae',
    'media_image': '#237a45',
    'timeline_lane': '#ffffff',
    'timeline_lane_alt': '#f2f5f9',
    'timeline_grid': '#b8c2d0',
    'timeline_grid_minor': '#dfe4eb',
    'timeline_playhead': '#b55400',
    'timeline_selection': '#4055d5',
}

THEME = DARK

def file_type(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in AUDIO_EXTS: return "audio"
    if ext in IMAGE_EXTS: return "image"
    if ext in VIDEO_EXTS: return "video"
    return "unknown"


def _font(size, bold=False):
    weight = "bold" if bold else "normal"
    return (FONT_FAMILY, size, weight)


def _pil_font(size):
    if FONT_PATH:
        try:
            from PIL import ImageFont
            return ImageFont.truetype(FONT_PATH, size)
        except Exception as error:
            _log_error("Configured preview font could not be loaded", error)
    from PIL import ImageFont
    return ImageFont.load_default()


class TrackItem:
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.filetype = file_type(filepath)
        self.analysis = None
        self.trim_start = 0.0
        self.trim_end = 0.0
        self.duration = 0.0
        self.enabled = True
        self.volume = 1.0
        self.fade_in = 0.01
        self.fade_out = 0.01
        self.effects = {}
        self.metadata = {}
        self.missing = not os.path.isfile(filepath)
        self.status = "missing" if self.missing else "pending"
        self.analysis_error = ""

    def analyze(self):
        if self.filetype != "audio": return
        self.status = "analyzing"
        self.analysis_error = ""
        try:
            _ensure_analysis_modules()
            self.analysis = _analyze_track(self.filepath)
            self.duration = self.analysis.duration
            self.trim_end = self.duration
            self.status = "completed"
        except Exception as e:
            self.status = "failed"
            self.analysis_error = str(e)
            print(t("errors.analysisFailed", name=self.filename, error=e))

    def to_dict(self):
        return {
            'filepath': self.filepath, 'filename': self.filename,
            'trim_start': self.trim_start, 'trim_end': self.trim_end,
        }


# ─── UI Helpers ───

def populate_group_tabs(container, video_groups, current_idx, on_select):
    """영상(분배 결과)이 2개 이상일 때 Mix 1 / Mix 2 ... 를 눌러 전환할 수 있는
    탭 바. 음악 편집(Stage2)과 영상 편집(Stage3)에서 공용으로 사용한다."""
    for w in container.winfo_children():
        w.destroy()
    if len(video_groups) <= 1:
        return
    styled_label(container, t("dist.groupList") + ":", size=9, color=THEME['fg_dim'],
                bg=container.cget('bg')).pack(side=tk.LEFT, padx=(0, 6))
    for i, g in enumerate(video_groups):
        active = (i == current_idx)
        n = len(g.get('tracks', []))
        dur = g.get('total_duration', 0)
        btn = styled_button(
            container, t("dist.mixTab", num=i+1, tracks=n, seconds=int(dur)) if len(video_groups) <= 4 else f"Mix {i+1}",
            command=lambda ii=i: on_select(ii),
            style="primary" if active else "default",
            padx=10, pady=4,
        )
        btn.pack(side=tk.LEFT, padx=(0, 4))


def styled_button(parent, text, command=None, style="default", **kw):
    btn_bg = THEME['accent'] if style == "primary" else THEME['bg_input']
    btn_fg = "#ffffff" if style == "primary" else THEME['fg']
    if style == "danger":
        btn_fg = THEME['danger']
    elif style == "success":
        btn_fg = THEME['success']
    action_hover = (
        THEME['danger'] if style == "danger"
        else THEME['success'] if style == "success"
        else THEME['accent_h'] if style == "primary"
        else THEME['bg_hover']
    )
    btn = tk.Button(
        parent, text=text, font=_font(10),
        bg=kw.get('bg', btn_bg), fg=kw.get('fg', btn_fg),
        activebackground=action_hover,
        activeforeground=(
            "#ffffff" if style in {"primary", "danger", "success"}
            else THEME['fg']
        ),
        disabledforeground=THEME['fg_dimmer'],
        relief=tk.FLAT, padx=kw.get('padx', 12), pady=kw.get('pady', 6),
        command=command, cursor="hand2",
        borderwidth=0, highlightthickness=1,
        highlightbackground=(
            THEME['accent'] if style == "primary" else THEME['border']
        ),
        highlightcolor=THEME['accent'],
        takefocus=True,
    )

    def paint(hovered=False):
        if str(btn.cget("state")) == tk.DISABLED:
            btn.configure(
                bg=THEME['bg_input'], fg=THEME['fg_dimmer'],
                highlightbackground=THEME['border'], cursor="",
            )
            return
        normal = (
            THEME['accent'] if style == "primary"
            else THEME['bg_input']
        )
        normal_border = (
            THEME['accent'] if style == "primary"
            else THEME['danger'] if style == "danger"
            else THEME['success'] if style == "success"
            else THEME['border']
        )
        btn.configure(
            bg=action_hover if hovered else normal,
            fg=(
                "#ffffff"
                if hovered and style in {"danger", "success"}
                else kw.get('fg', btn_fg)
            ),
            highlightbackground=action_hover if hovered else normal_border,
            cursor="hand2",
        )

    btn.bind("<Enter>", lambda _event: paint(True), add="+")
    btn.bind("<Leave>", lambda _event: paint(False), add="+")
    btn.bind("<FocusIn>", lambda _event: btn.configure(highlightbackground=THEME['accent']), add="+")
    btn.bind("<FocusOut>", lambda _event: paint(False), add="+")
    btn._paint_state = paint
    return btn


def set_button_state(button, state, **options):
    """Update a styled button without losing its disabled/active feedback."""
    button.configure(state=state, **options)
    paint = getattr(button, "_paint_state", None)
    if paint:
        paint(False)


def styled_entry(parent, textvariable=None, width=None, **kw):
    ent = ttk.Entry(
        parent, textvariable=textvariable, width=width,
        font=_font(10), style="APM.TEntry",
    )
    return ent


def styled_label(parent, text, size=10, bold=False, color=None, **kw):
    return tk.Label(
        parent, text=text, font=_font(size, bold),
        bg=kw.get('bg', THEME['bg_main']),
        fg=color or THEME['fg'], anchor=kw.get('anchor', tk.W),
    )


def styled_option_menu(parent, variable, options, **kw):
    value = options[0] if options else ""
    m = tk.OptionMenu(parent, variable, value, *options)
    m.configure(
        font=_font(10), bg=THEME['bg_input'], fg=THEME['fg'],
        activebackground=THEME['bg_hover'], activeforeground=THEME['fg'],
        highlightthickness=1, highlightbackground=THEME['border'],
        highlightcolor=THEME['accent'], relief=tk.FLAT, borderwidth=0,
        padx=6, pady=3,
    )
    m["menu"].configure(
        bg=THEME['bg_input'], fg=THEME['fg'],
        activebackground=THEME['accent'], activeforeground="#ffffff",
        borderwidth=0,
    )
    return m


def styled_choice_menu(parent, value_variable, choices, **kw):
    """Option menu that stores stable IDs while displaying translated labels.

    ``choices`` maps stable IDs to translation keys. Values restored from older
    projects may be translated labels; those are migrated to IDs immediately.
    """
    normalized = _i18n_mod.choice_id(
        value_variable.get(), choices, next(iter(choices), "")
    )
    if value_variable.get() != normalized:
        value_variable.set(normalized)

    labels = {choice_id: t(key) for choice_id, key in choices.items()}
    display_variable = tk.StringVar(value=labels.get(normalized, normalized))
    menu = styled_option_menu(parent, display_variable, list(labels.values()), **kw)
    syncing = {"active": False}

    def sync_from_value(*_):
        if syncing["active"]:
            return
        syncing["active"] = True
        try:
            choice_id = _i18n_mod.choice_id(
                value_variable.get(), choices, next(iter(choices), "")
            )
            if value_variable.get() != choice_id:
                value_variable.set(choice_id)
            display_variable.set(labels.get(choice_id, choice_id))
        finally:
            syncing["active"] = False

    def sync_from_display(*_):
        if syncing["active"]:
            return
        syncing["active"] = True
        try:
            selected = display_variable.get()
            choice_id = next(
                (item_id for item_id, label in labels.items()
                 if label == selected),
                next(iter(choices), ""),
            )
            value_variable.set(choice_id)
        finally:
            syncing["active"] = False

    value_variable.trace_add("write", sync_from_value)
    display_variable.trace_add("write", sync_from_display)
    menu._choice_display_variable = display_variable
    menu._choice_value_variable = value_variable
    menu._choice_labels = labels
    return menu


def styled_checkbutton(parent, text, variable, **kw):
    return ttk.Checkbutton(
        parent, text=text, variable=variable,
        style="APM.TCheckbutton", takefocus=True,
    )


def styled_scale(parent, variable, fr, to, res, **kw):
    scale = tk.Scale(
        parent, variable=variable, from_=fr, to=to, resolution=res,
        orient=tk.HORIZONTAL,
        bg=kw.get('bg', THEME['bg_card']), fg=THEME['fg'],
        troughcolor=THEME['slider_track'],
        activebackground=THEME['accent_h'],
        highlightthickness=1, highlightbackground=THEME['border'],
        highlightcolor=THEME['focus_ring'] if 'focus_ring' in THEME else THEME['accent'],
        sliderlength=20, sliderrelief=tk.FLAT, width=10, length=150,
        borderwidth=0, showvalue=True, takefocus=True,
    )
    try:
        scale._default_value = variable.get()
    except tk.TclError:
        scale._default_value = fr

    def reset_default(_event=None):
        variable.set(scale._default_value)
        scale.event_generate("<ButtonRelease-1>")
        return "break"

    def maybe_reset(event):
        if event.state & 0x0008:
            return reset_default(event)
        return None

    scale.bind("<Button-1>", maybe_reset, add="+")
    scale.bind("<Enter>", lambda _e: scale.configure(highlightbackground=THEME['accent']), add="+")
    scale.bind("<Leave>", lambda _e: scale.configure(highlightbackground=THEME['border']), add="+")
    _attach_tooltip(
        scale, lambda: t("progressOverlay.sliderResetHint")
    )
    return scale


def _attach_tooltip(widget, text_provider):
    state = {"after": None, "window": None}

    def hide(_event=None):
        if state["after"]:
            try:
                widget.after_cancel(state["after"])
            except tk.TclError:
                pass
            state["after"] = None
        if state["window"]:
            try:
                state["window"].destroy()
            except tk.TclError:
                pass
            state["window"] = None

    def show():
        state["after"] = None
        if not widget.winfo_exists():
            return
        tip = tk.Toplevel(widget)
        tip.overrideredirect(True)
        tip.configure(
            bg=THEME['bg_card'], highlightthickness=1,
            highlightbackground=THEME['border_strong'],
        )
        tk.Label(
            tip, text=text_provider(), font=_font(9),
            bg=THEME['bg_card'], fg=THEME['fg'],
            padx=9, pady=6,
        ).pack()
        tip.geometry(
            f"+{widget.winfo_pointerx() + 12}+"
            f"{widget.winfo_pointery() + 14}"
        )
        state["window"] = tip

    def schedule(_event=None):
        hide()
        state["after"] = widget.after(550, show)

    widget.bind("<Enter>", schedule, add="+")
    widget.bind("<Leave>", hide, add="+")
    widget.bind("<Destroy>", hide, add="+")


def styled_listbox(parent, **kw):
    lb = tk.Listbox(
        parent,
        bg=THEME['bg_input'], fg=THEME['fg'],
        selectbackground=THEME['select'], selectforeground="#ffffff",
        font=_font(10),
        relief=tk.FLAT, activestyle="none", borderwidth=0,
        highlightthickness=1, highlightbackground=THEME['border'],
        highlightcolor=THEME['accent'],
        selectborderwidth=0,
    )
    return lb


def styled_text(parent, **kw):
    return tk.Text(
        parent,
        bg=THEME['bg_input'], fg=THEME['fg'],
        insertbackground=THEME['fg'],
        selectbackground=THEME['accent'], selectforeground="#ffffff",
        font=_font(10),
        relief=tk.FLAT, borderwidth=0, highlightthickness=0,
    )


class TaskProgressOverlay:
    """Shared modal progress card driven by real worker callbacks."""

    def __init__(self, owner, title, cancellable=False, on_cancel=None):
        self.owner = owner
        self.root = owner.winfo_toplevel()
        self.on_cancel = on_cancel
        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)
        self.window.transient(self.root)
        self.window.configure(
            bg=THEME['bg_card'], highlightthickness=1,
            highlightbackground=THEME['border_strong'],
        )
        self.window.geometry("460x224")
        card = tk.Frame(self.window, bg=THEME['bg_card'], padx=24, pady=20)
        card.pack(fill=tk.BOTH, expand=True)
        styled_label(
            card, title, size=15, bold=True, bg=THEME['bg_card']
        ).pack(fill=tk.X)
        self.stage_label = styled_label(
            card, "", size=10, color=THEME['fg'], bg=THEME['bg_card']
        )
        self.stage_label.pack(fill=tk.X, pady=(14, 2))
        self.detail_label = styled_label(
            card, "", size=9, color=THEME['fg_dim'], bg=THEME['bg_card']
        )
        self.detail_label.pack(fill=tk.X)
        self.count_label = styled_label(
            card, "", size=9, color=THEME['fg_dim'], bg=THEME['bg_card']
        )
        self.count_label.pack(fill=tk.X, pady=(4, 8))
        self.progress = ttk.Progressbar(
            card, style="APM.Horizontal.TProgressbar",
            orient=tk.HORIZONTAL, mode="determinate", maximum=100,
        )
        self.progress.pack(fill=tk.X)
        self.cancel_btn = styled_button(
            card, t("common.cancel"), self._cancel, "danger", padx=12
        )
        if cancellable:
            self.cancel_btn.pack(anchor=tk.E, pady=(12, 0))
        self._root_bind = self.root.bind(
            "<Configure>", self._recenter, add="+"
        )
        self.window.protocol("WM_DELETE_WINDOW", self._cancel)
        self._recenter()
        self.window.lift()
        self.window.grab_set()

    def _recenter(self, _event=None):
        if not self.window.winfo_exists():
            return
        self.root.update_idletasks()
        width, height = 460, 224
        x = self.root.winfo_rootx() + max(
            0, (self.root.winfo_width() - width) // 2
        )
        y = self.root.winfo_rooty() + max(
            0, (self.root.winfo_height() - height) // 2
        )
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def update(self, stage, detail="", current=0, total=0):
        if not self.window.winfo_exists():
            return
        self.stage_label.configure(text=stage)
        self.detail_label.configure(text=detail)
        if total > 0:
            percent = max(0, min(100, current / total * 100))
            self.count_label.configure(
                text=t(
                    "progressOverlay.itemCount",
                    current=current, total=total, percent=int(percent),
                )
            )
            self.progress.configure(mode="determinate", value=percent)
        else:
            self.count_label.configure(text=t("progressOverlay.working"))
            self.progress.configure(mode="indeterminate")
            self.progress.start(12)

    def _cancel(self):
        if self.on_cancel:
            self.on_cancel()
            set_button_state(self.cancel_btn, tk.DISABLED)
            self.detail_label.configure(
                text=t("progressOverlay.cancelling")
            )

    def close(self):
        if not self.window.winfo_exists():
            return
        self.progress.stop()
        try:
            self.window.grab_release()
        except tk.TclError:
            pass
        if self._root_bind:
            self.root.unbind("<Configure>", self._root_bind)
        self.window.destroy()


# ─── Stage 0: 프로젝트 + 파일 가져오기 ───

class Stage0Project(tk.Frame):
    _LANG_OPTIONS = (
        ("ko-KR", "🇰🇷", "한국어"),
        ("en-US", "🇺🇸", "English"),
        ("ja-JP", "🇯🇵", "日本語"),
        ("zh-CN", "🇨🇳", "简体中文"),
        ("zh-TW", "🇹🇼", "繁體中文"),
        ("es-ES", "🇪🇸", "Español"),
        ("fr-FR", "🇫🇷", "Français"),
        ("it-IT", "🇮🇹", "Italiano"),
        ("de-DE", "🇩🇪", "Deutsch"),
        ("ru-RU", "🇷🇺", "Русский"),
        ("ar", "🇸🇦", "العربية"),
    )

    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg_main'])
        self.app = app
        self._lang_popup = None
        self._analysis_cancel_event = threading.Event()
        self._task_overlay = None
        self.build_ui()

    def _build_lang_button(self):
        header = tk.Frame(self, bg=THEME['bg_main'])
        header.pack(fill=tk.X, padx=24, pady=(18, 10))
        styled_label(
            header, t("navigation.stage0"), size=20, bold=True,
            bg=THEME['bg_main'],
        ).pack(side=tk.LEFT)
        self.lang_btn = styled_button(
            header, t("lang.button"), self._toggle_lang_popup, padx=10,
        )
        self.lang_btn.pack(side=tk.RIGHT)

    def _toggle_lang_popup(self):
        if self._lang_popup and self._lang_popup.winfo_exists():
            self._close_lang_popup()
            return
        self._open_lang_popup()

    def _open_lang_popup(self):
        root = self.winfo_toplevel()
        self._close_lang_popup()
        popup = tk.Toplevel(root, bg=THEME['bg_main'])
        popup.overrideredirect(True)
        popup.transient(root)
        self._lang_popup = popup
        self._pending_locale = _i18n_mod.get_instance().locale
        self._lang_option_widgets = {}

        popup_width, popup_height = 690, 540
        root.update_idletasks()
        x = root.winfo_rootx() + max(0, (root.winfo_width() - popup_width) // 2)
        y = root.winfo_rooty() + max(0, (root.winfo_height() - popup_height) // 2)
        x = min(max(8, x), popup.winfo_screenwidth() - popup_width - 8)
        y = min(max(8, y), popup.winfo_screenheight() - popup_height - 48)
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        card = tk.Canvas(
            popup, width=popup_width, height=popup_height,
            bg=THEME['bg_main'], highlightthickness=0,
        )
        card.pack(fill=tk.BOTH, expand=True)
        self._rounded_rect(
            card, 8, 8, popup_width - 8, popup_height - 8, 24,
            fill=THEME['bg_card'], outline=THEME['border'], width=2,
            tags=("lang_card",),
        )
        card.create_text(
            38, 34, text="🌐 " + t("lang.selectTitle"), anchor=tk.NW,
            fill=THEME['fg'], font=_font(18, True),
        )
        card.create_text(
            38, 72, text=t("lang.description"), anchor=tk.NW,
            fill=THEME['fg_dim'], font=_font(10),
        )
        close_id = card.create_text(
            popup_width - 38, 34, text="×", anchor=tk.NE,
            fill=THEME['fg_dim'], font=("Segoe UI", 20, "bold"),
            tags=("lang_close",),
        )
        card.tag_bind(close_id, "<Button-1>", lambda _e: self._close_lang_popup())
        card.tag_bind(close_id, "<Enter>", lambda _e: card.itemconfigure(close_id, fill=THEME['danger']))
        card.tag_bind(close_id, "<Leave>", lambda _e: card.itemconfigure(close_id, fill=THEME['fg_dim']))

        grid = tk.Frame(card, bg=THEME['bg_card'])
        card.create_window(32, 112, window=grid, anchor=tk.NW, width=626, height=306)
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="language")
        for index, (code, flag, native_name) in enumerate(self._LANG_OPTIONS):
            widget = self._make_language_option(
                grid, code, flag, native_name, index // 3, index % 3,
            )
            self._lang_option_widgets[code] = widget

        actions = tk.Frame(card, bg=THEME['bg_card'])
        card.create_window(340, 468, window=actions, anchor=tk.N, width=610, height=58)
        cancel = self._make_rounded_action(
            actions, t("common.cancel"), self._close_lang_popup,
            normal="#d64550", hover="#ef5964",
        )
        cancel.pack(side=tk.LEFT, padx=(64, 12))
        apply_button = self._make_rounded_action(
            actions, t("common.apply"), self._apply_pending_language,
            normal=THEME['accent'], hover=THEME['accent_h'],
        )
        apply_button.pack(side=tk.LEFT, padx=(12, 0))

        popup.bind("<Escape>", lambda _e: self._close_lang_popup())
        popup.protocol("WM_DELETE_WINDOW", self._close_lang_popup)
        popup.update_idletasks()
        popup.lift()
        popup.grab_set()
        popup.focus_force()
        logger.debug("LANG popup visible at %s,%s size=%sx%s", x, y, popup_width, popup_height)

    @staticmethod
    def _rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
        points = (
            x1 + radius, y1, x2 - radius, y1, x2, y1,
            x2, y1 + radius, x2, y2 - radius, x2, y2,
            x2 - radius, y2, x1 + radius, y2, x1, y2,
            x1, y2 - radius, x1, y1 + radius, x1, y1,
        )
        return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

    def _make_language_option(self, parent, code, flag, native_name, row, column):
        canvas = tk.Canvas(
            parent, width=192, height=62, bg=THEME['bg_card'],
            highlightthickness=0, cursor="hand2",
        )
        canvas.grid(row=row, column=column, padx=7, pady=7, sticky="nsew")
        canvas._language_code = code
        canvas._selected = False
        canvas._shape = self._rounded_rect(
            canvas, 2, 2, 190, 60, 14,
            fill=THEME['bg_input'], outline=THEME['border'], width=1,
        )
        self._draw_language_flag(canvas, code, 14, 22)
        canvas._label = canvas.create_text(
            52, 31, text=native_name, anchor=tk.W,
            fill=THEME['fg'], font=("Segoe UI", 11),
        )
        canvas._check = canvas.create_text(
            174, 31, text="", anchor=tk.CENTER,
            fill="#ffffff", font=("Segoe UI", 11, "bold"),
        )
        canvas.bind("<Button-1>", lambda _e, c=code: self._choose_pending_language(c))
        canvas.bind("<Enter>", lambda _e, w=canvas: self._paint_language_option(w, True))
        canvas.bind("<Leave>", lambda _e, w=canvas: self._paint_language_option(w, False))
        self._paint_language_option(
            canvas, False, selected=(code == self._pending_locale)
        )
        return canvas

    @staticmethod
    def _draw_language_flag(canvas, code, x, y):
        """Draw stable flag icons; Windows renders flag emoji as country letters."""
        x2, y2 = x + 28, y + 18
        canvas.create_rectangle(x, y, x2, y2, fill="#ffffff", outline="#74777d")
        if code == "ko-KR":
            canvas.create_oval(x + 9, y + 4, x + 19, y + 14, fill="#d94b55", outline="")
            canvas.create_arc(x + 9, y + 4, x + 19, y + 14, start=180, extent=180,
                              fill="#3158a5", outline="")
        elif code == "en-US":
            for stripe in range(0, 18, 4):
                canvas.create_rectangle(x, y + stripe, x2, min(y2, y + stripe + 2),
                                        fill="#d64b54", outline="")
            canvas.create_rectangle(x, y, x + 12, y + 9, fill="#31558e", outline="")
        elif code == "ja-JP":
            canvas.create_oval(x + 9, y + 4, x + 19, y + 14, fill="#d93c4a", outline="")
        elif code == "zh-CN":
            canvas.create_rectangle(x, y, x2, y2, fill="#dc3545", outline="")
            canvas.create_text(x + 7, y + 6, text="★", fill="#ffd84d", font=("Arial", 6))
        elif code == "zh-TW":
            canvas.create_rectangle(x, y, x2, y2, fill="#d93645", outline="")
            canvas.create_rectangle(x, y, x + 13, y + 9, fill="#244b9b", outline="")
            canvas.create_oval(x + 4, y + 2, x + 9, y + 7, fill="#ffffff", outline="")
        elif code == "es-ES":
            canvas.create_rectangle(x, y, x2, y + 4, fill="#c9363f", outline="")
            canvas.create_rectangle(x, y + 4, x2, y + 14, fill="#f5c943", outline="")
            canvas.create_rectangle(x, y + 14, x2, y2, fill="#c9363f", outline="")
        elif code == "fr-FR":
            canvas.create_rectangle(x, y, x + 9, y2, fill="#3156a3", outline="")
            canvas.create_rectangle(x + 19, y, x2, y2, fill="#d7444e", outline="")
        elif code == "it-IT":
            canvas.create_rectangle(x, y, x + 9, y2, fill="#319065", outline="")
            canvas.create_rectangle(x + 19, y, x2, y2, fill="#d7444e", outline="")
        elif code == "de-DE":
            canvas.create_rectangle(x, y, x2, y + 6, fill="#1b1b1b", outline="")
            canvas.create_rectangle(x, y + 6, x2, y + 12, fill="#d7444e", outline="")
            canvas.create_rectangle(x, y + 12, x2, y2, fill="#e8bd3f", outline="")
        elif code == "ru-RU":
            canvas.create_rectangle(x, y + 6, x2, y + 12, fill="#3156a3", outline="")
            canvas.create_rectangle(x, y + 12, x2, y2, fill="#d7444e", outline="")
        elif code == "ar":
            canvas.create_rectangle(x, y, x2, y2, fill="#23824d", outline="")
            canvas.create_line(x + 6, y + 12, x + 22, y + 12, fill="#ffffff", width=2)

    def _paint_language_option(self, widget, hovered=False, selected=None):
        if selected is not None:
            widget._selected = selected
        if widget._selected:
            fill, outline, width, check = THEME['accent'], "#9aa7ff", 2, "✓"
        elif hovered:
            fill, outline, width, check = THEME['bg_hover'], THEME['accent'], 2, ""
        else:
            fill, outline, width, check = THEME['bg_input'], THEME['border'], 1, ""
        widget.itemconfigure(widget._shape, fill=fill, outline=outline, width=width)
        widget.itemconfigure(widget._check, text=check)

    def _choose_pending_language(self, code):
        if code not in _i18n_mod.SUPPORTED_LOCALES:
            return
        self._pending_locale = code
        for locale, widget in self._lang_option_widgets.items():
            self._paint_language_option(widget, selected=(locale == code))

    def _make_rounded_action(self, parent, text, command, normal, hover):
        canvas = tk.Canvas(
            parent, width=220, height=48, bg=THEME['bg_card'],
            highlightthickness=0, cursor="hand2",
        )
        shape = self._rounded_rect(
            canvas, 2, 2, 218, 46, 13, fill=normal, outline=normal,
        )
        label = canvas.create_text(
            110, 24, text=text, fill="#ffffff", font=_font(11, True),
        )
        for item in (canvas,):
            item.bind("<Button-1>", lambda _e: command())
            item.bind("<Enter>", lambda _e: canvas.itemconfigure(shape, fill=hover, outline=hover))
            item.bind("<Leave>", lambda _e: canvas.itemconfigure(shape, fill=normal, outline=normal))
        canvas._action_label = label
        return canvas

    def _apply_pending_language(self):
        selected = getattr(self, "_pending_locale", _i18n_mod.get_instance().locale)
        self._select_lang(selected)

    def _close_lang_popup(self):
        if self._lang_popup:
            try:
                if self._lang_popup.winfo_exists():
                    try:
                        self._lang_popup.grab_release()
                    except tk.TclError:
                        pass
                    self._lang_popup.destroy()
            except tk.TclError:
                pass
            self._lang_popup = None
        if self.lang_btn.winfo_exists():
            self.lang_btn.focus_set()

    def _select_lang(self, code):
        self._close_lang_popup()
        if code == _i18n_mod.get_instance().locale:
            return
        app = self.app
        _i18n_mod.get_instance().locale = code
        self.lang_btn.configure(text=t("lang.button"))
        app._on_language_changed()

    def _apply_lang(self):
        self.lang_btn.configure(text=t("lang.button"))

    def build_ui(self):
        self._build_lang_button()
        top = tk.Frame(self, bg=THEME['bg_main'])
        top.pack(fill=tk.X, padx=24)

        proj_frame = tk.Frame(
            top, bg=THEME['bg_card'],
            padx=16, pady=14, borderwidth=0,
            highlightthickness=1, highlightbackground=THEME['border'],
        )
        proj_frame.pack(fill=tk.X)
        styled_label(
            proj_frame, t("project.title"), size=11, bold=True,
            bg=THEME['bg_card'],
        ).pack(fill=tk.X, anchor=tk.W, pady=(0, 10))

        row1 = tk.Frame(proj_frame, bg=THEME['bg_card'])
        row1.pack(fill=tk.X, pady=2)
        styled_label(row1, t("project.nameLabel"), size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        self.proj_name_var = tk.StringVar(value=t("project.namePlaceholder"))
        styled_entry(row1, textvariable=self.proj_name_var, width=25).pack(side=tk.LEFT, padx=8)
        styled_button(row1, t("project.new"), self.new_project, padx=10).pack(side=tk.LEFT, padx=4)
        styled_button(row1, t("project.load"), self.load_project, padx=10).pack(side=tk.LEFT, padx=2)
        styled_button(row1, t("project.relink"), self.relink_missing_files, padx=10).pack(side=tk.LEFT, padx=2)
        self.save_btn = styled_button(row1, t("common.save"), self.save_project, padx=10)
        self.save_btn.pack(side=tk.LEFT, padx=2)
        self.proj_status = styled_label(row1, "", size=9, color=THEME['success'], bg=THEME['bg_card'])
        self.proj_status.pack(side=tk.RIGHT)
        self.donation_btn = tk.Button(
            row1,
            text=t("project.donation"),
            command=self._open_donation_link,
            font=_font(9),
            bg=THEME['bg_card'],
            fg=THEME['fg_dim'],
            activebackground=THEME['bg_hover'],
            activeforeground=THEME['fg'],
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            padx=6,
            pady=2,
        )
        self.donation_btn.pack(side=tk.RIGHT, padx=(8, 2))

        row_path = tk.Frame(proj_frame, bg=THEME['bg_card'])
        row_path.pack(fill=tk.X, pady=(6, 2))
        styled_label(row_path, t("project.pathLabel"), size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        self.proj_path_var = tk.StringVar(value=os.path.abspath(t("project.pathPlaceholder")))
        styled_entry(row_path, textvariable=self.proj_path_var, width=40).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        styled_button(row_path, t("common.browse"), self._pick_proj_path, padx=8).pack(side=tk.LEFT)

        row2 = tk.Frame(proj_frame, bg=THEME['bg_card'])
        row2.pack(fill=tk.X, pady=(6, 2))
        styled_label(row2, t("project.targetDuration"), size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        self.target_h_var = tk.StringVar(value="1")
        self.target_m_var = tk.StringVar(value="0")
        self.tolerance_var = tk.StringVar(value="10")
        styled_entry(row2, textvariable=self.target_h_var, width=3).pack(side=tk.LEFT, padx=2)
        styled_label(row2, t("project.hoursUnit"), size=10, color=THEME['fg_dim'], bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_entry(row2, textvariable=self.target_m_var, width=3).pack(side=tk.LEFT, padx=2)
        styled_label(row2, t("project.minUnit"), size=10, color=THEME['fg_dim'], bg=THEME['bg_card']).pack(side=tk.LEFT, padx=(0, 12))
        styled_label(row2, t("project.tolerance"), size=10, bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_entry(row2, textvariable=self.tolerance_var, width=3).pack(side=tk.LEFT, padx=2)
        styled_label(row2, t("project.toleranceUnit"), size=10, color=THEME['fg_dim'], bg=THEME['bg_card']).pack(side=tk.LEFT)
        styled_label(row2, t("project.toleranceHelp"), size=9, color=THEME['fg_dimmer'], bg=THEME['bg_card']).pack(side=tk.LEFT)

        drop_frame = tk.Frame(self, bg=THEME['bg_main'])
        drop_frame.pack(fill=tk.X, padx=24, pady=(16, 0))
        self.drop_area = tk.Frame(
            drop_frame, bg=THEME['bg_card'],
            highlightbackground=THEME['border'],
            highlightthickness=1, highlightcolor=THEME['accent'],
        )
        self.drop_area.pack(fill=tk.X, ipady=26)
        styled_label(self.drop_area, "+", size=28, color=THEME['accent'], bg=THEME['bg_card']).pack()
        styled_label(self.drop_area, t("project.dropHint"),
                     size=12, color=THEME['fg_dim'], bg=THEME['bg_card']).pack()
        styled_label(self.drop_area, t("project.dropFormats"),
                     size=9, color=THEME['fg_dimmer'], bg=THEME['bg_card']).pack(pady=(2, 0))

        btn_frame = tk.Frame(self, bg=THEME['bg_main'])
        btn_frame.pack(fill=tk.X, padx=24, pady=(10, 0))
        styled_button(btn_frame, t("project.browseFiles"), self.browse_files, padx=14).pack(side=tk.LEFT)
        styled_button(
            btn_frame, t("project.clearAll"), self.clear_files,
            padx=14, fg=THEME['danger'],
        ).pack(side=tk.LEFT, padx=6)
        self.analyze_btn = styled_button(btn_frame, t("project.analyze"), self.start_analysis, "primary", padx=20, fg="#ffffff")
        self.analyze_btn.pack(side=tk.RIGHT)
        self.status_label = styled_label(btn_frame, "", size=9, color=THEME['fg_dim'], bg=THEME['bg_main'])
        self.status_label.pack(side=tk.RIGHT, padx=(0, 12))

        list_frame = tk.Frame(self, bg=THEME['bg_card'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(12, 20))
        cols = ("name", "type", "duration", "bpm", "key", "camelot")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="extended", height=10)
        for c, h, w in [("name", t("table.fileName"), 260), ("type", t("table.type"), 65), ("duration", t("table.duration"), 75),
                         ("bpm", t("table.bpm"), 65), ("key", t("table.key"), 95), ("camelot", t("table.camelot"), 65)]:
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, minwidth=40)

        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.tag_configure(
            "audio", foreground=THEME['media_audio']
        )
        self.tree.tag_configure(
            "image", foreground=THEME['media_image']
        )

        self._setup_dnd()

    def _open_donation_link(self):
        try:
            if not webbrowser.open_new_tab(DONATION_URL):
                raise RuntimeError(t("errors.cannotOpenBrowser"))
        except Exception as exc:
            messagebox.showerror(
                t("project.donationTitle"),
                t("errors.failedToOpenDonation", url=DONATION_URL, error=exc),
                parent=self,
            )

    def _setup_dnd(self):
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_area.drop_target_register(DND_FILES)
            self.drop_area.dnd_bind('<<Drop>>', self._on_drop)
            self.drop_area.dnd_bind('<<DropEnter>>', lambda e: self.drop_area.configure(highlightbackground=THEME['accent']))
            self.drop_area.dnd_bind('<<DropLeave>>', lambda e: self.drop_area.configure(highlightbackground=THEME['border']))
        except Exception as error:
            logger.info("Drag-and-drop unavailable: %s", error)
        for w in [self.drop_area] + self.drop_area.winfo_children():
            try:
                w.bind("<Button-1>", lambda e: self.browse_files())
            except tk.TclError as error:
                logger.debug("Could not bind drop-area child: %s", error)

    def _on_drop(self, event):
        self.drop_area.configure(highlightbackground=THEME['border'])
        try:
            self.add_files(self.tk.splitlist(event.data))
        except (AttributeError, tk.TclError, ValueError):
            try:
                self.add_files([event.data])
            except Exception as error:
                logger.warning("Dropped files could not be added: %s", error)

    def browse_files(self):
        exts = " ".join(f"*{e}" for e in AUDIO_EXTS | IMAGE_EXTS)
        files = filedialog.askopenfilenames(filetypes=[(t("common.fileType"), exts)])
        if files: self.add_files(files)

    def add_files(self, filepaths):
        existing = {t.filepath for t in self.app.tracks}
        added = 0
        for fp in filepaths:
            fp = fp.strip()
            if not os.path.exists(fp) or fp in existing: continue
            item = TrackItem(fp)
            self.app.tracks.append(item)
            existing.add(fp)
            added += 1
            tag = item.filetype if item.filetype in ("audio", "image") else "unknown"
            self.tree.insert("", tk.END, iid=str(id(item)),
                             values=(item.filename, tag.upper(), "-", "-", "-", "-"), tags=(tag,))
        self.status_label.configure(text=t("project.filesStatus", total=len(self.app.tracks), added=added))

    def add_missing_file(self, filepath, file_kind=None):
        if any(t.filepath == filepath for t in self.app.tracks):
            return
        item = TrackItem(filepath)
        item.missing = True
        if file_kind in ("audio", "image", "video"):
            item.filetype = file_kind
        self.app.tracks.append(item)
        self.tree.insert(
            "", tk.END, iid=str(id(item)),
            values=(
                item.filename or os.path.basename(filepath),
                item.filetype.upper(), t("table.missing"), "-", "-", "-"
            ),
            tags=("missing",),
        )
        self.tree.tag_configure(
            "missing", foreground=THEME['danger']
        )

    def clear_files(self):
        self.app.tracks.clear()
        for i in self.tree.get_children(): self.tree.delete(i)
        self.status_label.configure(text="")

    def start_analysis(self):
        audio = [
            track for track in self.app.tracks
            if track.filetype == "audio"
        ]
        if not audio:
            messagebox.showwarning(t("common.warning"), t("project.addMusicFirst"))
            return
        self._analysis_cancel_event = threading.Event()
        self._task_overlay = TaskProgressOverlay(
            self,
            t("progressOverlay.analysisTitle"),
            cancellable=True,
            on_cancel=self._analysis_cancel_event.set,
        )
        self._task_overlay.update(
            t("progressOverlay.checkingFiles"),
            current=0, total=len(audio),
        )
        set_button_state(
            self.analyze_btn, tk.DISABLED, text=t("project.analyzing")
        )

        def run():
            failures = []
            completed = 0
            for i, track in enumerate(audio):
                if self._analysis_cancel_event.is_set():
                    break
                self.after(
                    0,
                    lambda tt=track, ii=i: self._update_analysis_progress(
                        tt, ii, len(audio)
                    ),
                )
                track.analyze()
                completed += 1
                if not track.analysis:
                    failures.append((track.filename, track.analysis_error))
                self.after(
                    0,
                    lambda tt=track, done=completed: (
                        self._update_tree(tt),
                        self._task_overlay.update(
                            t("progressOverlay.cacheReady"),
                            tt.filename, done, len(audio),
                        ) if self._task_overlay else None,
                    ),
                )
            self.after(
                0,
                lambda: self._done(
                    cancelled=self._analysis_cancel_event.is_set(),
                    failures=failures,
                ),
            )

        threading.Thread(target=run, daemon=True).start()

    def _update_analysis_progress(self, track, index, total):
        self.status_label.configure(
            text=t(
                "project.analyzeProgress", current=index + 1,
                total=total, filename=track.filename,
            )
        )
        if self._task_overlay:
            self._task_overlay.update(
                t("progressOverlay.analyzingAudio"),
                track.filename, index, total,
            )

    def _update_tree(self, track):
        iid = str(id(track))
        if not self.tree.exists(iid): return
        if track.analysis:
            a = track.analysis
            m = "Maj" if a.mode == "major" else "Min"
            d = f"{int(a.duration//60)}:{int(a.duration%60):02d}"
            self.tree.item(iid, values=(track.filename, "AUDIO", d, f"{a.bpm:.0f}", f"{a.key} {m}", a.camelot))
        else:
            status_id = getattr(
                track, "status",
                "missing" if getattr(track, "missing", False) else "pending",
            )
            status = t(f"project.fileStatus.{status_id}")
            self.tree.item(
                iid,
                values=(
                    track.filename, track.filetype.upper(), status,
                    "-", "-", "-",
                ),
                tags=("missing",) if getattr(track, 'missing', False) else (
                    track.filetype,
                ),
            )

    def _done(self, cancelled=False, failures=None):
        if self._task_overlay:
            self._task_overlay.close()
            self._task_overlay = None
        set_button_state(
            self.analyze_btn, tk.NORMAL, text=t("project.analyze")
        )
        n = sum(1 for track in self.app.tracks if track.analysis)
        if cancelled:
            self.status_label.configure(
                text=t("progressOverlay.cancelled")
            )
        else:
            self.status_label.configure(
                text=t("project.analyzeDone", count=n)
            )
        if failures:
            detail = "\n".join(
                f"{name}: {error}" for name, error in failures[:8]
            )
            messagebox.showwarning(
                t("common.warning"),
                t(
                    "progressOverlay.partialFailure",
                    count=len(failures), detail=detail,
                ),
                parent=self,
            )
        if n > 0: self.app.enable_next(True)

    def get_target_seconds(self):
        try:
            h = int(self.target_h_var.get() or 0)
            m = int(self.target_m_var.get() or 0)
            return h * 3600 + m * 60
        except (TypeError, ValueError, tk.TclError):
            return 3600

    def get_tolerance(self):
        try:
            return float(self.tolerance_var.get()) / 100.0
        except (TypeError, ValueError, tk.TclError):
            return 0.10

    def _pick_proj_path(self):
        path = filedialog.askdirectory(title=t("project.selectSaveFolder"))
        if path: self.proj_path_var.set(path)

    def new_project(self):
        name = self.proj_name_var.get().strip()
        if not name:
            messagebox.showwarning(t("common.warning"), t("project.enterName"))
            return
        base = self.proj_path_var.get().strip() or os.path.abspath(t("project.pathPlaceholder"))
        self.app.project = _Project(base_dir=base)
        self.app.project.create(name)
        self.proj_status.configure(
            text=t(
                "project.created",
                name=name,
                path=self.app.project.project_dir,
            )
        )

    def load_project(self):
        path = filedialog.askdirectory(title=t("project.selectFolder"))
        if not path:
            return
        overlay = TaskProgressOverlay(
            self, t("progressOverlay.projectTitle")
        )
        self._task_overlay = overlay
        overlay.update(t("progressOverlay.readingProject"))

        def run():
            try:
                project = _Project()
                data = project.load(path)
                audio_files = [
                    item.get("original", "")
                    for item in project.all_files
                    if item.get("type") == "audio"
                ]
                analyses = {
                    os.path.abspath(track.get("filepath", "")):
                    track["analysis"]
                    for group in project.video_groups
                    for track in group.get("tracks", [])
                    if track.get("filepath") and track.get("analysis")
                }
                audio_total = len(audio_files)
                for index, filepath in enumerate(audio_files):
                    self.after(
                        0,
                        lambda fp=filepath, i=index, total=audio_total:
                        overlay.update(
                            t("progressOverlay.restoringCache"),
                            os.path.basename(fp), i, total,
                        ),
                    )
                    key = os.path.abspath(filepath)
                    if key not in analyses:
                        analysis = project.get_analysis_for(filepath)
                        if analysis is None and os.path.isfile(filepath):
                            analysis = _analyze_track(filepath)
                        if analysis:
                            analyses[key] = analysis
                self.after(
                    0,
                    lambda: self._finish_project_load(
                        project, data, analyses
                    ),
                )
            except Exception as error:
                self.after(
                    0,
                    lambda detail=str(error): self._fail_project_load(detail),
                )

        threading.Thread(target=run, daemon=True).start()

    def _finish_project_load(self, project, data, analyses):
        try:
            if self._task_overlay:
                self._task_overlay.update(
                    t("progressOverlay.restoringUi")
                )
            self.app.project = project
            self.clear_files()
            self.proj_name_var.set(data.get('name', ''))
            self.proj_path_var.set(os.path.dirname(self.app.project.project_dir))
            self.proj_status.configure(
                text=t(
                    "project.loaded",
                    name=data.get('name', ''),
                    path=self.app.project.project_dir,
                )
            )
            self.target_h_var.set(str(int(data.get('target_duration', 3600) // 3600)))
            self.target_m_var.set(str(int(data.get('target_duration', 3600) % 3600) // 60))
            self.tolerance_var.set(str(int(data.get('tolerance', 0.10) * 100)))
            existing_files = {
                f['original'] for f in self.app.project.all_files
                if f.get('original') and os.path.isfile(f['original'])
            }
            self.add_files(list(existing_files))
            for file_info in self.app.project.all_files:
                filepath = file_info.get('original', '')
                if filepath and not os.path.isfile(filepath):
                    self.add_missing_file(
                        filepath, file_info.get('type')
                    )

            for track in self.app.tracks:
                if track.filetype == "audio" and not track.analysis:
                    a = analyses.get(os.path.abspath(track.filepath))
                    if a:
                        track.analysis = a
                        track.duration = a.duration
                        track.trim_end = a.duration
                        self._update_tree(track)

            self.app.video_groups = self.app.project.video_groups

            for vg in self.app.video_groups:
                for track_info in vg.get('tracks', []):
                    if not track_info.get('analysis'):
                        fp = track_info.get('filepath', '')
                        a = self.app.project.get_analysis_for(fp)
                        if a:
                            track_info['analysis'] = a
                            if not track_info.get('duration'):
                                track_info['duration'] = a.duration

            n = sum(
                1 for track in self.app.tracks if track.analysis
            )
            self.status_label.configure(text=t("project.loadComplete", count=n))
            if n > 0:
                self.app.enable_next(True)
            self.app.restore_project_state(self.app.project.app_state)
            self.app.set_dirty(False)
            if self._task_overlay:
                self._task_overlay.close()
                self._task_overlay = None
        except Exception as error:
            self._fail_project_load(str(error))

    def _fail_project_load(self, detail):
        if self._task_overlay:
            self._task_overlay.close()
            self._task_overlay = None
        messagebox.showerror(
            t("common.error"),
            t("progressOverlay.projectFailed", error=detail),
            parent=self,
        )

    def save_project(self):
        if not self.app.project or not self.app.project.project_dir:
            name = self.proj_name_var.get().strip()
            if not name:
                from datetime import datetime
                name = datetime.now().strftime("mix_%Y%m%d_%H%M%S")
                self.proj_name_var.set(name)
            base = self.proj_path_var.get().strip() or os.path.abspath(t("project.pathPlaceholder"))
            self.app.project = _Project(base_dir=base)
            self.app.project.create(name)
            self.proj_status.configure(text=t("project.created", name=name, path=self.app.project.project_dir))

        self.app.project.target_duration = self.get_target_seconds()
        self.app.project.tolerance = self.get_tolerance()

        analyses = {}
        for track in self.app.tracks:
            if track.analysis:
                analyses[track.filepath] = track.analysis
        video_groups = []
        for group in self.app.video_groups:
            snapshot = dict(group)
            snapshot['tracks'] = [
                dict(track) for track in group.get('tracks', [])
            ]
            snapshot['clips'] = [
                dict(clip) for clip in group.get('clips', [])
            ]
            video_groups.append(snapshot)
        filepaths = [
            track.filepath for track in self.app.tracks
        ]
        for group in video_groups:
            filepaths.extend(
                clip.get('filepath', '')
                for clip in group.get('clips', [])
                if clip.get('filepath')
            )
        if len(self.app.stages) > 4:
            design_stage = self.app.stages[4]
            filepaths.extend(
                path for path in (
                    design_stage.bg_image.get(),
                    design_stage.album_image_var.get(),
                    design_stage.logo_image_var.get(),
                ) if path
            )
        app_state = self.app.collect_project_state()
        self.app._project_save_generation += 1

        self.save_btn.configure(state=tk.DISABLED)
        self.proj_status.configure(text=t("project.saving"))

        def _on_progress(cur, total, msg):
            self.after(0, lambda c=cur, tot=total, m=msg: self.proj_status.configure(text=t("project.saveProgress", msg=m, cur=c, total=tot)))

        def run():
            try:
                with self.app._project_save_lock:
                    self.app.project.backup_files(filepaths)
                    self.app.project.save(
                        analyses=analyses,
                        video_groups=video_groups,
                        app_state=app_state,
                        progress_callback=_on_progress,
                    )
                self.after(0, lambda: (
                    self.proj_status.configure(text=t("project.saved")),
                    self.save_btn.configure(state=tk.NORMAL),
                    self.app.set_dirty(False),
                ))
            except Exception as error:
                error_text = str(error)
                self.after(0, lambda detail=error_text: (
                    messagebox.showerror(
                        t("common.error"),
                        t("project.saveError", error=detail),
                    ),
                    self.proj_status.configure(text=t("project.saveFailedStatus")),
                    self.save_btn.configure(state=tk.NORMAL),
                ))

        threading.Thread(target=run, daemon=True).start()

    def relink_missing_files(self):
        if not self.app.project or not self.app.project.project_dir:
            messagebox.showinfo(t("project.relinkInfo"), t("project.loadFirst"))
            return
        missing = self.app.project.missing_paths()
        if not missing:
            messagebox.showinfo(t("project.relinkInfo"), t("project.noMissing"))
            return
        search_dir = filedialog.askdirectory(title=t("project.searchMissingFolder"))
        if not search_dir:
            return
        replacements = self.app.project.relink_missing(search_dir)
        for track in self.app.tracks:
            if track.filepath in replacements:
                track.filepath = replacements[track.filepath]
                track.filename = os.path.basename(track.filepath)
                track.missing = False
                self._update_tree(track)
        self.app.video_groups = self.app.project.video_groups
        self.proj_status.configure(
            text=t("project.relinkComplete", count=len(replacements), total=len(missing))
        )
        if replacements:
            self.app.persist_video_groups()
        if len(replacements) < len(missing):
            messagebox.showwarning(
                t("project.someMissing"),
                t("project.filesNotFound", count=len(missing) - len(replacements)),
            )


# ─── Stage 1: 자동 분배 ───

class Stage1Distribute(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg_main'])
        self.app = app
        self.distribute_mode = "auto"
        self.manual_group_idx = -1
        self._drag_data = {'listbox': None, 'start_idx': None}
        self.build_ui()

    def build_ui(self):
        hdr = tk.Frame(self, bg=THEME['bg_main'])
        hdr.pack(fill=tk.X, padx=24, pady=(14, 0))
        styled_label(hdr, t("dist.title"), size=20, bold=True, bg=THEME['bg_main']).pack(side=tk.LEFT)
        styled_button(hdr, t("common.save"), lambda: self.app.persist_video_groups(), padx=10).pack(side=tk.RIGHT, padx=2)

        self._mode_btn_frame = tk.Frame(self, bg=THEME['bg_main'])
        self._mode_btn_frame.pack(fill=tk.X, padx=24, pady=(6, 2))
        self.btn_auto = styled_button(self._mode_btn_frame, t("dist.auto"),
                                       lambda: self._set_mode("auto"), "primary", padx=14, pady=4)
        self.btn_auto.pack(side=tk.LEFT, padx=(0, 6))
        self.btn_manual = styled_button(self._mode_btn_frame, t("dist.manual"),
                                         lambda: self._set_mode("manual"), padx=14, pady=4)
        self.btn_manual.pack(side=tk.LEFT)

        self.desc_label = styled_label(self, "", size=11, color=THEME['fg_dim'], bg=THEME['bg_main'])
        self.desc_label.pack(pady=(2, 8))

        self.auto_frame = tk.Frame(self, bg=THEME['bg_main'])
        self.manual_frame = tk.Frame(self, bg=THEME['bg_main'])

        self._build_auto_ui()
        self._build_manual_ui()

        self._set_mode("auto")

    def _set_mode(self, mode):
        self.distribute_mode = mode
        if mode == "auto":
            self.btn_auto.configure(bg=THEME['accent'], fg="#ffffff")
            self.btn_manual.configure(bg=THEME['bg_input'], fg=THEME['fg'])
            self.desc_label.configure(text=t("dist.autoDesc"))
            self.manual_frame.pack_forget()
            self.auto_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))
        else:
            self.btn_manual.configure(bg=THEME['accent'], fg="#ffffff")
            self.btn_auto.configure(bg=THEME['bg_input'], fg=THEME['fg'])
            self.desc_label.configure(text=t("dist.manualDesc"))
            self.auto_frame.pack_forget()
            self.manual_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))
            if self.manual_group_idx < 0 and self.app.video_groups:
                self.manual_group_idx = 0
            self._refresh_manual()

    def _build_auto_ui(self):
        ctrl = tk.Frame(self.auto_frame, bg=THEME['bg_main'])
        ctrl.pack(fill=tk.X, pady=(0, 8))
        styled_button(ctrl, t("dist.autoRun"), self.run_distribute, "primary", padx=18, pady=6).pack(side=tk.LEFT)
        self.flow_preset_var = tk.StringVar(value="balanced")
        styled_choice_menu(
            ctrl, self.flow_preset_var, {
                "balanced": "dist.flowBalanced",
                "build_up": "dist.flowBuildUp",
                "calm": "dist.flowCalm",
                "peak_middle": "dist.flowPeakMiddle",
            }
        ).pack(side=tk.LEFT, padx=(8, 4))
        self.avoid_artist_var = tk.BooleanVar(value=True)
        styled_checkbutton(
            ctrl, t("dist.noSameArtist"), self.avoid_artist_var,
            bg=THEME['bg_main'],
        ).pack(side=tk.LEFT, padx=4)
        self.dist_status = styled_label(ctrl, "", size=10, color=THEME['fg_dim'], bg=THEME['bg_main'])
        self.dist_status.pack(side=tk.LEFT, padx=12)

        main = tk.PanedWindow(self.auto_frame, orient=tk.HORIZONTAL, bg=THEME['bg_main'], sashwidth=3, sashrelief=tk.FLAT)
        main.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(main, bg=THEME['bg_card'])
        main.add(left, width=350, minsize=250)
        styled_label(left, t("dist.groupList"), size=11, bold=True, bg=THEME['bg_card']).pack(pady=(10, 4), padx=10, anchor=tk.W)
        self.group_listbox = styled_listbox(left)
        self.group_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.group_listbox.bind("<<ListboxSelect>>", self.on_select_group)

        right = tk.Frame(main, bg=THEME['bg_card'])
        main.add(right, minsize=350)
        self.detail_text = styled_text(right)
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _build_manual_ui(self):
        top = tk.Frame(self.manual_frame, bg=THEME['bg_main'])
        top.pack(fill=tk.X, pady=(0, 8))
        styled_button(top, t("dist.groupAdd"), self._manual_add_group, "success", padx=12, pady=4).pack(side=tk.LEFT, padx=(0, 6))
        styled_button(top, t("dist.groupDelete"), self._manual_del_group, "danger", padx=12, pady=4).pack(side=tk.LEFT, padx=(0, 6))
        styled_button(top, t("dist.moveSelected"), self._manual_move_to_group, padx=12, pady=4).pack(side=tk.LEFT, padx=(0, 6))
        styled_button(top, t("dist.moveBack"), self._manual_move_from_group, padx=12, pady=4).pack(side=tk.LEFT)
        self._manual_status = styled_label(top, "", size=10, color=THEME['fg_dim'], bg=THEME['bg_main'])
        self._manual_status.pack(side=tk.RIGHT, padx=8)

        body = tk.Frame(self.manual_frame, bg=THEME['bg_main'])
        body.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(body, bg=THEME['bg_card'])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        styled_label(left, t("dist.allTracks"), size=11, bold=True, bg=THEME['bg_card']).pack(pady=(10, 4), padx=10, anchor=tk.W)
        self._manual_track_list = tk.Listbox(left, selectmode=tk.EXTENDED,
                                             bg=THEME['bg_input'], fg=THEME['fg'],
                                             selectbackground=THEME['select'], selectforeground="#ffffff",
                                             font=_font(10), relief=tk.FLAT, activestyle="none",
                                             highlightthickness=1, highlightbackground=THEME['border'],
                                             highlightcolor=THEME['accent'])
        self._manual_track_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self._manual_track_list.bind('<ButtonPress-1>', self._track_list_press)
        self._manual_track_list.bind('<B1-Motion>', self._track_list_drag)
        self._manual_track_list.bind('<ButtonRelease-1>', self._track_list_release)

        mid = tk.Frame(body, bg=THEME['bg_main'])
        mid.pack(side=tk.LEFT, padx=4)

        right = tk.Frame(body, bg=THEME['bg_card'])
        self._manual_group_panel = right
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        styled_label(right, t("dist.groupTracks"), size=11, bold=True, bg=THEME['bg_card']).pack(pady=(10, 4), padx=10, anchor=tk.W)
        self._manual_group_tabs = tk.Frame(right, bg=THEME['bg_card'])
        self._manual_group_tabs.pack(fill=tk.X, padx=10)
        self._manual_group_list = tk.Listbox(right, selectmode=tk.SINGLE,
                                             bg=THEME['bg_input'], fg=THEME['fg'],
                                             selectbackground=THEME['select'], selectforeground="#ffffff",
                                             font=_font(10), relief=tk.FLAT, activestyle="none",
                                             highlightthickness=1, highlightbackground=THEME['border'],
                                             highlightcolor=THEME['accent'])
        self._manual_group_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))
        self._manual_group_list.bind('<ButtonPress-1>', self._group_list_press)
        self._manual_group_list.bind('<B1-Motion>', self._group_list_drag)
        self._manual_group_list.bind('<ButtonRelease-1>', self._group_list_release)
        self._manual_group_list.bind('<Escape>', lambda e: self._clear_group_drag())

        self._drag_label = None
        self._track_drag_data = {}
        self._group_drag_data = {}
        self._group_drop_indicator = None
        self._group_drop_target = None
        self._empty_group_drop_hint = None

    def _refresh_manual(self):
        # Sync group track analysis with TrackItem to prevent stale display data
        track_analysis_map = {tr.filepath: tr.analysis for tr in self.app.tracks if tr.analysis}
        for g in self.app.video_groups:
            for ti in g.get('tracks', []):
                fp = ti.get('filepath', '')
                if fp in track_analysis_map:
                    ti['analysis'] = track_analysis_map[fp]

        # Show all tracks (including assigned) so user can re-organize
        all_tracks = [tr for tr in self.app.tracks if tr.filetype == "audio" and tr.analysis]
        assigned_fps = set()
        for g in self.app.video_groups:
            for ti in g.get('tracks', []):
                assigned_fps.add(ti.get('filepath', ''))

        self._manual_track_list.delete(0, tk.END)
        for i, tr in enumerate(all_tracks):
            a = tr.analysis
            m = "Maj" if a.mode == "major" else "Min"
            prefix = "✓ " if tr.filepath in assigned_fps else "  "
            self._manual_track_list.insert(tk.END, f"{prefix}{t('dist.trackInfo', num=i+1, filename=tr.filename, bpm=a.bpm, key=a.key, mode=m)}")
        self._manual_track_list._track_items = all_tracks

        self._refresh_group_tabs()
        self._refresh_group_list()
        unassigned_count = len(all_tracks) - len(assigned_fps)
        self._manual_status.configure(text=t("dist.unassigned", count=unassigned_count, groups=len(self.app.video_groups)))

    def _refresh_group_tabs(self):
        for w in self._manual_group_tabs.winfo_children():
            w.destroy()
        for i, g in enumerate(self.app.video_groups):
            n = len(g.get('tracks', []))
            btn = styled_button(
                                self._manual_group_tabs,
                                f"{g.get('name') or t('dist.tabMix', num=i+1)} ({n})",
                                lambda idx=i: self._select_manual_group(idx),
                                "primary",
                                padx=8, pady=2)
            btn.pack(side=tk.LEFT, padx=(0, 4))
            btn._group_index = i
            if i != self.manual_group_idx:
                btn.configure(bg=THEME['bg_input'], fg=THEME['fg'])
            if i == self._group_drop_target:
                btn.configure(
                    bg=THEME['accent_h'], fg="#ffffff",
                    highlightthickness=2,
                    highlightbackground=THEME['warning'],
                )

    def _refresh_group_list(self):
        if self._empty_group_drop_hint is not None:
            self._empty_group_drop_hint.destroy()
            self._empty_group_drop_hint = None
        self._manual_group_list.delete(0, tk.END)
        if self.manual_group_idx < 0 or self.manual_group_idx >= len(self.app.video_groups):
            self._manual_group_list._group_items = []
            self._show_empty_group_hint(create_group=True)
            return
        g = self.app.video_groups[self.manual_group_idx]
        tracks = g.get('tracks', [])
        for i, tr in enumerate(tracks):
            a = tr.get('analysis')
            if a:
                m = "Maj" if a.mode == "major" else "Min"
                self._manual_group_list.insert(tk.END, t("dist.trackInfo", num=i+1, filename=tr.get('filename',''), bpm=a.bpm, key=a.key, mode=m))
            else:
                self._manual_group_list.insert(tk.END, f"{i+1}. {tr.get('filename','')} ({t('dist.noAnalysis')})")
        self._manual_group_list._group_items = tracks
        if not tracks:
            self._manual_group_list.insert(tk.END, t("dist.dropHere"))
            self._manual_group_list.itemconfigure(
                0, foreground=THEME['fg_dimmer']
            )
            self._show_empty_group_hint(create_group=False)

    def _show_empty_group_hint(self, create_group):
        text = (
            t("dist.dragCopyHint")
            if create_group else t("dist.dropHere")
        )
        self._empty_group_drop_hint = tk.Label(
            self._manual_group_list,
            text=text,
            bg=THEME['bg_hover'],
            fg=THEME['fg_dim'],
            font=_font(10, bold=True),
            relief=tk.FLAT,
            highlightthickness=2,
            highlightbackground=THEME['border'],
            cursor="hand2",
        )
        self._empty_group_drop_hint.place(
            relx=0, rely=0, relwidth=1, relheight=1
        )

    def _select_manual_group(self, idx):
        self.manual_group_idx = idx
        self._refresh_group_tabs()
        self._refresh_group_list()

    def _on_manual_group_select(self, event):
        sel = self._manual_group_list.curselection()
        if sel:
            self.manual_group_idx = sel[0] if sel[0] < len(self.app.video_groups) else self.manual_group_idx
            self._refresh_group_tabs()

    def _manual_add_group(self):
        name = self._next_group_name()
        self.app.video_groups.append({
            'name': name,
            'tracks': [],
            'total_duration': 0,
            'bg_image': '',
        })
        self.manual_group_idx = len(self.app.video_groups) - 1
        self._refresh_manual()
        self.app.enable_next(bool(self.app.video_groups))
        self.app.persist_video_groups()

    def _manual_del_group(self):
        if self.manual_group_idx < 0 or self.manual_group_idx >= len(self.app.video_groups):
            return
        self.app.video_groups.pop(self.manual_group_idx)
        if not self.app.video_groups:
            self.manual_group_idx = -1
        elif self.manual_group_idx >= len(self.app.video_groups):
            self.manual_group_idx = max(0, len(self.app.video_groups) - 1)
        self._refresh_manual()
        self.app.enable_next(bool(self.app.video_groups))
        self.app.persist_video_groups()

    def _manual_move_to_group(self):
        sel = list(self._manual_track_list.curselection())
        self._move_unassigned_to_group(sel)

    def _next_group_name(self):
        existing = {
            str(group.get('name', '')).casefold()
            for group in self.app.video_groups
        }
        used_numbers = []
        for name in existing:
            if name.startswith("mix "):
                try:
                    used_numbers.append(int(name[4:]))
                except ValueError:
                    pass
        number = max(used_numbers, default=0) + 1
        while f"mix {number}".casefold() in existing:
            number += 1
        return f"Mix {number}"

    def _move_unassigned_to_group(self, indices):
        """Validate first, then create/append as one logical transaction."""
        items = getattr(self._manual_track_list, '_track_items', [])
        ordered_indices = sorted(set(indices))
        selected = [
            items[index] for index in ordered_indices
            if 0 <= index < len(items)
        ]
        if not selected:
            return False

        # Filter out tracks already assigned to any group
        assigned_fps = set()
        for g in self.app.video_groups:
            for ti in g.get('tracks', []):
                assigned_fps.add(ti.get('filepath', ''))
        payload = []
        try:
            for track in selected:
                if track.filepath in assigned_fps:
                    continue
                if track.analysis is None or not track.filepath:
                    raise ValueError(t("dist.invalidTrack"))
                payload.append({
                    'track': track,
                    'analysis': track.analysis,
                    'duration': track.duration,
                    'filename': track.filename,
                    'filepath': track.filepath,
                    'trim_start': track.trim_start,
                    'trim_end': (
                        track.trim_end if track.trim_end > 0
                        else track.duration
                    ),
                    'volume': getattr(track, 'volume', 1.0),
                    'fade_in': getattr(track, 'fade_in', 0.01),
                    'fade_out': getattr(track, 'fade_out', 0.01),
                })
        except (AttributeError, TypeError, ValueError) as error:
            messagebox.showerror(t("dist.moveError"), str(error))
            return False

        created_group = False
        if not self.app.video_groups:
            group = {
                'name': self._next_group_name(),
                'tracks': [],
                'total_duration': 0,
                'bg_image': '',
            }
            target_index = 0
            created_group = True
        else:
            target_index = self.manual_group_idx
            if not (0 <= target_index < len(self.app.video_groups)):
                target_index = 0
            group = self.app.video_groups[target_index]

        try:
            if created_group:
                self.app.video_groups.append(group)
            group['tracks'].extend(payload)
            group['total_duration'] = sum(
                max(
                    0,
                    item.get('trim_end', item.get('duration', 0))
                    - item.get('trim_start', 0),
                )
                for item in group['tracks']
            )
            self.manual_group_idx = target_index
        except Exception:
            if created_group and group in self.app.video_groups:
                self.app.video_groups.remove(group)
            raise

        self._refresh_manual()
        self.app.enable_next(True)
        self.app.persist_video_groups()
        return True

    def _manual_move_from_group(self):
        sel = list(self._manual_group_list.curselection())
        if not sel or self.manual_group_idx < 0 or self.manual_group_idx >= len(self.app.video_groups):
            return
        g = self.app.video_groups[self.manual_group_idx]
        tracks = g.get('tracks', [])
        for idx in sorted(sel, reverse=True):
            if idx < len(tracks):
                tracks.pop(idx)
        g['total_duration'] = sum(ti.get('duration', 0) for ti in tracks)
        self._refresh_manual()
        self.app.persist_video_groups()

    def _show_drag_label(self, widget, text, x, y):
        if self._drag_label is None:
            self._drag_label = tk.Toplevel(widget)
            self._drag_label.overrideredirect(True)
            self._drag_label.configure(bg=THEME['accent'])
            try:
                self._drag_label.attributes('-alpha', 0.78)
            except tk.TclError:
                pass
            lbl = tk.Label(self._drag_label, text=text, bg=THEME['accent'], fg="#ffffff",
                           font=_font(10, bold=True), padx=8, pady=2)
            lbl.pack()
        else:
            for w in self._drag_label.winfo_children():
                if isinstance(w, tk.Label):
                    if len(text) > 40:
                        text = text[:37] + "..."
                    w.configure(text=text)
        abs_x = widget.winfo_rootx() + x
        abs_y = widget.winfo_rooty() + y
        self._drag_label.geometry(f"+{abs_x+10}+{abs_y+10}")
        self._drag_label.deiconify()

    def _hide_drag_label(self):
        if self._drag_label:
            self._drag_label.withdraw()

    def _track_list_press(self, event):
        lb = self._manual_track_list
        idx = lb.nearest(event.y)
        if idx >= 0:
            if idx not in lb.curselection():
                if not (event.state & (0x0001 | 0x0004)):
                    lb.selection_clear(0, tk.END)
                lb.selection_set(idx)
            lb.activate(idx)
        self._track_drag_data = {
            'start_idx': idx, 'moved': False, 'widget': lb,
            'valid_target': False,
        }
        try:
            lb.grab_set()
        except tk.TclError:
            pass

    def _track_list_drag(self, event):
        dd = self._track_drag_data
        if not dd.get('widget'):
            return
        lb = dd['widget']
        items = getattr(lb, '_track_items', [])
        sel = list(lb.curselection())
        if not sel:
            return
        dd['moved'] = True
        dd['valid_target'] = self._is_group_panel_target(
            event.x_root, event.y_root
        )
        self._set_group_panel_drop_state(dd['valid_target'])
        first = sel[0]
        if first < len(items):
            name = items[first].filename
            extra = t("dist.dragExtra", count=len(sel)-1) if len(sel) > 1 else ""
            self._show_drag_label(lb, f"{name}{extra}", event.x, event.y)

    def _track_list_release(self, event):
        dd = self._track_drag_data
        self._hide_drag_label()
        self._set_group_panel_drop_state(False)
        widget = dd.get('widget')
        if widget:
            try:
                if widget.grab_current() == widget:
                    widget.grab_release()
            except tk.TclError:
                pass
        if not dd.get('moved') or not dd.get('widget'):
            self._track_drag_data = {}
            return

        lb = dd['widget']
        sel = list(lb.curselection())
        if not sel or not dd.get('valid_target'):
            self._track_drag_data = {}
            return
        self._track_drag_data = {}
        self._move_unassigned_to_group(sel)

    def _clear_track_drag(self):
        self._hide_drag_label()
        self._set_group_panel_drop_state(False)
        widget = self._track_drag_data.get('widget') if self._track_drag_data else None
        if widget:
            try:
                if widget.grab_current() == widget:
                    widget.grab_release()
            except tk.TclError:
                pass
        self._track_drag_data = {}

    def _is_group_panel_target(self, root_x, root_y):
        try:
            left = self._manual_group_panel.winfo_rootx()
            top = self._manual_group_panel.winfo_rooty()
            right = left + self._manual_group_panel.winfo_width()
            bottom = top + self._manual_group_panel.winfo_height()
            return left <= root_x <= right and top <= root_y <= bottom
        except tk.TclError:
            return False

    def _set_group_panel_drop_state(self, active):
        try:
            color = THEME['accent'] if active else THEME['border']
            self._manual_group_list.configure(highlightbackground=color)
            if self._empty_group_drop_hint is not None:
                self._empty_group_drop_hint.configure(
                    highlightbackground=color,
                    bg=THEME['bg_hover'] if active else THEME['bg_input'],
                )
        except tk.TclError:
            pass

    def _group_list_press(self, event):
        lb = self._manual_group_list
        idx = lb.nearest(event.y)
        if idx >= 0:
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
            lb.activate(idx)
        self._clear_group_drag()
        self._group_drag_data = {
            'start_idx': idx, 'moved': False, 'widget': lb,
            'insert_at': None, 'source_group': self.manual_group_idx,
            'item': (
                self.app.video_groups[self.manual_group_idx]['tracks'][idx]
                if (
                    0 <= self.manual_group_idx < len(self.app.video_groups)
                    and 0 <= idx < len(
                        self.app.video_groups[self.manual_group_idx].get(
                            'tracks', []
                        )
                    )
                )
                else None
            ),
        }
        try:
            lb.grab_set()
        except tk.TclError:
            pass
        lb.configure(cursor='hand2')

    def _group_list_drag(self, event):
        dd = self._group_drag_data
        if not dd.get('widget'):
            return
        lb = dd['widget']
        start = dd.get('start_idx', -1)
        if start < 0:
            return
        dd['moved'] = True
        target = lb.winfo_containing(event.x_root, event.y_root)
        while target is not None and not hasattr(target, '_group_index'):
            target = target.master
        if target is not None:
            target_index = target._group_index
            self._group_drop_target = target_index
            if target_index != self.manual_group_idx:
                self.manual_group_idx = target_index
                self._refresh_group_tabs()
                self._refresh_group_list()
            dd['insert_at'] = len(
                self.app.video_groups[target_index].get('tracks', [])
            )
            self._show_group_drop_indicator(2)
            return
        if self._group_drop_target is not None:
            self._group_drop_target = None
            self._refresh_group_tabs()
        g = self.app.video_groups[self.manual_group_idx] if 0 <= self.manual_group_idx < len(self.app.video_groups) else None
        if not g:
            return
        tracks = g.get('tracks', [])
        if dd.get('item') is not None:
            if (
                event.x < 0 or event.x > lb.winfo_width()
                or event.y < -20 or event.y > lb.winfo_height() + 20
            ):
                dd['insert_at'] = None
                if self._group_drop_indicator is not None:
                    self._group_drop_indicator.place_forget()
                self._hide_drag_label()
                return
            insert_at, indicator_y = self._group_insert_position(event.y)
            dd['insert_at'] = insert_at
            self._show_group_drop_indicator(indicator_y)
            name = dd['item'].get('filename', '')
            position = min(insert_at + 1, len(tracks))
            self._show_drag_label(
                lb, t("dist.dragPosition", name=name, position=position), event.x, event.y
            )
            lb.configure(cursor='fleur')

    def _group_list_release(self, event):
        dd = self._group_drag_data
        if not dd.get('moved') or not dd.get('widget'):
            self._clear_group_drag()
            return

        start = dd['start_idx']
        source_group = dd.get('source_group', self.manual_group_idx)
        insert_at = dd.get('insert_at')
        if insert_at is None:
            self._clear_group_drag()
            return

        if self.manual_group_idx < 0 or self.manual_group_idx >= len(self.app.video_groups):
            self._clear_group_drag()
            return
        source = self.app.video_groups[source_group]
        target = self.app.video_groups[self.manual_group_idx]
        source_tracks = source.get('tracks', [])
        target_tracks = target.get('tracks', [])
        if not (0 <= start < len(source_tracks)):
            self._clear_group_drag()
            return

        item = source_tracks.pop(start)
        if source_group == self.manual_group_idx and insert_at > start:
            insert_at -= 1
        insert_at = max(0, min(insert_at, len(target_tracks)))
        target_tracks.insert(insert_at, item)
        source['total_duration'] = sum(
            max(0, item.get('trim_end', item.get('duration', 0))
                - item.get('trim_start', 0))
            for item in source_tracks
        )
        target['total_duration'] = sum(
            max(0, item.get('trim_end', item.get('duration', 0))
                - item.get('trim_start', 0))
            for item in target_tracks
        )
        self._clear_group_drag()
        self._refresh_group_list()
        self._manual_group_list.selection_set(insert_at)
        self._manual_group_list.activate(insert_at)
        self.app.persist_video_groups()

    def _group_insert_position(self, pointer_y):
        lb = self._manual_group_list
        if (
            0 <= self.manual_group_idx < len(self.app.video_groups)
            and not self.app.video_groups[self.manual_group_idx].get('tracks')
        ):
            return 0, max(2, lb.winfo_height() // 2)
        size = lb.size()
        if size <= 0:
            return 0, 2
        first_box = lb.bbox(0)
        last_box = lb.bbox(size - 1)
        if not first_box or not last_box:
            return 0, 2
        if pointer_y <= first_box[1]:
            return 0, first_box[1]
        last_bottom = last_box[1] + last_box[3]
        if pointer_y >= last_bottom:
            return size, last_bottom
        idx = max(0, min(lb.nearest(pointer_y), size - 1))
        box = lb.bbox(idx)
        if not box:
            return size, last_bottom
        before = pointer_y < box[1] + box[3] / 2
        return (idx, box[1]) if before else (idx + 1, box[1] + box[3])

    def _show_group_drop_indicator(self, y):
        lb = self._manual_group_list
        if self._group_drop_indicator is None:
            shade = tk.Frame(lb, bg='#17181b', height=10)
            line = tk.Frame(shade, bg=THEME['accent'], height=3)
            line.place(relx=0.03, rely=0.5, relwidth=0.94, anchor=tk.W)
            self._group_drop_indicator = shade
        self._group_drop_indicator.place(
            x=2, y=max(0, int(y) - 5), relwidth=1.0, width=-4, height=10
        )
        self._group_drop_indicator.lift()
        self._group_drop_indicator.update_idletasks()

    def _clear_group_drag(self):
        self._hide_drag_label()
        if self._group_drop_indicator is not None:
            self._group_drop_indicator.place_forget()
        widget = self._group_drag_data.get('widget') if self._group_drag_data else None
        if widget:
            try:
                if widget.grab_current() == widget:
                    widget.grab_release()
                widget.configure(cursor='')
            except tk.TclError:
                pass
        self._group_drag_data = {}
        if self._group_drop_target is not None:
            self._group_drop_target = None
            if self.winfo_exists():
                self._refresh_group_tabs()

    def on_hide(self):
        self._clear_group_drag()
        self._clear_track_drag()

    def refresh(self):
        if self.distribute_mode == "auto":
            self.group_listbox.delete(0, tk.END)
            for i, g in enumerate(self.app.video_groups):
                dur = g.get('total_duration', 0)
                n = len(g.get('tracks', []))
                self.group_listbox.insert(tk.END, t("dist.groupEntry", num=i+1, count=n, seconds=int(dur), minutes=int(dur//60), secs=int(dur%60)))
            self._show_detail(None)
        else:
            self._refresh_manual()

    def on_select_group(self, event):
        sel = self.group_listbox.curselection()
        if not sel: return
        self._show_detail(sel[0])

    def _show_detail(self, idx):
        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        if idx is None or idx >= len(self.app.video_groups):
            self.detail_text.insert("1.0", t("dist.selectGroup"))
            self.detail_text.configure(state=tk.DISABLED)
            return
        g = self.app.video_groups[idx]
        lines = [t("dist.mixSummary", idx=idx+1, name=g.get('name','')),
                 t("dist.totalDuration", duration=g.get('total_duration',0), minutes=int(g.get('total_duration',0)//60), seconds=int(g.get('total_duration',0)%60)),
                 t("dist.trackCount", count=len(g.get('tracks',[]))), ""]
        for j, tr in enumerate(g.get('tracks', [])):
            a = tr.get('analysis')
            if a:
                m = "Maj" if a.mode == "major" else "Min"
                dur = tr.get('duration', a.duration)
                lines.append(t("dist.detailTrackNum", num=j+1, filename=tr.get('filename','')))
                lines.append(t("dist.detailTrackAnalysis", bpm=a.bpm, key=a.key, mode=m, camelot=a.camelot, duration=dur))
            else:
                lines.append(f"  [{j+1}] {tr.get('filename','')} ({t('dist.noAnalysis')})")
        self.detail_text.insert("1.0", "\n".join(lines))
        self.detail_text.configure(state=tk.DISABLED)

    def run_distribute(self):
        audio_tracks = [tr for tr in self.app.tracks if tr.filetype == "audio" and tr.analysis]
        if not audio_tracks:
            messagebox.showwarning(t("common.warning"), t("dist.noAnalyzedTracks"))
            return
        target = self.app.stages[0].get_target_seconds()
        tol = self.app.stages[0].get_tolerance()
        n = len(audio_tracks)
        self.dist_status.configure(text=t("dist.distributing", count=0, total=n))
        flow_preset = _i18n_mod.choice_id(
            self.flow_preset_var.get(),
            {
                "balanced": "dist.flowBalanced",
                "build_up": "dist.flowBuildUp",
                "calm": "dist.flowCalm",
                "peak_middle": "dist.flowPeakMiddle",
            },
            "balanced",
        )
        avoid_same_artist = self.avoid_artist_var.get()

        def _on_progress(current, total, msg):
            self.after(0, lambda c=current, tt=total, m=msg: self.dist_status.configure(text=f"{m} {c+1}/{tt}"))

        def run():
            try:
                _ensure_distribution_modules()
                groups = _distribute_tracks(
                    audio_tracks, target, tol, progress_callback=_on_progress,
                    preset=flow_preset,
                    avoid_same_artist=avoid_same_artist,
                )
                for g in groups:
                    for ti in g['tracks']:
                        ti['analysis'] = ti['track'].analysis

                def _apply():
                    self.app.video_groups = groups
                    self.refresh()
                    self.dist_status.configure(text=t("dist.groupsCreated", count=len(groups)))
                    self.app.enable_next(bool(groups))
                    self.app.persist_video_groups()
                self.after(0, _apply)
            except Exception as e:
                def _show_error(error=e):
                    self.dist_status.configure(text=t("dist.distributeFailed"))
                    messagebox.showerror(t("common.error"), str(error))
                self.after(0, _show_error)
        threading.Thread(target=run, daemon=True).start()


# ─── Stage 2: 음악 편집 (타임라인) ───

_TIMELINE_COLORS = ['#5865f2', '#57f287', '#fee75c', '#ed4245', '#eb459e',
                     '#ff9063', '#3ba55c', '#5865f2', '#e67e22', '#9b59b6']
MIN_TRIM_SECONDS = 0.25

def _fmt_ts(sec):
    m = int(sec) // 60
    s = int(sec) % 60
    return f"{m}:{s:02d}"


def _waveform_peaks(samples, max_peaks=1200):
    chunk = max(1, len(samples) // max_peaks)
    usable = len(samples) - (len(samples) % chunk)
    body = samples[:usable].reshape(-1, chunk)
    peaks = list(zip(
        body.min(axis=1).astype(float),
        body.max(axis=1).astype(float),
        strict=False,
    ))
    if usable < len(samples):
        tail = samples[usable:]
        peaks.append((float(tail.min()), float(tail.max())))
    return peaks


class Stage2MusicEdit(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg_main'])
        self.app = app
        self.selected_group = -1
        self.tl_sel = -1
        self.tl_drag = None
        self.tl_px_per_sec = 8
        self.tl_scroll_x = 0
        self.playhead_sec = 0.0
        self._drop_index = None
        self.LANE_H = 56
        self._waveform_cache = {}
        self._waveform_loading = set()
        self._history = []
        self._history_index = -1
        self._preview_player = None
        self._audio_preview_after_id = None
        self._audio_preview_started = 0.0
        self._audio_preview_duration = 0.0
        self._audio_preview_timeline_start = 0.0
        self._updating_track_controls = False
        self._zoom_after_id = None
        self.build_ui()

    def build_ui(self):
        styled_label(self, t("audio.title"), size=20, bold=True, bg=THEME['bg_main']).pack(pady=(14, 2))
        styled_label(self, t("audio.helpTimeline"),
                     size=11, color=THEME['fg_dim'], bg=THEME['bg_main']).pack(pady=(0, 6))

        top = tk.Frame(self, bg=THEME['bg_main'])
        top.pack(fill=tk.X, padx=24)
        self.tabs_container = tk.Frame(top, bg=THEME['bg_main'])
        self.tabs_container.pack(side=tk.LEFT)

        styled_button(top, t("common.save"), lambda: self.app.persist_video_groups(), padx=10).pack(side=tk.RIGHT, padx=2)
        styled_button(top, t("audio.zoomIn"), self._zoom_in, padx=6).pack(side=tk.RIGHT, padx=(4, 0))
        styled_button(top, t("audio.zoomOut"), self._zoom_out, padx=6).pack(side=tk.RIGHT)
        styled_button(top, t("audio.fitAll"), self._zoom_fit, padx=6).pack(side=tk.RIGHT, padx=(0, 4))
        styled_button(top, t("audio.resetAll"), self._reset_all, padx=6).pack(side=tk.RIGHT, padx=(0, 4))

        info_row = tk.Frame(self, bg=THEME['bg_main'])
        info_row.pack(fill=tk.X, padx=24, pady=(2, 2))
        self.tl_info = styled_label(info_row, t("audio.selectGroup"), size=10, color=THEME['fg_dim'], bg=THEME['bg_main'])
        self.tl_info.pack(side=tk.LEFT)
        self.wave_progress_label = styled_label(
            info_row, "", size=9, color=THEME['fg_dim'],
            bg=THEME['bg_main'],
        )
        self.wave_progress_label.pack(side=tk.RIGHT)
        self.wave_progress = ttk.Progressbar(
            info_row, style="APM.Horizontal.TProgressbar",
            orient=tk.HORIZONTAL, mode="determinate", maximum=100,
            length=150,
        )

        tl_frame = tk.Frame(self, bg=THEME['wave_bg'])
        tl_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 4))
        self.tl_hscroll = tk.Scrollbar(tl_frame, orient=tk.HORIZONTAL)
        self.tl_hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.tl_canvas = tk.Canvas(tl_frame, bg=THEME['wave_bg'], highlightthickness=0,
                                    xscrollcommand=self.tl_hscroll.set)
        self.tl_canvas.pack(fill=tk.BOTH, expand=True)
        self.tl_hscroll.configure(command=self.tl_canvas.xview)
        self.tl_canvas.bind("<ButtonPress-1>", self._tl_press)
        self.tl_canvas.bind("<B1-Motion>", self._tl_drag_motion)
        self.tl_canvas.bind("<ButtonRelease-1>", self._tl_release)
        self.tl_canvas.bind("<Double-Button-1>", self._tl_double_click)
        self.tl_canvas.bind("<Motion>", self._tl_hover)
        self.tl_canvas.bind("<Leave>", lambda e: self.tl_canvas.configure(cursor=''))
        self.tl_canvas.bind("<MouseWheel>", self._tl_scroll)
        self.tl_canvas.bind("<Button-4>", lambda e: self._tl_scroll_linux(1))
        self.tl_canvas.bind("<Button-5>", lambda e: self._tl_scroll_linux(-1))
        self.tl_canvas.bind("<Escape>", lambda e: self._cancel_tl_drag())

        tf = tk.Frame(self, bg=THEME['bg_main'])
        tf.pack(fill=tk.X, padx=24, pady=(0, 8))
        styled_label(tf, t("audio.helpTrim"),
                     size=10, color=THEME['fg_dim'], bg=THEME['bg_main']).pack(side=tk.LEFT)

        btn_row = tk.Frame(self, bg=THEME['bg_main'])
        btn_row.pack(fill=tk.X, padx=24, pady=(0, 10))
        styled_button(btn_row, t("audio.preview"), self._play_selection, "primary", padx=10).pack(side=tk.LEFT)
        styled_button(btn_row, t("audio.stop"), self._stop_preview, padx=10).pack(side=tk.LEFT, padx=(4, 12))
        styled_button(btn_row, t("audio.undo"), self._undo, padx=10).pack(side=tk.LEFT)
        styled_button(btn_row, t("audio.redo"), self._redo, padx=10).pack(side=tk.LEFT, padx=4)
        styled_button(btn_row, t("audio.moveUp"), self._move_up, padx=10).pack(side=tk.LEFT)
        styled_button(btn_row, t("audio.moveDown"), self._move_down, padx=10).pack(side=tk.LEFT, padx=4)
        self.bind_all(
            "<Control-z>",
            lambda e: self._undo() if self.app.current_stage == 2 else None,
        )
        self.bind_all(
            "<Control-y>",
            lambda e: self._redo() if self.app.current_stage == 2 else None,
        )

        edit_row = tk.Frame(self, bg=THEME['bg_card'])
        edit_row.pack(fill=tk.X, padx=24, pady=(0, 10))
        self.track_volume_var = tk.DoubleVar(value=1.0)
        self.track_fade_in_var = tk.DoubleVar(value=0.01)
        self.track_fade_out_var = tk.DoubleVar(value=0.01)
        self.track_edit_label = styled_label(
            edit_row, t("audio.trackSettings"), size=10, bold=True,
            bg=THEME['bg_card'],
        )
        self.track_edit_label.pack(side=tk.LEFT, padx=(10, 12))
        for label, variable, upper, resolution in (
            (t("audio.volume"), self.track_volume_var, 2.0, 0.05),
            (t("audio.fadeIn"), self.track_fade_in_var, 10.0, 0.1),
            (t("audio.fadeOut"), self.track_fade_out_var, 10.0, 0.1),
        ):
            styled_label(
                edit_row, label, size=9, bg=THEME['bg_card']
            ).pack(side=tk.LEFT, padx=(8, 2))
            scale = styled_scale(
                edit_row, variable, 0, upper, resolution,
                bg=THEME['bg_card'],
            )
            scale.configure(length=110)
            scale.pack(side=tk.LEFT)
            scale.bind("<ButtonRelease-1>", self._commit_track_audio_settings)

        self._recompute_positions()

    def _load_track_audio_settings(self):
        if not (0 <= self.tl_sel < len(self._track_rects)):
            return
        track = self._track_rects[self.tl_sel]['track']
        self._updating_track_controls = True
        try:
            self.track_volume_var.set(float(track.get('volume', 1.0)))
            self.track_fade_in_var.set(float(track.get('fade_in', 0.01)))
            self.track_fade_out_var.set(float(track.get('fade_out', 0.01)))
            self.track_edit_label.configure(
                text=t("audio.trackSettingsName", name=track.get('filename', '')[:28])
            )
        finally:
            self._updating_track_controls = False

    def _commit_track_audio_settings(self, _event=None):
        if self._updating_track_controls:
            return
        if not (0 <= self.tl_sel < len(self._track_rects)):
            return
        track = self._track_rects[self.tl_sel]['track']
        duration = max(
            MIN_TRIM_SECONDS,
            float(track.get('trim_end', track.get('duration', 0)))
            - float(track.get('trim_start', 0)),
        )
        track['volume'] = max(0.0, min(2.0, self.track_volume_var.get()))
        track['fade_in'] = max(
            0.0, min(duration / 2, self.track_fade_in_var.get())
        )
        track['fade_out'] = max(
            0.0, min(duration / 2, self.track_fade_out_var.get())
        )
        self.track_fade_in_var.set(track['fade_in'])
        self.track_fade_out_var.set(track['fade_out'])
        self.app.persist_video_groups()

    def _recompute_positions(self):
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            self._track_rects = []
            return
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        rects = []
        x_cursor = 0
        for i, tr in enumerate(tracks):
            ts = tr.get('trim_start', 0)
            te = tr.get('trim_end', 0)
            a = tr.get('analysis')
            if a:
                if te <= 0:
                    te = a.duration
                dur = max(0.1, te - ts)
            else:
                dur = tr.get('duration', 1)
            fade_in = min(float(tr.get('fade_in', 0.01)), dur / 2)
            fade_out = min(float(tr.get('fade_out', 0.01)), dur / 2)
            x_start = x_cursor
            x_end = x_cursor + dur
            rects.append({
                'idx': i, 'x_start': x_start, 'x_end': x_end, 'track': tr,
                'fade_in': fade_in, 'fade_out': fade_out,
            })
            x_cursor = x_end
        self._track_rects = rects
        group = self.app.video_groups[self.selected_group]
        group['total_duration'] = x_cursor
        self._precompute_waveforms()

    def _precompute_waveforms(self):
        total = len(self._track_rects)
        ready = 0
        for r in self._track_rects:
            fp = r['track'].get('filepath', '')
            if not fp or fp in self._waveform_cache:
                ready += 1
                continue
            try:
                analysis = r['track'].get('analysis')
                samples = getattr(analysis, 'waveform', None)
                sr = getattr(analysis, 'sr', 22050)
                if samples is None or len(samples) == 0:
                    if fp not in self._waveform_loading:
                        self._waveform_loading.add(fp)
                        threading.Thread(
                            target=self._load_waveform_async,
                            args=(fp,), daemon=True,
                        ).start()
                    continue
                peaks = _waveform_peaks(samples)
                self._waveform_cache[fp] = (peaks, sr, len(samples))
                ready += 1
            except Exception as error:
                logger.debug("Waveform cache failed for %s: %s", fp, error)
        self._update_waveform_progress(ready, total)

    def _load_waveform_async(self, filepath):
        try:
            _ensure_analysis_modules()
            samples, sr = _load_audio_pydub(filepath)
            if samples is None or len(samples) == 0:
                return
            peaks = _waveform_peaks(samples)
            self.after(
                0,
                lambda: self._waveform_ready(
                    filepath, (peaks, sr, len(samples))
                ),
            )
        except Exception as error:
            logger.debug(
                "Waveform loading failed for %s: %s", filepath, error
            )
        finally:
            self._waveform_loading.discard(filepath)

    def _waveform_ready(self, filepath, cached):
        self._waveform_cache[filepath] = cached
        self._update_waveform_progress(
            sum(
                1 for rect in self._track_rects
                if rect['track'].get('filepath') in self._waveform_cache
            ),
            len(self._track_rects),
        )
        self._draw_timeline()

    def _update_waveform_progress(self, ready, total):
        if total <= 0 or ready >= total:
            self.wave_progress.pack_forget()
            self.wave_progress_label.configure(text="")
            return
        percent = int(ready / total * 100)
        self.wave_progress.configure(value=percent)
        if not self.wave_progress.winfo_manager():
            self.wave_progress.pack(side=tk.RIGHT, padx=(8, 0))
        self.wave_progress_label.configure(
            text=t(
                "progressOverlay.waveformCount",
                current=ready, total=total, percent=percent,
            )
        )

    def _draw_timeline(self):
        self.tl_canvas.delete("all")
        cw = self.tl_canvas.winfo_width()
        ch = self.tl_canvas.winfo_height()
        if cw < 20 or ch < 20:
            return
        lane_top = 36
        pps = self.tl_px_per_sec

        self.tl_canvas.create_line(0, lane_top - 1, cw, lane_top - 1, fill=THEME['separator'], width=1)

        total_dur = 0
        if self._track_rects:
            total_dur = self._track_rects[-1]['x_end']
        n_secs = int(total_dur) + 10

        if pps >= 20:
            major_step = 5
            minor_step = 1
        elif pps >= 8:
            major_step = 10
            minor_step = 5
        elif pps >= 3:
            major_step = 30
            minor_step = 10
        else:
            major_step = 60
            minor_step = 30

        for s in range(n_secs + 1):
            x = int(s * pps)
            if x > int(total_dur * pps) + cw:
                break
            if s % major_step == 0:
                self.tl_canvas.create_line(
                    x, lane_top, x, ch,
                    fill=THEME['timeline_grid'], width=1,
                )
                self.tl_canvas.create_text(x + 3, lane_top - 12, text=_fmt_ts(s),
                                           fill=THEME['fg_dim'], font=_font(8), anchor=tk.W)
            elif s % minor_step == 0:
                self.tl_canvas.create_line(
                    x, lane_top, x, ch,
                    fill=THEME['timeline_grid_minor'], width=1,
                )

        for ri, r in enumerate(self._track_rects):
            x1 = int(r['x_start'] * pps)
            x2 = int(r['x_end'] * pps)
            y1 = lane_top + 4
            y2 = lane_top + self.LANE_H - 4
            color = _TIMELINE_COLORS[ri % len(_TIMELINE_COLORS)]
            is_sel = (ri == self.tl_sel)

            lane_fill = (
                THEME['timeline_selection'] if is_sel
                else THEME[
                    'timeline_lane_alt' if ri % 2 else 'timeline_lane'
                ]
            )
            self.tl_canvas.create_rectangle(
                x1, y1, x2, y2, fill=lane_fill,
                outline=color if not is_sel else THEME['accent'],
                width=3 if is_sel else 1,
                tags=("tl_rect", f"tl_{ri}"),
            )

            fp = r['track'].get('filepath', '')
            cached = self._waveform_cache.get(fp)
            if cached and len(cached[0]) > 1:
                peaks_full, w_sr, w_total = cached
                analysis = r['track'].get('analysis')
                source_duration = (
                    analysis.duration if analysis else w_total / max(w_sr, 1)
                )
                trim_start = max(0.0, r['track'].get('trim_start', 0.0))
                trim_end = r['track'].get('trim_end', source_duration)
                if trim_end <= 0:
                    trim_end = source_duration
                peak_start = int(len(peaks_full) * trim_start / max(source_duration, 0.001))
                peak_end = int(len(peaks_full) * trim_end / max(source_duration, 0.001))
                peaks = peaks_full[
                    max(0, peak_start):min(len(peaks_full), max(peak_start + 1, peak_end))
                ]
                wave_w = x2 - x1 - 16
                if wave_w > 10 and len(peaks) > 1:
                    mid_y = (y1 + y2) / 2
                    max_abs = max(
                        max(abs(low), abs(high)) for low, high in peaks
                    ) or 1.0
                    pts = []
                    step = wave_w / len(peaks)
                    for pi, (_low, high) in enumerate(peaks):
                        px = x1 + 8 + int(pi * step)
                        norm_hi = high / max_abs
                        half_h = (y2 - y1 - 12) / 2
                        pts.append((px, int(mid_y - norm_hi * half_h)))
                    for pi in range(len(peaks) - 1, -1, -1):
                        low, _high = peaks[pi]
                        px = x1 + 8 + int(pi * step)
                        norm_lo = low / max_abs
                        half_h = (y2 - y1 - 12) / 2
                        pts.append((px, int(mid_y - norm_lo * half_h)))
                    if len(pts) >= 3:
                        flat = []
                        for px_c, py_c in pts:
                            flat.extend([px_c, py_c])
                        wave_color = (
                            '#ffffff' if is_sel else THEME['wave_line']
                        )
                        self.tl_canvas.create_polygon(flat, fill=wave_color, outline='',
                                                       stipple='gray25' if not is_sel else '',
                                                       tags=(f"tl_{ri}",))

            a = r['track'].get('analysis')
            track_dur = max(0.1, r['x_end'] - r['x_start'])
            fname = r['track'].get('filename', '')
            if len(fname) > 20:
                fname = fname[:17] + "..."
            label = fname
            if a:
                label = f"{fname}  {_fmt_ts(track_dur)}"

            fade_in_px = int(r.get('fade_in', 0) / track_dur * (x2 - x1)) if track_dur > 0 else 0
            fade_out_px = int(r.get('fade_out', 0) / track_dur * (x2 - x1)) if track_dur > 0 else 0

            self.tl_canvas.create_text(x1 + fade_in_px + 8, y1 + 4, text=label,
                                       fill=THEME['fg'], font=_font(9), anchor=tk.NW, tags=(f"tl_{ri}",))

            if fade_in_px > 2:
                self.tl_canvas.create_rectangle(x1, y1, x1 + fade_in_px, y2,
                                                fill='', outline='',
                                                stipple='gray50', tags=(f"tl_{ri}",))
                self.tl_canvas.create_text(x1 + 2, y1 + 2, text=t("audio.fadeInShort"),
                                           fill=THEME['fg_dim'], font=_font(7), anchor=tk.NW, tags=(f"tl_{ri}",))
            if fade_out_px > 2:
                self.tl_canvas.create_rectangle(x2 - fade_out_px, y1, x2, y2,
                                                fill='', outline='',
                                                stipple='gray50', tags=(f"tl_{ri}",))
                self.tl_canvas.create_text(x2 - 2, y1 + 2, text=t("audio.fadeOutShort"),
                                           fill=THEME['fg_dim'], font=_font(7), anchor=tk.NE, tags=(f"tl_{ri}",))

            edge_w = max(6, min(16, int((x2 - x1) * 0.10)))
            self.tl_canvas.create_rectangle(x1, y1, x1 + edge_w, y2,
                                            fill=THEME['accent'], outline='', tags=("tl_edge", f"tl_{ri}"))
            self.tl_canvas.create_rectangle(x1 + 2, y1 + 4, x1 + 3, y2 - 4,
                                            fill='#ffffff', outline='', tags=("tl_edge", f"tl_{ri}"))
            self.tl_canvas.create_rectangle(x2 - edge_w, y1, x2, y2,
                                            fill=THEME['wave_trim'], outline='', tags=("tl_edge", f"tl_{ri}"))
            self.tl_canvas.create_rectangle(x2 - 3, y1 + 4, x2 - 2, y2 - 4,
                                            fill='#ffffff', outline='', tags=("tl_edge", f"tl_{ri}"))

        if self._drop_index is not None and self._track_rects:
            if self._drop_index >= len(self._track_rects):
                drop_sec = self._track_rects[-1]['x_end']
            else:
                drop_sec = self._track_rects[self._drop_index]['x_start']
            drop_x = int(drop_sec * pps)
            self.tl_canvas.create_line(
                drop_x, lane_top, drop_x, lane_top + self.LANE_H,
                fill=THEME['warning'], width=4, tags=("drop_marker",)
            )

        playhead_x = int(self.playhead_sec * pps)
        self.tl_canvas.create_line(
            playhead_x, 4, playhead_x, lane_top + self.LANE_H + 4,
            fill=THEME['timeline_playhead'], width=3, tags=("playhead",)
        )
        self.tl_canvas.create_polygon(
            playhead_x - 5, 4, playhead_x + 5, 4, playhead_x, 11,
            fill=THEME['timeline_playhead'], outline='', tags=("playhead",)
        )

        time_label = t("audio.totalTime", time=_fmt_ts(total_dur), seconds=int(total_dur))
        info = t("audio.trackInfo", count=len(self._track_rects), time=time_label)
        if 0 <= self.tl_sel < len(self._track_rects):
            selected = self._track_rects[self.tl_sel]['track']
            analysis = selected.get('analysis')
            if analysis:
                start = selected.get('trim_start', 0.0)
                end = selected.get('trim_end', analysis.duration)
                if end <= 0:
                    end = analysis.duration
                info += t("audio.selectedInfo", name=selected.get('filename', ''), start=self._fmt_precise(start), end=self._fmt_precise(end), duration=self._fmt_precise(end - start))
        self.tl_info.configure(text=info)

        if self.selected_group >= 0:
            self.tl_canvas.configure(scrollregion=(0, 0, int(total_dur * pps) + 50, ch))

    def _px_to_track(self, px):
        pps = self.tl_px_per_sec
        sec = px / max(pps, 1)
        for r in self._track_rects:
            if r['x_start'] <= sec <= r['x_end']:
                return r
        return None

    def _tl_press(self, event):
        if self.selected_group < 0 or not self._track_rects:
            return
        cx = self.tl_canvas.canvasx(event.x)
        cy = self.tl_canvas.canvasy(event.y)
        lane_top = 36
        if cy < lane_top or cy > lane_top + self.LANE_H:
            self.playhead_sec = max(0.0, cx / max(self.tl_px_per_sec, 1))
            self._draw_timeline()
            return
        r = self._px_to_track(cx)
        if not r:
            return
        ri = r['idx']
        self.tl_sel = ri
        self._load_track_audio_settings()
        self.playhead_sec = max(0.0, cx / max(self.tl_px_per_sec, 1))
        self._draw_timeline()
        pps = self.tl_px_per_sec
        sec = cx / max(pps, 1)
        x1 = r['x_start']
        x2 = r['x_end']
        analysis = r['track'].get('analysis')
        source_end = analysis.duration if analysis else r['x_end'] - r['x_start']
        trim_end = r['track'].get('trim_end', source_end)
        if trim_end <= 0:
            trim_end = source_end
        edge_px = max(25 / pps, 0.25)
        if abs(sec - x1) < edge_px:
            self._push_history()
            self.tl_drag = {
                'mode': 'trim_start', 'idx': ri, 'press_x': cx,
                'initial_start': r['track'].get('trim_start', 0.0),
                'initial_end': trim_end,
            }
            self.tl_canvas.configure(cursor='sb_h_double_arrow')
            self._capture_timeline_pointer()
        elif abs(sec - x2) < edge_px:
            self._push_history()
            self.tl_drag = {
                'mode': 'trim_end', 'idx': ri, 'press_x': cx,
                'initial_start': r['track'].get('trim_start', 0.0),
                'initial_end': trim_end,
            }
            self.tl_canvas.configure(cursor='sb_h_double_arrow')
            self._capture_timeline_pointer()
        else:
            self._push_history()
            self.tl_drag = {
                'mode': 'reorder_pending', 'idx': ri, 'press_x': cx,
            }
            self.tl_canvas.configure(cursor='hand2')
            self._capture_timeline_pointer()

    def _tl_drag_motion(self, event):
        if not self.tl_drag or self.selected_group < 0:
            return
        cx = self.tl_canvas.canvasx(event.x)
        pps = self.tl_px_per_sec
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        ri = self.tl_drag['idx']
        tr = tracks[ri]
        a = tr.get('analysis')
        if not a:
            return
        orig_dur = a.duration
        mode = self.tl_drag['mode']
        delta = (cx - self.tl_drag['press_x']) / max(pps, 1)
        delta = self._snap_drag_delta(delta, event.state)

        if mode == 'trim_start':
            new_start = max(
                0.0,
                min(
                    self.tl_drag['initial_start'] + delta,
                    self.tl_drag['initial_end'] - MIN_TRIM_SECONDS,
                ),
            )
            tr['trim_start'] = new_start
        elif mode == 'trim_end':
            new_end = max(
                self.tl_drag['initial_start'] + MIN_TRIM_SECONDS,
                min(self.tl_drag['initial_end'] + delta, orig_dur),
            )
            tr['trim_end'] = new_end
        elif mode in ('reorder_pending', 'reorder'):
            if mode == 'reorder_pending' and abs(cx - self.tl_drag['press_x']) < 6:
                return
            self.tl_drag['mode'] = 'reorder'
            self.tl_canvas.configure(cursor='fleur')
            self._drop_index = self._reorder_drop_index(cx)

        self._recompute_positions()
        self._draw_timeline()
        if mode in ('trim_start', 'trim_end'):
            start = tr.get('trim_start', 0.0)
            end = tr.get('trim_end', orig_dur)
            self.tl_info.configure(
                text=t("audio.trimInfo", start=self._fmt_precise(start), end=self._fmt_precise(end), duration=self._fmt_precise(end - start))
            )

    def _tl_release(self, event):
        mode = self.tl_drag.get('mode') if self.tl_drag else None
        changed = mode in ('trim_start', 'trim_end', 'reorder')
        if mode == 'reorder':
            tracks = self.app.video_groups[self.selected_group].get('tracks', [])
            old_index = self.tl_drag['idx']
            new_index = self._drop_index
            if new_index is not None and 0 <= old_index < len(tracks):
                item = tracks.pop(old_index)
                if new_index > old_index:
                    new_index -= 1
                new_index = max(0, min(new_index, len(tracks)))
                tracks.insert(new_index, item)
                self.tl_sel = new_index
        self._cancel_tl_drag(redraw=False)
        self._recompute_positions()
        self._draw_timeline()
        if changed:
            self.app.persist_video_groups()

    def _capture_timeline_pointer(self):
        try:
            self.tl_canvas.focus_set()
            self.tl_canvas.grab_set()
        except tk.TclError:
            self._cancel_tl_drag(redraw=False)

    def _cancel_tl_drag(self, redraw=True):
        self._drop_index = None
        self.tl_drag = None
        try:
            if self.tl_canvas.grab_current() == self.tl_canvas:
                self.tl_canvas.grab_release()
            self.tl_canvas.configure(cursor='')
        except tk.TclError:
            pass
        if redraw and self.winfo_exists():
            self._recompute_positions()
            self._draw_timeline()

    @staticmethod
    def _fmt_precise(seconds):
        seconds = max(0.0, float(seconds))
        minutes = int(seconds // 60)
        remainder = seconds - minutes * 60
        return f"{minutes:02d}:{remainder:06.3f}"

    @staticmethod
    def _snap_drag_delta(delta, event_state):
        alt_pressed = bool(event_state & (0x0008 | 0x20000))
        shift_pressed = bool(event_state & 0x0001)
        snap = 0.001 if alt_pressed else (0.01 if shift_pressed else 0.1)
        return round(delta / snap) * snap

    def _snapshot(self):
        if self.selected_group < 0:
            return []
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        return [
            {
                'track': track,
                'trim_start': track.get('trim_start', 0.0),
                'trim_end': track.get('trim_end', 0.0),
            }
            for track in tracks
        ]

    def _push_history(self):
        snapshot = self._snapshot()
        if not snapshot:
            return
        self._history = self._history[:self._history_index + 1]
        self._history.append(snapshot)
        self._history = self._history[-100:]
        self._history_index = len(self._history) - 1

    def _restore_snapshot(self, snapshot):
        tracks = []
        for state in snapshot:
            track = state['track']
            track['trim_start'] = state['trim_start']
            track['trim_end'] = state['trim_end']
            tracks.append(track)
        self.app.video_groups[self.selected_group]['tracks'] = tracks
        self.tl_sel = min(self.tl_sel, len(tracks) - 1)
        self._recompute_positions()
        self._draw_timeline()
        self.app.persist_video_groups()

    def _undo(self):
        if self._history_index < 0:
            return
        current = self._snapshot()
        snapshot = self._history[self._history_index]
        if self._history_index == len(self._history) - 1:
            self._history.append(current)
        self._restore_snapshot(snapshot)
        self._history_index -= 1

    def _redo(self):
        target = self._history_index + 2
        if target >= len(self._history):
            return
        self._restore_snapshot(self._history[target])
        self._history_index += 1

    def _play_selection(self):
        if not (0 <= self.tl_sel < len(self._track_rects)):
            messagebox.showinfo(t("audio.preview"), t("audio.previewNeedSelect"))
            return
        track = self._track_rects[self.tl_sel]['track']
        analysis = track.get('analysis')
        if not analysis:
            return
        if self._preview_player is None:
            from audio_preview import AudioPreviewPlayer
            self._preview_player = AudioPreviewPlayer()
        start = track.get('trim_start', 0.0)
        end = track.get('trim_end', analysis.duration)
        if end <= 0:
            end = analysis.duration
        timeline_start = self._track_rects[self.tl_sel]['x_start']
        self.tl_info.configure(text=t("audio.previewReady"))
        self._preview_player.play(
            track.get('filepath', ''), start, end - start,
            volume=float(track.get('volume', 1.0)),
            fade_in=float(track.get('fade_in', 0.01)),
            fade_out=float(track.get('fade_out', 0.01)),
            on_ready=lambda: self.after(
                0, lambda: self._start_preview_playhead(
                    end - start, timeline_start
                )
            ),
            on_error=lambda error: self.after(
                0, lambda: messagebox.showerror(t("audio.previewError"), str(error))
            ),
        )

    def _stop_preview(self):
        if self._preview_player:
            self._preview_player.stop()
        if self._audio_preview_after_id:
            self.after_cancel(self._audio_preview_after_id)
            self._audio_preview_after_id = None

    def _start_preview_playhead(self, duration, timeline_start):
        self._audio_preview_started = time.monotonic()
        self._audio_preview_duration = duration
        self._audio_preview_timeline_start = timeline_start
        self._tick_preview_playhead()

    def _tick_preview_playhead(self):
        elapsed = time.monotonic() - self._audio_preview_started
        self.playhead_sec = self._audio_preview_timeline_start + min(
            elapsed, self._audio_preview_duration
        )
        self._draw_timeline()
        if elapsed < self._audio_preview_duration:
            self._audio_preview_after_id = self.after(
                33, self._tick_preview_playhead
            )
        else:
            self._audio_preview_after_id = None

    def _reorder_drop_index(self, canvas_x):
        sec = canvas_x / max(self.tl_px_per_sec, 1)
        for i, rect in enumerate(self._track_rects):
            midpoint = (rect['x_start'] + rect['x_end']) / 2
            if sec < midpoint:
                return i
        return len(self._track_rects)

    def _tl_double_click(self, event):
        cx = self.tl_canvas.canvasx(event.x)
        r = self._px_to_track(cx)
        if r:
            self._open_trim_modal(r['idx'])

    def _tl_hover(self, event):
        if self.tl_drag or self.selected_group < 0:
            return
        cx = self.tl_canvas.canvasx(event.x)
        r = self._px_to_track(cx)
        if not r:
            self.tl_canvas.configure(cursor='crosshair')
            return
        pps = self.tl_px_per_sec
        sec = cx / max(pps, 1)
        edge_px = max(25 / pps, 0.25)
        x1 = r['x_start']
        x2 = r['x_end']
        if abs(sec - x1) < edge_px or abs(sec - x2) < edge_px:
            self.tl_canvas.configure(cursor='sb_h_double_arrow')
        else:
            self.tl_canvas.configure(cursor='hand2')

    def _tl_scroll(self, event):
        if event.state & 0x4:
            if event.delta > 0:
                self.tl_px_per_sec = min(80, self.tl_px_per_sec * 1.2)
            else:
                self.tl_px_per_sec = max(1, self.tl_px_per_sec / 1.2)
            self._recompute_positions()
            self._draw_timeline()
        else:
            self.tl_canvas.xview_scroll(int(-event.delta / 120), "units")

    def _tl_scroll_linux(self, direction):
        if direction > 0:
            self.tl_px_per_sec = min(80, self.tl_px_per_sec * 1.2)
        else:
            self.tl_px_per_sec = max(1, self.tl_px_per_sec / 1.2)
        self._recompute_positions()
        self._draw_timeline()

    def _zoom_in(self):
        self.tl_px_per_sec = min(80, self.tl_px_per_sec * 1.5)
        self._recompute_positions()
        self._draw_timeline()

    def _zoom_out(self):
        self.tl_px_per_sec = max(1, self.tl_px_per_sec / 1.5)
        self._recompute_positions()
        self._draw_timeline()

    def _zoom_fit(self):
        if not self._track_rects:
            return
        self.tl_canvas.update_idletasks()
        cw = self.tl_canvas.winfo_width()
        total = self._track_rects[-1]['x_end']
        if total > 0:
            self.tl_px_per_sec = max(1, (cw - 60) / total)
        self._recompute_positions()
        self._draw_timeline()

    def _sec_to_hms(self, sec):
        m = int(sec) // 60
        s = int(sec) % 60
        ms = int((sec - int(sec)) * 1000)
        return f"{m:02d}:{s:02d}:{ms:03d}"

    def _hms_to_sec(self, text):
        parts = text.strip().split(":")
        if len(parts) == 3:
            m, s, ms = parts
            return int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000.0
        elif len(parts) == 2:
            s, ms = parts
            return int(s) + int(ms.ljust(3, "0")[:3]) / 1000.0
        else:
            return int(parts[0])

    def _open_trim_modal(self, idx):
        if self.selected_group < 0:
            return
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        if idx < 0 or idx >= len(tracks):
            return
        tr = tracks[idx]
        a = tr.get('analysis')
        if not a:
            return
        ts = tr.get('trim_start', 0)
        te = tr.get('trim_end', a.duration)

        win = tk.Toplevel(self)
        win.title(t("audio.trimTitle", name=tr.get('filename', '')))
        win.configure(bg=THEME['bg_main'])
        win.geometry("420x300")
        win.resizable(False, False)
        win.grab_set()

        styled_label(win, tr.get('filename', ''), size=12, bold=True, bg=THEME['bg_main']).pack(pady=(16, 4))
        styled_label(win, t("audio.totalLength", duration=self._sec_to_hms(a.duration)), size=10, color=THEME['fg_dim'], bg=THEME['bg_main']).pack(pady=(0, 12))

        sf = tk.Frame(win, bg=THEME['bg_main'])
        sf.pack(fill=tk.X, padx=30, pady=4)
        styled_label(sf, t("audio.startTime"), size=10, bg=THEME['bg_main']).pack(side=tk.LEFT)
        start_ent = styled_entry(sf, width=14)
        start_ent.insert(0, self._sec_to_hms(ts))
        start_ent.pack(side=tk.RIGHT)

        ef = tk.Frame(win, bg=THEME['bg_main'])
        ef.pack(fill=tk.X, padx=30, pady=4)
        styled_label(ef, t("audio.endTime"), size=10, bg=THEME['bg_main']).pack(side=tk.LEFT)
        end_ent = styled_entry(ef, width=14)
        end_ent.insert(0, self._sec_to_hms(te))
        end_ent.pack(side=tk.RIGHT)

        styled_label(win, t("audio.timeHint"), size=9, color=THEME['fg_dimmer'], bg=THEME['bg_main']).pack(pady=(2, 12))

        btn_frame = tk.Frame(win, bg=THEME['bg_main'])
        btn_frame.pack(pady=8)

        def apply_trim():
            try:
                self._push_history()
                new_start = max(0, min(self._hms_to_sec(start_ent.get()), a.duration))
                new_end = max(new_start + 0.5, min(self._hms_to_sec(end_ent.get()), a.duration))
                tr['trim_start'] = new_start
                tr['trim_end'] = new_end
                self._recompute_positions()
                self._draw_timeline()
                self.app.persist_video_groups()
                win.destroy()
            except Exception:
                pass

        styled_button(btn_frame, t("common.apply"), apply_trim, "primary", padx=16, pady=4).pack(side=tk.LEFT, padx=6)
        styled_button(btn_frame, t("common.cancel"), win.destroy, "danger", padx=16, pady=4).pack(side=tk.LEFT, padx=6)
        start_ent.bind("<Return>", lambda e: apply_trim())
        end_ent.bind("<Return>", lambda e: apply_trim())

    def _reset_all(self):
        if self.selected_group < 0:
            return
        self._push_history()
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        for tr in tracks:
            a = tr.get('analysis')
            if a:
                tr['trim_start'] = 0
                tr['trim_end'] = a.duration
        self._recompute_positions()
        self._draw_timeline()
        self.app.persist_video_groups()

    def _move_up(self):
        if self.tl_sel <= 0 or self.selected_group < 0:
            return
        self._push_history()
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        i = self.tl_sel
        tracks[i], tracks[i - 1] = tracks[i - 1], tracks[i]
        self.tl_sel = i - 1
        self._recompute_positions()
        self._draw_timeline()
        self.app.persist_video_groups()

    def _move_down(self):
        if self.selected_group < 0:
            return
        tracks = self.app.video_groups[self.selected_group].get('tracks', [])
        i = self.tl_sel
        if i < 0 or i >= len(tracks) - 1:
            return
        self._push_history()
        tracks[i], tracks[i + 1] = tracks[i + 1], tracks[i]
        self.tl_sel = i + 1
        self._recompute_positions()
        self._draw_timeline()
        self.app.persist_video_groups()

    def refresh(self):
        if not self.app.video_groups:
            self.selected_group = -1
            self.tl_sel = -1
            self._track_rects = []
            populate_group_tabs(self.tabs_container, [], -1, self._set_group)
            self._draw_timeline()
            return

        # 새로고침해도 기존에 보고 있던 영상 선택은 그대로 유지 (범위를 벗어나면 0번으로)
        idx = self.selected_group if 0 <= self.selected_group < len(self.app.video_groups) else 0
        self._set_group(idx)

    def _set_group(self, idx):
        self._cancel_tl_drag(redraw=False)
        self.selected_group = idx
        populate_group_tabs(self.tabs_container, self.app.video_groups, idx, self._set_group)
        self.tl_sel = -1
        self._recompute_positions()
        if self._zoom_after_id:
            try:
                self.after_cancel(self._zoom_after_id)
            except tk.TclError:
                pass
        self._zoom_after_id = self.after(50, self._run_zoom_fit)

    def _run_zoom_fit(self):
        self._zoom_after_id = None
        if self.winfo_exists():
            self._zoom_fit()

    def on_hide(self):
        self._cancel_tl_drag(redraw=False)
        self._stop_preview()
        if self._zoom_after_id:
            try:
                self.after_cancel(self._zoom_after_id)
            except tk.TclError:
                pass
            self._zoom_after_id = None


# ─── Stage 3: 클립 목록 (이미지/영상) ───

class Stage2ClipList(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg_main'])
        self.app = app
        self.selected_group = 0
        self._thumbnail_cache = {}
        self._thumbnail_generation = 0
        self._thumbnail_photo = None
        self._thumbnail_results = queue.Queue()
        self._thumbnail_after_id = None
        self.build_ui()
        self._thumbnail_after_id = self.after(50, self._drain_thumbnail_results)

    def build_ui(self):
        hdr = tk.Frame(self, bg=THEME['bg_main'])
        hdr.pack(fill=tk.X, padx=24, pady=(14, 0))
        styled_label(hdr, t("clip.title"), size=20, bold=True, bg=THEME['bg_main']).pack(side=tk.LEFT)
        styled_button(hdr, t("common.save"), lambda: self.app.persist_video_groups(), padx=10).pack(side=tk.RIGHT, padx=2)
        styled_label(self, t("clip.desc"),
                     size=11, color=THEME['fg_dim'], bg=THEME['bg_main']).pack(pady=(0, 6))

        self.tabs_container = tk.Frame(self, bg=THEME['bg_main'])
        self.tabs_container.pack(fill=tk.X, padx=24, pady=(0, 4))

        main = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, bg=THEME['panel_sash'],
            sashwidth=7, sashrelief=tk.FLAT, borderwidth=0,
            showhandle=False,
        )
        main.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))

        left = tk.Frame(main, bg=THEME['bg_card'])
        main.add(left, minsize=280, stretch="always")
        styled_label(left, t("clip.list"), size=11, bold=True, bg=THEME['bg_card']).pack(pady=(10, 4), padx=10, anchor=tk.W)

        self.clip_listbox = styled_listbox(left)
        self.clip_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.clip_listbox.bind("<<ListboxSelect>>", self._on_clip_selected)

        clip_btn_row = tk.Frame(left, bg=THEME['bg_card'])
        clip_btn_row.pack(fill=tk.X, padx=10, pady=(0, 10))
        styled_button(clip_btn_row, t("clip.addImage"), self._add_images, "success", padx=8).pack(side=tk.LEFT)
        styled_button(clip_btn_row, t("clip.addVideo"), self._add_videos, "success", padx=8).pack(side=tk.LEFT, padx=(4, 0))
        styled_button(clip_btn_row, t("clip.deleteSelected"), self._remove_selected, "danger", padx=8).pack(side=tk.LEFT, padx=(4, 0))
        styled_button(clip_btn_row, t("clip.moveUp"), self._move_up, padx=4).pack(side=tk.RIGHT)
        styled_button(clip_btn_row, t("clip.moveDown"), self._move_down, padx=4).pack(side=tk.RIGHT, padx=(0, 4))

        right = tk.Frame(main, bg=THEME['bg_card'])
        main.add(right, minsize=360, stretch="always")
        self.clip_preview_ratio = 0.48
        self.clip_vertical_pane = tk.PanedWindow(
            right, orient=tk.VERTICAL, bg=THEME['panel_sash'],
            sashwidth=9, sashrelief=tk.FLAT, borderwidth=0,
            showhandle=True, cursor="sb_v_double_arrow",
        )
        self.clip_vertical_pane.pack(fill=tk.BOTH, expand=True)
        preview_panel = tk.Frame(
            self.clip_vertical_pane, bg=THEME['bg_card']
        )
        settings_panel = tk.Frame(
            self.clip_vertical_pane, bg=THEME['bg_card']
        )
        self.clip_vertical_pane.add(
            preview_panel, minsize=180, stretch="always"
        )
        self.clip_vertical_pane.add(
            settings_panel, minsize=190, stretch="always"
        )
        self.clip_vertical_pane.bind(
            "<ButtonRelease-1>", self._remember_clip_preview_ratio,
            add="+",
        )
        self.after_idle(self._restore_clip_preview_ratio)

        styled_label(
            preview_panel, t("clip.preview"), size=11, bold=True,
            bg=THEME['bg_card']
        ).pack(pady=(10, 4), padx=10, anchor=tk.W)
        self.clip_preview_canvas = tk.Canvas(
            preview_panel, width=360, height=240, bg="#000000",
            highlightthickness=1, highlightbackground=THEME['border'],
        )
        self.clip_preview_canvas.pack(
            fill=tk.BOTH, expand=True, padx=10, pady=(0, 4)
        )
        self.clip_preview_canvas.bind(
            "<Configure>",
            lambda _event: self._refresh_selected_thumbnail(),
            add="+",
        )
        self.clip_preview_canvas.create_text(
            180, 100, text=t("clip.previewSelect"), fill=THEME['fg_dim'],
            font=_font(9), tags="message",
        )
        self.clip_preview_meta = styled_label(
            preview_panel, "", size=8, color=THEME['fg_dim'],
            bg=THEME['bg_card']
        )
        self.clip_preview_meta.pack(fill=tk.X, padx=10, pady=(0, 4))

        sec_label = styled_label(
            settings_panel, t("clip.settings"), size=11, bold=True,
            bg=THEME['bg_card'],
        )
        sec_label.pack(pady=(10, 8), padx=10, anchor=tk.W)

        self.clip_enabled = tk.BooleanVar(value=False)
        ef = tk.Frame(settings_panel, bg=THEME['bg_card'])
        ef.pack(fill=tk.X, padx=10, pady=2)
        styled_checkbutton(ef, t("clip.useTransition"), self.clip_enabled, bg=THEME['bg_card']).pack(side=tk.LEFT)

        styled_label(settings_panel, t("clip.interval"), size=10, bg=THEME['bg_card']).pack(anchor=tk.W, padx=10, pady=(10, 2))
        iv = tk.Frame(settings_panel, bg=THEME['bg_card'])
        iv.pack(fill=tk.X, padx=10, pady=2)
        self.clip_interval = tk.DoubleVar(value=1.0)
        self.clip_interval_scale = styled_scale(
            iv, self.clip_interval, 0.1, 30.0, 0.1,
            bg=THEME['bg_card'],
        )
        self.clip_interval_scale.pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        self.clip_interval_scale.bind(
            "<ButtonRelease-1>",
            lambda _event: self._sync_group_settings(save=True),
            add="+",
        )
        self.clip_interval_unit = tk.StringVar(value="seconds")
        styled_choice_menu(
            iv, self.clip_interval_unit, {
                "seconds": "clip.seconds",
                "beat": "clip.beat",
                "per_track": "clip.perTrack",
            }
        ).pack(side=tk.LEFT, padx=(8, 0))

        styled_label(settings_panel, t("clip.random"), size=10, bg=THEME['bg_card']).pack(anchor=tk.W, padx=10, pady=(10, 2))
        rf = tk.Frame(settings_panel, bg=THEME['bg_card'])
        rf.pack(fill=tk.X, padx=10, pady=2)
        self.clip_random = tk.BooleanVar(value=False)
        styled_checkbutton(rf, t("clip.randomPlay"), self.clip_random, bg=THEME['bg_card']).pack(side=tk.LEFT)
        self.clip_random_base = tk.StringVar(value="bpm")
        styled_choice_menu(
            rf, self.clip_random_base, {
                "bpm": "clip.sortBpm",
                "key": "clip.sortKey",
                "camelot": "clip.sortCamelot",
                "order": "clip.sortOrder",
            }
        ).pack(side=tk.LEFT, padx=(8, 0))

        styled_label(settings_panel, "", size=1, bg=THEME['bg_card']).pack()
        self._clip_status = styled_label(settings_panel, t("clip.clipCount", count=0), size=10, color=THEME['fg_dim'], bg=THEME['bg_card'])
        self._clip_status.pack(anchor=tk.W, padx=10, pady=(6, 0))

    def _restore_clip_preview_ratio(self):
        pane = self.clip_vertical_pane
        height = pane.winfo_height()
        if height <= 1:
            return
        position = max(180, min(height - 190, int(
            height * float(self.clip_preview_ratio)
        )))
        try:
            pane.sash_place(0, 0, position)
        except tk.TclError:
            pass

    def _remember_clip_preview_ratio(self, _event=None):
        try:
            height = max(1, self.clip_vertical_pane.winfo_height())
            _x, y = self.clip_vertical_pane.sash_coord(0)
            self.clip_preview_ratio = max(0.25, min(0.75, y / height))
            self.app.persist_video_groups()
        except tk.TclError:
            pass

    def _refresh_selected_thumbnail(self):
        if self.clip_listbox.curselection():
            self._on_clip_selected()

    def _on_clip_selected(self, _event=None):
        selection = self.clip_listbox.curselection()
        if not selection or not (0 <= self.selected_group < len(self.app.video_groups)):
            self._show_thumbnail_message(t("clip.previewSelect"))
            return
        clips = self.app.video_groups[self.selected_group].get("clips", [])
        index = selection[0]
        if index >= len(clips):
            return
        self._load_clip_thumbnail(clips[index])

    def _show_thumbnail_message(self, message):
        self.clip_preview_canvas.delete("all")
        self.clip_preview_canvas.create_text(
            max(1, self.clip_preview_canvas.winfo_width()) // 2,
            max(1, self.clip_preview_canvas.winfo_height()) // 2,
            text=message, fill=THEME['fg_dim'], font=_font(9),
        )
        self.clip_preview_meta.configure(text="")
        self._thumbnail_photo = None

    def _load_clip_thumbnail(self, clip):
        filepath = clip.get("filepath", "")
        if not os.path.isfile(filepath):
            self._show_thumbnail_message(t("clip.previewMissing"))
            return
        try:
            key = (os.path.abspath(filepath), os.path.getmtime(filepath))
        except OSError:
            self._show_thumbnail_message(t("clip.previewMissing"))
            return
        self._thumbnail_generation += 1
        generation = self._thumbnail_generation
        cached = self._thumbnail_cache.get(key)
        if cached is not None:
            self._display_clip_thumbnail(cached, filepath)
            return
        self._show_thumbnail_message(t("clip.previewLoading"))

        def worker():
            temp_path = None
            try:
                from PIL import Image
                if clip.get("type") == "video":
                    import tempfile
                    from ffmpeg_service import ensure_ffmpeg_available
                    fd, temp_path = tempfile.mkstemp(
                        prefix="apm_thumb_", suffix=".jpg"
                    )
                    os.close(fd)
                    result = subprocess.run([
                        ensure_ffmpeg_available(), "-hide_banner", "-loglevel",
                        "error", "-y", "-ss", "1", "-i", filepath,
                        "-frames:v", "1", "-vf",
                        "scale=640:360:force_original_aspect_ratio=decrease",
                        temp_path,
                    ], capture_output=True, creationflags=(
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    ))
                    if result.returncode:
                        raise RuntimeError(result.stderr.decode(errors="replace"))
                    image = Image.open(temp_path).convert("RGB").copy()
                else:
                    image = Image.open(filepath).convert("RGB")
                image.thumbnail((640, 360), Image.Resampling.LANCZOS)
                self._thumbnail_cache[key] = image.copy()
                if generation == self._thumbnail_generation:
                    self._thumbnail_results.put(("image", generation, image, filepath))
            except Exception:
                logger.exception("Clip thumbnail failed: %s", filepath)
                if generation == self._thumbnail_generation:
                    self._thumbnail_results.put(
                        ("error", generation, t("clip.previewFailed"), None)
                    )
            finally:
                if temp_path:
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
        threading.Thread(target=worker, daemon=True, name="clip-thumbnail").start()

    def _drain_thumbnail_results(self):
        try:
            while True:
                kind, generation, payload, filepath = self._thumbnail_results.get_nowait()
                if generation != self._thumbnail_generation:
                    continue
                if kind == "image":
                    self._display_clip_thumbnail(payload, filepath)
                else:
                    self._show_thumbnail_message(payload)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self._thumbnail_after_id = self.after(50, self._drain_thumbnail_results)

    def destroy(self):
        self._thumbnail_generation += 1
        if self._thumbnail_after_id:
            try:
                self.after_cancel(self._thumbnail_after_id)
            except tk.TclError:
                pass
            self._thumbnail_after_id = None
        super().destroy()

    def _display_clip_thumbnail(self, image, filepath):
        from PIL import Image, ImageTk
        width = max(100, self.clip_preview_canvas.winfo_width())
        height = max(100, self.clip_preview_canvas.winfo_height())
        preview = image.copy()
        preview.thumbnail((width, height), Image.Resampling.LANCZOS)
        self._thumbnail_photo = ImageTk.PhotoImage(
            preview, master=self.clip_preview_canvas
        )
        self.clip_preview_canvas.delete("all")
        self.clip_preview_canvas.create_image(
            width // 2, height // 2, image=self._thumbnail_photo
        )
        name = os.path.basename(filepath)
        if len(name) > 55:
            name = name[:52] + "..."
        self.clip_preview_meta.configure(
            text=f"{name} · {image.width}×{image.height}"
        )

    def _ensure_group_clips(self):
        media_fps = set()
        for g in self.app.video_groups:
            if 'clips' not in g:
                g['clips'] = []
            for c in g.get('clips', []):
                media_fps.add(os.path.abspath(c.get('filepath', '')))
        media_items = [tr for tr in self.app.tracks if tr.filetype in ("image", "video")]
        for tr in media_items:
            absp = os.path.abspath(tr.filepath)
            if absp not in media_fps:
                for g in self.app.video_groups:
                    g['clips'].append({'filepath': tr.filepath, 'type': tr.filetype})
                    media_fps.add(absp)

    def _add_images(self):
        exts = " ".join(f"*{e}" for e in IMAGE_EXTS)
        files = filedialog.askopenfilenames(filetypes=[(t("common.imageType"), exts)])
        if not files:
            return
        self._ensure_group_clips()
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            return
        g = self.app.video_groups[self.selected_group]
        for fp in files:
            g['clips'].append({'filepath': fp, 'type': 'image'})
        self._refresh_clip_list()

    def _add_videos(self):
        exts = " ".join(f"*{e}" for e in VIDEO_EXTS)
        files = filedialog.askopenfilenames(filetypes=[(t("common.videoType"), exts)])
        if not files:
            return
        self._ensure_group_clips()
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            return
        g = self.app.video_groups[self.selected_group]
        for fp in files:
            g['clips'].append({'filepath': fp, 'type': 'video'})
        self._refresh_clip_list()

    def _remove_selected(self):
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            return
        sel = self.clip_listbox.curselection()
        if not sel:
            return
        g = self.app.video_groups[self.selected_group]
        clips = g.get('clips', [])
        for idx in sorted(sel, reverse=True):
            if idx < len(clips):
                clips.pop(idx)
        self._refresh_clip_list()

    def _move_up(self):
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            return
        sel = self.clip_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        g = self.app.video_groups[self.selected_group]
        clips = g.get('clips', [])
        i = sel[0]
        clips[i], clips[i-1] = clips[i-1], clips[i]
        self._refresh_clip_list()
        self.clip_listbox.selection_set(i-1)

    def _move_down(self):
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            return
        sel = self.clip_listbox.curselection()
        if not sel:
            return
        g = self.app.video_groups[self.selected_group]
        clips = g.get('clips', [])
        i = sel[0]
        if i >= len(clips) - 1:
            return
        clips[i], clips[i+1] = clips[i+1], clips[i]
        self._refresh_clip_list()
        self.clip_listbox.selection_set(i+1)

    def _refresh_clip_list(self):
        self.clip_listbox.delete(0, tk.END)
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            self._clip_status.configure(text=t("clip.clipCount", count=0))
            return
        g = self.app.video_groups[self.selected_group]
        clips = g.get('clips', [])
        for i, c in enumerate(clips):
            name = os.path.basename(c.get('filepath', ''))
            tag = "IMG" if c.get('type') == 'image' else "VID"
            self.clip_listbox.insert(tk.END, t("clip.clipItem", index=i+1, tag=tag, name=name))
        self._clip_status.configure(text=t("clip.clipCount", count=len(clips)))

    def _sync_group_settings(self, save=True):
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            return
        g = self.app.video_groups[self.selected_group]
        if save:
            g['clip_enabled'] = self.clip_enabled.get()
            g['clip_interval'] = self.clip_interval.get()
            g['clip_interval_unit'] = self.clip_interval_unit.get()
            g['clip_random'] = self.clip_random.get()
            g['clip_random_base'] = self.clip_random_base.get()
        else:
            self.clip_enabled.set(g.get('clip_enabled', False))
            self.clip_interval.set(g.get('clip_interval', 1.0))
            self.clip_interval_unit.set(_i18n_mod.choice_id(
                g.get('clip_interval_unit', 'seconds'),
                {
                    "seconds": "clip.seconds",
                    "beat": "clip.beat",
                    "per_track": "clip.perTrack",
                },
                "seconds",
            ))
            self.clip_random.set(g.get('clip_random', False))
            self.clip_random_base.set(_i18n_mod.choice_id(
                g.get('clip_random_base', 'bpm'),
                {
                    "bpm": "clip.sortBpm",
                    "key": "clip.sortKey",
                    "camelot": "clip.sortCamelot",
                    "order": "clip.sortOrder",
                },
                "bpm",
            ))

    def _set_group(self, idx):
        if idx == self.selected_group:
            return
        self._sync_group_settings(save=True)
        self.selected_group = idx
        populate_group_tabs(self.tabs_container, self.app.video_groups, idx, self._set_group)
        self._sync_group_settings(save=False)
        self._refresh_clip_list()

    def refresh(self):
        self._ensure_group_clips()
        if not self.app.video_groups:
            self.selected_group = -1
            populate_group_tabs(self.tabs_container, [], -1, self._set_group)
            self._refresh_clip_list()
            return
        idx = self.selected_group if 0 <= self.selected_group < len(self.app.video_groups) else 0
        self.selected_group = idx
        populate_group_tabs(self.tabs_container, self.app.video_groups, idx, self._set_group)
        self._sync_group_settings(save=False)
        self._refresh_clip_list()

# Stage3VideoEdit is split into Stage4DesignEffects (stage4_design_effects.py)
# and Stage5Render (stage5_render.py) — imported at top of module.


# ─── 메인 앱 ───

class _LazyStage(tk.Frame):
    """Lightweight placeholder replaced when a packaged user opens the stage."""

    def __init__(self, parent, index):
        super().__init__(parent, bg=THEME['bg_main'])
        self.stage_index = index


class AutoPlaylistMakerApp:
    def __init__(self, defer_show=False):
        _ensure_project_module()
        self.tracks = []
        self.video_groups = []
        self.project = _Project()
        self.current_stage = 0
        self.dark_mode = True
        self.dirty = False
        self._suspend_state_tracking = False
        self._state_save_after_id = None
        self._project_save_lock = threading.Lock()
        self._project_save_generation = 0

        root = None
        if '--safe' not in sys.argv:
            try:
                from tkinterdnd2 import TkinterDnD
                root = TkinterDnD.Tk()
            except Exception:
                pass
        if root is None:
            root = tk.Tk()
        if defer_show:
            root.withdraw()

        self.root = root
        self.root.title(t("splash.title") + " v" + APP_VERSION)
        self.root.geometry("1200x750")
        self.root.minsize(950, 620)
        self.root.configure(bg=THEME['bg_main'])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_icon()

        self._apply_theme()
        self.build_nav()
        self.build_stages()
        self.show_stage(0)
        self._install_dirty_tracking()

    def collect_project_state(self):
        from ui_state import capture_pages
        def safe_int(value, default=0):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        pages = capture_pages(self.stages) if hasattr(self, 'stages') else []
        design = {}
        visualizer = {}
        render = {}
        repeat = {}
        visibility = {}
        if (hasattr(self, 'stages') and len(self.stages) > 4
                and hasattr(self.stages[4], "_collect_config")):
            design_stage = self.stages[4]
            config = design_stage._collect_config()
            design = {
                key: config[key]
                for key in (
                    'background', 'overlays', 'text', 'progress_bar',
                    'fade', 'effects', 'global_audio',
                )
                if key in config
            }
            design['active_effects'] = config.get('active_effects', [])
            visualizer = config.get('visualizer', {})
            visibility = config.get('visibility', {})
            from stage4_design_effects import LOOP_MODE_CHOICES
            repeat_mode = _i18n_mod.choice_id(
                design_stage.loop_mode_var.get(),
                LOOP_MODE_CHOICES,
                "count",
            )
            repeat = {
                'enabled': design_stage.loop_video_var.get(),
                'mode': repeat_mode,
                'count': max(
                    1, safe_int(design_stage.loop_count_var.get(), 1)
                ),
                'target_h': safe_int(design_stage.loop_target_h_var.get()),
                'target_m': safe_int(design_stage.loop_target_m_var.get()),
                'target_s': safe_int(design_stage.loop_target_s_var.get()),
            }
        if (hasattr(self, 'stages') and len(self.stages) > 5
                and hasattr(self.stages[5], "resolution")):
            render_stage = self.stages[5]
            render = {
                'resolution': render_stage.resolution.get(),
                'fps': render_stage.fps_var.get(),
                'video_codec': render_stage.video_codec_var.get(),
                'audio_codec': render_stage.audio_codec_var.get(),
                'video_bitrate': render_stage.video_bitrate_var.get(),
                'audio_bitrate': render_stage.audio_bitrate_var.get(),
                'normalize_loudness': render_stage.normalize_loudness_var.get(),
                'target_lufs': render_stage.target_lufs_var.get(),
                'output_dir': render_stage._last_render_dir or '',
            }
        return {
            'current_step': self.current_stage,
            'step_complete': {
                'import': bool(self.tracks),
                'distribution': bool(self.video_groups),
                'audio_edit': bool(self.video_groups),
                'clips': any(group.get('clips') for group in self.video_groups),
                'design': bool(design),
            },
            'pages': pages,
            'distribution': {'group_count': len(self.video_groups)},
            'design': design,
            'visualizer': visualizer,
            'render': render,
            'repeat': repeat or dict(
                getattr(self, "_pending_repeat_state", {}) or {}
            ),
            'visibility': visibility,
            'ui': {'dark_mode': self.dark_mode},
        }

    def restore_project_state(self, state):
        if not state:
            return
        from ui_state import restore_pages
        self._suspend_state_tracking = True
        try:
            restore_pages(self.stages, state.get('pages', []))
            if len(self.stages) > 4 and hasattr(
                self.stages[4], "_restore_effect_card_state"
            ):
                design_state = state.get("design", {}) or {}
                has_effect_state = any(
                    "active_effect_ids" in page.get("plain", {})
                    for page in state.get("pages", [])
                )
                if not has_effect_state:
                    from stage4_design_effects import EFFECT_DEFINITIONS
                    saved_effects = design_state.get("active_effects")
                    # Pre-card projects exposed every legacy effect control.
                    # Keep their output unchanged on first migration.
                    self.stages[4].active_effect_ids = list(
                        saved_effects
                        if isinstance(saved_effects, list)
                        else EFFECT_DEFINITIONS
                    )
                    self.stages[4]._restore_effect_card_state()
                audio_state = design_state.get("global_audio", {})
                has_audio_page_state = any(
                    "music_master_db" in page.get("variables", {})
                    for page in state.get("pages", [])
                )
                design_stage = self.stages[4]
                if audio_state and not has_audio_page_state:
                    for variable_name, field_name, default in (
                        ("music_master_db", "music_master_db", 0.0),
                        ("normalize_tracks", "normalize_tracks", False),
                        ("target_lufs", "target_lufs", -14.0),
                        ("true_peak_ceiling", "true_peak_dbtp", -1.0),
                        (
                            "max_normalize_gain",
                            "max_auto_gain_db",
                            12.0,
                        ),
                        (
                            "ambient_master_db",
                            "ambient_master_db",
                            -18.0,
                        ),
                    ):
                        getattr(design_stage, variable_name).set(
                            audio_state.get(field_name, default)
                        )
                    design_stage.ambient_tracks = list(
                        audio_state.get("ambient_tracks", [])
                    )
                    design_stage._refresh_ambient_list()
                elif not has_audio_page_state:
                    legacy_render = state.get("render", {})
                    if legacy_render.get("normalize_loudness"):
                        design_stage.normalize_tracks.set(True)
                        design_stage.target_lufs.set(
                            legacy_render.get("target_lufs", -14.0)
                        )
            self._pending_repeat_state = dict(state.get('repeat', {}))
            if len(self.stages) > 4 and hasattr(
                    self.stages[4], "loop_video_var"):
                self._apply_repeat_state_to_design(self.stages[4])
            if len(self.stages) > 5 and hasattr(self.stages[5], "_last_render_dir"):
                self.stages[5]._last_render_dir = state.get('render', {}).get('output_dir') or None
            if len(self.stages) > 4 and hasattr(self.stages[4], "visibility_enabled"):
                vis = state.get('visibility', {})
                ds = self.stages[4]
                if vis.get('enabled'):
                    ds.visibility_enabled.set(True)
                ds.set_visibility_seconds(
                    vis.get("turn_off_after", vis.get("initial_visible", 0)),
                    vis.get("restore_before_end", vis.get("ending_visible", 0)),
                    vis.get("restore", bool(vis.get("ending_visible", 0))),
                )
            step = int(state.get('current_step', 0))
            self.show_stage(max(0, min(step, len(self.stages) - 1)))
        finally:
            self._suspend_state_tracking = False

    def _apply_repeat_state_to_design(self, stage):
        repeat = getattr(self, "_pending_repeat_state", None) or {}
        if not repeat:
            return
        target_seconds = int(repeat.get("target_seconds", 0) or 0)
        target_h = int(repeat.get("target_h", target_seconds // 3600) or 0)
        target_m = int(
            repeat.get("target_m", (target_seconds % 3600) // 60) or 0
        )
        target_s = int(repeat.get("target_s", target_seconds % 60) or 0)
        stage.loop_video_var.set(bool(repeat.get("enabled", False)))
        stage.loop_mode_var.set(
            "target" if repeat.get("mode") == "target" else "count"
        )
        stage.loop_count_var.set(str(max(1, int(repeat.get("count", 1)))))
        stage.loop_target_h_var.set(str(max(0, target_h)))
        stage.loop_target_m_var.set(str(max(0, target_m)))
        stage.loop_target_s_var.set(str(max(0, target_s)))
        stage._commit_repeat_fields()

    def _install_dirty_tracking(self):
        for stage in getattr(self, 'stages', []):
            for value in vars(stage).values():
                if isinstance(value, tk.Variable):
                    value.trace_add("write", self._on_project_variable_changed)

    def _on_project_variable_changed(self, *_args):
        if self._suspend_state_tracking:
            return
        self.set_dirty(True)
        if self._state_save_after_id:
            try:
                self.root.after_cancel(self._state_save_after_id)
            except tk.TclError:
                pass
        self._state_save_after_id = self.root.after(
            700, self._autosave_project_state
        )

    def _autosave_project_state(self):
        self._state_save_after_id = None
        self.persist_video_groups()

    def set_dirty(self, dirty=True):
        self.dirty = bool(dirty)
        if not self.dirty and self._state_save_after_id:
            try:
                self.root.after_cancel(self._state_save_after_id)
            except tk.TclError:
                pass
            self._state_save_after_id = None
        if hasattr(self, 'project_label'):
            name = self.project.name if self.project else ""
            suffix = t("navigation.unsaved") if self.dirty else ""
            self.project_label.configure(
                text=(t("navigation.projectLabel", name=name) + suffix if name else suffix.lstrip(" ·"))
            )

    def _on_close(self):
        if getattr(self, "_closing", False):
            return
        if self.dirty and not messagebox.askyesno(
            t("navigation.unsavedTitle"),
            t("navigation.unsavedBody"),
        ):
            return
        self._closing = True
        if self._state_save_after_id:
            try:
                self.root.after_cancel(self._state_save_after_id)
            except tk.TclError:
                pass
            self._state_save_after_id = None
        for stage in getattr(self, 'stages', []):
            if hasattr(stage, 'on_hide'):
                stage.on_hide()
            cancel_event = getattr(
                stage, "_analysis_cancel_event", None
            )
            if cancel_event is not None:
                cancel_event.set()
            overlay = getattr(stage, "_task_overlay", None)
            if overlay is not None:
                overlay.close()
                stage._task_overlay = None
            cancel_event = getattr(stage, "_render_cancel_event", None)
            if cancel_event is not None:
                cancel_event.set()
            player = getattr(stage, "_preview_audio_player", None)
            if player is not None:
                player.stop()
        try:
            for after_id in self.root.tk.call('after', 'info'):
                self.root.after_cancel(after_id)
        except tk.TclError:
            pass
        try:
            import psutil
            children = psutil.Process(os.getpid()).children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except psutil.Error:
                    pass
            _, alive = psutil.wait_procs(children, timeout=1.5)
            for child in alive:
                try:
                    child.kill()
                except psutil.Error:
                    pass
        except (ImportError, OSError):
            logger.exception("Failed to clean child processes during shutdown")
        try:
            self.root.quit()
        except tk.TclError:
            pass
        self.root.destroy()

    def _set_icon(self):
        apply_window_icon(self.root)

    def _apply_theme(self):
        global THEME
        THEME = DARK if self.dark_mode else LIGHT
        self.root.configure(bg=THEME['bg_main'])
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            ".",
            background=THEME['bg_main'], foreground=THEME['fg'],
            fieldbackground=THEME['bg_input'], bordercolor=THEME['border'],
            focuscolor=THEME['accent'], font=_font(10),
        )
        style.configure(
            "Treeview", background=THEME['bg_input'],
            foreground=THEME['fg'], fieldbackground=THEME['bg_input'],
            rowheight=30, borderwidth=0,
        )
        style.configure(
            "Treeview.Heading", background=THEME['bg_mid'],
            foreground=THEME['fg_dim'], font=_font(9, True),
            padding=(8, 7), borderwidth=0, relief=tk.FLAT,
        )
        style.map(
            "Treeview",
            background=[("selected", THEME['tree_sel'])],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "TScrollbar", background=THEME['scroll_fg'],
            troughcolor=THEME['scroll_bg'], borderwidth=0,
            arrowcolor=THEME['fg_dim'], relief=tk.FLAT,
        )
        style.map("TScrollbar", background=[("active", THEME['accent'])])
        style.configure(
            "TScale", background=THEME['bg_card'],
            troughcolor=THEME['bg_input'], borderwidth=0,
        )
        style.configure(
            "APM.TEntry",
            fieldbackground=THEME['bg_input'], foreground=THEME['fg'],
            insertcolor=THEME['fg'], bordercolor=THEME['border'],
            lightcolor=THEME['border'], darkcolor=THEME['border'],
            padding=(8, 6), relief=tk.FLAT,
        )
        style.map(
            "APM.TEntry",
            bordercolor=[
                ("focus", THEME['accent']),
                ("disabled", THEME['separator']),
            ],
            fieldbackground=[("disabled", THEME['bg_mid'])],
            foreground=[("disabled", THEME['fg_dimmer'])],
        )
        style.configure(
            "APM.TCheckbutton",
            background=THEME['bg_card'], foreground=THEME['fg'],
            indicatorcolor=THEME['bg_input'], indicatorrelief=tk.FLAT,
            indicatormargin=(0, 0, 7, 0), padding=(0, 4),
        )
        style.map(
            "APM.TCheckbutton",
            background=[("active", THEME['bg_card'])],
            foreground=[("disabled", THEME['fg_dimmer'])],
            indicatorcolor=[
                ("selected", THEME['accent']),
                ("active", THEME['bg_hover']),
            ],
        )
        style.configure(
            "APM.Horizontal.TProgressbar",
            troughcolor=THEME['slider_track'],
            background=THEME['slider_fill'],
            bordercolor=THEME['border'],
            lightcolor=THEME['slider_fill'],
            darkcolor=THEME['slider_fill'],
            thickness=10,
        )

    def build_nav(self):
        self.nav = tk.Frame(
            self.root, bg=THEME['bg_mid'], height=58,
            highlightthickness=1, highlightbackground=THEME['separator'],
        )
        self.nav.pack(fill=tk.X)
        self.nav.pack_propagate(False)
        self._nav_rtl = False

        self._nav_left_frame = tk.Frame(self.nav, bg=THEME['bg_mid'])
        self._nav_left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._nav_right_frame = tk.Frame(self.nav, bg=THEME['bg_mid'])

        self.prev_btn = styled_button(self._nav_left_frame, t("navigation.prev"), self.go_prev, padx=12)
        self.prev_btn.pack(side=tk.LEFT, padx=(16, 0), pady=11)

        self.stage_label = styled_label(self._nav_left_frame, "", size=12, bold=True, bg=THEME['bg_mid'])
        self.stage_label.pack(side=tk.LEFT, padx=(18, 12))

        self._nav_dots = tk.Frame(self._nav_left_frame, bg=THEME['bg_mid'])
        self._nav_dots.pack(side=tk.LEFT, padx=8)
        self.dots = []
        for _ in range(6):
            l = tk.Label(self._nav_dots, text="\u25cf", font=_font(9), bg=THEME['bg_mid'], fg=THEME['fg_dimmer'])
            l.pack(side=tk.LEFT, padx=4)
            self.dots.append(l)

        self.project_label = styled_label(self._nav_left_frame, "", size=9, color=THEME['success'], bg=THEME['bg_mid'])
        self.project_label.pack(side=tk.LEFT, padx=16)

        self.theme_btn = styled_button(self._nav_right_frame, t("navigation.themeLight") if self.dark_mode else t("navigation.themeDark"),
                                        self._toggle_theme, padx=8)
        self.theme_btn.pack(side=tk.RIGHT, padx=(0, 8), pady=11)

        self.next_btn = styled_button(self._nav_right_frame, t("navigation.next"), self.go_next, "primary", padx=12)
        self.next_btn.pack(side=tk.RIGHT, padx=(0, 16), pady=11)
        set_button_state(self.next_btn, tk.DISABLED)
        self._nav_right_frame.pack(side=tk.RIGHT)

    def _apply_nav_rtl(self, rtl):
        if rtl == self._nav_rtl:
            return
        self._nav_rtl = rtl
        if rtl:
            self._nav_left_frame.pack_forget()
            self._nav_right_frame.pack_forget()
            self._nav_right_frame.pack(side=tk.LEFT)
            self._nav_left_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        else:
            self._nav_left_frame.pack_forget()
            self._nav_right_frame.pack_forget()
            self._nav_left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._nav_right_frame.pack(side=tk.RIGHT)

    def _toggle_theme(self):
        from ui_state import capture_pages
        stage_state = capture_pages(self.stages)
        self.dark_mode = not self.dark_mode
        self._apply_theme()

        self.nav.configure(
            bg=THEME['bg_mid'], highlightbackground=THEME['separator']
        )
        self._nav_left_frame.configure(bg=THEME['bg_mid'])
        self._nav_right_frame.configure(bg=THEME['bg_mid'])
        self._nav_dots.configure(bg=THEME['bg_mid'])
        self.stage_label.configure(bg=THEME['bg_mid'], fg=THEME['fg'])
        self.project_label.configure(bg=THEME['bg_mid'], fg=THEME['success'])
        self.theme_btn.configure(text=t("navigation.themeLight") if self.dark_mode else t("navigation.themeDark"),
                                 bg=THEME['bg_input'], fg=THEME['fg'])
        for d in self.dots:
            d.configure(bg=THEME['bg_mid'])
        self.prev_btn.configure(bg=THEME['bg_input'], fg=THEME['fg'],
                                activebackground=THEME['bg_hover'])
        self.next_btn.configure(bg=THEME['accent'], fg="#ffffff",
                                activebackground=THEME['accent_h'])
        for button in (self.prev_btn, self.next_btn, self.theme_btn):
            button._paint_state(False)

        self._rebuild_stages(stage_state)

    def _rebuild_stages(self, stage_state=None):
        if hasattr(self, '_stage_container'):
            for stage in getattr(self, 'stages', []):
                if hasattr(stage, 'on_hide'):
                    stage.on_hide()
            self._stage_container.destroy()

        self._stage_container = tk.Frame(self.root, bg=THEME['bg_main'])
        self._stage_container.pack(fill=tk.BOTH, expand=True)

        self._create_stage_collection()
        self.titles = [t("navigation.stage0"), t("navigation.stage1"),
                       t("navigation.stage2"), t("navigation.stage3"),
                       t("navigation.stage4"), t("navigation.stage5")]

        if stage_state and not self._lazy_stage_mode:
            from ui_state import restore_pages
            restore_pages(self.stages, stage_state)
        elif stage_state:
            self._pending_stage_state = stage_state
        self._install_dirty_tracking()
        self.show_stage(self.current_stage)

    def build_stages(self):
        self._stage_container = tk.Frame(self.root, bg=THEME['bg_main'])
        self._stage_container.pack(fill=tk.BOTH, expand=True)

        self._create_stage_collection()
        self.titles = [t("navigation.stage0"), t("navigation.stage1"),
                       t("navigation.stage2"), t("navigation.stage3"),
                       t("navigation.stage4"), t("navigation.stage5")]

    def _create_stage_collection(self):
        self._output_settings_linked = False
        factories = (
            Stage0Project, Stage1Distribute, Stage2MusicEdit,
            Stage2ClipList, Stage4DesignEffects, Stage5Render,
        )
        self._stage_factories = factories
        self._lazy_stage_mode = bool(getattr(sys, "frozen", False))
        if self._lazy_stage_mode:
            self.stages = [
                factories[0](self._stage_container, self),
                *(_LazyStage(self._stage_container, index) for index in range(1, 6)),
            ]
        else:
            self.stages = [
                factory(self._stage_container, self) for factory in factories
            ]
            self._link_preview_output_settings()

    def _ensure_stage(self, index):
        stage = self.stages[index]
        if not isinstance(stage, _LazyStage):
            return stage
        stage.destroy()
        stage = self._stage_factories[index](self._stage_container, self)
        self.stages[index] = stage
        pending = getattr(self, "_pending_stage_state", None)
        if pending and index < len(pending):
            from ui_state import restore_pages
            restore_pages([stage], [pending[index]])
        if index == 4:
            self._apply_repeat_state_to_design(stage)
        if index in (4, 5):
            self._link_preview_output_settings()
        for value in vars(stage).values():
            if isinstance(value, tk.Variable):
                value.trace_add("write", self._on_project_variable_changed)
        return stage

    def _link_preview_output_settings(self):
        """Keep preview and final output canvas settings on one live value."""
        if len(getattr(self, "stages", [])) < 6:
            return
        design, render = self.stages[4], self.stages[5]
        if isinstance(design, _LazyStage) or isinstance(render, _LazyStage):
            return
        if getattr(self, "_output_settings_linked", False):
            return
        self._output_settings_linked = True
        self._syncing_output_settings = False
        pairs = (
            (design.resolution, render.resolution),
            (design.custom_width_var, render.custom_width_var),
            (design.custom_height_var, render.custom_height_var),
            (design.fps_var, render.fps_var),
        )

        def sync(source, target):
            if self._syncing_output_settings:
                return
            self._syncing_output_settings = True
            try:
                target.set(source.get())
            finally:
                self._syncing_output_settings = False

        for design_var, render_var in pairs:
            design_var.set(render_var.get())
            design_var.trace_add(
                "write",
                lambda *_args, source=design_var, target=render_var:
                sync(source, target),
            )
            render_var.trace_add(
                "write",
                lambda *_args, source=render_var, target=design_var:
                sync(source, target),
            )

    def _refresh_lang_ui(self):
        self.titles = [t("navigation.stage0"), t("navigation.stage1"),
                       t("navigation.stage2"), t("navigation.stage3"),
                       t("navigation.stage4"), t("navigation.stage5")]
        try:
            if 0 <= self.current_stage < len(self.stages):
                self.stage_label.configure(text=self.titles[self.current_stage])
                s = self.stages[self.current_stage]
                if hasattr(s, 'refresh'):
                    s.refresh()
        except Exception as error:
            _log_error("Language UI refresh failed", error)

    def _on_language_changed(self):
        rtl = _i18n_mod.get_instance().is_rtl()
        self._apply_nav_rtl(rtl)
        from ui_state import capture_pages
        stage_state = capture_pages(self.stages)
        self._rebuild_stages(stage_state)

    def show_stage(self, idx):
        self._ensure_stage(idx)
        if (
            hasattr(self, 'stages')
            and 0 <= self.current_stage < len(self.stages)
            and self.current_stage != idx
        ):
            current = self.stages[self.current_stage]
            if hasattr(current, 'on_hide'):
                current.on_hide()
        for s in self.stages:
            s.pack_forget()
        self.current_stage = idx
        self.stages[idx].pack(fill=tk.BOTH, expand=True)
        self.stage_label.configure(text=self.titles[idx])
        for i, d in enumerate(self.dots):
            d.configure(fg=THEME['accent'] if i == idx else (THEME['fg_dim'] if i < idx else THEME['fg_dimmer']))
        set_button_state(
            self.prev_btn, tk.NORMAL if idx > 0 else tk.DISABLED
        )

        if idx >= 5:
            self.next_btn.pack_forget()
        else:
            self.next_btn.pack(side=tk.RIGHT, padx=(0, 16), pady=11)
            if idx == 0:
                has = any(
                    track.analysis
                    for track in self.tracks
                    if track.filetype == "audio"
                )
                set_button_state(
                    self.next_btn, tk.NORMAL if has else tk.DISABLED
                )
            elif idx == 1:
                set_button_state(
                    self.next_btn,
                    tk.NORMAL if self.video_groups else tk.DISABLED,
                )
            else:
                set_button_state(self.next_btn, tk.NORMAL)

        if self.project and self.project.name:
            self.project_label.configure(text=t("navigation.projectLabel", name=self.project.name))
        else:
            self.project_label.configure(text="")

        active_stage = self.stages[idx]
        if hasattr(active_stage, "refresh"):
            try:
                active_stage.refresh()
            except Exception as error:
                _log_error("show_stage.refresh", error)

    def enable_next(self, enabled=True):
        set_button_state(
            self.next_btn, tk.NORMAL if enabled else tk.DISABLED
        )

    def persist_video_groups(self):
        """Atomically persist lightweight edit metadata without rewriting caches."""
        project = self.project
        self.set_dirty(True)
        if not project or not project.project_file or not os.path.isfile(project.project_file):
            return
        app_state = self.collect_project_state()
        self._project_save_generation += 1
        save_generation = self._project_save_generation
        groups_snapshot = []
        for group in self.video_groups:
            snapshot = dict(group)
            snapshot['tracks'] = [
                dict(track) for track in group.get('tracks', [])
            ]
            snapshot['clips'] = [
                dict(clip) for clip in group.get('clips', [])
            ]
            groups_snapshot.append(snapshot)

        def save():
            try:
                with self._project_save_lock:
                    if save_generation != self._project_save_generation:
                        return
                    project.save(
                        analyses=None,
                        video_groups=groups_snapshot,
                        app_state=app_state,
                    )
                self.root.after(
                    0,
                    lambda: (
                        self.set_dirty(False)
                        if save_generation == self._project_save_generation
                        else None
                    ),
                )
            except Exception as error:
                print(t("navigation.autoSaveFailed", error=error))

        threading.Thread(target=save, daemon=True).start()

    def go_next(self):
        if self.current_stage < len(self.stages) - 1:
            self.show_stage(self.current_stage + 1)

    def go_prev(self):
        if self.current_stage > 0:
            self.show_stage(self.current_stage - 1)

    def run(self):
        self.root.mainloop()


# ─── 스플래시 스크린 ───

class SplashScreen:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg='#111827')
        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)
        apply_window_icon(self.root)

        w, h = 440, 300
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        outer = tk.Frame(self.root, bg='#111827')
        outer.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(outer, bg='#111827')
        inner.pack(fill=tk.BOTH, expand=True)

        try:
            self.icon_image = tk.PhotoImage(file=resource_path("app_icon.png"))
            self.icon_image = self.icon_image.subsample(4, 4)
            tk.Label(
                inner,
                image=self.icon_image,
                bg="#111827",
                borderwidth=0,
                highlightthickness=0,
            ).pack(pady=(18, 2))
        except (OSError, tk.TclError):
            self.icon_image = None

        tk.Label(inner, text=t("splash.title"), font=(FONT_FAMILY, 19, "bold"),
                 bg='#111827', fg='#f8fafc').pack(pady=(2, 0))
        tk.Label(inner, text=t("splash.version", version=APP_VERSION), font=(FONT_FAMILY, 11),
                 bg='#111827', fg='#94a3b8').pack()

        self.status_var = tk.StringVar(value=t("splash.starting"))
        self.status_label = tk.Label(inner, textvariable=self.status_var,
                                     font=(FONT_FAMILY, 9), bg='#111827', fg='#94a3b8')
        self.status_label.pack(pady=(10, 6))

        bar_frame = tk.Frame(inner, bg='#263247', height=6)
        bar_frame.pack(fill=tk.X, padx=42, pady=(0, 18))
        bar_frame.pack_propagate(False)
        self.bar_canvas = tk.Canvas(bar_frame, bg='#263247', highlightthickness=0, height=6)
        self.bar_canvas.pack(fill=tk.BOTH, expand=True)

        self.bar_width = 0
        self.bar_max = 1

        self.root.deiconify()
        self.root.update_idletasks()
        self.root.update()

    def update(self, text, progress):
        try:
            self.status_var.set(text)
            self.bar_max = max(1, self.bar_canvas.winfo_width())
            self.bar_width = int(progress * self.bar_max)
            self.bar_canvas.delete("all")
            if self.bar_width > 0:
                self.bar_canvas.create_rectangle(0, 0, self.bar_width, 8,
                                                  fill='#818cf8', outline='')
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            pass

    def close(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass


class NativeSplash:
    """Keep the PyInstaller bootloader splash visible until the main UI paints."""

    def __init__(self):
        import pyi_splash
        self._splash = pyi_splash

    def update(self, text, _progress):
        try:
            self._splash.update_text(text)
        except Exception:
            logger.debug("Native splash text update failed", exc_info=True)

    def close(self):
        try:
            self._splash.close()
        except Exception:
            logger.debug("Native splash close failed", exc_info=True)


def _create_startup_splash():
    if "--launcher-splash" in sys.argv:
        return SplashScreen()
    if getattr(sys, "frozen", False) and os.environ.get("_PYI_SPLASH_IPC"):
        try:
            return NativeSplash()
        except (ImportError, KeyError, OSError):
            logger.exception("Native splash unavailable; using Tk fallback")
    return SplashScreen()


# ─── 진입점 ───

def _load_heavy_modules_step(splash, step, prog):
    splash.update(step, prog)
    time.sleep(0.01)


def _preflight_ffmpeg():
    """Resolve and verify FFmpeg before importing MoviePy."""
    from ffmpeg_service import resolve_ffmpeg_executable
    return resolve_ffmpeg_executable(force_refresh=True)


def _write_ffmpeg_log(lines):
    try:
        # exe가 있는 실제 경로에 로그 저장 (PyInstaller 임시 폴더가 아님)
        if getattr(sys, 'frozen', False):
            log_dir = os.path.dirname(sys.executable)
        else:
            log_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(log_dir, "ffmpeg_debug.log")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    except Exception:
        # 최후의 수단: 유저 홈
        try:
            log_path = os.path.join(os.path.expanduser("~"), "ffmpeg_debug.log")
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
        except Exception:
            pass


def main():
    _startup_mark("python_entry")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"AutoPlaylistMaker.Desktop.{APP_VERSION}"
            )
        except (AttributeError, OSError):
            pass

    if getattr(sys, 'frozen', False):
        if sys.stdout is None:
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        if sys.stderr is None:
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')

    splash = _create_startup_splash()
    _startup_mark("startup_splash_visible")

    _load_heavy_modules_step(splash, t("splash.loadingProject"), 0.65)
    _ensure_project_module()
    _startup_mark("project_model_ready")
    _load_heavy_modules_step(splash, t("splash.loadingGui"), 0.90)

    app = AutoPlaylistMakerApp(defer_show=True)
    splash.update(t("splash.complete"), 1.0)
    app.root.deiconify()
    app.root.update_idletasks()
    app.root.update()
    _startup_mark("main_window_interactive")
    splash.close()
    app.root.lift()
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        try:
            log_dir = (
                os.path.dirname(sys.executable)
                if getattr(sys, 'frozen', False)
                else os.path.dirname(os.path.abspath(__file__))
            )
            with open(
                os.path.join(log_dir, "startup_error.log"),
                "w",
                encoding="utf-8",
            ) as error_file:
                error_file.write(traceback.format_exc())
        except Exception:
            pass
        raise
