import unittest
from types import SimpleNamespace

import numpy as np

from video_gen import LiveFrameRenderer


def _analysis(name, magnitudes):
    return SimpleNamespace(
        filepath=name, filename=name, duration=4.0,
        bpm=120, key="C", mode="major", camelot="8B",
        waveform=np.zeros(400, dtype=np.float32),
        stft_magnitudes=np.asarray(magnitudes, dtype=np.float32),
        stft_times=np.arange(np.shape(magnitudes)[1], dtype=np.float32),
        beat_times=np.array([], dtype=np.float32),
        rms=np.array([], dtype=np.float32),
        sr=10, hop_length=10,
    )


def _config(viz_type="eq_bars"):
    return {
        "background": {"darken": 0},
        "visualizer": {
            "type": viz_type, "color": "#ffffff", "position": "top",
            "bar_count": 4, "height": 30, "width": 120,
            "smoothing": 0, "decay": 0, "gradient": False,
            "min_height": 0, "opacity": 1,
        },
        "text": {
            "show_title": False, "show_bpm": False, "show_key": False,
            "show_camelot": False, "show_time": False,
            "custom_text": "",
        },
        "progress_bar": {"show": False},
        "fade": {"fade_in_duration": 0, "fade_out_duration": 0},
    }


class VisualizerRendererTests(unittest.TestCase):
    def test_visualizer_pixels_follow_audio_analysis(self):
        magnitudes = np.zeros((8, 4), dtype=np.float32)
        magnitudes[:, 1] = 1
        renderer = LiveFrameRenderer(
            [_analysis("song.wav", magnitudes)], 120, 80, 4,
            config_dict=_config(),
        )

        quiet = renderer.render_frame(0)
        active = renderer.render_frame(1)

        self.assertGreater(np.count_nonzero(active - quiet), 100)

    def test_second_track_uses_its_own_cache_and_trimmed_source_time(self):
        first = np.zeros((8, 4), dtype=np.float32)
        first[:, 0] = 1
        second = np.zeros((8, 4), dtype=np.float32)
        second[:, 2] = 1
        timestamps = [
            {
                "start_time": 0, "end_time": 1, "source_start": 0,
            },
            {
                "start_time": 1, "end_time": 3, "source_start": 2,
            },
        ]
        renderer = LiveFrameRenderer(
            [
                _analysis("duplicate.wav", first),
                _analysis("duplicate.wav", second),
            ],
            120, 80, 3, timestamps=timestamps, config_dict=_config(),
        )

        first_frame = renderer.render_frame(0)
        second_frame = renderer.render_frame(1)

        self.assertEqual(renderer.track_at(1), 1)
        self.assertGreater(np.count_nonzero(first_frame), 100)
        self.assertGreater(np.count_nonzero(second_frame), 100)
        self.assertIn("0_eq", renderer.smooth_cache)
        self.assertIn("1_eq", renderer.smooth_cache)

    def test_black_visibility_suppresses_visualizer(self):
        config = _config()
        config["visibility"] = {
            "enabled": True, "turn_off_after": 1,
            "restore_before_end": 0, "restore": False,
            "black_color": "#000000",
        }
        renderer = LiveFrameRenderer(
            [_analysis("song.wav", np.ones((8, 4)))], 120, 80, 4,
            config_dict=config,
        )

        self.assertEqual(np.count_nonzero(renderer.render_frame(2)), 0)


if __name__ == "__main__":
    unittest.main()
