"""Built-in ambience asset discovery, validation, and manifest access."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile


AUDIO_EXTENSIONS = {".wav", ".flac", ".ogg", ".mp3", ".m4a", ".aac"}
ARCHIVE_EXTENSIONS = {".zip", ".7z", ".rar"}
MAX_ARCHIVE_FILES = 5000
MAX_ARCHIVE_UNCOMPRESSED = 2 * 1024**3
MAX_ARCHIVE_RATIO = 250

CATEGORY_IDS = (
    "rain", "thunder", "wind", "ocean", "stream", "fire", "forest",
    "birds", "crickets", "cafe", "city", "train", "fan",
    "ventilation", "water", "miscellaneous", "unclassified",
)
CATEGORY_GROUPS = {
    "nature": (
        "rain", "thunder", "wind", "ocean", "stream", "forest",
        "birds", "crickets",
    ),
    "indoor": ("fire", "cafe", "fan", "ventilation"),
    "urban": ("city", "train"),
    "other": ("water", "miscellaneous", "unclassified"),
}
CATEGORY_PRESETS = {
    "rain": (-18.0, 55, 35, 5.0, 20.0, 90.0, True, True),
    "thunder": (-24.0, 20, 65, 2.0, 30.0, 180.0, False, True),
    "wind": (-20.0, 45, 45, 6.0, 20.0, 100.0, True, True),
    "ocean": (-18.0, 50, 30, 7.0, 15.0, 60.0, True, True),
    "stream": (-20.0, 45, 25, 6.0, 12.0, 45.0, True, True),
    "fire": (-22.0, 55, 35, 4.0, 2.0, 12.0, True, True),
    "forest": (-20.0, 45, 45, 8.0, 8.0, 35.0, True, True),
    "birds": (-24.0, 45, 65, 2.0, 4.0, 20.0, True, True),
    "crickets": (-23.0, 50, 30, 6.0, 5.0, 25.0, True, True),
    "cafe": (-22.0, 45, 30, 8.0, 6.0, 25.0, True, True),
    "city": (-23.0, 40, 45, 8.0, 8.0, 35.0, True, True),
    "train": (-22.0, 40, 30, 8.0, 10.0, 40.0, True, True),
    "fan": (-25.0, 35, 20, 8.0, 20.0, 80.0, True, False),
    "ventilation": (-25.0, 35, 20, 8.0, 20.0, 80.0, True, False),
    "water": (-23.0, 40, 55, 4.0, 3.0, 20.0, True, True),
    "miscellaneous": (-24.0, 35, 45, 5.0, 8.0, 40.0, True, True),
    "unclassified": (-24.0, 30, 35, 5.0, 10.0, 45.0, True, True),
}

_CATEGORY_KEYWORDS = (
    ("thunder", ("thunder", "lightning")),
    ("crickets", ("cricket", "cicada", "night insect")),
    ("birds", ("bird", "birds", "chirp")),
    ("ventilation", ("ventilation", "air conditioner", "aircon", "air_conditioner")),
    ("fan", ("fan", "brown noise", "pink noise", "white noise", "static noise")),
    ("train", ("train", "railway", "railroad")),
    ("cafe", ("cafe", "coffee shop", "restaurant")),
    ("city", ("city", "traffic", "urban", "street")),
    ("ocean", ("ocean", "sea", "wave")),
    ("stream", ("stream", "river", "creek", "water flowing")),
    ("fire", ("fire", "fireplace", "crackle")),
    ("forest", ("forest", "woods", "woodland")),
    ("rain", ("rain", "rainfall", "storm")),
    ("wind", ("wind", "gust")),
    ("water", ("water", "splash", "bubble", "slime", "boiling", "drop")),
)
_EVENT_WORDS = (
    "thunder", "splash", "bubble", "slime", "alarm", "gust", "crackle",
    "chirp", "drop", "impact", "hit",
)


def resource_root() -> Path:
    """Resolve movable onedir/source resources without storing absolute paths."""
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent)
        internal = getattr(sys, "_MEIPASS", None)
        if internal:
            candidates.append(Path(internal))
    candidates.append(Path(__file__).resolve().parent)
    for base in candidates:
        path = base / "sound_effect_library"
        if path.is_dir():
            return path
    return candidates[0] / "sound_effect_library"


class SoundLibrary:
    def __init__(self, root: str | os.PathLike | None = None):
        self.root = Path(root) if root else resource_root()
        self.manifest_path = self.root / "manifests" / "sound_library.json"
        self.processed_manifest_path = (
            self.root / "manifests" / "processed_loops.json"
        )
        self.preset_path = self.root / "manifests" / "category_presets.json"
        self.assets = []
        self.by_id = {}
        self.presets = {}
        self.reload()

    def reload(self):
        data = _read_json(self.manifest_path, {"assets": []})
        self.assets = [
            item for item in data.get("assets", [])
            if isinstance(item, dict) and item.get("asset_id")
        ]
        processed = _read_json(self.processed_manifest_path, {"assets": []})
        self.assets.extend(
            item for item in processed.get("assets", [])
            if isinstance(item, dict) and item.get("asset_id")
        )
        self.by_id = {item["asset_id"]: item for item in self.assets}
        preset_data = _read_json(self.preset_path, {"categories": []})
        self.presets = {
            item["category_id"]: item
            for item in preset_data.get("categories", [])
            if isinstance(item, dict) and item.get("category_id")
        }
        return self

    def available(self, category_id=None, playback_type=None):
        result = []
        for asset in self.assets:
            if not asset.get("enabled", True):
                continue
            if category_id and asset.get("category_id") != category_id:
                continue
            if playback_type and asset.get("playback_type") != playback_type:
                continue
            if self.resolve(asset.get("asset_id")):
                result.append(asset)
        return result

    def resolve(self, asset_id):
        asset = self.by_id.get(asset_id)
        if not asset:
            return None
        relative = asset.get("relative_path", "")
        candidate = (self.root / relative).resolve()
        try:
            candidate.relative_to(self.root.resolve())
        except ValueError:
            return None
        return str(candidate) if candidate.is_file() else None

    def category_counts(self):
        counts = {
            category: {"continuous": 0, "event": 0, "hybrid": 0}
            for category in CATEGORY_IDS
        }
        for asset in self.available():
            category = asset.get("category_id", "unclassified")
            playback = asset.get("playback_type", "hybrid")
            counts.setdefault(
                category, {"continuous": 0, "event": 0, "hybrid": 0}
            )[playback] = counts.get(category, {}).get(playback, 0) + 1
        return counts


def _read_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return default


def _atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _safe_zip_entries(archive: Path):
    with zipfile.ZipFile(archive) as bundle:
        entries = [item for item in bundle.infolist() if not item.is_dir()]
        if not entries or len(entries) > MAX_ARCHIVE_FILES:
            raise ValueError("empty archive or excessive entry count")
        total = sum(item.file_size for item in entries)
        if total > MAX_ARCHIVE_UNCOMPRESSED:
            raise ValueError("uncompressed archive size exceeds safety limit")
        for item in entries:
            name = item.filename.replace("\\", "/")
            path = PurePosixPath(name)
            if (
                path.is_absolute() or ".." in path.parts
                or re.match(r"^[A-Za-z]:", name)
            ):
                raise ValueError(f"unsafe archive path: {name}")
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"archive symbolic link rejected: {name}")
            if (
                item.file_size > 0 and item.compress_size > 0
                and item.file_size / item.compress_size > MAX_ARCHIVE_RATIO
            ):
                raise ValueError(f"suspicious compression ratio: {name}")
        return entries


def _extract_zip(archive: Path, destination: Path):
    entries = _safe_zip_entries(archive)
    with zipfile.ZipFile(archive) as bundle:
        for item in entries:
            relative = PurePosixPath(item.filename.replace("\\", "/"))
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(item) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
    return entries


def _sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _probe_audio(path: Path, ffprobe: str, ffmpeg: str):
    probe = subprocess.run(
        [
            ffprobe, "-v", "error", "-select_streams", "a:0",
            "-show_entries",
            "stream=codec_name,sample_rate,channels,bit_rate:"
            "format=duration,bit_rate:format_tags",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False,
    )
    if probe.returncode:
        raise ValueError((probe.stderr or "ffprobe failed").strip())
    data = json.loads(probe.stdout or "{}")
    streams = data.get("streams") or []
    duration = float((data.get("format") or {}).get("duration") or 0)
    if not streams or not math.isfinite(duration) or duration <= 0:
        raise ValueError("no valid audio stream")
    stream = streams[0]
    decoded = subprocess.run(
        [
            ffmpeg, "-v", "error", "-i", str(path), "-t", "120",
            "-ac", "1", "-ar", "8000", "-f", "s16le", "-",
        ],
        capture_output=True, check=False,
    )
    if decoded.returncode or not decoded.stdout:
        raise ValueError(
            decoded.stderr.decode("utf-8", "replace").strip()
            or "audio decode failed"
        )
    pcm = memoryview(decoded.stdout).cast("h")
    count = len(pcm)
    squares = 0.0
    peak = 0
    silent = 0
    fingerprint = hashlib.sha256()
    sample_bytes = bytearray()
    for sample in pcm:
        absolute = abs(int(sample))
        peak = max(peak, absolute)
        squares += absolute * absolute
        silent += absolute < 33
        sample_bytes.extend(int(sample).to_bytes(2, "little", signed=True))
    fingerprint.update(sample_bytes)
    rms = math.sqrt(squares / max(1, count)) / 32768
    peak_ratio = peak / 32768
    silence_ratio = silent / max(1, count)
    if duration < .25:
        raise ValueError("audio is too short")
    if silence_ratio > .995 or peak_ratio < .001:
        raise ValueError("audio is effectively silent")
    tags = (data.get("format") or {}).get("tags") or {}
    return {
        "duration_seconds": round(duration, 6),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "codec": stream.get("codec_name") or "unknown",
        "bitrate": int(
            stream.get("bit_rate")
            or (data.get("format") or {}).get("bit_rate")
            or 0
        ),
        "average_level_dbfs": round(20 * math.log10(max(rms, 1e-9)), 3),
        "peak_dbfs": round(20 * math.log10(max(peak_ratio, 1e-9)), 3),
        "silence_ratio": round(silence_ratio, 6),
        "audio_fingerprint": fingerprint.hexdigest(),
        "metadata": {
            str(key): str(value) for key, value in tags.items()
        },
    }


def _classify(path: Path, archive_name: str, metadata):
    text = " ".join(
        [
            path.name, str(path.parent), archive_name,
            " ".join(metadata.get("metadata", {}).values()),
        ]
    ).casefold().replace("_", " ").replace("-", " ")
    matches = [
        (category, keyword)
        for category, keywords in _CATEGORY_KEYWORDS
        for keyword in keywords if keyword in text
    ]
    if matches:
        category, keyword = matches[0]
        confidence = .9 if keyword in path.name.casefold() else .75
        reasons = [f"keyword:{keyword}"]
    else:
        category, confidence, reasons = "unclassified", .25, [
            "no reliable category keyword"
        ]
    duration = metadata["duration_seconds"]
    event_word = next((word for word in _EVENT_WORDS if word in text), None)
    if category == "thunder" or event_word and duration < 20:
        playback = "event"
        reasons.append(f"event cue:{event_word or category}")
    elif duration >= 12:
        playback = "continuous"
        reasons.append(f"duration:{duration:.1f}s")
    elif category in {"rain", "wind", "ocean", "stream", "fan", "ventilation"}:
        playback = "continuous"
        reasons.append(f"continuous category:{category}")
    elif category in {"birds", "water"}:
        playback = "event"
        reasons.append(f"event category:{category}")
    else:
        playback = "hybrid"
        reasons.append(f"ambiguous duration:{duration:.1f}s")
    if "birds and wind" in text:
        playback = "hybrid"
        reasons.append("mixed continuous/event filename")
    return category, playback, min(confidence, .65 if category == "unclassified" else 1), reasons


def _preset_manifest():
    categories = []
    for category in CATEGORY_IDS:
        values = CATEGORY_PRESETS[category]
        categories.append({
            "category_id": category,
            "display_name_key": f"ambientCategory.{category}",
            "default_gain_db": values[0],
            "default_density": values[1],
            "default_variation": values[2],
            "default_crossfade_seconds": values[3],
            "default_event_min_interval": values[4],
            "default_event_max_interval": values[5],
            "allow_continuous": values[6],
            "allow_events": values[7],
            "icon": "",
        })
    return {"schema_version": 1, "categories": categories}


def process_sound_library(
    root: str | os.PathLike,
    ffprobe: str,
    ffmpeg: str,
    progress=None,
    cancel_event=None,
):
    """Process top-level inputs transactionally and delete only proven ZIPs."""
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    started = time.time()
    source_files = [item for item in root.iterdir() if item.is_file()]
    archives = [
        item for item in source_files
        if item.suffix.casefold() in ARCHIVE_EXTENSIONS
    ]
    direct_audio = [
        item for item in source_files
        if item.suffix.casefold() in AUDIO_EXTENSIONS
    ]
    unsupported = [
        item for item in archives if item.suffix.casefold() != ".zip"
    ]
    zip_archives = [item for item in archives if item not in unsupported]
    staging = Path(tempfile.mkdtemp(prefix=".staging_", dir=root))
    candidate_dir = staging / "candidates"
    candidate_dir.mkdir()
    final_dir = staging / "library"
    final_dir.mkdir()
    records = []
    rejected_records = []
    failures = []
    archive_counts = {}
    deleted_archives = []
    exact_duplicates = []
    fingerprint_candidates = []

    def emit(stage, current="", done=0, total=0):
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("cancelled")
        if progress:
            progress(stage, current, done, total)

    try:
        for archive_index, archive in enumerate(zip_archives):
            emit("extract", archive.name, archive_index, len(zip_archives))
            destination = candidate_dir / f"archive_{archive_index:04d}"
            destination.mkdir()
            try:
                entries = _extract_zip(archive, destination)
                archive_counts[archive.name] = {
                    "entries": len(entries), "audio_candidates": 0,
                    "valid_audio": 0, "preserved_rejected": 0,
                }
            except Exception as error:
                failures.append({
                    "path": archive.name, "kind": "archive",
                    "reason": str(error),
                })
                continue
            for item in destination.rglob("*"):
                if item.is_file() and item.suffix.casefold() in AUDIO_EXTENSIONS:
                    archive_counts[archive.name]["audio_candidates"] += 1
                    records.append({
                        "source": item,
                        "original_filename": item.name,
                        "original_archive": archive.name,
                    })
        for item in direct_audio:
            records.append({
                "source": item,
                "original_filename": item.name,
                "original_archive": "",
            })
        for item in unsupported:
            failures.append({
                "path": item.name, "kind": "archive",
                "reason": "archive format is not supported without an external tool",
            })

        valid = []
        for index, record in enumerate(records):
            emit("probe", record["original_filename"], index, len(records))
            try:
                metadata = _probe_audio(record["source"], ffprobe, ffmpeg)
                record.update(metadata)
                record["sha256"] = _sha256(record["source"])
                record["file_size"] = record["source"].stat().st_size
                valid.append(record)
                archive_name = record["original_archive"]
                if archive_name:
                    archive_counts[archive_name]["valid_audio"] += 1
            except Exception as error:
                record["rejection_reason"] = str(error)
                rejected_records.append(record)
                failures.append({
                    "path": record["original_filename"],
                    "archive": record["original_archive"],
                    "kind": "audio", "reason": str(error),
                })

        kept = []
        by_hash = {}
        by_fingerprint = {}
        for record in valid:
            if record["sha256"] in by_hash:
                exact_duplicates.append({
                    "duplicate": record["original_filename"],
                    "kept": by_hash[record["sha256"]]["original_filename"],
                    "reason": "identical sha256",
                })
                continue
            fingerprint = record["audio_fingerprint"]
            if fingerprint in by_fingerprint:
                fingerprint_candidates.append({
                    "candidate": record["original_filename"],
                    "similar_to": by_fingerprint[fingerprint][
                        "original_filename"
                    ],
                    "reason": "matching decoded PCM fingerprint",
                })
            by_hash[record["sha256"]] = record
            by_fingerprint.setdefault(fingerprint, record)
            kept.append(record)

        counters = {}
        assets = []
        for index, record in enumerate(kept):
            emit("classify", record["original_filename"], index, len(kept))
            category, playback, confidence, reasons = _classify(
                record["source"], record["original_archive"], record
            )
            key = (category, playback)
            counters[key] = counters.get(key, 0) + 1
            asset_id = f"{category}_{playback}_{counters[key]:03d}"
            extension = record["source"].suffix.casefold()
            relative = Path("library") / category / playback / (
                asset_id + extension
            )
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record["source"], target)
            if _sha256(target) != record["sha256"]:
                raise IOError(f"copy verification failed: {target.name}")
            _probe_audio(target, ffprobe, ffmpeg)
            preset = CATEGORY_PRESETS[category]
            assets.append({
                "asset_id": asset_id,
                "category_id": category,
                "playback_type": playback,
                "subtype": "",
                "display_name": Path(record["original_filename"]).stem,
                "relative_path": relative.as_posix(),
                "original_filename": record["original_filename"],
                "original_archive": record["original_archive"],
                "duration_seconds": record["duration_seconds"],
                "sample_rate": record["sample_rate"],
                "channels": record["channels"],
                "codec": record["codec"],
                "bitrate": record["bitrate"],
                "file_size": record["file_size"],
                "sha256": record["sha256"],
                "audio_fingerprint": record["audio_fingerprint"],
                "average_level_dbfs": record["average_level_dbfs"],
                "peak_dbfs": record["peak_dbfs"],
                "silence_ratio": record["silence_ratio"],
                "default_gain_db": preset[0],
                "loop_candidate": playback in {"continuous", "hybrid"},
                "event_candidate": playback in {"event", "hybrid"},
                "classification_confidence": confidence,
                "classification_reasons": reasons,
                "source_name": "",
                "creator": "",
                "license": "unknown",
                "license_status": "needs_review",
                "source_page": "",
                "attribution_required": None,
                "enabled": category != "unclassified",
                "metadata": record["metadata"],
            })

        manifest = {
            "schema_version": 1,
            "generated_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            ),
            "assets": assets,
        }
        manifests = staging / "manifests"
        rejected_root = staging / "unclassified" / "rejected"
        for index, record in enumerate(rejected_records, 1):
            archive_prefix = (
                Path(record["original_archive"]).stem
                if record["original_archive"] else "direct"
            )
            safe_name = re.sub(
                r"[^a-z0-9_.-]+", "_",
                f"{archive_prefix}_{record['original_filename']}".casefold(),
            ).strip("._") or f"rejected_{index:03d}"
            target = rejected_root / safe_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record["source"], target)
            if not target.is_file() or target.stat().st_size != record[
                "source"
            ].stat().st_size:
                raise IOError(f"rejected asset preservation failed: {safe_name}")
            record["rejected_relative_path"] = (
                Path("unclassified") / "rejected" / safe_name
            ).as_posix()
            archive_name = record["original_archive"]
            if archive_name:
                archive_counts[archive_name]["preserved_rejected"] += 1
            for failure in failures:
                if (
                    failure.get("path") == record["original_filename"]
                    and failure.get("archive", "") == archive_name
                ):
                    failure["preserved_path"] = record[
                        "rejected_relative_path"
                    ]
                    break
        _atomic_json(manifests / "sound_library.json", manifest)
        _atomic_json(manifests / "category_presets.json", _preset_manifest())
        duplicate_report = {
            "exact_duplicates": exact_duplicates,
            "fingerprint_candidates": fingerprint_candidates,
        }
        _atomic_json(manifests / "duplicate_report.json", duplicate_report)
        report = {
            "schema_version": 1,
            "started_at": started,
            "completed_at": time.time(),
            "source_file_count": len(source_files),
            "source_bytes": sum(item.stat().st_size for item in source_files),
            "archives_found": len(archives),
            "archives": archive_counts,
            "audio_candidates": len(records),
            "valid_audio": len(valid),
            "registered_assets": len(assets),
            "failures": failures,
            "deleted_archives": [],
        }
        _atomic_json(manifests / "processing_report.json", report)

        old_library = root / "library"
        old_manifests = root / "manifests"
        if old_library.exists() or old_manifests.exists():
            raise FileExistsError(
                "managed library already exists; use incremental rescan"
            )
        os.replace(staging / "library", old_library)
        os.replace(staging / "manifests", old_manifests)
        if (staging / "unclassified").exists():
            os.replace(staging / "unclassified", root / "unclassified")
        for record in valid:
            if not record["original_archive"]:
                record["source"].unlink()
        for record in rejected_records:
            if not record["original_archive"] and record["source"].exists():
                record["source"].unlink()
        for archive in zip_archives:
            stats = archive_counts.get(archive.name)
            fully_accounted = (
                stats
                and stats["valid_audio"] >= 1
                and stats["valid_audio"] + stats["preserved_rejected"]
                == stats["audio_candidates"]
            )
            if not fully_accounted:
                failed_dir = root / "failed_archives"
                failed_dir.mkdir(exist_ok=True)
                target = failed_dir / archive.name
                if not target.exists():
                    archive.replace(target)
                continue
            archive.unlink()
            deleted_archives.append(archive.name)
        for archive in unsupported:
            failed_dir = root / "failed_archives"
            failed_dir.mkdir(exist_ok=True)
            target = failed_dir / archive.name
            if not target.exists():
                archive.replace(target)
        report["deleted_archives"] = deleted_archives
        report["completed_at"] = time.time()
        _atomic_json(old_manifests / "processing_report.json", report)
        licenses = root / "licenses"
        licenses.mkdir(exist_ok=True)
        _atomic_json(licenses / "THIRD_PARTY_SOUNDS.json", {
            "schema_version": 1,
            "status": "needs_review",
            "assets": [
                {
                    "asset_id": item["asset_id"],
                    "original_filename": item["original_filename"],
                    "license_status": item["license_status"],
                }
                for item in assets
            ],
        })
        (licenses / "README.md").write_text(
            "# Third-party ambience sounds\n\n"
            "No bundled license documents were found during processing. "
            "Every asset is marked `needs_review`; do not infer CC0 status "
            "from a filename or download source.\n",
            encoding="utf-8",
        )
        return report
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def preserve_rejected_archive_member(
    root, archive_path, member_name, reason, original_archive=None
):
    """Recover one excluded member and record its review location."""
    root = Path(root).resolve()
    archive_path = Path(archive_path).resolve()
    entries = {item.filename: item for item in _safe_zip_entries(archive_path)}
    if member_name not in entries:
        raise KeyError(member_name)
    target_dir = root / "unclassified" / "rejected"
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_label = original_archive or archive_path.name
    safe_name = re.sub(
        r"[^a-z0-9_.-]+", "_",
        f"{Path(archive_label).stem}_{Path(member_name).name}".casefold(),
    ).strip("._")
    target = target_dir / safe_name
    with zipfile.ZipFile(archive_path) as bundle:
        data = bundle.read(member_name)
    if target.exists() and target.read_bytes() != data:
        raise FileExistsError(target)
    target.write_bytes(data)
    report_path = root / "manifests" / "processing_report.json"
    report = _read_json(report_path, {})
    relative = target.relative_to(root).as_posix()
    for failure in report.get("failures", []):
        if (
            failure.get("path") == Path(member_name).name
            and failure.get("archive") == archive_label
        ):
            failure["reason"] = reason
            failure["preserved_path"] = relative
    _atomic_json(report_path, report)
    return target


def apply_archive_license_evidence(
    root, original_archive, license_name, creator, source_page,
    attribution_required,
):
    """Apply explicit source-page evidence to one archive's assets."""
    root = Path(root).resolve()
    manifest_path = root / "manifests" / "sound_library.json"
    manifest = _read_json(manifest_path, {"assets": []})
    changed = []
    for asset in manifest.get("assets", []):
        if asset.get("original_archive") != original_archive:
            continue
        asset.update({
            "source_name": "OpenGameArt",
            "creator": creator,
            "license": license_name,
            "license_status": "verified",
            "source_page": source_page,
            "attribution_required": bool(attribution_required),
        })
        changed.append(asset["asset_id"])
    if not changed:
        raise ValueError(f"no assets from archive: {original_archive}")
    _atomic_json(manifest_path, manifest)
    license_path = root / "licenses" / "THIRD_PARTY_SOUNDS.json"
    license_data = _read_json(
        license_path, {"schema_version": 1, "assets": []}
    )
    by_id = {
        item.get("asset_id"): item
        for item in license_data.get("assets", [])
    }
    for asset_id in changed:
        item = by_id.setdefault(asset_id, {"asset_id": asset_id})
        item.update({
            "license": license_name,
            "license_status": "verified",
            "creator": creator,
            "source_page": source_page,
            "attribution_required": bool(attribution_required),
        })
    license_data["assets"] = list(by_id.values())
    _atomic_json(license_path, license_data)
    return changed


def confirm_library_cc0(root, confirmation_note):
    """Record the project owner's CC0 confirmation for bundled originals."""
    root = Path(root).resolve()
    manifest_path = root / "manifests" / "sound_library.json"
    manifest = _read_json(manifest_path, {"assets": []})
    assets = manifest.get("assets", [])
    for asset in assets:
        asset.update({
            "license": "CC0-1.0",
            "license_status": "user_confirmed",
            "attribution_required": False,
        })
    manifest["license_basis"] = confirmation_note
    _atomic_json(manifest_path, manifest)

    license_path = root / "licenses" / "THIRD_PARTY_SOUNDS.json"
    license_data = _read_json(
        license_path, {"schema_version": 1, "assets": []}
    )
    by_id = {
        item.get("asset_id"): item
        for item in license_data.get("assets", [])
    }
    for asset in assets:
        item = by_id.setdefault(asset["asset_id"], {
            "asset_id": asset["asset_id"],
            "original_filename": asset.get("original_filename", ""),
        })
        item.update({
            "license": "CC0-1.0",
            "license_status": "user_confirmed",
            "attribution_required": False,
        })
    license_data.update({
        "status": "user_confirmed",
        "license_basis": confirmation_note,
        "assets": list(by_id.values()),
    })
    _atomic_json(license_path, license_data)
    return len(assets)


def rescan_sound_library(
    root, ffprobe, ffmpeg, progress=None, cancel_event=None
):
    """Incrementally process new top-level inputs into an existing manifest."""
    root = Path(root).resolve()
    managed = root / "manifests" / "sound_library.json"
    if not managed.exists():
        return process_sound_library(
            root, ffprobe, ffmpeg, progress, cancel_event
        )
    incoming = [
        item for item in root.iterdir()
        if item.is_file() and item.suffix.casefold() in (
            AUDIO_EXTENSIONS | ARCHIVE_EXTENSIONS
        )
    ]
    if not incoming:
        return {
            "registered_assets": 0, "deleted_archives": [],
            "failures": [], "incremental": True,
        }
    staging = Path(tempfile.mkdtemp(prefix=".ambient_rescan_", dir=root))
    try:
        for item in incoming:
            shutil.copy2(item, staging / item.name)
        new_report = process_sound_library(
            staging, ffprobe, ffmpeg, progress, cancel_event
        )
        existing_data = _read_json(managed, {"assets": []})
        new_data = _read_json(
            staging / "manifests" / "sound_library.json", {"assets": []}
        )
        existing_assets = existing_data.get("assets", [])
        known_hashes = {
            item.get("sha256") for item in existing_assets
            if item.get("sha256")
        }
        counters = {}
        for item in existing_assets:
            key = (
                item.get("category_id", "unclassified"),
                item.get("playback_type", "hybrid"),
            )
            match = re.search(r"_(\d+)$", item.get("asset_id", ""))
            counters[key] = max(
                counters.get(key, 0),
                int(match.group(1)) if match else 0,
            )
        added = []
        skipped = []
        copied_paths = []
        try:
            for asset in new_data.get("assets", []):
                if asset.get("sha256") in known_hashes:
                    skipped.append({
                        "original_filename": asset.get("original_filename"),
                        "reason": "already registered sha256",
                    })
                    continue
                category = asset.get("category_id", "unclassified")
                playback = asset.get("playback_type", "hybrid")
                key = (category, playback)
                counters[key] = counters.get(key, 0) + 1
                asset_id = f"{category}_{playback}_{counters[key]:03d}"
                source = staging / asset["relative_path"]
                target = (
                    root / "library" / category / playback
                    / f"{asset_id}{source.suffix.casefold()}"
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    raise FileExistsError(target)
                shutil.copy2(source, target)
                copied_paths.append(target)
                if _sha256(target) != asset["sha256"]:
                    raise IOError(f"rescan copy verification failed: {target}")
                _probe_audio(target, ffprobe, ffmpeg)
                asset = dict(asset)
                asset["asset_id"] = asset_id
                asset["relative_path"] = target.relative_to(root).as_posix()
                existing_assets.append(asset)
                known_hashes.add(asset["sha256"])
                added.append(asset_id)
            existing_data["assets"] = existing_assets
            existing_data["generated_at"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            )
            _atomic_json(managed, existing_data)
            license_path = root / "licenses" / "THIRD_PARTY_SOUNDS.json"
            license_data = _read_json(
                license_path,
                {"schema_version": 1, "status": "needs_review", "assets": []},
            )
            license_by_id = {
                item.get("asset_id"): item
                for item in license_data.get("assets", [])
                if item.get("asset_id")
            }
            for asset in existing_assets:
                asset_id = asset.get("asset_id")
                if asset_id in license_by_id:
                    continue
                license_by_id[asset_id] = {
                    "asset_id": asset_id,
                    "original_filename": asset.get("original_filename", ""),
                    "license_status": asset.get(
                        "license_status", "needs_review"
                    ),
                }
            license_data["assets"] = list(license_by_id.values())
            _atomic_json(license_path, license_data)
        except Exception:
            for path in copied_paths:
                try:
                    path.unlink()
                except OSError:
                    pass
            raise

        rejected_source = staging / "unclassified" / "rejected"
        if rejected_source.is_dir():
            rejected_target = root / "unclassified" / "rejected"
            rejected_target.mkdir(parents=True, exist_ok=True)
            for source in rejected_source.iterdir():
                target = rejected_target / source.name
                if target.exists():
                    target = rejected_target / (
                        f"{source.stem}_{int(time.time())}{source.suffix}"
                    )
                shutil.copy2(source, target)

        successful_archives = set(new_report.get("deleted_archives", []))
        registered_direct = {
            item.get("original_filename")
            for item in new_data.get("assets", [])
            if not item.get("original_archive")
        }
        duplicate_direct = {
            item.get("duplicate")
            for item in _read_json(
                staging / "manifests" / "duplicate_report.json", {}
            ).get("exact_duplicates", [])
        }
        failed_archive_names = {
            item.get("path")
            for item in new_report.get("failures", [])
            if item.get("kind") == "archive"
        }
        for item in incoming:
            if item.suffix.casefold() in ARCHIVE_EXTENSIONS:
                if item.name in successful_archives:
                    item.unlink()
                elif item.name in failed_archive_names:
                    failed = root / "failed_archives"
                    failed.mkdir(exist_ok=True)
                    item.replace(failed / item.name)
            elif item.name in registered_direct or item.name in duplicate_direct:
                item.unlink()
            else:
                failure = next(
                    (
                        entry for entry in new_report.get("failures", [])
                        if entry.get("path") == item.name
                    ),
                    None,
                )
                if failure and failure.get("preserved_path"):
                    item.unlink()
        result = dict(new_report)
        result.update({
            "incremental": True,
            "registered_assets": len(added),
            "added_asset_ids": added,
            "existing_duplicates": skipped,
        })
        return result
    finally:
        shutil.rmtree(staging, ignore_errors=True)
