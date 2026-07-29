# 1.3.0 버전 개요

- 사용자가 명시한 버전: 1.3.0
- 이전 비교 버전: 1.2.1
- 작업 시작일: 2026-07-25
- 기준 커밋: `de32dbf` 위 미커밋 작업 트리
- 상태: 릴리스

## 버전 목표

- 단일 대형 편집·렌더 화면을 디자인/효과와 렌더 단계로 분리한다.
- 음원 트림, 수동 분배 DnD, 미리보기·FFmpeg·반복 기능의 실동작 회귀를 해결한다.
- 프로젝트 모든 단계의 상태를 저장·복원한다.
- 11개 언어 UI가 상태를 잃지 않고 전환되게 한다.
- 1.2 계열을 덮어쓰지 않는 1.3.0 폴더형 Windows 배포를 만든다.

## 포함 기능

- AUDIO-002, AUDIO-003
- DIST-002, DIST-003
- PREVIEW-001, PREVIEW-002
- DESIGN-001, FONT-001, VIS-001, EFFECT-001
- REPEAT-001
- RENDER-001, RENDER-002
- SAVE-001, SAVE-002
- I18N-001, I18N-002, UI-001
- UI-002, UI-003, SHUTDOWN-001, BUILD-001
- DOC-001

## 포함하지 않는 기능

- PC 종료 예약
- 마지막 곡이나 반복 일부를 잘라 목표 시간을 정확히 맞추는 모드
- 새 UI 프레임워크 교체
- 새 데이터베이스 저장 방식
- 사용자 확인 없는 1.3.1 이상 버전 증가

## 이전 버전에서 이월

- 스트리밍 오디오 pipeline과 LUFS 정규화
- 프로젝트 미디어 백업·분석 cache
- 자동 분배·비트 효과·기본 visualizer
- render job cancel/checkpoint

## 반드시 유지할 기존 동작

- `docs/PROJECT_OVERVIEW.md`의 “반드시 유지할 특성”
- DEC-002 프로젝트 호환 저장
- DEC-003 안정적 선택 ID
- DEC-005 전체 플레이리스트 반복
- DEC-006 FFmpeg streaming

## 완료 기준

1. REQUIREMENTS의 1.3.0 대상 항목이 코드·UI·저장·테스트에 연결된다.
2. 전체 unittest, locale, correctness lint, dependency 검사가 통과한다.
3. Windows folder build, ZIP 열기, main window, 정상 종료를 검증한다.
4. ISSUE-BUILD-001, ISSUE-PERF-001, ISSUE-TEST-001 등 미완료 사항을 숨기지 않고 기록한다.
5. 검증된 변경을 commit/tag하고 배포 여부를 `VERSION_INDEX`에 기록한다.

## 현재 진행 상태

- 주요 기능 구현과 자동 테스트: 완료
- Windows 후보 빌드·실행: 완료
- 프로젝트 기억 체계: 완료
- 작업 트리 commit/tag: 릴리스 워크플로에서 완료
- macOS 1.3.0 빌드: GitHub Actions의 릴리스 필수 단계로 구성
- 네 해상도 시각 비교·번역 원어민 검수·GPU 실기기 검사: 미완료
- 시작 성능 병목 분석: 미완료
