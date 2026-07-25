"""Non-blocking audio preview used by the timeline editor."""

import os
import subprocess
import sys
import tempfile
import threading

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


class AudioPreviewPlayer:
    def __init__(self, ffmpeg_finder):
        self._ffmpeg_finder = ffmpeg_finder
        self._generation = 0
        self._temp_path = None

    def play(
        self, filepath, start=0.0, duration=None, volume=1.0,
        fade_in=0.0, fade_out=0.0, on_ready=None, on_error=None,
    ):
        self.stop()
        self._generation += 1
        generation = self._generation

        def run():
            try:
                ffmpeg = self._ffmpeg_finder()
                if not ffmpeg:
                    raise RuntimeError("미리듣기에 필요한 ffmpeg를 찾을 수 없습니다.")
                fd, wav_path = tempfile.mkstemp(prefix="apm_preview_", suffix=".wav")
                os.close(fd)
                command = [
                    ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                    '-ss', f'{max(0.0, start):.3f}', '-i', filepath,
                ]
                if duration is not None:
                    command += ['-t', f'{max(0.05, duration):.3f}']
                filters = [f"volume={max(0.0, min(4.0, volume)):.4f}"]
                if fade_in > 0:
                    filters.append(f"afade=t=in:st=0:d={fade_in:.4f}")
                if fade_out > 0 and duration:
                    filters.append(
                        f"afade=t=out:st={max(0, duration-fade_out):.4f}"
                        f":d={fade_out:.4f}"
                    )
                command += ['-af', ",".join(filters)]
                command += ['-ac', '2', '-ar', '44100', wav_path]
                result = subprocess.run(command, capture_output=True, text=True, creationflags=_NO_WINDOW)
                if result.returncode:
                    raise RuntimeError(result.stderr.strip() or "미리듣기 변환 실패")
                if generation != self._generation:
                    os.unlink(wav_path)
                    return
                self._temp_path = wav_path
                if os.name != 'nt':
                    raise RuntimeError("현재 미리듣기는 Windows 환경을 지원합니다.")
                import winsound
                winsound.PlaySound(
                    wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC
                )
                if on_ready:
                    on_ready()
            except Exception as exc:
                if on_error:
                    on_error(exc)

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self._generation += 1
        if os.name == 'nt':
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except RuntimeError:
                pass
        if self._temp_path:
            try:
                os.unlink(self._temp_path)
            except OSError:
                pass
            self._temp_path = None
