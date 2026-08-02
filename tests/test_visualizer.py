import unittest
import os
import tempfile
from types import SimpleNamespace

import numpy as np
from PIL import Image

from video_gen import LiveFrameRenderer, hex_to_rgb


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
        "layout": {
            "version": 2, "reference_width": 120, "reference_height": 80,
        },
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
    def test_partial_color_input_uses_safe_fallback(self):
        self.assertEqual(hex_to_rgb("#"), (255, 255, 255))
        self.assertEqual(hex_to_rgb("#zzzzzz", (0, 0, 0)), (0, 0, 0))

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

    def test_every_visualizer_type_changes_the_composed_frame(self):
        analysis = _analysis("song.wav", np.ones((16, 8)))
        analysis.waveform = np.sin(
            np.linspace(0, 40 * np.pi, 400)
        ).astype(np.float32)
        baseline = LiveFrameRenderer(
            [analysis], 120, 80, 4, config_dict=_config("none"),
        ).render_frame(1)
        for viz_type in (
            "eq_bars", "waveform", "spectrum", "circles", "radial"
        ):
            with self.subTest(viz_type=viz_type):
                rendered = LiveFrameRenderer(
                    [analysis], 120, 80, 4,
                    config_dict=_config(viz_type),
                ).render_frame(1)
                self.assertGreater(
                    np.count_nonzero(rendered - baseline), 20
                )

    def test_every_beat_and_post_effect_changes_the_frame(self):
        analysis = _analysis("song.wav", np.ones((8, 4)))
        analysis.beat_times = np.array([1.0], dtype=np.float32)
        base_config = _config("none")
        base_config["text"].update({
            "custom_text": "FX",
            "custom_x": .35,
            "custom_y": .35,
            "custom_font_size": 22,
            "custom_color": "#ffffff",
        })
        baseline = LiveFrameRenderer(
            [analysis], 120, 80, 4, config_dict=base_config,
        ).render_frame(1)
        effect_settings = {
            "bounce": {"bounce": True, "bounce_intensity": 1.2},
            "shake": {"shake": True, "shake_intensity": 20},
            "zoom": {"zoom": True, "zoom_intensity": 1.2},
            "flash": {"flash": True, "flash_intensity": .8},
            "crt": {
                "crt": True, "crt_intensity": .8,
                "crt_scanlines": .8, "crt_vignette": .8,
            },
        }
        for name, settings in effect_settings.items():
            with self.subTest(effect=name):
                config = {
                    **base_config,
                    "effects": settings,
                }
                rendered = LiveFrameRenderer(
                    [analysis], 120, 80, 4, config_dict=config,
                ).render_frame(1)
                self.assertGreater(
                    np.count_nonzero(rendered - baseline), 20
                )

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

    def test_visualizer_alpha_composite_preserves_background(self):
        base_config = _config("none")
        visual_config = _config("eq_bars")
        analysis = _analysis("song.wav", np.ones((8, 4)))
        base = LiveFrameRenderer(
            [analysis], 120, 80, 4, config_dict=base_config,
        ).render_frame(1)
        visual = LiveFrameRenderer(
            [analysis], 120, 80, 4, config_dict=visual_config,
        ).render_frame(1)

        np.testing.assert_array_equal(visual[60:, :, :], base[60:, :, :])
        self.assertGreater(np.count_nonzero(visual[:30] - base[:30]), 0)

    def test_trimmed_duplicate_tracks_get_track_local_global_beats(self):
        first = _analysis("duplicate.wav", np.ones((8, 4)))
        second = _analysis("duplicate.wav", np.ones((8, 4)))
        first.beat_times = np.array([0.5, 1.5], dtype=np.float32)
        second.beat_times = np.array([2.0, 2.5, 3.0], dtype=np.float32)
        renderer = LiveFrameRenderer(
            [first, second], 120, 80, 4,
            timestamps=[
                {"start_time": 0, "end_time": 2, "source_start": 0},
                {"start_time": 2, "end_time": 4, "source_start": 2},
            ],
            config_dict={
                **_config("none"),
                "effects": {"flash": True, "flash_intensity": .5},
            },
        )

        np.testing.assert_allclose(renderer.beat_time_cache[0], [.5, 1.5])
        np.testing.assert_allclose(renderer.beat_time_cache[1], [2, 2.5, 3])
        before = renderer.render_frame(1.9)
        on_beat = renderer.render_frame(2.0)
        self.assertGreater(on_beat.mean(), before.mean())

    def test_overlay_order_changes_real_composition(self):
        with tempfile.TemporaryDirectory() as directory:
            red_path = os.path.join(directory, "red.png")
            blue_path = os.path.join(directory, "blue.png")
            Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(red_path)
            Image.new("RGBA", (20, 20), (0, 0, 255, 255)).save(blue_path)
            config = _config("none")
            config["overlays"] = {
                "album": {
                    "image": red_path, "x": 0, "y": 0,
                    "width": 20, "opacity": 1,
                },
                "logo": {
                    "image": blue_path, "x": 0, "y": 0,
                    "width": 20, "opacity": 1,
                },
            }
            config["effect_order"] = ["background", "album", "logo"]
            renderer = LiveFrameRenderer(
                [_analysis("song.wav", np.ones((8, 4)))],
                120, 80, 4, config_dict=config,
            )
            blue_top = renderer.render_frame(1)[5, 5]
            config["effect_order"] = ["background", "logo", "album"]
            renderer.reconfigure(config)
            red_top = renderer.render_frame(1)[5, 5]

            np.testing.assert_array_equal(blue_top, [0, 0, 255])
            np.testing.assert_array_equal(red_top, [255, 0, 0])

    def test_scene_transition_remains_the_base_for_following_effects(self):
        first = _analysis("first.wav", np.ones((8, 4)))
        second = _analysis("second.wav", np.ones((8, 4)))
        second.key = "G"
        renderer = LiveFrameRenderer(
            [first, second], 120, 80, 4,
            timestamps=[
                {"start_time": 0, "end_time": 3, "source_start": 0},
                {"start_time": 1, "end_time": 4, "source_start": 0},
            ],
            config_dict=_config("none"),
        )

        expected = np.asarray(Image.blend(
            Image.fromarray(renderer._static_cache[0]),
            Image.fromarray(renderer._static_cache[1]),
            0.5,
        ))
        np.testing.assert_array_equal(renderer.render_frame(2), expected)

    def test_fullscreen_clip_keeps_track_and_custom_text_visible(self):
        config = _config("none")
        config["text"].update({
            "show_title": True,
            "font_size": 16,
            "color": "#ffffff",
            "custom_text": "CUSTOM",
            "custom_x": .5,
            "custom_y": .5,
            "custom_font_size": 18,
            "custom_color": "#ffffff",
        })
        renderer = LiveFrameRenderer(
            [_analysis("Track Title.wav", np.ones((8, 4)))],
            120, 80, 4, config_dict=config,
        )
        renderer._clip_enabled = True
        renderer._get_clip_frame = lambda _t: Image.new(
            "RGB", (120, 80), "#000000"
        )

        frame = renderer.render_frame(1)

        self.assertGreater(np.count_nonzero(frame), 100)
        self.assertGreater(np.count_nonzero(frame[25:60]), 20)

    def test_custom_text_timing_and_target_track(self):
        first = _analysis("first.wav", np.ones((8, 4)))
        second = _analysis("second.wav", np.ones((8, 4)))
        config = _config("none")
        config["text"].update({
            "custom_text": "ONLY SECOND",
            "custom_x": .5,
            "custom_y": .5,
            "custom_font_size": 18,
            "custom_color": "#ffffff",
            "custom_start_seconds": .5,
            "custom_end_seconds": 3.5,
            "custom_target_track": 2,
        })
        renderer = LiveFrameRenderer(
            [first, second], 120, 80, 4,
            timestamps=[
                {"start_time": 0, "end_time": 2, "source_start": 0},
                {"start_time": 2, "end_time": 4, "source_start": 0},
            ],
            config_dict=config,
        )

        np.testing.assert_array_equal(
            renderer.render_frame(1), renderer._static_cache[0]
        )
        self.assertFalse(np.array_equal(
            renderer.render_frame(2.5), renderer._static_cache[1]
        ))
        np.testing.assert_array_equal(
            renderer.render_frame(3.75), renderer._static_cache[1]
        )

    def test_duplicate_filenames_keep_track_specific_info(self):
        first = _analysis("duplicate.wav", np.ones((8, 4)))
        second = _analysis("duplicate.wav", np.ones((8, 4)))
        first.bpm = 90
        second.bpm = 150
        config = _config("none")
        config["text"].update({
            "show_bpm": True,
            "sub_font_size": 16,
            "color": "#ffffff",
        })
        renderer = LiveFrameRenderer(
            [first, second], 120, 80, 4,
            timestamps=[
                {"start_time": 0, "end_time": 2, "source_start": 0},
                {"start_time": 2, "end_time": 4, "source_start": 0},
            ],
            config_dict=config,
        )

        self.assertFalse(np.array_equal(
            renderer._static_cache[0], renderer._static_cache[1]
        ))

    def test_custom_text_effect_order_and_unicode_are_rendered(self):
        analysis = _analysis("unicode.wav", np.ones((8, 4)))
        analysis.beat_times = np.array([1.0], dtype=np.float32)
        config = _config("none")
        config["text"].update({
            "custom_text": "한글 APM\n♫ 123",
            "custom_x": .5,
            "custom_y": .5,
            "custom_font_size": 18,
            "custom_color": "#ffffff",
            "custom_affects_by_effects": True,
        })
        config["effects"] = {"flash": True, "flash_intensity": .8}
        affected = LiveFrameRenderer(
            [analysis], 120, 80, 4, config_dict=config,
        ).render_frame(1)
        config["text"]["custom_affects_by_effects"] = False
        unaffected = LiveFrameRenderer(
            [analysis], 120, 80, 4, config_dict=config,
        ).render_frame(1)

        self.assertGreater(np.count_nonzero(affected), 100)
        self.assertGreater(np.count_nonzero(affected - unaffected), 20)


if __name__ == "__main__":
    unittest.main()
