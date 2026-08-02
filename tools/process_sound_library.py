"""One-shot developer command for organizing the bundled ambience library."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ambient_library import process_sound_library
from ffmpeg_service import ensure_ffmpeg_available, resolve_ffmpeg_executable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root", nargs="?",
        default=Path(__file__).resolve().parents[1] / "sound_effect_library",
    )
    args = parser.parse_args()
    ffmpeg = ensure_ffmpeg_available()
    ffprobe = str(Path(ffmpeg).with_name("ffprobe.exe"))
    if not Path(ffprobe).is_file():
        ffprobe = str(Path(resolve_ffmpeg_executable()).with_name("ffprobe"))

    def progress(stage, current, done, total):
        print(f"[{stage}] {done}/{total} {current}", flush=True)

    report = process_sound_library(
        args.root, ffprobe=ffprobe, ffmpeg=ffmpeg, progress=progress
    )
    print(
        f"registered={report['registered_assets']} "
        f"deleted_archives={len(report['deleted_archives'])}"
    )


if __name__ == "__main__":
    main()
