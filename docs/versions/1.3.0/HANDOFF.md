# 1.3.0 인수인계

- 작성일: 2026-07-29
- 버전: 사용자 지정 1.3.0
- 기준: `de32dbf` + 큰 미커밋 작업 트리
- 상태: 주요 기능·자동 테스트·Windows 후보 빌드 완료, 정식 릴리스 미확정

## 마지막 완료 작업

- 전문 도구형 공통 UI 디자인 시스템, Noto Sans KR, 컨트롤 상태와 패널 위계를 적용했다.
- dark/light × 6 Stage × 3개 창 크기와 120행 긴 목록을 검증했다.
- 기존 대화·실제 코드·Git·테스트를 대조해 프로젝트 기억 체계를 구축했다.
- 29개 요구사항, 23개 기능, 10개 결정, 9개 known issue를 연결했다.
- 코드 정리 후 49 tests와 Windows folder package smoke를 통과했다.

## 변경한 주요 파일

- 기능 코드: 현재 `git status`의 수정·신규 파일 전체
- 이번 인수인계 작업: `AGENTS.md`, `CHANGELOG.md`, `docs/`, `.codex/`

## 현재 코드 상태

- Windows 1.3.0 후보 bundle이 실행되고 정상 종료된다.
- 프로젝트 save format은 v4다.
- 11개 locale 구조 검사는 통과한다.
- Stage 4가 design/effects/repeat를, Stage 5가 render queue를 소유한다.
- 미리보기와 output은 공통 renderer와 linked resolution/FPS를 사용한다.
- 작업 트리는 깨끗하지 않다. 관련 없는 변경을 reset하면 안 된다.

## 미완료·막힌 문제

1. ISSUE-WORK-001: 검증된 변경 commit/tag 없음
2. ISSUE-BUILD-001: macOS script가 1.2.1
3. ISSUE-PERF-001: cold startup 약 77초
4. ISSUE-TEST-001: 네 해상도 시각 비교 없음
5. ISSUE-I18N-001: 원어민 번역 검수 없음
6. 실제 GPU encoder 검증 없음
7. DATA-001과 ARCH-001은 동작 변경 위험 때문에 미수정

## 다음 작업 순서

1. 사용자가 다음 작업 버전을 직접 명시했는지 확인
2. 현재 `git status`와 diff를 보존한 채 ISSUE-WORK-001 처리 방침 결정
3. 요청 범위에 따라 ISSUE-BUILD-001 또는 ISSUE-PERF-001 중 하나만 독립적으로 처리
4. 관련 자동·수동 검사를 실행하고 공통/버전 문서 상태 갱신

## 반드시 유지할 동작

- `docs/PROJECT_OVERVIEW.md`의 핵심 특성
- DEC-002~DEC-009
- AUDIO-002, DIST-003, REPEAT-001, SAVE-001, I18N-001, SHUTDOWN-001

## 최근 검증

[`TEST_RESULTS.md`](TEST_RESULTS.md)를 기준으로 한다. 49 tests, Windows folder build, ZIP, main window, 잔류 프로세스 0을 확인했다.

## 작업 재개 시 읽을 파일

1. `AGENTS.md`
2. `docs/PROJECT_OVERVIEW.md`
3. `docs/REQUIREMENTS.md`
4. `docs/FEATURE_STATUS.md`
5. `docs/KNOWN_ISSUES.md`
6. `.codex/CURRENT_CONTEXT.md`
7. `.codex/CURRENT_HANDOFF.md`
8. 이 파일
9. 현재 Git status/diff

## 2026-07-29 최종 인계

- EFFECT-002, AUDIO-004, UI-005 구현과 검증을 완료했다.
- Stage 4는 preview-left/inspector-right이며 효과는 빈 목록에서 명시적으로 추가한다.
- 전역 audio bus와 stem meter, 반복 최종 timeline 환경음, Stage 5 light root, danger/success hover를 완료했다.
- FFmpeg `music_bus_main` 미연결 오류는 timeout이 아니라 `asplit` 뒤 label 갱신 누락이었고 해결됐다.
- 63 tests, 11 locale 0/0, py_compile, Ruff F/B, pip check가 통과했다.
- Windows onedir/ZIP을 새로 만들고 main window 52.350초, graceful exit, 잔류 process 0을 확인했다.
- 배포 ZIP SHA-256: `27FD5A609DBD57DC77FA1B1EB4F92E437FC1954E02AA969AC85625876FFA223E`.
- 남은 제한: macOS/GPU/모든 DPI·장문 locale 미검증, 카드 순서는 renderer z-order가 아님, 환경음 event scheduler·momentary LUFS 없음, 작업 트리 미커밋.

## 2026-07-30 네이티브 시작 화면·11개 언어 인계

- Windows 배포 진입점은 약 29KB `AutoPlaylistMaker_v1.3.0.exe`이고 실제 앱은 `AutoPlaylistMaker_v1.3.0.core.exe`다.
- 런처는 투명 `app_splash.png` 심볼을 띄우고 Tk 진행 로딩 창이 보이면 닫는다. 로딩 창은 main 직전에 닫힌다.
- 최종 실측은 native 2.53초, loading 53.09초, main 87.24초, 두 전환 공백 0.2초 미만, 잔류 없음이다.
- 브랜드 자산은 배경 없는 RGBA 재생·목록 심볼이며 컬러키가 아닌 per-pixel alpha를 사용한다.
- 독일어 `de-DE`, 러시아어 `ru-RU`를 더해 총 11개 locale이며 popup 11개 항목이 잘림 없이 표시된다.
- 최신 검증은 63 tests, locale 0/0, py_compile, Ruff F/B, pip check, C# compile 통과다.
- core cold-start 시간 자체는 여전히 ISSUE-PERF-001이며, 외부 런처를 제거하지 말고 별도로 최적화해야 한다.
