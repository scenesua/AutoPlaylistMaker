# 1.3.0 구현 기록

## 2026-07-25 — 버전 분리와 Windows folder 배포

- 목적: 1.2 계열 위 덮어쓰기를 피하고 1.3.0 독립 folder/ZIP 배포 구성.
- 요구사항: BUILD-001, UI-002
- 주요 파일: build scripts, icon assets, `app.py`
- 구현: `AutoPlaylistMaker_v1.3.0` 이름과 icon/splash resource, one-dir bundle.
- 발생 문제: icon alpha/halo 반복, 패키지 imageio metadata 누락, Tcl/Tk resource.
- 해결: 승인 asset 고정, PyInstaller metadata와 Tcl/Tk 복사, clean build.
- 검증: Windows 후보 실행·종료. macOS는 BUILD-001로 남김.

## 2026-07-27~28 — 1.3.0 구조와 기능 회귀 수정

- 목적: 디자인/효과·render 분리, 다국어·preview·repeat·save 실동작 복원.
- 요구사항: CORE-001, PREVIEW-001/002, REPEAT-001, SAVE-001, I18N-001
- 주요 파일: `stage4_design_effects.py`, `stage5_render.py`, `i18n.py`, `locales/`, `ffmpeg_service.py`, `timeline_utils.py`, `project.py`
- 구현:
  - Stage 4/5 책임 분리와 공유 resolution/FPS/repeat state
  - 공통 `LiveFrameRenderer` preview/output 경로
  - 11개 locale와 stable choice ID
  - project format v4와 full app state
  - 공통 FFmpeg executable resolver
- 중요 결정: DEC-002~DEC-008
- 발생 문제: frozen 실행에서 `app` 이중 import, FFmpeg filter 출력, 언어 rebuild 상태 손실.
- 해결: 실행 중 app module lookup, `atrim+asetpts`, page state capture/restore.
- 검증: UI interaction, repeat, locale, FFmpeg pipeline tests.

## 2026-07-28 — 편집·분배·UI 실동작

- 목적: trim drag 고착, DnD 위치 불명확, 그룹 없는 최초 이동, font UX 해결.
- 요구사항: AUDIO-002/003, DIST-002/003, FONT-001
- 주요 파일: `app.py`, `font_combo.py`, tests
- 구현:
  - Tk grab 기반 trim capture/release와 modifier precision
  - 삽입 indicator, 그룹 간/빈 그룹 이동
  - button/drag 공통 자동 그룹 transaction
  - reusable searchable font popup
- 발생 문제: release가 widget 밖에서 누락, 실패 후 빈 그룹, popup root bind 잔류.
- 해결: grab release cleanup, rollback, destroy/bind/timer cleanup.
- 검증: `tests/test_ui_interactions.py`.

## 2026-07-29 — 안전한 코드 정리와 재검증

- 목적: 기능·UI·저장 형식 변경 없이 중복·미사용 코드와 오류 처리를 정리.
- 요구사항: 기존 동작 보존
- 주요 파일: analyzer/app/audio pipeline/distributor/i18n/mixer/Stage 4·5/timeline/transition/video/tests.
- 구현:
  - 미사용 import·변수·동일 결과 분기 제거
  - waveform peak helper 통합과 회귀 test
  - 예상 가능한 Tk/입력 예외 구체화와 로그 추가
  - render queue codec callback late-binding 수정
  - repeat 입력의 불필요한 preview refresh 제거
- 검증:
  - 49 tests
  - Ruff F,B clean
  - locale 0/0
  - pip check clean
  - folder build·ZIP·실행·종료
- 남은 작업: ISSUE-ARCH-001, ISSUE-DATA-001, ISSUE-PERF-001.

## 2026-07-29 — 프로젝트 기억 체계 구축

- 목적: 새 Codex 작업이 과거 대화 없이 요구사항·결정·상태·문제를 복원.
- 요구사항: DOC-001
- 주요 파일: `AGENTS.md`, `CHANGELOG.md`, `docs/`, `.codex/`
- 구현:
  - 29개 요구사항과 23개 기능 상태 복원
  - 10개 설계 결정과 9개 known issue 연결
  - 1.3.0 version 기록과 reusable templates
  - current context/handoff와 version index
- 중요 결정: DEC-001, DEC-010
- 발생 문제: 저장소가 큰 미커밋 작업 트리이며 macOS script는 1.2.1.
- 해결: 다른 변경을 수정하지 않고 ISSUE-WORK-001/ISSUE-BUILD-001로 기록.
- 검증: 문서 구조, link target, ID/status count 검사.
- 남은 작업: commit/tag·배포 여부는 사용자 승인과 별도 작업 필요.

## 2026-07-29 — 전문 소프트웨어형 UI 시스템 개선

- 목적: 기능과 6단계 흐름을 유지하면서 정보 위계, 한글 가독성, 컨트롤 상태, 패널 구조와 리사이즈 품질 개선.
- 요구사항: UI-004
- 주요 파일: `app.py`, `stage4_design_effects.py`, `stage5_render.py`
- 구현:
  - 3단계 표면·텍스트·상태 색상 토큰과 Noto Sans KR 타이포그래피
  - 공통 버튼의 기본/hover/focus/disabled 상태와 역할별 계층
  - padding·focus·disabled 상태가 있는 입력창/체크박스/표/scrollbar/scale 스타일
  - 상단 진행 내비게이션, 프로젝트 섹션, 파일 drop 빈 상태의 위계 재배치
  - 디자인·렌더 좌우 패널 경계와 리사이즈 sash 개선
  - 밝은 모드 전환 시 내비게이션 내부 프레임·진행점·버튼 색상이 남던 문제 수정
- 유지: 단계 순서, 이벤트 핸들러, 저장 형식, 미리보기/출력 좌표, 다국어·RTL.
- 검증: 전체 49 tests, UI/state 19 tests, Ruff F/B, locale 0/0, 최소·기본·확장 크기와 긴 120행 목록.

## 2026-07-29 — 효과 카드·전역 오디오·최종 UI 마감

- 목적: 긴 효과 설정을 추가형 카드로 정리하고 전역 오디오를 독립 bus로 구현하며 Stage 4·5 light/resize와 행동 피드백을 마감.
- 요구사항: EFFECT-002, AUDIO-004, UI-005
- 주요 파일: `app.py`, `stage4_design_effects.py`, `stage5_render.py`, `audio_pipeline.py`, `ui_state.py`, `locales/`, tests
- 구현:
  - Stage 4 preview 좌측, 효과·설정 inspector 우측 배치와 최소/대형 창 sash 검증
  - 빈 효과 목록, 검색·카테고리·스크롤·키보드 선택 메뉴, 추가된 효과 카드와 카드/섹션 reset
  - 위험 행동의 red hover와 추가 행동의 green hover
  - 음악/정규화/환경음/고급 전역 오디오 accordion과 선택 환경음 enable·volume
  - 독립 music/ambient/master bus와 실제 preview stem 기반 L/R meter
  - 환경음 2-stream 비동기 loop와 최종 반복 media 전체에 연속 환경음 합성
  - Stage 5 light root 하드코딩 제거와 전역 오디오 읽기 전용 요약
  - effect/audio 구형 프로젝트 migration과 page plain state deep copy
- 중요 결정: DEC-011, DEC-012
- 발생 문제:
  - stem `asplit` 뒤 `music_bus_main`을 master가 소비하지 않아 FFmpeg filtergraph 오류
  - ambient `amix` duration 설정이 결과를 목표보다 길게 만듦
  - Windows clean build가 10분 도구 제한을 넘겼지만 PyInstaller child는 계속 진행
- 해결:
  - split 뒤 current label을 main output으로 갱신
  - ambient bus는 shortest, master bus는 first 기준으로 duration 고정
  - 완료된 COLLECT를 확인한 뒤 Tcl/Tk root 복사와 ZIP 단계를 이어서 수행
- 검증:
  - 63 tests, 11 locale 0/0, py_compile, Ruff F/B, pip check
  - preview/final integrated LUFS 차이 -0.01 dB, True Peak 차이 +0.26 dB
  - Stage 4·5 최소·기본·대형·긴 효과 목록·빈 상태 캡처
  - Windows onedir 1,419 files / 387.9 MB, ZIP 162,349,669 bytes
- 남은 제한: 카드 순서는 inspector 정리 순서이며 renderer 합성은 기존 고정 의미 순서. macOS/GPU/모든 DPI·번역 장문은 미검증.

## 2026-07-30 — 네이티브 시작 화면과 독일어·러시아어

- 목적: 실행 직후 피드백을 제공하고 메인 창 준비 전까지 시작 화면을 유지하며 지원 언어를 11개로 확장.
- 요구사항: UI-002, UI-006, I18N-001, PERF-001, BUILD-001
- 주요 파일: `native_launcher.cs`, `app.py`, `app_icon.png`, `app_icon.ico`, `app_splash.png`, build scripts, `i18n.py`, `locales/de-DE.json`, `locales/ru-RU.json`
- 구현:
  - 약 29KB WinForms launcher가 core보다 먼저 240×180 투명 심볼 표시
  - Tk 로딩 splash가 보이면 native icon을 닫고 실제 main 직전에 loading splash 종료
  - PyInstaller 내장 splash를 제거하고 아이콘·로딩·메인 세 화면의 소유권 분리
  - 배경 없는 RGBA 브랜드 아이콘과 per-pixel alpha layered window 적용
  - 독일어·러시아어 각 661개 leaf와 plural rule, 11개 언어 popup layout 적용
- 중요 결정: DEC-013
- 검증: 63 tests, 11 locale 0/0, py_compile, Ruff F/B, pip check, C# compiler 통과.
- 실측: native 2.53초, loading 53.09초, main 87.24초, 두 전환 공백 0.2초 미만, main 뒤 잔류 없음.
- 남은 작업: core cold-start 자체의 import/profile 최적화는 ISSUE-PERF-001.
