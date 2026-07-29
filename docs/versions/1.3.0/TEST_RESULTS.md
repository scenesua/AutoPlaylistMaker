# 1.3.0 검증 결과

## 2026-07-29

- 환경: Windows 11, Python 3.12.10, PyInstaller 6.21.0
- 기준: `de32dbf` + 현재 미커밋 작업 트리

### 자동 테스트

```text
python -m unittest discover -s tests -v
결과: 49 passed
```

실제 FFmpeg 짧은 audio mix·LUFS·video encode·cancel·전체 3회 반복을 포함했다.

### 구문·린트·로케일·의존성

```text
명시적 루트 Python 파일 py_compile: 통과
ruff --select F,B: 오류 0
python check_locales.py: errors 0, warnings 0
python -m pip check: broken requirements 없음
git diff --check: 통과, CRLF 변환 경고만 존재
```

정식 type checker 구성은 없어 실행하지 않았다. 확장 style lint 50건은 cleanup catch, ternary 권고, UI Unicode 기호 등 동작 무관 항목이라 자동 수정하지 않았다.

### Windows folder build

```text
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows_onedir.ps1
결과: 성공
시간: 약 724초
bundle: 1,414 files / 387.7 MB
ZIP: 154.6 MB
```

PyInstaller 경고:

- 선택적 Numba TBB backend의 `tbb12.dll` 누락: ISSUE-BUILD-002
- 일부 선택적 hidden import 경고. 현재 실행·테스트에는 영향 없음.

### 패키지 smoke

```text
ZIP entries: 1,444
main window: Auto Playlist Maker v1.3.0
cold startup: 약 77초
CloseMainWindow: 성공
종료 후 잔류 프로세스: 0
```

### 직접 확인하지 못한 검사

- macOS `.app`: ISSUE-BUILD-001
- NVIDIA/Intel/AMD GPU 실제 encoder
- 11개 언어 원어민 의미 검수: ISSUE-I18N-001
- 네 해상도 preview/output 캡처 비교: ISSUE-TEST-001
- 최종 splash logo 외곽 캡처: ISSUE-UI-001
- 수 시간짜리 실제 최종 영상 전체 재생

## 2026-07-29 UI 시스템 개선 검증

- `python -m unittest discover -s tests -v`: 49 passed
- UI/state 집중 검사: 19 passed
- `ruff --select F,B`: 오류 0
- `python check_locales.py`: errors 0, warnings 0
- `py_compile`: 통과
- 레이아웃 자동 점검: dark/light × 6 Stage × 950×620·1200×750·1600×900 = 36개 조합, 경계 이탈 0
- 긴 목록: 프로젝트 표 120행에서 독립 scrollbar와 레이아웃 유지
- 실제 캡처: 950×620과 최대화에서 겹침·가로 잘림 없음
- 밝은 모드 내비게이션의 5개 배경 영역이 모두 light `bg_mid` 토큰과 일치
- 남은 수동 검사: 모든 locale 장문, OS DPI 배율별 픽셀 수준 비교

## 2026-07-29 효과·전역 오디오·최종 패키지 검증

### 자동 검사

```text
python -m unittest discover -s tests -v
결과: 62 passed

python check_locales.py
결과: 0 errors, 0 warnings

루트·tests Python 파일 py_compile
결과: 통과

python -m ruff check . --exclude build --exclude dist --exclude .git --select F,B
결과: 오류 0

python -m pip check
결과: broken requirements 없음
```

추가된 회귀 검사는 환경음 독립 bus/stem, 짧은 환경음의 최종 반복 타임라인 연속 재생, Stage 4 좌우 배치, 효과 섹션 reset, effect/audio migration, deep-copy state, Stage 5 light root와 danger/success hover를 포함한다.

### 실제 오디오 경로 비교

```text
duration: preview WAV 5.500s / final MP4 audio 5.503s
preview master: -22.18 LUFS / -21.10 dBTP
final render:   -22.19 LUFS / -20.84 dBTP
delta:          -0.01 LUFS / +0.26 dBTP
```

입력 test tone이 매우 작아 최대 자동 gain 제한에 걸렸으므로 목표 -14 LUFS 도달 검사가 아니라 preview/final 경로 일치 검사로 판정했다. 원본 결과는 `test_artifacts/audio_validation/report.json`에 있다.

### UI 시각 검사

- Stage 4 light preview-left, effect picker, dark 950×620 긴 효과 목록
- Stage 5 light 대형 창과 hardcoded gray gutter 제거
- 빈 효과 상태, long list scrollbar, 최소·기본·대형 창에서 겹침·잘림 없음
- 캡처: `test_artifacts/ui_qa/`

### Windows onedir/ZIP

```text
bundle: 1,419 files / 387.9 MB
ZIP: 162,349,669 bytes
SHA-256: 27FD5A609DBD57DC77FA1B1EB4F92E437FC1954E02AA969AC85625876FFA223E
main window interactive: 52.350s
window title: Auto Playlist Maker v1.3.0
CloseMainWindow: 성공
종료 후 잔류 프로세스: 0
```

PyInstaller clean COLLECT가 도구의 10분 제한 뒤에도 child process로 계속 진행되어, 완료 확인 후 build script의 Tcl/Tk root 복사와 ZIP 단계를 동일하게 이어서 수행했다. 선택적 `tbb12.dll` 경고는 ISSUE-BUILD-002와 같다.

## 2026-07-30 native launcher·11 locale 검증

```text
python -m unittest discover -s tests -v
결과: 63 passed

python check_locales.py
결과: 0 errors, 0 warnings (11 locales)

python -m ruff check . --select F,B --exclude build,dist,.git
결과: 오류 0

py_compile / python -m pip check
결과: 통과 / broken requirements 없음

native_launcher.cs
결과: .NET Framework csc 최적화 winexe 컴파일 성공, 28,672 bytes
```

실제 배포 폴더 cold start:

```text
NATIVE_FIRST=2.5339929s
NATIVE_LAST=52.8916960s
LOADING_FIRST=53.0863161s
LOADING_LAST=87.0419011s
MAIN_SEEN=87.2352729s
SPLASH_AFTER_MAIN=False
```

첫 화면 asset은 `test_artifacts/branding/native_icon_splash_transparent.png`, 로딩 화면 실캡처는 `test_artifacts/branding/loading_splash_first_frame.png`다. 로딩 캡처에서 `GUI 구성 중...`과 90% 진행 바를 확인했다. 네이티브→로딩 0.195초, 로딩→main 0.193초다.

## 2026-07-30 버전 종료 재검증

### 자동 검사

```text
python -m unittest discover -s tests -v
결과: 63 passed, 57.256s

python check_locales.py
결과: 0 errors, 0 warnings

python -m ruff check . --exclude build --exclude dist --exclude .git --select F,B
결과: All checks passed

루트 및 tests Python 파일 py_compile
결과: 통과

python -m pip check
결과: No broken requirements found

bash -n build_mac.sh
bash -n setup_mac.sh
결과: 두 스크립트 모두 통과

.github/workflows/release.yml YAML 파싱
결과: 통과
```

별도의 `mypy` 또는 `pyright` 설정은 저장소에 없으므로 타입 검사는 실행하지 않았으며 통과로 기록하지 않는다.

### 릴리스 증거

- GitHub Actions run `30471288589`: `build-windows`, `build-macos`, `publish` 모두 `success`
- 공개 릴리스: `v1.3.0`, draft 아님, prerelease 아님
- 릴리스 대상 commit: `f5e7c1a`
- Windows ZIP: `149,289,942` bytes, SHA-256 `234AF2B1A286E855A0F95443CDA3324969CCC94CF69DB55D1B09B13F38B86063`
- macOS ZIP: `105,059,064` bytes, SHA-256 `EE181CD4B6E89B7A68958B91E9278714D78370E6859ABF063849131BA0B32712`
- `setup.bat`: SHA-256 `236F979C0B4232C88B739EB1E2BCCCF324049A2C053C9E247621B0FA895C021E`
- `setup_mac.sh`: SHA-256 `0D69D0C4376D471D95017335159E7BB1DA9CFACD3666A9C24CA789C447BB7ADD`

버전 종료 시점에는 릴리스 commit에서 이미 성공한 양 플랫폼 빌드를 다시 만들지 않았다. 이후 변경은 문서뿐이므로 위 Actions 결과를 실제 배포 바이너리의 빌드 근거로 사용한다.

### 종료 시점에 실행하지 못한 검사

- 실제 macOS 장비에서 `.app` 실행, 첫 화면, 종료 및 렌더 smoke
- NVIDIA/Intel/AMD 각 GPU의 실제 하드웨어 인코더
- 11개 언어의 원어민 문구 검수
- 최소·기본·최대·전체 화면 4해상도 최종 캡처 비교
- 수 시간짜리 실제 프로젝트의 전체 재생과 장시간 렌더
