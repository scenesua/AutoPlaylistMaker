"""
Music Mixer - 음악 트랜지션 믹서
BPM/코드 감지 → 자연스러운 트랜지션 → YouTube 영상 생성

사용법:
  python mixer.py [옵션] file1.mp3 file2.mp3 file3.mp3 ...

예시:
  python mixer.py --crossfade 6 --output my_mix.mp3 song1.mp3 song2.mp3
  python mixer.py --video --resolution 1080p --output mix_output *.mp3
  python mixer.py --list tracklist.txt --output final_mix.mp3

비주얼 설정:
  python mixer.py --video --bg-image bg.png --visualizer eq_bars *.mp3
  python mixer.py --video --visual-config visual_config.json *.mp3
  python mixer.py --video --visualizer waveform --fade-in 3 --fade-out 4 *.mp3
"""

import argparse
import os
import sys
import time
import json

from analyzer import analyze_track, find_compatible_transition
from transition import create_mixed_audio, load_audio_pydub
from video_gen import generate_video


AUDIO_EXTS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus', '.aiff'}


def find_audio_files(path):
    if os.path.isfile(path):
        if os.path.splitext(path)[1].lower() in AUDIO_EXTS:
            return [path]
        return []
    elif os.path.isdir(path):
        files = []
        for f in sorted(os.listdir(path)):
            if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                files.append(os.path.join(path, f))
        return files
    return []


def parse_tracklist(filepath):
    tracks = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if os.path.exists(line):
                    tracks.append(line)
    return tracks


def print_analysis_summary(analyses):
    print("\n" + "=" * 70)
    print("  분석 결과 요약")
    print("=" * 70)

    for i, a in enumerate(analyses):
        mode_str = "메이저" if a.mode == 'major' else "마이너"
        dur_m = int(a.duration // 60)
        dur_s = int(a.duration % 60)
        print(f"  [{i+1:2d}] {a.filename}")
        print(f"       BPM: {a.bpm:6.1f} | 키: {a.key} {mode_str} ({a.camelot}) | 길이: {dur_m}:{dur_s:02d}")

    print("\n  트랜지션 호환성:")
    for i in range(len(analyses) - 1):
        compat = find_compatible_transition(analyses[i], analyses[i+1])
        rating = "★★★" if compat['score'] >= 60 else ("★★☆" if compat['score'] >= 40 else "★☆☆")
        print(f"  [{i+1:2d}→{i+2:2d}] {analyses[i].filename[:25]:25s} → {analyses[i+1].filename[:25]:25s}")
        print(f"         BPM 차이: {compat['bpm_diff']:.1f} | 키 거리: {compat['key_distance']} | "
              f"점수: {compat['score']:.0f} {rating}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Music Mixer - 음악 트랜지션 믹서',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python mixer.py song1.mp3 song2.mp3 song3.mp3
  python mixer.py --crossfade 6 --video --output my_mix *.mp3
  python mixer.py --list tracklist.txt --video --resolution 720p
  python mixer.py --video --bg-image cover.png --visualizer eq_bars *.mp3
  python mixer.py --video --visual-config visual_config.json *.mp3
        """
    )

    parser.add_argument('files', nargs='*', help='음악 파일 경로 (여러 개 가능)')
    parser.add_argument('--list', '-l', dest='tracklist', help='트랙 리스트 파일 (한 줄에 파일 경로)')
    parser.add_argument('--dir', '-d', help='음악 파일 디렉토리')
    parser.add_argument('--output', '-o', default='mixed_output', help='출력 파일명 (기본: mixed_output)')
    parser.add_argument('--crossfade', '-c', type=float, default=4.0, help='크로스페이드 시간(초) (기본: 4.0)')
    parser.add_argument('--video', '-v', action='store_true', help='YouTube 영상 생성')
    parser.add_argument('--resolution', '-r', choices=['720p', '1080p', '4k'], default='1080p',
                        help='영상 해상도 (기본: 1080p)')
    parser.add_argument('--order', choices=['input', 'bpm', 'key', 'smart'], default='input',
                        help='트랙 정렬 방식 (기본: 입력 순서)')
    parser.add_argument('--info', '-i', action='store_true', help='분석 정보만 출력 (믹싱 안 함)')
    parser.add_argument('--json', action='store_true', help='분석 결과를 JSON으로 저장')

    viz_group = parser.add_argument_group('비주얼 설정')
    viz_group.add_argument('--visual-config', help='비주얼 설정 JSON 파일 경로')
    viz_group.add_argument('--bg-image', help='배경 이미지 경로 (전체 트랙 공유)')
    viz_group.add_argument('--visualizer', '-V',
                           choices=['eq_bars', 'waveform', 'spectrum', 'circles', 'radial', 'none'],
                           help='비주얼라이저 타입 (설정 파일보다 우선)')
    viz_group.add_argument('--viz-position', choices=['top', 'bottom'], help='비주얼라이저 위치')
    viz_group.add_argument('--viz-color', help='비주얼라이저 색상 (예: #ff0000)')
    viz_group.add_argument('--viz-bars', type=int, help='이퀄라이저 바 개수')
    viz_group.add_argument('--viz-height', type=int, help='비주얼라이저 높이 (px)')
    viz_group.add_argument('--no-title', action='store_true', help='제목 텍스트 숨기기')
    viz_group.add_argument('--no-bpm', action='store_true', help='BPM 텍스트 숨기기')
    viz_group.add_argument('--no-key', action='store_true', help='키 텍스트 숨기기')
    viz_group.add_argument('--show-camelot', action='store_true', help='캠롯 표시')
    viz_group.add_argument('--no-progress', action='store_true', help='프로그레스 바 숨기기')
    viz_group.add_argument('--fade-in', type=float, help='페이드 인 시간(초)')
    viz_group.add_argument('--fade-out', type=float, help='페이드 아웃 시간(초)')

    args = parser.parse_args()

    tracks = []

    if args.tracklist:
        tracks = parse_tracklist(args.tracklist)
        if not tracks:
            print(f"오류: 트랙 리스트 파일에서 음악 파일을 찾을 수 없습니다: {args.tracklist}")
            sys.exit(1)
    elif args.dir:
        tracks = find_audio_files(args.dir)
        if not tracks:
            print(f"오류: 디렉토리에서 음악 파일을 찾을 수 없습니다: {args.dir}")
            sys.exit(1)
    elif args.files:
        for f in args.files:
            found = find_audio_files(f)
            tracks.extend(found)
        if not tracks:
            print(f"오류: 지정된 파일에서 음악 파일을 찾을 수 없습니다.")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    print(f"\n🎵 Music Mixer")
    print(f"   {len(tracks)}개 파일 로드됨\n")

    print("음악 분석 중...")
    start_time = time.time()
    analyses = []
    tracks_data = []

    for i, filepath in enumerate(tracks):
        try:
            analysis = analyze_track(filepath)
            analyses.append(analysis)
            samples, sr = load_audio_pydub(filepath)
            tracks_data.append((samples, sr))
        except Exception as e:
            print(f"  ⚠ 분석 실패: {filepath} - {e}")
            continue

    if not analyses:
        print("오류: 분석할 수 있는 음악 파일이 없습니다.")
        sys.exit(1)

    elapsed = time.time() - start_time
    print(f"\n분석 완료! ({elapsed:.1f}초 소요)")

    if args.order == 'bpm':
        indices = sorted(range(len(analyses)), key=lambda i: analyses[i].bpm)
        analyses = [analyses[i] for i in indices]
        tracks_data = [tracks_data[i] for i in indices]
        print("BPM 순으로 정렬됨")
    elif args.order == 'key':
        from analyzer import CAMELOT
        indices = sorted(range(len(analyses)),
                         key=lambda i: (analyses[i].camelot[-1], int(analyses[i].camelot[:-1])))
        analyses = [analyses[i] for i in indices]
        tracks_data = [tracks_data[i] for i in indices]
        print("캠롯 휠 순으로 정렬됨")
    elif args.order == 'smart':
        indices = _smart_order(analyses)
        analyses = [analyses[i] for i in indices]
        tracks_data = [tracks_data[i] for i in indices]
        print("스마트 정렬됨 (호환성 최적화)")

    print_analysis_summary(analyses)

    if args.json:
        json_data = []
        for a in analyses:
            json_data.append({
                'filename': a.filename,
                'bpm': round(a.bpm, 1),
                'key': a.key,
                'mode': a.mode,
                'camelot': a.camelot,
                'duration': round(a.duration, 1),
            })
        json_path = os.path.splitext(args.output)[0] + '_analysis.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"\n분석 결과 저장: {json_path}")

    if args.info:
        print("\n--info 모드: 분석 정보만 출력합니다.")
        return

    output_dir = os.path.dirname(args.output) or '.'
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    audio_output = os.path.splitext(args.output)[0] + '.mp3'
    _, total_duration, timestamps = create_mixed_audio(analyses, tracks_data, audio_output, args.crossfade)

    txt_output = os.path.splitext(args.output)[0] + '_timestamps.txt'
    _save_timestamps_txt(txt_output, timestamps, total_duration)
    print(f"타임스탬프 저장: {txt_output}")

    if args.video:
        res_map = {'720p': (1280, 720), '1080p': (1920, 1080), '4k': (3840, 2160)}
        w, h = res_map[args.resolution]
        video_output = os.path.splitext(args.output)[0] + '.mp4'

        viz_config_path = args.visual_config
        if not viz_config_path and os.path.exists('visual_config.json'):
            viz_config_path = 'visual_config.json'

        if args.bg_image or args.visualizer or args.viz_position or args.viz_color or \
           args.viz_bars or args.viz_height or args.no_title or args.no_bpm or \
           args.no_key or args.show_camelot or args.no_progress or \
           args.fade_in is not None or args.fade_out is not None:

            import shutil
            tmp_config = os.path.join(os.environ.get('TEMP', '.'),
                                       'mixer_visual_config.json')
            base_config = {}
            if viz_config_path and os.path.exists(viz_config_path):
                with open(viz_config_path, 'r', encoding='utf-8') as f:
                    base_config = json.load(f)
            else:
                base_config = {
                    "background": {"image": None, "opacity": 1.0, "blur": 0, "darken": 0.0},
                    "visualizer": {
                        "type": "eq_bars", "position": "bottom", "color": "#ffffff",
                        "opacity": 0.85, "bar_count": 64, "height": 120,
                        "smoothing": 0.3, "mirror": False, "gradient": True,
                    },
                    "text": {
                        "show_title": True, "show_bpm": True, "show_key": True,
                        "show_camelot": False, "show_time": True, "position": "center",
                        "font_size": 42, "sub_font_size": 28, "color": "#ffffff",
                        "shadow": True, "shadow_color": "#000000", "shadow_offset": 3,
                    },
                    "progress_bar": {
                        "show": True, "position": "bottom", "height": 4,
                        "color": "#ffffff", "background_color": "#333333", "margin": 30,
                    },
                    "fade": {"fade_in_duration": 2.0, "fade_out_duration": 3.0},
                }

            if args.bg_image:
                base_config.setdefault('background', {})['image'] = os.path.abspath(args.bg_image)
            if args.visualizer:
                base_config.setdefault('visualizer', {})['type'] = args.visualizer
            if args.viz_position:
                base_config.setdefault('visualizer', {})['position'] = args.viz_position
            if args.viz_color:
                base_config.setdefault('visualizer', {})['color'] = args.viz_color
            if args.viz_bars:
                base_config.setdefault('visualizer', {})['bar_count'] = args.viz_bars
            if args.viz_height:
                base_config.setdefault('visualizer', {})['height'] = args.viz_height
            if args.no_title:
                base_config.setdefault('text', {})['show_title'] = False
            if args.no_bpm:
                base_config.setdefault('text', {})['show_bpm'] = False
            if args.no_key:
                base_config.setdefault('text', {})['show_key'] = False
            if args.show_camelot:
                base_config.setdefault('text', {})['show_camelot'] = True
            if args.no_progress:
                base_config.setdefault('progress_bar', {})['show'] = False
            if args.fade_in is not None:
                base_config.setdefault('fade', {})['fade_in_duration'] = args.fade_in
            if args.fade_out is not None:
                base_config.setdefault('fade', {})['fade_out_duration'] = args.fade_out

            with open(tmp_config, 'w', encoding='utf-8') as f:
                json.dump(base_config, f, indent=2, ensure_ascii=False)
            viz_config_path = tmp_config

        generate_video(analyses, audio_output, video_output,
                       width=w, height=h, visual_config_path=viz_config_path,
                       timestamps=timestamps, crossfade_duration=args.crossfade)

    print("\n" + "=" * 40)
    print("  완료!")
    print("=" * 40)
    print(f"  출력 오디오: {audio_output}")
    if args.video:
        print(f"  출력 영상: {video_output}")
    print(f"  총 길이: {total_duration:.1f}s ({total_duration/60:.1f}분)")
    print(f"  트랙 수: {len(analyses)}")


def _save_timestamps_txt(filepath, timestamps, total_duration):
    lines = []
    lines.append("=" * 55)
    lines.append("  TRACK LIST / 타임스탬프")
    lines.append("=" * 55)
    lines.append("")

    for i, ts in enumerate(timestamps):
        start = ts.get('start_time', 0)
        end = ts.get('end_time', 0)
        sm = int(start // 60)
        ss = int(start % 60)
        em = int(end // 60)
        es = int(end % 60)

        filename = ts.get('filename', 'Unknown')
        bpm = ts.get('bpm', 0)
        key = ts.get('key', '')
        mode = "Major" if ts.get('mode') == 'major' else "Minor"
        camelot = ts.get('camelot', '')

        lines.append(f"  [{sm:02d}:{ss:02d}] {filename}")
        lines.append(f"          BPM: {bpm:.0f}  |  Key: {key} {mode}  |  Camelot: {camelot}")
        lines.append(f"          구간: {sm:02d}:{ss:02d} ~ {em:02d}:{es:02d}")
        if ts.get('transition_from'):
            lines.append(f"          ← {ts['transition_from']} 에서 전환")
        lines.append("")

    lines.append("-" * 55)
    tm = int(total_duration // 60)
    ts_s = int(total_duration % 60)
    lines.append(f"  총 길이: {tm:02d}:{ts_s:02d}  |  트랙 수: {len(timestamps)}")
    lines.append("=" * 55)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def _smart_order(analyses):
    n = len(analyses)
    if n <= 2:
        return list(range(n))

    best_order = list(range(n))
    best_score = 0

    for _ in range(min(1000, n * 100)):
        import random
        order = list(range(n))
        random.shuffle(order)
        score = 0
        for i in range(n - 1):
            compat = find_compatible_transition(analyses[order[i]], analyses[order[i+1]])
            score += compat['score']
        if score > best_score:
            best_score = score
            best_order = order[:]

    return best_order


if __name__ == '__main__':
    main()
