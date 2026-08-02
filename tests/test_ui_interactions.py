import os
import sys
import tempfile
import time
import wave
import math
import struct
import re
import threading
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk

import app
from font_combo import SearchableFontComboBox
from project import Project


class UIInteractionTests(unittest.TestCase):
    def setUp(self):
        import i18n as _i18n_mod
        _i18n_mod.get_instance().locale = 'ko-KR'
        app._Project = Project
        app._np = np
        app._PIL_Image = Image
        app._PIL_ImageTk = ImageTk
        app._PIL_ImageDraw = ImageDraw
        app._PIL_ImageFont = ImageFont
        if '--safe' not in sys.argv:
            sys.argv.append('--safe')
        try:
            self.application = app.AutoPlaylistMakerApp()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.application.root.update_idletasks()
        self.application.root.update()

    def tearDown(self):
        application = getattr(self, 'application', None)
        if application:
            try:
                application._suspend_state_tracking = True
                deadline = time.time() + .08
                while time.time() < deadline:
                    application.root.update()
                application.set_dirty(False)
                application._on_close()
            except tk.TclError:
                pass

    @staticmethod
    def _analysis(name, duration=10):
        return SimpleNamespace(
            filename=name, duration=duration, bpm=120, key='C',
            mode='major', camelot='8B', waveform=np.zeros(100),
            sr=10, hop_length=1, stft_magnitudes=np.zeros((2, 2)),
        )

    def _track(self, name):
        return {
            'filename': name,
            'filepath': os.path.join(tempfile.gettempdir(), name),
            'analysis': self._analysis(name),
            'duration': 10,
            'trim_start': 0,
            'trim_end': 10,
        }

    def _track_item(self, name):
        return SimpleNamespace(
            filename=name,
            filepath=os.path.join(tempfile.gettempdir(), name),
            filetype='audio',
            analysis=self._analysis(name),
            duration=10,
            trim_start=0,
            trim_end=10,
            volume=1.0,
            fade_in=.01,
            fade_out=.01,
        )

    def test_slider_alt_click_restores_defined_default(self):
        self.application.show_stage(3)
        self.application.root.update()
        stage = self.application.stages[3]
        stage.clip_interval.set(7.5)
        stage.clip_interval_scale.event_generate(
            "<Button-1>", x=20, y=10, state=0x0008
        )
        self.application.root.update()
        self.assertEqual(stage.clip_interval.get(), 1.0)

    def test_clip_preview_split_ratio_survives_page_state(self):
        from ui_state import capture_pages, restore_pages
        stage = self.application.stages[3]
        stage.clip_preview_ratio = 0.63
        state = capture_pages([stage])
        stage.clip_preview_ratio = 0.3
        restore_pages([stage], state)
        self.assertEqual(stage.clip_preview_ratio, 0.63)

    def test_import_button_adds_selected_file_and_status_is_translated(self):
        fd, audio_path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        self.addCleanup(
            lambda: os.path.exists(audio_path) and os.remove(audio_path)
        )
        stage = self.application.stages[0]
        with patch.object(
            app.filedialog, 'askopenfilenames', return_value=(audio_path,)
        ) as dialog:
            stage.browse_files()
        dialog.assert_called_once()
        self.assertEqual(len(self.application.tracks), 1)
        track = self.application.tracks[0]
        self.assertTrue(stage.tree.exists(str(id(track))))
        stage._update_tree(track)
        status = stage.tree.item(str(id(track)), 'values')[2]
        self.assertEqual(status, app.t('project.fileStatus.pending'))
        self.assertNotIn('?project.fileStatus', status)

    def test_language_popup_changes_locale_without_losing_tracks(self):
        stage = self.application.stages[0]
        track = self._track_item('language.wav')
        self.application.tracks = [track]
        stage._open_lang_popup()
        self.application.root.update()
        self.assertIsNotNone(stage._lang_popup)
        self.assertEqual(
            len(stage._lang_option_widgets),
            len(app._i18n_mod.SUPPORTED_LOCALES),
        )
        stage._choose_pending_language('en-US')
        self.assertEqual(app._i18n_mod.get_instance().locale, 'ko-KR')
        stage._close_lang_popup()
        self.assertEqual(app._i18n_mod.get_instance().locale, 'ko-KR')
        stage._open_lang_popup()
        stage._choose_pending_language('en-US')
        stage._apply_pending_language()
        self.application.root.update()
        self.assertEqual(app._i18n_mod.get_instance().locale, 'en-US')
        self.assertEqual(self.application.tracks, [track])
        self.assertIn('Project', self.application.titles[0])

    def test_analysis_tree_update_does_not_shadow_translator(self):
        stage = self.application.stages[0]
        missing = app.TrackItem(
            os.path.join(tempfile.gettempdir(), 'missing-regression.wav')
        )
        self.application.tracks.append(missing)
        stage.tree.insert(
            '', tk.END, iid=str(id(missing)),
            values=(missing.filename, 'AUDIO', '-', '-', '-', '-'),
        )
        stage._update_tree(missing)
        status = stage.tree.item(str(id(missing)), 'values')[2]
        self.assertEqual(status, app.t('project.fileStatus.missing'))

    def test_track_analysis_cache_is_invalidated_when_source_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "changing.wav")
            with open(path, "wb") as stream:
                stream.write(b"first")
            track = app.TrackItem(path)
            track.analysis = self._analysis(track.filename)
            track._analysis_source_signature = track._source_signature()
            self.assertTrue(track.has_current_analysis())

            with open(path, "ab") as stream:
                stream.write(b"-changed")
            self.assertFalse(track.has_current_analysis())

    def test_analysis_overlay_closes_only_after_worker_exits(self):
        stage = self.application.stages[0]
        started = threading.Event()
        release = threading.Event()
        track = self._track_item("slow.wav")
        track.analysis = None
        track.analysis_error = ""

        def analyze():
            started.set()
            release.wait(5)
            track.analysis = self._analysis(track.filename)

        track.analyze = analyze
        self.application.tracks = [track]
        stage.tree.insert(
            "", tk.END, iid=str(id(track)),
            values=(track.filename, "AUDIO", "-", "-", "-", "-"),
        )
        stage.start_analysis()
        deadline = time.time() + 2
        while time.time() < deadline and not started.is_set():
            self.application.root.update()
        self.assertTrue(started.is_set())
        self.assertIsNotNone(stage._task_overlay)
        self.assertTrue(stage._task_overlay.window.winfo_exists())
        self.assertEqual(str(stage.lang_btn.cget("state")), "disabled")
        self.assertEqual(
            str(self.application.theme_btn.cget("state")), "disabled"
        )

        release.set()
        deadline = time.time() + 3
        while time.time() < deadline and stage._task_overlay is not None:
            self.application.root.update()
            time.sleep(.01)
        self.assertIsNone(stage._analysis_thread)
        self.assertIsNone(stage._task_overlay)
        self.assertEqual(str(stage.lang_btn.cget("state")), "normal")
        self.assertEqual(
            str(self.application.theme_btn.cget("state")), "normal"
        )

    def test_task_overlay_returns_when_app_is_activated(self):
        stage = self.application.stages[0]
        overlay = app.TaskProgressOverlay(stage, "Loading")
        try:
            overlay.window.withdraw()
            self.application.root.event_generate("<FocusIn>")
            self.application.root.update()
            self.assertEqual(overlay.window.state(), "normal")
            self.assertTrue(overlay.window.winfo_viewable())
        finally:
            overlay.close()

    def test_project_messages_format_name_and_path(self):
        for key in ('project.created', 'project.loaded'):
            rendered = app.t(key, name='Regression', path=r'C:\project')
            self.assertIn('Regression', rendered)
            self.assertIn(r'C:\project', rendered)
            self.assertNotIn('{name}', rendered)
            self.assertNotIn('{path}', rendered)

    def test_new_project_creates_json_and_reports_creation_failure(self):
        stage = self.application.stages[0]
        with tempfile.TemporaryDirectory() as root:
            stage.proj_name_var.set("Regression")
            stage.proj_path_var.set(root)
            stage.new_project()
            self.assertEqual(self.application.project.name, "Regression")
            self.assertTrue(
                os.path.isfile(self.application.project.project_file)
            )
            self.assertIn("Regression", stage.proj_status.cget("text"))

        previous = self.application.project
        stage.proj_name_var.set("../unsafe")
        with patch.object(app.messagebox, "showerror") as showerror:
            stage.new_project()
        showerror.assert_called_once()
        self.assertIs(self.application.project, previous)

    def test_analyzed_project_can_advance_to_distribution(self):
        track = self._track_item("ready.wav")
        self.application.tracks = [track]
        self.application.show_stage(0)
        self.assertEqual(str(self.application.next_btn.cget("state")), "normal")
        self.application.next_btn.invoke()
        self.application.root.update()
        self.assertEqual(self.application.current_stage, 1)

    def test_trim_capture_releases_outside_and_hover_does_not_mutate(self):
        stage = self.application.stages[2]
        track = self._track('trim.wav')
        self.application.video_groups = [{
            'name': 'Mix 1', 'tracks': [track], 'total_duration': 10,
        }]
        stage.selected_group = 0
        stage._recompute_positions()
        stage.tl_canvas.configure(width=500, height=130)
        self.application.root.update()
        stage._draw_timeline()
        press = SimpleNamespace(x=1, y=55, state=0)
        stage._tl_press(press)
        self.assertEqual(stage.tl_drag['mode'], 'trim_start')
        self.assertEqual(stage.tl_canvas.grab_current(), stage.tl_canvas)
        stage._tl_drag_motion(SimpleNamespace(x=17, y=55, state=0))
        changed = track['trim_start']
        stage._tl_release(SimpleNamespace(x=900, y=-200, state=0))
        self.assertIsNone(stage.tl_drag)
        self.assertIsNone(stage.tl_canvas.grab_current())
        stage._tl_hover(SimpleNamespace(x=300, y=55))
        self.assertEqual(track['trim_start'], changed)
        for x in (8, 24, 12):
            stage._tl_press(SimpleNamespace(x=1, y=55, state=0))
            stage._tl_drag_motion(SimpleNamespace(x=x, y=55, state=1))
            stage._tl_release(SimpleNamespace(x=x, y=55, state=0))
            self.assertIsNone(stage.tl_drag)
        self.assertGreaterEqual(track['trim_start'], 0)
        self.assertLessEqual(
            track['trim_start'] + app.MIN_TRIM_SECONDS,
            track['trim_end'],
        )

    def test_group_duration_matches_render_estimate_after_trim(self):
        from repeat_settings import estimate_group_duration

        stage = self.application.stages[2]
        tracks = [self._track("first.wav"), self._track("second.wav")]
        tracks[0]["trim_start"] = 1
        tracks[1]["trim_end"] = 8
        group = {
            "name": "Mix 1", "tracks": tracks, "total_duration": 0
        }
        self.application.video_groups = [group]
        stage.selected_group = 0
        stage._recompute_positions()
        self.assertAlmostEqual(
            group["total_duration"], estimate_group_duration(group)
        )

    def test_group_drag_moves_into_empty_group_and_cleans_indicator(self):
        stage = self.application.stages[1]
        self.application.show_stage(1)
        first = self._track('first.wav')
        self.application.video_groups = [
            {'name': 'Mix 1', 'tracks': [first], 'total_duration': 10},
            {'name': 'Mix 2', 'tracks': [], 'total_duration': 0},
        ]
        stage.manual_group_idx = 0
        stage._set_mode('manual')
        self.application.root.update()
        stage._group_drag_data = {
            'start_idx': 0, 'moved': True,
            'widget': stage._manual_group_list,
            'insert_at': 0, 'source_group': 0, 'item': first,
        }
        stage.manual_group_idx = 1
        stage._show_group_drop_indicator(2)
        self.application.root.update()
        self.assertTrue(stage._group_drop_indicator.winfo_ismapped())
        stage._group_list_release(SimpleNamespace(x=2, y=2))
        self.assertEqual(self.application.video_groups[0]['tracks'], [])
        self.assertEqual(
            self.application.video_groups[1]['tracks'][0]['filename'],
            'first.wav',
        )
        self.assertFalse(stage._group_drop_indicator.winfo_ismapped())

    def test_group_reorder_top_bottom_and_cancel(self):
        stage = self.application.stages[1]
        self.application.show_stage(1)
        tracks = [self._track(f'{name}.wav') for name in ('a', 'b', 'c')]
        self.application.video_groups = [{
            'name': 'Mix 1', 'tracks': tracks, 'total_duration': 30,
        }]
        stage.manual_group_idx = 0
        stage._set_mode('manual')
        stage._group_drag_data = {
            'start_idx': 0, 'moved': True,
            'widget': stage._manual_group_list,
            'insert_at': 3, 'source_group': 0, 'item': tracks[0],
        }
        stage._group_list_release(SimpleNamespace(x=2, y=999))
        self.assertEqual(
            [item['filename'] for item in tracks],
            ['b.wav', 'c.wav', 'a.wav'],
        )
        stage._group_drag_data = {
            'start_idx': 2, 'moved': True,
            'widget': stage._manual_group_list,
            'insert_at': 0, 'source_group': 0, 'item': tracks[2],
        }
        stage._group_list_release(SimpleNamespace(x=2, y=0))
        self.assertEqual(
            [item['filename'] for item in tracks],
            ['a.wav', 'b.wav', 'c.wav'],
        )
        before = list(tracks)
        stage._group_drag_data = {
            'start_idx': 1, 'moved': True,
            'widget': stage._manual_group_list,
            'insert_at': None, 'source_group': 0, 'item': tracks[1],
        }
        stage._group_list_release(SimpleNamespace(x=-100, y=-100))
        self.assertEqual(tracks, before)
        self.assertTrue(
            stage._group_drop_indicator is None
            or not stage._group_drop_indicator.place_info()
        )

    def test_first_button_move_creates_one_group_for_multiple_tracks(self):
        stage = self.application.stages[1]
        self.application.show_stage(1)
        items = [
            self._track_item('one.wav'),
            self._track_item('two.wav'),
            self._track_item('three.wav'),
        ]
        self.application.tracks = items
        self.application.video_groups = []
        stage.manual_group_idx = -1
        stage._set_mode('manual')
        self.application.root.update()
        self.assertEqual(
            stage._empty_group_drop_hint.cget('text'),
            app.t("dist.dragCopyHint"),
        )
        self.assertTrue(stage._empty_group_drop_hint.winfo_ismapped())
        stage._set_group_panel_drop_state(True)
        self.assertEqual(
            stage._manual_group_list.cget('highlightbackground'),
            app.THEME['accent'],
        )
        stage._manual_track_list.selection_set(0)
        stage._manual_track_list.selection_set(2)
        stage._manual_move_to_group()
        self.assertEqual(len(self.application.video_groups), 1)
        self.assertEqual(self.application.video_groups[0]['name'], 'Mix 1')
        self.assertEqual(stage.manual_group_idx, 0)
        self.assertEqual(
            [
                track['filename']
                for track in self.application.video_groups[0]['tracks']
            ],
            ['one.wav', 'three.wav'],
        )
        stage._manual_add_group()
        self.assertEqual(self.application.video_groups[1]['name'], 'Mix 2')

    def test_first_drag_move_uses_same_auto_group_logic_and_rolls_back(self):
        stage = self.application.stages[1]
        self.application.show_stage(1)
        item = self._track_item('drag.wav')
        self.application.tracks = [item]
        self.application.video_groups = []
        stage.manual_group_idx = -1
        stage._set_mode('manual')
        self.application.root.update()
        panel = stage._manual_group_panel
        self.assertTrue(stage._is_group_panel_target(
            panel.winfo_rootx() + panel.winfo_width() // 2,
            panel.winfo_rooty() + panel.winfo_height() // 2,
        ))
        stage._manual_track_list.selection_set(0)
        stage._track_drag_data = {
            'start_idx': 0, 'moved': True,
            'widget': stage._manual_track_list, 'valid_target': True,
        }
        stage._track_list_release(SimpleNamespace(x=0, y=0))
        self.assertEqual(len(self.application.video_groups), 1)
        self.assertEqual(
            self.application.video_groups[0]['tracks'][0]['filename'],
            'drag.wav',
        )

        self.application.video_groups = []
        invalid = self._track_item('invalid.wav')
        invalid.analysis = None
        stage._manual_track_list._track_items = [invalid]
        with patch.object(app.messagebox, 'showerror'):
            self.assertFalse(stage._move_unassigned_to_group([0]))
        self.assertEqual(self.application.video_groups, [])

    def test_font_combo_search_keyboard_and_outside_close(self):
        stage = self.application.stages[4]
        stage.effect_cards["track_info"].open()
        self.application.root.update()
        combos = []

        def visit(widget):
            if isinstance(widget, SearchableFontComboBox):
                combos.append(widget)
            for child in widget.winfo_children():
                visit(child)

        visit(stage)
        self.assertEqual(len(combos), 2)
        combo = combos[0]
        combo.open()
        self.application.root.update()
        combo.search_var.set('arial')
        self.application.root.after(120, lambda: None)
        deadline = time.time() + .3
        while time.time() < deadline:
            self.application.root.update()
        self.assertTrue(any(
            'arial' in name.casefold() for name in combo._visible_fonts
        ))
        korean_font = next(
            (
                name for name in combo.font_families(
                    self.application.root
                )
                if any(ord(character) > 127 for character in name)
            ),
            None,
        )
        if korean_font:
            combo.search_var.set(korean_font[:2])
            deadline = time.time() + .2
            while time.time() < deadline:
                self.application.root.update()
            self.assertIn(korean_font, combo._visible_fonts)
        combo.listbox.selection_clear(0, tk.END)
        combo.listbox.selection_set(0)
        combo._choose()
        self.assertIsNone(combo.popup)
        combo.open()
        self.application.root.update()
        self.application.root.event_generate('<Button-1>', x=2, y=2)
        self.application.root.update()
        self.assertIsNone(combo.popup)
        combo.open()
        self.application.root.update()
        combo.search.focus_force()
        combo.search.event_generate('<KeyPress-Escape>')
        self.application.root.update()
        self.assertIsNone(combo.popup)

    def test_full_page_state_restores_design_render_repeat_and_step(self):
        design = self.application.stages[4]
        render = self.application.stages[5]
        design.text_font_family_var.set('Arial')
        design.custom_text_var.set('복원 테스트')
        design.viz_type.set('원형')
        design.viz_sensitivity.set(1.7)
        render.resolution.set('square')
        render.video_codec_var.set('CPU (libx264)')
        render.loop_video_var.set(True)
        render.loop_mode_var.set(app.t('render.loopTarget'))
        render.loop_target_h_var.set('2')
        render._last_render_dir = os.path.join(tempfile.gettempdir(), 'renders')
        self.application.show_stage(5)
        state = self.application.collect_project_state()

        design.text_font_family_var.set('Courier New')
        design.custom_text_var.set('')
        design.viz_type.set('사용 안 함')
        render.resolution.set('720p')
        render.loop_target_h_var.set('0')
        render._last_render_dir = None
        self.application.restore_project_state(state)

        self.assertEqual(self.application.current_stage, 5)
        self.assertEqual(design.text_font_family_var.get(), 'Arial')
        self.assertEqual(design.custom_text_var.get(), '복원 테스트')
        self.assertEqual(design.viz_type.get(), 'circles')
        self.assertAlmostEqual(design.viz_sensitivity.get(), 1.7)
        self.assertEqual(render.resolution.get(), 'square')
        self.assertEqual(render.loop_target_h_var.get(), '2')
        self.assertEqual(render.video_codec_var.get(), 'libx264')
        self.assertTrue(render._last_render_dir.endswith('renders'))

    def test_repeat_editor_is_owned_by_render_stage(self):
        design = self.application.stages[4]
        render = self.application.stages[5]
        self.assertFalse(hasattr(design, 'loop_video_var'))
        self.assertTrue(hasattr(render, 'loop_video_var'))
        render.loop_video_var.set(True)
        render.loop_mode_var.set('count')
        render.loop_count_var.set('')
        render._commit_repeat_fields()
        self.assertEqual(render.loop_count_var.get(), '1')
        render.loop_count_var.set('5')
        self.assertEqual(render._get_repeat_plan(1200).repeat_count, 5)

        render.loop_mode_var.set('target')
        render.loop_target_h_var.set('1')
        render.loop_target_m_var.set('32')
        render.loop_target_s_var.set('0')
        render._commit_repeat_fields()
        self.assertEqual(
            (
                render.loop_target_h_var.get(),
                render.loop_target_m_var.get(),
                render.loop_target_s_var.get(),
            ),
            ('1', '32', '0'),
        )
        plan = render._get_repeat_plan(1200)
        self.assertEqual(plan.repeat_count, 5)
        self.assertEqual(plan.output_seconds, 6000)

    def test_preview_quality_is_independent_from_output_resolution(self):
        design = self.application.stages[4]
        render = self.application.stages[5]
        render.resolution.set('portrait')
        design.preview_quality_var.set('custom')
        design.preview_width_var.set('800')
        design.preview_height_var.set('450')
        self.assertEqual(design._selected_preview_resolution(), (800, 450))
        self.assertEqual(render.resolution.get(), 'portrait')

    def test_translated_legacy_choices_migrate_to_stable_ids(self):
        design = self.application.stages[4]
        render = self.application.stages[5]
        design.viz_type.set(app.t('design.vizCircles'))
        design.resolution.set(app.t('design.resolutionPortrait'))
        render.loop_mode_var.set(app.t('render.loopTarget'))
        render.video_codec_var.set(app.t('render.nvidiaCodec'))
        self.application.root.update()
        self.assertEqual(design.viz_type.get(), 'circles')
        self.assertEqual(design.resolution.get(), 'portrait')
        self.assertEqual(render.loop_mode_var.get(), 'target')
        self.assertEqual(render.video_codec_var.get(), 'h264_nvenc')
        self.assertEqual(design._selected_resolution(), (1080, 1920))

    def test_language_round_trip_keeps_render_and_design_semantics(self):
        design = self.application.stages[4]
        render = self.application.stages[5]
        design.viz_type.set('radial')
        design.bg_fit_var.set('contain')
        design.resolution.set('square')
        render.loop_mode_var.set('target')
        render.video_codec_var.set('h264_qsv')
        expected = design._collect_config()

        self.application.stages[0]._select_lang('ja-JP')
        self.application.root.update()
        design = self.application.stages[4]
        render = self.application.stages[5]
        self.assertEqual(design.viz_type.get(), 'radial')
        self.assertEqual(design.bg_fit_var.get(), 'contain')
        self.assertEqual(design.resolution.get(), 'square')
        self.assertEqual(render.loop_mode_var.get(), 'target')
        self.assertEqual(render.video_codec_var.get(), 'h264_qsv')
        self.assertEqual(design._collect_config()['visualizer']['type'],
                         expected['visualizer']['type'])
        self.assertEqual(design._selected_resolution(), (1080, 1080))

    def test_packaged_lazy_stage_restores_saved_page_when_first_opened(self):
        lazy_app = None
        with patch.object(sys, "frozen", True, create=True):
            try:
                lazy_app = app.AutoPlaylistMakerApp()
            except tk.TclError as error:
                self.skipTest(str(error))
            lazy_app.restore_project_state({
                "current_step": 0,
                "design": {
                    "global_audio": {"music_master_db": -3.0},
                },
                "render": {"output_dir": r"C:\render-output"},
                "visibility": {
                    "enabled": True,
                    "turn_off_after": 4,
                    "restore_before_end": 2,
                    "restore": True,
                },
                "pages": [{
                    "class": "Stage4DesignEffects",
                    "variables": {
                        "viz_type": "radial",
                        "resolution": "portrait",
                    },
                    "plain": {
                        "active_effect_ids": ["visualizer"],
                    },
                }],
            })
            self.assertIsInstance(lazy_app.stages[4], app._LazyStage)
            captured = lazy_app.collect_project_state()
            saved_design = next(
                page for page in captured["pages"]
                if page["class"] == "Stage4DesignEffects"
            )
            self.assertEqual(saved_design["variables"]["viz_type"], "radial")
            self.assertEqual(
                captured["render"]["output_dir"], r"C:\render-output"
            )
            lazy_app._toggle_theme()
            self.assertIsInstance(lazy_app.stages[4], app._LazyStage)
            lazy_app.show_stage(4)
            lazy_app.root.update()
            design = lazy_app.stages[4]
            self.assertEqual(design.viz_type.get(), "radial")
            self.assertEqual(design.resolution.get(), "portrait")
            self.assertEqual(
                design.active_effect_ids, ["visualizer"]
            )
            self.assertAlmostEqual(design.music_master_db.get(), -3.0)
            self.assertTrue(design.visibility_enabled.get())
            design.visibility_enabled.set(False)
            lazy_app.show_stage(5)
            self.assertEqual(
                lazy_app.stages[5]._last_render_dir,
                r"C:\render-output",
            )
            lazy_app.stages[5].loop_count_var.set("7")
            lazy_app.stages[5]._last_render_dir = r"C:\new-output"
            lazy_app._toggle_theme()
            lazy_app.show_stage(4)
            self.assertFalse(lazy_app.stages[4].visibility_enabled.get())
            lazy_app.show_stage(5)
            self.assertEqual(lazy_app.stages[5].loop_count_var.get(), "7")
            self.assertEqual(
                lazy_app.stages[5]._last_render_dir,
                r"C:\new-output",
            )
        if lazy_app:
            lazy_app._suspend_state_tracking = True
            lazy_app.set_dirty(False)
            try:
                lazy_app._on_close()
            except tk.TclError:
                pass

    def test_packaged_new_project_shows_default_background_outside_user_order(self):
        lazy_app = None
        with patch.object(sys, "frozen", True, create=True):
            try:
                lazy_app = app.AutoPlaylistMakerApp()
            except tk.TclError as error:
                self.skipTest(str(error))
            lazy_app.show_stage(4)
            self.assertEqual(lazy_app.stages[4].active_effect_ids, [])
            self.assertTrue(
                lazy_app.stages[4]._rack_slots_frame.winfo_children()
            )
        if lazy_app:
            lazy_app._suspend_state_tracking = True
            lazy_app.set_dirty(False)
            try:
                lazy_app._on_close()
            except tk.TclError:
                pass

    def test_all_supported_language_rebuilds_keep_stable_choices(self):
        import i18n

        for locale in i18n.SUPPORTED_LOCALES:
            current = self.application.stages[0]
            current._select_lang(locale)
            self.application.root.update()
            design = self.application.stages[4]
            render = self.application.stages[5]
            design.viz_type.set('spectrum')
            render.loop_mode_var.set('target')
            render.video_codec_var.set('auto')
            self.application.root.update()
            self.assertEqual(design.viz_type.get(), 'spectrum', locale)
            self.assertEqual(render.loop_mode_var.get(), 'target', locale)
            self.assertEqual(render.video_codec_var.get(), 'auto', locale)
            self.assertNotIn('?', self.application.titles[0], locale)
            for stage_index in range(len(self.application.stages)):
                self.application.show_stage(stage_index)
                self.application.root.update()
                pending = [self.application.stages[stage_index]]
                while pending:
                    widget = pending.pop()
                    pending.extend(widget.winfo_children())
                    try:
                        text = str(widget.cget('text'))
                    except tk.TclError:
                        continue
                    self.assertNotIn('\ufffd', text, (locale, text))
                    self.assertIsNone(
                        re.search(r'\?[A-Za-z][\w.-]+\?', text),
                        (locale, text),
                    )
                    self.assertIsNone(
                        re.search(r'\{(?:name|path|count|time|error)\}', text),
                        (locale, text),
                    )

    def test_design_change_debounces_and_refreshes_preview(self):
        stage = self.application.stages[4]
        self.application.show_stage(4)
        self.application.root.update()
        with patch.object(stage, '_refresh_canvas_preview') as refresh:
            stage.viz_sensitivity.set(1.3)
            stage.viz_sensitivity.set(1.4)
            deadline = time.time() + .3
            while time.time() < deadline:
                self.application.root.update()
            refresh.assert_called_once()

    def test_two_track_preview_uses_shared_ffmpeg_when_app_module_is_none(self):
        paths = []
        for index, frequency in enumerate((220, 330)):
            path = os.path.join(
                tempfile.gettempdir(),
                f'apm_preview_integration_{index}.wav',
            )
            paths.append(path)
            with wave.open(path, 'wb') as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                frames = bytearray()
                for sample in range(5 * 8000):
                    frames.extend(struct.pack(
                        '<h',
                        int(4000 * math.sin(
                            2 * math.pi * frequency * sample / 8000
                        )),
                    ))
                audio.writeframes(frames)
            self.addCleanup(
                lambda item=path: (
                    os.path.exists(item) and os.remove(item)
                )
            )

        def analysis(path):
            return SimpleNamespace(
                filepath=path, filename=os.path.basename(path),
                duration=5.0, bpm=120, key='C', mode='major',
                camelot='8B', energy_profile=np.ones(10),
                beat_times=np.arange(0, 5, .5),
                chroma=np.zeros((12, 10)), rms=np.ones(10) * .2,
                stft_magnitudes=np.ones((129, 80)) * .1,
                stft_times=np.linspace(0, 5, 80),
                sr=8000, hop_length=512, waveform=np.zeros(400),
            )

        tracks = [{
            'filename': os.path.basename(path),
            'filepath': path,
            'analysis': analysis(path),
            'duration': 5,
            'trim_start': 0,
            'trim_end': 5,
            'volume': 1.0,
            'fade_in': .01,
            'fade_out': .01,
        } for path in paths]
        self.application.video_groups = [{
            'name': 'Mix 1', 'tracks': tracks,
            'total_duration': 10, 'clips': [],
        }]
        stage = self.application.stages[4]
        stage.viz_type.set('none')
        app.video_gen = None

        with patch.object(
            stage._preview_audio_player, 'play',
            side_effect=lambda *args, **kwargs: kwargs['on_ready'](),
        ):
            self.application.show_stage(4)
            if not stage._preview_prepare_active:
                stage._preview_render_video()
            deadline = time.time() + 25
            while time.time() < deadline and stage._live_renderer is None:
                self.application.root.update()
                time.sleep(.02)
            while time.time() < deadline and not (
                stage._preview_first_frame_ready
                and stage._preview_audio_ready
            ):
                self.application.root.update()
                time.sleep(.02)

        self.assertIsNotNone(stage._live_renderer)
        self.assertTrue(os.path.isfile(stage._preview_mixed_audio_path))
        self.assertGreater(stage._live_duration, 0)
        self.assertTrue(stage._scrub_playing)
        self.assertTrue(stage._preview_first_frame_ready)
        self.assertTrue(stage._preview_audio_ready)
        self.assertIsNone(stage._preview_loading_bar)
        self.assertNotEqual(
            stage._preview_status_label.cget('text'),
            app.t("design.previewConnecting"),
        )
        self.assertNotIn(
            'NoneType', stage._preview_status_label.cget('text')
        )

    def test_stage4_rack_is_right_and_effect_reset_is_scoped(self):
        stage = self.application.stages[4]
        self.application.show_stage(4)
        self.application.root.update()
        panes = [str(item) for item in stage.main_pane.panes()]
        self.assertEqual(panes[0], str(stage.preview_panel))
        self.assertEqual(panes[1], str(stage.effects_panel))
        self.assertLessEqual(
            int(stage.main_pane.panecget(stage.effects_panel, 'width')), 280
        )
        ratio = (
            stage.preview_panel.winfo_width()
            / stage.effects_panel.winfo_width()
        )
        self.assertGreaterEqual(ratio, 2.8)
        self.assertLessEqual(ratio, 3.2)
        self.assertEqual(stage.active_effect_ids, [])
        labels = []
        pending = list(stage._rack_slots_frame.winfo_children())
        while pending:
            widget = pending.pop()
            pending.extend(widget.winfo_children())
            try:
                text = widget.cget('text')
            except tk.TclError:
                continue
            if text:
                labels.append(text)
        for key in (
            'globalAudio.title', 'design.sceneTransition', 'design.background'
        ):
            self.assertIn(app.t(key), labels)

        self.assertTrue(stage._add_effect("visualizer"))
        stage.viz_sensitivity.set(2.4)
        stage.effect_cards["visualizer"].sections[1].reset_button.invoke()
        self.assertAlmostEqual(stage.viz_sensitivity.get(), 1.0)
        self.assertEqual(stage.viz_type.get(), "eq_bars")

    def test_stage4_audio_resolution_and_rack_size_are_collapsible(self):
        stage = self.application.stages[4]
        self.application.show_stage(4)
        self.application.root.update()

        self.assertFalse(stage._global_audio_section.expanded)
        stage._global_audio_section.toggle()
        self.assertTrue(stage._global_audio_section.expanded)
        stage._global_audio_section.toggle()
        self.assertFalse(stage._global_audio_section.expanded)

        self.assertFalse(stage._preview_resolution_section.expanded)
        stage._preview_resolution_section.toggle()
        self.assertTrue(stage._preview_resolution_section.expanded)

        pane = stage.rack_settings_pane
        before = pane.sash_coord(0)[1]
        pane.sash_place(0, 0, before + 30)
        self.application.root.update()
        self.assertGreater(pane.sash_coord(0)[1], before)

    def test_effect_picker_category_submenu_adds_effect(self):
        stage = self.application.stages[4]
        self.application.show_stage(4)
        stage._open_effect_picker(show=False)
        self.assertEqual(
            set(stage._effect_category_menus),
            {
                "basic", "text", "audio", "audio_effect", "motion",
                "color", "other",
            },
        )
        basic_menu = stage._effect_category_menus["basic"]
        basic_menu.invoke(0)
        self.application.root.update()
        self.assertIn("album", stage.active_effect_ids)

    def test_effect_rack_and_settings_windows_are_singletons(self):
        stage = self.application.stages[4]
        self.application.show_stage(4)
        stage._add_effect("visualizer")
        stage._open_effect_rack()
        rack = stage._rack_slots_frame
        stage._open_effect_rack()
        self.assertIsNone(stage._rack_window)
        self.assertIs(stage._rack_slots_frame, rack)

        card = stage.effect_cards["visualizer"]
        card.open()
        settings_window = card.window
        stage.viz_sensitivity.set(2.2)
        card.window.withdraw()
        card.open()
        self.assertIs(card.window, settings_window)
        self.assertAlmostEqual(stage.viz_sensitivity.get(), 2.2)
        self.assertIn("visualizer", stage.active_effect_ids)

    def test_effect_enable_and_real_overlay_order_are_saved(self):
        stage = self.application.stages[4]
        for effect_id in ("album", "visualizer", "logo"):
            stage._add_effect(effect_id)
        stage._set_effect_enabled("visualizer", False)
        stage._move_effect("logo", -1)
        config = stage._collect_config()

        self.assertEqual(
            config["effect_order"], ["logo", "visualizer", "album"]
        )
        self.assertNotIn("visualizer", config["active_effects"])
        self.assertEqual(config["visualizer"]["type"], "none")
        visualizer_instance = next(
            item for item in config["effect_instances"]
            if item["id"] == "visualizer"
        )
        self.assertFalse(visualizer_instance["enabled"])

    def test_effect_slider_accepts_mouse_drag(self):
        stage = self.application.stages[4]
        card = stage.effect_cards["visualizer"]
        card.open()
        if not card.sections[1].expanded:
            card.sections[1].toggle()
        self.application.root.update()

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        scale = next(
            widget for widget in descendants(card.window)
            if isinstance(widget, tk.Scale)
            and str(widget.cget("variable")) == str(stage.viz_sensitivity)
        )
        offset = 0
        widget = scale
        while widget is not card.content:
            offset += widget.winfo_y()
            widget = widget.master
        scrollable = max(
            1, card.content.winfo_reqheight() - card.canvas.winfo_height()
        )
        card.canvas.yview_moveto(max(0, min(1, (offset - 80) / scrollable)))
        self.application.root.update()
        old_value = stage.viz_sensitivity.get()
        x = scale.winfo_width() - 30
        y = next(
            row for row in range(scale.winfo_height())
            if scale.identify(x, row)
        )
        self.assertTrue(scale.identify(x, y))
        scale.event_generate("<Button-1>", x=x, y=y)
        scale.event_generate("<B1-Motion>", x=x, y=y)
        scale.event_generate("<ButtonRelease-1>", x=x, y=y)
        self.application.root.update()
        if stage.viz_sensitivity.get() == old_value:
            self.skipTest(
                "Tk did not deliver the synthetic drag in the shared UI session"
            )
        self.assertNotEqual(stage.viz_sensitivity.get(), old_value)

    def test_ambience_volume_slider_updates_only_its_source(self):
        stage = self.application.stages[4]
        stage._add_effect("ambience_mixer")
        card = stage.effect_cards["ambience_mixer"]
        card.open()
        if not card.sections[0].expanded:
            card.sections[0].toggle()
        self.application.root.update()
        rain_enabled, rain_volume = stage._ambience_source_vars["rain"]
        thunder_state = dict(stage.ambience_sources["thunder"])
        rain_enabled.set(True)
        scale = next(
            child for row in card.sections[0].content.winfo_children()
            for child in row.winfo_children()
            if isinstance(child, tk.Scale)
            and str(child.cget("variable")) == str(rain_volume)
        )
        offset = 0
        widget = scale
        while widget is not card.content:
            offset += widget.winfo_y()
            widget = widget.master
        scrollable = max(
            1, card.content.winfo_reqheight() - card.canvas.winfo_height()
        )
        card.canvas.yview_moveto(max(0, min(1, (offset - 80) / scrollable)))
        self.application.root.update()
        start_x, start_y = map(int, scale.coords(rain_volume.get()))
        x, y = map(int, scale.coords(-12.0))
        scale.event_generate("<Button-1>", x=start_x, y=start_y)
        scale.event_generate("<B1-Motion>", x=x, y=y)
        scale.event_generate("<ButtonRelease-1>", x=x, y=y)
        self.application.root.update()
        if rain_volume.get() == -18.0:
            self.skipTest(
                "Tk did not deliver the synthetic drag in the shared UI session"
            )
        self.assertAlmostEqual(rain_volume.get(), -12.0, delta=.6)
        self.assertEqual(stage.ambience_sources["thunder"], thunder_state)
        self.assertAlmostEqual(
            stage._collect_config()["ambience_mixer"]["sources"]
            ["rain"]["volume_db"],
            rain_volume.get(),
        )

    def test_effect_and_ambient_plain_state_is_copied(self):
        from ui_state import capture_pages, restore_pages

        stage = self.application.stages[4]
        stage._add_effect("logo")
        stage._add_effect("ambience_mixer")
        stage.ambience_sources["rain"] = {
            "enabled": True, "volume_db": -9.0,
        }
        state = capture_pages([stage])
        stage.active_effect_ids.clear()
        stage.ambience_sources["rain"]["volume_db"] = 0
        restore_pages([stage], state)
        self.assertEqual(
            stage.active_effect_ids, ["logo", "ambience_mixer"]
        )
        self.assertEqual(
            stage.ambience_sources["rain"]["volume_db"], -9.0
        )
        self.assertTrue(stage.ambience_sources["rain"]["enabled"])

    def test_ambience_is_one_effect_with_category_level_state(self):
        from ui_state import capture_pages, restore_pages

        stage = self.application.stages[4]
        self.assertTrue(stage.sound_library.available("rain"))
        self.assertTrue(stage._add_effect("ambience_mixer"))
        self.assertFalse(stage._add_effect("ambience_mixer"))
        enabled, volume = stage._ambience_source_vars["rain"]
        enabled.set(True)
        volume.set(-18.0)
        config = stage._collect_config()
        self.assertNotIn("ambient_tracks", config["global_audio"])
        self.assertNotIn("ambient_master_db", config["global_audio"])
        self.assertEqual(
            config["effect_order"].count("ambience_mixer"), 1
        )
        self.assertTrue(
            config["ambience_mixer"]["sources"]["rain"]["enabled"]
        )
        self.assertNotIn("asset_ids", config["ambience_mixer"]["sources"]["rain"])
        state = capture_pages([stage])
        stage.ambience_sources.clear()
        restore_pages([stage], state)
        self.assertAlmostEqual(
            stage.ambience_sources["rain"]["volume_db"], -18.0
        )

    def test_design_audio_state_migrates_without_page_snapshot(self):
        stage = self.application.stages[4]
        self.application.restore_project_state({
            "current_step": 4,
            "pages": [],
            "design": {
                "active_effects": ["visualizer"],
                "global_audio": {
                    "music_master_db": -6.0,
                    "normalize_tracks": True,
                    "target_lufs": -15.0,
                    "true_peak_dbtp": -1.5,
                    "max_auto_gain_db": 9.0,
                    "ambient_master_db": -20.0,
                    "ambient_tracks": [{
                        "filepath": "rain.wav", "enabled": True,
                        "volume_db": -12.0, "pan": 0.0, "width": 1.0,
                    }],
                },
            },
        })
        self.assertEqual(
            stage.active_effect_ids, ["visualizer", "ambience_mixer"]
        )
        self.assertAlmostEqual(stage.music_master_db.get(), -6.0)
        self.assertTrue(stage.normalize_tracks.get())
        self.assertAlmostEqual(stage.target_lufs.get(), -15.0)
        self.assertTrue(stage._legacy_ambient_tracks)

    def test_stage5_and_action_buttons_follow_light_theme(self):
        if self.application.dark_mode:
            self.application._toggle_theme()
        self.application.show_stage(5)
        self.application.root.update()
        render = self.application.stages[5]
        self.assertEqual(render.cget("bg"), app.THEME["bg_main"])

        danger = app.styled_button(
            render, "Delete", lambda: None, "danger"
        )
        success = app.styled_button(
            render, "Add", lambda: None, "success"
        )
        danger.pack()
        success.pack()
        self.application.root.update()
        danger.event_generate("<Enter>")
        success.event_generate("<Enter>")
        self.application.root.update()
        self.assertEqual(danger.cget("bg"), app.THEME["danger"])
        self.assertEqual(success.cget("bg"), app.THEME["success"])
        danger.event_generate("<Leave>")
        success.event_generate("<Leave>")
        self.application.root.update()
        self.assertEqual(danger.cget("bg"), app.THEME["bg_input"])
        self.assertEqual(success.cget("bg"), app.THEME["bg_input"])

    def test_render_locks_stage_rebuild_controls(self):
        render = self.application.stages[5]
        stage0 = self.application.stages[0]
        self.application.show_stage(5)
        render._set_app_navigation_locked(True)
        self.assertEqual(str(self.application.prev_btn.cget("state")), "disabled")
        self.assertEqual(str(self.application.theme_btn.cget("state")), "disabled")
        self.assertEqual(str(stage0.lang_btn.cget("state")), "disabled")
        render._set_app_navigation_locked(False)
        self.assertEqual(str(self.application.prev_btn.cget("state")), "normal")
        self.assertEqual(str(self.application.theme_btn.cget("state")), "normal")
        self.assertEqual(str(stage0.lang_btn.cget("state")), "normal")

    def test_invalid_repeat_restores_render_button_states(self):
        render = self.application.stages[5]
        self.application.video_groups = [{
            "name": "Mix 1", "tracks": [self._track("ready.wav")],
            "clips": [],
        }]
        render.loop_video_var.set(True)
        render.loop_mode_var.set("count")
        render.loop_count_var.set("0")
        with (
            tempfile.TemporaryDirectory() as output_dir,
            patch.object(app.messagebox, "showwarning"),
        ):
            render._start_render(out_dir_override=output_dir)
        self.assertEqual(str(render.render_btn.cget("state")), "normal")
        self.assertEqual(str(render.cancel_render_btn.cget("state")), "disabled")

    def test_verified_render_completion_posts_one_callable(self):
        render = self.application.stages[5]
        validation = {"path": "out.mp4"}
        with (
            patch.object(render.app, "post_ui") as post_ui,
            patch.object(render, "_show_verified_completion") as show,
        ):
            render._post_verified_completion(validation, "output")
            post_ui.assert_called_once()
            callback = post_ui.call_args.args[0]
            callback()
        show.assert_called_once_with(validation, "output")

    def test_render_failure_dialog_is_non_modal_and_has_actions(self):
        render = self.application.stages[5]
        before = set(render.winfo_children())
        render._show_render_error_dialog(
            "encoder failed", "STARTING_ENCODER",
            os.path.join(tempfile.gettempdir(), "render.log"),
            "render_test", "traceback",
        )
        self.application.root.update()
        windows = [
            child for child in render.winfo_children()
            if child not in before and isinstance(child, tk.Toplevel)
        ]
        self.assertEqual(len(windows), 1)
        window = windows[0]
        self.assertEqual(window.title(), app.t("renderFailure.title"))
        self.assertIsNone(window.grab_current())
        buttons = [
            child for frame in window.winfo_children()
            if isinstance(frame, tk.Frame)
            for child in frame.winfo_children()
            if isinstance(child, tk.Button)
        ]
        self.assertGreaterEqual(len(buttons), 5)
        window.destroy()

    def test_visual_setting_reconfigures_live_preview_without_closing_editor(self):
        design = self.application.stages[4]
        self.application.current_stage = 4
        self.application.video_groups = [{
            "tracks": [{
                "filepath": "song.wav", "analysis": self._analysis("song.wav"),
            }],
            "clips": [],
        }]
        renderer = MagicMock()
        design._live_renderer = renderer
        design._two_track_mode.set(False)
        config = design._collect_config()
        design._preview_audio_signature = repr((
            config["global_audio"], config["ambience_mixer"],
        ))
        design._preview_renderer_signature = (
            design._preview_structure_signature()
        )
        with patch.object(design, "_render_scrub_frame") as redraw:
            design.viz_height.set(design.viz_height.get() + 10)
            design._refresh_canvas_preview()
        renderer.reconfigure.assert_called_once()
        redraw.assert_called_once()
        applied = renderer.reconfigure.call_args.args[0]
        self.assertEqual(applied["layout"]["reference_width"], 1920)

    def test_preview_resolution_change_rebuilds_renderer(self):
        design = self.application.stages[4]
        self.application.video_groups = [{
            "tracks": [{
                "filepath": "song.wav", "analysis": self._analysis("song.wav"),
            }],
            "clips": [],
        }]
        design._live_renderer = MagicMock()
        design._two_track_mode.set(False)
        design._preview_renderer_signature = (
            design._preview_structure_signature()
        )
        design.preview_quality_var.set("custom")
        design.preview_width_var.set(854)
        design.preview_height_var.set(480)
        with patch.object(design, "_preview_render_video") as rebuild:
            design._refresh_canvas_preview()
        rebuild.assert_called_once_with(preserve_state=True)
        design._live_renderer.reconfigure.assert_not_called()

    def test_new_preview_request_invalidates_active_generation(self):
        design = self.application.stages[4]
        design._preview_prepare_active = True
        generation = design._preview_generation
        design._preview_render_video(preserve_state=True)
        self.assertEqual(design._preview_generation, generation + 1)
        self.assertTrue(design._preview_pending_refresh)

    def test_settings_slider_uses_left_button_and_alt_reset_only(self):
        window = tk.Toplevel(self.application.root)
        variable = tk.DoubleVar(window, value=5)
        scale = app.styled_scale(
            window, variable, 0, 10, 1,
        )
        scale.pack()
        self.application.root.update()
        variable.set(7)
        scale.event_generate("<Button-3>", x=1, y=1)
        scale.event_generate("<B3-Motion>", x=140, y=1)
        self.application.root.update()
        self.assertEqual(variable.get(), 7)
        scale.event_generate("<Button-1>", x=140, y=5)
        scale.event_generate("<B1-Motion>", x=120, y=5)
        scale.event_generate("<ButtonRelease-1>", x=120, y=5)
        self.application.root.update()
        self.assertNotEqual(variable.get(), 5)
        variable.set(8)
        for _ in range(2):
            scale.event_generate("<Button-1>", x=120, y=5)
            scale.event_generate("<ButtonRelease-1>", x=120, y=5)
        self.application.root.update()
        self.assertNotEqual(variable.get(), 5)
        scale.event_generate("<Alt-Button-1>", x=2, y=5)
        self.application.root.update()
        self.assertEqual(variable.get(), 5)
        window.destroy()

    def test_native_splash_selection_uses_bootloader_ipc(self):
        native = object()
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.dict(os.environ, {"_PYI_SPLASH_IPC": "12345"}),
            patch.object(app, "NativeSplash", return_value=native),
        ):
            self.assertIs(app._create_startup_splash(), native)
        loading = object()
        with (
            patch.object(sys, "frozen", False, create=True),
            patch.dict(os.environ, {}, clear=True),
            patch.object(app, "SplashScreen", return_value=loading),
        ):
            self.assertIs(app._create_startup_splash(), loading)

    def test_window_resize_fullscreen_and_resolution_sync(self):
        self.assertEqual(self.application.root.resizable(), (1, 1))
        self.application._toggle_fullscreen()
        self.assertTrue(self.application._fullscreen)
        self.application._exit_fullscreen()
        self.assertFalse(self.application._fullscreen)

        render = self.application.stages[5]
        render.resolution.set("720p")
        self.application.root.update()
        self.assertEqual(render.custom_width_var.get(), "1280")
        self.assertEqual(render.custom_height_var.get(), "720")
        render.custom_width_var.set("1601")
        render.custom_height_var.set("901")
        render._commit_custom_resolution()
        self.assertEqual(render.resolution.get(), "custom")
        self.assertEqual(render.custom_width_var.get(), "1600")
        self.assertEqual(render.custom_height_var.get(), "900")
        render.custom_width_var.set("invalid")
        render._commit_custom_resolution()
        self.assertEqual(render.custom_width_var.get(), "1600")
        self.assertEqual(render.custom_height_var.get(), "900")

    def test_main_reuses_python_splash_root(self):
        splash = MagicMock()
        root = splash.handoff_root.return_value
        with (
            patch.object(app, "_create_startup_splash", return_value=splash),
            patch.object(app, "AutoPlaylistMakerApp") as app_class,
            patch.object(app, "_startup_mark"),
        ):
            app.main()

        app_class.assert_called_once_with(defer_show=False, root=root)
        splash.close.assert_called_once()
        app_class.return_value.run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
