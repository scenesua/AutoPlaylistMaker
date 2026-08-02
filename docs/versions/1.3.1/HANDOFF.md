# 1.3.1 작업 인수인계

## 2026-08-01 최종 상태 추가

- 최종 Windows ZIP SHA-256: `77AA7E9F7E50C374393E6BC4D64FC3354A7DD0E11EA4445D95DAF9C91159C074`.
- 최종 onedir: 1,487 files / 713.3MB, ZIP 403,115,334 bytes.
- 단일 사용자 EXE·단일 프로세스이며 native launcher/core EXE 분리는 없다.
- 효과 화면 기본 분할은 미리보기 3 : 효과 랙 1이다. 사용자가 조정한 sash는 초기 적용 뒤 강제로 되돌리지 않는다.
- packaged 실행은 Stage 1~5와 Stage 4/5 모듈을 최초 진입까지 지연한다. 비활성 효과 UI가 첫 실행 병목인 구조가 아니다.
- cold smoke는 스플래시 11.735초, 메인 42.491초였다. Python 진입 전 PyInstaller 파일 접근 약 11초와 Tk/TkinterDnD 초기화가 주 병목이다.
- `--safe` 비교에서 TkinterDnD 제외 시 메인이 35.901초였다. 파일 드래그앤드롭 보존 때문에 기본 경로에서는 유지했다.

- 버전: 1.3.1
- 이전 버전: 1.3.0
- 작성일: 2026-07-30
- 기준 커밋: `3768c3e`
- 작업 폴더: `D:\aldente yt\AutoPlaylistMaker_v1.3.1`
- 브랜치: `codex/v1.3.1`
- 상태: 구현·Windows 검증 완료, 미커밋

## 완료

- 프로젝트 생성·저장·lazy Stage·분석 수명주기 회귀 수정
- 모든 background Tk callback을 메인 UI queue 경로로 정리
- trim·crossfade 그룹 길이 계산 통일
- 효과 category submenu와 edge flip 구현
- heavy import 지연과 splash Tk root 재사용
- Numba 선택 backend 제외와 GitHub Actions 갱신
- 전체 92 tests 통과(환경 제한 21 skipped), locale, Ruff, py_compile, pip check 통과
- 네 해상도 preview/output 비교 통과
- Windows 1.3.1 onedir/ZIP 빌드·GUI 시작·정상 종료·잔류 프로세스 0 확인
- FL Studio의 개념만 참고한 미리보기 오른쪽 고정 효과 랙과 효과별 설정 창
- 단일 인스턴스/활성화/경고/저장 복원 및 실제 overlay 순서 연결
- visualizer 배경 보존, trim beat timeline, preview audio 상태 보존 수정
- 11개 locale의 새 효과 랙 문자열
- 1초 오디오 포함 실제 비트 효과 MP4 렌더 성공

## 남은 일

1. 실제 macOS에서 1.3.1 `.app` 시작·FFmpeg 탐색·종료를 확인한다.
2. 지원 GPU 장치에서 NVENC/QSV/AMF 실제 렌더를 확인한다.
3. 최신 action workflow를 원격 GitHub Actions에서 실행한다.
4. Windows 단일 EXE 기준 main 64.536초인 cold-start를 추가 profile한다.
5. 원어민 번역과 고DPI·장문 UI 수동 검수를 진행한다.

## 반드시 유지할 동작

- project format v4, atomic save, legacy migration, media backup/relink
- stable choice ID와 11개 locale
- preview/output 공통 renderer와 독립 미리보기 품질; auto는 최종 출력 종횡비만 따른다
- 마지막 playlist 비절단 repeat
- music/ambient/master 독립 bus
- PyInstaller splash→loading→main 흐름과 정상 종료 후 child process 0

## 주의

- 현재 변경은 커밋·stage하지 않았다.
- `build/`, `dist/`, `test_artifacts/`는 생성 산출물이며 직접 수정하지 않는다.
- 1.3.0 원본·릴리스 폴더의 내용을 1.3.1 기록으로 덮어쓰지 않는다.
- 렌더 합성 단계가 다른 효과의 순서를 임의로 이동 가능하게 만들지 않는다. 현재 실제 이동 가능한 단계는 album/logo뿐이다.
- `sound_effect_library/`는 1.3.1 내장 자산이다. 매니페스트에 등록되지 않은 사용자 파일은 삭제하지 않는다.

## 2026-07-30 환경음 작업 인계

- 런타임: `ambient_library.py`, `ambient_engine.py`, `audio_pipeline.py`
- UI: `stage4_design_effects.py`
- 개발용 재처리: `python tools/process_sound_library.py sound_effect_library`
- 현재 매니페스트는 95개 자산을 포함한다. `unclassified` 27개와 `needs_review` 56개를 임의로 활성화·확정하지 않는다.
- 다음 우선순위는 장시간·고밀도 렌더 스트레스 검증, 56개 출처 확인, `unclassified` 수동 분류다.

## 2026-08-01 구조 정정

- 환경음은 `active_effect_ids`의 `ambience_mixer` 단일 슬롯이다. 비·천둥 등 category를 별도 효과로 만들지 않는다.
- `global_audio`에 환경음 UI 상태를 다시 넣지 않는다. 렌더 호출 직전에만 `ambience_mixer`를 audio settings에 결합한다.
- 환경음 렌더는 `audio_pipeline.render_ambient_bus()`의 bounded chunk/batch 경로를 유지한다.
- 최종 Windows ZIP SHA-256: `E33EC7E95CA758E13D0E957451871A360BE76871AB8343DF9EEF63FC97F11E9B`.

## 2026-08-01 최종 코드 리뷰

- 배치 기준: 미리보기 왼쪽, 효과 랙 오른쪽 고정. 효과 랙 `Toplevel` 금지.
- 수정된 리뷰 발견: 종료 callback 이중 삭제, progressbar timer 수명, 분석 단계 표시 시점, 변경된 소스의 메모리 캐시 재사용, 잘못된 사용자 해상도 잔류.
- 배포 구조: onedir 안의 단일 사용자 EXE. `native_launcher.cs`와 `.core.exe` 경로는 제거했다.
## 2026-08-02 최종 상태

- 실시간 미리보기, Render Space, 최종 타임라인 화면 꺼짐, 슬라이더 입력 규칙, 환경음 루프 계획과 렌더 완료 콜백 수정 완료.
- deep-code-reviewer 검토에서 두 트랙 미리보기 재구성 누락, 타임라인 offset, 취소 pipe 정리, manifest 절대경로, 효과 메뉴 테스트 방식을 추가 보정했다.
- Lullaby Scene의 검증된 processed loop 14개를 CC0-1.0 사용자 확인 상태로 내부 이식했다. 외부 프로젝트 런타임 의존 없음.
- 최종 Windows onedir 재빌드 및 smoke 통과. ZIP SHA-256: `34701F53BEC897E3CD98977E6651B9D49E9D9F6E86374DEA4ECAC50B4E240F19`.
- 배포 후보: `dist/AutoPlaylistMaker_v1.3.1_windows_x64.zip`.
- 아직 commit, tag, push, GitHub release는 수행하지 않았다.
- 남은 수동 확인: 실제 패키지 마우스 조작 전 범위, 환경음 장시간 주관 청취, macOS/GPU.
