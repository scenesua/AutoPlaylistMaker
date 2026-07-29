# 아키텍처

## 주요 파일

| 파일 | 역할 |
|---|---|
| `app.py` | 앱 부팅, 공통 Tk UI, 프로젝트·분배·음원 편집·클립 단계, 전역 상태 |
| `stage4_design_effects.py` | 디자인·효과·반복 설정, 라이브/두 곡 미리보기 |
| `stage5_render.py` | 출력 설정, 렌더 큐, 취소·재시도, 반복 후처리 |
| `project.py` | 프로젝트 폴더, 미디어 백업, JSON·분석 캐시 저장/복원·마이그레이션 |
| `analyzer.py` | BPM·키·Camelot·에너지·파형 분석 |
| `distributor.py` | 목표 길이와 음악 특성을 이용한 그룹 분배·순서 평가 |
| `audio_pipeline.py` | FFmpeg 스트리밍 믹스와 LUFS 정규화 |
| `audio_preview.py` | 비차단 FFmpeg 미리듣기 |
| `transition.py` | 크로스페이드와 메모리 기반 전환 유틸리티 |
| `video_gen.py` | 공통 프레임 렌더러, 비주얼라이저, 효과, FFmpeg 영상 출력·반복 |
| `ffmpeg_service.py` | 번들·환경·PATH·imageio 순서의 공통 FFmpeg 탐색·검증 |
| `repeat_settings.py` | UI·저장·렌더가 공유하는 전체 플레이리스트 반복 계획 |
| `timeline_utils.py` | 표시 시간, 트랙 경계, 두 곡 미리보기 구간 계산 |
| `font_combo.py` | 검색형 폰트 콤보상자 |
| `i18n.py`, `locales/` | 안정적 ID 기반 11개 언어 번역·환경 설정 |
| `render_jobs.py` | 렌더 취소 이벤트와 그룹별 완료 체크포인트 |
| `ui_state.py` | Tk 변수와 일부 페이지 선택 상태 캡처·복원 |
| `tests/` | 저장, UI 상호작용, 반복, FFmpeg 파이프라인, 번역 회귀 검사 |

## 실행 흐름

```text
main()
├─ SplashScreen 생성
├─ FFmpeg 사전 검사
├─ 무거운 분석·렌더 모듈 단계적 로드
└─ AutoPlaylistMakerApp
   ├─ Stage0Project
   ├─ Stage1Distribute
   ├─ Stage2MusicEdit
   ├─ Stage2ClipList
   ├─ Stage4DesignEffects
   └─ Stage5Render
```

패키지 실행에서는 첫 단계만 즉시 만들고 나머지는 `_LazyStage`로 두었다가 사용자가 해당 단계에 진입할 때 생성한다. 소스 실행과 테스트에서는 전체 단계를 즉시 생성한다.

## 데이터와 상태 흐름

```text
파일 선택
→ TrackItem
→ TrackAnalysis + 분석 캐시
→ video_groups[group].tracks
→ 트림·볼륨·페이드·클립·디자인 설정
→ collect_project_state()
→ Project.save()
→ project.json + analysis_cache/*.npz + 미디어 백업
```

- 런타임 핵심 상태는 `AutoPlaylistMakerApp.tracks`, `video_groups`, `project`, 각 Stage의 Tk 변수다.
- `collect_project_state()`가 디자인, 비주얼라이저, 렌더, 반복, 표시 시간, 현재 단계와 페이지 변수를 직렬화한다.
- 일반 변경은 700ms debounce 후 `persist_video_groups()`가 원자적으로 저장한다.
- 전체 저장은 분석 캐시까지 갱신하고, 메타데이터 자동 저장은 기존 분석 캐시를 보존한다.
- 언어·테마 변경으로 Stage를 재구성할 때 `ui_state.capture_pages/restore_pages`가 Tk 상태를 유지한다.

## UI와 렌더 연결

- 디자인과 렌더 단계의 해상도·사용자 해상도·FPS 변수는 양방향 연결된다.
- `Stage4DesignEffects`가 설정을 렌더 구성으로 만들고 `LiveFrameRenderer`가 미리보기와 최종 출력 양쪽에서 사용한다.
- 미리보기 캔버스는 출력 프레임 전체를 종횡비에 맞춰 축소한다.
- 오디오 미리듣기와 최종 오디오 믹스는 FFmpeg 기반 파이프라인을 사용한다.

## 외부 프로세스와 렌더링

1. `ffmpeg_service`가 실제 실행 가능한 FFmpeg를 한 번 탐색해 캐시한다.
2. `audio_pipeline`이 각 트랙의 trim/volume/fade와 crossfade 필터 그래프를 구성한다.
3. 선택 시 2-pass LUFS 정규화를 수행한다.
4. `LiveFrameRenderer`가 프레임을 생성하고 `video_gen.generate_video()`가 FFmpeg stdin으로 전송한다.
5. 전체 영상 반복은 완성된 영상 단위를 concat해 마지막 반복을 자르지 않는다.
6. `RenderJob`과 cancel event가 그룹 단위 취소·재시도를 관리한다.

## 회귀 위험이 높은 영역

- `app.py`의 Stage 재구성, dirty tracking, 자동 저장 상호작용
- `project.py` 경로 변환·형식 마이그레이션·분석 캐시 키
- `stage4_design_effects.py`와 `stage5_render.py`의 공유 변수 연결
- FFmpeg 필터 그래프, stderr 배수, 취소 시 부분 파일 정리
- `repeat_settings.py`와 `timeline_utils.py`에 중복된 반복 관련 공개 API
- 그룹의 `total_duration`을 갱신하는 여러 수동/드래그 경로
- 번역된 과거 저장값을 안정적 ID로 바꾸는 호환 로직
- Tk grab, 전역 키 바인딩, `after` 콜백과 하위 프로세스 종료

관련 문제는 [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md)를 참조한다.
