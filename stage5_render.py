import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
import sys
import json
import copy
import logging
import subprocess
from repeat_settings import MODE_COUNT, MODE_TARGET, build_repeat_plan, hms_to_seconds, estimate_group_duration, format_duration
from i18n import t, choice_id
from ffmpeg_service import ensure_ffmpeg_available

logger = logging.getLogger(__name__)


RESOLUTION_CHOICES = {
    "720p": "render.res720",
    "1080p": "render.res1080",
    "4k": "render.res4k",
    "portrait": "design.resolutionPortrait",
    "square": "design.resolutionSquare",
    "custom": "render.resCustom",
}
RESOLUTION_PRESETS = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
    "portrait": (1080, 1920),
    "square": (1080, 1080),
}
VIDEO_CODEC_CHOICES = {
    "auto": "render.autoCodec",
    "libx264": "render.cpuCodec",
    "h264_nvenc": "render.nvidiaCodec",
    "h264_qsv": "render.intelCodec",
    "h264_amf": "render.amdCodec",
}
LOOP_MODE_CHOICES = {
    MODE_COUNT: "render.loopCount",
    MODE_TARGET: "render.loopTarget",
}


def _get_app(app):
    return sys.modules[app.__class__.__module__]


class Stage5Render(tk.Frame):
    def __init__(self, parent, app):
        self.app = app
        self._a = _get_app(app)
        super().__init__(parent, bg=self._a.THEME['bg_main'])
        self.selected_group = 0
        self.build_ui()

    def build_ui(self):
        a = self._a
        T = a.THEME
        hdr = tk.Frame(self, bg=T['bg_main'])
        hdr.pack(fill=tk.X, padx=24, pady=(14, 0))
        a.styled_label(hdr, t("render.title"), size=20, bold=True, bg=T['bg_main']).pack(side=tk.LEFT)
        a.styled_button(hdr, t("common.save"), lambda: self.app.persist_video_groups(), padx=10).pack(side=tk.RIGHT, padx=2)

        main = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, bg=T['bg_main'], sashwidth=6,
            sashrelief=tk.FLAT, borderwidth=0, showhandle=False,
        )
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))

        left = tk.Frame(
            main, bg=T['bg_card'], highlightthickness=1,
            highlightbackground=T['border'],
        )
        main.add(left, width=350, minsize=280)
        canvas = tk.Canvas(left, bg=T['bg_card'], highlightthickness=0)
        sb = tk.Scrollbar(left, orient=tk.VERTICAL, command=canvas.yview,
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

        self.tabs_container = tk.Frame(self, bg=T['bg_main'])
        self.tabs_container.pack(pady=(0, 4))

        self.resolution = tk.StringVar(value="1080p")
        self.custom_width_var = tk.StringVar(value="1920")
        self.custom_height_var = tk.StringVar(value="1080")
        self._last_valid_resolution = (1920, 1080)
        self._resolution_syncing = False
        self.fps_var = tk.StringVar(value="24")
        self.video_codec_var = tk.StringVar(value="auto")
        self.audio_codec_var = tk.StringVar(value="aac")
        self.video_bitrate_var = tk.StringVar(value="5000k")
        self.audio_bitrate_var = tk.StringVar(value="320k")
        self.normalize_loudness_var = tk.BooleanVar(value=False)
        self.target_lufs_var = tk.StringVar(value="-14")
        self.loop_video_var = tk.BooleanVar(value=False)
        self.loop_mode_var = tk.StringVar(value=MODE_COUNT)
        self.loop_count_var = tk.StringVar(value="1")
        self.loop_target_h_var = tk.StringVar(value="1")
        self.loop_target_m_var = tk.StringVar(value="0")
        self.loop_target_s_var = tk.StringVar(value="0")
        self._render_cancel_event = threading.Event()
        self._render_job = None
        self._last_render_dir = None

        def sec(text):
            a.styled_label(sf, text, size=11, bold=True, bg=T['bg_card']).pack(fill=tk.X, pady=(12, 3), padx=12, anchor=tk.W)

        def sep():
            tk.Frame(sf, bg=T['separator'], height=1).pack(fill=tk.X, padx=12, pady=6)

        def opt(label, var, opts):
            f = tk.Frame(sf, bg=T['bg_card'])
            f.pack(fill=tk.X, padx=12, pady=2)
            if label: a.styled_label(f, label, size=10, bg=T['bg_card']).pack(side=tk.LEFT)
            m = a.styled_option_menu(f, var, opts)
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

        sec(t("render.resolution"))
        a.styled_choice_menu(
            sf, self.resolution, RESOLUTION_CHOICES
        ).pack(fill=tk.X, padx=12, pady=2)
        custom_res_row = tk.Frame(sf, bg=T['bg_card'])
        custom_res_row.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(custom_res_row, t("render.customRes"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        self.custom_width_entry = a.styled_entry(
            custom_res_row, textvariable=self.custom_width_var, width=6
        )
        self.custom_width_entry.pack(side=tk.LEFT, padx=(6, 2))
        a.styled_label(custom_res_row, t("render.resMulti"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        self.custom_height_entry = a.styled_entry(
            custom_res_row, textvariable=self.custom_height_var, width=6
        )
        self.custom_height_entry.pack(side=tk.LEFT, padx=2)
        for entry in (self.custom_width_entry, self.custom_height_entry):
            entry.bind("<Return>", self._commit_custom_resolution, add="+")
            entry.bind("<FocusOut>", self._commit_custom_resolution, add="+")
        opt(t("render.fps"), self.fps_var, ["8", "12", "24", "30"])
        codec_row = tk.Frame(sf, bg=T['bg_card'])
        codec_row.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(
            codec_row, t("render.videoCodec"), size=10, bg=T['bg_card']
        ).pack(side=tk.LEFT)
        a.styled_choice_menu(
            codec_row, self.video_codec_var, VIDEO_CODEC_CHOICES
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        opt(t("render.audioCodec"), self.audio_codec_var, ["aac", "libmp3lame"])
        _video_bitrate_options = {
            "720p": ["2500k", "3000k", "4000k", "5000k"],
            "1080p": ["4000k", "5000k", "6000k", "8000k"],
            "4k": ["16000k", "20000k", "24000k", "35000k"],
            "portrait": ["4000k", "5000k", "6000k", "8000k"],
            "square": ["4000k", "5000k", "6000k", "8000k"],
            "custom": ["4000k", "5000k", "6000k", "8000k"],
        }
        bitrate_row = tk.Frame(sf, bg=T['bg_card'])
        bitrate_row.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(bitrate_row, t("render.videoBitrate"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        self.video_bitrate_menu = a.styled_option_menu(bitrate_row, self.video_bitrate_var, [])
        self.video_bitrate_menu.pack(side=tk.LEFT, padx=(6, 2))
        a.styled_label(bitrate_row, t("render.bitrateVideo"), size=9, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_option_menu(bitrate_row, self.audio_bitrate_var, ["128k", "192k", "256k", "320k"]).pack(side=tk.LEFT, padx=(8, 2))
        a.styled_label(bitrate_row, t("render.bitrateAudio"), size=9, bg=T['bg_card']).pack(side=tk.LEFT)

        def _update_video_bitrate_options(*_):
            opts = _video_bitrate_options.get(self.resolution.get(), _video_bitrate_options["1080p"])
            cur = self.video_bitrate_var.get()
            if cur not in opts:
                self.video_bitrate_var.set(opts[len(opts)//2])
            menu = self.video_bitrate_menu["menu"]
            menu.delete(0, "end")
            for o in opts:
                menu.add_command(label=o, command=lambda v=o: self.video_bitrate_var.set(v))
        _update_video_bitrate_options()
        self.resolution.trace_add("write", _update_video_bitrate_options)
        self.resolution.trace_add("write", self._sync_preset_dimensions)

        sep()
        sec(t("render.repeatSection"))
        chk(t("render.loopEnable"), self.loop_video_var)
        repeat_mode_row = tk.Frame(sf, bg=T['bg_card'])
        repeat_mode_row.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(
            repeat_mode_row, t("render.loopMode"), size=10, bg=T['bg_card']
        ).pack(side=tk.LEFT)
        a.styled_choice_menu(
            repeat_mode_row, self.loop_mode_var, LOOP_MODE_CHOICES
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        count_row = tk.Frame(sf, bg=T['bg_card'])
        count_row.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(
            count_row, t("render.loopCountLabel"), size=10, bg=T['bg_card']
        ).pack(side=tk.LEFT)
        self.loop_count_entry = a.styled_entry(
            count_row, textvariable=self.loop_count_var, width=7
        )
        self.loop_count_entry.pack(side=tk.LEFT, padx=6)
        target_row = tk.Frame(sf, bg=T['bg_card'])
        target_row.pack(fill=tk.X, padx=12, pady=2)
        a.styled_label(
            target_row, t("render.loopTargetLabel"), size=10, bg=T['bg_card']
        ).pack(side=tk.LEFT)
        self.loop_target_entries = []
        for variable, unit in (
            (self.loop_target_h_var, t("render.loopTargetHours")),
            (self.loop_target_m_var, t("render.loopTargetMinutes")),
            (self.loop_target_s_var, t("render.loopTargetSec")),
        ):
            entry = a.styled_entry(target_row, textvariable=variable, width=4)
            entry.pack(side=tk.LEFT, padx=(5, 2))
            self.loop_target_entries.append(entry)
            a.styled_label(
                target_row, unit, size=9, bg=T['bg_card']
            ).pack(side=tk.LEFT)
        self.loop_summary_label = a.styled_label(sf, "", size=9, color=T['fg_dim'], bg=T['bg_card'])
        self.loop_summary_label.pack(fill=tk.X, anchor=tk.W, padx=12, pady=(4, 2))
        a.styled_label(
            sf, t("render.loopInfo"), size=8,
            color=T['fg_dimmer'], bg=T['bg_card']
        ).pack(anchor=tk.W, padx=12, pady=(0, 4))
        for entry in [self.loop_count_entry, *self.loop_target_entries]:
            entry.bind("<Return>", self._commit_repeat_fields, add="+")
            entry.bind("<FocusOut>", self._commit_repeat_fields, add="+")
        for variable in (
            self.loop_video_var, self.loop_mode_var, self.loop_count_var,
            self.loop_target_h_var, self.loop_target_m_var,
            self.loop_target_s_var,
        ):
            variable.trace_add("write", lambda *_: self._update_repeat_summary())

        sep()
        sec(t("globalAudio.title"))
        self.audio_summary_label = a.styled_label(
            sf, "", size=9, color=T['fg_dim'], bg=T['bg_card']
        )
        self.audio_summary_label.pack(fill=tk.X, padx=12, pady=4)
        a.styled_button(
            sf, t("render.editInEffects"), lambda: self.app.show_stage(4),
            padx=8,
        ).pack(anchor=tk.W, padx=12, pady=(0, 4))

        def _bind_wheel_recursive(widget):
            widget.bind("<MouseWheel>", _sf_mousewheel)
            for child in widget.winfo_children():
                _bind_wheel_recursive(child)

        _bind_wheel_recursive(sf)

        right = tk.Frame(
            main, bg=T['bg_card'], highlightthickness=1,
            highlightbackground=T['border'],
        )
        main.add(right, minsize=400)

        a.styled_label(right, t("render.queue"), size=12, bold=True, bg=T['bg_card']).pack(pady=(12, 6))

        self.queue_listbox = a.styled_listbox(right)
        self.queue_listbox.configure(height=10)
        self.queue_listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        self.render_btn = a.styled_button(right, t("render.startAll"), self._start_render, "primary", padx=10, pady=8)
        self.render_btn.pack(fill=tk.X, padx=12, pady=(0, 6))
        self.cancel_render_btn = a.styled_button(right, t("render.cancelAll"), self._cancel_render, "danger", padx=10, pady=6)
        self.cancel_render_btn.pack(fill=tk.X, padx=12, pady=(0, 6))
        a.set_button_state(self.cancel_render_btn, tk.DISABLED)
        self.retry_render_btn = a.styled_button(right, t("render.retryFailed"), self._retry_render, padx=10, pady=6)
        self.retry_render_btn.pack(fill=tk.X, padx=12, pady=(0, 6))
        a.set_button_state(self.retry_render_btn, tk.DISABLED)
        self.render_status = a.styled_label(right, "", size=9, color=T['fg_dim'], bg=T['bg_card'])
        self.render_status.pack(padx=12, anchor=tk.W)
        self.render_progress_frame = tk.Frame(right, bg=T['bg_card'])
        self.render_progress_frame.pack(fill=tk.X, padx=12, pady=(4, 8))
        self.render_progress_canvas = tk.Canvas(self.render_progress_frame, bg=T['bg_hover'],
                                                height=12, highlightthickness=0)
        self.render_progress_canvas.pack(fill=tk.X)
        self.render_progress_label = a.styled_label(self.render_progress_frame, "", size=8,
                                                    color=T['fg_dim'], bg=T['bg_card'])
        self.render_progress_label.pack(anchor=tk.W)

    def _get_repeat_plan(self, base_duration=None):
        if base_duration is None:
            if self.app.video_groups:
                index = min(self.selected_group, len(self.app.video_groups) - 1)
                base_duration = estimate_group_duration(
                    self.app.video_groups[index]
                )
            else:
                base_duration = 0
        return build_repeat_plan(
            base_duration,
            enabled=self.loop_video_var.get(),
            mode=choice_id(
                self.loop_mode_var.get(), LOOP_MODE_CHOICES, MODE_COUNT
            ),
            repeat_count=max(1, int(self.loop_count_var.get() or "1")),
            target_seconds=hms_to_seconds(
                self.loop_target_h_var.get() or "0",
                self.loop_target_m_var.get() or "0",
                self.loop_target_s_var.get() or "0",
            ),
        )

    def _commit_repeat_fields(self, _event=None):
        try:
            count = max(1, int(self.loop_count_var.get() or "1"))
            hours = max(0, int(self.loop_target_h_var.get() or "0"))
            minutes = max(0, min(59, int(self.loop_target_m_var.get() or "0")))
            seconds = max(0, min(59, int(self.loop_target_s_var.get() or "0")))
        except ValueError:
            count, hours, minutes, seconds = 1, 1, 0, 0
        self.loop_count_var.set(str(count))
        self.loop_target_h_var.set(str(hours))
        self.loop_target_m_var.set(str(minutes))
        self.loop_target_s_var.set(str(seconds))
        self._update_repeat_summary()
        self.app.set_dirty(True)

    def _update_repeat_summary(self):
        if not hasattr(self, "loop_summary_label"):
            return
        target_mode = choice_id(
            self.loop_mode_var.get(), LOOP_MODE_CHOICES, MODE_COUNT
        ) == MODE_TARGET
        self.loop_count_entry.configure(
            state=tk.DISABLED if target_mode else tk.NORMAL
        )
        for entry in self.loop_target_entries:
            entry.configure(state=tk.NORMAL if target_mode else tk.DISABLED)
        try:
            plan = self._get_repeat_plan()
            if not self.loop_video_var.get():
                text = t("render.loopSummaryNone", duration=format_duration(plan.base_seconds))
            elif target_mode:
                text = t("render.loopSummaryWithRepeat",
                         duration=format_duration(plan.base_seconds),
                         count=plan.repeat_count,
                         output=format_duration(plan.output_seconds),
                         overflow=format_duration(plan.overflow_seconds))
            else:
                text = t("render.loopSummarySimple",
                         duration=format_duration(plan.base_seconds),
                         count=plan.repeat_count,
                         output=format_duration(plan.output_seconds))
        except (TypeError, ValueError):
            text = t("render.loopSummaryError")
        self.loop_summary_label.configure(text=text)

    def refresh(self):
        self.queue_listbox.delete(0, tk.END)
        if not self.app.video_groups:
            self.render_status.configure(text=t("render.noGroup"))
            return
        for i, g in enumerate(self.app.video_groups):
            base_duration = estimate_group_duration(g)
            dur = self._get_repeat_plan(base_duration).output_seconds
            n = len(g.get('tracks', []))
            self.queue_listbox.insert(tk.END, t("render.queueItem", idx=i+1, count=n, seconds=int(dur), status=t("render.waiting")))
        a = self._a
        if 0 <= self.selected_group < len(self.app.video_groups):
            idx = self.selected_group
        else:
            idx = 0
            self.selected_group = 0
        a.populate_group_tabs(self.tabs_container, self.app.video_groups, idx, self._set_group)
        self._update_repeat_summary()
        if hasattr(self, "audio_summary_label"):
            config = self._collect_render_config()
            audio = config.get("global_audio", {})
            self.audio_summary_label.configure(text=(
                f"{t('globalAudio.musicMaster')}: "
                f"{audio.get('music_master_db', 0):.1f} dB\n"
                f"{t('globalAudio.normalizeTracks')}: "
                f"{'ON' if audio.get('normalize_tracks') else 'OFF'}  ·  "
                f"{t('globalAudio.targetLufs')}: "
                f"{audio.get('target_lufs', -14):.1f}\n"
                f"{t('globalAudio.truePeak')}: "
                f"{audio.get('true_peak_dbtp', -1):.1f} dBTP"
            ))

    def _set_group(self, idx):
        if idx == self.selected_group:
            return
        self.selected_group = idx
        self._a.populate_group_tabs(self.tabs_container, self.app.video_groups, idx, self._set_group)
        self._update_repeat_summary()

    def on_hide(self):
        pass

    def _selected_resolution(self):
        resolution_id = choice_id(
            self.resolution.get(), RESOLUTION_CHOICES, "1080p"
        )
        if resolution_id != "custom":
            return RESOLUTION_PRESETS.get(resolution_id, (1920, 1080))
        width = int(self.custom_width_var.get())
        height = int(self.custom_height_var.get())
        if not (64 <= width <= 7680 and 64 <= height <= 7680):
            raise ValueError(t("render.resolutionRange"))
        return width - width % 2, height - height % 2

    def _sync_preset_dimensions(self, *_args):
        if self._resolution_syncing:
            return
        preset_id = choice_id(
            self.resolution.get(), RESOLUTION_CHOICES, "1080p"
        )
        dimensions = RESOLUTION_PRESETS.get(preset_id)
        if not dimensions:
            return
        self._resolution_syncing = True
        try:
            self.custom_width_var.set(str(dimensions[0]))
            self.custom_height_var.set(str(dimensions[1]))
            self._last_valid_resolution = dimensions
        finally:
            self._resolution_syncing = False
        self.app.set_dirty(True)

    def _commit_custom_resolution(self, _event=None):
        if self._resolution_syncing:
            return
        try:
            width = int(self.custom_width_var.get())
            height = int(self.custom_height_var.get())
        except ValueError:
            width, height = self._last_valid_resolution
            self.custom_width_var.set(str(width))
            self.custom_height_var.set(str(height))
            return
        width = max(64, min(7680, width))
        height = max(64, min(7680, height))
        width -= width % 2
        height -= height % 2
        preset_id = next(
            (key for key, value in RESOLUTION_PRESETS.items()
             if value == (width, height)),
            "custom",
        )
        self._resolution_syncing = True
        try:
            self.custom_width_var.set(str(width))
            self.custom_height_var.set(str(height))
            self.resolution.set(preset_id)
            self._last_valid_resolution = (width, height)
        finally:
            self._resolution_syncing = False
        self.app.set_dirty(True)

    def _set_app_navigation_locked(self, locked):
        state = tk.DISABLED if locked else tk.NORMAL
        self._a.set_button_state(self.app.prev_btn, state)
        self._a.set_button_state(self.app.theme_btn, state)
        stage0 = self.app.stages[0]
        if hasattr(stage0, "lang_btn"):
            self._a.set_button_state(stage0.lang_btn, state)

    def _start_render(self, out_dir_override=None):
        if not self.app.video_groups:
            messagebox.showwarning(t("common.warning"), t("render.noGroup"))
            return
        out_dir = out_dir_override or filedialog.askdirectory(title=t("render.saveFolder"))
        if not out_dir:
            return
        self._last_render_dir = out_dir
        from render_jobs import RenderJob
        self._render_job = RenderJob(out_dir)
        self._render_job.set_state("VALIDATING_SETTINGS")
        self._render_cancel_event = self._render_job.cancel_event

        self._a.set_button_state(
            self.render_btn, tk.DISABLED, text=t("render.startAll")
        )
        self._a.set_button_state(self.cancel_render_btn, tk.NORMAL)
        self._a.set_button_state(self.retry_render_btn, tk.DISABLED)
        try:
            w, h = self._selected_resolution()
        except (TypeError, ValueError) as error:
            messagebox.showwarning(t("render.resolutionError"), str(error))
            self._a.set_button_state(
                self.render_btn, tk.NORMAL, text=t("render.startAll")
            )
            self._a.set_button_state(self.cancel_render_btn, tk.DISABLED)
            return
        loop_enabled = self.loop_video_var.get()
        try:
            repeat_mode = choice_id(
                self.loop_mode_var.get(), LOOP_MODE_CHOICES, MODE_COUNT
            )
            repeat_count = int(self.loop_count_var.get() or "1")
            repeat_target_seconds = hms_to_seconds(
                self.loop_target_h_var.get() or "0",
                self.loop_target_m_var.get() or "0",
                self.loop_target_s_var.get() or "0",
            )
        except (TypeError, ValueError):
            messagebox.showwarning(t("render.inputError"), t("render.loopCountError"))
            self._a.set_button_state(
                self.render_btn, tk.NORMAL, text=t("render.startAll")
            )
            self._a.set_button_state(self.cancel_render_btn, tk.DISABLED)
            return
        if loop_enabled and repeat_mode == MODE_COUNT and repeat_count < 1:
            messagebox.showwarning(t("render.inputError"), t("render.loopCountMin"))
            self._a.set_button_state(
                self.render_btn, tk.NORMAL, text=t("render.startAll")
            )
            self._a.set_button_state(self.cancel_render_btn, tk.DISABLED)
            return
        if loop_enabled and repeat_mode == MODE_TARGET and repeat_target_seconds <= 0:
            messagebox.showwarning(t("render.inputError"), t("render.loopTargetMin"))
            self._a.set_button_state(
                self.render_btn, tk.NORMAL, text=t("render.startAll")
            )
            self._a.set_button_state(self.cancel_render_btn, tk.DISABLED)
            return
        render_fps = int(self.fps_var.get())
        render_video_codec = choice_id(
            self.video_codec_var.get(), VIDEO_CODEC_CHOICES, "auto"
        )
        render_audio_codec = self.audio_codec_var.get()
        render_video_bitrate = self.video_bitrate_var.get().strip() or "5000k"
        render_audio_bitrate = self.audio_bitrate_var.get().strip() or "320k"
        render_groups = []
        for group in self.app.video_groups:
            snapshot = dict(group)
            snapshot['tracks'] = [dict(track) for track in group.get('tracks', [])]
            snapshot['clips'] = [dict(clip) for clip in group.get('clips', [])]
            render_groups.append(snapshot)
        base_render_config = self._collect_render_config()
        group_render_configs = []
        for group in render_groups:
            config = copy.deepcopy(base_render_config)
            config['background']['image'] = group.get('bg_image', config['background'].get('image'))
            config['clips'] = copy.deepcopy(group.get('clips', []))
            config['clip_enabled'] = group.get('clip_enabled', False)
            config['clip_interval'] = group.get('clip_interval', 1.0)
            config['clip_interval_unit'] = group.get('clip_interval_unit', 'seconds')
            config['clip_random'] = group.get('clip_random', False)
            config['clip_random_base'] = group.get('clip_random_base', 'bpm')
            group_render_configs.append(config)
        project_state_snapshot = self.app.collect_project_state()
        all_analysis_map = {track.filepath: track.analysis for track in self.app.tracks if track.analysis}
        stage0 = self.app.stages[0]
        project_target_duration = (
            stage0.get_target_seconds()
            if hasattr(stage0, "get_target_seconds") else 0
        )
        project_tolerance = (
            stage0.get_tolerance()
            if hasattr(stage0, "get_tolerance") else 0
        )
        def _rlog(msg):
            logger.info(msg)
            self._render_job.log(msg)

        def _encoder_started(pid):
            self._render_job.process_pid = pid
            self._render_job.set_state("RUNNING")
            logger.info("Render encoder pid=%s", pid)

        def run():
            _rlog(f"=== render start: {len(render_groups)} groups ===")
            from video_gen import (
                RenderCancelledError,
                loop_video_repetitions,
            )
            try:
                from ffmpeg_service import ensure_ffprobe_available
                from render_jobs import validate_media_output
                self._render_job.set_state("PREPARING")
                total_groups = len(render_groups)
                self.app.post_ui(
                    lambda tt=total_groups:
                    self._render_set_progress(0, tt, 0)
                )
                render_errors = 0
                successful_outputs = 0
                last_render_error = None
                for gi, g in enumerate(render_groups):
                    if self._render_cancel_event.is_set():
                        raise RuntimeError(t("render.cancelled"))
                    tracks = g.get('tracks', [])
                    if not tracks:
                        render_errors += 1
                        self.app.post_ui(
                            lambda ii=gi: self._update_queue(
                                ii, t("render.noAnalyzedTracks")
                            )
                        )
                        continue
                    self.app.post_ui(
                        lambda ii=gi:
                        self._update_queue(ii, t("render.mixingAudio"))
                    )
                    valid_tracks = [tr for tr in tracks if tr.get('analysis') and tr.get('filepath')]
                    analyses = [tr['analysis'] for tr in valid_tracks]
                    if not analyses:
                        render_errors += 1
                        self.app.post_ui(
                            lambda ii=gi: self._update_queue(
                                ii, t("render.noAnalyzedTracks")
                            )
                        )
                        continue
                    try:
                        self._render_job.set_state("BUILDING_TIMELINE")
                        g_dir = os.path.join(out_dir, f"mix_{gi+1}")
                        os.makedirs(g_dir, exist_ok=True)
                        a_out = os.path.join(g_dir, "audio.wav")
                        from audio_pipeline import mix_tracks_streaming
                        ffmpeg_exe = ensure_ffmpeg_available()
                        self._render_job.set_state("PREPARING_AUDIO")
                        audio_settings = copy.deepcopy(
                            group_render_configs[gi].get(
                                "global_audio", {}
                            )
                        )
                        audio_settings["ambience_mixer"] = copy.deepcopy(
                            group_render_configs[gi].get(
                                "ambience_mixer", {}
                            )
                        )
                        from ambient_engine import has_active_ambience
                        deferred_ambient = (
                            loop_enabled
                            and has_active_ambience(audio_settings)
                        )
                        if deferred_ambient:
                            audio_settings["ambience_mixer"] = {
                                "enabled": False, "sources": {}
                            }
                        crossfade_duration = float(
                            group_render_configs[gi].get(
                                "scene_transition", {}
                            ).get("crossfade_duration", 4.0)
                        )
                        _, dur, timestamps = mix_tracks_streaming(
                            ffmpeg_exe, analyses, valid_tracks, a_out,
                            crossfade_duration,
                            cancel_event=self._render_cancel_event,
                            audio_settings=audio_settings,
                        )
                        if render_video_codec == "auto":
                            from video_gen import _detect_gpu_encoder
                            _actual_codec = _detect_gpu_encoder()
                        else:
                            _actual_codec = render_video_codec
                        _codec_label = "GPU" if _actual_codec != "libx264" else "CPU"
                        self.app.post_ui(
                            lambda ii=gi, label=_codec_label:
                            self._update_queue(
                                ii, t("render.encoding", codec=label)
                            )
                        )
                        config = copy.deepcopy(group_render_configs[gi])
                        final_visibility = copy.deepcopy(
                            config.get("visibility", {})
                        )
                        if loop_enabled:
                            config.setdefault("visibility", {})["enabled"] = False
                        vc = os.path.join(g_dir, "_visual.json")
                        with open(vc, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                        _last_progress_ts = [0.0]
                        _group_render_start = time.time()

                        def _on_frame_progress(
                            value, total, ii=gi, tt=total_groups,
                            cl=_codec_label, last_progress=_last_progress_ts,
                            render_start=_group_render_start,
                        ):
                            if self._render_cancel_event.is_set():
                                raise RenderCancelledError(t("render.cancelled"))
                            now = time.time()
                            if now - last_progress[0] < 0.2 and value < total:
                                return
                            last_progress[0] = now
                            frac = value / total if total else 0
                            overall = (ii + frac) / max(tt, 1)
                            elapsed = now - render_start
                            if frac > 0:
                                remaining = (elapsed / frac) - elapsed
                                if remaining >= 3600:
                                    eta = t("render.etaHours", hours=int(remaining//3600), minutes=int(remaining%3600//60))
                                elif remaining >= 60:
                                    eta = t("render.etaMin", minutes=int(remaining//60), seconds=int(remaining%60))
                                else:
                                    eta = t("render.etaSec", seconds=int(remaining))
                            else:
                                eta = ""
                            self.app.post_ui(lambda
                                cl=cl, frac=frac, ii=ii, tt=tt, eta=eta,
                                overall=overall: (
                                self.render_status.configure(text=t("render.encodingProgress", codec=cl, percent=int(frac*100), current=ii+1, total=tt, eta=eta)),
                                self._render_set_progress(ii, tt, overall),
                            ))

                        v_out = os.path.join(g_dir, f"mix_{gi+1}.mp4")
                        from video_gen import generate_video
                        self._render_job.set_state("PREPARING_VIDEO")
                        self._render_job.set_state("STARTING_ENCODER")
                        generate_video(
                            analyses, a_out, v_out, width=w, height=h,
                            visual_config_path=vc, timestamps=timestamps,
                            crossfade_duration=crossfade_duration,
                            frame_progress_callback=_on_frame_progress,
                            fps=render_fps, video_codec=render_video_codec,
                            audio_codec=render_audio_codec,
                            video_bitrate=render_video_bitrate,
                            audio_bitrate=render_audio_bitrate,
                            process_callback=_encoder_started,
                            cancel_event=self._render_cancel_event,
                            log_callback=_rlog,
                        )
                        self._render_job.set_state("FINALIZING")
                        final_output = v_out
                        expected_duration = dur
                        txt_path = os.path.join(g_dir, "timestamps.txt")
                        self._save_timestamps_txt(txt_path, timestamps, dur)
                        if loop_enabled:
                            if self._render_cancel_event.is_set():
                                raise RuntimeError(t("render.cancelled"))
                            self.app.post_ui(
                                lambda ii=gi:
                                self._update_queue(ii, t("render.loopVideo"))
                            )
                            repeat_plan = build_repeat_plan(
                                dur, enabled=True,
                                mode=repeat_mode,
                                repeat_count=repeat_count, target_seconds=repeat_target_seconds,
                            )
                            loop_label = (t("render.loopTargetSeconds", seconds=repeat_target_seconds) if repeat_plan.mode == MODE_TARGET
                                          else t("render.loopRepeatCount", count=repeat_plan.repeat_count))
                            loop_out = os.path.join(g_dir, f"mix_{gi+1}_loop_{loop_label}.mp4")
                            loop_video_repetitions(
                                v_out, loop_out, repeat_plan.repeat_count,
                                cancel_event=self._render_cancel_event,
                            )
                            if final_visibility.get("enabled"):
                                from video_gen import apply_visibility_window
                                visibility_out = os.path.join(
                                    g_dir, f"mix_{gi+1}_final.mp4"
                                )
                                apply_visibility_window(
                                    loop_out, visibility_out,
                                    repeat_plan.output_seconds,
                                    final_visibility,
                                    cancel_event=self._render_cancel_event,
                                    video_codec=render_video_codec,
                                )
                                os.replace(visibility_out, loop_out)
                            if deferred_ambient:
                                from audio_pipeline import (
                                    mix_ambient_over_media,
                                )
                                ambient_out = os.path.join(
                                    g_dir, f"mix_{gi+1}_ambient.mp4"
                                )
                                mix_ambient_over_media(
                                    ffmpeg_exe, loop_out, ambient_out,
                                    repeat_plan.output_seconds,
                                    {
                                        **group_render_configs[gi].get(
                                            "global_audio", {}
                                        ),
                                        "ambience_mixer":
                                        group_render_configs[gi].get(
                                            "ambience_mixer", {}
                                        ),
                                    },
                                    audio_codec=render_audio_codec,
                                    audio_bitrate=render_audio_bitrate,
                                    cancel_event=self._render_cancel_event,
                                )
                                os.replace(ambient_out, loop_out)
                            final_output = loop_out
                            expected_duration = repeat_plan.output_seconds
                        self._render_job.set_state("VALIDATING_OUTPUT")
                        validation = validate_media_output(
                            final_output, ensure_ffprobe_available(), w, h,
                            expected_duration, require_audio=True,
                        )
                        self._render_job.last_output = validation
                        successful_outputs += 1
                        done_text = t("render.completedWithLoop") if loop_enabled else t("render.completed")
                        self.app.post_ui(
                            lambda ii=gi, text=done_text:
                            self._update_queue(ii, text)
                        )
                        self.app.post_ui(
                            lambda ii=gi, tt=total_groups:
                            self._render_set_progress(
                                ii + 1, tt, (ii + 1) / max(tt, 1)
                            )
                        )
                    except Exception as group_error:
                        render_errors += 1
                        _cancel_text = t("render.cancelled")
                        if _cancel_text in str(group_error) or isinstance(group_error, RenderCancelledError):
                            self.app.post_ui(
                                lambda ii=gi:
                                self._update_queue(ii, t("render.cancelled"))
                            )
                            raise
                        else:
                            self.app.post_ui(
                                lambda ii=gi, err=group_error:
                                self._update_queue(
                                    ii, t("render.groupError", error=err)
                                )
                            )
                            import traceback
                            _tb = traceback.format_exc()
                            last_render_error = (
                                str(group_error), self._render_job.stage, _tb
                            )
                            _rlog(f"group {gi+1} render error: {group_error}\n{_tb}")
                if self.app.project and self.app.project.project_dir and len(self.app.stages) > 0:
                    self.app.project.target_duration = project_target_duration
                    self.app.project.tolerance = project_tolerance
                    with self.app._project_save_lock:
                        self.app.project.save(
                            analyses=all_analysis_map,
                            video_groups=render_groups,
                            app_state=project_state_snapshot,
                        )
                if render_errors or not successful_outputs:
                    self._render_job.set_state("FAILED")
                    error, stage, detail = last_render_error or (
                        t("render.renderErrors", errors=render_errors, path=out_dir),
                        self._render_job.stage,
                        "",
                    )
                    self.app.post_ui(lambda: (
                        self.render_status.configure(text=t("render.completedWithErrors", count=render_errors)),
                        self.retry_render_btn.configure(state=tk.NORMAL),
                    ))
                    self.app.post_ui(
                        lambda err=error, st=stage, extra=detail:
                        self._show_render_error_dialog(
                            err, st, self._render_job.log_path,
                            self._render_job.job_id, extra,
                        )
                    )
                else:
                    self._render_job.set_state("COMPLETED")
                    validation = dict(self._render_job.last_output or {})
                    self._post_verified_completion(validation, out_dir)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                _cancel_text = t("render.cancelled")
                is_cancel = _cancel_text in str(e) or isinstance(e, RenderCancelledError)
                error_text = str(e)
                failure_stage = self._render_job.stage
                _rlog(f"render failed at {failure_stage}: {e}\n{tb}")
                if is_cancel:
                    self._render_job.set_state("CANCELLED")
                    self.app.post_ui(lambda: (
                        self.render_status.configure(text=t("render.cancelled")),
                        self.retry_render_btn.configure(state=tk.NORMAL),
                    ))
                else:
                    self._render_job.set_state("FAILED")
                    self.app.post_ui(
                        lambda detail=error_text:
                        self.render_status.configure(
                            text=t("render.renderError", error=detail)
                        )
                    )
                    self.app.post_ui(
                        lambda: self.retry_render_btn.configure(
                            state=tk.NORMAL
                        )
                    )
                    self.app.post_ui(
                        lambda detail=error_text, trace=tb, st=failure_stage:
                        self._show_render_error_dialog(
                            detail, st,
                            self._render_job.log_path,
                            self._render_job.job_id, trace,
                        )
                    )
            finally:
                def _restore():
                    self.render_btn.configure(state=tk.NORMAL, text=t("render.startAll"))
                    self.cancel_render_btn.configure(state=tk.DISABLED, text=t("render.cancelAll"))
                    self._set_app_navigation_locked(False)
                self.app.post_ui(_restore)

        self._set_app_navigation_locked(True)
        threading.Thread(target=run, daemon=True).start()

    def _show_render_error_dialog(
        self, error, stage, log_path, job_id, traceback_text="",
    ):
        details = (
            f"{t('renderFailure.job')}: {job_id}\n"
            f"{t('renderFailure.stage')}: {stage}\n"
            f"{t('renderFailure.log')}: {log_path}\n\n{error}"
        )
        if traceback_text:
            details += f"\n\n{traceback_text}"
        window = tk.Toplevel(self)
        window.title(t("renderFailure.title"))
        window.transient(self.winfo_toplevel())
        window.geometry("760x430")
        window.minsize(560, 300)
        window.configure(bg=self._a.THEME["bg_main"])
        text_widget = tk.Text(
            window, wrap="word", bg=self._a.THEME["bg_input"],
            fg=self._a.THEME["fg"], relief=tk.FLAT, padx=12, pady=12,
        )
        text_widget.insert("1.0", details)
        text_widget.configure(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 6))
        buttons = tk.Frame(window, bg=self._a.THEME["bg_main"])
        buttons.pack(fill=tk.X, padx=12, pady=(0, 12))

        def open_path(path):
            try:
                if sys.platform == "win32":
                    os.startfile(path)
                else:
                    subprocess.Popen(["xdg-open", path])
            except OSError as open_error:
                messagebox.showerror(t("common.error"), str(open_error))

        def copy_details():
            window.clipboard_clear()
            window.clipboard_append(details)
            window.update_idletasks()

        def retry():
            window.destroy()
            self.after(0, self._retry_render)

        for label, command in (
            (t("renderFailure.openLog"), lambda: open_path(log_path)),
            (t("renderFailure.openFolder"), lambda: open_path(os.path.dirname(log_path))),
            (t("renderFailure.copyDetails"), copy_details),
            (t("common.retry"), retry),
            (t("common.close"), window.destroy),
        ):
            self._a.styled_button(
                buttons, label, command, padx=8, pady=5,
            ).pack(side=tk.LEFT, padx=(0, 6))

    def _show_verified_completion(self, validation, output_dir):
        self.render_status.configure(text=t("render.completed"))
        self.retry_render_btn.configure(state=tk.DISABLED)
        if validation:
            message = t(
                "render.outputVerified",
                path=validation["path"],
                duration=format_duration(validation["duration"]),
                width=validation["width"],
                height=validation["height"],
                size=f"{validation['size'] / (1024 * 1024):.1f} MB",
            )
        else:
            message = t("render.outputSaved", path=output_dir)
        messagebox.showinfo(t("common.done"), message)

    def _post_verified_completion(self, validation, output_dir):
        self.app.post_ui(
            lambda result=validation, directory=output_dir:
            self._show_verified_completion(result, directory)
        )

    def _collect_render_config(self):
        if len(self.app.stages) > 4 and hasattr(self.app.stages[4], '_collect_config'):
            config = self.app.stages[4]._collect_config()
        else:
            config = {}
        config.setdefault('visibility', {
            'enabled': False, 'turn_off_after': 0.0,
            'restore_before_end': 0.0, 'restore': False,
            'black_color': '#000000',
        })
        return config

    def _cancel_render(self):
        if self._render_job:
            self._render_job.cancel()
        self.cancel_render_btn.configure(state=tk.DISABLED, text=t("render.cancelling"))
        self.render_status.configure(text=t("render.cancellingStatus"))

    def _retry_render(self):
        if not self._last_render_dir:
            messagebox.showinfo(t("common.retry"), t("render.noPrevious"))
            return
        self._start_render(self._last_render_dir)

    def _update_queue(self, idx, text):
        group = self.app.video_groups[idx]
        dur = self._get_repeat_plan(
            estimate_group_duration(group)
        ).output_seconds
        n = len(group.get('tracks', []))
        self.queue_listbox.delete(idx)
        self.queue_listbox.insert(idx, t("render.queueItem", idx=idx+1, count=n, seconds=int(dur), status=text))

    def _render_set_progress(self, done, total, pct):
        self.render_progress_canvas.delete("all")
        cw = self.render_progress_canvas.winfo_width()
        if cw < 10:
            cw = 200
        h = 12
        a = self._a
        self.render_progress_canvas.create_rectangle(0, 0, cw, h, fill=a.THEME['bg_hover'], outline='')
        if pct > 0:
            self.render_progress_canvas.create_rectangle(0, 0, int(cw * pct), h, fill=a.THEME['accent'], outline='')
        self.render_progress_label.configure(text=t("render.progress", done=done, total=total, percent=int(pct*100)))

    def _save_timestamps_txt(self, filepath, timestamps, total_duration):
        lines = []
        for ts in timestamps:
            start = ts.get('start_time', 0)
            sm, ss = int(start // 60), int(start % 60)
            filename = ts.get('filename', 'Unknown')
            lines.append(f"[{sm:02d}:{ss:02d}] {filename}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
