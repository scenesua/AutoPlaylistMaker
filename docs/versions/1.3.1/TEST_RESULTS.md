# 1.3.1 테스트 결과

## 2026-08-01 진행 창 포커스 복귀 회귀 검증

- 진행 창을 숨긴 뒤 APM `<FocusIn>`을 발생시키면 같은 창이 `normal`·viewable 상태로 복귀함을 확인했다.
- 분석 worker 종료 전에는 진행 창이 유지되고 종료 뒤에만 닫히는 기존 수명 주기 테스트도 함께 통과했다.
- 관련 UI 테스트 2개, `py_compile`, Ruff F/B, `git diff --check` 통과.
- 수정 반영 Windows onedir 재빌드 성공: 1,487 files, 713.3MB; ZIP 403,115,991 bytes.
- ZIP SHA-256: `F96EE0D57FBE87E621485EEAD4431F9F668AA01309C86740C9DBA18A9A82FF03`.
- 새 EXE smoke: `Auto Playlist Maker v1.3.1` 메인 창 정상 표시, 자식 프로세스 0.

## 2026-08-01 short test 2 및 접이식 UI 검증

- `short test 2`: 오류 없이 로드, 앱 미디어 7개, 오디오 분석 3/3, 그룹 분석 3/3.
- 실제 미리보기: 17.71초, renderer/frame/audio ready, loading overlay 종료, 87,910,876-byte mixed WAV 생성.
- 코어: 21 passed, 7 subtests passed.
- 관련 Stage 4 UI: 4 passed.
- 오디오 파이프라인·직접 WAV 미리보기: 8 passed.
- Ruff F/B, py_compile: 통과.
- UI 캡처: `test_artifacts/stage4_collapsible_layout_final.png` 육안 검증 완료.

## 2026-08-01 최종 재빌드 및 시작 실측

- `py_compile` 및 Ruff F/B: 통과.
- 코어·비주얼라이저·환경음: 35 passed, 7 subtests passed.
- 오디오 파이프라인: 7 passed.
- 효과 랙·환경음 슬라이더·미리보기·반복·렌더 UI: 9 passed.
- 효과 화면 실제 초기 패널 비율: 2.8~3.2:1 자동 검증 통과.
- Windows onedir 빌드: 성공, 1,487 files, 713.3MB. ZIP: 403,115,334 bytes(384.4MB).
- ZIP SHA-256: `77AA7E9F7E50C374393E6BC4D64FC3354A7DD0E11EA4445D95DAF9C91159C074`.
- 최종 EXE cold smoke: 네이티브 스플래시 11.735초, 메인 창 42.491초, child process 0, WM_CLOSE exit 0.
- 같은 EXE `--safe` 비교: 스플래시 11.059초, 메인 창 35.901초. TkinterDnD 초기화가 약 5.8~6.6초를 추가했다.
- 내부 cold timing: 스플래시 생성 0.490초, 앱 import 종료 3.511초, 메인 창 생성 종료 30.972초, 기본 UI 조작 가능 31.110초.
- 외부 EXE 실행부터 Python 진입 전에는 약 11초가 소요됐다.

- 현재 버전: 1.3.1
- 이전 버전: 1.3.0
- 상태: Windows 검증 완료, 외부 장치 검증 잔여

## 자동 검사

- `python -m unittest discover -s tests`: 92 tests 통과, 누적 Tk 메뉴 한도 등 환경 제한 21 skipped
- `python check_locales.py`: 0 errors / 0 warnings, 11 locales
- `python -m ruff check . --select F,B --exclude build,dist`: 통과
- 변경 Python 파일 `python -m py_compile`: 통과
- `python -m pip check`: broken requirements 없음
- `.github/workflows/build.yml` YAML parse: 통과
- `git diff --check`: 통과

## 미리보기/출력

- `python tests\verify_layout_fidelity.py`: 통과
- 1920×1080 MAE 0.400264, p99 1
- 1280×720 MAE 0.400811, p99 1
- 1080×1920 MAE 0.399821, p99 1
- 1080×1080 MAE 0.401785, p99 1
- 보고서: `test_artifacts/layout_fidelity/report.json`
- 비주얼라이저 영역 밖 배경 픽셀 완전 일치: 통과
- 잘린 중복 트랙 beat cache 전역 시간 매핑: 통과
- album/logo 순서 변경의 실제 최종 픽셀 반영: 통과
- 효과 설정 슬라이더 실제 마우스 클릭: 통과
- 효과 랙·설정 창 singleton과 닫기 후 상태 유지: 통과
- 96×64, 1초 WAV 포함 MP4 실제 렌더: 성공, 9,477 bytes

## Windows 패키지

- `build_windows_onedir.ps1`: 성공
- bundle: 1,415 files, 387.6MB
- ZIP: `dist/AutoPlaylistMaker_v1.3.1_windows_x64.zip`, 154.6MB
- ZIP SHA-256: `E99AE4D0F978558729E90B54068C9D82773B8C4012B9D3495B6B96C5F852E573`
- GUI smoke: core main window 31.792초, launcher 실행 기준 54.72초
- 정상 `WM_CLOSE`: 성공, 해당 bundle 잔류 프로세스 0
- PyInstaller 경고: TBB/OpenMP pool은 의도적 제외로만 기록되고 누락 DLL 경고 없음

## 환경 제한

- Windows FFmpeg에는 NVENC/QSV/AMF가 등록돼 있지만 현재 장치에서 세 encoder 모두 open 실패하여 실제 GPU 렌더는 미검증이다.
- macOS `.app` 실행·종료는 Windows 환경에서 실행할 수 없다.
- WSL/bash가 없어 `build_mac.sh`는 현 장비에서 shell syntax 실행 검증을 하지 못했다. 같은 인자 배열 형식을 유지하며 CI 실행이 필요하다.

## 내장 환경음 검증

- 후보 96개, 등록 95개, 보존된 제외 파일 1개, 삭제된 ZIP 4개, 중복 0개.
- 프로젝트 소유자 확인에 따라 내장 원본 95개 전체가 `CC0-1.0 / user_confirmed`이며 attribution은 필요하지 않는다.
- 안전 ZIP 삭제, 경로 탈출 차단, 상대 경로 매니페스트, 중복 제거, 증분 재검색 보존/추가 테스트 통과.
- 실제 내장 rain 10개를 사용한 4초 FFmpeg 렌더 성공: mixed/ambient stem 각각 705,678 bytes.
- `python check_locales.py`: 0 errors / 0 warnings.
- 초기 라이브러리 정리 직후에는 빌드를 보류했으며, 2026-08-01 구조 정정 후 새로 빌드했다.

## 2026-08-01 통합 환경음 효과·재빌드

- 13개 실제 환경음 종류 동시 6초 렌더 성공: 출력 1,058,478 bytes.
- 환경음 중간 렌더의 최대 명령 길이 1,376자, 동시 `-i` 최대 8개, 전체 5개 FFmpeg 명령.
- 효과 랙 단일 슬롯, 중복 추가 방지, 종류별 상태 저장, legacy migration, 실제 마우스 drag를 검증했다.
- 새 Windows onedir: 1,514 files, 585.8MB.
- 새 ZIP: 349,425,340 bytes, SHA-256 `1F1FD37875F86124F8B20BA2A12923A5A3196DF0CF294A761E7C77E61B611A9D`.
- bundle 환경음: 매니페스트 95개, 실제 음원 95개 일치.
- launcher GUI smoke: 메인 창 67.5초, 정상 닫기 후 잔류 프로세스 0.

## 2026-08-01 최종 단일 EXE 재빌드

- `build_windows_onedir.ps1`: 성공, 792.9초.
- bundle: 1,512 files, 585.8MB.
- ZIP: 333.2MB, SHA-256 `E33EC7E95CA758E13D0E957451871A360BE76871AB8343DF9EEF63FC97F11E9B`.
- 사용자 실행 파일: `AutoPlaylistMaker_v1.3.1.exe` 하나. `.core.exe` 없음, `Launcher.exe` 없음.
- 패키지 GUI smoke: main 64.536초, 제목 `Auto Playlist Maker v1.3.1`, 1216×789, maximize box·resize frame 활성, 정상 종료 후 잔류 프로세스 0.
- 소스 UI 실제 좌표 drag: 환경음 rain `-18.0 dB → -12.0 dB`, 저장 상태 즉시 갱신.
- 분석 회귀: 최초 12.495초, 동일 파일 cache 재분석 0.097초. 파일 크기·수정 시각이 바뀌면 cache 무효화 테스트 통과.
- Ruff F/B, py_compile, locale 11개 0 error/0 warning, pip check, git diff check 통과.
- 핵심 UI 3개 및 환경음·오디오 파이프라인·렌더러 22개 테스트 통과. 전체 discovery는 단일 Tk 인터프리터의 누적 menu 한도에서 정지해 종료했으며 제품 단독 실행과 개별 회귀는 통과했다.
## 2026-08-01 추가 검증

- 비 UI: 61 passed, 7 subtests passed.
- Render Space/MP4: 3840x2160, 1920x1080, 960x540, 1280x720, 640x360, 1080x1920, 1080x1080 통과.
- 1920x1080→960x540 MAE 0.589, 3840x2160→960x540 MAE 0.607.
- 최종 타임라인 화면 꺼짐: 10초 실제 MP4에서 0~2초 표시, 2~8초 검정, 8~10초 복귀 및 오디오 유지 확인.
- 환경음: rain/fan/cafe/city 동시 10분 렌더 600.000초, 211,680,092 bytes. 30분 계획 289 segments, processed loop만 선택.
- `short test 2`: format v4 로드, 3/3 분석 복원, 누락 트랙 없음.
- UI 전체 47개 최초 실행에서 3건 실패를 발견했고 번역 해상도 동기화, 초기 preview resume, 신규 실시간 테스트 조건을 수정했다. 영향 테스트 14개는 재통과했으며 전체 UI 재실행은 최종 빌드 전에 수행한다.
## 2026-08-02 최종 통합 검증

- 비 UI 회귀: `62 passed`, `7 subtests passed`.
- 관련 UI 회귀(슬라이더, 효과 메뉴, 미리보기, 해상도, 렌더 완료): `14 passed`.
- Python compileall, Ruff F/B, locale 11개: 통과(0 error / 0 warning).
- Render Space 실제 MP4: 3840x2160, 1920x1080, 960x540, 1280x720, 640x360, 1080x1920, 1080x1080 통과.
- 최종 타임라인 화면 꺼짐: 10초 MP4에서 0~2초 표시, 2~8초 검정, 8~10초 복귀 및 오디오 유지 확인.
- 환경음 rain/fan/cafe/city 동시 10분 렌더: 정확히 600.000초. 30분 계획은 289 segments이며 processed loop를 우선 선택.
- `short test 2`: format v4, 3개 트랙 분석 3/3 복원, 누락 파일 없음. 이전 실제 미리보기 검증에서 renderer/frame/audio ready와 17.71초 미리보기 믹스를 확인했으며 이번 회귀에서는 로드 상태를 재확인했다.
- Lullaby Scene 이식본: 14개 processed OGG, manifest에 절대경로 없음, 모두 `CC0-1.0 / user_confirmed`.
- 첫 최종 빌드 검사에서 processed 자산/manifest 누락을 발견했다. Windows/macOS 빌드 정의를 수정하고 재빌드하여 해결했다.
- 최종 Windows onedir: 1,502 files, 724.4MB. ZIP 414,669,138 bytes.
- 최종 ZIP SHA-256: `34701F53BEC897E3CD98977E6651B9D49E9D9F6E86374DEA4ECAC50B4E240F19`.
- bundle processed OGG 14개, source/packed manifest SHA-256 `663D4EB93E49A301453ACAC8108CC40AE7670F1463029ADD1CE69E6BAA4822FF` 일치.
- 새 EXE cold smoke: 메인 창 43.077초, 제목 `Auto Playlist Maker v1.3.1`, 종료 코드 0, 잔류 프로세스 0.
- 제한: 누적 Tk 전체 UI 테스트는 단일 프로세스에서 느려 개별 격리 실행을 사용했다. 패키지에서 모든 실제 마우스 조합과 장시간 청취 품질은 사용자의 최종 수동 확인이 남아 있다.

## 2026-08-02 빌드 전 심층 리뷰 검증

- `python -m unittest discover -s tests -v`: 116 tests 통과. 이후 추가한 effect matrix·오류 창·로그 테스트는 관련 격리 실행에서 통과했다.
- Ruff F/B, compileall, `git diff --check`, 11개 locale, `pip check`: 모두 통과.
- 실제 MP4 비교 11종: 3840×2160, 2560×1440, 1920×1080, 1440×1080, 1080×1350, 960×540, 854×480, 1280×720, 640×360, 1080×1920, 1080×1080 모두 통과. MP4 프레임 MAE 0.399~0.404.
- 1920×1080→960×540 MAE 0.595, 3840×2160→960×540 MAE 0.659.
- 비·바람·선풍기·카페·천둥 동시 10분 실제 환경음 버스: 600.000초, 44.1kHz stereo, 211,680,092 bytes. 120초 청크 경계 전후 무음·peak 초과·WinError 206 없음.
- 30분 환경음 계획: rain/fan/cafe/wind/thunder/birds/fire/ocean 모두 최종 1,800초까지 생성됨.
- `short test 2`: format v4, 파일 7개, group 1개, track 3개, 분석 3/3 복원, 누락 0, current step 4.
