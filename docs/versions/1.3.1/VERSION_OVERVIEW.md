# 1.3.1 시작 문서

- 버전: 1.3.1
- 이전 버전: 1.3.0
- 상태: 작업 시작 전

## 이전 버전에서 이월된 작업

- PERF-001 cold-start 병목 profile과 최적화
- ISSUE-DATA-001 group duration 계산 경로 검증
- PREVIEW-001, DESIGN-001, VIS-001 네 해상도·visualizer 회귀 검증
- RENDER-001 실제 GPU encoder 검증
- BUILD-001/ISSUE-BUILD-003 macOS `.app` 실행 smoke
- I18N-002/UI-004 원어민·DPI·장문 UI 검수
- EFFECT-002/ISSUE-UI-003 계층형 category submenu 검토
- ISSUE-ARCH-001, ISSUE-BUILD-002, ISSUE-CI-001 유지보수

## 반드시 유지해야 할 동작

- project format v4, atomic save, legacy migration과 media backup/relink
- stable choice ID와 11개 locale 상태 보존
- preview/output 공통 renderer와 linked resolution/FPS
- 마지막 playlist를 자르지 않는 repeat
- 명시적으로 추가한 effect만 활성화하고 legacy effect를 migration
- music/ambient/master 독립 bus와 최종 반복 timeline 환경음
- native icon→loading progress→main 시작 흐름
- 종료 후 preview/render child process 0

## 초기 목표

- 1.3.0 기능과 데이터 호환성을 유지하며 재현 가능한 버그부터 수정한다.
- cold-start를 단계별로 측정하고 가장 큰 병목만 최적화한다.
- 미검증 플랫폼·해상도·GPU 경로를 실제 증거로 확인한다.
- 부분 구현된 효과 탐색 UX와 문서 상태를 코드와 일치시킨다.
