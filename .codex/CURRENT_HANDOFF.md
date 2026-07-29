# 현재 작업 인수인계

- 현재 버전: 1.3.0
- 다음 버전: 1.3.1
- 상태: 1.3.0 종료·정식 릴리스 완료, 1.3.1 작업 시작 전
- 다음 버전 목표: 버그 개선 및 최적화
- 상세 인수인계: `docs/versions/1.3.0/HANDOFF.md`
- 시작 문서: `docs/versions/1.3.1/VERSION_OVERVIEW.md`

## 완료 기준점

- code/tag: `v1.3.0` / `f5e7c1a`
- release note main: `04c281f`
- GitHub Actions: run `30471288589` Windows·macOS·publish 성공
- release assets: Windows ZIP, macOS ZIP, `setup.bat`, `setup_mac.sh`
- tests: 63 passed, locale 0/0, Ruff F/B, py_compile, pip check

## 완료

- 6단계 흐름, Stage 4/5 분리, trim/DnD/preview/repeat/save 회귀 해결
- 전문 UI, 11개 언어, effect card, global audio/ambient/meter
- native→loading→main splash, Windows runtime smoke, 양 플랫폼 CI package

## 부분 완료·미구현

- 부분: CLIP-001, PREVIEW-001, DESIGN-001, VIS-001, RENDER-001, I18N-002, UI-004, BUILD-001, EFFECT-002
- 미구현: 환경음 scheduler, momentary/short-term LUFS, effect multi-instance/z-order, 정확히 자르는 repeat, PC 종료 예약

## 1.3.1 이월

- 요구사항: PERF-001, PREVIEW-001, DESIGN-001, VIS-001, RENDER-001, UI-004, EFFECT-002, BUILD-001, I18N-002, CLIP-001
- 문제: ISSUE-DATA-001, ISSUE-ARCH-001, ISSUE-TEST-001, ISSUE-I18N-001, ISSUE-BUILD-002, ISSUE-BUILD-003, ISSUE-CI-001, ISSUE-UI-003

## 첫 작업

1. baseline tests를 실행한다.
2. `app.py` startup import와 `_LazyStage`를 profile해 PERF-001의 실제 병목을 수치화한다.
3. `app.py` duration 표시와 `repeat_settings.estimate_group_duration()` 차이를 재현 test로 만든다.
4. 측정 전 native splash나 대형 library를 임의로 제거하지 않는다.

## 먼저 읽을 경로

1. `AGENTS.md`
2. `.codex/CURRENT_CONTEXT.md`
3. `docs/versions/1.3.1/VERSION_OVERVIEW.md`
4. `docs/versions/1.3.0/HANDOFF.md`
5. `docs/KNOWN_ISSUES.md`, `docs/DECISIONS.md`
6. `app.py`, `project.py`, `repeat_settings.py`, `timeline_utils.py`
7. `stage4_design_effects.py`, `video_gen.py`, `audio_pipeline.py`
