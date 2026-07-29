# 현재 프로젝트 컨텍스트

- 현재 종료 버전: 1.3.0
- 다음 작업 버전: 1.3.1
- 다음 버전 목적: 버그 개선 및 최적화
- 상태: 1.3.0 종료·릴리스 완료, 1.3.1 작업 시작 전
- 릴리스 기준: `v1.3.0` / `f5e7c1a`
- 최신 main: `04c281f` + 종료 인수인계 문서
- 권장 작업 경로: `D:\aldente yt\AutoPlaylistMaker_release_v1.3.0`

## 현재 사실

- GitHub v1.3.0은 Latest 정식 릴리스이며 Windows ZIP, macOS ZIP, `setup.bat`, `setup_mac.sh`를 제공한다.
- Actions run `30471288589`에서 Windows, macOS, publish가 모두 성공했다.
- 63 tests, 11 locale 0/0, Ruff F/B, py_compile, pip check가 통과했다.
- project format은 v4이고 stable ID, atomic save, media backup/relink를 유지해야 한다.
- Stage 4는 design/effects/repeat/global audio, Stage 5는 render queue를 소유한다.

## 1.3.1 우선순위

1. ISSUE-PROJECT-001·ISSUE-NAV-001 프로젝트 이름/저장/다음 단계 차단 복구
2. ISSUE-UI-004 양방향 테마 전환 뒤 사라지는 요소 복구
3. ISSUE-ANALYSIS-001 분석 진행 창과 background 작업 수명주기 복구
4. 위 회귀 테스트 고정 후 PERF-001 cold-start profile과 최적화
5. duration·네 해상도·macOS/GPU 검증과 효과/CI 경고 정리

## 주의

- 원본 `AutoPlaylistMaker_v1.3.0` master dirty tree를 reset하거나 source of truth로 사용하지 않는다.
- native splash는 core 속도 문제의 우회 피드백이므로 profile 없이 제거하지 않는다.
- 효과 카드 순서는 renderer z-order가 아니다.
- 미검증 항목을 완료로 올리지 않는다.
