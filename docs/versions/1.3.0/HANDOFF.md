# 1.3.0 → 1.3.1 인수인계

- 현재 버전: 1.3.0
- 다음 버전: 1.3.1
- 다음 버전 성격: 버그 개선 및 최적화
- 작성일: 2026-07-30
- 릴리스 코드: `v1.3.0` / `f5e7c1a`
- 최신 main 기준: `04c281f` + 이 종료 문서 변경
- 공개 릴리스: `https://github.com/scenesua/AutoPlaylistMaker/releases/tag/v1.3.0`

## 현재 버전의 주요 목표

- 6단계 작업 흐름을 유지하면서 디자인/효과와 렌더 책임을 분리한다.
- 음원 trim, 분배 DnD, preview, repeat, project save 회귀를 실제 동작 기준으로 복구한다.
- 전문 소프트웨어형 다크·라이트 UI, 효과 카드, 전역 오디오와 11개 언어를 구현한다.
- 실행 즉시 보이는 native splash와 진행 loading splash를 연결한다.
- Windows와 macOS 1.3.0 패키지를 정식 릴리스한다.

## 실제로 완료된 기능

- 6단계 제작 흐름과 Stage 4 design/effects·Stage 5 render 분리
- DAW형 파형 trim, Shift/Alt 정밀 drag, volume/fade와 미리듣기
- 자동/수동 분배, group/track reorder, 빈 상태 최초 `Mix N` 생성과 rollback
- preview/output 공통 renderer 상태와 두 곡 전환 preview
- 완성 playlist 반복 count/target 계획과 마지막 반복 비절단
- project format v4, atomic save, 전체 page state, media backup/relink
- 11개 locale와 번역 독립 stable choice ID
- 빈 효과 목록, 검색형 category popup, 10개 실제 효과 카드, card/section reset
- music/ambient/master bus, Integrated LUFS·True Peak·LRA, 환경음과 selectable L/R stem meter
- Stage 4 preview-left/inspector-right, light/dark token, danger red/add green hover
- native icon→진행 loading→main handoff와 transparent RGBA brand
- 종료 시 preview/render/Tk timer와 child process 정리
- Windows 실제 실행 smoke, Windows·macOS CI build, 정식 GitHub release

## 부분 완료된 기능

- CLIP-001: clip 저장·thumbnail 경로는 연결됐으나 실제 다양한 이미지/영상의 전체 UI 회귀 검사가 부족하다.
- PREVIEW-001, DESIGN-001, VIS-001: 공통 renderer와 자동 픽셀 검사는 있으나 네 해상도·모든 스타일 수동 비교가 없다.
- RENDER-001: CPU/cancel은 검증했으나 NVIDIA/Intel/AMD 실제 encoder는 미검증이다.
- I18N-002, UI-004: locale 구조와 주요 창 크기는 검증했으나 원어민·DPI·모든 장문 조합은 미검증이다.
- BUILD-001: macOS package build와 ZIP 내부는 확인했지만 `.app` 실행·종료는 확인하지 못했다.
- EFFECT-002: 검색·category heading·Up/Down·Enter·Esc·scroll·outside close는 동작하지만 계층형 category submenu와 edge flip은 없다.

## 미구현 기능

- 환경음 folder/event scheduler
- momentary/short-term LUFS
- 효과 다중 인스턴스와 사용자 정의 renderer z-order
- 목표 시간에 맞추는 마지막 곡/반복 강제 절단
- PC 종료 예약

## 다음 버전으로 이월할 요구사항 ID

- 최우선 회귀 복구: CORE-001, SAVE-001, AUDIO-001, UI-004
- 최적화: PERF-001
- 버그 조사: PREVIEW-001, DESIGN-001, VIS-001, RENDER-001
- UI·효과: UI-004, EFFECT-002
- 플랫폼·품질: BUILD-001, I18N-002, CLIP-001
- 연결 issue: ISSUE-UI-004, ISSUE-PROJECT-001, ISSUE-NAV-001, ISSUE-ANALYSIS-001, ISSUE-DATA-001, ISSUE-ARCH-001, ISSUE-TEST-001, ISSUE-I18N-001, ISSUE-BUILD-002, ISSUE-BUILD-003, ISSUE-CI-001, ISSUE-UI-003

## 변경한 주요 파일

- 앱/흐름: `app.py`, `stage4_design_effects.py`, `stage5_render.py`
- 오디오/렌더: `audio_pipeline.py`, `audio_preview.py`, `video_gen.py`, `ffmpeg_service.py`
- 데이터/상태: `project.py`, `ui_state.py`, `repeat_settings.py`, `timeline_utils.py`
- 분석/분배: `analyzer.py`, `distributor.py`, `mixer.py`, `transition.py`
- UI/i18n: `font_combo.py`, `i18n.py`, `locales/`, `visual_config.json`
- 시작/빌드: `native_launcher.cs`, icon/splash assets, build scripts, `.github/workflows/build.yml`
- 검증/기록: `tests/`, `check_locales.py`, `docs/`, `.codex/`

## 중요한 코드 흐름과 설계 결정

1. `app.py`가 공통 app state와 lazy Stage를 소유한다. frozen 실행의 후속 Stage는 첫 진입 때 생성한다.
2. Stage 4가 effect/repeat/global audio를 편집하고 Stage 5는 render option·queue와 읽기 전용 요약을 제공한다.
3. `LiveFrameRenderer`가 preview와 output을 같은 출력 좌표계로 만들고 preview는 완성 frame 전체를 축소한다.
4. `audio_pipeline.py`는 track→music bus, ambient bus, master bus 순으로 streaming filtergraph를 만들고 필요할 때 stem을 `asplit`한다.
5. 완성 영상 반복 뒤 환경음은 최종 media timeline에 다시 연속 합성한다.
6. `project.py`는 format v4를 임시 파일+`os.replace`로 저장하고 legacy localized 값은 stable ID로 migration한다.
7. 효과는 `active_effects`에 명시된 ID만 활성화한다. 구형 프로젝트에 필드가 없으면 기존 전체 효과를 활성화해 호환한다.
8. Windows launcher가 core보다 먼저 transparent splash를 띄우고 IPC 준비 뒤 Tk loading splash에 넘긴다.
9. DEC-014에 따라 Windows/macOS artifact가 모두 성공해야 release publish가 실행된다.

## 반드시 유지해야 하는 기존 동작

- format v4/atomic save와 v2·v3 migration, media backup/relink와 analysis cache 보존
- translated label이 아닌 stable ID 저장
- trim은 handle을 누른 동안만 변경하고 release/destroy에서 grab을 해제
- 그룹이 없을 때 첫 이동은 그룹 하나만 만들고 실패 시 빈 그룹을 남기지 않음
- 목표 반복에서 마지막 playlist를 자르지 않음
- preview/output linked resolution/FPS와 공통 renderer
- 명시적으로 추가한 effect만 처리하고 legacy project는 기존 effect를 복원
- music/ambient/master 독립 bus와 True Peak ceiling
- native splash를 제거하지 않고 core 최적화와 분리
- 앱 종료 후 하위 process 0

## 현재 알려진 버그와 재현 조건

- ISSUE-UI-004: 다크→라이트 또는 라이트→다크로 테마를 전환한 뒤 일부 화면 요소가 사라지거나 다시 그려지지 않는다는 사용자 보고가 있다. 영향 Stage와 상태 조합은 아직 재현하지 못했다.
- ISSUE-PROJECT-001: 새 프로젝트 흐름에서 프로젝트 이름을 확정할 수 없고 저장도 완료되지 않는다는 사용자 보고가 있다. 프로젝트 생성·dirty 상태·저장 경로를 함께 추적해야 한다.
- ISSUE-NAV-001: 상단 `다음`을 눌러도 다음 Stage로 넘어가지 않는다는 사용자 보고가 있다. 프로젝트 유효성 검사와 버튼 상태, stage 전환 callback을 분리해 확인해야 한다.
- ISSUE-ANALYSIS-001: 분석을 시작하면 진행 창이 먼저 닫히고 실제 분석은 백그라운드에서 계속된다는 사용자 보고가 있다. 완료·취소 신호보다 앞서 창이 종료되는지 확인해야 한다.
- ISSUE-PERF-001: Windows cold start. 실행 후 native 2.53초, loading 53.09초, main 87.24초.
- ISSUE-DATA-001: trim/crossfade 뒤 수동 제거·group drag를 수행하고 UI `total_duration`과 render estimate를 비교한다.
- ISSUE-TEST-001: 같은 프로젝트를 720p/1080p/세로/정사각 preview와 output으로 캡처 비교한다.
- ISSUE-BUILD-003: 실제 macOS에서 release ZIP의 `.app`을 열고 splash/main/FFmpeg/종료를 확인한다.
- ISSUE-UI-003: `+ 효과 추가` 뒤 category hover/click 시 하위 메뉴가 열리지 않고 단일 grouped popup만 표시된다.
- ISSUE-BUILD-002: PyInstaller에서 Windows `tbb12.dll`, macOS `libomp.dylib` 선택 backend 경고가 난다.
- ISSUE-CI-001: Actions run summary에 Node 20 action deprecation 경고가 난다.

## 임시 구현이나 우회 처리

- cold start core 지연은 native icon과 진행 loading splash로 사용자 피드백만 보완했다.
- 효과 category submenu 대신 검색 가능한 단일 grouped popup을 사용한다.
- group duration이 의심되면 `repeat_settings.estimate_group_duration()` 결과를 render 기준으로 본다.
- macOS unsigned app은 Finder 우클릭 `열기`, FFmpeg가 없으면 `bash setup_mac.sh`를 사용한다.
- 선택적 Numba 병렬 backend는 현재 기본 분석·렌더 경로에서 사용하지 않는다.

## 데이터 형식과 호환성 주의사항

- `PROJECT_FORMAT_VERSION = 4`; schema를 바꾸면 version 증가와 migration test가 먼저다.
- `app_state.design.active_effects`가 없으면 legacy project는 전체 기존 effect를 활성화한다.
- `design.global_audio`가 없으면 legacy render normalization 값을 migration한다.
- 환경음 layer 필드는 `filepath`, `enabled`, `volume_db`, `pan`, `width`다.
- locale code는 Arabic `ar`, German `de-DE`, Russian `ru-RU`다.
- unknown JSON field 보존은 공개 확장 계약이 아니다.
- missing media는 항목을 삭제하지 않고 backup/alias/relink 순으로 복원한다.

## 실행한 빌드와 테스트 결과

- `python -m unittest discover -s tests -v`: 63 passed
- `python check_locales.py`: 0 errors / 0 warnings, 11 locales
- `python -m ruff check . --exclude build --exclude dist --exclude .git --select F,B`: 통과
- root/tests `py_compile`: 통과
- `python -m pip check`: 통과
- Windows local onedir build·main window·graceful exit: 성공
- GitHub Actions run `30471288589`: Windows build, macOS build, publish 모두 성공
- release 자산 4종 size/SHA-256과 ZIP 핵심 entry 확인

## 실행하지 못한 검사와 이유

- 정식 type checker: 프로젝트에 mypy/pyright 설정과 type-complete code가 없어 `py_compile`로 구문만 검증했다.
- macOS `.app` GUI smoke: 현재 장비가 Windows이고 Actions job은 build-only다.
- NVIDIA/Intel/AMD encoder: 해당 실기기 조합이 없다.
- 11개 언어 원어민 의미 검수: 자동 key/placeholder 검사로 대체할 수 없다.
- 네 해상도 최종 육안 비교·모든 DPI: 장시간 수동 승인 작업으로 1.3.1에 이월한다.
- 수 시간짜리 실제 프로젝트 전체 재생: 테스트 fixture와 짧은 FFmpeg 경로만 실행했다.

## 현재 git 상태

- 릴리스 tag `v1.3.0`은 `f5e7c1a`를 가리킨다.
- 원격 `main`은 릴리스 노트 보강 `04c281f`까지이며, `codex/release-v1.3.0`은 버전 종료와 릴리스 후 이슈 기록 commit 2개 앞선 clean 상태로 확정한다.
- 버전 종료 commit은 코드가 아니라 `AGENTS.md`, `CHANGELOG.md`, `docs/`, `.codex/` 문서만 변경하며 이번 요청에서는 원격에 push하지 않는다.
- 원본 개발 폴더 `AutoPlaylistMaker_v1.3.0`의 `master`는 `de32dbf` 기반 큰 dirty tree이므로 reset하지 않는다.
- 다음 작업은 릴리스 기준 worktree `D:\aldente yt\AutoPlaylistMaker_release_v1.3.0`에서 시작한다.

## 1.3.1에서 먼저 처리할 순서

1. baseline 63 tests를 실행한 뒤 ISSUE-PROJECT-001과 ISSUE-NAV-001을 새 프로젝트 기준으로 재현해 생성·이름·저장·단계 이동을 먼저 복구한다.
2. ISSUE-UI-004를 각 Stage에서 양방향 테마 전환으로 재현하고, stage 재구성 전후의 widget/state 수명주기를 검사한다.
3. ISSUE-ANALYSIS-001의 progress window 생성·완료·취소 callback을 계측해 실제 분석 작업과 창 수명주기를 다시 연결한다.
4. 위 네 회귀를 end-to-end 테스트로 고정한 뒤 ISSUE-PERF-001 cold-start profile과 최적화를 진행한다.
5. ISSUE-DATA-001 duration 경로, 네 해상도 preview/output, macOS·GPU 검증을 차례로 수행한다.
6. ISSUE-UI-003과 CI·선택 backend 경고는 차단 회귀가 해결된 뒤 정리한다.

## 다음 채팅에서 먼저 읽어야 할 문서와 코드 경로

1. `AGENTS.md`
2. `.codex/CURRENT_CONTEXT.md`
3. `.codex/CURRENT_HANDOFF.md`
4. `docs/versions/1.3.1/VERSION_OVERVIEW.md`
5. `docs/REQUIREMENTS.md`, `docs/FEATURE_STATUS.md`
6. `docs/KNOWN_ISSUES.md`, `docs/DECISIONS.md`
7. 이 파일과 `docs/versions/1.3.0/TEST_RESULTS.md`
8. `app.py` startup import/`_LazyStage`/`SplashScreen`
9. `repeat_settings.py`, `timeline_utils.py`, `project.py`
10. `stage4_design_effects.py:_open_effect_picker`, `video_gen.py`, `audio_pipeline.py`
