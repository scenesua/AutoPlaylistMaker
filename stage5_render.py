import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
import sys
import json
import copy
import logging
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
        self.fps_var = tk.StringVar(value="24")
        self.video_codec_var = tk.StringVar(value="auto")
        self.audio_codec_var = tk.StringVar(value="aac")
        self.video_bitrate_var = tk.StringVar(value="5000k")
        self.audio_bitrate_var = tk.StringVar(value="320k")
        self.normalize_loudness_var = tk.BooleanVar(value=False)
        self.target_lufs_var = tk.StringVar(value="-14")
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
        a.styled_entry(custom_res_row, textvariable=self.custom_width_var, width=6).pack(side=tk.LEFT, padx=(6, 2))
        a.styled_label(custom_res_row, t("render.resMulti"), size=10, bg=T['bg_card']).pack(side=tk.LEFT)
        a.styled_entry(custom_res_row, textvariable=self.custom_height_var, width=6).pack(side=tk.LEFT, padx=2)
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

        sep()
        sec(t("render.loopVideo"))
        self.loop_summary_label = a.styled_label(sf, "", size=9, color=T['fg_dim'], bg=T['bg_card'])
        self.loop_summary_label.pack(fill=tk.X, anchor=tk.W, padx=12, pady=(4, 2))
        a.styled_label(
            sf, t("render.loopReadOnlyInfo"), size=8,
            color=T['fg_dimmer'], bg=T['bg_card']
        ).pack(anchor=tk.W, padx=12, pady=(0, 4))
        a.styled_button(
            sf, t("render.editInEffects"), lambda: self.app.show_stage(4),
            padx=8,
        ).pack(anchor=tk.W, padx=12, pady=(0, 4))

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

    def _repeat_stage(self):
        return self.app._ensure_stage(4)

    @property
    def loop_video_var(self):
        return self._repeat_stage().loop_video_var

    @property
    def loop_mode_var(self):
        return self._repeat_stage().loop_mode_var

    @property
    def loop_count_var(self):
        return self._repeat_stage().loop_count_var

    @property
    def loop_target_h_var(self):
        return self._repeat_stage().loop_target_h_var

    @property
    def loop_target_m_var(self):
        return self._repeat_stage().loop_target_m_var

    @property
    def loop_target_s_var(self):
        return self._repeat_stage().loop_target_s_var

    def _get_repeat_plan(self, base_duration=None):
        return self._repeat_stage().get_repeat_plan(base_duration)

    def _update_repeat_summary(self):
        if not hasattr(self, "loop_summary_label"):
            return
        target_mode = choice_id(
            self.loop_mode_var.get(), LOOP_MODE_CHOICES, MODE_COUNT
        ) == MODE_TARGET
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
            ambient_count = sum(
                1 for item in audio.get("ambient_tracks", [])
                if item.get("enabled", True)
            )
            self.audio_summary_label.configure(text=(
                f"{t('globalAudio.musicMaster')}: "
                f"{audio.get('music_master_db', 0):.1f} dB\n"
                f"{t('globalAudio.normalizeTracks')}: "
                f"{'ON' if audio.get('normalize_tracks') else 'OFF'}  ·  "
                f"{t('globalAudio.targetLufs')}: "
                f"{audio.get('target_lufs', -14):.1f}\n"
                f"{t('globalAudio.truePeak')}: "
                f"{audio.get('true_peak_dbtp', -1):.1f} dBTP  ·  "
                f"{t('globalAudio.ambientTracks')}: {ambient_count}"
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
            raise ValueError(t("render.resolutionRange"))
        return width - width % 2, height - height % 2

    def _start_render(self, out_dir_override=None, skip_completed=False):
        if not self.app.video_groups:
            messagebox.showwarning(t("common.warning"), t("render.noGroup"))
            return
        out_dir = out_dir_override or filedialog.askdirectory(title=t("render.saveFolder"))
        if not out_dir:
            return
        self._last_render_dir = out_dir
        from render_jobs import RenderJob
        self._render_job = RenderJob(out_dir)
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
            return
        if loop_enabled and repeat_mode == MODE_COUNT and repeat_count < 1:
            messagebox.showwarning(t("render.inputError"), t("render.loopCountMin"))
            self._a.set_button_state(
                self.render_btn, tk.NORMAL, text=t("render.startAll")
            )
            return
        if loop_enabled and repeat_mode == MODE_TARGET and repeat_target_seconds <= 0:
            messagebox.showwarning(t("render.inputError"), t("render.loopTargetMin"))
            self._a.set_button_state(
                self.render_btn, tk.NORMAL, text=t("render.startAll")
            )
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
        def _rlog(msg):
            logger.info(msg)

        def run():
            _rlog(f"=== render start: {len(render_groups)} groups ===")
            from video_gen import (
                RenderCancelledError,
                loop_video_repetitions,
            )
            try:
                total_groups = len(render_groups)
                self.after(0, lambda tt=total_groups: self._render_set_progress(0, tt, 0))
                render_errors = 0
                render_skipped = 0
                for gi, g in enumerate(render_groups):
                    if self._render_cancel_event.is_set():
                        raise RuntimeError(t("render.cancelled"))
                    tracks = g.get('tracks', [])
                    if not tracks:
                        render_skipped += 1
                        continue
                    if skip_completed and self._render_job.is_completed(gi):
                        self.after(0, lambda ii=gi: self._update_queue(ii, t("render.keepCompleted")))
                        continue
                    self.after(0, lambda ii=gi: self._update_queue(ii, t("render.mixingAudio")))
                    valid_tracks = [tr for tr in tracks if tr.get('analysis') and tr.get('filepath')]
                    analyses = [tr['analysis'] for tr in valid_tracks]
                    if not analyses:
                        render_skipped += 1
                        continue
                    try:
                        g_dir = os.path.join(out_dir, f"mix_{gi+1}")
                        os.makedirs(g_dir, exist_ok=True)
                        a_out = os.path.join(g_dir, "audio.wav")
                        from audio_pipeline import mix_tracks_streaming
                        ffmpeg_exe = ensure_ffmpeg_available()
                        audio_settings = copy.deepcopy(
                            group_render_configs[gi].get(
                                "global_audio", {}
                            )
                        )
                        deferred_ambient = (
                            loop_enabled
                            and any(
                                item.get("enabled", True)
                                and item.get("filepath")
                                and os.path.isfile(item["filepath"])
                                for item in audio_settings.get(
                                    "ambient_tracks", []
                                )
                            )
                        )
                        if deferred_ambient:
                            audio_settings["ambient_tracks"] = []
                        _, dur, timestamps = mix_tracks_streaming(
                            ffmpeg_exe, analyses, valid_tracks, a_out, 4.0,
                            cancel_event=self._render_cancel_event,
                            audio_settings=audio_settings,
                        )
                        if render_video_codec == "auto":
                            from video_gen import _detect_gpu_encoder
                            _actual_codec = _detect_gpu_encoder()
                        else:
                            _actual_codec = render_video_codec
                        _codec_label = "GPU" if _actual_codec != "libx264" else "CPU"
                        self.after(
                            0, lambda ii=gi, label=_codec_label:
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
                            self.after(0, lambda: (
                                self.render_status.configure(text=t("render.encodingProgress", codec=cl, percent=int(frac*100), current=ii+1, total=tt, eta=eta)),
                                self._render_set_progress(ii, tt, overall),
                            ))

                        v_out = os.path.join(g_dir, f"mix_{gi+1}.mp4")
                        from video_gen import generate_video
                        generate_video(
                            analyses, a_out, v_out, width=w, height=h,
                            visual_config_path=vc, timestamps=timestamps,
                            crossfade_duration=4.0,
                            frame_progress_callback=_on_frame_progress,
                            fps=render_fps, video_codec=render_video_codec,
                            audio_codec=render_audio_codec,
                            video_bitrate=render_video_bitrate,
                            audio_bitrate=render_audio_bitrate,
                        )
                        txt_path = os.path.join(g_dir, "timestamps.txt")
                        self._save_timestamps_txt(txt_path, timestamps, dur)
                        if loop_enabled:
                            if self._render_cancel_event.is_set():
                                raise RuntimeError(t("render.cancelled"))
                            self.after(0, lambda ii=gi: self._update_queue(ii, t("render.loopVideo")))
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
                                    group_render_configs[gi].get(
                                        "global_audio", {}
                                    ),
                                    audio_codec=render_audio_codec,
                                    audio_bitrate=render_audio_bitrate,
                                    cancel_event=self._render_cancel_event,
                                )
                                os.replace(ambient_out, loop_out)
                        done_text = t("render.completedWithLoop") if loop_enabled else t("render.completed")
                        self.after(0, lambda ii=gi, text=done_text: self._update_queue(ii, text))
                        self.after(0, lambda ii=gi, tt=total_groups: self._render_set_progress(ii+1, tt, (ii+1)/max(tt, 1)))
                    except Exception as group_error:
                        render_errors += 1
                        _cancel_text = t("render.cancelled")
                        if _cancel_text in str(group_error) or isinstance(group_error, RenderCancelledError):
                            self.after(0, lambda ii=gi: self._update_queue(ii, t("render.cancelled")))
                        else:
                            self.after(0, lambda ii=gi, err=group_error: self._update_queue(ii, t("render.groupError", error=err)))
                            import traceback
                            _tb = traceback.format_exc()
                            _rlog(f"group {gi+1} render error: {group_error}\n{_tb}")
                if self.app.project and self.app.project.project_dir and len(self.app.stages) > 0:
                    s0 = self.app.stages[0]
                    if hasattr(s0, 'get_target_seconds'):
                        self.app.project.target_duration = s0.get_target_seconds()
                    if hasattr(s0, 'get_tolerance'):
                        self.app.project.tolerance = s0.get_tolerance()
                    with self.app._project_save_lock:
                        self.app.project.save(
                            analyses=all_analysis_map,
                            video_groups=self.app.video_groups,
                            app_state=project_state_snapshot,
                        )
                if render_errors:
                    self.after(0, lambda: (
                        self.render_status.configure(text=t("render.completedWithErrors", count=render_errors)),
                        self.retry_render_btn.configure(state=tk.NORMAL),
                        messagebox.showwarning(t("common.warning"), t("render.renderErrors", errors=render_errors, path=out_dir)),
                    ))
                else:
                    self.after(0, lambda: (
                        self.render_status.configure(text=t("render.completed")),
                        self.retry_render_btn.configure(state=tk.DISABLED),
                        messagebox.showinfo(t("common.done"), t("render.outputSaved", path=out_dir)),
                    ))
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                _cancel_text = t("render.cancelled")
                is_cancel = _cancel_text in str(e) or isinstance(e, RenderCancelledError)
                error_text = str(e)
                try:
                    log_dir = (os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
                               else os.path.dirname(os.path.abspath(__file__)))
                    with open(os.path.join(log_dir, "render_error.log"), "w", encoding="utf-8") as ef:
                        ef.write(f"{e}\n\n{tb}\n")
                except Exception:
                    pass
                if is_cancel:
                    self.after(0, lambda: (
                        self.render_status.configure(text=t("render.cancelled")),
                        self.retry_render_btn.configure(state=tk.NORMAL),
                    ))
                else:
                    self.after(
                        0, lambda detail=error_text:
                        self.render_status.configure(
                            text=t("render.renderError", error=detail)
                        )
                    )
                    self.after(0, lambda: self.retry_render_btn.configure(state=tk.NORMAL))
                    self.after(
                        0, lambda detail=error_text: messagebox.showerror(
                            t("common.error"),
                            t("render.renderErrorDetail", error=detail),
                        )
                    )
            finally:
                def _restore():
                    self.render_btn.configure(state=tk.NORMAL, text=t("render.startAll"))
                    self.cancel_render_btn.configure(state=tk.DISABLED, text=t("render.cancelAll"))
                self.after(0, _restore)

        threading.Thread(target=run, daemon=True).start()

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
        self._start_render(self._last_render_dir, skip_completed=True)

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
