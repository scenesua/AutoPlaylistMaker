# 1.3.0 관련 문제

상세 내용과 해결 이력은 [`../../KNOWN_ISSUES.md`](../../KNOWN_ISSUES.md)를 기준으로 한다.

| 문제 ID | 1.3.0 상태 | 영향 |
|---|---|---|
| ISSUE-BUILD-001 | 해결 | 1.3.0 버전·asset·locale·모듈 동기화, 릴리스 전 macOS CI 빌드 필수 |
| ISSUE-PERF-001 | 체감 완화·분석 중 | 아이콘 2.53초, 로딩 53.09초, main 87.24초 |
| ISSUE-ARCH-001 | 보류 | 반복 API 중복 |
| ISSUE-DATA-001 | 확인 필요 | 그룹 길이 표시 경로 불일치 가능 |
| ISSUE-TEST-001 | 미해결 | preview/output 시각 동일성 최종 승인 불가 |
| ISSUE-I18N-001 | 확인 필요 | 번역 의미 품질 승인 불가 |
| ISSUE-BUILD-002 | 보류 | 선택적 Numba TBB 경고 |
| ISSUE-UI-001 | 해결 | transparent RGBA icon과 로딩 splash 캡처 확인 |
| ISSUE-WORK-001 | 해결 | `v1.3.0` 릴리스 태그를 기준점으로 사용 |

## 2026-07-29 최종 상태

- 해결: ISSUE-AUDIO-001 (`asplit` 뒤 `music_bus_main` 미연결). 시간 제한이 아니라 filtergraph label 연결 오류였다.
- 해결: ISSUE-UI-002 (Stage 5 밝은 모드 고정 회색 root/gutter).
- 해결: ISSUE-UI-001 (배경 없는 RGBA brand asset과 layered native launcher).
- 해결: ISSUE-BUILD-001 (Mac 빌드 구성 동기화와 양 플랫폼 성공 후 게시 gate).
- 해결: ISSUE-WORK-001 (`v1.3.0` 태그와 GitHub 릴리스 기준점).
- 유지: ISSUE-PERF-001, ISSUE-TEST-001, ISSUE-I18N-001, ISSUE-BUILD-002.
- 범위 제한: 효과 카드 순서는 renderer z-order가 아니며, 환경음 event scheduler와 momentary/short-term LUFS는 구현하지 않았다.
- 최신 검증: 63 tests, 11 locale 0/0, native→loading→main 전환 공백 0.2초 미만·잔류 splash 없음.
