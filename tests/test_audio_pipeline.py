import os
import subprocess
import tempfile
import unittest
from types import SimpleNamespace

import json
import numpy as np
import soundfile as sf

from analyzer import TrackAnalysis
from audio_pipeline import mix_tracks_streaming, normalize_loudness
from video_gen import RenderCancelledError, _find_ffmpeg_exe, generate_video


@unittest.skipUnless(_find_ffmpeg_exe(), "ffmpeg is required")
class AudioPipelineTests(unittest.TestCase):
    def test_streaming_mix_and_normalization(self):
        ffmpeg = _find_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as root:
            paths = []
            for index, frequency in enumerate((440, 660)):
                path = os.path.join(root, f'{index}.wav')
                subprocess.run([
                    ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                    '-f', 'lavfi', '-i',
                    f'sine=frequency={frequency}:duration=1',
                    '-c:a', 'pcm_s16le', path,
                ], check=True)
                paths.append(path)
            analyses = [
                SimpleNamespace(
                    filename=f'{i}.wav', duration=1, bpm=120,
                    key='C', mode='major', camelot='8B',
                )
                for i in range(2)
            ]
            specs = [
                {'filepath': path, 'trim_start': 0, 'trim_end': 1}
                for path in paths
            ]
            mixed = os.path.join(root, 'mixed.wav')
            normalized = os.path.join(root, 'normalized.wav')
            _, duration, timestamps = mix_tracks_streaming(
                ffmpeg, analyses, specs, mixed, 0.2,
            )
            normalize_loudness(ffmpeg, mixed, normalized)
            self.assertAlmostEqual(duration, 1.8)
            self.assertEqual(len(timestamps), 2)
            self.assertGreater(os.path.getsize(normalized), 1024)

    def test_track_volume_and_fades_are_applied(self):
        ffmpeg = _find_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, 'tone.wav')
            output = os.path.join(root, 'edited.wav')
            subprocess.run([
                ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                '-c:a', 'pcm_s16le', source,
            ], check=True)
            analysis = SimpleNamespace(
                filename='tone.wav', duration=1, bpm=120,
                key='C', mode='major', camelot='8B',
            )
            mix_tracks_streaming(
                ffmpeg, [analysis], [{
                    'filepath': source, 'trim_start': 0, 'trim_end': 1,
                    'volume': 0.25, 'fade_in': 0.2, 'fade_out': 0.2,
                }], output, 0,
            )
            samples, rate = sf.read(output)
            edge_rms = np.sqrt(np.mean(samples[:int(rate * .05)] ** 2))
            center_rms = np.sqrt(np.mean(
                samples[int(rate * .45):int(rate * .55)] ** 2
            ))
            self.assertLess(edge_rms, center_rms * .5)
            self.assertLess(center_rms, .05)

    def test_direct_ffmpeg_video_pipeline(self):
        ffmpeg = _find_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as root:
            audio = os.path.join(root, 'audio.wav')
            output = os.path.join(root, 'video.mp4')
            config_path = os.path.join(root, 'visual.json')
            subprocess.run([
                ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.5',
                '-c:a', 'pcm_s16le', audio,
            ], check=True)
            with open(config_path, 'w', encoding='utf-8') as handle:
                json.dump({
                    'visualizer': {'type': 'none'},
                    'text': {
                        'show_title': False, 'show_bpm': False,
                        'show_key': False, 'show_camelot': False,
                        'show_time': False, 'custom_text': '',
                    },
                    'progress_bar': {'show': False},
                    'fade': {'fade_in_duration': 0, 'fade_out_duration': 0},
                }, handle)
            analysis = TrackAnalysis(
                audio, 'test.wav', 120, 'C', 'major', '8B', .5,
                np.array([.1]), np.array([]), np.empty((12, 0)),
                np.array([]), np.empty((0, 0)), np.array([]),
                22050, 512, np.zeros(11025, dtype=np.float32),
            )
            generate_video(
                [analysis], audio, output, width=64, height=64,
                visual_config_path=config_path, fps=5,
            )
            self.assertGreater(os.path.getsize(output), 1024)
            probe = subprocess.run(
                [ffmpeg, '-hide_banner', '-i', output],
                capture_output=True, text=True,
            )
            self.assertIn('Video:', probe.stderr)
            self.assertIn('Audio:', probe.stderr)

    def test_direct_video_pipeline_can_be_cancelled(self):
        ffmpeg = _find_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as root:
            audio = os.path.join(root, 'audio.wav')
            output = os.path.join(root, 'video.mp4')
            config_path = os.path.join(root, 'visual.json')
            subprocess.run([
                ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                '-c:a', 'pcm_s16le', audio,
            ], check=True)
            with open(config_path, 'w', encoding='utf-8') as handle:
                json.dump({
                    'visualizer': {'type': 'none'},
                    'text': {'show_title': False, 'show_bpm': False,
                             'show_key': False, 'show_camelot': False,
                             'show_time': False, 'custom_text': ''},
                    'progress_bar': {'show': False},
                    'fade': {'fade_in_duration': 0, 'fade_out_duration': 0},
                }, handle)
            analysis = TrackAnalysis(
                audio, 'test.wav', 120, 'C', 'major', '8B', 1,
                np.array([.1]), np.array([]), np.empty((12, 0)),
                np.array([]), np.empty((0, 0)), np.array([]),
                22050, 512, np.zeros(22050, dtype=np.float32),
            )

            def cancel(*_):
                raise RenderCancelledError("cancel")

            with self.assertRaises(RenderCancelledError):
                generate_video(
                    [analysis], audio, output, width=64, height=64,
                    visual_config_path=config_path, fps=5,
                    frame_progress_callback=cancel,
                )
            self.assertFalse(os.path.exists(output))


if __name__ == '__main__':
    unittest.main()
