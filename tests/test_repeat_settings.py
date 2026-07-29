import unittest
import os
import re
import subprocess
import tempfile

from repeat_settings import (
    MODE_COUNT,
    MODE_TARGET,
    build_repeat_plan,
    hms_to_seconds,
)
from timeline_utils import should_render_visuals, normalize_visibility_settings
from video_gen import _find_ffmpeg_exe, loop_video_repetitions


class RepeatSettingsTests(unittest.TestCase):
    def test_visibility_uses_final_timeline_and_optional_restore(self):
        self.assertTrue(should_render_visuals(179, 600, 180, 120, True, True))
        self.assertFalse(should_render_visuals(181, 600, 180, 120, True, True))
        self.assertTrue(should_render_visuals(481, 600, 180, 120, True, True))
        self.assertFalse(should_render_visuals(599, 600, 180, 120, True, False))
        self.assertTrue(should_render_visuals(200, 300, 180, 180, True, True))

    def test_legacy_visibility_migrates(self):
        migrated = normalize_visibility_settings({
            "enabled": True, "initial_visible": 300,
            "ending_visible": 180,
        })
        self.assertEqual(migrated["turn_off_after"], 300)
        self.assertEqual(migrated["restore_before_end"], 180)
        self.assertTrue(migrated["restore"])
    def test_count_mode(self):
        plan = build_repeat_plan(1390, mode=MODE_COUNT, repeat_count=3)
        self.assertEqual(plan.repeat_count, 3)
        self.assertEqual(plan.output_seconds, 4170)

    def test_target_shorter_than_one_playlist_keeps_whole_playlist(self):
        plan = build_repeat_plan(
            2100, mode=MODE_TARGET, target_seconds=1200
        )
        self.assertEqual(plan.repeat_count, 1)
        self.assertEqual(plan.output_seconds, 2100)

    def test_exact_target_multiple(self):
        plan = build_repeat_plan(
            2100, mode=MODE_TARGET, target_seconds=4200
        )
        self.assertEqual(plan.repeat_count, 2)
        self.assertEqual(plan.overflow_seconds, 0)

    def test_non_multiple_rounds_up_without_truncation(self):
        plan = build_repeat_plan(
            2100, mode=MODE_TARGET, target_seconds=3600
        )
        self.assertEqual(plan.repeat_count, 2)
        self.assertEqual(plan.output_seconds, 4200)
        self.assertEqual(plan.overflow_seconds, 600)

    def test_hms(self):
        self.assertEqual(hms_to_seconds(2, 3, 4), 7384)

    @unittest.skipUnless(_find_ffmpeg_exe(), "ffmpeg is required")
    def test_actual_repeat_contains_whole_three_copies(self):
        ffmpeg = _find_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "one.mp4")
            output = os.path.join(root, "three.mp4")
            subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=64x64:d=1",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-shortest", "-c:v", "libx264", "-c:a", "aac", source,
            ], check=True)
            loop_video_repetitions(source, output, 3)
            probe = subprocess.run(
                [ffmpeg, "-hide_banner", "-i", output],
                capture_output=True, text=True,
            )
            match = re.search(
                r"Duration: (\d+):(\d+):([\d.]+)", probe.stderr
            )
            self.assertIsNotNone(match)
            duration = (
                int(match.group(1)) * 3600
                + int(match.group(2)) * 60
                + float(match.group(3))
            )
            self.assertGreaterEqual(duration, 2.9)
            self.assertLess(duration, 3.2)


if __name__ == "__main__":
    unittest.main()
