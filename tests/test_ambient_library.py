import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import wave
import zipfile

from ambient_library import (
    SoundLibrary,
    confirm_library_cc0,
    process_sound_library,
    rescan_sound_library,
)


def _wave_bytes(seconds=1.0, frequency=220):
    output = io.BytesIO()
    with wave.open(output, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        frames = bytearray()
        for index in range(int(8000 * seconds)):
            sample = int(
                6000 * math.sin(2 * math.pi * frequency * index / 8000)
            )
            frames.extend(struct.pack("<h", sample))
        handle.writeframes(frames)
    return output.getvalue()


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class AmbientLibraryTests(unittest.TestCase):
    def test_owner_cc0_confirmation_updates_both_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifests").mkdir()
            (root / "licenses").mkdir()
            asset = {
                "asset_id": "rain_001",
                "original_filename": "rain.wav",
                "license": "unknown",
                "license_status": "needs_review",
            }
            (root / "manifests/sound_library.json").write_text(
                json.dumps({"assets": [asset]}), encoding="utf-8"
            )
            (root / "licenses/THIRD_PARTY_SOUNDS.json").write_text(
                json.dumps({"assets": [{
                    "asset_id": "rain_001",
                    "original_filename": "rain.wav",
                    "license_status": "needs_review",
                }]}), encoding="utf-8"
            )

            self.assertEqual(confirm_library_cc0(root, "owner confirmed"), 1)

            manifest = json.loads(
                (root / "manifests/sound_library.json").read_text(
                    encoding="utf-8"
                )
            )
            licenses = json.loads(
                (root / "licenses/THIRD_PARTY_SOUNDS.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["assets"][0]["license"], "CC0-1.0")
            self.assertEqual(
                licenses["assets"][0]["license_status"], "user_confirmed"
            )
            self.assertFalse(
                licenses["assets"][0]["attribution_required"]
            )

    def test_processed_loop_manifest_is_loaded_with_relative_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifests").mkdir()
            (root / "processed/loops/rain").mkdir(parents=True)
            (root / "processed/loops/rain/rain_loop.ogg").write_bytes(b"ogg")
            (root / "manifests/sound_library.json").write_text(
                '{"assets": []}', encoding="utf-8"
            )
            (root / "manifests/processed_loops.json").write_text(
                json.dumps({"assets": [{
                    "asset_id": "processed_rain_loop",
                    "category_id": "rain",
                    "playback_type": "continuous",
                    "relative_path": "processed/loops/rain/rain_loop.ogg",
                    "processed": True,
                }]}), encoding="utf-8",
            )
            library = SoundLibrary(root)
            self.assertEqual(len(library.available("rain")), 1)
            self.assertTrue(library.resolve("processed_rain_loop"))

    def test_safe_zip_is_registered_and_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "Rain Pack.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("loops/rain_loop.wav", _wave_bytes())

            report = process_sound_library(
                root, shutil.which("ffprobe"), shutil.which("ffmpeg")
            )
            library = SoundLibrary(root)

            self.assertEqual(report["registered_assets"], 1)
            self.assertEqual(report["deleted_archives"], ["Rain Pack.zip"])
            self.assertFalse(archive.exists())
            self.assertEqual(library.assets[0]["category_id"], "rain")
            self.assertEqual(
                library.assets[0]["license_status"], "needs_review"
            )
            self.assertTrue(library.resolve(library.assets[0]["asset_id"]))

    def test_unsafe_zip_is_kept_in_failed_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../escape.wav", _wave_bytes())
            direct = root / "wind.wav"
            direct.write_bytes(_wave_bytes(frequency=330))

            report = process_sound_library(
                root, shutil.which("ffprobe"), shutil.which("ffmpeg")
            )

            self.assertTrue((root / "failed_archives" / "unsafe.zip").is_file())
            self.assertFalse((root.parent / "escape.wav").exists())
            failure = next(
                item for item in report["failures"]
                if item["path"] == "unsafe.zip"
            )
            self.assertIn("unsafe archive path", failure["reason"])

    def test_manifest_uses_relative_paths_and_exact_duplicates_are_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = _wave_bytes()
            (root / "ocean-wave-a.wav").write_bytes(content)
            (root / "ocean-wave-b.wav").write_bytes(content)

            report = process_sound_library(
                root, shutil.which("ffprobe"), shutil.which("ffmpeg")
            )
            manifest = json.loads(
                (root / "manifests" / "sound_library.json").read_text(
                    encoding="utf-8"
                )
            )
            duplicates = json.loads(
                (root / "manifests" / "duplicate_report.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(report["registered_assets"], 1)
            self.assertFalse(os.path.isabs(manifest["assets"][0]["relative_path"]))
            self.assertEqual(len(duplicates["exact_duplicates"]), 1)

    def test_rescan_keeps_existing_assets_and_imports_new_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rain.wav").write_bytes(_wave_bytes(frequency=220))
            process_sound_library(
                root, shutil.which("ffprobe"), shutil.which("ffmpeg")
            )
            archive = root / "wind-pack.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("wind.wav", _wave_bytes(frequency=330))

            report = rescan_sound_library(
                root, shutil.which("ffprobe"), shutil.which("ffmpeg")
            )
            library = SoundLibrary(root)

            self.assertEqual(report["registered_assets"], 1)
            self.assertEqual(len(library.assets), 2)
            self.assertFalse(archive.exists())
            licenses = json.loads(
                (
                    root / "licenses" / "THIRD_PARTY_SOUNDS.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(len(licenses["assets"]), 2)


if __name__ == "__main__":
    unittest.main()
