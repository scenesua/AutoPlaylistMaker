"""Render job state, cancellation, and resumable output checkpoints."""

import os
import json
import subprocess
import threading
import datetime
import tempfile
import uuid


RENDER_STATES = (
    "CREATED", "VALIDATING_SETTINGS", "PREPARING", "BUILDING_TIMELINE",
    "PREPARING_AUDIO", "PREPARING_VIDEO", "STARTING_ENCODER", "RUNNING",
    "FINALIZING", "VALIDATING_OUTPUT", "COMPLETED", "FAILED", "CANCELLED",
)


def validate_media_output(
    path, ffprobe_exe, expected_width, expected_height,
    expected_duration, require_audio=True,
):
    if not os.path.isfile(path) or os.path.getsize(path) <= 1024:
        raise RuntimeError(f"Output file is missing or empty: {path}")
    result = subprocess.run(
        [
            ffprobe_exe, "-v", "error", "-show_streams", "-show_format",
            "-of", "json", path,
        ],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "FFprobe failed")
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video:
        raise RuntimeError("Rendered output has no video stream")
    if require_audio and not audio:
        raise RuntimeError("Rendered output has no audio stream")
    actual_size = (int(video.get("width", 0)), int(video.get("height", 0)))
    if actual_size != (expected_width, expected_height):
        raise RuntimeError(
            f"Output resolution {actual_size} != "
            f"{(expected_width, expected_height)}"
        )
    duration = float(payload.get("format", {}).get("duration") or 0)
    tolerance = max(2.0, float(expected_duration) * .02)
    if duration <= 0 or abs(duration - float(expected_duration)) > tolerance:
        raise RuntimeError(
            f"Output duration {duration:.3f}s is outside "
            f"{expected_duration:.3f}s ± {tolerance:.3f}s"
        )
    return {
        "path": path, "size": os.path.getsize(path),
        "width": actual_size[0], "height": actual_size[1],
        "duration": duration, "has_audio": bool(audio),
    }


class RenderJob:
    def __init__(self, output_dir):
        self.output_dir = os.path.abspath(output_dir)
        self.cancel_event = threading.Event()
        self.state = "CREATED"
        self.stage = "CREATED"
        self.process_pid = None
        self.last_output = None
        self.job_id = f"render_{uuid.uuid4().hex[:10]}"
        preferred_log_dir = os.path.join(
            os.path.expanduser("~"), "AutoPlaylistMaker_logs", "render"
        )
        try:
            os.makedirs(preferred_log_dir, exist_ok=True)
            self.log_dir = preferred_log_dir
        except OSError:
            self.log_dir = tempfile.gettempdir()
        self.log_path = os.path.join(self.log_dir, f"{self.job_id}.log")
        self._log_lock = threading.Lock()
        self.log(f"job created; output_dir={self.output_dir}")

    def set_state(self, state):
        if state not in RENDER_STATES:
            raise ValueError(state)
        self.state = state
        self.stage = state
        self.log(f"state={state}")

    def log(self, message):
        timestamp = datetime.datetime.now().isoformat(timespec="seconds")
        try:
            with self._log_lock:
                with open(self.log_path, "a", encoding="utf-8") as stream:
                    stream.write(f"[{timestamp}] {message}\n")
        except OSError:
            pass

    def cancel(self):
        self.cancel_event.set()

    @property
    def cancelled(self):
        return self.cancel_event.is_set()

    def mix_dir(self, index):
        return os.path.join(self.output_dir, f"mix_{index + 1}")

    def video_path(self, index):
        return os.path.join(self.mix_dir(index), f"mix_{index + 1}.mp4")

    def is_completed(self, index):
        path = self.video_path(index)
        return os.path.isfile(path) and os.path.getsize(path) > 1024
