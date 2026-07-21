"""프로젝트 관리: 폴더 구조, 파일 백업, 저장/로드"""

import os
import json
import shutil
import re
import hashlib
import numpy as np
from datetime import datetime

AUDIO_EXTS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus', '.aiff'}
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}


def _safe_cache_name(filepath):
    """파일 경로 하나당 고유하고 파일시스템에 안전한 캐시 파일명 생성."""
    base = os.path.splitext(os.path.basename(filepath))[0]
    safe_base = re.sub(r'[^\w\-]', '_', base)[:40]
    h = hashlib.md5(os.path.abspath(filepath).encode('utf-8')).hexdigest()[:10]
    return f"{safe_base}_{h}"


def _arr(x):
    return x if x is not None else np.array([])


class Project:
    def __init__(self, base_dir="projects"):
        self.base_dir = os.path.abspath(base_dir)
        self.project_dir = None
        self.project_file = None
        self.name = ""
        self.created = ""
        self.target_duration = 3600.0
        self.tolerance = 0.10
        self.videos = []
        self.all_files = []
        self.video_groups = []

    def create(self, name=None):
        if not name:
            name = datetime.now().strftime("mix_%Y%m%d_%H%M%S")
        self.name = name
        self.created = datetime.now().isoformat()
        self.project_dir = os.path.join(self.base_dir, name)
        self.project_file = os.path.join(self.project_dir, "project.json")

        for sub in ["audio", "images", "video", "drafts"]:
            os.makedirs(os.path.join(self.project_dir, sub), exist_ok=True)

        return self.project_dir

    def backup_files(self, filepaths):
        if not self.project_dir:
            raise RuntimeError("프로젝트 폴더가 지정되지 않았습니다.")
        backed_up = []
        for fp in filepaths:
            if not os.path.exists(fp):
                continue
            ext = os.path.splitext(fp)[1].lower()
            if ext in AUDIO_EXTS:
                dest_dir = os.path.join(self.project_dir, "audio")
            elif ext in IMAGE_EXTS:
                dest_dir = os.path.join(self.project_dir, "images")
            else:
                continue

            dest = os.path.join(dest_dir, os.path.basename(fp))
            if os.path.exists(dest):
                base, ext_part = os.path.splitext(os.path.basename(fp))
                dest = os.path.join(dest_dir, f"{base}_{len(backed_up)}{ext_part}")

            shutil.copy2(fp, dest)
            backed_up.append({
                'original': os.path.abspath(fp),
                'backup': dest,
                'type': 'audio' if ext in AUDIO_EXTS else 'image',
            })

        self.all_files = backed_up
        return backed_up

    def save(self, analyses=None, video_groups=None, progress_callback=None):
        if not self.project_file or not self.project_dir:
            raise RuntimeError("프로젝트가 생성되지 않았습니다. 먼저 새 프로젝트를 만드세요.")

        data = {
            'name': self.name,
            'created': self.created,
            'saved': datetime.now().isoformat(),
            'target_duration': self.target_duration,
            'tolerance': self.tolerance,
            'files': self.all_files,
            'video_groups': [],
            'track_analyses': {},
        }

        if analyses:
            cache_dir = os.path.join(self.project_dir, "analysis_cache")
            os.makedirs(cache_dir, exist_ok=True)
            items = [(fp, a) for fp, a in analyses.items() if a is not None]
            for i, (filepath, a) in enumerate(items):
                if progress_callback:
                    progress_callback(i, len(items), "분석 결과 저장 중...")
                cache_name = _safe_cache_name(filepath)
                npz_path = os.path.join(cache_dir, cache_name + ".npz")
                np.savez_compressed(
                    npz_path,
                    energy_profile=_arr(a.energy_profile),
                    beat_times=_arr(a.beat_times),
                    chroma=_arr(a.chroma),
                    rms=_arr(a.rms),
                    stft_magnitudes=_arr(a.stft_magnitudes),
                    stft_times=_arr(a.stft_times),
                    waveform=_arr(a.waveform),
                )
                data['track_analyses'][os.path.abspath(filepath)] = {
                    'filepath': a.filepath, 'filename': a.filename,
                    'bpm': round(a.bpm, 1), 'key': a.key, 'mode': a.mode,
                    'camelot': a.camelot, 'duration': round(a.duration, 2),
                    'sr': a.sr, 'hop_length': a.hop_length,
                    'cache_file': os.path.relpath(npz_path, self.project_dir),
                }
            if progress_callback:
                progress_callback(len(items), len(items), "저장 마무리 중...")

        if video_groups:
            for vg in video_groups:
                group_data = {
                    'name': vg.get('name', ''),
                    'tracks': [],
                    'total_duration': vg.get('total_duration', 0),
                    'bg_image': vg.get('bg_image', ''),
                    'clip_enabled': vg.get('clip_enabled', False),
                    'clip_interval': vg.get('clip_interval', 1.0),
                    'clip_interval_unit': vg.get('clip_interval_unit', '초'),
                    'clip_random': vg.get('clip_random', False),
                    'clip_random_base': vg.get('clip_random_base', 'BPM'),
                    'clips': [],
                }
                for track_info in vg.get('tracks', []):
                    td = {
                        'filename': track_info.get('filename', ''),
                        'filepath': track_info.get('filepath', ''),
                        'trim_start': track_info.get('trim_start', 0),
                        'trim_end': track_info.get('trim_end', 0),
                    }
                    if track_info.get('analysis'):
                        a = track_info['analysis']
                        td['bpm'] = round(a.bpm, 1)
                        td['key'] = a.key
                        td['mode'] = a.mode
                        td['camelot'] = a.camelot
                        td['duration'] = round(a.duration, 1)
                    group_data['tracks'].append(td)
                for clip_info in vg.get('clips', []):
                    group_data['clips'].append({
                        'filepath': clip_info.get('filepath', ''),
                        'type': clip_info.get('type', 'image'),
                    })
                data['video_groups'].append(group_data)

        with open(self.project_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return self.project_file

    def load(self, project_path):
        if os.path.isfile(project_path):
            project_file = project_path
        elif os.path.isdir(project_path):
            project_file = os.path.join(project_path, "project.json")
        else:
            raise FileNotFoundError(f"프로젝트를 찾을 수 없습니다: {project_path}")

        with open(project_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.name = data.get('name', '')
        self.created = data.get('created', '')
        self.project_dir = os.path.dirname(project_file)
        self.project_file = project_file
        self.target_duration = data.get('target_duration', 3600.0)
        self.tolerance = data.get('tolerance', 0.10)
        self.all_files = data.get('files', [])
        self.video_groups = data.get('video_groups', [])
        self.track_analyses = data.get('track_analyses', {})

        return data

    def get_analysis_for(self, filepath):
        from analyzer import TrackAnalysis
        norm = os.path.abspath(filepath) if filepath else filepath
        ad = self.track_analyses.get(norm) or self.track_analyses.get(filepath)
        if not ad:
            return None

        arrays = {
            'energy_profile': np.array([]), 'beat_times': np.array([]),
            'chroma': np.array([]), 'rms': np.array([]),
            'stft_magnitudes': np.array([]), 'stft_times': np.array([]),
            'waveform': np.array([]),
        }
        cache_rel = ad.get('cache_file')
        if cache_rel:
            cache_path = os.path.join(self.project_dir, cache_rel)
            if os.path.isfile(cache_path):
                try:
                    with np.load(cache_path) as npz:
                        for k in arrays:
                            if k in npz:
                                arrays[k] = npz[k]
                except Exception as e:
                    print(f"  분석 캐시 로드 실패({cache_path}): {e}")
        else:
            for k in arrays:
                if k in ad:
                    arrays[k] = np.array(ad[k])

        return TrackAnalysis(
            filepath=ad.get('filepath', filepath),
            filename=ad.get('filename', ''),
            bpm=ad.get('bpm', 120),
            key=ad.get('key', 'C'),
            mode=ad.get('mode', 'major'),
            camelot=ad.get('camelot', '8B'),
            duration=ad.get('duration', 0),
            energy_profile=arrays['energy_profile'],
            beat_times=arrays['beat_times'],
            chroma=arrays['chroma'],
            rms=arrays['rms'],
            stft_magnitudes=arrays['stft_magnitudes'],
            stft_times=arrays['stft_times'],
            sr=ad.get('sr', 22050),
            hop_length=ad.get('hop_length', 512),
            waveform=arrays['waveform'],
        )

    def list_projects(self):
        projects = []
        if not os.path.exists(self.base_dir):
            return projects
        for d in sorted(os.listdir(self.base_dir)):
            p = os.path.join(self.base_dir, d, "project.json")
            if os.path.isfile(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    projects.append({
                        'name': data.get('name', d),
                        'path': os.path.dirname(p),
                        'created': data.get('created', ''),
                        'saved': data.get('saved', ''),
                        'n_files': len(data.get('files', [])),
                        'n_groups': len(data.get('video_groups', [])),
                    })
                except Exception:
                    pass
        return projects

    def get_audio_dir(self):
        return os.path.join(self.project_dir, "audio") if self.project_dir else None

    def get_images_dir(self):
        return os.path.join(self.project_dir, "images") if self.project_dir else None

    def get_video_dir(self):
        return os.path.join(self.project_dir, "video") if self.project_dir else None
