# 실행·검증 기준

## 개발 실행

```powershell
python app.py
python app.py --safe
```

`--safe`는 `tkinterdnd2` root 대신 기본 Tk root를 사용해 UI 테스트·진단 시 DnD 초기화 영향을 줄인다.

## 자동 테스트

```powershell
python -m unittest discover -s tests -v
```

주요 범위:

- `test_core.py`: 분석 edge, 분배, 프로젝트 이동·migration·누락·순서
- `test_audio_pipeline.py`: 실제 FFmpeg mix, trim/volume/fade, video encode, cancel
- `test_repeat_settings.py`: 반복 계산, 표시 시간, 실제 세 번 반복
- `test_ui_interactions.py`: import, 언어, trim grab, DnD, 폰트, 전체 상태, preview linkage
- `test_ui_state.py`: Stage 재구성 상태
- `test_i18n.py`: 11개 언어 키·placeholder·stable ID

FFmpeg 또는 display가 없으면 관련 테스트가 skip될 수 있다. skip 수와 이유를 `TEST_RESULTS.md`에 기록한다.

## 구문·린트·의존성

```powershell
python -m py_compile app.py analyzer.py audio_pipeline.py audio_preview.py distributor.py ffmpeg_service.py font_combo.py i18n.py mixer.py project.py render_jobs.py repeat_settings.py stage4_design_effects.py stage5_render.py timeline_utils.py transition.py ui_state.py video_gen.py
python -m ruff check . --exclude build --exclude dist --exclude .git --select F,B
python check_locales.py
python -m pip check
git diff --check
```

- 정식 type checker 구성은 현재 없다. 타입 검사 항목은 “구성 없음”으로 기록한다.
- 확장 스타일 lint는 동작 변경 없는 정리 작업에서 참고만 하고 기계적으로 모두 수정하지 않는다.

## Windows 빌드

권장 배포는 folder형이다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows_onedir.ps1
```

one-file 진단 빌드:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1
```

버전은 사용자가 명시한 값과 스크립트·`APP_VERSION`·산출물명이 일치해야 한다.

## macOS 빌드

```bash
bash build_mac.sh
```

현재 ISSUE-BUILD-001 때문에 1.3.0 배포 명령으로 사용하지 않는다. 버전과 hidden imports를 먼저 동기화하고 macOS runner에서 `.app` 실행까지 검증해야 한다.

## 수동 회귀 절차

### 프로젝트·저장

1. 프로젝트 생성, 여러 음원·이미지·영상 추가.
2. 분석 후 모든 Stage에서 값을 변경.
3. 저장하고 앱을 종료·재실행해 동일 상태 확인.
4. 원본 미디어를 이동한 뒤 backup 복원과 재연결 확인.
5. dirty 표시와 종료 확인창 확인.

### 트림

1. handle 누른 동안만 이동.
2. 파형 밖에서 release 후 고정.
3. hover만으로 불변.
4. 빠른 반복 drag, start/end 경계, 최소 길이.
5. 기본/Shift/Alt 정밀도와 cursor.

### 분배 DnD

1. 위/아래, 최상단/최하단, 여러 항목 건너뛰기.
2. 그룹 간, 빈 그룹, 취소.
3. 그룹 0개 상태에서 단일·다중 drag와 버튼 이동.
4. 저장·재실행 후 순서.

### 폰트·언어

1. 한글/영문 검색, 방향키, Enter, Esc, 바깥 클릭.
2. 목록 wheel이 부모 패널을 움직이지 않는지 확인.
3. 11개 언어 전환 후 트랙·디자인·렌더 값 유지.
4. Arabic RTL과 긴 번역 문자열 확인.

### 반복·렌더

1. 1회, 여러 회, 목표보다 1회가 긴 경우, 정확/비정확 배수.
2. 마지막 곡·반복이 잘리지 않는지 probe.
3. CPU codec, 가능한 GPU codec, LUFS, cancel, 실패 재시도.
4. 렌더 중 종료 후 하위 프로세스가 남지 않는지 확인.

### 미리보기/출력

같은 프로젝트를 다음 해상도로 출력하고 캡처를 비교한다.

```text
1920×1080
1280×720
1080×1920
1080×1080
```

`tests/verify_layout_fidelity.py`에 preview/output 캡처를 제공해 비교할 수 있다. 텍스트, overlay, visualizer, cover/contain, fade/effect 경계를 확인한다.

## 배포 전 필수 검사

1. Git status와 사용자 변경 확인
2. 전체 unittest
3. `F,B` lint, locale, pip, diff 검사
4. clean folder build
5. ZIP central directory 열기와 entry 수 확인
6. EXE cold start, main title/version 확인
7. 정상 close 후 잔류 프로세스 0
8. 샘플 프로젝트 열기·저장·짧은 실제 렌더
9. known issue와 version test results 갱신

## 현재 자동화할 수 없는 항목

- 원어민 번역 자연스러움
- 스플래시·시각 효과의 미적 승인
- 모든 GPU vendor 실기기 인코딩
- macOS `.app` 실행
- 여러 시간 출력의 전체 재생 확인
- 네 해상도 캡처의 사람 기준 pixel/layout 승인

실행하지 못한 검사는 “통과”로 쓰지 않고 버전 `TEST_RESULTS.md`에 이유를 남긴다.
