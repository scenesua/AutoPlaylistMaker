import os
import json
import random
import shutil
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

from analyzer import compute_energy_profile
from distributor import distribute_tracks, sequence_score
from project import Project
from render_jobs import RenderJob
from transition import apply_edge_fades
from app import Stage2MusicEdit, _waveform_peaks


class CoreTests(unittest.TestCase):
    def test_waveform_peaks_keep_final_partial_chunk(self):
        peaks = _waveform_peaks(
            np.array([-1.0, 0.5, -0.25, 0.75, 0.2]), max_peaks=2
        )
        self.assertEqual(peaks, [(-1.0, 0.5), (-0.25, 0.75), (0.2, 0.2)])

    def test_music_editor_reuses_analysis_waveform_without_redecoding(self):
        stage = object.__new__(Stage2MusicEdit)
        stage._waveform_cache = {}
        stage._waveform_loading = set()
        stage._track_rects = [{
            'track': {
                'filepath': 'cached.wav',
                'analysis': SimpleNamespace(
                    waveform=np.linspace(-1, 1, 5000),
                    sr=22050,
                ),
            },
        }]
        progress = []
        stage._update_waveform_progress = (
            lambda ready, total: progress.append((ready, total))
        )
        stage._precompute_waveforms()
        self.assertIn('cached.wav', stage._waveform_cache)
        self.assertEqual(progress[-1], (1, 1))

    def test_changed_source_invalidates_analysis_cache(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "song.wav")
            with open(source, "wb") as handle:
                handle.write(b"first")
            cache = os.path.join(root, "cache.npz")
            np.savez_compressed(
                cache,
                waveform=np.ones(8),
                stft_magnitudes=np.ones((4, 3)),
                stft_times=np.arange(3),
            )
            stat = os.stat(source)
            project = Project()
            project.project_dir = root
            project.track_analyses = {
                os.path.abspath(source): {
                    "filepath": source,
                    "filename": "song.wav",
                    "cache_file": "cache.npz",
                    "source_size": stat.st_size,
                    "source_mtime_ns": stat.st_mtime_ns,
                    "analysis_version": 2,
                },
            }
            self.assertIsNotNone(project.get_analysis_for(source))
            with open(source, "ab") as handle:
                handle.write(b"changed")
            self.assertIsNone(project.get_analysis_for(source))

    def test_trim_precision_modifiers(self):
        self.assertAlmostEqual(
            Stage2MusicEdit._snap_drag_delta(0.146, 0), 0.1
        )
        self.assertAlmostEqual(
            Stage2MusicEdit._snap_drag_delta(0.146, 0x0001), 0.15
        )
        self.assertAlmostEqual(
            Stage2MusicEdit._snap_drag_delta(0.1464, 0x20000), 0.146
        )
        self.assertEqual(Stage2MusicEdit._fmt_precise(65.432), "01:05.432")

    def test_render_job_checkpoint_and_cancel(self):
        with tempfile.TemporaryDirectory() as root:
            job = RenderJob(root)
            os.makedirs(job.mix_dir(0))
            with open(job.video_path(0), 'wb') as handle:
                handle.write(b'x' * 2048)
            self.assertTrue(job.is_completed(0))
            self.assertFalse(job.cancelled)
            job.cancel()
            self.assertTrue(job.cancelled)

    def test_energy_keeps_partial_segment(self):
        result = compute_energy_profile(
            np.zeros(10), 10, segment_duration=0.4,
            rms=np.array([1., 2., 3., 4., 5.]), hop_length=2,
        )
        np.testing.assert_allclose(result, [1.5, 3.5, 5.0])

    def test_edge_fades_remove_trim_clicks(self):
        result = apply_edge_fades(np.ones(1000), 1000, 0.01)
        self.assertAlmostEqual(float(result[0]), 0.0)
        self.assertAlmostEqual(float(result[-1]), 0.0, places=5)
        self.assertEqual(float(result[20]), 1.0)

    def test_distribution_does_not_mutate_global_random(self):
        random.seed(1234)
        expected = random.random()
        random.seed(1234)
        distribute_tracks([], seed=99)
        self.assertEqual(random.random(), expected)

    def test_distribution_presets_and_artist_spacing(self):
        def track(name, energy):
            analysis = SimpleNamespace(energy_profile=np.array([energy]))
            return {'filename': name, 'analysis': analysis}
        rising = [track('A - 1', .1), track('B - 2', .2), track('C - 3', .3)]
        falling = list(reversed(rising))
        self.assertGreater(
            sequence_score(rising, 'build_up'),
            sequence_score(falling, 'build_up'),
        )
        repeated = [track('Artist - 1', .1), track('Artist - 2', .2)]
        separated = [track('Artist - 1', .1), track('Other - 2', .2)]
        self.assertGreater(sequence_score(separated), sequence_score(repeated))

    def test_project_survives_move_without_original(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, 'song.wav')
            with open(source, 'wb') as handle:
                handle.write(b'audio')
            project = Project(os.path.join(root, 'projects'))
            old_dir = project.create('demo')
            project.backup_files([source])
            project.save()
            os.unlink(source)
            moved_dir = os.path.join(root, 'moved')
            shutil.move(old_dir, moved_dir)
            loaded = Project()
            data = loaded.load(moved_dir)
            self.assertEqual(data['format_version'], 4)
            self.assertTrue(os.path.isfile(loaded.all_files[0]['original']))

    def test_missing_media_can_be_relinked_recursively(self):
        with tempfile.TemporaryDirectory() as root:
            replacement_dir = os.path.join(root, 'library', 'album')
            os.makedirs(replacement_dir)
            replacement = os.path.join(replacement_dir, 'missing.wav')
            with open(replacement, 'wb') as handle:
                handle.write(b'audio')
            project = Project(os.path.join(root, 'projects'))
            project.create('demo')
            missing = os.path.join(root, 'old', 'missing.wav')
            project.all_files = [{
                'original': missing, 'backup': '', 'type': 'audio',
            }]
            project.video_groups = [{
                'tracks': [{'filepath': missing}], 'clips': [],
            }]
            project.track_analyses = {
                os.path.abspath(missing): {'filename': 'missing.wav'},
            }
            replacements = project.relink_missing(os.path.join(root, 'library'))
            self.assertEqual(replacements[missing], replacement)
            self.assertEqual(
                project.video_groups[0]['tracks'][0]['filepath'], replacement,
            )
            self.assertIn(os.path.abspath(replacement), project.track_analyses)

    def test_metadata_autosave_preserves_analysis_cache_entries(self):
        with tempfile.TemporaryDirectory() as root:
            project = Project(os.path.join(root, 'projects'))
            project.create('demo')
            project.save(video_groups=[])
            with open(project.project_file, 'r', encoding='utf-8') as handle:
                data = __import__('json').load(handle)
            data['track_analyses'] = {
                'song.wav': {'filename': 'song.wav', 'cache_file': 'cache.npz'},
            }
            with open(project.project_file, 'w', encoding='utf-8') as handle:
                __import__('json').dump(data, handle)
            project.save(
                analyses=None,
                video_groups=[{'name': 'Mix 1', 'tracks': []}],
            )
            with open(project.project_file, 'r', encoding='utf-8') as handle:
                saved = __import__('json').load(handle)
            self.assertIn('song.wav', saved['track_analyses'])
            self.assertEqual(saved['video_groups'][0]['name'], 'Mix 1')

    def test_project_v2_migrates_and_preserves_full_track_edit_state(self):
        with tempfile.TemporaryDirectory() as root:
            project = Project(os.path.join(root, 'projects'))
            project.create('legacy')
            legacy = {
                'format_version': 2,
                'name': 'legacy',
                'created': '',
                'files': [],
                'video_groups': [],
                'track_analyses': {},
            }
            with open(project.project_file, 'w', encoding='utf-8') as handle:
                __import__('json').dump(legacy, handle)
            loaded = Project()
            loaded.load(project.project_dir)
            self.assertEqual(loaded.app_state['current_step'], 0)
            self.assertEqual(loaded.app_state['repeat']['mode'], 'count')

            loaded.save(video_groups=[{
                'name': 'Mix 1',
                'tracks': [{
                    'filepath': 'missing.wav',
                    'filename': 'missing.wav',
                    'trim_start': 1.25,
                    'trim_end': 9.75,
                    'volume': .8,
                    'fade_in': .5,
                    'fade_out': .7,
                    'effects': {'lowpass': 9000},
                    'metadata': {'note': 'keep'},
                }],
            }], app_state={'current_step': 4})
            restored = Project()
            restored.load(loaded.project_dir)
            track = restored.video_groups[0]['tracks'][0]
            self.assertEqual(track['trim_start'], 1.25)
            self.assertEqual(track['volume'], .8)
            self.assertEqual(track['effects']['lowpass'], 9000)
            self.assertEqual(track['metadata']['note'], 'keep')
            self.assertEqual(restored.app_state['current_step'], 4)

    def test_missing_file_entry_survives_resave(self):
        with tempfile.TemporaryDirectory() as root:
            missing = os.path.join(root, 'gone.wav')
            project = Project(os.path.join(root, 'projects'))
            project.create('missing')
            project.all_files = [{
                'original': missing, 'backup': '', 'type': 'audio',
            }]
            project.save()
            project.backup_files([missing])
            project.save()
            restored = Project()
            restored.load(project.project_dir)
            self.assertEqual(len(restored.all_files), 1)
            self.assertFalse(os.path.exists(restored.all_files[0]['original']))

    def test_design_media_in_app_state_uses_portable_backup(self):
        with tempfile.TemporaryDirectory() as root:
            image = os.path.join(root, 'logo.png')
            with open(image, 'wb') as handle:
                handle.write(b'not-a-real-png-but-copyable')
            project = Project(os.path.join(root, 'projects'))
            original_dir = project.create('portable-design')
            project.backup_files([image])
            project.save(app_state={
                'design': {'overlays': {'logo': {'image': image}}},
                'pages': [],
            })
            os.unlink(image)
            moved = os.path.join(root, 'moved-design')
            shutil.move(original_dir, moved)
            restored = Project()
            restored.load(moved)
            restored_path = restored.app_state[
                'design'
            ]['overlays']['logo']['image']
            self.assertTrue(os.path.isfile(restored_path))
            self.assertTrue(restored_path.startswith(moved))

    def test_group_and_track_order_survives_save_reload(self):
        with tempfile.TemporaryDirectory() as root:
            project = Project(os.path.join(root, 'projects'))
            project.create('order')
            groups = [
                {
                    'name': 'Mix 2',
                    'tracks': [
                        {'filename': 'c.wav', 'filepath': 'c.wav'},
                    ],
                },
                {
                    'name': 'Mix 1',
                    'tracks': [
                        {'filename': 'b.wav', 'filepath': 'b.wav'},
                        {'filename': 'a.wav', 'filepath': 'a.wav'},
                    ],
                },
            ]
            project.save(video_groups=groups)
            restored = Project()
            restored.load(project.project_dir)
            self.assertEqual(
                [group['name'] for group in restored.video_groups],
                ['Mix 2', 'Mix 1'],
            )
            self.assertEqual(
                [
                    track['filename']
                    for track in restored.video_groups[1]['tracks']
                ],
                ['b.wav', 'a.wav'],
            )

    def test_legacy_localized_clip_settings_migrate_to_stable_ids(self):
        with tempfile.TemporaryDirectory() as root:
            project_file = os.path.join(root, 'project.json')
            with open(project_file, 'w', encoding='utf-8') as handle:
                json.dump({
                    'format_version': 3,
                    'name': 'legacy-localized',
                    'files': [],
                    'track_analyses': {},
                    'video_groups': [{
                        'name': 'Mix 1',
                        'tracks': [],
                        'clips': [],
                        'clip_interval_unit': '박자',
                        'clip_random_base': '캠롯',
                    }],
                    'app_state': {},
                }, handle, ensure_ascii=False)

            restored = Project()
            restored.load(project_file)
            group = restored.video_groups[0]
            self.assertEqual(group['clip_interval_unit'], 'beat')
            self.assertEqual(group['clip_random_base'], 'camelot')


if __name__ == '__main__':
    unittest.main()
