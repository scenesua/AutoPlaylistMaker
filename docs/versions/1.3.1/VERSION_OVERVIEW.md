# 1.3.1 버전 개요

- 버전: 1.3.1
- 이전 버전: 1.3.0
- 작업 시작일: 2026-07-30
- 기준 커밋: `3768c3e`
- 작업 폴더: `D:\aldente yt\AutoPlaylistMaker_v1.3.1`
- 상태: 구현·Windows 검증 완료, 외부 환경 검증 잔여

## 이번 버전 목표

- 1.3.0 기능과 project format v4 호환성을 유지하면서 릴리스 후 차단 회귀와 확인된 미해결 문제를 우선순위대로 수정한다.
- 분석·저장·내비게이션·테마·길이 계산·효과 메뉴·시작 속도·빌드 재현성을 회귀 테스트와 실제 Windows 패키지로 검증한다.

## 완료

- 프로젝트 이름 검증, 사용자 쓰기 경로, 생성 즉시 format v4 저장
- packaged lazy Stage 상태 복원과 Stage 0→1 이동 검증
- 분석 worker/UI 수명주기와 background Tk 호출 수정
- trim·crossfade 기준 그룹 길이 계산 통일
- 효과 카테고리 하위 메뉴와 화면 경계 반전
- heavy import 지연과 스플래시 Tk root 재사용
- Windows/macOS 선택적 Numba backend 제외와 GitHub Actions 갱신
- 네 해상도 preview/output 픽셀 비교
- Windows 1.3.1 onedir/ZIP 빌드, 실행, 정상 종료

## 반드시 유지해야 할 동작

- project format v4, atomic save, v2·v3 migration, media backup/relink와 analysis cache
- stable choice ID와 11개 locale 상태 보존
- preview/output 공통 renderer와 linked resolution/FPS
- 마지막 playlist를 자르지 않는 repeat
- 명시적으로 추가한 effect만 활성화하고 legacy effect를 migration
- music/ambient/master 독립 bus와 최종 반복 timeline 환경음
- native icon→loading progress→main 시작 흐름
- 종료 후 preview/render child process 0

## 완료 기준 결과

- 핵심 회귀와 확인 가능한 이월 문제는 코드·자동 테스트·Windows 패키지로 검증했다.
- 전체 89 tests가 통과했다(환경 제한 17 skipped). locale 0/0, Ruff F/B, py_compile, pip check도 통과했다.
- 저장 형식은 v4로 유지했고 기존 이동·누락·재연결·legacy migration 테스트가 통과했다.

## 남은 외부 검증

- macOS `.app` 실제 실행·종료
- 실제 지원 GPU 장치의 NVENC/QSV/AMF 렌더
- 11개 언어 원어민 의미 검수와 모든 DPI·장문 UI 수동 검수
- Windows package cold-start 추가 최적화
