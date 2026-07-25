import os
import sys
import tempfile
import time
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import app
from font_combo import SearchableFontComboBox
from project import Project


class UIInteractionTests(unittest.TestCase):
    def setUp(self):
        app._Project = Project
        app._np = np
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
        self.assertIn(
            '새 그룹을 생성',
            stage._empty_group_drop_hint.cget('text'),
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
        stage = self.application.stages[4]
        stage.text_font_family_var.set('Arial')
        stage.custom_text_var.set('복원 테스트')
        stage.viz_type.set('원형')
        stage.viz_sensitivity.set(1.7)
        stage.resolution.set('정사각 1080x1080')
        stage.video_codec_var.set('CPU (libx264)')
        stage.loop_video_var.set(True)
        stage.loop_mode_var.set('목표 재생시간')
        stage.loop_target_h_var.set('2')
        stage._last_render_dir = os.path.join(tempfile.gettempdir(), 'renders')
        self.application.show_stage(4)
        state = self.application.collect_project_state()

        stage.text_font_family_var.set('Courier New')
        stage.custom_text_var.set('')
        stage.viz_type.set('사용 안 함')
        stage.resolution.set('720p')
        stage.loop_target_h_var.set('0')
        stage._last_render_dir = None
        self.application.restore_project_state(state)

        self.assertEqual(self.application.current_stage, 4)
        self.assertEqual(stage.text_font_family_var.get(), 'Arial')
        self.assertEqual(stage.custom_text_var.get(), '복원 테스트')
        self.assertEqual(stage.viz_type.get(), '원형')
        self.assertAlmostEqual(stage.viz_sensitivity.get(), 1.7)
        self.assertEqual(stage.resolution.get(), '정사각 1080x1080')
        self.assertEqual(stage.loop_target_h_var.get(), '2')
        self.assertTrue(stage._last_render_dir.endswith('renders'))
        stage.resolution.set('사용자 지정')
        stage.custom_width_var.set('1001')
        stage.custom_height_var.set('777')
        self.assertEqual(stage._selected_resolution(), (1000, 776))

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


if __name__ == '__main__':
    unittest.main()
