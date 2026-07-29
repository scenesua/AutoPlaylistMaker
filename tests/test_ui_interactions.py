import os
import sys
import tempfile
import time
import wave
import math
import struct
import re
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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

    def test_project_messages_format_name_and_path(self):
        for key in ('project.created', 'project.loaded'):
            rendered = app.t(key, name='Regression', path=r'C:\project')
            self.assertIn('Regression', rendered)
            self.assertIn(r'C:\project', rendered)
            self.assertNotIn('{name}', rendered)
            self.assertNotIn('{path}', rendered)

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

    def test_repeat_editor_is_owned_by_effects_and_normalizes_on_commit(self):
        design = self.application.stages[4]
        render = self.application.stages[5]
        design.loop_video_var.set(True)
        design.loop_mode_var.set('count')
        design.loop_count_var.set('')
        design._commit_repeat_fields()
        self.assertEqual(design.loop_count_var.get(), '1')
        design.loop_count_var.set('5')
        self.assertIs(render.loop_count_var, design.loop_count_var)
        self.assertEqual(render._get_repeat_plan(1200).repeat_count, 5)

        design.loop_mode_var.set('target')
        design.loop_target_h_var.set('0')
        design.loop_target_m_var.set('90')
        design.loop_target_s_var.set('120')
        design._commit_repeat_fields()
        self.assertEqual(
            (
                design.loop_target_h_var.get(),
                design.loop_target_m_var.get(),
                design.loop_target_s_var.get(),
            ),
            ('1', '32', '0'),
        )
        plan = render._get_repeat_plan(1200)
        self.assertEqual(plan.repeat_count, 5)
        self.assertEqual(plan.output_seconds, 6000)

    def test_preview_and_output_canvas_settings_stay_linked(self):
        design = self.application.stages[4]
        render = self.application.stages[5]
        render.resolution.set('portrait')
        render.fps_var.set('30')
        self.assertEqual(design.resolution.get(), 'portrait')
        self.assertEqual(design.fps_var.get(), '30')
        design.resolution.set('square')
        design.custom_width_var.set('1440')
        self.assertEqual(render.resolution.get(), 'square')
        self.assertEqual(render.custom_width_var.get(), '1440')

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

        self.assertIsNotNone(stage._live_renderer)
        self.assertTrue(os.path.isfile(stage._preview_mixed_audio_path))
        self.assertGreater(stage._live_duration, 0)
        self.assertTrue(stage._scrub_playing)
        self.assertNotIn(
            'NoneType', stage._preview_status_label.cget('text')
        )

    def test_stage4_preview_is_left_and_effect_reset_is_scoped(self):
        stage = self.application.stages[4]
        self.application.show_stage(4)
        self.application.root.update()
        panes = [str(item) for item in stage.main_pane.panes()]
        self.assertEqual(panes[0], str(stage.preview_panel))
        self.assertEqual(panes[1], str(stage.effects_panel))
        self.assertEqual(stage.active_effect_ids, [])

        self.assertTrue(stage._add_effect("visualizer"))
        stage.viz_sensitivity.set(2.4)
        stage.effect_cards["visualizer"].sections[1].reset_button.invoke()
        self.assertAlmostEqual(stage.viz_sensitivity.get(), 1.0)
        self.assertEqual(stage.viz_type.get(), "eq_bars")

    def test_effect_and_ambient_plain_state_is_copied(self):
        from ui_state import capture_pages, restore_pages

        stage = self.application.stages[4]
        stage._add_effect("logo")
        stage.ambient_tracks = [{
            "filepath": "missing.wav", "enabled": False,
            "volume_db": -9.0, "pan": .25, "width": 1.2,
        }]
        state = capture_pages([stage])
        stage.active_effect_ids.clear()
        stage.ambient_tracks[0]["volume_db"] = 0
        restore_pages([stage], state)
        self.assertEqual(stage.active_effect_ids, ["logo"])
        self.assertEqual(stage.ambient_tracks[0]["volume_db"], -9.0)
        self.assertFalse(stage.ambient_tracks[0]["enabled"])

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
        self.assertEqual(stage.active_effect_ids, ["visualizer"])
        self.assertAlmostEqual(stage.music_master_db.get(), -6.0)
        self.assertTrue(stage.normalize_tracks.get())
        self.assertAlmostEqual(stage.target_lufs.get(), -15.0)
        self.assertEqual(len(stage.ambient_tracks), 1)

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
            patch.object(sys, "argv", [sys.argv[0], "--launcher-splash"]),
            patch.object(app, "SplashScreen", return_value=loading),
        ):
            self.assertIs(app._create_startup_splash(), loading)


if __name__ == '__main__':
    unittest.main()
