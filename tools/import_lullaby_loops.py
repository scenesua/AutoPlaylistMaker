"""Import only QA-passed Lullaby Scene loops whose APM originals match."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess


APM_ROOT = Path(__file__).resolve().parents[1]
APM_LIBRARY = APM_ROOT / "sound_effect_library"
SOURCE_ROOT = Path(r"D:\lullaby scene\sound_effect_library")
REPORT = SOURCE_ROOT / "loop_deployment_final/manifest/loop_deployment_report.json"
SOURCE_LIBRARY = SOURCE_ROOT / "library"
SOURCE_PROCESSED = SOURCE_ROOT / "loop_deployment_final"
OUTPUT_ROOT = APM_LIBRARY / "processed/loops"
OUTPUT_MANIFEST = APM_LIBRARY / "manifests/processed_loops.json"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def only(paths, label):
    paths = list(paths)
    if len(paths) != 1:
        raise RuntimeError(f"Expected one {label}, found {len(paths)}")
    return paths[0]


def probe(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=sample_rate,channels:format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return (
        float(data["format"]["duration"]),
        int(stream["sample_rate"]), int(stream["channels"]),
    )


def main():
    if not REPORT.is_file():
        raise FileNotFoundError(REPORT)
    base_manifest = json.loads(
        (APM_LIBRARY / "manifests/sound_library.json").read_text(
            encoding="utf-8"
        )
    )
    by_name = {
        Path(item["relative_path"]).name: item
        for item in base_manifest["assets"]
    }
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    imported = []
    for category, source in sorted(report["sources"].items()):
        for candidate in source.get("candidates", []):
            if not candidate.get("qa", {}).get("passed"):
                continue
            original_name = candidate["original"]
            apm_original = only(
                (APM_LIBRARY / "library").rglob(original_name),
                f"APM original {original_name}",
            )
            source_original = only(
                SOURCE_LIBRARY.rglob(original_name),
                f"Lullaby original {original_name}",
            )
            if sha256(apm_original) != sha256(source_original):
                raise RuntimeError(f"Original hash mismatch: {original_name}")
            asset_id = candidate["asset_id"]
            processed_source = SOURCE_PROCESSED / category / "continuous" / f"{asset_id}.ogg"
            if not processed_source.is_file():
                continue
            output_dir = OUTPUT_ROOT / category
            output_dir.mkdir(parents=True, exist_ok=True)
            output = output_dir / processed_source.name
            shutil.copy2(processed_source, output)
            duration, sample_rate, channels = probe(output)
            original_asset = by_name[original_name]
            imported.append({
                "asset_id": f"processed_{asset_id}",
                "category_id": category,
                "playback_type": "continuous",
                "relative_path": output.relative_to(APM_LIBRARY).as_posix(),
                "original_path": apm_original.relative_to(APM_LIBRARY).as_posix(),
                "processed_path": output.relative_to(APM_LIBRARY).as_posix(),
                "loop_mode": source.get("loop_mode", "crossfade"),
                "loop_start_seconds": candidate.get("loop_start_seconds"),
                "loop_end_seconds": candidate.get("loop_end_seconds"),
                "crossfade_seconds": candidate.get("crossfade_seconds", 0),
                "duration_seconds": round(duration, 6),
                "sample_rate": sample_rate,
                "channels": channels,
                "sha256": sha256(output),
                "source_project": "lullaby_scene",
                "source_asset_id": original_asset["asset_id"],
                "processing_version": report.get("analysis_version", 2),
                "processing_notes": (
                    "QA-passed Lullaby Scene derivative; original SHA-256 "
                    "matched APM; CC0 status confirmed by project owner."
                ),
                "license": "CC0-1.0",
                "license_status": "user_confirmed",
                "processed": True,
                "enabled": True,
            })
    OUTPUT_MANIFEST.write_text(
        json.dumps({
            "schema_version": 1,
            "source_project": "lullaby_scene",
            "license_basis": "Project owner confirmed the matched originals are CC0.",
            "assets": imported,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Imported {len(imported)} QA-passed loops")


if __name__ == "__main__":
    main()
