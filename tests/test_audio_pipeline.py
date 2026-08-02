import os
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import json
import numpy as np
import soundfile as sf

import audio_pipeline
from analyzer import TrackAnalysis
from audio_pipeline import (
    mix_ambient_over_media, mix_tracks_streaming, normalize_loudness,
)
from video_gen import RenderCancelledError, _find_ffmpeg_exe, generate_video
from ambient_library import SoundLibrary
from ffmpeg_service import ensure_ffprobe_available
from render_jobs import validate_media_output


@unittest.skipUnless(os.name == "nt", "direct WAV preview is Windows-only")
class AudioPreviewTests(unittest.TestCase):
    def test_zero_offset_wav_starts_without_ffmpeg_reencoding(self):
        from audio_preview import AudioPreviewPlayer

        ready = threading.Event()
        winsound = SimpleNamespace(
            SND_FILENAME=1, SND_ASYNC=2, SND_PURGE=4, PlaySound=Mock(),
        )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav:
            path = wav.name
        try:
            player = AudioPreviewPlayer(
                lambda: self.fail("FFmpeg must not run for direct WAV")
            )
            with patch.dict(sys.modules, {"winsound": winsound}):
                player.play(path, duration=None, on_ready=ready.set)
                self.assertTrue(ready.wait(1))
            winsound.PlaySound.assert_any_call(path, 3)
            self.assertTrue(os.path.exists(path))
        finally:
            os.unlink(path)


@unittest.skipUnless(_find_ffmpeg_exe(), "ffmpeg is required")
class AudioPipelineTests(unittest.TestCase):
    def test_integrated_ambience_keeps_ffmpeg_commands_bounded(self):
        ffmpeg = _find_ffmpeg_exe()
        library = SoundLibrary()
        categories = {
            category: {"enabled": bool(library.available(category)),
                       "volume_db": -30.0}
            for category in ("rain", "thunder", "wind", "water")
        }
        settings = {"ambience_mixer": {
            "enabled": True, "random_seed": 12345,
            "sources": categories,
        }}
        commands = []
        original_run = audio_pipeline._run

        def record(command, cancel_event=None):
            commands.append(command)
            return original_run(command, cancel_event)

        with tempfile.TemporaryDirectory() as root:
            music = os.path.join(root, "music.wav")
            output = os.path.join(root, "mixed.wav")
            subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                "-c:a", "pcm_s16le", music,
            ], check=True)
            analysis = SimpleNamespace(
                filename="music.wav", duration=2, bpm=120, key="C",
                mode="major", camelot="8B", integrated_lufs=None,
                true_peak_dbtp=None,
            )
            audio_pipeline._run = record
            try:
                mix_tracks_streaming(
                    ffmpeg, [analysis], [{"filepath": music}], output, 0,
                    audio_settings=settings,
                )
            finally:
                audio_pipeline._run = original_run
            self.assertGreater(os.path.getsize(output), 1024)
        self.assertLessEqual(
            max(sum(item == "-i" for item in command) for command in commands),
            8,
        )
        self.assertTrue(any(
            "-filter_complex_script" in command for command in commands
        ))

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
            self.assertEqual(
                [stamp["source_start"] for stamp in timestamps], [0.0, 0.0]
            )
            self.assertGreater(os.path.getsize(normalized), 1024)
            samples, rate = sf.read(normalized, always_2d=True)
            self.assertEqual(rate, 44100)
            self.assertEqual(samples.shape[1], 2)
            self.assertTrue(np.isfinite(samples).all())
            self.assertGreater(float(np.sqrt(np.mean(samples ** 2))), 0.001)
            self.assertLessEqual(float(np.max(np.abs(samples))), 1.0)

            def dominant_frequency(segment):
                mono = segment.mean(axis=1)
                spectrum = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
                return np.fft.rfftfreq(len(mono), 1 / rate)[np.argmax(spectrum)]

            first_freq = dominant_frequency(samples[int(.1*rate):int(.6*rate)])
            second_freq = dominant_frequency(samples[int(1.2*rate):int(1.7*rate)])
            self.assertAlmostEqual(first_freq, 440, delta=8)
            self.assertAlmostEqual(second_freq, 660, delta=8)
            boundary = samples[int(.75*rate):int(1.05*rate)]
            self.assertGreater(float(np.sqrt(np.mean(boundary ** 2))), 0.001)

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

    def test_ambient_bus_is_independent_and_true_peak_limited(self):
        ffmpeg = _find_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as root:
            music = os.path.join(root, "music.wav")
            ambience = os.path.join(root, "rain.wav")
            output = os.path.join(root, "mixed.wav")
            music_stem = os.path.join(root, "music-stem.wav")
            ambient_stem = os.path.join(root, "ambient-stem.wav")
            for path, frequency in ((music, 440), (ambience, 90)):
                subprocess.run([
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i",
                    f"sine=frequency={frequency}:duration=2",
                    "-c:a", "pcm_s16le", path,
                ], check=True)
            analysis = SimpleNamespace(
                filename="music.wav", duration=2, bpm=120,
                key="C", mode="major", camelot="8B",
                integrated_lufs=-20.0, true_peak_dbtp=-10.0,
            )
            settings = {
                "music_master_db": -6.0,
                "true_peak_dbtp": -1.0,
                "ambient_master_db": -3.0,
                "ambient_tracks": [{
                    "filepath": ambience, "enabled": True,
                    "volume_db": -3.0, "pan": 0.4, "width": 1.2,
                }],
            }
            mix_tracks_streaming(
                ffmpeg, [analysis], [{
                    "filepath": music, "trim_start": 0, "trim_end": 2,
                }], output, 0, audio_settings=settings,
                stem_output_paths={
                    "music": music_stem, "ambient": ambient_stem,
                },
            )
            self.assertGreater(os.path.getsize(music_stem), 1024)
            self.assertGreater(os.path.getsize(ambient_stem), 1024)
            self.assertAlmostEqual(sf.info(output).duration, 2.0, places=2)
            self.assertAlmostEqual(
                sf.info(ambient_stem).duration, 2.0, places=2
            )
            samples, rate = sf.read(output, always_2d=True)
            self.assertEqual(rate, 44100)
            self.assertGreater(np.mean(np.abs(samples[:, 0] - samples[:, 1])), 1e-4)
            self.assertLessEqual(float(np.max(np.abs(samples))), 0.95)
            spectrum = np.abs(np.fft.rfft(samples[:, 0]))
            frequencies = np.fft.rfftfreq(len(samples), 1 / rate)
            self.assertGreater(
                spectrum[np.argmin(np.abs(frequencies - 90))], 10
            )

    def test_ambient_can_span_a_final_repeated_media_timeline(self):
        ffmpeg = _find_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as root:
            media = os.path.join(root, "looped.mp4")
            ambience = os.path.join(root, "rain.wav")
            output = os.path.join(root, "final.mp4")
            extracted = os.path.join(root, "final.wav")
            subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=64x64:d=3",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                "-shortest", "-c:v", "libx264", "-c:a", "aac", media,
            ], check=True)
            subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i",
                "sine=frequency=90:duration=0.8",
                "-c:a", "pcm_s16le", ambience,
            ], check=True)
            mix_ambient_over_media(
                ffmpeg, media, output, 3.0, {
                    "ambient_master_db": -3.0,
                    "true_peak_dbtp": -1.0,
                    "ambient_tracks": [{
                        "filepath": ambience, "enabled": True,
                        "volume_db": -3.0, "pan": 0.0, "width": 1.0,
                    }],
                },
            )
            subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-i", output, "-vn", "-c:a", "pcm_s16le", extracted,
            ], check=True)
            self.assertAlmostEqual(sf.info(extracted).duration, 3.0, places=1)
            samples, rate = sf.read(extracted, always_2d=True)
            spectrum = np.abs(np.fft.rfft(samples[:, 0]))
            frequencies = np.fft.rfftfreq(len(samples), 1 / rate)
            self.assertGreater(
                spectrum[np.argmin(np.abs(frequencies - 90))], 10
            )

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
            process_ids = []
            generate_video(
                [analysis], audio, output, width=64, height=64,
                visual_config_path=config_path, fps=5,
                process_callback=process_ids.append,
            )
            self.assertEqual(len(process_ids), 1)
            self.assertGreater(process_ids[0], 0)
            self.assertGreater(os.path.getsize(output), 1024)
            validated = validate_media_output(
                output, ensure_ffprobe_available(), 64, 64, .5
            )
            self.assertTrue(validated['has_audio'])
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
