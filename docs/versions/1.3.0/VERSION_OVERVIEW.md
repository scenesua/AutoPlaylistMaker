# 1.3.0 버전 개요

- 사용자가 지정한 현재 버전: 1.3.0
- 다음 버전: 1.3.1
- 이전 비교 버전: 1.2.1
- 작업 기간: 2026-07-25 ~ 2026-07-30
- 릴리스 기준: `v1.3.0` / `f5e7c1a`
- 릴리스 노트 보강: `04c281f`
- 공개 릴리스: `https://github.com/scenesua/AutoPlaylistMaker/releases/tag/v1.3.0`
- 상태: 종료·정식 릴리스

## 주요 목표

- 단일 대형 편집·렌더 화면을 디자인/효과와 렌더 단계로 분리한다.
- 음원 트림, 수동 분배 DnD, 미리보기·FFmpeg·반복 기능의 실동작 회귀를 해결한다.
- 프로젝트 모든 단계의 상태를 저장·복원한다.
- 전문 소프트웨어형 다크·라이트 UI와 11개 언어 전환을 적용한다.
- 효과를 명시적으로 추가하는 구조와 독립 전역 오디오 버스를 구현한다.
- 실행 즉시 피드백을 주는 네이티브→로딩→메인 시작 흐름을 만든다.
- Windows와 macOS 1.3.0 패키지를 한 릴리스에 게시한다.

## 완료된 기능

- CORE-001 6단계 제작 흐름과 Stage 4/5 책임 분리
- AUDIO-001~004 분석, 파형 trim, 트랙 편집, 전역 오디오·환경음·meter
- DIST-001~003 자동/수동 분배, DnD indicator, 최초 `Mix N` 생성
- PREVIEW-002 두 곡 전환 preview
- FONT-001 검색형 폰트 팝업
- EFFECT-001 beat/CRT/visibility와 REPEAT-001 완성 영상 반복
- RENDER-002 공통 FFmpeg 탐색
- SAVE-001/002 project format v4, atomic save, backup/relink
- I18N-001, UI-001 11개 locale와 안정적 선택 ID
- UI-002/003/005/006 브랜딩, 후원 링크, Stage 4 배치, 두 단계 splash
- SHUTDOWN-001 종료 자원 정리
- DOC-001 공통·버전·CURRENT 기록 체계

## 부분 완료된 기능

- CLIP-001: 실제 이미지/영상 조합의 전체 수동 회귀 검사가 부족하다.
- PREVIEW-001, DESIGN-001, VIS-001: 공통 renderer와 자동 검사는 연결됐지만 네 해상도 및 모든 visualizer 스타일의 수동 비교가 남아 있다.
- RENDER-001: CPU·취소는 검증했지만 NVIDIA/Intel/AMD 실제 encoder는 미검증이다.
- I18N-002: 11개 locale 구조는 통과했지만 원어민 의미 검수는 하지 못했다.
- UI-004: 주요 창 크기와 긴 목록은 확인했지만 모든 DPI·장문 locale 전수 검사는 남아 있다.
- BUILD-001: Windows 실행·종료와 양 플랫폼 CI 빌드는 성공했지만 macOS `.app` 실제 실행·종료는 미검증이다.
- EFFECT-002: 빈 목록, 검색형 category popup, keyboard/scroll/reset은 구현했지만 계층형 하위 메뉴와 edge flip은 미구현이다.

## 미구현·범위 밖

- 환경음 폴더/event scheduler
- momentary/short-term LUFS
- 효과 다중 인스턴스와 사용자 정의 renderer z-order
- 목표 시간에 맞추기 위한 마지막 곡/반복 강제 절단
- PC 종료 예약
- 새 UI framework 또는 database

## 반드시 유지할 동작

- `project.json` format v4와 원자적 저장·이전 형식 migration
- 번역 문자열이 아닌 stable ID 저장
- 미리보기/출력 공통 `LiveFrameRenderer`와 linked resolution/FPS
- 마지막 playlist를 자르지 않는 전체 반복
- FFmpeg streaming 처리와 공통 resolver
- 명시적으로 추가한 효과만 활성화하되 기존 프로젝트는 legacy 효과를 복원
- music/ambient/master 독립 bus와 최종 반복 timeline의 연속 환경음
- native icon→진행 loading→main handoff와 종료 후 하위 process 0

## 종료 판단

- 63개 자동 테스트, locale 11종, Ruff F/B, py_compile, pip check 통과
- Windows 실제 folder package 실행·종료 성공
- GitHub Actions run `30471288589`에서 Windows·macOS build와 publish 성공
- v1.3.0 정식 릴리스와 자산 4종의 크기·SHA-256·ZIP 내부 핵심 파일 확인
- 남은 문제는 `KNOWN_ISSUES.md`에 재현 조건과 1.3.1 이월 상태로 기록
