# 1.3.0 관련 문제

상세 재현 조건과 해결 이력은 [`../../KNOWN_ISSUES.md`](../../KNOWN_ISSUES.md)를 기준으로 한다.

| 문제 ID | 1.3.0 종료 상태 | 다음 조치 |
|---|---|---|
| ISSUE-BUILD-001 | 해결 | macOS script와 1.3.0 asset/module 동기화 완료 |
| ISSUE-WORK-001 | 해결 | `v1.3.0`/`f5e7c1a`를 릴리스 기준으로 사용 |
| ISSUE-AUDIO-001 | 해결 | `asplit` 뒤 main label 연결 회귀 테스트 유지 |
| ISSUE-UI-001 | 해결 | RGBA icon과 layered native splash 유지 |
| ISSUE-UI-002 | 해결 | Stage 5 light theme 회귀 테스트 유지 |
| ISSUE-PERF-001 | 미해결 | 1.3.1 첫 작업으로 cold-start profile |
| ISSUE-DATA-001 | 확인 필요 | trim/crossfade 기준 duration 경로 대조 |
| ISSUE-ARCH-001 | 보류 | repeat 공개 API 사용처 확인 후 단일화 |
| ISSUE-TEST-001 | 미해결 | 네 해상도 preview/output 캡처 비교 |
| ISSUE-I18N-001 | 확인 필요 | 11개 언어 원어민·장문 UI 검수 |
| ISSUE-BUILD-002 | 보류 | 선택적 TBB/OpenMP backend 경고 조사 |
| ISSUE-BUILD-003 | 확인 필요 | 실제 macOS `.app` 실행·종료 smoke |
| ISSUE-CI-001 | 보류 | Node 24 지원 action major로 갱신 |
| ISSUE-UI-003 | 부분 구현 | 효과 category submenu·edge flip 구현 여부 결정 |
| ISSUE-UI-004 | 사용자 보고·재현 필요 | 테마 전환 뒤 사라지는 UI 요소 복구 |
| ISSUE-PROJECT-001 | 사용자 보고·재현 필요 | 프로젝트 이름 지정과 저장 흐름 복구 |
| ISSUE-NAV-001 | 사용자 보고·재현 필요 | `다음` 단계 이동 차단 복구 |
| ISSUE-ANALYSIS-001 | 사용자 보고·재현 필요 | 분석 진행 창 수명주기와 취소 피드백 복구 |

## 1.3.1 이월 요약

- 최우선 차단 회귀: ISSUE-PROJECT-001, ISSUE-NAV-001, ISSUE-UI-004, ISSUE-ANALYSIS-001
- 최적화·데이터: ISSUE-PERF-001, ISSUE-DATA-001
- 기능 회귀 검증: ISSUE-TEST-001, ISSUE-BUILD-003, 실제 GPU encoder
- UI 마감: ISSUE-UI-003, 모든 DPI·장문 locale
- 유지보수: ISSUE-ARCH-001, ISSUE-BUILD-002, ISSUE-CI-001
- 번역 품질: ISSUE-I18N-001

## 의도적 범위 제한

- 효과 카드 순서는 inspector 정리 순서이며 renderer z-order가 아니다.
- 환경음 event scheduler와 momentary/short-term LUFS는 구현하지 않았다.
- 목표 시간 반복은 마지막 playlist를 자르지 않으므로 목표를 초과할 수 있다.
