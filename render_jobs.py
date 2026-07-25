"""Render job state, cancellation, and resumable output checkpoints."""

import os
import threading


class RenderJob:
    def __init__(self, output_dir):
        self.output_dir = os.path.abspath(output_dir)
        self.cancel_event = threading.Event()

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
