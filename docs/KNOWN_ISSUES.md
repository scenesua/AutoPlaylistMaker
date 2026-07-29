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
- 검증 결과: 버전, 아이콘·스플래시·locale, 1.3.0 모듈 포함을 동기화하고 셸 구문 검사를 통과했다. 릴리스 워크플로는 Windows와 macOS 빌드가 모두 성공한 경우에만 태그와 자산을 게시한다.

## ISSUE-PERF-001 패키지 첫 실행 지연

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0
- 상태: 사용자 피드백 경로 완화, 코어 속도 분석 중
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

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0
- 상태: 보류
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

- 발견 버전 / 영향 버전: 1.3.0 코드 정리 / 1.3.0
- 상태: 확인 필요
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

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0
- 상태: 해결
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

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0
- 상태: 확인 필요
- 심각도: 중간
- 재현 조건: 각 언어 원어민이 모든 단계 문구를 맥락과 함께 검수.
- 기대 동작: 자연스럽고 일관된 전문 UI 문구.
- 실제 동작: key, placeholder, 깨진 문자열 검사는 통과했지만 의미 품질을 자동 검사할 수 없다.
- 관련 코드: `locales/*.json`, `check_locales.py`
- 원인: 자동 번역·다국어 리소스 대량 추가 후 전문 감수 부재.
- 임시 우회: 영어·한국어를 기준 문구로 사용하고 신고된 문구를 ID별 수정.
- 수정된 버전: 없음
- 검증 결과: 11개 언어 구조 검사 0 errors, 0 warnings.

## ISSUE-BUILD-002 선택적 `tbb12.dll` PyInstaller 경고

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0
- 상태: 보류
- 심각도: 낮음
- 재현 조건: Windows PyInstaller 빌드.
- 기대 동작: 의존 DLL 경고 없음.
- 실제 동작: Numba 선택적 TBB pool의 `tbb12.dll`을 찾지 못한다.
- 관련 코드: 빌드 환경의 Numba, `build_windows_onedir.ps1`
- 원인: 사용하지 않는 선택적 TBB backend가 분석 대상에 포함됨.
- 임시 우회: 현재 기본 분석·렌더 경로는 해당 backend를 사용하지 않는다.
- 수정된 버전: 없음
- 검증 결과: 전체 테스트와 패키지 실행 성공.

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

## ISSUE-WORK-001 1.3.0 주요 변경이 미커밋 작업 트리에 존재

- 발견 버전 / 영향 버전: 1.3.0 / 1.3.0
- 상태: 미해결
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
