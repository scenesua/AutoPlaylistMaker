import os
import tempfile
import unittest

from ambient_engine import build_ambient_plan


class _Library:
    def __init__(self, root):
        self.by_id = {
            "rain_a": {
                "asset_id": "rain_a", "category_id": "rain",
                "playback_type": "continuous", "duration_seconds": 40,
            },
            "rain_b": {
                "asset_id": "rain_b", "category_id": "rain",
                "playback_type": "continuous", "duration_seconds": 45,
            },
            "rain_hit": {
                "asset_id": "rain_hit", "category_id": "rain",
                "playback_type": "event", "duration_seconds": 2,
            },
        }
        self.root = root

    def available(self, category_id=None):
        return [
            item for item in self.by_id.values()
            if item["category_id"] == category_id
        ]

    def resolve(self, asset_id):
        return os.path.join(self.root, asset_id + ".wav")


class AmbientEngineTests(unittest.TestCase):
    def test_single_mixer_expands_enabled_categories_only(self):
        with tempfile.TemporaryDirectory() as directory:
            library = _Library(directory)
            settings = {"ambience_mixer": {
                "enabled": True,
                "random_seed": 12345,
                "sources": {
                    "rain": {"enabled": True, "volume_db": -18.0},
                    "thunder": {"enabled": False, "volume_db": -26.0},
                },
            }}
            plan = build_ambient_plan(settings, 60, library)
            self.assertTrue(plan)
            self.assertEqual({item["category_id"] for item in plan}, {"rain"})
            settings["ambience_mixer"]["enabled"] = False
            self.assertEqual(build_ambient_plan(settings, 60, library), [])

    def test_plan_is_deterministic_and_spans_final_timeline(self):
        with tempfile.TemporaryDirectory() as directory:
            library = _Library(directory)
            settings = {"ambient_tracks": [{
                "element_id": "rain-1", "category_id": "rain",
                "enabled": True, "density": 50, "variation": 40,
                "event_min_interval": 10, "event_max_interval": 20,
                "seed": 1234,
            }]}
            first = build_ambient_plan(settings, 1800, library)
            second = build_ambient_plan(settings, 1800, library)

            self.assertEqual(first, second)
            self.assertGreater(len(first), 30)
            self.assertTrue(any(item["kind"] == "event" for item in first))
            self.assertGreater(max(item["start"] for item in first), 1700)

    def test_continuous_sources_do_not_repeat_back_to_back(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = build_ambient_plan(
                {"ambient_tracks": [{
                    "element_id": "rain-1", "category_id": "rain",
                    "asset_ids": ["rain_a", "rain_b"],
                    "event_min_interval": 1000,
                }]},
                300, _Library(directory),
            )
            continuous = [
                item["asset_id"] for item in plan
                if item["kind"] == "continuous"
            ]
            self.assertGreater(len(continuous), 2)
            self.assertTrue(all(
                left != right
                for left, right in zip(
                    continuous, continuous[1:], strict=False
                )
            ))

    def test_volume_change_does_not_change_event_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            library = _Library(directory)
            base = {
                "element_id": "rain-1", "category_id": "rain",
                "asset_ids": ["rain_hit"], "density": 60, "seed": 88,
            }
            quiet = build_ambient_plan(
                {"ambient_tracks": [{**base, "volume_db": -30}]},
                300, library,
            )
            loud = build_ambient_plan(
                {"ambient_tracks": [{**base, "volume_db": -10}]},
                300, library,
            )
            self.assertEqual(
                [item["start"] for item in quiet],
                [item["start"] for item in loud],
            )
            self.assertNotEqual(quiet[0]["gain_db"], loud[0]["gain_db"])

    def test_known_continuous_assets_do_not_hard_loop_inside_a_segment(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = build_ambient_plan(
                {"ambient_tracks": [{
                    "element_id": "rain-1", "category_id": "rain",
                    "asset_ids": ["rain_a"], "seed": 7,
                }]},
                180, _Library(directory),
            )
            continuous = [item for item in plan if item["kind"] == "continuous"]
            self.assertTrue(continuous)
            self.assertTrue(all(not item["loop_input"] for item in continuous))
            self.assertTrue(all(
                item["source_offset"] + item["duration"] <= 40.001
                for item in continuous
            ))


if __name__ == "__main__":
    unittest.main()
