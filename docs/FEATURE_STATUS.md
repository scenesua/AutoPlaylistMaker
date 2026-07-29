# 기능 구현 상태

`완료`는 UI·실행·저장·오류 처리·검증이 확인된 경우에만 사용한다. 세부 완료 조건은 [`REQUIREMENTS.md`](REQUIREMENTS.md)를 기준으로 한다.

| 기능 ID | 기능명 | 요구사항 | 최초/마지막 버전 | 상태 | 관련 파일 | UI | 실행 | 저장·복원 | 테스트 | 제한 사항 / 다음 작업 |
|---|---|---|---|---|---|---|---|---|---|---|
| FEAT-001 | 6단계 작업 흐름 | CORE-001 | 기존 / 1.3.0 | 완료 | `app.py`, Stage 4·5 | 연결 | 연결 | 연결 | UI 상태 테스트 | 내부 클래스 번호 정리 여부는 보류 |
| FEAT-002 | 음원 분석·캐시 | AUDIO-001 | 기존 / 1.3.0 | 완료 | `analyzer.py`, `project.py` | 연결 | 연결 | 연결 | cache 보존 테스트 | 손상 음원 표본 확대 |
| FEAT-003 | 파형 트림 편집 | AUDIO-002 | 1.3.0 / 1.3.0 | 완료 | `app.py` | 연결 | 연결 | 연결 | drag·modifier 테스트 | 실제 고DPI 장치 수동 검사 |
| FEAT-004 | 볼륨·fade·미리듣기 | AUDIO-003 | 1.2.1 / 1.3.0 | 완료 | `app.py`, `audio_preview.py`, `audio_pipeline.py` | 연결 | 연결 | 연결 | FFmpeg RMS 테스트 | 오디오 장치별 수동 재생 |
| FEAT-005 | 자동 분배 | DIST-001 | 기존 / 1.3.0 | 완료 | `distributor.py`, `app.py` | 연결 | 연결 | 연결 | core 테스트 | 휴리스틱 최적성 보장 없음 |
| FEAT-006 | 수동 DnD·자동 그룹 | DIST-002, DIST-003 | 1.3.0 / 1.3.0 | 완료 | `app.py` | 연결 | 연결 | 연결 | UI 상호작용 테스트 | 실제 장시간 목록 수동 검사 |
| FEAT-007 | 클립 목록·썸네일 | CLIP-001 | 1.2.1 / 1.3.0 | 부분 완료 | `app.py`, `project.py`, `video_gen.py` | 연결 | 연결 | 연결 | 저장 호환 테스트 | 전체 이미지/영상 UI 회귀 검사 필요 |
| FEAT-008 | 디자인·오버레이·텍스트 | DESIGN-001 | 기존 / 1.3.0 | 부분 완료 | Stage 4, `video_gen.py` | 연결 | 연결 | 연결 | 상태 복원 테스트 | 네 해상도 시각 비교 필요 |
| FEAT-009 | 검색형 폰트 선택 | FONT-001 | 1.3.0 / 1.3.0 | 완료 | `font_combo.py`, Stage 4 | 연결 | 연결 | 연결 | 검색·키보드 테스트 | 실제 미설치 폰트 fallback 수동 검사 |
| FEAT-010 | 비주얼라이저 | VIS-001 | 기존 / 1.3.0 | 부분 완료 | Stage 4, `video_gen.py` | 연결 | 연결 | 연결 | 공통 렌더 경로 | 스타일별 FPS·시각 검사 필요 |
| FEAT-011 | 비트·CRT·표시 시간 | EFFECT-001 | 기존 / 1.3.0 | 완료 | Stage 4, `video_gen.py`, `timeline_utils.py` | 연결 | 연결 | 연결 | 표시 경계 테스트 | 미적 품질은 사용자 조정 |
| FEAT-012 | 라이브·두 곡 미리보기 | PREVIEW-001, PREVIEW-002 | 1.3.0 / 1.3.0 | 부분 완료 | Stage 4, `video_gen.py`, `audio_preview.py` | 연결 | 연결 | 해당 없음 | 공통 경로 테스트 | ISSUE-TEST-001 미완료 |
| FEAT-013 | 완성 영상 반복 | REPEAT-001 | 1.3.0 / 1.3.0 | 완료 | `repeat_settings.py`, Stage 4·5, `video_gen.py` | 연결 | 연결 | 연결 | 계산·실제 3회 영상 테스트 | 목표 초과가 정상 동작 |
| FEAT-014 | 렌더 큐·설정·재시도 | RENDER-001 | 1.2.1 / 1.3.0 | 부분 완료 | Stage 5, `render_jobs.py` | 연결 | 연결 | 연결 | CPU·cancel 테스트 | GPU 실기기 검증 필요 |
| FEAT-015 | FFmpeg 공통 서비스 | RENDER-002 | 1.3.0 / 1.3.0 | 완료 | `ffmpeg_service.py`, 관련 미디어 모듈 | 오류 UI 연결 | 연결 | 해당 없음 | FFmpeg·패키지 smoke | 플랫폼별 후보 유지 필요 |
| FEAT-016 | 프로젝트 전체 저장 | SAVE-001 | 1.2.1 / 1.3.0 | 완료 | `project.py`, `app.py`, `ui_state.py` | dirty 표시 | 연결 | 연결 | migration·상태 테스트 | 패널 접힘·스크롤은 저장하지 않음 |
| FEAT-017 | 미디어 백업·재연결 | SAVE-002 | 1.2.1 / 1.3.0 | 완료 | `project.py`, `app.py` | 연결 | 연결 | 연결 | 이동·누락·재연결 테스트 | basename 충돌 시 첫 경로 |
| FEAT-018 | 11개 언어·LANG 팝업 | I18N-001, I18N-002, UI-001 | 1.3.0 / 1.3.0 | 부분 완료 | `i18n.py`, `locales/`, `app.py` | 연결 | 연결 | 언어 환경 설정 | 11개 locale 구조·상태 테스트 | 원어민 의미 검수 필요 |
| FEAT-019 | 스플래시·브랜딩 | UI-002 | 1.2.0 / 1.3.0 | 완료 | `app.py`, icon assets, build scripts | 연결 | 연결 | 해당 없음 | 투명 asset·로딩 창 실캡처 | 해당 없음 |
| FEAT-020 | 후원 링크 | UI-003 | 1.2.0 / 1.3.0 | 완료 | `app.py` | 연결 | 연결 | 해당 없음 | 코드 경로 확인 | 외부 사이트는 앱 범위 밖 |
| FEAT-021 | 종료 자원 정리 | SHUTDOWN-001 | 1.3.0 / 1.3.0 | 완료 | `app.py`, preview/render 모듈 | 확인창 | 연결 | dirty 상태 연계 | 패키지 잔류 프로세스 0 | 강제 kill 전 1.5초 대기 |
| FEAT-022 | Windows 폴더형 배포 | BUILD-001 | 1.3.0 / 1.3.0 | 부분 완료 | build scripts, workflow | 해당 없음 | Windows 연결 | 해당 없음 | exe·ZIP smoke | macOS 불일치 ISSUE-BUILD-001 |
| FEAT-023 | 프로젝트 기억 체계 | DOC-001 | 1.3.0 / 1.3.0 | 완료 | `AGENTS.md`, `docs/`, `.codex/` | 해당 없음 | 절차 연결 | Markdown 기록 | 링크·ID 검사 | 이후 버전별 문서만 추가 |
| FEAT-024 | 전문 도구형 공통 UI 시스템 | UI-004 | 1.3.0 / 1.3.0 | 부분 완료 | `app.py`, Stage 4·5 | 연결 | 연결 | 테마 상태 연결 | 63 tests·최소/기본/대형·긴 목록 캡처 | 모든 locale·고DPI 실기기 시각 검수 필요 |
| FEAT-025 | 추가형 효과 카드·선택 메뉴 | EFFECT-002 | 1.3.0 / 1.3.0 | 완료 | Stage 4, `ui_state.py` | 연결 | 연결 | migration 연결 | 빈 상태·reset·deep-copy UI 테스트 | 카드 순서는 inspector 순서, 합성 순서는 기존 고정 의미 순서 |
| FEAT-026 | 전역 오디오·환경음·버스 미터 | AUDIO-004 | 1.3.0 / 1.3.0 | 완료 | `audio_pipeline.py`, Stage 4·5 | 연결 | 연결 | migration 연결 | 실제 FFmpeg stem·반복 환경음·level 비교 | momentary/short-term LUFS·이벤트 스케줄러는 없음 |
| FEAT-027 | Stage 4 좌측 preview·역할 버튼 | UI-005 | 1.3.0 / 1.3.0 | 완료 | `app.py`, Stage 4·5 | 연결 | 해당 없음 | 테마 연결 | light root·hover·3개 창 크기 캡처 | 모든 DPI·번역 장문 수동 검수 필요 |
| FEAT-028 | 두 단계 네이티브·로딩 스플래시 | UI-002, UI-006, PERF-001 | 1.3.0 / 1.3.0 | 완료 | `native_launcher.cs`, `app.py`, build scripts, brand assets | 연결 | 연결 | 해당 없음 | 아이콘 2.53초·로딩 53.09초·메인 87.24초, 전환 공백 <0.2초 | 코어 cold-start 최적화는 별도 |
