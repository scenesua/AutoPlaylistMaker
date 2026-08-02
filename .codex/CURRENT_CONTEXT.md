# 현재 프로젝트 컨텍스트

## 2026-08-01 진행 창 포커스 복귀

- 프로젝트 로딩·음원 분석 진행 창은 다른 앱에서 APM으로 복귀할 때 동일한 창을 다시 표시하고 전면으로 올린다.
- 관련 코드: `app.py:TaskProgressOverlay`; 회귀 테스트: `tests/test_ui_interactions.py:test_task_overlay_returns_when_app_is_activated`.

## 2026-08-01 short test 2 후속 상태

- 효과 랙/하단 기본 설정은 세로 sash로 크기 조절 가능하며 기본값은 랙 우선이다.
- 전역 오디오와 미리보기 해상도 설정은 기본 접힘이다.
- `short test 2`처럼 최상위 files/analysis가 비어도 그룹 미디어에서 복구·재분석한다.
- 초기 mixed WAV는 재인코딩 없이 직접 재생해 미리보기 준비 완료를 지연하지 않는다.
- 실제 `short test 2` 로드와 Stage 4 미리보기 검증이 완료됐다.

## 2026-08-01 최신 상태

- 현재 버전: 1.3.1 / 이전 버전: 1.3.0.
- 최종 Windows onedir/ZIP 빌드와 단일 프로세스 GUI smoke가 완료됐다.
- 최종 ZIP SHA-256: `F96EE0D57FBE87E621485EEAD4431F9F668AA01309C86740C9DBA18A9A82FF03`.
- 효과 화면 기본 분할은 미리보기 3 : 효과 랙 1이며 UI 자동 테스트가 실제 비율을 검증한다.
- packaged 앱은 Stage 1~5, 디자인/렌더 모듈, 분석·영상 모듈을 사용 시점까지 지연 로딩한다.
- 현재 우선순위: macOS 실제 smoke, 지원 GPU 실제 encoder 검증, 장문/RTL/DPI 수동 검증.
- 시작 성능 위험: cold 실행에서 Python 진입 전 약 11초, Tk/TkinterDnD 및 메인 루트 생성이 약 27초다. 비활성 효과 UI 선로딩은 원인이 아니다.
- 반드시 유지: 단일 사용자 EXE, 파일 드래그앤드롭, project format v4/legacy migration, 미리보기-렌더 의미 일치, 음악/환경음 독립 bus, FFprobe 완료 검증.
- 관련 코드: `bootstrap.py`, `app.py`, `stage4_design_effects.py`, `build_windows_onedir.ps1`.

- 현재 버전: 1.3.1
- 이전 버전: 1.3.0
- 이번 버전 목표: 1.3.0 호환성을 유지하면서 차단 회귀와 확인 가능한 이월 문제를 우선순위대로 수정
- 상태: 시작·효과 랙·미리보기·렌더 완료 판정 개편, 진행 창 포커스 복귀 수정 포함 Windows 재빌드 완료
- 시작 기준: `3768c3e`
- 작업 브랜치: `codex/v1.3.1`
- 작업 경로: `D:\aldente yt\AutoPlaylistMaker_v1.3.1`

## 현재 우선순위

1. 최종 Windows onedir 시작 시간·스플래시·아이콘·종료 smoke
2. 실제 macOS `.app` 실행·종료와 GitHub Actions 원격 run
3. 지원 GPU 장치의 NVENC/QSV/AMF 실제 렌더
4. 원어민 번역·고DPI·장문 UI 수동 검수

## 완료

- 프로젝트 생성·저장, packaged lazy Stage, 분석 progress 수명주기 회귀
- background 작업의 Tk 직접 호출 제거와 공통 UI queue
- trim·crossfade 기준 그룹 길이 계산 통일
- 효과 category submenu와 화면 경계 반전
- heavy import 지연과 Python splash Tk root 재사용
- 선택적 Numba backend 제외와 GitHub Actions action 갱신
- 92 tests 통과(환경 제한 21 skipped)·locale·Ruff·py_compile·pip check·네 해상도 비교
- Windows 1.3.1 단일 EXE onedir/ZIP 최종 빌드와 GUI 시작·정상 종료
- 미리보기 오른쪽 고정 효과 랙·효과별 설정 창과 단일 인스턴스 상태 저장
- 실제 album/logo 합성 순서, visualizer 배경 보존, trim beat timeline
- 미리보기 오디오 설정 갱신의 위치·재생 상태 보존
- 분석 진행 창의 비모달 수명주기, 실제 단계 표시, 변경된 소스 cache 무효화
- 단일 Windows EXE와 PyInstaller splash, 창 resize/maximize/F11 전체 화면
- 효과 랙 기본 폭 280px/최소 220px, 미리보기 왼쪽·랙 오른쪽 배치
- 기본 효과 슬롯 `전역 오디오 → 장면 전환 → 기본 배경`과 환경음 단일 사용자 효과
- 완료 영상 반복 설정을 Stage 5 렌더 전용으로 이동
- 미리보기 범위 기본 2곡과 최종 출력에서 독립된 품질·해상도
- 렌더 상태·인코더 PID 기록과 FFprobe 기반 최종 산출물 검증

## 이월된 작업

- ISSUE-PERF-001 추가 최적화
- ISSUE-BUILD-003 macOS 실제 GUI smoke
- RENDER-001 실제 GPU encoder 검증
- ISSUE-I18N-001 원어민 의미 검수
- UI-004 모든 DPI·장문 locale 수동 검수

## 주요 위험

- packaged start는 PyInstaller 파일 검사와 보안 소프트웨어 영향이 커 source import 개선만으로 충분하지 않다.
- macOS와 GPU 결과는 현재 Windows/비지원 GPU 환경에서 완료로 올릴 수 없다.
- project format v4 변경은 금지하며 schema 변경 시 별도 migration 결정이 선행돼야 한다.

## 반드시 유지해야 하는 동작

- project format v4, atomic save, v2·v3 migration, media backup/relink와 analysis cache
- stable choice ID와 언어 변경 후 상태
- trim grab/release, 최초 `Mix N` rollback, 마지막 playlist 비절단
- preview/output 공통 renderer, 출력 종횡비를 따르는 auto 미리보기와 독립 custom 품질
- global audio bus와 종료 후 하위 프로세스 0

## 관련 문서와 코드 경로

- 버전 기록: `docs/versions/1.3.1/`
- 이전 인수인계: `docs/versions/1.3.0/HANDOFF.md`
- 공통 상태: `docs/REQUIREMENTS.md`, `docs/FEATURE_STATUS.md`, `docs/KNOWN_ISSUES.md`
- 핵심 코드: `bootstrap.py`, `app.py`, `project.py`, `stage4_design_effects.py`, `stage5_render.py`, `render_jobs.py`, `video_gen.py`, `ffmpeg_service.py`, `ui_state.py`
- 빌드: `build_windows_onedir.ps1`, `build_mac.sh`, `.github/workflows/build.yml`
- 테스트: `tests/test_core.py`, `tests/test_ui_interactions.py`, `tests/verify_layout_fidelity.py`

## 2026-07-30 환경음 개편 상태

- 내장 환경음 95개 등록, 제외 1개 보존, ZIP 4개 안전 처리 완료.
- 현재 우선순위: 장시간 환경음 렌더 스트레스 검증과 미확인 라이선스·분류 정리.
- 주요 위험: 장시간 환경음 렌더 시간, `needs_review` 56개, 비활성 `unclassified` 27개, 자산이 없는 forest 종류.
- 반드시 유지: 등록되지 않은 사용자 파일은 삭제하지 않으며 압축 원본은 모든 후보가 등록 또는 별도 보존된 경우에만 삭제.
- 관련 코드: `ambient_library.py`, `ambient_engine.py`, `audio_pipeline.py`, `stage4_design_effects.py`, `stage5_render.py`.
- 관련 데이터: `sound_effect_library/manifests/sound_library.json`.
- UI·저장 구조: 효과 랙의 단일 `ambience_mixer`; `global_audio`에는 음악·정규화·True Peak만 저장.
- WinError 206 방지: 120초 chunk, 최대 8-input batch, filter script, FFconcat, 중간 ambient bus WAV.
- 최종 Windows 단일 EXE onedir/ZIP 빌드와 GUI smoke 완료. ZIP SHA-256: `F96EE0D57FBE87E621485EEAD4431F9F668AA01309C86740C9DBA18A9A82FF03`.
## 2026-08-01 현재 우선순위 갱신

- Render Space, 실시간 preview, slider 입력, 최종 timeline visibility, 렌더 완료 callback 수정 완료.
- Lullaby Scene 원본 hash/QA/CC0 확인 기반 processed loop 14개 이식 완료.
- 다음 순서: 전체 UI 재검증 → short test 2 실제 preview/짧은 render → Windows onedir rebuild/smoke → 문서 최종화.
- 주요 위험: Windows 미리보기 백엔드의 category gain 무중단 변경 미지원, macOS/GPU/RTL 미검증.
- 관련 경로: `video_gen.py`, `stage4_design_effects.py`, `stage5_render.py`, `app.py`, `ambient_engine.py`, `ambient_library.py`, `audio_pipeline.py`, `sound_effect_library/manifests/processed_loops.json`.
