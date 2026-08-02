# 알려진 문제

해결된 문제도 삭제하지 않고 상태와 검증 결과를 보존한다.

## ISSUE-BUILD-001 macOS 빌드가 1.3.0과 불일치

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0
- 상태: 해결
- 심각도: 높음
- 재현 조건: `build_mac.sh` 실행 또는 내용을 확인한다.
- 기대 동작: 사용자가 지정한 1.3.0 이름, locales와 1.3.0 모듈을 포함한 `.app`/ZIP 생성.
- 실제 동작: 기존 스크립트가 `version="1.2.1"`이며 i18n, Stage 4·5, FFmpeg service 등 1.3.0 hidden import가 없었다.
- 관련 코드: `build_mac.sh`, `.github/workflows/build.yml`
- 원인: Windows 1.3.0 구조 변경 후 macOS 스크립트 동기화 누락.
- 임시 우회: 필요 없음.
- 수정된 버전: 1.3.0
- 검증 결과: 버전, 아이콘·스플래시·locale, 1.3.0 모듈 포함을 동기화했다. GitHub Actions run `30471288589`에서 macOS `.app`/ZIP 빌드와 양 플랫폼 성공 후 publish가 통과했다.

## ISSUE-PERF-001 패키지 첫 실행 지연

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0, 1.3.1
- 상태: 1.3.1 개선 완료, 추가 최적화는 계속
- 심각도: 높음
- 재현 조건: Windows one-dir 빌드를 cold start하고 main window 표시까지 측정.
- 기대 동작: 스플래시가 즉시 표시되고 합리적인 시간 안에 메인 창 전환.
- 실제 동작: 1.3.0 smoke에서 main window 87.24초였고, 1.3.1 첫 패키지에서는 Python 로딩 스플래시와 메인 창이 각각 Tk 루트를 만들어 core main window가 100.176초에 표시됐다.
- 관련 코드: `app.py` 부팅·heavy import·`_LazyStage`, PyInstaller splash/spec/build script
- 원인 또는 추정: 설계·렌더·NumPy의 조기 import와, 네이티브 스플래시 뒤 Python 로딩 스플래시와 메인 창이 별도 Tk 루트를 만드는 중복 초기화가 확인됐다. PyInstaller 파일 검사 비용도 남아 있다.
- 임시 우회: 외부 네이티브 런처가 Python 초기화 전 아이콘을 띄우고, Tk 준비 뒤 실제 작업 문구·진행 바 로딩 창으로 인계.
- 수정된 버전: 1.3.1
- 검증 결과: source import 누적 시간이 약 4.419초에서 2.331초로 줄었다. 최종 단일 EXE Windows 1.3.1 onedir smoke에서 main window는 64.536초에 표시됐고 정상 종료 뒤 해당 bundle 프로세스는 0개였다. 절대 시작 시간은 여전히 길어 추가 최적화 대상으로 유지한다.

## ISSUE-ARCH-001 반복 계산 공개 API 중복

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0, 1.3.1
- 상태: 1.3.1 해결
- 심각도: 중간
- 재현 조건: `repeat_settings.py`와 `timeline_utils.py`의 `RepeatPlan`, `build_repeat_plan`, duration 추정 함수 비교.
- 기대 동작: 반복 계획의 기준 구현이 하나여야 한다.
- 실제 동작: UI·렌더는 `repeat_settings.py`를 사용하지만 `timeline_utils.py`에도 유사 공개 API가 남아 있었다.
- 관련 코드: 두 모듈과 외부 import 가능 경로
- 원인: 기능 이동 후 호환 목적 또는 정리 누락.
- 임시 우회: 새 코드는 `repeat_settings.py`만 사용.
- 수정된 버전: 1.3.1
- 검증 결과: `timeline_utils.estimate_group_duration()`의 공개 인터페이스는 보존하되 내부 계산은 `repeat_settings.estimate_group_duration()`에 위임한다. 반복·UI 회귀 테스트가 통과했다.

## ISSUE-DATA-001 그룹 총 길이 계산 경로 불일치 가능성

- 발견 버전 / 영향 버전: 1.3.0 코드 정리 / 1.3.0, 1.3.1
- 상태: 1.3.1 해결
- 심각도: 중간
- 재현 조건: 수동 제거·그룹 drag·trim 변경 후 `total_duration`과 렌더 추정 길이를 비교.
- 기대 동작: 모든 UI·저장·렌더 경로가 trim과 crossfade를 반영한 같은 기준을 사용.
- 실제 동작: 일부 `app.py` 경로는 raw duration 합계를, 다른 경로는 trim 길이 또는 timeline 계산을 사용했다.
- 관련 코드: `app.py`, `repeat_settings.estimate_group_duration`
- 원인 또는 추정: 기능별 갱신 로직 중복.
- 임시 우회: 렌더 예상 길이는 `estimate_group_duration()` 결과를 기준으로 확인.
- 수정된 버전: 1.3.1
- 검증 결과: 수동 추가·제거·그룹 drag·trim·자동 분배 갱신을 공통 `estimate_group_duration()`으로 통일했다. trim과 crossfade가 포함된 UI 그룹 길이와 렌더 추정 길이 일치 회귀 테스트가 통과했다.

## ISSUE-TEST-001 미리보기/출력 네 해상도 캡처 비교 미완료

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0, 1.3.1
- 상태: 1.3.1 자동 비교 완료
- 심각도: 중간
- 재현 조건: 같은 프로젝트를 네 지원 해상도로 preview/output 캡처 비교.
- 기대 동작: 텍스트·이미지·비주얼라이저의 좌표와 상대 크기 일치.
- 실제 동작: 공통 변수와 renderer 테스트만 있었으나 1.3.1에서 네 해상도 preview/output 프레임 비교 기록을 생성했다.
- 관련 코드: Stage 4·5, `video_gen.py`, `tests/verify_layout_fidelity.py`
- 원인: 실제 미디어와 장시간 수동 시각 검증 필요.
- 임시 우회: 공통 renderer와 출력 좌표 기준을 유지.
- 수정된 버전: 1.3.1
- 검증 결과: `tests/verify_layout_fidelity.py`로 1920×1080, 1280×720, 1080×1920, 1080×1080을 비교했다. 모든 해상도에서 MAE 0.400 미만~0.402, p99 오차 1로 통과했으며 보고서는 `test_artifacts/layout_fidelity/report.json`에 있다. 미적 품질의 사람 평가는 별도다.

## ISSUE-I18N-001 번역 의미 품질의 사람 검수 미완료

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0, 1.3.1
- 상태: 확인 필요, 1.3.1 이월
- 심각도: 중간
- 재현 조건: 각 언어 원어민이 모든 단계 문구를 맥락과 함께 검수.
- 기대 동작: 자연스럽고 일관된 전문 UI 문구.
- 실제 동작: key, placeholder, 깨진 문자열 검사는 통과했지만 의미 품질을 자동 검사할 수 없다.
- 관련 코드: `locales/*.json`, `check_locales.py`
- 원인: 자동 번역·다국어 리소스 대량 추가 후 전문 감수 부재.
- 임시 우회: 영어·한국어를 기준 문구로 사용하고 신고된 문구를 ID별 수정.
- 수정된 버전: 없음
- 검증 결과: 11개 언어 구조 검사 0 errors, 0 warnings.

## ISSUE-BUILD-002 선택적 Numba 병렬 backend PyInstaller 경고

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0, 1.3.1
- 상태: 1.3.1 해결
- 심각도: 낮음
- 재현 조건: Windows 또는 macOS PyInstaller 빌드.
- 기대 동작: 의존 DLL 경고 없음.
- 실제 동작: Windows에서는 Numba 선택적 TBB pool의 `tbb12.dll`, macOS에서는 선택적 OpenMP pool의 `libomp.dylib`을 찾지 못한다.
- 관련 코드: 빌드 환경의 Numba, `build_windows_onedir.ps1`, `build_mac.sh`
- 원인: 사용하지 않는 선택적 병렬 backend가 PyInstaller 분석 대상에 포함됨.
- 임시 우회: 현재 기본 분석·렌더 경로는 해당 backend를 사용하지 않는다.
- 수정된 버전: 1.3.1
- 검증 결과: Windows·macOS 빌드에서 사용하지 않는 `numba.np.ufunc.tbbpool`과 `omppool`만 제외했다. Windows 빌드 경고 파일에는 두 모듈의 의도적 제외만 기록되고 `tbb12.dll`·`libomp` 누락 경고는 없으며, Windows 패키지 실행 smoke가 통과했다.

## ISSUE-BUILD-003 macOS 릴리스 패키지 실행 미검증

- 발견 버전 / 영향 버전: 1.3.0 종료 / 1.3.0, 1.3.1
- 상태: 확인 필요, 1.3.1 이월
- 심각도: 중간
- 재현 조건: GitHub 릴리스의 `AutoPlaylistMaker_v1.3.0_macos.zip`을 실제 macOS 장치에서 풀고 `.app`을 실행해 첫 화면, 메인 창, FFmpeg 탐색과 종료를 확인한다.
- 기대 동작: `.app`이 열리고 11개 locale·스플래시·미리보기·종료 경로가 동작한다.
- 실제 동작: GitHub Actions에서 `.app`/ZIP 생성과 내부 executable/resource 존재만 확인했으며 GUI 실행은 수행하지 않았다.
- 관련 코드: `build_mac.sh`, `.github/workflows/build.yml`, `app.py`, `ffmpeg_service.py`
- 원인: 현재 작업 환경이 Windows이고 Actions build job에 GUI smoke가 없다.
- 임시 우회: macOS 사용자는 Finder 우클릭 `열기`로 unsigned app을 실행하고 FFmpeg가 없으면 `bash setup_mac.sh`를 사용한다.
- 수정된 버전: 없음
- 검증 결과: CI bundle 273MB/756 files, release ZIP 105,059,064 bytes, SHA-256 `EE181CD4B6E89B7A68958B91E9278714D78370E6859ABF063849131BA0B32712`; 실행은 미검증.

## ISSUE-CI-001 GitHub Actions Node 20 사용 action 경고

- 발견 버전 / 영향 버전: 1.3.0 릴리스 / 1.3.1
- 상태: 1.3.1 workflow 수정 완료, 원격 실행 대기
- 심각도: 낮음
- 재현 조건: GitHub Actions build run의 job summary를 확인한다.
- 기대 동작: 지원 중인 Node runtime을 사용하는 action으로 경고 없이 실행한다.
- 실제 동작: `actions/checkout@v4`, `setup-python@v5`, `upload-artifact@v4`, `download-artifact@v4`가 Node 20 deprecation 경고와 함께 Node 24 강제 실행됐다.
- 관련 코드: `.github/workflows/build.yml`
- 원인: workflow action major version이 현재 runner 권장 runtime보다 오래됐다.
- 임시 우회: 현재 runner가 Node 24로 강제 실행해 build와 publish는 성공한다.
- 수정된 버전: 1.3.1
- 검증 결과: 공식 최신 major에 맞춰 `checkout@v7`, `setup-python@v6`, `upload-artifact@v7`, `download-artifact@v8`로 갱신하고 workflow 기본 tag를 `v1.3.1`로 수정했다. YAML 파싱은 통과했으며 원격 Actions 실행은 아직 하지 않았다.

## ISSUE-UI-003 효과 선택 메뉴의 계층형 하위 메뉴 미구현

- 발견 버전 / 영향 버전: 1.3.0 종료 감사 / 1.3.0, 1.3.1
- 상태: 1.3.1 해결
- 심각도: 중간
- 재현 조건: Stage 4에서 `+ 효과 추가`를 누르고 카테고리에 hover 또는 click한다.
- 기대 동작: 카테고리별 하위 효과 메뉴가 열리고 화면 경계에서는 반대 방향으로 배치된다.
- 실제 동작: 검색 결과는 기존 단일 스크롤 목록으로 유지하고, 카테고리 버튼에는 hover/click으로 여는 실제 하위 메뉴가 추가됐다. 오른쪽 화면 경계에서는 왼쪽으로 배치한다.
- 관련 코드: `stage4_design_effects.py:_open_effect_picker`, `docs/UI_SPEC.md`
- 원인: 계층형 submenu 대신 더 단순한 grouped popup으로 구현을 마감했다.
- 임시 우회: 검색 또는 세로 스크롤로 효과를 선택한다.
- 수정된 버전: 1.3.1
- 검증 결과: 하위 메뉴에서 효과를 추가하고 기존 효과가 비활성화되는 UI 회귀 테스트가 통과했다.

## ISSUE-UI-004 테마 전환 뒤 일부 UI 요소 소실

- 발견 버전 / 영향 버전: 1.3.0 릴리스 후 사용자 보고 / 1.3.0, 1.3.1
- 상태: 1.3.1 수정 완료
- 심각도: 높음
- 재현 조건: 앱에서 다크→라이트 또는 라이트→다크로 테마를 전환하고 현재 Stage의 패널과 컨트롤을 확인한다.
- 기대 동작: 모든 요소가 새 테마 토큰으로 즉시 다시 그려지고 현재 입력값·선택·스크롤 상태가 유지된다.
- 실제 동작: 일부 화면 요소가 사라지거나 다시 그려지지 않는다는 사용자 보고가 있다. 영향 Stage와 정확한 상태 조합은 아직 확인하지 못했다.
- 관련 코드: `app.py`의 테마 전환·Stage 재구성, `ui_state.py`, 각 Stage의 `apply_theme`
- 원인: 패키지의 lazy Stage는 프로젝트에서 읽은 `pages` 상태를 아직 생성되지 않은 Stage에 보관하지 않았다. 첫 진입뿐 아니라 진입 전 자동 저장·테마/언어 재구성에서 빈 placeholder 상태가 저장될 수 있었고, legacy repeat·visibility·출력 경로가 최신 page 값을 덮을 수도 있었다.
- 임시 우회: 수정 전에는 해당 Stage에 진입한 뒤 다시 설정해야 했다.
- 수정된 버전: 1.3.1
- 검증 결과: packaged lazy 경로에서 저장한 `radial`/세로 해상도/활성 효과·legacy audio·visibility·render output을 첫 진입 전 저장과 테마 재구성 뒤에도 복원하고, 새 프로젝트는 빈 효과로 시작하는 회귀 테스트가 통과했다. 전체 75 tests도 통과했다.

## ISSUE-PROJECT-001 프로젝트 이름 지정과 저장 차단

- 발견 버전 / 영향 버전: 1.3.0 릴리스 후 사용자 보고 / 1.3.0, 1.3.1
- 상태: 1.3.1 수정 완료
- 심각도: 차단
- 재현 조건: 새 프로젝트를 시작해 프로젝트 이름을 입력·확정한 뒤 저장을 시도한다.
- 기대 동작: 이름이 프로젝트 상태와 제목에 반영되고 유효한 `project.json`이 저장된다.
- 실제 동작: 프로젝트 이름을 지정할 수 없고 저장도 완료되지 않는다는 사용자 보고가 있다. 입력 검증과 저장 중 어느 지점이 먼저 실패하는지는 미확인이다.
- 관련 코드: `app.py` 프로젝트 생성·이름 입력·저장 callback, `project.py`
- 원인: 기본 저장 경로가 실행 위치 기준 상대 `projects`여서 설치 폴더가 쓰기 불가능하면 생성이 실패했고, `새 프로젝트`는 하위 폴더만 만든 뒤 `project.json`을 저장하지 않았다. 생성 오류도 UI callback 밖으로 전파됐다.
- 임시 우회: 수정 전에는 쓰기 가능한 절대 경로를 직접 선택하고 별도로 저장해야 했다.
- 수정된 버전: 1.3.1
- 검증 결과: 사용자 문서 아래 기본 경로, 생성 즉시 format v4 `project.json`, 잘못된 이름 거부, UI 오류 표시를 자동 테스트로 확인했다.

## ISSUE-NAV-001 다음 작업 단계 이동 차단

- 발견 버전 / 영향 버전: 1.3.0 릴리스 후 사용자 보고 / 1.3.0, 1.3.1
- 상태: 독립 회귀 미재현, 선행 프로젝트 회귀 수정 후 자동 경로 확인
- 심각도: 차단
- 재현 조건: 프로젝트 설정 또는 현재 단계의 필수 입력을 마치고 상단 `다음`을 누른다.
- 기대 동작: 현재 상태를 보존한 뒤 다음 Stage가 표시된다.
- 실제 동작: `다음`이 반응하지 않아 작업 흐름을 계속 진행할 수 없다는 사용자 보고가 있다.
- 관련 코드: `app.py` 상단 내비게이션, 단계 유효성 검사, Stage 전환 callback
- 원인: 독립적인 callback 실패는 재현되지 않았다. Stage 0의 `다음`은 분석된 오디오가 있을 때만 활성화되는 기존 조건이며 ISSUE-PROJECT-001의 생성·저장 실패와 함께 보고된 흐름을 우선 복구했다.
- 임시 우회: 확인된 안전한 우회 없음.
- 수정된 버전: 1.3.1에서 선행 회귀 수정, 독립 수정 없음
- 검증 결과: 분석된 트랙이 있는 Stage 0에서 버튼이 `normal`이고 invoke 후 Stage 1로 이동하는 자동 테스트가 통과했다. 실제 패키지에서 분석 완료 후에도 이동하지 않는다면 별도 재현 정보가 필요하다.

## ISSUE-ANALYSIS-001 분석 진행 창 조기 종료

- 발견 버전 / 영향 버전: 1.3.0 릴리스 후 사용자 보고 / 1.3.0, 1.3.1
- 상태: 1.3.1 해결
- 심각도: 높음
- 재현 조건: 여러 음원을 추가하고 분석을 시작한 뒤 분석 진행 창과 실제 worker 상태를 관찰한다.
- 기대 동작: 진행 창이 현재 작업과 진행률·취소 상태를 표시하고, 분석 완료 또는 취소가 확정된 뒤 닫힌다.
- 실제 동작: 분석 진행 창이 먼저 닫히고 실제 분석은 백그라운드에서 계속되어 상태와 취소 여부를 확인하기 어렵다는 사용자 보고가 있다.
- 관련 코드: `app.py` 분석 시작·progress UI·worker callback, `analyzer.py`
- 원인: worker thread가 Tk `after()`를 직접 호출해 메인 루프 상태에 따라 `RuntimeError`가 발생했고, callback 등록과 worker 종료 순서도 분리돼 있었다.
- 임시 우회: 분석이 끝날 때까지 기다릴 수는 있으나 진행 상태와 취소 제어를 잃으므로 정상 동작으로 간주하지 않는다.
- 수정된 버전: 1.3.1
- 검증 결과: worker는 thread-safe queue에만 진행 상태를 기록하고 메인 thread poller가 UI를 갱신한다. 차단 worker를 사용한 회귀 테스트에서 worker 생존 중에는 overlay가 유지되고 종료 뒤에만 닫히는 것을 확인했다. 프로젝트 저장·분배·waveform·preview·render callback도 공통 `post_ui()` 큐로 정리했다.

## ISSUE-UI-001 최종 스플래시 로고 외곽

- 발견 버전 / 영향 버전: 1.2.0 / 1.3.0
- 상태: 해결
- 심각도: 낮음
- 재현 조건: Windows 패키지 cold start를 캡처해 투명 외곽·핑크 halo 확인.
- 기대 동작: 배경 없는 심플한 재생·목록 심볼, 불필요한 경계·halo 없음.
- 실제 동작: 아이콘과 첫 스플래시를 RGBA 심볼로 만들고 Windows per-pixel alpha 레이어드 창에 표시한다.
- 관련 코드: `app_icon.png`, `app_icon.ico`, `app_splash.png`, `app.py:NativeSplash`, `app.py:SplashScreen`
- 원인: 과거 여러 asset과 icon cache 문제로 반복 회귀가 있었음.
- 임시 우회: 필요 없음.
- 수정된 버전: 1.3.0
- 검증 결과: PNG 모서리 alpha 0, layered-window API 성공, 별도 로딩 스플래시 실캡처 확인.

## ISSUE-WORK-001 1.3.0 릴리스 이전 주요 변경의 미커밋 상태

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0
- 상태: 해결
- 심각도: 높음
- 재현 조건: `git status --short`.
- 기대 동작: 검증된 버전 기준점을 식별할 수 있는 commit 또는 tag 존재.
- 실제 동작: 기준 커밋 `de32dbf` 이후 핵심 수정·신규 파일·삭제가 작업 트리에 남아 있었다.
- 관련 코드: 저장소 전체
- 원인: 여러 연속 Codex 작업이 커밋 없이 진행됨.
- 임시 우회: 필요 없음.
- 수정된 버전: 1.3.0
- 검증 결과: 기존 GitHub `main` 이력을 보존한 릴리스 커밋과 `v1.3.0` 태그를 기준점으로 사용한다.

## ISSUE-AUDIO-001 미리보기 `asplit` 미연결 오류

- 발견 버전 / 영향 버전: 1.3.0 전역 오디오 작업 중 / 1.3.0 개발본
- 상태: 해결
- 심각도: 높음
- 재현 조건: 환경음 없는 preview mix에서 music stem용 `asplit` 뒤 master가 원래 label을 다시 소비한다.
- 기대 동작: `music_bus_main`이 master 출력에 연결되고 선택한 stem도 생성된다.
- 실제 동작: FFmpeg가 `Filter 'asplit' has output 0 (music_bus_main) unconnected`로 실패했다.
- 관련 코드: `audio_pipeline.py`
- 원인: stem 분기 후 현재 audio label을 split의 main 출력으로 갱신하지 않았다. 시간 제한과 무관한 filtergraph 연결 오류였다.
- 임시 우회: 없음
- 수정된 버전: 1.3.0
- 검증 결과: 환경음 유무·stem 생성·반복 최종 timeline 테스트와 전체 62 tests 통과.

## ISSUE-UI-002 Stage 5 밝은 모드 외곽 회색 테두리

- 발견 버전 / 영향 버전: 1.3.0 UI 개선 중 / 1.3.0 개발본
- 상태: 해결
- 심각도: 중간
- 재현 조건: 밝은 모드에서 Stage 5를 최소·대형 창으로 연다.
- 기대 동작: Stage root와 내부 panel이 현재 light theme surface를 사용한다.
- 실제 동작: Stage root의 고정 `#36393f`가 빈 gutter와 외곽 테두리로 남았다.
- 관련 코드: `stage5_render.py`
- 원인: 이전 다크 테마 배경값 하드코딩.
- 임시 우회: 없음
- 수정된 버전: 1.3.0
- 검증 결과: light Stage 5 root token 자동 테스트와 1600×900 캡처 통과.
