import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import copy
import threading
import os
import tempfile
import logging
import queue
import sys
import time
import uuid
import numpy as np
from PIL import Image, ImageTk, ImageDraw
from timeline_utils import compute_two_track_window, build_track_boundaries
from repeat_settings import estimate_group_duration
from i18n import t, choice_id
from audio_preview import AudioPreviewPlayer
from ffmpeg_service import ensure_ffmpeg_available, resolve_ffmpeg_executable
from ambient_library import (
    CATEGORY_GROUPS, CATEGORY_PRESETS, SoundLibrary, rescan_sound_library,
)

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}
logger = logging.getLogger(__name__)
FIT_CHOICES = {"cover": "design.cover", "contain": "design.contain"}
VISUALIZER_CHOICES = {
    "eq_bars": "design.vizBars",
    "waveform": "design.vizMinimal",
    "spectrum": "design.vizSpectrum",
    "circles": "design.vizCircles",
    "radial": "design.vizRadial",
    "none": "design.vizNone",
}
POSITION_CHOICES = {
    "top": "design.top", "center": "design.center", "bottom": "design.bottom"
}
ALIGN_CHOICES = {
    "left": "design.left", "center": "design.center", "right": "design.right"
}
RESOLUTION_CHOICES = {
    "720p": "render.res720",
    "1080p": "render.res1080",
    "4k": "render.res4k",
    "portrait": "design.resolutionPortrait",
    "square": "design.resolutionSquare",
    "custom": "design.resCustom",
}
METER_SOURCE_CHOICES = {
    "master": "globalAudio.finalMaster",
    "music": "globalAudio.musicBus",
    "ambient": "globalAudio.ambientBus",
}

EFFECT_DEFINITIONS = {
    "global_audio": ("basic", "globalAudio.title"),
    "scene_transition": ("basic", "design.sceneTransition"),
    "background": ("basic", "design.background"),
    "album": ("basic", "design.albumArt"),
    "logo": ("basic", "design.logo"),
    "track_info": ("text", "design.text"),
    "custom_text": ("text", "design.customText"),
    "visualizer": ("audio", "design.visualizer"),
    "ambience_mixer": ("audio_effect", "effects.ambienceMixer"),
    "fade": ("motion", "design.fade"),
    "beat": ("motion", "design.beatEffects"),
    "crt": ("color", "design.crt"),
    "visibility": ("other", "design.visibility"),
}
DEFAULT_EFFECT_IDS = ("global_audio", "scene_transition", "background")
# The renderer has a real, fixed composition pipeline.  Only effects in the
# same stage may be reordered; currently that is the image-overlay pair.
EFFECT_COMPOSITION_STAGES = {
    "global_audio": (20, "effects.stageGlobalAudio"),
    "scene_transition": (0, "effects.stageTransition"),
    "background": (0, "effects.stageBackground"),
    "album": (1, "effects.stageOverlay"),
    "logo": (1, "effects.stageOverlay"),
    "track_info": (2, "effects.stageText"),
    "custom_text": (2, "effects.stageText"),
    "visualizer": (3, "effects.stageVisualizer"),
    "ambience_mixer": (30, "effects.stageAudio"),
    "fade": (4, "effects.stageFade"),
    "beat": (5, "effects.stageBeat"),
    "crt": (6, "effects.stagePost"),
    "visibility": (7, "effects.stageVisibility"),
}
AMBIENCE_MIXER_GROUPS = {
    "nature": (
        "rain", "thunder", "wind", "ocean", "stream", "forest",
        "birds", "crickets",
    ),
    "indoor": ("fire", "cafe", "fan", "ventilation"),
    "urban": ("city", "train"),
}
EFFECT_DEFAULT_GROUPS = {
    "background": [
        {"bg_image": "", "bg_fit_var": "cover"},
    ],
    "album": [
        {"album_image_var": ""},
        {
            "album_x_var": 80, "album_y_var": 80,
            "album_width_var": 360, "album_opacity_var": 1.0,
        },
    ],
    "logo": [
        {"logo_image_var": ""},
        {
            "logo_x_var": 1660, "logo_y_var": 60,
            "logo_width_var": 180, "logo_opacity_var": 1.0,
        },
    ],
    "visualizer": [
        {"viz_type": "eq_bars", "viz_pos": "bottom"},
        {
            "viz_bars": 48, "viz_height": 104, "viz_smooth": 0.3,
            "viz_decay": 0.82, "viz_bar_width": 0, "viz_bar_gap": 4,
            "viz_min_height": 2, "viz_sensitivity": 1.0,
        },
        {
            "viz_opacity": 0.9, "viz_corner_radius": 4,
            "viz_glow": 3, "viz_line_width": 2,
            "viz_mirror": False, "viz_invert": False,
            "viz_gradient": True, "viz_color": "#6f8cff",
        },
        {"viz_x_var": 0.0, "viz_y_var": 0.0, "viz_w_var": 0},
    ],
    "fade": [{"fade_in": 2.0, "fade_out": 3.0}],
    "track_info": [
        {
            "show_title": True, "show_bpm": True, "show_key": True,
            "show_camelot": False, "show_time": True, "show_progress": True,
        },
        {
            "text_font_size_var": 42, "text_sub_font_size_var": 28,
            "text_align_var": "center", "text_bold_var": False,
            "text_italic_var": False, "text_underline_var": False,
            "text_strip_ext_var": True, "text_x_var": 0.5,
            "text_y_var": 0.5, "text_color_var": "#ffffff",
        },
    ],
    "custom_text": [
        {"custom_text_var": ""},
        {"custom_x_var": 0.5, "custom_y_var": 0.3},
        {
            "custom_font_size_var": 36, "custom_bold_var": False,
            "custom_italic_var": False, "custom_underline_var": False,
            "custom_color_var": "#ffffff",
            "custom_affects_fx_var": True,
            "custom_opacity_var": 1.0,
            "custom_outline_width_var": 0,
            "custom_outline_color_var": "#000000",
            "custom_background_var": False,
            "custom_background_color_var": "#000000",
            "custom_background_opacity_var": 0.5,
            "custom_background_padding_var": 12,
            "custom_start_seconds_var": 0.0,
            "custom_end_seconds_var": 0.0,
            "custom_target_track_var": 0,
        },
    ],
    "beat": [{
        "fx_bounce": False, "fx_shake": False, "fx_zoom": False,
        "fx_flash": False, "fx_bounce_i": 1.03, "fx_shake_i": 3,
        "fx_zoom_i": 1.05, "fx_flash_i": 0.3,
    }],
    "crt": [{
        "fx_crt": False, "fx_crt_intensity": 1.0,
        "fx_crt_scanlines": True, "fx_crt_curvature": 0.0,
        "fx_crt_chromatic": 0.0, "fx_crt_vignette": 0.0,
        "fx_crt_noise": 0.0, "fx_crt_flicker": 0.0,
    }],
    "visibility": [{
        "visibility_enabled": False, "visibility_restore": False,
        "visibility_off_h": 0, "visibility_off_m": 0,
        "visibility_off_s": 0, "visibility_restore_h": 0,
        "visibility_restore_m": 0, "visibility_restore_s": 0,
    }],
}


class EffectCard:
    """A singleton settings window for one implemented effect."""

    def __init__(
        self, parent, app_module, effect_id, title,
        on_remove, on_up, on_down, on_reset, on_section_reset,
        removable=True,
    ):
        self.effect_id = effect_id
        self.on_section_reset = on_section_reset
        self.expanded = True
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.window.title(title)
        self.window.geometry("520x680")
        self.window.minsize(420, 360)
        self.window.configure(bg=app_module.THEME["bg_card"])
        self.window.protocol("WM_DELETE_WINDOW", self.window.withdraw)
        self.frame = tk.Frame(
            self.window, bg=app_module.THEME["bg_card"],
            highlightthickness=1,
            highlightbackground=app_module.THEME["border"],
        )
        self.frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.header = tk.Frame(
            self.frame, bg=app_module.THEME["bg_mid"], cursor="hand2"
        )
        self.header.pack(fill=tk.X)
        self.arrow = app_module.styled_label(
            self.header, "▼", size=9, bg=app_module.THEME["bg_mid"]
        )
        self.arrow.pack(side=tk.LEFT, padx=(10, 6), pady=9)
        app_module.styled_label(
            self.header, title, size=11, bold=True,
            bg=app_module.THEME["bg_mid"],
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, pady=9)
        if removable:
            app_module.styled_button(
                self.header, t("effects.remove"), on_remove, "danger", padx=6
            ).pack(side=tk.RIGHT, padx=6, pady=5)
        app_module.styled_button(
            self.header, t("common.reset"), on_reset, padx=6
        ).pack(side=tk.RIGHT, padx=1, pady=5)
        self.body = tk.Frame(self.frame, bg=app_module.THEME["bg_card"])
        self.body.pack(fill=tk.BOTH, expand=True, pady=(2, 8))
        self.canvas = tk.Canvas(
            self.body, bg=app_module.THEME["bg_card"], highlightthickness=0,
        )
        scrollbar = tk.Scrollbar(
            self.body, orient=tk.VERTICAL, command=self.canvas.yview,
        )
        self.content = tk.Frame(
            self.canvas, bg=app_module.THEME["bg_card"],
        )
        content_window = self.canvas.create_window(
            (0, 0), window=self.content, anchor=tk.NW,
        )
        self.content.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(
                content_window, width=event.width
            ),
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind(
            "<MouseWheel>",
            lambda event: self.canvas.yview_scroll(
                int(-event.delta / 120), "units"
            ),
        )
        self.sections = []
        for widget in (self.header, self.arrow):
            widget.bind("<Button-1>", self.toggle, add="+")
            widget.bind("<Return>", self.toggle, add="+")
            widget.bind("<space>", self.toggle, add="+")
        self.header.configure(takefocus=True)

    def toggle(self, _event=None):
        self.expanded = not self.expanded
        if self.expanded:
            self.body.pack(fill=tk.BOTH, expand=True, pady=(2, 8))
            self.arrow.configure(text="▼")
        else:
            self.body.pack_forget()
            self.arrow.configure(text="▶")

    def show(self):
        # Presence in the rack must never open every settings window.
        return

    def hide(self):
        self.window.withdraw()

    def open(self):
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def destroy(self):
        if self.window.winfo_exists():
            self.window.destroy()

    def add_section(self, app_module, title):
        section_index = len(self.sections)
        section = AccordionSection(
            self.content, app_module, title,
            on_reset=lambda: self.on_section_reset(section_index),
        )
        self.sections.append(section)
        return section.content


class AccordionSection:
    def __init__(
        self, parent, app_module, title, initially_expanded=None,
        on_reset=None,
    ):
        self.expanded = (
            not bool(parent.winfo_children())
            if initially_expanded is None else bool(initially_expanded)
        )
        self.frame = tk.Frame(parent, bg=app_module.THEME["bg_card"])
        self.frame.pack(fill=tk.X, padx=6, pady=2)
        self.header = tk.Frame(
            self.frame, bg=app_module.THEME["bg_hover"],
            cursor="hand2", takefocus=True,
        )
        self.header.pack(fill=tk.X)
        self.arrow = app_module.styled_label(
            self.header, "▼" if self.expanded else "▶", size=8,
            bg=app_module.THEME["bg_hover"],
        )
        self.arrow.pack(side=tk.LEFT, padx=(8, 5), pady=6)
        app_module.styled_label(
            self.header, title, size=9, bold=True,
            bg=app_module.THEME["bg_hover"],
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, pady=6)
        self.reset_button = None
        if on_reset is not None:
            self.reset_button = app_module.styled_button(
                self.header, "↶", on_reset, padx=5
            )
            self.reset_button.pack(side=tk.RIGHT, padx=5, pady=3)
        self.content = tk.Frame(
            self.frame, bg=app_module.THEME["bg_card"]
        )
        if self.expanded:
            self.content.pack(fill=tk.X, pady=3)
        for widget in (self.header, self.arrow):
            widget.bind("<Button-1>", self.toggle, add="+")
            widget.bind("<Return>", self.toggle, add="+")
            widget.bind("<space>", self.toggle, add="+")

    def toggle(self, _event=None):
        self.expanded = not self.expanded
        if self.expanded:
            self.content.pack(fill=tk.X, pady=3)
            self.arrow.configure(text="▼")
        else:
            self.content.pack_forget()
            self.arrow.configure(text="▶")


def _get_app_globals(app):
    """Return the module that owns the running app class.

    A frozen executable runs app.py as ``__main__``. Importing ``app`` again
    creates a second module whose lazy globals are still None.
    """
    return sys.modules[app.__class__.__module__]


class Stage4DesignEffects(tk.Frame):
    def __init__(self, parent, app):
        self.app = app
        self._a = _get_app_globals(app)
        super().__init__(parent, bg=self._a.THEME['bg_main'])
        self.selected_group = 0
        self.active_effect_ids = []
        self.effect_enabled_states = {}
        self.effect_card_states = {}
        self.effect_cards = {}
        self._rack_window = None
        self._rack_slots_frame = None
        self._pane_ratio_applied = False
        self.build_ui()

    def build_ui(self):
        a = self._a
        T = a.THEME
        hdr = tk.Frame(self, bg=T['bg_main'])
        hdr.pack(fill=tk.X, padx=24, pady=(14, 0))
        a.styled_label(hdr, t("design.title"), size=20, bold=True, bg=T['bg_main']).pack(side=tk.LEFT)
        a.styled_button(hdr, t("common.save"), lambda: self.app.persist_video_groups(), padx=10).pack(side=tk.RIGHT, padx=2)

        self.tabs_container = tk.Frame(self, bg=T['bg_main'])
        self.tabs_container.pack(pady=(0, 4))

        main = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, bg=T['bg_main'], sashwidth=6,
            sashrelief=tk.FLAT, borderwidth=0, showhandle=False,
        )
        self.main_pane = main
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))

        left = tk.Frame(
            main, bg=T['bg_card'], highlightthickness=1,
            highlightbackground=T['border'],
        )
        self.effects_panel = left
        main.add(left, width=240, minsize=200)

        rack_header = tk.Frame(left, bg=T['bg_card'])
        rack_header.pack(fill=tk.X, padx=8, pady=(8, 4))
        a.styled_label(
            rack_header, t("effects.rackTitle"), size=13, bold=True,
            bg=T['bg_card'],
        ).pack(side=tk.LEFT)
        self._effect_add_button = a.styled_button(
            rack_header, t("effects.add"), self._open_effect_picker,
            "success", padx=8,
        )
        self._effect_add_button.pack(side=tk.RIGHT)
        self._effect_add_button.bind(
            "<Enter>", lambda _event: self.after(
                140, self._open_effect_picker_if_hovered
            ), add="+",
        )
        self.effect_summary_label = a.styled_label(
            left, "", size=8, color=T['fg_dim'], bg=T['bg_card'],
        )
        self.effect_summary_label.pack(fill=tk.X, padx=10, pady=(0, 4))
        rack_split = tk.PanedWindow(
            left, orient=tk.VERTICAL, bg=T['bg_card'], sashwidth=6,
            sashrelief=tk.FLAT, borderwidth=0, showhandle=False,
        )
        self.rack_settings_pane = rack_split
        rack_split.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        rack_body = tk.Frame(rack_split, bg=T['bg_card'])
        rack_split.add(
            rack_body, height=230, minsize=100, stretch="always"
        )
        rack_canvas = tk.Canvas(
            rack_body, bg=T['bg_card'], highlightthickness=0,
        )
        rack_scrollbar = tk.Scrollbar(
            rack_body, orient=tk.VERTICAL, command=rack_canvas.yview,
        )
        rack_slots = tk.Frame(rack_canvas, bg=T['bg_card'])
        self._rack_slots_frame = rack_slots
        rack_window = rack_canvas.create_window(
            (0, 0), window=rack_slots, anchor=tk.NW,
        )
        rack_slots.bind(
            "<Configure>", lambda _event: rack_canvas.configure(
                scrollregion=rack_canvas.bbox("all")
            ),
        )
        rack_canvas.bind(
            "<Configure>", lambda event: rack_canvas.itemconfigure(
                rack_window, width=event.width
            ),
        )
        rack_canvas.configure(yscrollcommand=rack_scrollbar.set)
        rack_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rack_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        rack_canvas.bind(
            "<MouseWheel>", lambda event: rack_canvas.yview_scroll(
                int(-event.delta / 120), "units"
            ),
        )
        settings_body = tk.Frame(rack_split, bg=T['bg_card'])
        rack_split.add(
            settings_body, height=150, minsize=80, stretch="never"
        )
        tk.Frame(settings_body, bg=T['separator'], height=1).pack(
            fill=tk.X, padx=8, pady=(0, 2)
        )
        canvas = tk.Canvas(
            settings_body, bg=T['bg_card'], highlightthickness=0
        )
        self._settings_canvas = canvas
        sb = tk.Scrollbar(settings_body, orient=tk.VERTICAL, command=canvas.yview,
                          bg=T['bg_mid'], troughcolor=T['bg_input'],
                          activebackground=T['accent'], width=14, relief=tk.FLAT,
                          highlightthickness=0)
        sf = tk.Frame(canvas, bg=T['bg_card'])
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=sf, anchor=tk.NW)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 2))

        def _sf_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _sf_mousewheel)
        sf.bind("<MouseWheel>", _sf_mousewheel)

        self.viz_type = tk.StringVar(value="eq_bars")
        self.viz_pos = tk.StringVar(value="bottom")
        self.viz_color = tk.StringVar(value="#6f8cff")
        self.viz_bars = tk.IntVar(value=48)
        self.viz_height = tk.IntVar(value=104)
        self.viz_smooth = tk.DoubleVar(value=0.3)
        self.viz_bar_width = tk.IntVar(value=0)
        self.viz_bar_gap = tk.IntVar(value=4)
        self.viz_min_height = tk.IntVar(value=2)
        self.viz_sensitivity = tk.DoubleVar(value=1.0)
        self.viz_opacity = tk.DoubleVar(value=0.9)
        self.viz_corner_radius = tk.IntVar(value=4)
        self.viz_decay = tk.DoubleVar(value=0.82)
        self.viz_mirror = tk.BooleanVar(value=False)
        self.viz_invert = tk.BooleanVar(value=False)
        self.viz_gradient = tk.BooleanVar(value=True)
        self.viz_glow = tk.IntVar(value=3)
        self.viz_line_width = tk.IntVar(value=2)
        self.music_master_db = tk.DoubleVar(value=0.0)
        self.normalize_tracks = tk.BooleanVar(value=False)
        self.target_lufs = tk.DoubleVar(value=-14.0)
        self.true_peak_ceiling = tk.DoubleVar(value=-1.0)
        self.max_normalize_gain = tk.DoubleVar(value=12.0)
        self.crossfade_duration = tk.DoubleVar(value=4.0)
        self.ambience_random_seed = tk.IntVar(value=12345)
        self.ambience_sources = {
            source_id: {
                "enabled": False,
                "volume_db": float(CATEGORY_PRESETS[source_id][0]),
            }
            for source_ids in AMBIENCE_MIXER_GROUPS.values()
            for source_id in source_ids
        }
        self._ambience_source_vars = {}
        self._ambience_state_sync = False
        self._legacy_ambient_tracks = []
        self.meter_source = tk.StringVar(value="master")
        self.sound_library = SoundLibrary()
        self._ambient_picker = None
        self._ambient_source_manager = None
        self._ambient_rescan_window = None
        self._ambient_rescan_cancel_event = None
        self._ambient_rescan_queue = queue.Queue()
        self._ambient_preview_player = AudioPreviewPlayer(
            resolve_ffmpeg_executable
        )
        self._ambient_selection_sync = False
        self.bg_image = tk.StringVar(value="")
        self.bg_fit_var = tk.StringVar(value="cover")
        self.album_image_var = tk.StringVar(value="")
        self.album_x_var = tk.IntVar(value=80)
        self.album_y_var = tk.IntVar(value=80)
        self.album_width_var = tk.IntVar(value=360)
        self.album_opacity_var = tk.DoubleVar(value=1.0)
        self.logo_image_var = tk.StringVar(value="")
        self.logo_x_var = tk.IntVar(value=1660)
        self.logo_y_var = tk.IntVar(value=60)
        self.logo_width_var = tk.IntVar(value=180)
        self.logo_opacity_var = tk.DoubleVar(value=1.0)
        self.fade_in = tk.DoubleVar(value=2.0)
        self.fade_out = tk.DoubleVar(value=3.0)
        self.show_title = tk.BooleanVar(value=True)
        self.show_bpm = tk.BooleanVar(value=True)
        self.show_key = tk.BooleanVar(value=True)
        self.show_camelot = tk.BooleanVar(value=False)
        self.show_time = tk.BooleanVar(value=True)
        self.show_progress = tk.BooleanVar(value=True)
        self.text_font_size_var = tk.IntVar(value=42)
        self.text_sub_font_size_var = tk.IntVar(value=28)
        self.text_color_var = tk.StringVar(value="#ffffff")
        self.text_align_var = tk.StringVar(value="center")
        self.text_x_var = tk.DoubleVar(value=0.5)
        self.text_y_var = tk.DoubleVar(value=0.5)
        self.text_bold_var = tk.BooleanVar(value=False)
        self.text_italic_var = tk.BooleanVar(value=False)
        self.text_underline_var = tk.BooleanVar(value=False)
        self.text_strip_ext_var = tk.BooleanVar(value=True)
        self.fx_bounce = tk.BooleanVar(value=False)
        self.fx_shake = tk.BooleanVar(value=False)
        self.fx_zoom = tk.BooleanVar(value=False)
        self.fx_flash = tk.BooleanVar(value=False)
        self.fx_bounce_i = tk.DoubleVar(value=1.03)
        self.fx_shake_i = tk.DoubleVar(value=3)
        self.fx_zoom_i = tk.DoubleVar(value=1.05)
        self.fx_flash_i = tk.DoubleVar(value=0.3)
        self.fx_crt = tk.BooleanVar(value=False)
        self.fx_crt_intensity = tk.DoubleVar(value=1.0)
        self.fx_crt_scanlines = tk.BooleanVar(value=True)
        self.fx_crt_curvature = tk.DoubleVar(value=0.0)
        self.fx_crt_chromatic = tk.DoubleVar(value=0.0)
        self.fx_crt_vignette = tk.DoubleVar(value=0.0)
        self.fx_crt_noise = tk.DoubleVar(value=0.0)
        self.fx_crt_flicker = tk.DoubleVar(value=0.0)
        self.resolution = tk.StringVar(value="1080p")
        self.custom_width_var = tk.StringVar(value="1920")
        self.custom_height_var = tk.StringVar(value="1080")
        self.fps_var = tk.StringVar(value="24")
        self.visibility_enabled = tk.BooleanVar(value=False)
        self.visibility_restore = tk.BooleanVar(value=False)
        self.visibility_off_h = tk.IntVar(value=0)
        self.visibility_off_m = tk.IntVar(value=0)
        self.visibility_off_s = tk.IntVar(value=0)
        self.visibility_restore_h = tk.IntVar(value=0)
        self.visibility_restore_m = tk.IntVar(value=0)
        self.visibility_restore_s = tk.IntVar(value=0)

        self._render_cancel_event = threading.Event()
        self._render_job = None
        self._last_render_dir = None
        self._preview_render_lock = threading.Lock()
        self._preview_frame_worker_active = False
        self._preview_requested_t = None

        self._two_track_mode = tk.BooleanVar(value=True)
        self.preview_range_var = tk.StringVar(value="two")
        self.preview_quality_var = tk.StringVar(value="auto")
        self.preview_width_var = tk.StringVar(value="960")
        self.preview_height_var = tk.StringVar(value="540")
        self._two_track_index = 0
        form_root = sf
        current_card = None

        global_audio_section = AccordionSection(
            form_root, a, t("globalAudio.title"), initially_expanded=False,
        )
        self._global_audio_section = global_audio_section
        self._global_audio_card = global_audio_section.frame
        audio_card = global_audio_section.content
        music_section = AccordionSection(
            audio_card, a, t("globalAudio.music"),
            initially_expanded=True,
        )
        audio_music = tk.Frame(music_section.content, bg=T['bg_card'])
        audio_music.pack(fill=tk.X, padx=10, pady=2)
        a.styled_label(
            audio_music, t("globalAudio.musicMaster"), size=9,
            bg=T['bg_card'], width=16,
        ).pack(side=tk.LEFT)
        a.styled_scale(
            audio_music, self.music_master_db, -60, 12, .5,
            bg=T['bg_card'],
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        normalization_section = AccordionSection(
            audio_card, a, t("globalAudio.normalization"),
            initially_expanded=False,
        )
        a.styled_checkbutton(
            normalization_section.content, t("globalAudio.normalizeTracks"),
            self.normalize_tracks, bg=T['bg_card'],
        ).pack(anchor=tk.W, padx=10, pady=3)
        for label_key, variable, low, high, step in (
            ("globalAudio.targetLufs", self.target_lufs, -24, -8, .5),
            ("globalAudio.maxGain", self.max_normalize_gain, 0, 24, .5),
        ):
            row = tk.Frame(normalization_section.content, bg=T['bg_card'])
            row.pack(fill=tk.X, padx=10, pady=2)
            a.styled_label(
                row, t(label_key), size=9, bg=T['bg_card'], width=16,
            ).pack(side=tk.LEFT)
            a.styled_scale(
                row, variable, low, high, step, bg=T['bg_card'],
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.loudness_summary_label = a.styled_label(
            normalization_section.content, "", size=8,
            color=T['fg_dim'], bg=T['bg_card'],
        )
        self.loudness_summary_label.pack(
            fill=tk.X, padx=10, pady=(5, 7), anchor=tk.W
        )

        advanced_section = AccordionSection(
            audio_card, a, t("globalAudio.advanced"),
            initially_expanded=False,
        )
        advanced_row = tk.Frame(
            advanced_section.content, bg=T['bg_card']
        )
        advanced_row.pack(fill=tk.X, padx=10, pady=2)
        a.styled_label(
            advanced_row, t("globalAudio.truePeak"), size=9,
            bg=T['bg_card'], width=16,
        ).pack(side=tk.LEFT)
        a.styled_scale(
            advanced_row, self.true_peak_ceiling, -6, 0, .5,
            bg=T['bg_card'],
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        for variable in (
            self.target_lufs, self.max_normalize_gain,
            self.true_peak_ceiling,
        ):
            variable.trace_add("write", self._update_loudness_summary)

        transition_card = tk.Frame(
            form_root, bg=T['bg_card'], highlightthickness=1,
            highlightbackground=T['border'],
        )
        transition_card.pack(fill=tk.X, padx=8, pady=6)
        self._scene_transition_card = transition_card
        a.styled_label(
            transition_card, t("design.sceneTransition"), size=13,
            bold=True, bg=T['bg_card'],
        ).pack(fill=tk.X, padx=10, pady=(10, 4), anchor=tk.W)
        transition_row = tk.Frame(transition_card, bg=T['bg_card'])
        transition_row.pack(fill=tk.X, padx=10, pady=(2, 10))
        a.styled_label(
            transition_row, t("design.crossfadeDuration"), size=9,
            bg=T['bg_card'], width=16,
        ).pack(side=tk.LEFT)
        a.styled_scale(
            transition_row, self.crossfade_duration, 0, 12, .5,
            bg=T['bg_card'],
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.effects_list_frame = tk.Frame(form_root, bg=T['bg_card'])
        self._effects_empty = a.styled_label(
            self.effects_list_frame, t("effects.empty"), size=9,
            color=T['fg_dim'], bg=T['bg_card'],
        )

        def begin_effect(effect_id):
            nonlocal current_card
            category, label_key = EFFECT_DEFINITIONS[effect_id]
            card = EffectCard(
                self.effects_list_frame, a, effect_id, t(label_key),
                lambda eid=effect_id: self._remove_effect(eid),
                lambda eid=effect_id: self._move_effect(eid, -1),
                lambda eid=effect_id: self._move_effect(eid, 1),
                lambda eid=effect_id: self._reset_effect(eid),
                lambda section, eid=effect_id: (
                    self._reset_effect_section(eid, section)
                ),
                removable=effect_id not in DEFAULT_EFFECT_IDS,
            )
            card.category = category
            card.hide()
            self.effect_cards[effect_id] = card
            current_card = card
            return card.content

        def sec(text):
            nonlocal sf
            if current_card is not None and sf is not form_root:
                sf = current_card.add_section(a, text)
                return
            a.styled_label(sf, text, size=11, bold=True, bg=T['bg_card']).pack(fill=tk.X, pady=(12, 3), padx=12, anchor=tk.W)

        def sep():
            tk.Frame(sf, bg=T['separator'], height=1).pack(fill=tk.X, padx=12, pady=6)

        def opt(label, var, opts):
            f = tk.Frame(sf, bg=T['bg_card'])
            f.pack(fill=tk.X, padx=12, pady=2)
            if label: a.styled_label(f, label, size=10, bg=T['bg_card']).pack(side=tk.LEFT)
            m = (
                a.styled_choice_menu(f, var, opts)
                if isinstance(opts, dict)
                else a.styled_option_menu(f, var, opts)
            )
            m.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def chk(label, var):
            f = tk.Frame(sf, bg=T['bg_card'])
            f.pack(fill=tk.X, padx=12, pady=2)
            a.styled_checkbutton(f, label, var, bg=T['bg_card']).pack(side=tk.LEFT)

        def sld(label, var, fr, to, res):
            f = tk.Frame(sf, bg=T['bg_card'])
            f.pack(fill=tk.X, padx=12, pady=2)
            a.styled_label(f, label, size=10, bg=T['bg_card'], width=11).pack(side=tk.LEFT)
            a.styled_scale(f, var, fr, to, res, bg=T['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True)

        sf = begin_effect("background")
        sec(t("effects.basic"))
        bf = tk.Frame(sf, bg=T['bg_card'])
        bf.pack(fill=tk.X, padx=12, pady=(0, 3))
        a.styled_entry(bf, textvariable=self.bg_image, width=20).pack(side=tk.LEFT, fill=tk.X, expand=True)
        a.styled_button(bf, t("common.browse"), lambda: self._pick_bg(), padx=6).pack(side=tk.RIGHT, padx=(4, 0))
        a.styled_label(sf, t("design.noImage"), size=8, color=T['fg_dimmer'], bg=T['bg_card']).pack(anchor=tk.W, padx=12)
        opt(t("design.fit"), self.bg_fit_var, FIT_CHOICES)

        def overlay_controls(path_var, x_var, y_var, width_var, opacity_var):
            row = tk.Frame(sf, bg=T['bg_card'])
            row.pack(fill=tk.X, padx=12, pady=2)
            a.styled_entry(row, textvariable=path_var, width=18).pack(side=tk.LEFT, fill=tk.X, expand=True)
            a.styled_button(row, t("common.browse"), lambda: self._pick_overlay(path_var), padx=6).pack(side=tk.RIGHT, padx=(4, 0))
            sec(t("effects.transform"))
            sld(t("design.x"), x_var, 0, 3840, 1)
            sld(t("design.y"), y_var, 0, 2160, 1)
            sld(t("design.width"), width_var, 16, 1920, 1)
            sld(t("design.opacity"), opacity_var, 0, 1, 0.05)

        sf = begin_effect("album")
        sec(t("effects.basic"))
        overlay_controls(self.album_image_var, self.album_x_var, self.album_y_var, self.album_width_var, self.album_opacity_var)
        sf = begin_effect("logo")
        sec(t("effects.basic"))
        overlay_controls(self.logo_image_var, self.logo_x_var, self.logo_y_var, self.logo_width_var, self.logo_opacity_var)

        sf = begin_effect("visualizer")
        sec(t("effects.basic"))
        opt(t("design.type"), self.viz_type, VISUALIZER_CHOICES)
        opt(t("design.position"), self.viz_pos, POSITION_CHOICES)
        sec(t("effects.audioResponse"))
        sld(t("design.barCount"), self.viz_bars, 8, 256, 8)
        sld(t("design.height"), self.viz_height, 40, 300, 10)
        sld(t("design.smoothing"), self.viz_smooth, 0, 0.95, 0.05)
        sld(t("design.decay"), self.viz_decay, 0, 0.99, 0.01)
        sld(t("design.barWidth"), self.viz_bar_width, 0, 30, 1)
        sld(t("design.barGap"), self.viz_bar_gap, 0, 16, 1)
        sld(t("design.minHeight"), self.viz_min_height, 0, 30, 1)
        sld(t("design.sensitivity"), self.viz_sensitivity, 0.1, 3.0, 0.1)
        sec(t("effects.style"))
        sld(t("design.opacity"), self.viz_opacity, 0.1, 1.0, 0.05)
        sld(t("design.roundness"), self.viz_corner_radius, 0, 16, 1)
        sld(t("design.glow"), self.viz_glow, 0, 20, 1)
        sld(t("design.lineWidth"), self.viz_line_width, 1, 12, 1)
        chk(t("design.mirror"), self.viz_mirror)
        chk(t("design.reverse"), self.viz_invert)
        chk(t("design.gradient"), self.viz_gradient)
        viz_color_row = tk.Frame(sf, bg=T['bg_card'])
        viz_color_row.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(viz_color_row, t("design.color"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_entry(viz_color_row, textvariable=self.viz_color, width=10).pack(side=tk.LEFT, padx=4)

        sec(t("effects.transform"))
        self.viz_x_var = tk.DoubleVar(value=0)
        self.viz_y_var = tk.DoubleVar(value=0)
        self.viz_w_var = tk.IntVar(value=0)
        sv1 = tk.Frame(sf, bg=T['bg_card'])
        sv1.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(sv1, t("design.xOffset"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_scale(sv1, self.viz_x_var, 0, 3840, 1, bg=T['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        sv2 = tk.Frame(sf, bg=T['bg_card'])
        sv2.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(sv2, t("design.yOffset"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_scale(sv2, self.viz_y_var, 0, 2160, 1, bg=T['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        sv3 = tk.Frame(sf, bg=T['bg_card'])
        sv3.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(sv3, t("design.width"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_scale(sv3, self.viz_w_var, 0, 3840, 1, bg=T['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        sf = begin_effect("ambience_mixer")
        a.styled_label(
            sf, t("ambientUi.mixerHint"), size=9,
            color=T["fg_dim"], bg=T["bg_card"],
        ).pack(fill=tk.X, padx=12, pady=(8, 2), anchor=tk.W)
        for group_id, source_ids in AMBIENCE_MIXER_GROUPS.items():
            sec(t(f"ambientGroup.{group_id}"))
            for source_id in source_ids:
                state = self.ambience_sources[source_id]
                enabled_var = tk.BooleanVar(value=state["enabled"])
                volume_var = tk.DoubleVar(value=state["volume_db"])
                self._ambience_source_vars[source_id] = (
                    enabled_var, volume_var
                )
                row = tk.Frame(sf, bg=T["bg_card"])
                row.pack(fill=tk.X, padx=12, pady=3)
                a.styled_checkbutton(
                    row, t(f"ambientCategory.{source_id}"), enabled_var,
                    bg=T["bg_card"],
                ).pack(side=tk.LEFT, padx=(0, 6))
                scale = a.styled_scale(
                    row, volume_var, -60, 6, .5, bg=T["bg_card"],
                )
                scale.pack(side=tk.RIGHT, fill=tk.X, expand=True)
                enabled_var.trace_add(
                    "write",
                    lambda *_args, sid=source_id:
                    self._update_ambience_source(sid),
                )
                volume_var.trace_add(
                    "write",
                    lambda *_args, sid=source_id:
                    self._update_ambience_source(sid),
                )
        ambience_actions = tk.Frame(sf, bg=T["bg_card"])
        ambience_actions.pack(fill=tk.X, padx=12, pady=(8, 6))
        a.styled_button(
            ambience_actions, t("ambientUi.rescanLibrary"),
            self._rescan_ambient_library, padx=7,
        ).pack(side=tk.LEFT)

        sf = begin_effect("fade")
        sec(t("effects.basic"))
        sld(t("design.fadeIn"), self.fade_in, 0, 10, 0.5)
        sld(t("design.fadeOut"), self.fade_out, 0, 10, 0.5)

        sf = begin_effect("track_info")
        sec(t("effects.basic"))
        chk(t("design.showTitle"), self.show_title)
        chk(t("design.showBpm"), self.show_bpm)
        chk(t("design.showKey"), self.show_key)
        chk(t("design.showCamelot"), self.show_camelot)
        chk(t("design.showTimer"), self.show_time)
        chk(t("design.showProgress"), self.show_progress)
        sec(t("effects.style"))
        sld(t("design.titleSize"), self.text_font_size_var, 12, 160, 1)
        sld(t("design.infoSize"), self.text_sub_font_size_var, 10, 100, 1)
        opt(t("design.align"), self.text_align_var, ALIGN_CHOICES)
        chk(t("design.bold"), self.text_bold_var)
        chk(t("design.italic"), self.text_italic_var)
        chk(t("design.underline"), self.text_underline_var)
        chk(t("design.hideExtension"), self.text_strip_ext_var)
        sld(t("design.textX"), self.text_x_var, 0, 1, 0.01)
        sld(t("design.textY"), self.text_y_var, 0, 1, 0.01)
        text_color_row = tk.Frame(sf, bg=T['bg_card'])
        text_color_row.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(text_color_row, t("design.color"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_entry(text_color_row, textvariable=self.text_color_var, width=10).pack(side=tk.LEFT, padx=4)

        self.text_font_family_var = tk.StringVar(value=a.FONT_FAMILY)
        tf_font = tk.Frame(sf, bg=T['bg_card'])
        tf_font.pack(fill=tk.X, padx=12, pady=(6, 2))
        a.styled_label(tf_font, t("design.textFont"), size=10, bg=T['bg_card']).pack(anchor=tk.W)
        from font_combo import SearchableFontComboBox
        SearchableFontComboBox(tf_font, self.text_font_family_var, T, a._font(9)).pack(fill=tk.X)

        sf = begin_effect("custom_text")
        sec(t("effects.basic"))
        self.custom_text_var = tk.StringVar(value="")
        cf1 = tk.Frame(sf, bg=T['bg_card'])
        cf1.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(cf1, t("design.textLabel"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_entry(cf1, textvariable=self.custom_text_var, width=20).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        sec(t("effects.transform"))
        cf2 = tk.Frame(sf, bg=T['bg_card'])
        cf2.pack(fill=tk.X, padx=12, pady=2)
        self.custom_x_var = tk.DoubleVar(value=0.5)
        self.custom_y_var = tk.DoubleVar(value=0.3)
        a.styled_label(cf2, t("design.xOffset"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_scale(cf2, self.custom_x_var, 0.0, 1.0, 0.01, bg=T['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        cf3 = tk.Frame(sf, bg=T['bg_card'])
        cf3.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(cf3, t("design.yOffset"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_scale(cf3, self.custom_y_var, 0.0, 1.0, 0.01, bg=T['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        cf4 = tk.Frame(sf, bg=T['bg_card'])
        cf4.pack(fill=tk.X, padx=12, pady=2)
        self.custom_font_size_var = tk.IntVar(value=36)
        self.custom_bold_var = tk.BooleanVar(value=False)
        self.custom_italic_var = tk.BooleanVar(value=False)
        self.custom_underline_var = tk.BooleanVar(value=False)
        a.styled_label(cf4, t("design.fontSize"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_scale(cf4, self.custom_font_size_var, 8, 120, 1, bg=T['bg_card']).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        cf5 = tk.Frame(sf, bg=T['bg_card'])
        cf5.pack(fill=tk.X, padx=12, pady=2)
        a.styled_checkbutton(cf5, t("design.fontBold"), self.custom_bold_var, bg=T['bg_card']).pack(side=tk.LEFT, padx=(0,8))
        a.styled_checkbutton(cf5, t("design.fontItalic"), self.custom_italic_var, bg=T['bg_card']).pack(side=tk.LEFT, padx=(0,8))
        a.styled_checkbutton(cf5, t("design.fontUnderline"), self.custom_underline_var, bg=T['bg_card']).pack(side=tk.LEFT)

        self.custom_color_var = tk.StringVar(value="#ffffff")
        sec(t("effects.style"))
        cf6 = tk.Frame(sf, bg=T['bg_card'])
        cf6.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(cf6, t("design.color"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_entry(cf6, textvariable=self.custom_color_var, width=10).pack(side=tk.LEFT, padx=4)

        self.custom_font_family_var = tk.StringVar(value=a.FONT_FAMILY)
        cf_font = tk.Frame(sf, bg=T['bg_card'])
        cf_font.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(cf_font, t("design.fontFamily"), size=10, bg=T['bg_card']).pack(anchor=tk.W)
        SearchableFontComboBox(cf_font, self.custom_font_family_var, T, a._font(9)).pack(fill=tk.X)

        self.custom_affects_fx_var = tk.BooleanVar(value=True)
        cf7 = tk.Frame(sf, bg=T['bg_card'])
        cf7.pack(fill=tk.X, padx=12, pady=2)
        a.styled_checkbutton(cf7, t("design.affectedByEffects"), self.custom_affects_fx_var, bg=T['bg_card']).pack(side=tk.LEFT)

        self.custom_opacity_var = tk.DoubleVar(value=1.0)
        self.custom_outline_width_var = tk.IntVar(value=0)
        self.custom_outline_color_var = tk.StringVar(value="#000000")
        self.custom_background_var = tk.BooleanVar(value=False)
        self.custom_background_color_var = tk.StringVar(value="#000000")
        self.custom_background_opacity_var = tk.DoubleVar(value=0.5)
        self.custom_background_padding_var = tk.IntVar(value=12)
        self.custom_start_seconds_var = tk.DoubleVar(value=0.0)
        self.custom_end_seconds_var = tk.DoubleVar(value=0.0)
        self.custom_target_track_var = tk.IntVar(value=0)
        sld(t("textEffect.opacity"), self.custom_opacity_var, 0, 1, .05)
        sld(t("textEffect.outlineWidth"), self.custom_outline_width_var, 0, 12, 1)
        chk(t("textEffect.backgroundEnabled"), self.custom_background_var)
        sld(
            t("textEffect.backgroundOpacity"),
            self.custom_background_opacity_var, 0, 1, .05,
        )
        sld(
            t("textEffect.backgroundPadding"),
            self.custom_background_padding_var, 0, 64, 1,
        )
        for label, variable in (
            (t("textEffect.outlineColor"), self.custom_outline_color_var),
            (t("textEffect.backgroundColor"), self.custom_background_color_var),
            (t("textEffect.startSeconds"), self.custom_start_seconds_var),
            (t("textEffect.endSeconds"), self.custom_end_seconds_var),
            (t("textEffect.targetTrack"), self.custom_target_track_var),
        ):
            row = tk.Frame(sf, bg=T['bg_card'])
            row.pack(fill=tk.X, padx=12, pady=2)
            a.styled_label(row, label, size=10, bg=T['bg_card']).pack(side=tk.LEFT)
            a.styled_entry(row, textvariable=variable, width=10).pack(side=tk.RIGHT)

        sf = begin_effect("beat")
        sec(t("effects.basic"))
        chk(t("design.bounce"), self.fx_bounce)
        sld(t("design.bounceIntensity"), self.fx_bounce_i, 1.01, 1.15, 0.01)
        chk(t("design.shake"), self.fx_shake)
        sld(t("design.shakeIntensity"), self.fx_shake_i, 1, 20, 1)
        chk(t("design.zoom"), self.fx_zoom)
        sld(t("design.zoomIntensity"), self.fx_zoom_i, 1.01, 1.20, 0.01)
        chk(t("design.flash"), self.fx_flash)
        sld(t("design.flashIntensity"), self.fx_flash_i, 0.05, 0.8, 0.05)
        sf = begin_effect("crt")
        sec(t("effects.basic"))
        chk(t("design.crtEnable"), self.fx_crt)
        sld(t("design.crtIntensity"), self.fx_crt_intensity, 0.1, 2.0, 0.1)
        chk(t("design.scanline"), self.fx_crt_scanlines)
        sld(t("design.distortion"), self.fx_crt_curvature, 0.0, 5.0, 0.5)
        sld(t("design.chromatic"), self.fx_crt_chromatic, 0.0, 5.0, 0.5)
        sld(t("design.vignette"), self.fx_crt_vignette, 0.0, 3.0, 0.5)
        sld(t("design.noise"), self.fx_crt_noise, 0.0, 3.0, 0.5)
        sld(t("design.flicker"), self.fx_crt_flicker, 0.0, 3.0, 0.5)

        a.styled_button(sf, t("common.refresh"), self._refresh_canvas_preview, "primary", padx=8).pack(padx=12, pady=4, anchor=tk.W)

        sf = begin_effect("visibility")
        sec(t("effects.basic"))
        chk(t("design.visibilityEnable"), self.visibility_enabled)
        a.styled_label(sf, t("design.visibilityOffAt"), size=9, bg=T['bg_card']).pack(anchor=tk.W, padx=12)
        self._build_hms_row(sf, self.visibility_off_h, self.visibility_off_m,
                            self.visibility_off_s)
        mode_frame = tk.Frame(sf, bg=T['bg_card'])
        mode_frame.pack(fill=tk.X, padx=12, pady=2)
        for label, value in (
            (t("design.visibilityNeverRestore"), False),
            (t("design.visibilityRestore"), True),
        ):
            tk.Radiobutton(
                mode_frame, text=label, variable=self.visibility_restore,
                value=value, bg=T['bg_card'], fg=T['fg'],
                selectcolor=T['bg_input'], activebackground=T['bg_card'],
                activeforeground=T['fg'], font=a._font(9),
            ).pack(anchor=tk.W)
        a.styled_label(sf, t("design.visibilityRestoreBefore"), size=9,
                       bg=T['bg_card']).pack(anchor=tk.W, padx=12)
        self._build_hms_row(
            sf, self.visibility_restore_h, self.visibility_restore_m,
            self.visibility_restore_s,
        )

        right = tk.Frame(
            main, bg=T['bg_card'], highlightthickness=1,
            highlightbackground=T['border'],
        )
        self.preview_panel = right
        # The preview is the primary left workspace; the embedded rack stays
        # docked on its right (never in a separate Toplevel).
        main.forget(left)
        main.add(right, minsize=400)
        main.add(left, width=240, minsize=200)
        main.bind(
            "<Map>", lambda _event: self.after_idle(
                self._set_default_pane_ratio
            ), add="+",
        )

        preview_header = tk.Frame(right, bg=T['bg_card'])
        preview_header.pack(fill=tk.X, padx=12, pady=(12, 4))
        a.styled_label(preview_header, t("design.preview"), size=12, bold=True, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_choice_menu(
            preview_header, self.preview_range_var,
            {"one": "design.previewRangeOne", "two": "design.previewRangeTwo"},
        ).pack(side=tk.RIGHT, padx=2)
        preview_settings_section = AccordionSection(
            right, a, t("design.resolution"), initially_expanded=False,
        )
        self._preview_resolution_section = preview_settings_section
        preview_settings_row = preview_settings_section.content
        quality_menu = a.styled_choice_menu(
            preview_settings_row, self.preview_quality_var,
            {
                "auto": "design.previewQualityAuto",
                "low": "design.previewQualityLow",
                "medium": "design.previewQualityMedium",
                "high": "design.previewQualityHigh",
                "custom": "design.previewQualityCustom",
            },
        )
        quality_menu.pack(fill=tk.X, padx=6, pady=(4, 2))
        self.preview_resolution_label = a.styled_label(
            preview_settings_row, "", size=8, color=T['fg_dim'],
            bg=T['bg_card'],
        )
        self.preview_resolution_label.pack(fill=tk.X, padx=6, pady=2)
        custom_resolution_row = tk.Frame(
            preview_settings_row, bg=T['bg_card']
        )
        custom_resolution_row.pack(fill=tk.X, padx=6, pady=(2, 5))
        a.styled_entry(
            custom_resolution_row, textvariable=self.preview_height_var,
            width=5,
        ).pack(side=tk.RIGHT, padx=(2, 0))
        a.styled_label(
            custom_resolution_row, "×", size=8, bg=T['bg_card']
        ).pack(side=tk.RIGHT)
        a.styled_entry(
            custom_resolution_row, textvariable=self.preview_width_var,
            width=5,
        ).pack(side=tk.RIGHT, padx=2)

        preview_body = tk.Frame(right, bg=T['bg_card'])
        preview_body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))
        self.preview_canvas = tk.Canvas(preview_body, bg=T['bg'], highlightthickness=1, highlightbackground=T['separator'])
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        meter_panel = tk.Frame(preview_body, bg=T['bg_mid'], width=112)
        meter_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        meter_panel.pack_propagate(False)
        a.styled_label(
            meter_panel, t("globalAudio.volumeMeter"), size=8, bold=True,
            bg=T['bg_mid'],
        ).pack(pady=(8, 2))
        a.styled_choice_menu(
            meter_panel, self.meter_source, METER_SOURCE_CHOICES
        ).pack(fill=tk.X, padx=5, pady=(0, 3))
        self.meter_canvas = tk.Canvas(
            meter_panel, width=70, bg=T['bg_mid'], highlightthickness=0
        )
        self.meter_canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.meter_value_label = a.styled_label(
            meter_panel, "-∞ dB", size=8, bg=T['bg_mid']
        )
        self.meter_value_label.pack(pady=(0, 8))
        self._meter_hold = [-60.0, -60.0]
        self._meter_clip_until = 0.0
        self._preview_photo = None
        self._last_preview_pil_frame = None
        self.preview_canvas.bind("<Configure>", self._on_preview_canvas_resize)

        prev_ctrl = tk.Frame(right, bg=T['bg_card'])
        prev_ctrl.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.preview_play_btn = a.styled_button(prev_ctrl, t("design.livePlayback"), self._preview_render_video, "primary", padx=6)
        self.preview_play_btn.pack(side=tk.RIGHT, padx=2)
        a.styled_button(prev_ctrl, t("common.refresh"), self._manual_preview_refresh, padx=6).pack(side=tk.RIGHT, padx=2)
        self._preview_status_label = a.styled_label(prev_ctrl, t("design.autoApply"), size=9, color=T['fg_dim'], bg=T['bg_card'])
        self._preview_status_label.pack(side=tk.LEFT)

        scrub_frame = tk.Frame(right, bg=T['bg_card'])
        scrub_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.scrub_var = tk.DoubleVar(value=0)
        self.scrub_scale = ttk.Scale(scrub_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                     variable=self.scrub_var, command=self._on_scrub_drag)
        self.scrub_scale.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.scrub_scale.state(['disabled'])
        self._live_renderer = None
        self._live_duration = 0.0
        self._preview_audio_player = AudioPreviewPlayer(
            resolve_ffmpeg_executable
        )
        self._preview_mixed_audio_path = None
        self._preview_bus_audio_paths = {}
        self._meter_audio_handle = None
        self._meter_audio_path = None
        self._meter_last_update = 0.0
        self._preview_prepare_active = False
        self._preview_ui_queue = queue.Queue()
        self._preview_destroyed = False
        self._preview_ui_after_id = self.after(
            30, self._drain_preview_ui_queue
        )
        self._scrub_playing = False
        self._scrub_after_id = None
        self._programmatic_scrub = False
        self._preview_settings_after_id = None
        self._preview_generation = 0
        self._preview_audio_signature = None
        self._preview_renderer_signature = None
        self._preview_build_signature = None
        self._preview_prepare_cancel_event = None
        self._preview_state = "IDLE"
        self._preview_restore_state = None
        self._preview_pending_refresh = False
        self._preview_first_frame_ready = False
        self._preview_audio_ready = False

        self._track_nav_frame = tk.Frame(right, bg=T['bg_card'])
        self._track_nav_label = a.styled_label(self._track_nav_frame, "", size=9, color=T['fg_dim'], bg=T['bg_card'])
        self._track_nav_label.pack(side=tk.LEFT)
        self._track_prev_btn = a.styled_button(self._track_nav_frame, t("design.prevTrack"), self._prev_track_pair, padx=4)
        self._track_next_btn = a.styled_button(self._track_nav_frame, t("design.nextTrack"), self._next_track_pair, padx=4)

        def _bind_wheel_recursive(widget):
            widget.bind("<MouseWheel>", _sf_mousewheel)
            for child in widget.winfo_children():
                _bind_wheel_recursive(child)

        _bind_wheel_recursive(form_root)
        preview_variables = [
            value for name, value in vars(self).items()
            if isinstance(value, tk.Variable)
            and name not in {
                'scrub_var', 'fps_var',
            }
        ]
        for variable in preview_variables:
            variable.trace_add("write", self._on_effect_state_changed)
        self.preview_range_var.trace_add(
            "write", self._on_preview_range_changed
        )
        self.preview_quality_var.trace_add(
            "write", self._on_preview_quality_changed
        )
        self.preview_width_var.trace_add(
            "write", self._on_preview_quality_changed
        )
        self.preview_height_var.trace_add(
            "write", self._on_preview_quality_changed
        )
        self._update_preview_resolution_label()
        self._refresh_effect_rack()

    def _set_default_pane_ratio(self):
        """Give the preview three quarters of the initial workspace."""
        if self._pane_ratio_applied or not self.main_pane.winfo_ismapped():
            return
        width = self.main_pane.winfo_width()
        if width <= 1 or len(self.main_pane.panes()) < 2:
            return
        sash_width = int(self.main_pane.cget("sashwidth"))
        available = max(0, width - sash_width)
        preview_width = max(400, round(available * .75))
        preview_width = min(preview_width, max(400, available - 200))
        self._pane_ratio_applied = True
        self.main_pane.sash_place(0, preview_width, 0)

    def _build_hms_row(self, parent, hours, minutes, seconds):
        row = tk.Frame(parent, bg=self._a.THEME['bg_card'])
        row.pack(fill=tk.X, padx=12, pady=(1, 5))
        for variable, unit in (
            (hours, t("design.hoursUnit")), (minutes, t("design.minutesUnit")),
            (seconds, t("design.secondsUnit")),
        ):
            self._a.styled_entry(row, textvariable=variable, width=5).pack(side=tk.LEFT)
            self._a.styled_label(
                row, unit, size=8, bg=self._a.THEME['bg_card']
            ).pack(side=tk.LEFT, padx=(2, 8))

    @staticmethod
    def _hms_seconds(hours, minutes, seconds):
        def number(value):
            try:
                return max(0, int(float(value)))
            except (TypeError, ValueError, tk.TclError):
                return 0
        return number(hours.get()) * 3600 + number(minutes.get()) * 60 + number(seconds.get())

    def set_visibility_seconds(self, off_after=0, restore_before_end=0,
                               restore=False):
        for value, h, m, s in (
            (off_after, self.visibility_off_h, self.visibility_off_m, self.visibility_off_s),
            (restore_before_end, self.visibility_restore_h,
             self.visibility_restore_m, self.visibility_restore_s),
        ):
            value = max(0, int(float(value or 0)))
            h.set(value // 3600)
            m.set((value % 3600) // 60)
            s.set(value % 60)
        self.visibility_restore.set(bool(restore))

    def _toggle_two_track_mode(self):
        self._two_track_mode.set(not self._two_track_mode.get())
        self.preview_range_var.set(
            "two" if self._two_track_mode.get() else "one"
        )
        self._two_track_index = 0
        self._on_preview_range_changed()
        self._refresh_canvas_preview()

    def _on_preview_range_changed(self, *_args):
        self._two_track_mode.set(self.preview_range_var.get() == "two")
        self._two_track_index = 0
        if self._two_track_mode.get():
            self._track_nav_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
            self._track_nav_label.pack(side=tk.LEFT)
            self._track_prev_btn.pack(side=tk.RIGHT, padx=2)
            self._track_next_btn.pack(side=tk.RIGHT, padx=2)
        else:
            self._track_nav_frame.pack_forget()
        self._schedule_preview_refresh()

    def _on_preview_quality_changed(self, *_args):
        self._update_preview_resolution_label()
        self._schedule_preview_refresh()

    def _preview_structure_signature(self):
        if not self.app.video_groups:
            return None
        index = (
            self.selected_group
            if 0 <= self.selected_group < len(self.app.video_groups) else 0
        )
        tracks = [
            track for track in self.app.video_groups[index].get('tracks', [])
            if track.get('analysis') and track.get('filepath')
        ]
        start = max(0, min(self._two_track_index, max(0, len(tracks) - 1)))
        count = 2 if self._two_track_mode.get() else 1
        selected = tracks[start:start + count]
        return (
            index, tuple(track.get('filepath') for track in selected),
            self._selected_preview_resolution(),
        )

    def _update_preview_resolution_label(self):
        try:
            width, height = self._selected_preview_resolution()
            text = t(
                "design.actualPreviewResolution", width=width, height=height
            )
        except (TypeError, ValueError, tk.TclError):
            text = t("design.resError")
        if hasattr(self, "preview_resolution_label"):
            self.preview_resolution_label.configure(text=text)

    def _prev_track_pair(self):
        if self._two_track_index > 0:
            self._two_track_index -= 1
            self._refresh_canvas_preview()

    def _next_track_pair(self):
        self._two_track_index += 1
        self._refresh_canvas_preview()

    def _schedule_preview_refresh(self):
        if self._preview_settings_after_id:
            try:
                self.after_cancel(self._preview_settings_after_id)
            except tk.TclError:
                pass
        self._preview_settings_after_id = self.after(180, self._apply_scheduled_preview_refresh)

    def _on_effect_state_changed(self, *_args):
        self.app.set_dirty(True)
        self._schedule_preview_refresh()

    def _manual_preview_refresh(self):
        self._preview_render_video(preserve_state=True)

    def _preview_final_timeline_duration(self, base_duration):
        render_stage = self.app.stages[5] if len(self.app.stages) > 5 else None
        if render_stage is not None and hasattr(render_stage, "_get_repeat_plan"):
            try:
                return render_stage._get_repeat_plan(base_duration).output_seconds
            except (TypeError, ValueError, tk.TclError):
                pass
        repeat = getattr(self.app, "_pending_repeat_state", {}) or {}
        if not repeat.get("enabled"):
            return base_duration
        from repeat_settings import build_repeat_plan
        return build_repeat_plan(
            base_duration,
            enabled=True,
            mode=repeat.get("mode", "count"),
            repeat_count=repeat.get("count", 1),
            target_seconds=repeat.get("target_seconds", 0),
        ).output_seconds

    def _apply_scheduled_preview_refresh(self):
        self._preview_settings_after_id = None
        if self.winfo_exists() and self.winfo_ismapped() and self.app.current_stage == 4:
            self._refresh_canvas_preview()

    def on_hide(self):
        self._preview_generation += 1
        if self._preview_prepare_cancel_event:
            self._preview_prepare_cancel_event.set()
        self._preview_pending_refresh = False
        self._preview_requested_t = None
        self._stop_scrub_play()
        self._cleanup_preview_audio()
        if self._preview_settings_after_id:
            try:
                self.after_cancel(self._preview_settings_after_id)
            except tk.TclError:
                pass
            self._preview_settings_after_id = None

    def destroy(self):
        self._preview_destroyed = True
        self._preview_generation += 1
        if self._preview_prepare_cancel_event:
            self._preview_prepare_cancel_event.set()
        self._preview_requested_t = None
        self._stop_scrub_play()
        self._cleanup_preview_audio()
        for attribute in (
            "_preview_ui_after_id",
            "_preview_loading_after",
            "_preview_settings_after_id",
            "_scrub_after_id",
        ):
            after_id = getattr(self, attribute, None)
            if after_id:
                try:
                    self.after_cancel(after_id)
                except tk.TclError:
                    pass
                setattr(self, attribute, None)
        while not self._preview_ui_queue.empty():
            try:
                self._preview_ui_queue.get_nowait()
            except queue.Empty:
                break
        for window in (
            getattr(self, "_effect_picker", None),
            getattr(self, "_rack_window", None),
            getattr(self, "_ambient_picker", None),
            getattr(self, "_ambient_source_manager", None),
            getattr(self, "_ambient_rescan_window", None),
        ):
            if window and window.winfo_exists():
                window.destroy()
        for card in getattr(self, "effect_cards", {}).values():
            card.destroy()
        cancel_event = getattr(self, "_ambient_rescan_cancel_event", None)
        if cancel_event:
            cancel_event.set()
        player = getattr(self, "_ambient_preview_player", None)
        if player:
            player.stop()
        super().destroy()

    def _post_preview_ui(self, callback, *args, **kwargs):
        if not self._preview_destroyed:
            self._preview_ui_queue.put((callback, args, kwargs))

    def _drain_preview_ui_queue(self):
        if self._preview_destroyed:
            return
        try:
            while True:
                callback, args, kwargs = self._preview_ui_queue.get_nowait()
                if self._preview_destroyed:
                    return
                try:
                    callback(*args, **kwargs)
                except tk.TclError:
                    if not self._preview_destroyed:
                        logger.debug(
                            "Discarded preview UI callback after Tk teardown",
                            exc_info=True,
                        )
        except queue.Empty:
            pass
        try:
            if not self._preview_destroyed and self.winfo_exists():
                self._preview_ui_after_id = self.after(
                    30, self._drain_preview_ui_queue
                )
        except tk.TclError:
            self._preview_ui_after_id = None

    def refresh(self):
        a = self._a
        if 0 <= self.selected_group < len(self.app.video_groups):
            idx = self.selected_group
        else:
            idx = 0
            self.selected_group = 0
        a.populate_group_tabs(self.tabs_container, self.app.video_groups, idx, self._set_group)
        self._update_loudness_summary()
        if not self.bg_image.get():
            for trk in self.app.tracks:
                if trk.filetype == "image" and os.path.isfile(trk.filepath):
                    self.bg_image.set(trk.filepath)
                    for vg in self.app.video_groups:
                        if not vg.get('bg_image'):
                            vg['bg_image'] = trk.filepath
                    break

    def _sync_group_bg(self, save=True):
        if self.selected_group < 0 or self.selected_group >= len(self.app.video_groups):
            return
        g = self.app.video_groups[self.selected_group]
        if save:
            g['bg_image'] = self.bg_image.get()
        else:
            self.bg_image.set(g.get('bg_image', ''))

    def _set_group(self, idx):
        if idx == self.selected_group:
            return
        self._sync_group_bg(save=True)
        self.selected_group = idx
        self._a.populate_group_tabs(self.tabs_container, self.app.video_groups, idx, self._set_group)
        self._sync_group_bg(save=False)
        self._stop_scrub_play()
        self._preview_generation += 1
        self._live_renderer = None
        self._live_duration = 0.0
        self.scrub_var.set(0)
        self.scrub_scale.state(['disabled'])
        self.preview_canvas.delete("all")
        self._last_preview_pil_frame = None
        self._preview_status_label.configure(text=t("design.mixSelected", mix=idx+1))
        self._update_loudness_summary()

    def _update_loudness_summary(self, *_):
        label = getattr(self, "loudness_summary_label", None)
        if label is None:
            return
        tracks = []
        if 0 <= self.selected_group < len(self.app.video_groups):
            tracks = self.app.video_groups[self.selected_group].get(
                "tracks", []
            )
        lines = []
        target = float(self.target_lufs.get())
        max_gain = max(0.0, float(self.max_normalize_gain.get()))
        ceiling = float(self.true_peak_ceiling.get())
        for track in tracks[:5]:
            analysis = track.get("analysis")
            name = track.get("filename") or os.path.basename(
                track.get("filepath", "")
            )
            loudness = getattr(analysis, "integrated_lufs", None)
            peak = getattr(analysis, "true_peak_dbtp", None)
            if loudness is None:
                lines.append(
                    f"{name}: {t('globalAudio.analysisUnavailable')}"
                )
                continue
            requested = target - float(loudness)
            applied = max(-24.0, min(max_gain, requested))
            if peak is not None:
                applied = min(applied, ceiling - float(peak))
            limited = (
                f" · {t('globalAudio.gainLimited')}"
                if abs(applied - requested) > .05 else ""
            )
            lines.append(
                f"{name}: {float(loudness):.1f} LUFS → "
                f"{applied:+.1f} dB{limited}"
            )
        if len(tracks) > 5:
            lines.append(f"… +{len(tracks) - 5}")
        label.configure(
            text="\n".join(lines) if lines
            else t("globalAudio.noTracks")
        )

    def _refresh_ambient_list(self):
        if not hasattr(self, "ambient_list"):
            return
        selected = self.ambient_list.curselection()
        self.ambient_list.delete(0, tk.END)
        for spec in self.ambient_tracks:
            marker = "●" if spec.get("enabled", True) else "○"
            category_id = spec.get("category_id")
            if category_id:
                name = t(f"ambientCategory.{category_id}")
                asset_ids = spec.get("asset_ids", [])
                resolved = sum(
                    bool(self.sound_library.resolve(asset_id))
                    for asset_id in asset_ids
                )
                missing = (
                    f" · {t('globalAudio.fileMissing')}"
                    if resolved < len(asset_ids) else ""
                )
                detail = t("ambientUi.sourceCount", count=resolved)
            else:
                name = os.path.basename(spec.get("filepath", ""))
                missing = (
                    f" · {t('globalAudio.fileMissing')}"
                    if not os.path.isfile(spec.get("filepath", "")) else ""
                )
                detail = t("ambientUi.userSource")
            self.ambient_list.insert(
                tk.END,
                f"{marker}  {name} · {detail}{missing}",
            )
        if selected and selected[0] < len(self.ambient_tracks):
            self.ambient_list.selection_set(selected[0])

    def _add_ambient_track(self):
        paths = filedialog.askopenfilenames(
            title=t("globalAudio.addAmbient"),
            filetypes=[("Audio", "*.wav *.mp3 *.flac *.m4a *.ogg")],
        )
        existing = {item["filepath"] for item in self.ambient_tracks}
        for path in paths:
            if path in existing:
                continue
            self.ambient_tracks.append({
                "element_id": f"user_{uuid.uuid4().hex}",
                "filepath": path, "enabled": True,
                "use_builtin": False, "use_user": True,
                "volume_db": -12.0, "pan": 0.0, "width": 1.0,
                "density": 50, "variation": 20, "start_time": 0.0,
                "end_time": 0.0, "fade_in": 5.0, "fade_out": 5.0,
                "mute": False, "solo": False, "seed": uuid.uuid4().int & 0x7FFFFFFF,
            })
        project = getattr(self.app, "project", None)
        if paths and project and project.project_dir:
            project.backup_files(paths)
        self._refresh_ambient_list()
        if paths:
            self.app.set_dirty(True)
            self._preview_render_video()

    def _remove_ambient_track(self):
        selected = self.ambient_list.curselection()
        if not selected:
            return
        self.ambient_tracks.pop(selected[0])
        self._refresh_ambient_list()
        self.app.set_dirty(True)
        self._preview_render_video()

    def _select_ambient_track(self, _event=None):
        selected = self.ambient_list.curselection()
        if not selected:
            return
        spec = self.ambient_tracks[selected[0]]
        self._ambient_selection_sync = True
        try:
            self.ambient_item_enabled.set(spec.get("enabled", True))
            self.ambient_item_db.set(spec.get("volume_db", -12.0))
            self.ambient_item_pan.set(spec.get("pan", 0.0))
            self.ambient_item_width.set(spec.get("width", 1.0))
            self.ambient_item_density.set(spec.get("density", 50))
            self.ambient_item_variation.set(spec.get("variation", 35))
            self.ambient_item_start.set(spec.get("start_time", 0.0))
            self.ambient_item_end.set(spec.get("end_time", 0.0))
            self.ambient_item_fade_in.set(spec.get("fade_in", 5.0))
            self.ambient_item_fade_out.set(spec.get("fade_out", 5.0))
            self.ambient_item_mute.set(spec.get("mute", False))
            self.ambient_item_solo.set(spec.get("solo", False))
        finally:
            self._ambient_selection_sync = False

    def _toggle_ambient_track(self, _event=None):
        selected = self.ambient_list.curselection()
        if not selected:
            return
        spec = self.ambient_tracks[selected[0]]
        spec["enabled"] = not spec.get("enabled", True)
        self.ambient_item_enabled.set(spec["enabled"])
        self._refresh_ambient_list()
        self.ambient_list.selection_set(selected[0])
        self.app.set_dirty(True)
        self._schedule_preview_refresh()

    def _update_ambient_track(self, *_):
        if (
            not hasattr(self, "ambient_list")
            or self._ambient_selection_sync
        ):
            return
        selected = self.ambient_list.curselection()
        if not selected or selected[0] >= len(self.ambient_tracks):
            return
        spec = self.ambient_tracks[selected[0]]
        spec["enabled"] = bool(self.ambient_item_enabled.get())
        spec["volume_db"] = float(self.ambient_item_db.get())
        spec["pan"] = float(self.ambient_item_pan.get())
        spec["width"] = float(self.ambient_item_width.get())
        spec["density"] = int(self.ambient_item_density.get())
        spec["variation"] = int(self.ambient_item_variation.get())
        spec["start_time"] = float(self.ambient_item_start.get())
        spec["end_time"] = float(self.ambient_item_end.get())
        spec["fade_in"] = float(self.ambient_item_fade_in.get())
        spec["fade_out"] = float(self.ambient_item_fade_out.get())
        spec["mute"] = bool(self.ambient_item_mute.get())
        spec["solo"] = bool(self.ambient_item_solo.get())
        self.app.set_dirty(True)
        self._refresh_ambient_list()
        self.ambient_list.selection_set(selected[0])
        self._schedule_preview_refresh()

    def _set_all_effect_cards(self, expanded):
        for effect_id in self.active_effect_ids:
            card = self.effect_cards.get(effect_id)
            if card and card.expanded != expanded:
                card.toggle()

    def _update_ambience_source(self, source_id):
        if self._ambience_state_sync:
            return
        variables = self._ambience_source_vars.get(source_id)
        if not variables:
            return
        enabled_var, volume_var = variables
        self.ambience_sources[source_id] = {
            "enabled": bool(enabled_var.get()),
            "volume_db": float(volume_var.get()),
        }
        self.app.set_dirty(True)
        self._schedule_preview_refresh()

    def _open_effect_rack(self):
        self._refresh_effect_rack()
        if self._effect_add_button.winfo_exists():
            self._effect_add_button.focus_set()

    def _open_effect_picker_if_hovered(self):
        button = getattr(self, "_effect_add_button", None)
        if button and button.winfo_exists():
            x, y = button.winfo_pointerxy()
            target = button.winfo_containing(x, y)
            if target is button:
                self._open_effect_picker()

    def _effect_warning(self, effect_id):
        path = {
            "background": self.bg_image.get(),
            "album": self.album_image_var.get(),
            "logo": self.logo_image_var.get(),
        }.get(effect_id)
        if path and not os.path.isfile(path):
            return t("effects.missingFile")
        return ""

    def _same_stage_siblings(self, effect_id):
        stage = EFFECT_COMPOSITION_STAGES[effect_id][0]
        return [
            item for item in self.active_effect_ids
            if EFFECT_COMPOSITION_STAGES[item][0] == stage
        ]

    def _can_move_effect(self, effect_id, delta):
        siblings = self._same_stage_siblings(effect_id)
        if effect_id not in siblings:
            return False
        index = siblings.index(effect_id)
        return 0 <= index + delta < len(siblings)

    def _set_effect_enabled(self, effect_id, enabled):
        self.effect_enabled_states[effect_id] = bool(enabled)
        self.app.set_dirty(True)
        self._sync_effect_empty_state()
        self.after_idle(self._refresh_effect_rack)
        self._schedule_preview_refresh()

    def _open_ambient_library_picker(self):
        if self._ambient_picker and self._ambient_picker.winfo_exists():
            self._ambient_picker.lift()
            self._ambient_picker.focus_force()
            return
        a, T = self._a, self._a.THEME
        popup = tk.Toplevel(self)
        self._ambient_picker = popup
        popup.title(t("ambientUi.ambientLibrary"))
        popup.geometry("540x640")
        popup.minsize(420, 360)
        popup.configure(bg=T["bg_card"])
        popup.transient(self.winfo_toplevel())
        query = tk.StringVar()
        a.styled_label(
            popup, t("globalAudio.addAmbient"), size=15, bold=True,
            bg=T["bg_card"],
        ).pack(fill=tk.X, padx=14, pady=(14, 5))
        search = a.styled_entry(popup, textvariable=query)
        search.pack(fill=tk.X, padx=14, pady=(0, 8))
        canvas = tk.Canvas(popup, bg=T["bg_card"], highlightthickness=0)
        scrollbar = tk.Scrollbar(
            popup, orient=tk.VERTICAL, command=canvas.yview
        )
        body = tk.Frame(canvas, bg=T["bg_card"])
        body_id = canvas.create_window((0, 0), window=body, anchor=tk.NW)
        body.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(body_id, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10))
        counts = self.sound_library.category_counts()
        rows = []
        for group_id, categories in CATEGORY_GROUPS.items():
            group_label = a.styled_label(
                body, t(f"ambientGroup.{group_id}"), size=11, bold=True,
                bg=T["bg_card"],
            )
            group_label.pack(fill=tk.X, padx=6, pady=(10, 3), anchor=tk.W)
            for category_id in categories:
                category_counts = counts.get(category_id, {})
                total = sum(category_counts.values())
                if not total:
                    continue
                row = tk.Frame(
                    body, bg=T["bg_mid"], highlightthickness=1,
                    highlightbackground=T["border"],
                )
                row.pack(fill=tk.X, padx=6, pady=3)
                label = t(f"ambientCategory.{category_id}")
                detail = t(
                    "ambientUi.categorySources",
                    continuous=category_counts.get("continuous", 0),
                    events=category_counts.get("event", 0),
                    hybrid=category_counts.get("hybrid", 0),
                )
                labels = tk.Frame(row, bg=T["bg_mid"])
                labels.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=9, pady=6)
                a.styled_label(
                    labels, label, size=10, bold=True, bg=T["bg_mid"],
                ).pack(anchor=tk.W)
                a.styled_label(
                    labels, detail, size=8, color=T["fg_dim"],
                    bg=T["bg_mid"],
                ).pack(anchor=tk.W)
                a.styled_button(
                    row, t("common.add"),
                    lambda cid=category_id: self._add_ambient_category(cid),
                    "success", padx=7,
                ).pack(side=tk.RIGHT, padx=8, pady=7)
                rows.append((f"{label} {category_id}".casefold(), row))

        def filter_rows(*_):
            needle = query.get().strip().casefold()
            for label, row in rows:
                if not needle or needle in label:
                    if not row.winfo_manager():
                        row.pack(fill=tk.X, padx=6, pady=3)
                else:
                    row.pack_forget()

        query.trace_add("write", filter_rows)
        search.bind("<Escape>", lambda _event: popup.destroy())
        search.focus_set()

    def _add_ambient_category(self, category_id):
        preset = self.sound_library.presets.get(category_id, {})
        assets = self.sound_library.available(category_id)
        if not assets:
            return
        self.ambient_tracks.append({
            "element_id": f"builtin_{category_id}_{uuid.uuid4().hex}",
            "category_id": category_id,
            "asset_ids": [asset["asset_id"] for asset in assets],
            "user_sources": [],
            "use_builtin": True, "use_user": False,
            "enabled": True, "mute": False, "solo": False,
            "volume_db": float(preset.get("default_gain_db", -20.0)),
            "pan": 0.0, "width": 1.0,
            "density": int(preset.get("default_density", 50)),
            "variation": int(preset.get("default_variation", 35)),
            "crossfade": float(
                preset.get("default_crossfade_seconds", 5.0)
            ),
            "event_min_interval": float(
                preset.get("default_event_min_interval", 8.0)
            ),
            "event_max_interval": float(
                preset.get("default_event_max_interval", 40.0)
            ),
            "start_time": 0.0, "end_time": 0.0,
            "fade_in": 5.0, "fade_out": 5.0,
            "seed": uuid.uuid4().int & 0x7FFFFFFF,
        })
        self._refresh_ambient_list()
        self.ambient_list.selection_clear(0, tk.END)
        self.ambient_list.selection_set(len(self.ambient_tracks) - 1)
        self._select_ambient_track()
        self.app.set_dirty(True)
        if self._ambient_picker and self._ambient_picker.winfo_exists():
            self._ambient_picker.destroy()
        self._schedule_preview_refresh()

    def _selected_ambient_spec(self):
        selected = self.ambient_list.curselection()
        if not selected or selected[0] >= len(self.ambient_tracks):
            return None
        return self.ambient_tracks[selected[0]]

    def _preview_ambient_path(self, path, duration=8.0):
        if not path or not os.path.isfile(path):
            messagebox.showwarning(
                t("common.warning"), t("globalAudio.fileMissing"),
                parent=self,
            )
            return
        self._ambient_preview_player.stop()
        self._ambient_preview_player.play(
            path, start=0.0, duration=duration,
            on_error=lambda error: self._post_preview_ui(
                messagebox.showerror, t("common.error"), str(error),
                parent=self,
            ),
        )

    def _preview_selected_ambient(self):
        spec = self._selected_ambient_spec()
        if not spec:
            return
        if spec.get("category_id"):
            asset_ids = spec.get("asset_ids", [])
            path = next(
                (
                    self.sound_library.resolve(asset_id)
                    for asset_id in asset_ids
                    if self.sound_library.resolve(asset_id)
                ),
                None,
            )
        else:
            path = spec.get("filepath")
        self._preview_ambient_path(path)

    def _open_ambient_source_manager(self):
        spec = self._selected_ambient_spec()
        if not spec or not spec.get("category_id"):
            return
        if (
            self._ambient_source_manager
            and self._ambient_source_manager.winfo_exists()
        ):
            self._ambient_source_manager.destroy()
        a, T = self._a, self._a.THEME
        popup = tk.Toplevel(self)
        self._ambient_source_manager = popup
        popup.title(t("ambientUi.sourceManager"))
        popup.geometry("620x620")
        popup.configure(bg=T["bg_card"])
        popup.transient(self.winfo_toplevel())
        a.styled_label(
            popup, t("ambientUi.sourceManager"), size=14, bold=True,
            bg=T["bg_card"],
        ).pack(fill=tk.X, padx=12, pady=12)
        canvas = tk.Canvas(popup, bg=T["bg_card"], highlightthickness=0)
        scrollbar = tk.Scrollbar(
            popup, orient=tk.VERTICAL, command=canvas.yview
        )
        body = tk.Frame(canvas, bg=T["bg_card"])
        body_id = canvas.create_window((0, 0), window=body, anchor=tk.NW)
        body.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(body_id, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8))
        selected_ids = set(spec.get("asset_ids", []))

        def set_asset(asset_id, variable):
            values = set(spec.get("asset_ids", []))
            if variable.get():
                values.add(asset_id)
            else:
                values.discard(asset_id)
            spec["asset_ids"] = [
                asset["asset_id"]
                for asset in self.sound_library.available(spec["category_id"])
                if asset["asset_id"] in values
            ]
            self.app.set_dirty(True)
            self._refresh_ambient_list()
            self._schedule_preview_refresh()

        for asset in self.sound_library.available(spec["category_id"]):
            row = tk.Frame(body, bg=T["bg_mid"])
            row.pack(fill=tk.X, padx=5, pady=3)
            enabled = tk.BooleanVar(
                row, value=asset["asset_id"] in selected_ids
            )
            a.styled_checkbutton(
                row, "", enabled, bg=T["bg_mid"],
            ).pack(side=tk.LEFT, padx=5)
            enabled.trace_add(
                "write",
                lambda *_args, aid=asset["asset_id"], var=enabled:
                set_asset(aid, var),
            )
            info = (
                f"{asset['asset_id']} · {asset['duration_seconds']:.1f}s · "
                f"{asset.get('license_status', 'unknown')}"
            )
            a.styled_label(
                row, info, size=9, bg=T["bg_mid"],
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, pady=7)
            a.styled_button(
                row, t("ambientUi.previewSource"),
                lambda aid=asset["asset_id"]:
                self._preview_ambient_path(self.sound_library.resolve(aid)),
                padx=5,
            ).pack(side=tk.RIGHT, padx=6)

    def _rescan_ambient_library(self):
        incoming = [
            path for path in self.sound_library.root.iterdir()
            if path.is_file() and path.suffix.casefold() in (
                ".zip", ".7z", ".rar", ".wav", ".flac", ".ogg",
                ".mp3", ".m4a", ".aac",
            )
        ]
        if not incoming:
            self.sound_library.reload()
            messagebox.showinfo(
                t("ambientUi.ambientLibrary"),
                t("ambientUi.libraryCurrent"), parent=self,
            )
            return
        if (
            self._ambient_rescan_window
            and self._ambient_rescan_window.winfo_exists()
        ):
            self._ambient_rescan_window.lift()
            return
        a, T = self._a, self._a.THEME
        window = tk.Toplevel(self)
        self._ambient_rescan_window = window
        window.title(t("ambientUi.organizingLibrary"))
        window.geometry("520x230")
        window.resizable(False, False)
        window.configure(bg=T["bg_card"])
        window.transient(self.winfo_toplevel())
        window.protocol("WM_DELETE_WINDOW", lambda: None)
        a.styled_label(
            window, t("ambientUi.organizingLibrary"), size=13, bold=True,
            bg=T["bg_card"],
        ).pack(fill=tk.X, padx=16, pady=(16, 8))
        status = a.styled_label(
            window, "", size=9, color=T["fg_dim"], bg=T["bg_card"],
        )
        status.pack(fill=tk.X, padx=16, pady=4)
        progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(
            window, variable=progress_var, maximum=100,
        ).pack(fill=tk.X, padx=16, pady=8)
        cancel_event = threading.Event()
        self._ambient_rescan_cancel_event = cancel_event
        cancel_button = a.styled_button(
            window, t("common.cancel"), cancel_event.set,
            "danger", padx=8,
        )
        cancel_button.pack(pady=8)
        while not self._ambient_rescan_queue.empty():
            self._ambient_rescan_queue.get_nowait()

        def progress(stage, current, done, total):
            self._ambient_rescan_queue.put(
                ("progress", stage, current, done, total)
            )

        def worker():
            try:
                ffmpeg = ensure_ffmpeg_available()
                ffprobe = os.path.join(
                    os.path.dirname(ffmpeg),
                    "ffprobe.exe" if sys.platform == "win32" else "ffprobe",
                )
                result = rescan_sound_library(
                    self.sound_library.root, ffprobe, ffmpeg,
                    progress=progress, cancel_event=cancel_event,
                )
                self._ambient_rescan_queue.put(("done", result))
            except InterruptedError:
                self._ambient_rescan_queue.put(("cancelled",))
            except Exception as error:
                self._ambient_rescan_queue.put(("error", error))

        threading.Thread(
            target=worker, daemon=True, name="ambient-library-rescan"
        ).start()

        stage_labels = {
            "extract": "ambientUi.extractingArchives",
            "probe": "ambientUi.checkingAudio",
            "classify": "ambientUi.classifyingAudio",
        }

        def poll():
            terminal = None
            while True:
                try:
                    item = self._ambient_rescan_queue.get_nowait()
                except queue.Empty:
                    break
                if item[0] == "progress":
                    _, stage, current, done, total = item
                    status.configure(
                        text=f"{t(stage_labels.get(stage, 'ambientUi.registeringLibrary'))}\n{current}"
                    )
                    progress_var.set(
                        100 * done / max(1, total)
                    )
                else:
                    terminal = item
            if terminal is None:
                if window.winfo_exists():
                    window.after(60, poll)
                return
            cancel_button.configure(state=tk.DISABLED)
            if terminal[0] == "done":
                self._ambient_rescan_cancel_event = None
                self.sound_library.reload()
                self._refresh_ambient_list()
                status.configure(text=t("ambientUi.libraryOrganized"))
                progress_var.set(100)
                window.after(700, window.destroy)
            elif terminal[0] == "cancelled":
                self._ambient_rescan_cancel_event = None
                status.configure(text=t("common.cancel"))
                window.after(900, window.destroy)
            else:
                self._ambient_rescan_cancel_event = None
                status.configure(
                    text=t("ambientUi.processingFailed")
                    + f": {terminal[1]}"
                )
                window.protocol("WM_DELETE_WINDOW", window.destroy)
                cancel_button.configure(
                    state=tk.NORMAL, text=t("common.close"),
                    command=window.destroy,
                )

        window.after(60, poll)

    def _refresh_effect_rack(self):
        self._sync_effect_empty_state()
        slots = self._rack_slots_frame
        if not slots or not slots.winfo_exists():
            return
        for child in slots.winfo_children():
            child.destroy()
        a, T = self._a, self._a.THEME
        user_effects = [
            effect_id for effect_id in self.active_effect_ids
            if effect_id not in DEFAULT_EFFECT_IDS
        ]
        default_effects = [
            effect_id for effect_id in DEFAULT_EFFECT_IDS
            if effect_id in EFFECT_DEFINITIONS
        ]
        if not user_effects:
            a.styled_label(
                slots, t("effects.empty"), size=10,
                color=T["fg_dim"], bg=T["bg_card"],
            ).pack(fill=tk.X, padx=12, pady=8)
        ordered = user_effects + default_effects
        default_section_started = False
        for effect_id in ordered:
            is_default = effect_id in DEFAULT_EFFECT_IDS
            if is_default and not default_section_started:
                default_section_started = True
                tk.Frame(slots, bg=T["separator"], height=1).pack(
                    fill=tk.X, padx=5, pady=(6, 4)
                )
                a.styled_label(
                    slots, t("effects.defaultEffects"), size=8,
                    color=T["fg_dim"], bg=T["bg_card"],
                ).pack(fill=tk.X, padx=7, anchor=tk.W)
            row = tk.Frame(
                slots, bg=T["bg_mid"], highlightthickness=1,
                highlightbackground=T["border"],
            )
            row.pack(fill=tk.X, padx=5, pady=4)
            enabled = tk.BooleanVar(row, value=self.effect_enabled_states.get(
                effect_id, True
            ))
            enabled_control = a.styled_checkbutton(
                row, "", enabled, bg=T["bg_mid"],
            )
            enabled_control.pack(side=tk.LEFT, padx=(7, 2), pady=8)
            if is_default:
                enabled_control.configure(state=tk.DISABLED)
            else:
                enabled.trace_add(
                    "write",
                    lambda *_args, eid=effect_id, var=enabled:
                    self._set_effect_enabled(eid, var.get()),
                )
            _, label_key = EFFECT_DEFINITIONS[effect_id]
            stage_key = EFFECT_COMPOSITION_STAGES[effect_id][1]
            label_frame = tk.Frame(row, bg=T["bg_mid"])
            label_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=6)
            a.styled_label(
                label_frame, t(label_key), size=10, bold=True,
                bg=T["bg_mid"],
            ).pack(anchor=tk.W)
            warning = self._effect_warning(effect_id)
            a.styled_label(
                label_frame,
                warning or t(stage_key),
                size=8,
                color=T.get("danger", "#ff6b6b") if warning else T["fg_dim"],
                bg=T["bg_mid"],
            ).pack(anchor=tk.W)
            a.styled_button(
                row, t("effects.settings"),
                lambda eid=effect_id: self._open_effect_settings(eid),
                padx=5,
            ).pack(side=tk.RIGHT, padx=(2, 6), pady=7)
            if not is_default:
                a.styled_button(
                    row, t("effects.remove"),
                    lambda eid=effect_id: self._remove_effect(eid),
                    "danger", padx=4,
                ).pack(side=tk.RIGHT, padx=2, pady=7)
                down = a.styled_button(
                    row, "↓", lambda eid=effect_id: self._move_effect(eid, 1),
                    padx=4,
                )
                down.pack(side=tk.RIGHT, padx=1, pady=7)
                up = a.styled_button(
                    row, "↑", lambda eid=effect_id: self._move_effect(eid, -1),
                    padx=4,
                )
                up.pack(side=tk.RIGHT, padx=1, pady=7)
                if not self._can_move_effect(effect_id, 1):
                    a.set_button_state(down, tk.DISABLED)
                if not self._can_move_effect(effect_id, -1):
                    a.set_button_state(up, tk.DISABLED)

    def _open_effect_settings(self, effect_id):
        card = self.effect_cards.get(effect_id)
        if card:
            card.open()
            return
        if effect_id == "global_audio":
            section = getattr(self, "_global_audio_section", None)
            if section and not section.expanded:
                section.toggle()
        target = {
            "global_audio": getattr(self, "_global_audio_card", None),
            "scene_transition": getattr(
                self, "_scene_transition_card", None
            ),
        }.get(effect_id)
        canvas = getattr(self, "_settings_canvas", None)
        if target and canvas:
            canvas.update_idletasks()
            bounds = canvas.bbox("all")
            if bounds:
                canvas.yview_moveto(
                    max(0.0, target.winfo_y() / max(1, bounds[3]))
                )

    def _restore_effect_card_state(self):
        valid_ids = [
            effect_id for effect_id in self.active_effect_ids
            if effect_id in self.effect_cards
        ]
        self.active_effect_ids = valid_ids
        self.effect_enabled_states = {
            effect_id: bool(self.effect_enabled_states.get(effect_id, True))
            for effect_id in valid_ids
        }
        self._ambience_state_sync = True
        try:
            for source_id, variables in self._ambience_source_vars.items():
                state = self.ambience_sources.get(source_id, {})
                enabled_var, volume_var = variables
                enabled_var.set(bool(state.get("enabled", False)))
                volume_var.set(float(state.get(
                    "volume_db", CATEGORY_PRESETS[source_id][0]
                )))
        finally:
            self._ambience_state_sync = False
        for effect_id, card in self.effect_cards.items():
            if effect_id in valid_ids:
                card.show()
                saved = self.effect_card_states.get(effect_id, True)
                desired = (
                    saved.get("expanded", True)
                    if isinstance(saved, dict) else bool(saved)
                )
                if card.expanded != desired:
                    card.toggle()
                if isinstance(saved, dict):
                    for section, section_open in zip(
                        card.sections, saved.get("sections", []),
                        strict=False,
                    ):
                        if section.expanded != section_open:
                            section.toggle()
            else:
                card.hide()
        self._sync_effect_empty_state()
        self._refresh_effect_rack()
        self._refresh_ambient_list()

    def _sync_effect_empty_state(self):
        enabled_count = sum(
            self.effect_enabled_states.get(effect_id, True)
            for effect_id in self.active_effect_ids
        )
        if hasattr(self, "effect_summary_label"):
            warnings = sum(
                bool(self._effect_warning(effect_id))
                for effect_id in self.active_effect_ids
            )
            self.effect_summary_label.configure(
                text=t(
                    "effects.summary", active=enabled_count,
                    total=len(self.active_effect_ids), warnings=warnings,
                )
            )
        if self.active_effect_ids:
            self._effects_empty.pack_forget()
        elif not self._effects_empty.winfo_manager():
            self._effects_empty.pack(fill=tk.X, padx=12, pady=8)

    def _add_effect(self, effect_id):
        if effect_id in self.active_effect_ids:
            card = self.effect_cards.get(effect_id)
            if card:
                card.open()
            return False
        card = self.effect_cards.get(effect_id)
        if not card:
            return False
        if effect_id == "ambience_mixer" and not self.ambience_sources:
            self.ambience_sources = {
                source_id: {
                    "enabled": False,
                    "volume_db": float(CATEGORY_PRESETS[source_id][0]),
                }
                for source_id in self._ambience_source_vars
            }
            self._ambience_state_sync = True
            for source_id, variables in self._ambience_source_vars.items():
                enabled_var, volume_var = variables
                enabled_var.set(False)
                volume_var.set(float(CATEGORY_PRESETS[source_id][0]))
            self._ambience_state_sync = False
        self.active_effect_ids.append(effect_id)
        self.effect_enabled_states[effect_id] = True
        card.show()
        self._sync_effect_empty_state()
        self._refresh_effect_rack()
        self._schedule_preview_refresh()
        self.app.set_dirty(True)
        return True

    def _reset_effect_values(self, values):
        for variable_name, default in values.items():
            variable = getattr(self, variable_name, None)
            if isinstance(variable, tk.Variable):
                variable.set(default)
        self.app.set_dirty(True)
        self._schedule_preview_refresh()

    def _reset_effect(self, effect_id):
        groups = EFFECT_DEFAULT_GROUPS.get(effect_id, [])
        self._reset_effect_values({
            name: default
            for group in groups
            for name, default in group.items()
        })

    def _reset_effect_section(self, effect_id, section_index):
        groups = EFFECT_DEFAULT_GROUPS.get(effect_id, [])
        if 0 <= section_index < len(groups):
            self._reset_effect_values(groups[section_index])

    def _remove_effect(self, effect_id):
        if effect_id in DEFAULT_EFFECT_IDS:
            return
        if effect_id not in self.active_effect_ids:
            return
        self.active_effect_ids.remove(effect_id)
        self.effect_enabled_states.pop(effect_id, None)
        if effect_id == "ambience_mixer":
            self.ambience_sources.clear()
            self._legacy_ambient_tracks.clear()
        self.effect_cards[effect_id].hide()
        self._sync_effect_empty_state()
        self._refresh_effect_rack()
        self._schedule_preview_refresh()
        self.app.set_dirty(True)

    def _move_effect(self, effect_id, delta):
        if effect_id not in self.active_effect_ids:
            return
        siblings = self._same_stage_siblings(effect_id)
        sibling_index = siblings.index(effect_id)
        target_sibling_index = sibling_index + delta
        if not 0 <= target_sibling_index < len(siblings):
            return
        other_id = siblings[target_sibling_index]
        index = self.active_effect_ids.index(effect_id)
        target = self.active_effect_ids.index(other_id)
        self.active_effect_ids[index], self.active_effect_ids[target] = (
            self.active_effect_ids[target], self.active_effect_ids[index]
        )
        self.app.set_dirty(True)
        self._refresh_effect_rack()
        self._schedule_preview_refresh()

    def _open_effect_picker(self, show=True):
        T = self._a.THEME
        category_keys = {
            "basic": "effects.categoryBasic",
            "text": "effects.categoryText",
            "audio": "effects.categoryAudio",
            "audio_effect": "effects.categoryAudioEffects",
            "motion": "effects.categoryMotion",
            "color": "effects.categoryColor",
            "other": "effects.categoryOther",
        }
        menu = tk.Menu(
            self, tearoff=False, bg=T["bg_input"], fg=T["fg"],
            activebackground=T["accent"], activeforeground="#ffffff",
        )
        self._effect_picker = menu
        category_menus = {}
        self._effect_category_menus = category_menus

        def choose_effect(effect_id):
            self._add_effect(effect_id)
            try:
                menu.unpost()
                menu.destroy()
            except tk.TclError:
                pass
            self._effect_picker = None

        for category, category_key in category_keys.items():
            effect_ids = [
                effect_id for effect_id, (item_category, _label_key)
                in EFFECT_DEFINITIONS.items()
                if item_category == category
                and effect_id not in DEFAULT_EFFECT_IDS
            ]
            if not effect_ids:
                continue
            submenu = tk.Menu(
                menu, tearoff=False, bg=T["bg_input"], fg=T["fg"],
                activebackground=T["accent"], activeforeground="#ffffff",
                relief=tk.FLAT, borderwidth=1,
            )
            category_menus[category] = submenu
            for effect_id in effect_ids:
                label_key = EFFECT_DEFINITIONS[effect_id][1]
                label = t(label_key)
                if effect_id in self.active_effect_ids:
                    label = f"{label} · {t('effects.alreadyAdded')}"
                submenu.add_command(
                    label=label,
                    command=lambda eid=effect_id: choose_effect(eid),
                )
            menu.add_cascade(label=f"{t(category_key)}  ▶", menu=submenu)
        button = self._effect_add_button
        if not show:
            return
        try:
            menu.tk_popup(
                button.winfo_rootx(),
                button.winfo_rooty() + button.winfo_height(),
            )
        finally:
            menu.grab_release()

    def _pick_bg(self):
        p = filedialog.askopenfilename(filetypes=[(t("design.image"), " ".join(f"*{e}" for e in IMAGE_EXTS))])
        if p: self.bg_image.set(p)

    def _pick_overlay(self, variable):
        path = filedialog.askopenfilename(filetypes=[(t("design.image"), " ".join(f"*{e}" for e in IMAGE_EXTS))])
        if path: variable.set(path)

    def _collect_config(self):
        def number(variable, default, cast=float):
            try:
                return cast(variable.get())
            except (TypeError, ValueError, tk.TclError):
                return default

        config = {
            "layout": {
                "version": 2,
                "reference_width": 1920,
                "reference_height": 1080,
            },
            "background": {
                "image": self.bg_image.get() or None, "opacity": 1.0,
                "blur": 0, "darken": 0.0,
                "fit": choice_id(self.bg_fit_var.get(), FIT_CHOICES, "cover"),
            },
            "overlays": {
                "album": {
                    "image": self.album_image_var.get() or None,
                    "x": int(self.album_x_var.get()),
                    "y": int(self.album_y_var.get()),
                    "width": int(self.album_width_var.get()),
                    "opacity": self.album_opacity_var.get(),
                },
                "logo": {
                    "image": self.logo_image_var.get() or None,
                    "x": int(self.logo_x_var.get()),
                    "y": int(self.logo_y_var.get()),
                    "width": int(self.logo_width_var.get()),
                    "opacity": self.logo_opacity_var.get(),
                },
            },
            "visualizer": {
                           "type": choice_id(self.viz_type.get(), VISUALIZER_CHOICES, "eq_bars"),
                           "position": choice_id(self.viz_pos.get(), POSITION_CHOICES, "bottom"),
                           "color": self.viz_color.get(),
                           "opacity": self.viz_opacity.get(), "bar_count": int(self.viz_bars.get()),
                           "height": int(self.viz_height.get()),
                           "smoothing": self.viz_smooth.get(),
                           "mirror": self.viz_mirror.get(), "invert": self.viz_invert.get(),
                           "gradient": self.viz_gradient.get(),
                           "bar_width": int(self.viz_bar_width.get()),
                           "bar_gap": int(self.viz_bar_gap.get()),
                           "min_height": int(self.viz_min_height.get()),
                           "sensitivity": self.viz_sensitivity.get(),
                           "corner_radius": int(self.viz_corner_radius.get()),
                           "decay": self.viz_decay.get(),
                           "glow": int(self.viz_glow.get()),
                           "line_width": int(self.viz_line_width.get()),
                           "x": int(self.viz_x_var.get()), "y": int(self.viz_y_var.get()),
                           "width": int(self.viz_w_var.get()), "height_override": 0},
            "text": {"show_title": self.show_title.get(), "show_bpm": self.show_bpm.get(),
                     "show_key": self.show_key.get(), "show_camelot": self.show_camelot.get(),
                     "show_time": self.show_time.get(), "position": "center",
                     "font_size": int(self.text_font_size_var.get()),
                     "sub_font_size": int(self.text_sub_font_size_var.get()),
                     "color": self.text_color_var.get(),
                     "align": choice_id(self.text_align_var.get(), ALIGN_CHOICES, "center"),
                     "x": self.text_x_var.get(), "y": self.text_y_var.get(),
                     "bold": self.text_bold_var.get(), "italic": self.text_italic_var.get(),
                     "underline": self.text_underline_var.get(),
                     "strip_extension": self.text_strip_ext_var.get(),
                     "shadow": True, "shadow_color": "#000000", "shadow_offset": 3,
                     "text_font_family": self.text_font_family_var.get(),
                     "custom_text": self.custom_text_var.get(),
                     "custom_x": self.custom_x_var.get(), "custom_y": self.custom_y_var.get(),
                     "custom_font_size": int(self.custom_font_size_var.get()),
                     "custom_bold": self.custom_bold_var.get(),
                     "custom_italic": self.custom_italic_var.get(),
                     "custom_underline": self.custom_underline_var.get(),
                     "custom_color": self.custom_color_var.get(),
                     "custom_font_family": self.custom_font_family_var.get(),
                     "custom_affects_by_effects": self.custom_affects_fx_var.get(),
                     "custom_opacity": number(self.custom_opacity_var, 1.0),
                     "custom_outline_width": number(self.custom_outline_width_var, 0, int),
                     "custom_outline_color": self.custom_outline_color_var.get(),
                     "custom_background": self.custom_background_var.get(),
                     "custom_background_color": self.custom_background_color_var.get(),
                     "custom_background_opacity": number(self.custom_background_opacity_var, 0.5),
                     "custom_background_padding": number(self.custom_background_padding_var, 12, int),
                     "custom_start_seconds": max(0.0, number(self.custom_start_seconds_var, 0.0)),
                     "custom_end_seconds": max(0.0, number(self.custom_end_seconds_var, 0.0)),
                     "custom_target_track": max(0, number(self.custom_target_track_var, 0, int))},
            "progress_bar": {"show": self.show_progress.get(), "position": "bottom", "height": 4,
                             "color": "#ffffff", "background_color": "#333333", "margin": 30},
            "fade": {"fade_in_duration": self.fade_in.get(), "fade_out_duration": self.fade_out.get()},
            "effects": {"bounce": self.fx_bounce.get(), "bounce_intensity": self.fx_bounce_i.get(),
                        "shake": self.fx_shake.get(), "shake_intensity": self.fx_shake_i.get(),
                        "zoom": self.fx_zoom.get(), "zoom_intensity": self.fx_zoom_i.get(),
                        "flash": self.fx_flash.get(), "flash_intensity": self.fx_flash_i.get(),
                        "crt": self.fx_crt.get(), "crt_intensity": self.fx_crt_intensity.get(),
                        "crt_scanlines": self.fx_crt_scanlines.get(),
                        "crt_curvature": self.fx_crt_curvature.get(),
                        "crt_chromatic": self.fx_crt_chromatic.get(),
                        "crt_vignette": self.fx_crt_vignette.get(),
                        "crt_noise": self.fx_crt_noise.get(),
                        "crt_flicker": self.fx_crt_flicker.get()},
            "visibility": {
                "enabled": self.visibility_enabled.get(),
                "turn_off_after": self._hms_seconds(
                    self.visibility_off_h, self.visibility_off_m,
                    self.visibility_off_s,
                ),
                "restore_before_end": self._hms_seconds(
                    self.visibility_restore_h, self.visibility_restore_m,
                    self.visibility_restore_s,
                ),
                "restore": self.visibility_restore.get(),
                "black_color": "#000000",
            },
            "global_audio": {
                "music_master_db": float(self.music_master_db.get()),
                "normalize_tracks": bool(self.normalize_tracks.get()),
                "target_lufs": float(self.target_lufs.get()),
                "true_peak_dbtp": float(self.true_peak_ceiling.get()),
                "max_auto_gain_db": float(self.max_normalize_gain.get()),
            },
            "scene_transition": {
                "crossfade_duration": float(self.crossfade_duration.get()),
            },
            "ambience_mixer": {
                "effect_id": "ambience_mixer",
                "instance_id": "ambience_mixer_001",
                "enabled": (
                    "ambience_mixer" in self.active_effect_ids
                    and self.effect_enabled_states.get(
                        "ambience_mixer", True
                    )
                ),
                "sources": copy.deepcopy(self.ambience_sources),
                "legacy_sources": copy.deepcopy(
                    self._legacy_ambient_tracks
                ),
                "random_seed": int(self.ambience_random_seed.get()),
            },
        }
        active = {
            effect_id for effect_id in self.active_effect_ids
            if self.effect_enabled_states.get(effect_id, True)
        }
        config["active_effects"] = [
            effect_id for effect_id in self.active_effect_ids
            if effect_id in active
        ]
        config["effect_order"] = list(self.active_effect_ids)
        config["effect_instances"] = [
            {
                "id": effect_id,
                "instance_id": (
                    "ambience_mixer_001"
                    if effect_id == "ambience_mixer" else effect_id
                ),
                "enabled": effect_id in active,
            }
            for effect_id in self.active_effect_ids
        ]
        if "background" not in active:
            config["background"]["image"] = None
        if "album" not in active:
            config["overlays"]["album"]["image"] = None
        if "logo" not in active:
            config["overlays"]["logo"]["image"] = None
        if "visualizer" not in active:
            config["visualizer"]["type"] = "none"
        if "track_info" not in active:
            for key in (
                "show_title", "show_bpm", "show_key",
                "show_camelot", "show_time",
            ):
                config["text"][key] = False
            config["progress_bar"]["show"] = False
        if "custom_text" not in active:
            config["text"]["custom_text"] = ""
        if "fade" not in active:
            config["fade"] = {
                "fade_in_duration": 0, "fade_out_duration": 0
            }
        if "beat" not in active:
            for key in ("bounce", "shake", "zoom", "flash"):
                config["effects"][key] = False
        if "crt" not in active:
            config["effects"]["crt"] = False
        if "visibility" not in active:
            config["visibility"]["enabled"] = False
        return config

    def _hex_to_rgb(self, h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _make_preview_bg(self, w, h, key='C', mode='major'):
        key_colors = {
            'C': (60, 60, 90), 'D': (50, 70, 80), 'E': (70, 50, 80),
            'F': (50, 80, 60), 'G': (80, 60, 50), 'A': (80, 50, 70),
            'B': (60, 70, 70),
        }
        base = key_colors.get(key, (50, 50, 70))
        if mode == 'minor':
            base = tuple(max(0, c - 15) for c in base)
        bg = Image.new('RGB', (w, h), base)
        draw = ImageDraw.Draw(bg)
        for y in range(h):
            alpha = int(60 * (y / h))
            draw.line([(0, y), (w, y)], fill=tuple(min(255, c + alpha) for c in base))
        return bg, draw

    def _refresh_canvas_preview(self):
        config = self._collect_config()
        if not self.app.video_groups:
            fw, fh = 640, 360
            try:
                fw, fh = self._selected_resolution()
            except (TypeError, ValueError, tk.TclError):
                pass
            bg, draw = self._make_preview_bg(fw, fh)
            draw.text((20, 20), t("design.runDistributionFirst"), fill=(220, 220, 220))
            self._show_pil_frame_fit(bg)
            self._preview_status_label.configure(text=t("design.noDistributionResult"))
            return
        idx = self.selected_group if 0 <= self.selected_group < len(self.app.video_groups) else 0
        group = self.app.video_groups[idx]
        config['clips'] = group.get('clips', [])
        config['clip_enabled'] = group.get('clip_enabled', False)
        config['clip_interval'] = group.get('clip_interval', 1.0)
        config['clip_interval_unit'] = group.get('clip_interval_unit', 'seconds')
        config['clip_random'] = group.get('clip_random', False)
        config['clip_random_base'] = group.get('clip_random_base', 'bpm')

        if self._two_track_mode.get():
            self._render_two_track_preview(idx)
            return

        try:
            structure_signature = self._preview_structure_signature()
        except (TypeError, ValueError, tk.TclError):
            return
        if (
            self._live_renderer
            and structure_signature != self._preview_renderer_signature
        ):
            self._preview_render_video(preserve_state=True)
            return

        audio_signature = repr((
            config.get("global_audio", {}),
            config.get("ambience_mixer", {}),
        ))
        if (
            self._live_renderer
            and self._preview_audio_signature is not None
            and audio_signature != self._preview_audio_signature
        ):
            self._preview_render_video(preserve_state=True)
        elif self._live_renderer:
            config["timeline"] = {
                "duration": self._preview_final_timeline_duration(
                    estimate_group_duration(group)
                ),
                "offset": 0.0,
            }
            with self._preview_render_lock:
                self._live_renderer.reconfigure(config)
            self._render_scrub_frame(self.scrub_var.get())
            self._preview_status_label.configure(text=t("design.configApplied", mix=idx+1))
        else:
            self._preview_render_video()

    def _render_two_track_preview(self, group_idx):
        g = self.app.video_groups[group_idx]
        tracks = g.get('tracks', [])
        valid = [trk for trk in tracks if trk.get('analysis') and trk.get('filepath')]
        if len(valid) < 2:
            self._preview_status_label.configure(text=t("design.needTwoTracks"))
            return
        analyses = [trk['analysis'] for trk in valid]
        boundaries = build_track_boundaries(analyses)
        first, second = compute_two_track_window(self._two_track_index, boundaries)
        if first is None:
            self._two_track_index = 0
            first, second = compute_two_track_window(0, boundaries)
        if second is None and first:
            self._preview_status_label.configure(text=t("design.lastTrack", index=self._two_track_index+1, total=len(valid)))
            self._show_pil_frame_fit(self._last_preview_pil_frame or Image.new('RGB', (640, 360), (30, 30, 40)))
            return
        total_tracks = len(boundaries)
        label_text = t("design.trackRange", start=self._two_track_index+1, end=min(self._two_track_index+2, total_tracks), total=total_tracks)
        self._preview_status_label.configure(text=label_text)
        if self._live_renderer:
            try:
                structure_signature = self._preview_structure_signature()
            except (TypeError, ValueError, tk.TclError):
                return
            if structure_signature != self._preview_renderer_signature:
                self._preview_render_video(preserve_state=False)
                return
            config = self._collect_config()
            config['clips'] = g.get('clips', [])
            config['clip_enabled'] = g.get('clip_enabled', False)
            config['clip_interval'] = g.get('clip_interval', 1.0)
            config['clip_interval_unit'] = g.get('clip_interval_unit', 'seconds')
            config['clip_random'] = g.get('clip_random', False)
            config['clip_random_base'] = g.get('clip_random_base', 'bpm')
            audio_signature = repr((
                config.get("global_audio", {}),
                config.get("ambience_mixer", {}),
            ))
            if (
                self._preview_audio_signature is not None
                and audio_signature != self._preview_audio_signature
            ):
                self._preview_render_video(preserve_state=True)
                return
            config["timeline"] = {
                "duration": self._preview_final_timeline_duration(
                    estimate_group_duration(g)
                ),
                "offset": float(first["start"]),
            }
            try:
                self._selected_resolution()
            except ValueError:
                return
            renderer = self._live_renderer
            window_duration = (second['end'] if second else first['end']) - first['start']
            mid_t = min(self._live_duration, window_duration) * 0.4
            try:
                with self._preview_render_lock:
                    renderer.reconfigure(config)
                    arr = renderer.render_frame(mid_t)
                image = Image.fromarray(arr)
                self._show_pil_frame_fit(image)
            except Exception as error:
                logger.debug("Two-track preview frame failed: %s", error)
        else:
            self._preview_render_video()

    def _selected_resolution(self):
        resolution_map = {
            "720p": (1280, 720), "1080p": (1920, 1080),
            "4k": (3840, 2160), "portrait": (1080, 1920),
            "square": (1080, 1080),
        }
        resolution_id = choice_id(
            self.resolution.get(), RESOLUTION_CHOICES, "1080p"
        )
        if resolution_id != "custom":
            return resolution_map.get(resolution_id, (1920, 1080))
        width = int(self.custom_width_var.get())
        height = int(self.custom_height_var.get())
        if not (64 <= width <= 7680 and 64 <= height <= 7680):
            raise ValueError(t("design.resRangeError"))
        return width - width % 2, height - height % 2

    def _selected_preview_resolution(self):
        quality = self.preview_quality_var.get()
        if quality == "custom":
            width = max(64, min(1920, int(self.preview_width_var.get())))
            height = max(64, min(1080, int(self.preview_height_var.get())))
            return width - width % 2, height - height % 2
        final_width, final_height = self._selected_resolution()
        long_edge = {
            "low": 640, "medium": 960, "high": 1280, "auto": 960,
        }.get(quality, 960)
        if final_width >= final_height:
            width = min(final_width, long_edge)
            height = round(width * final_height / final_width)
        else:
            height = min(final_height, long_edge)
            width = round(height * final_width / final_height)
        return max(64, width - width % 2), max(64, height - height % 2)

    def _preview_render_video(self, preserve_state=False):
        if self._preview_prepare_active:
            self._preview_generation += 1
            if self._preview_prepare_cancel_event:
                self._preview_prepare_cancel_event.set()
            self._preview_pending_refresh = True
            return
        if not self.app.video_groups:
            messagebox.showwarning(t("common.warning"), t("design.runDistributionFirst"))
            return
        idx = self.selected_group if 0 <= self.selected_group < len(self.app.video_groups) else 0
        g = self.app.video_groups[idx]
        tracks = g.get('tracks', [])
        if not tracks:
            return
        config = self._collect_config()
        if preserve_state and self._live_renderer is not None:
            self._preview_restore_state = (
                float(self.scrub_var.get()), bool(self._scrub_playing)
            )
        else:
            self._preview_restore_state = (0.0, True)
        self._preview_audio_signature = repr((
            config.get("global_audio", {}),
            config.get("ambience_mixer", {}),
        ))
        config['clips'] = g.get('clips', [])
        config['clip_enabled'] = g.get('clip_enabled', False)
        config['clip_interval'] = g.get('clip_interval', 1.0)
        config['clip_interval_unit'] = g.get('clip_interval_unit', 'seconds')
        config['clip_random'] = g.get('clip_random', False)
        config['clip_random_base'] = g.get('clip_random_base', 'bpm')
        try:
            pw, ph = self._selected_preview_resolution()
        except ValueError as error:
            messagebox.showwarning(t("design.resError"), str(error))
            return
        valid_tracks = [trk for trk in tracks if trk.get('analysis') and trk.get('filepath')]
        if not valid_tracks:
            return
        start = max(0, min(self._two_track_index, len(valid_tracks) - 1))
        count = 2 if self._two_track_mode.get() else 1
        valid_tracks = valid_tracks[start:start + count]
        self._preview_build_signature = (
            idx, tuple(track.get('filepath') for track in valid_tracks),
            (pw, ph),
        )
        analyses = [trk['analysis'] for trk in valid_tracks]
        self._stop_scrub_play()
        self._cleanup_preview_audio()
        self._a.set_button_state(
            self.preview_play_btn, tk.DISABLED, text=t("design.preparing")
        )
        self._preview_status_label.configure(text=t("design.mixingAudio"))
        self._preview_generation += 1
        preview_generation = self._preview_generation
        cancel_event = threading.Event()
        self._preview_prepare_cancel_event = cancel_event
        self._preview_state = "PREPARING"
        self._show_preview_loading()
        self._set_preview_loading_stage("design.previewTimeline")
        self._preview_prepare_active = True
        def _plog(msg):
            logger.info(msg)

        cumulative = 0.0
        crossfade = float(self.crossfade_duration.get())
        for trk in valid_tracks:
            ts = trk.get('trim_start', 0)
            te = trk.get('trim_end', 0)
            if te <= 0:
                an = trk.get('analysis')
                te = an.duration if an else te
            dur = max(0.1, te - ts)
            cumulative += dur
        analyses = [trk['analysis'] for trk in valid_tracks]
        _plog(f"valid_tracks={len(valid_tracks)}, est_duration={cumulative:.0f}s")
        estimated_base_duration = max(
            .1, cumulative - crossfade * max(0, len(valid_tracks) - 1)
        )
        preview_repeat_count = max(1, round(
            self._preview_final_timeline_duration(estimated_base_duration)
            / estimated_base_duration
        ))

        def run():
            _plog("=== 미리보기 시작 ===")
            tmp_audio = None
            tmp_stems = {}
            try:
                fd, tmp_audio = tempfile.mkstemp(
                    prefix="apm_livepreview_", suffix=".wav"
                )
                os.close(fd)
                for stem_name in ("music", "ambient"):
                    fd, stem_path = tempfile.mkstemp(
                        prefix=f"apm_{stem_name}_", suffix=".wav"
                    )
                    os.close(fd)
                    os.unlink(stem_path)
                    tmp_stems[stem_name] = stem_path
                from audio_pipeline import mix_tracks_streaming
                from video_gen import LiveFrameRenderer
                ffmpeg_exe = ensure_ffmpeg_available()
                self._post_preview_ui(
                    self._set_preview_loading_stage, "design.previewAudio"
                )
                _, dur, timestamps = mix_tracks_streaming(
                    ffmpeg_exe, analyses, valid_tracks, tmp_audio, crossfade,
                    cancel_event=cancel_event,
                    audio_settings={
                        **config.get("global_audio", {}),
                        "ambience_mixer": config.get(
                            "ambience_mixer", {}
                        ),
                    },
                    stem_output_paths=tmp_stems,
                )
                config["timeline"] = {
                    "duration": dur * preview_repeat_count,
                    "offset": 0.0,
                }
                self._post_preview_ui(
                    self._set_preview_loading_stage, "design.previewEffects"
                )
                renderer = LiveFrameRenderer(
                    analyses, pw, ph, dur, timestamps=timestamps,
                    crossfade_duration=crossfade, config_dict=config,
                )
                self._post_preview_ui(
                    self._on_live_renderer_ready,
                    renderer, dur, tmp_audio, tmp_stems,
                    preview_generation,
                )
            except Exception as e:
                import traceback
                _plog(f"ERROR: {e}\n{traceback.format_exc()}")
                if tmp_audio:
                    try:
                        os.unlink(tmp_audio)
                    except OSError:
                        pass
                for stem_path in tmp_stems.values():
                    try:
                        os.unlink(stem_path)
                    except OSError:
                        pass
                self._post_preview_ui(
                    self._on_preview_prepare_error, e, preview_generation
                )

        threading.Thread(target=run, daemon=True).start()

    def _on_preview_prepare_error(self, error, generation=None):
        self._preview_prepare_active = False
        self._preview_prepare_cancel_event = None
        if generation is not None and generation != self._preview_generation:
            if self._preview_pending_refresh:
                self._preview_pending_refresh = False
                self.after_idle(
                    lambda: self._preview_render_video(preserve_state=True)
                )
            return
        if self._preview_settings_after_id:
            try:
                self.after_cancel(self._preview_settings_after_id)
            except tk.TclError:
                pass
            self._preview_settings_after_id = None
        self._hide_preview_loading()
        self._preview_state = "FAILED"
        messagebox.showerror(
            t("common.error"),
            t("design.previewFailed", error=str(error)),
        )
        self._a.set_button_state(
            self.preview_play_btn, tk.NORMAL,
            text=t("design.livePlayback"),
        )
        self._preview_status_label.configure(text=t("design.failed"))
        if self._preview_pending_refresh:
            self._preview_pending_refresh = False
            self._schedule_preview_refresh()

    def _on_live_renderer_ready(
        self, renderer, duration, audio_path, bus_paths=None, generation=None
    ):
        self._preview_prepare_active = False
        self._preview_prepare_cancel_event = None
        if generation is not None and generation != self._preview_generation:
            try:
                os.unlink(audio_path)
            except OSError:
                pass
            for path in (bus_paths or {}).values():
                try:
                    os.unlink(path)
                except OSError:
                    pass
            if self._preview_pending_refresh:
                self._preview_pending_refresh = False
                self.after_idle(
                    lambda: self._preview_render_video(preserve_state=True)
                )
            return
        self._live_renderer = renderer
        self._preview_renderer_signature = self._preview_build_signature
        self._preview_state = "CONNECTING_PLAYER"
        self._live_duration = duration
        self._preview_mixed_audio_path = audio_path
        self._preview_bus_audio_paths = {
            name: path for name, path in (bus_paths or {}).items()
            if os.path.isfile(path)
        }
        self._preview_first_frame_ready = False
        self._preview_audio_ready = False
        self.scrub_scale.state(['!disabled'])
        self.scrub_scale.configure(to=max(duration, 0.1))
        restore_position, resume_playing = self._preview_restore_state or (
            0.0, True
        )
        restore_position = min(max(0.0, restore_position), duration)
        self._preview_restore_state = None
        self.scrub_var.set(restore_position)
        self._render_scrub_frame(restore_position)
        pw, ph = self._selected_preview_resolution()
        range_key = (
            "design.previewRangeTwo" if self._two_track_mode.get()
            else "design.previewRangeOne"
        )
        self._preview_status_label.configure(text=t(
            "design.previewReadyDetail", range=t(range_key),
            width=pw, height=ph, duration=duration,
        ))
        self._a.set_button_state(
            self.preview_play_btn, tk.NORMAL, text=t("design.stop"),
            command=self._stop_scrub_play,
        )
        if resume_playing:
            self._set_preview_loading_stage("design.previewConnecting")
            self._start_scrub_play()
        else:
            self._preview_audio_ready = True
            self._a.set_button_state(
                self.preview_play_btn, tk.NORMAL,
                text=t("design.livePlayback"),
                command=self._start_scrub_play,
            )
            self._maybe_finish_preview_loading()
        if self._preview_pending_refresh:
            self._preview_pending_refresh = False
            self._schedule_preview_refresh()

    def _show_preview_loading(self):
        self._hide_preview_loading()
        self.preview_canvas.delete("all")
        self._preview_loading_key = "design.loading"
        self._preview_loading_offset = [0.0]
        self._draw_preview_loading_overlay()
        self.preview_canvas.update_idletasks()
        self._animate_preview_loading()

    def _draw_preview_loading_overlay(self):
        cw = max(self.preview_canvas.winfo_width(), 640)
        ch = max(self.preview_canvas.winfo_height(), 360)
        cx, cy = cw // 2, ch // 2
        a = self._a
        self.preview_canvas.delete("_loading_text", "_loading_bg", "_loading_seg")
        self.preview_canvas.create_text(
                                        cx, cy - 20,
                                        text=t(self._preview_loading_key),
                                        font=(a.FONT_FAMILY, 14),
                                        fill=a.THEME.get('fg', '#cccccc'),
                                        tags="_loading_text")
        bar_w, bar_h = min(300, cw - 80), 6
        bx = (cw - bar_w) // 2
        by = cy + 10
        self.preview_canvas.create_rectangle(bx, by, bx + bar_w, by + bar_h,
                                             fill=a.THEME.get('bg_hover', '#333'), outline='',
                                             tags="_loading_bg")
        self._preview_loading_bar = (bx, by, bar_w, bar_h)

    def _set_preview_loading_stage(self, key):
        self._preview_loading_key = key
        self._preview_status_label.configure(text=t(key))
        self.preview_canvas.itemconfigure("_loading_text", text=t(key))

    def _maybe_finish_preview_loading(self):
        if self._preview_first_frame_ready and self._preview_audio_ready:
            self._hide_preview_loading()
            self._preview_state = "READY"
            width, height = self._selected_preview_resolution()
            range_key = (
                "design.previewRangeTwo" if self._two_track_mode.get()
                else "design.previewRangeOne"
            )
            self._preview_status_label.configure(text=t(
                "design.previewReadyDetail", range=t(range_key),
                width=width, height=height, duration=self._live_duration,
            ))

    def _animate_preview_loading(self):
        if not getattr(self, '_preview_loading_bar', None):
            return
        bx, by, bar_w, bar_h = self._preview_loading_bar
        self.preview_canvas.delete("_loading_seg")
        offset = self._preview_loading_offset[0]
        seg = bar_w * 0.3
        x1 = bx + int(offset * bar_w) % bar_w
        x2 = min(x1 + seg, bx + bar_w)
        a = self._a
        self.preview_canvas.create_rectangle(x1, by, x2, by + bar_h,
                                             fill=a.THEME.get('accent', '#5865f2'), outline='',
                                             tags="_loading_seg")
        self._preview_loading_offset[0] += 0.04
        self._preview_loading_after = self.after(30, self._animate_preview_loading)

    def _hide_preview_loading(self):
        if getattr(self, '_preview_loading_after', None):
            self.after_cancel(self._preview_loading_after)
            self._preview_loading_after = None
        self.preview_canvas.delete("_loading_text", "_loading_bg", "_loading_seg")
        self._preview_loading_bar = None
        self._preview_loading_key = "design.loading"

    def _show_pil_frame_fit(self, pil_img):
        self._last_preview_pil_frame = pil_img
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        img_w, img_h = pil_img.size
        scale = min(cw / img_w, ch / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))
        resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self._preview_photo = ImageTk.PhotoImage(
            resized, master=self.preview_canvas
        )
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(cw // 2, ch // 2, image=self._preview_photo)
        if getattr(self, "_preview_loading_bar", None):
            self._draw_preview_loading_overlay()
        if not self._preview_prepare_active and not self._preview_first_frame_ready:
            self._preview_first_frame_ready = True
            self._maybe_finish_preview_loading()

    def _on_preview_canvas_resize(self, event):
        if self._last_preview_pil_frame is not None:
            self._show_pil_frame_fit(self._last_preview_pil_frame)

    def _render_scrub_frame(self, pos):
        if not self._live_renderer:
            return
        self._preview_requested_t = float(pos)
        if self._preview_frame_worker_active:
            return
        self._preview_frame_worker_active = True
        generation = self._preview_generation

        def run():
            try:
                while self._preview_requested_t is not None:
                    if generation != self._preview_generation:
                        return
                    requested = self._preview_requested_t
                    self._preview_requested_t = None
                    with self._preview_render_lock:
                        renderer = self._live_renderer
                        if renderer is None:
                            return
                        arr = renderer.render_frame(requested)
                    image = Image.fromarray(arr)
                    self._post_preview_ui(
                        self._show_preview_frame, image, generation
                    )
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                print(f"[미리보기] 프레임 렌더링 실패: {e}\n{tb}")
                self._post_preview_ui(
                    self._on_preview_frame_error, e, generation
                )
            finally:
                self._preview_frame_worker_active = False
                if self._preview_requested_t is not None:
                    try:
                        self._post_preview_ui(
                            self._render_scrub_frame,
                            self._preview_requested_t,
                        )
                    except tk.TclError:
                        pass

        threading.Thread(target=run, daemon=True).start()

    def _show_preview_frame(self, image, generation):
        if generation == self._preview_generation:
            self._show_pil_frame_fit(image)

    def _on_preview_frame_error(self, error, generation):
        if generation != self._preview_generation:
            return
        self._hide_preview_loading()
        self._preview_state = "FAILED"
        self._preview_status_label.configure(
            text=t("design.renderError", error=str(error))
        )

    def _on_scrub_drag(self, value):
        if getattr(self, '_programmatic_scrub', False):
            return
        if self._scrub_playing:
            self._stop_scrub_play()
        self._render_scrub_frame(float(value))

    def _start_scrub_play(self):
        if not self._live_renderer:
            self._preview_render_video()
            return
        start = min(float(self.scrub_var.get()), self._live_duration)
        self.preview_play_btn.configure(
            state=tk.DISABLED, text=t("design.preparing")
        )
        generation = self._preview_generation
        if self._preview_mixed_audio_path:
            self._preview_audio_player.play(
                self._preview_mixed_audio_path,
                start=start,
                duration=(
                    None if start <= 0
                    else max(0.05, self._live_duration - start)
                ),
                on_ready=lambda: self._post_preview_ui(
                    self._begin_scrub_clock, generation
                ),
                on_error=lambda error: self._post_preview_ui(
                    self._on_preview_audio_error, error, generation
                ),
            )
        else:
            self._begin_scrub_clock(generation)

    def _begin_scrub_clock(self, generation=None):
        if generation is not None and generation != self._preview_generation:
            return
        self._preview_audio_ready = True
        self._maybe_finish_preview_loading()
        self._scrub_playing = True
        self.preview_play_btn.configure(
            state=tk.NORMAL, text=t("design.stop"),
            command=self._stop_scrub_play,
        )
        self._scrub_tick()

    def _on_preview_audio_error(self, error, generation=None):
        if generation is not None and generation != self._preview_generation:
            return
        logger.error(
            "Preview audio playback failed", exc_info=(
                type(error), error, error.__traceback__
            )
        )
        self._stop_scrub_play()
        self._hide_preview_loading()
        self._preview_state = "FAILED"
        self._preview_status_label.configure(
            text=t("design.previewFailed", error=str(error))
        )

    def _scrub_tick(self):
        if not self._scrub_playing:
            return
        cur_t = self.scrub_var.get()
        if cur_t >= self._live_duration:
            self._stop_scrub_play()
            return
        self._render_scrub_frame(cur_t)
        self._update_volume_meter(cur_t)
        self._programmatic_scrub = True
        try:
            self.scrub_var.set(cur_t + 1.0 / 24.0)
        finally:
            self._programmatic_scrub = False
        self._scrub_after_id = self.after(42, self._scrub_tick)

    def _stop_scrub_play(self):
        self._scrub_playing = False
        self._preview_audio_player.stop()
        if self._scrub_after_id:
            self.after_cancel(self._scrub_after_id)
            self._scrub_after_id = None
        self._a.set_button_state(
            self.preview_play_btn, tk.NORMAL, text=t("design.livePlayback"),
            command=self._start_scrub_play,
        )
        self._draw_volume_meter(-60.0, -60.0)

    def _update_volume_meter(self, position):
        now = time.perf_counter()
        if now - self._meter_last_update < .075:
            return
        self._meter_last_update = now
        source = choice_id(
            self.meter_source.get(), METER_SOURCE_CHOICES, "master"
        )
        path = (
            self._preview_mixed_audio_path
            if source == "master"
            else self._preview_bus_audio_paths.get(source)
        )
        if not path:
            self._draw_volume_meter(-60.0, -60.0)
            return
        try:
            import soundfile as sound_file
            if self._meter_audio_path != path:
                if self._meter_audio_handle is not None:
                    self._meter_audio_handle.close()
                self._meter_audio_handle = sound_file.SoundFile(path)
                self._meter_audio_path = path
            handle = self._meter_audio_handle
            start = max(0, int(position * handle.samplerate))
            handle.seek(min(start, max(0, len(handle) - 1)))
            samples = handle.read(
                max(256, int(handle.samplerate * .08)),
                dtype="float32", always_2d=True,
            )
            if not len(samples):
                self._draw_volume_meter(-60.0, -60.0)
                return
            peaks = np.max(np.abs(samples), axis=0)
            if len(peaks) == 1:
                peaks = np.repeat(peaks, 2)
            db = 20 * np.log10(np.maximum(peaks[:2], 1e-6))
            self._draw_volume_meter(float(db[0]), float(db[1]))
        except (OSError, RuntimeError, ValueError):
            self._draw_volume_meter(-60.0, -60.0)

    def _draw_volume_meter(self, left_db, right_db):
        if not hasattr(self, "meter_canvas"):
            return
        canvas = self.meter_canvas
        canvas.delete("all")
        width = max(50, canvas.winfo_width())
        height = max(120, canvas.winfo_height())
        now = time.time()
        for index, value in enumerate((left_db, right_db)):
            self._meter_hold[index] = max(
                value, self._meter_hold[index] - 1.2
            )
            x1 = 10 + index * 28
            x2 = x1 + 16
            canvas.create_rectangle(
                x1, 12, x2, height - 24,
                fill=self._a.THEME["slider_track"], outline="",
            )
            ratio = max(0.0, min(1.0, (value + 60.0) / 60.0))
            top = height - 24 - ratio * (height - 36)
            color = (
                self._a.THEME["danger"] if value >= -1
                else self._a.THEME["warning"] if value >= -12
                else self._a.THEME["success"]
            )
            canvas.create_rectangle(
                x1, top, x2, height - 24, fill=color, outline=""
            )
            hold_ratio = max(
                0.0, min(1.0, (self._meter_hold[index] + 60.0) / 60.0)
            )
            hold_y = height - 24 - hold_ratio * (height - 36)
            canvas.create_line(x1, hold_y, x2, hold_y, fill="#ffffff")
            canvas.create_text(
                (x1 + x2) / 2, height - 10,
                text=("L", "R")[index], fill=self._a.THEME["fg_dim"],
                font=(self._a.FONT_FAMILY, 8),
            )
        if max(left_db, right_db) >= -0.1:
            self._meter_clip_until = now + 1.5
        if now < self._meter_clip_until:
            canvas.create_text(
                width / 2, 5, text="CLIP", anchor=tk.N,
                fill=self._a.THEME["danger"],
                font=(self._a.FONT_FAMILY, 8, "bold"),
            )
        self.meter_value_label.configure(
            text=f"{max(left_db, right_db):.1f} dB"
        )

    def _cleanup_preview_audio(self):
        self._preview_audio_player.stop()
        if self._meter_audio_handle is not None:
            try:
                self._meter_audio_handle.close()
            except (OSError, RuntimeError):
                pass
        self._meter_audio_handle = None
        self._meter_audio_path = None
        path = self._preview_mixed_audio_path
        self._preview_mixed_audio_path = None
        if path:
            try:
                os.unlink(path)
            except OSError:
                logger.exception(
                    "Failed to remove preview audio file: %s", path
                )
        for stem_path in self._preview_bus_audio_paths.values():
            try:
                os.unlink(stem_path)
            except OSError:
                logger.exception(
                    "Failed to remove preview stem file: %s", stem_path
                )
        self._preview_bus_audio_paths = {}
