import unittest

from video_gen import scale_visual_config, validate_effect_plan


class RenderSpaceTests(unittest.TestCase):
    def test_reference_pixels_scale_once_for_preview_and_final(self):
        logical = {
            "layout": {
                "version": 2,
                "reference_width": 1920,
                "reference_height": 1080,
            },
            "overlays": {
                "album": {"x": 960, "y": 540, "width": 600},
            },
            "visualizer": {
                "x": 480, "y": 270, "width": 960, "height": 200,
                "bar_gap": 4, "line_width": 2,
            },
            "text": {"font_size": 42, "x": .5, "y": .5},
        }
        preview = scale_visual_config(logical, 960, 540)
        final = scale_visual_config(logical, 3840, 2160)
        self.assertEqual(preview["overlays"]["album"]["x"], 480)
        self.assertEqual(preview["overlays"]["album"]["width"], 300)
        self.assertEqual(final["overlays"]["album"]["x"], 1920)
        self.assertEqual(final["overlays"]["album"]["width"], 1200)
        self.assertEqual(preview["text"]["x"], .5)
        self.assertEqual(final["text"]["font_size"], 84)

    def test_portrait_keeps_normalized_position_and_uniform_object_scale(self):
        logical = {
            "layout": {"reference_width": 1920, "reference_height": 1080},
            "overlays": {"logo": {"x": 960, "y": 540, "width": 200}},
        }
        portrait = scale_visual_config(logical, 1080, 1920)
        self.assertEqual(portrait["overlays"]["logo"]["x"], 540)
        self.assertEqual(portrait["overlays"]["logo"]["y"], 960)
        self.assertEqual(portrait["overlays"]["logo"]["width"], 112)

    def test_unknown_active_effect_fails_before_rendering(self):
        with self.assertRaisesRegex(ValueError, "mystery"):
            validate_effect_plan({"active_effects": ["background", "mystery"]})


if __name__ == "__main__":
    unittest.main()
