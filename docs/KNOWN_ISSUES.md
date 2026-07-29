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
- 상태: 미해결, 1.3.1 이월
- 심각도: 높음
- 재현 조건: Windows one-dir 빌드를 cold start하고 main window 표시까지 측정.
- 기대 동작: 스플래시가 즉시 표시되고 합리적인 시간 안에 메인 창 전환.
- 실제 동작: 2026-07-30 최종 smoke에서 네이티브 아이콘 2.53초, 진행 로딩 화면 53.09초, main window 87.24초.
- 관련 코드: `native_launcher.cs`, `app.py` 부팅·heavy import·`_LazyStage`, PyInstaller spec/build script
- 원인 또는 추정: 과학·오디오 라이브러리 import, PyInstaller 파일 수, 백신 검사 가능성. 프로파일 미완료.
- 임시 우회: 외부 네이티브 런처가 Python 초기화 전 아이콘을 띄우고, Tk 준비 뒤 실제 작업 문구·진행 바 로딩 창으로 인계.
- 수정된 버전: 체감 피드백은 1.3.0에서 수정, 코어 cold-start 최적화는 미완료
- 검증 결과: 아이콘→로딩 0.195초, 로딩→메인 0.193초, 메인 표시 후 스플래시 잔류 없음.

## ISSUE-ARCH-001 반복 계산 공개 API 중복

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0, 1.3.1
- 상태: 보류, 1.3.1 이월
- 심각도: 중간
- 재현 조건: `repeat_settings.py`와 `timeline_utils.py`의 `RepeatPlan`, `build_repeat_plan`, duration 추정 함수 비교.
- 기대 동작: 반복 계획의 기준 구현이 하나여야 한다.
- 실제 동작: UI·렌더는 `repeat_settings.py`를 사용하지만 `timeline_utils.py`에도 유사 공개 API가 남아 있다.
- 관련 코드: 두 모듈과 외부 import 가능 경로
- 원인: 기능 이동 후 호환 목적 또는 정리 누락.
- 임시 우회: 새 코드는 `repeat_settings.py`만 사용.
- 수정된 버전: 없음
- 검증 결과: 외부 인터페이스 보존 요구 때문에 삭제하지 않음.

## ISSUE-DATA-001 그룹 총 길이 계산 경로 불일치 가능성

- 발견 버전 / 영향 버전: 1.3.0 코드 정리 / 1.3.0, 1.3.1
- 상태: 확인 필요, 1.3.1 우선 조사
- 심각도: 중간
- 재현 조건: 수동 제거·그룹 drag·trim 변경 후 `total_duration`과 렌더 추정 길이를 비교.
- 기대 동작: 모든 UI·저장·렌더 경로가 trim과 crossfade를 반영한 같은 기준을 사용.
- 실제 동작: 일부 `app.py` 경로는 raw duration 합계를, 다른 경로는 trim 길이 또는 timeline 계산을 사용한다.
- 관련 코드: `app.py`, `repeat_settings.estimate_group_duration`
- 원인 또는 추정: 기능별 갱신 로직 중복.
- 임시 우회: 렌더 예상 길이는 `estimate_group_duration()` 결과를 기준으로 확인.
- 수정된 버전: 없음
- 검증 결과: 동작 변경 위험 때문에 미수정.

## ISSUE-TEST-001 미리보기/출력 네 해상도 캡처 비교 미완료

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0, 1.3.1
- 상태: 미해결, 1.3.1 이월
- 심각도: 중간
- 재현 조건: 같은 프로젝트를 네 지원 해상도로 preview/output 캡처 비교.
- 기대 동작: 텍스트·이미지·비주얼라이저의 좌표와 상대 크기 일치.
- 실제 동작: 공통 변수와 renderer 테스트는 통과했지만 캡처 비교 기록이 없다.
- 관련 코드: Stage 4·5, `video_gen.py`, `tests/verify_layout_fidelity.py`
- 원인: 실제 미디어와 장시간 수동 시각 검증 필요.
- 임시 우회: 공통 renderer와 출력 좌표 기준을 유지.
- 수정된 버전: 없음
- 검증 결과: 자동 상태 연결만 통과.

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
- 상태: 보류, 1.3.1 이월
- 심각도: 낮음
- 재현 조건: Windows 또는 macOS PyInstaller 빌드.
- 기대 동작: 의존 DLL 경고 없음.
- 실제 동작: Windows에서는 Numba 선택적 TBB pool의 `tbb12.dll`, macOS에서는 선택적 OpenMP pool의 `libomp.dylib`을 찾지 못한다.
- 관련 코드: 빌드 환경의 Numba, `build_windows_onedir.ps1`, `build_mac.sh`
- 원인: 사용하지 않는 선택적 병렬 backend가 PyInstaller 분석 대상에 포함됨.
- 임시 우회: 현재 기본 분석·렌더 경로는 해당 backend를 사용하지 않는다.
- 수정된 버전: 없음
- 검증 결과: 전체 테스트, Windows 패키지 실행, Windows·macOS CI 빌드 성공. 해당 backend를 실제로 호출하는 경로는 확인되지 않았다.

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
- 상태: 보류, 1.3.1 이월
- 심각도: 낮음
- 재현 조건: GitHub Actions build run의 job summary를 확인한다.
- 기대 동작: 지원 중인 Node runtime을 사용하는 action으로 경고 없이 실행한다.
- 실제 동작: `actions/checkout@v4`, `setup-python@v5`, `upload-artifact@v4`, `download-artifact@v4`가 Node 20 deprecation 경고와 함께 Node 24 강제 실행됐다.
- 관련 코드: `.github/workflows/build.yml`
- 원인: workflow action major version이 현재 runner 권장 runtime보다 오래됐다.
- 임시 우회: 현재 runner가 Node 24로 강제 실행해 build와 publish는 성공한다.
- 수정된 버전: 없음
- 검증 결과: run `30471288589` 성공. 경고만 존재한다.

## ISSUE-UI-003 효과 선택 메뉴의 계층형 하위 메뉴 미구현

- 발견 버전 / 영향 버전: 1.3.0 종료 감사 / 1.3.0, 1.3.1
- 상태: 부분 구현, 1.3.1 이월
- 심각도: 중간
- 재현 조건: Stage 4에서 `+ 효과 추가`를 누르고 카테고리에 hover 또는 click한다.
- 기대 동작: 카테고리별 하위 효과 메뉴가 열리고 화면 경계에서는 반대 방향으로 배치된다.
- 실제 동작: 검색과 category heading이 있는 단일 스크롤 팝업에 효과가 모두 인라인으로 표시된다. Up/Down·Enter·Esc·바깥 닫기와 화면 안 배치는 동작한다.
- 관련 코드: `stage4_design_effects.py:_open_effect_picker`, `docs/UI_SPEC.md`
- 원인: 계층형 submenu 대신 더 단순한 grouped popup으로 구현을 마감했다.
- 임시 우회: 검색 또는 세로 스크롤로 효과를 선택한다.
- 수정된 버전: 없음
- 검증 결과: EFFECT-002를 부분 완료로 정정했다.

## ISSUE-UI-004 테마 전환 뒤 일부 UI 요소 소실

- 발견 버전 / 영향 버전: 1.3.0 릴리스 후 사용자 보고 / 1.3.0, 1.3.1
- 상태: 재현 필요, 1.3.1 최우선 이월
- 심각도: 높음
- 재현 조건: 앱에서 다크→라이트 또는 라이트→다크로 테마를 전환하고 현재 Stage의 패널과 컨트롤을 확인한다.
- 기대 동작: 모든 요소가 새 테마 토큰으로 즉시 다시 그려지고 현재 입력값·선택·스크롤 상태가 유지된다.
- 실제 동작: 일부 화면 요소가 사라지거나 다시 그려지지 않는다는 사용자 보고가 있다. 영향 Stage와 정확한 상태 조합은 아직 확인하지 못했다.
- 관련 코드: `app.py`의 테마 전환·Stage 재구성, `ui_state.py`, 각 Stage의 `apply_theme`
- 원인: 미확인. widget 재생성, page state 복원 또는 theme callback 순서를 우선 조사한다.
- 임시 우회: 확인된 안전한 우회 없음.
- 수정된 버전: 없음
- 검증 결과: 릴리스 후 보고 단계이며 자동 회귀 테스트가 없다.

## ISSUE-PROJECT-001 프로젝트 이름 지정과 저장 차단

- 발견 버전 / 영향 버전: 1.3.0 릴리스 후 사용자 보고 / 1.3.0, 1.3.1
- 상태: 재현 필요, 1.3.1 최우선 이월
- 심각도: 차단
- 재현 조건: 새 프로젝트를 시작해 프로젝트 이름을 입력·확정한 뒤 저장을 시도한다.
- 기대 동작: 이름이 프로젝트 상태와 제목에 반영되고 유효한 `project.json`이 저장된다.
- 실제 동작: 프로젝트 이름을 지정할 수 없고 저장도 완료되지 않는다는 사용자 보고가 있다. 입력 검증과 저장 중 어느 지점이 먼저 실패하는지는 미확인이다.
- 관련 코드: `app.py` 프로젝트 생성·이름 입력·저장 callback, `project.py`
- 원인: 미확인. 이름 입력 상태, dirty tracking, 프로젝트 경로 생성과 저장 예외를 함께 조사한다.
- 임시 우회: 확인된 안전한 우회 없음.
- 수정된 버전: 없음
- 검증 결과: 릴리스 후 보고 단계이며 새 프로젝트 end-to-end 테스트가 필요하다.

## ISSUE-NAV-001 다음 작업 단계 이동 차단

- 발견 버전 / 영향 버전: 1.3.0 릴리스 후 사용자 보고 / 1.3.0, 1.3.1
- 상태: 재현 필요, 1.3.1 최우선 이월
- 심각도: 차단
- 재현 조건: 프로젝트 설정 또는 현재 단계의 필수 입력을 마치고 상단 `다음`을 누른다.
- 기대 동작: 현재 상태를 보존한 뒤 다음 Stage가 표시된다.
- 실제 동작: `다음`이 반응하지 않아 작업 흐름을 계속 진행할 수 없다는 사용자 보고가 있다.
- 관련 코드: `app.py` 상단 내비게이션, 단계 유효성 검사, Stage 전환 callback
- 원인: 미확인. ISSUE-PROJECT-001과 같은 선행 상태 실패인지 독립적인 내비게이션 회귀인지 분리해야 한다.
- 임시 우회: 확인된 안전한 우회 없음.
- 수정된 버전: 없음
- 검증 결과: 릴리스 후 보고 단계이며 새 프로젝트·기존 프로젝트를 나눠 재현해야 한다.

## ISSUE-ANALYSIS-001 분석 진행 창 조기 종료

- 발견 버전 / 영향 버전: 1.3.0 릴리스 후 사용자 보고 / 1.3.0, 1.3.1
- 상태: 재현 필요, 1.3.1 최우선 이월
- 심각도: 높음
- 재현 조건: 여러 음원을 추가하고 분석을 시작한 뒤 분석 진행 창과 실제 worker 상태를 관찰한다.
- 기대 동작: 진행 창이 현재 작업과 진행률·취소 상태를 표시하고, 분석 완료 또는 취소가 확정된 뒤 닫힌다.
- 실제 동작: 분석 진행 창이 먼저 닫히고 실제 분석은 백그라운드에서 계속되어 상태와 취소 여부를 확인하기 어렵다는 사용자 보고가 있다.
- 관련 코드: `app.py` 분석 시작·progress UI·worker callback, `analyzer.py`
- 원인: 미확인. 창 종료 callback과 worker 완료·취소 신호 순서를 우선 계측한다.
- 임시 우회: 분석이 끝날 때까지 기다릴 수는 있으나 진행 상태와 취소 제어를 잃으므로 정상 동작으로 간주하지 않는다.
- 수정된 버전: 없음
- 검증 결과: 릴리스 후 보고 단계이며 장시간·복수 파일 분석으로 재현해야 한다.

## ISSUE-UI-001 최종 스플래시 로고 외곽

- 발견 버전 / 영향 버전: 1.2.0 / 1.3.0
- 상태: 해결
- 심각도: 낮음
- 재현 조건: Windows 패키지 cold start를 캡처해 투명 외곽·핑크 halo 확인.
- 기대 동작: 배경 없는 심플한 재생·목록 심볼, 불필요한 경계·halo 없음.
- 실제 동작: 아이콘과 첫 스플래시를 RGBA 심볼로 만들고 Windows per-pixel alpha 레이어드 창에 표시한다.
- 관련 코드: `app_icon.png`, `app_icon.ico`, `app_splash.png`, `native_launcher.cs`, `app.py:SplashScreen`
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
