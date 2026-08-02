# 1.3.1 구현 기록

## 2026-08-01 프로젝트·분석 진행 창 포커스 복귀

- `TaskProgressOverlay`가 APM 창의 `<FocusIn>`을 감지해 진행 중인 창을 다시 표시하고 전면으로 올리도록 수정했다.
- 프로젝트 로딩과 음원 분석이 같은 공용 진행 창을 사용하므로 한 곳의 수정으로 두 경로에 적용했다.
- 포커스 복귀 시 새 창이나 작업 객체를 만들지 않고 기존 진행 창과 상태를 유지한다.

## 2026-08-01 short test 2 실데이터 수정

- `short test 2`의 3개 WAV와 4개 이미지를 그룹 데이터에서 재구성했다.
- 캐시 없는 프로젝트 불러오기 worker가 분석 모듈을 준비하고, 결과를 Stage 0 트랙과 영상 그룹 트랙 양쪽에 연결한다.
- 실제 프로젝트 불러오기 41.52초 후 오디오 3개 분석 완료, Stage 4 미리보기 17.71초 후 렌더러·첫 프레임·오디오 준비 완료를 확인했다.
- 전역 오디오·미리보기 해상도는 `AccordionSection`을 재사용하고 랙/설정 크기 조절은 Tk `PanedWindow`를 재사용했다.

## 2026-08-01 최종 시작 최적화 및 효과 랙 비율

- Windows 패키지는 Tk가 준비되기 전에 동일 프로세스의 Win32 네이티브 스플래시를 표시한다. 별도 launcher/core EXE는 사용하지 않는다.
- 실제 패키지에서는 0단계만 시작 시 생성하고 1~5단계는 최초 진입 시 생성한다. Stage 4/5 모듈도 해당 단계 최초 진입 시 import한다.
- 분석기, NumPy, Pillow, 배포 및 영상 생성 모듈은 실제 작업이 요청될 때 import한다.
- 효과 화면은 최초 표시 때 실제 작업 영역 기준으로 `미리보기 3 : 효과 랙 1` 분할을 적용한다. 이후 사용자의 sash 드래그는 덮어쓰지 않는다.
- 효과 랙 요청 너비는 240px, 최소 너비는 200px이며 실제 초기 비율은 UI 테스트에서 2.8~3.2:1로 검증한다.
- PyInstaller에서 실행 시 쓰지 않는 pytest, setuptools, win32com, cryptography 계열 모듈을 제외했다.

- 현재 버전: 1.3.1
- 이전 버전: 1.3.0
- 기준 커밋: `3768c3e`
- 현재 상태: 구현 완료, 외부 검증 잔여

## 상태 복원

- clean `D:\aldente yt\AutoPlaylistMaker_release_v1.3.0`에서 독립 작업 폴더 `D:\aldente yt\AutoPlaylistMaker_v1.3.1`과 `codex/v1.3.1` 브랜치를 만들었다.
- 기준선은 63 tests 통과였다.

## 구현

- `app.py`
  - 프로젝트 기본 경로·생성 오류 처리·lazy Stage 복원을 수정했다.
  - 분석 worker는 queue에만 기록하고 메인 thread poller가 UI를 갱신한다.
  - 저장·분배·waveform·preview·render callback을 공통 `post_ui()` 큐로 전달한다.
  - 수동 추가·제거·drag·trim·자동 분배의 그룹 길이를 공통 estimator로 갱신한다.
  - Stage 4·5 import를 실제 진입 시점까지 지연한다.
  - Python loading splash의 Tk root를 메인 앱에 넘겨 중복 Tk 초기화를 제거한다.
- `project.py`
  - NumPy import를 분석 cache 사용 시점까지 지연한다.
  - 프로젝트 이름을 검증하고 기존 프로젝트 덮어쓰기를 막으며 생성 즉시 빈 format v4를 저장한다.
- `stage4_design_effects.py`
  - 검색 목록을 유지하면서 카테고리 hover/click 하위 메뉴와 화면 경계 반전을 추가했다.
  - Stage 본문 효과 목록을 랙 버튼·활성/경고 요약으로 교체했다.
  - 효과 랙은 미리보기 오른쪽에 고정된 임베디드 패널로 배치하고, 효과별 설정 `Toplevel`만 singleton으로 재사용한다.
  - 현재 데이터 모델에 맞춰 모든 효과를 단일 인스턴스로 제한했다.
  - background/text/visualizer/fade/beat/post/visibility의 고정 합성 단계를 표시하고 실제 순서를 지원하는 album/logo 단계만 이동할 수 있게 했다.
  - 효과별 enabled 상태와 effect order/instance 메타데이터를 저장·복원한다.
  - 시각 설정 갱신은 재생 오디오를 유지하고 오디오 설정 변경은 위치·재생 상태를 보존한 재믹스로 처리한다.

## 2026-08-01 최종 안정화

- Stage 4를 `미리보기 | 효과 랙` 순서의 수평 splitter로 확정했다. 효과 랙 자체는 별도 창을 만들지 않는다.
- 분석 진행 창을 비모달·앱 소유 객체로 유지하고, 워커는 UI 큐만 갱신하며 실제 분석 단계와 파일 진행률을 표시한다.
- 분석 결과에는 소스 크기·수정 시각 서명을 연결해 실행 중 파일이 바뀌면 낡은 캐시를 재사용하지 않는다.
- 장면 전환 중 영상도 오디오 overlap과 같은 구간에서 두 배경을 보간한다.
- 사용자 해상도는 preset과 즉시 동기화하고 홀수·범위 밖 값을 보정하며 잘못된 문자열은 마지막 정상값으로 복원한다.
- Windows는 PyInstaller splash를 포함한 단일 `AutoPlaylistMaker_v1.3.1.exe` onedir 구조로 통합했다. 별도 launcher/core EXE는 생성하지 않는다.
- 종료 시 root 전체의 Tcl callback을 일괄 삭제하던 코드를 제거해 정상 종료의 이중 삭제 오류를 해결했다.
- `video_gen.py`
  - overlay order를 실제 album/logo 합성 순서에 연결했다.
  - beat cache를 filename 기준에서 track index 기준으로 바꾸고 trim source offset을 반영했다.
  - beat timeline 준비 결과를 로그로 남긴다.
- `font_combo.py`
  - 독립 설정 창 안의 popup도 설정 창과 메인 창 양쪽 바깥 클릭으로 닫히게 했다.
- `ui_state.py`
  - `effect_enabled_states`를 plain state로 저장한다.
- `stage5_render.py`
  - render worker의 Tk 직접 호출을 공통 UI queue로 교체했다.
  - 렌더 시작 전에 프로젝트·UI 상태를 snapshot하고 렌더 중 테마·언어·Stage 이동을 잠근다.
  - progress callback 값을 queue 등록 시 고정하고 입력 오류 뒤 버튼 상태를 복원한다.
- `timeline_utils.py`
  - 호환 API는 유지하고 길이 계산을 `repeat_settings`에 위임한다.
- 빌드·CI
  - 버전을 1.3.1로 동기화했다.
  - 사용하지 않는 Numba TBB/OpenMP pool만 제외했다.
  - GitHub Actions major와 기본 tag를 갱신했다.

## 검증용 회귀 테스트

- 프로젝트 생성 즉시 저장·이름 거부·UI 오류 처리
- packaged lazy Stage의 첫 진입 전 저장·테마 재구성·legacy 상태 복원
- 분석 worker 종료 전 overlay 유지
- trim/crossfade 그룹 길이와 렌더 추정 일치
- 효과 category submenu 추가
- app import 시 Stage 4·5·NumPy 미로딩
- loading splash Tk root의 main handoff
- render 중 Stage 재구성 잠금과 잘못된 repeat 입력 버튼 복원

## 2026-07-30 — 내장 환경음 라이브러리

- `ambient_library.py`: 안전 ZIP 검사, FFprobe/FFmpeg 검증, 해시/PCM fingerprint, 분류, 원자적 매니페스트와 증분 재검색.
- `ambient_engine.py`: 요소별 seed로 전체 최종 타임라인의 연속/이벤트 환경음 계획을 결정적으로 생성.
- `audio_pipeline.py`: 환경음 전용 bus/stem과 gain·pan·width·fade·delay·true-peak 제한을 스트리밍 FFmpeg 경로에 연결.
- `stage4_design_effects.py`: Stage 4 진입 시 라이브러리 로드, worker queue 기반 재검색 진행 창.
- 원본 ZIP은 후보가 모두 등록 또는 별도 보존된 경우에만 삭제한다. 최초 처리에서 누락됐던 `slime_12.ogg`는 동일 원본 ZIP과 해시를 대조해 복구했다.

## 2026-08-01 — 환경음 효과 구조 정정

- UI·프로젝트 상태는 단일 `ambience_mixer`와 종류별 `enabled`·`volume_db`만 사용한다.
- 기존 `global_audio.ambient_tracks` 프로젝트는 category 항목과 사용자 파일을 통합 효과 내부 상태로 마이그레이션한다.
- 환경음 계획은 종류별 내부 자산을 자동 순환하지만 렌더 명령은 120초 chunk와 8-input batch로 제한한다.
- 긴 filtergraph는 `-filter_complex_script`, chunk 결합은 FFconcat 목록, 최종 music mix는 중간 ambient WAV 입력 하나만 사용한다.

## 2026-08-01 — 시작·기본 효과 랙·미리보기·렌더 완료 판정

- `bootstrap.py`에서 패키지 스플래시를 먼저 확인한 뒤 앱을 import하며 시작 timing marker를 기록한다.
- Windows 빌드는 알파 스플래시를 불투명 다크 카드에 합성하고, 아이콘과 FFprobe를 onedir 내부에 포함한다.
- Stage 4 기본 랙 폭은 280px/최소 220px이며 기본 슬롯은 전역 오디오, 장면 전환, 기본 배경이다.
- 환경음은 기본 슬롯이나 전역 오디오가 아니라 중복 불가 `ambience_mixer` 사용자 효과로 유지한다.
- 반복 설정은 Stage 5만 소유하고 기존 top-level `repeat` 저장 형식을 그대로 사용한다.
- 미리보기는 기본 2곡, 독립 품질/해상도, 단계별 로딩과 stale callback 차단을 사용한다.
- 렌더 작업은 명시적 상태, 인코더 PID, FFprobe 산출물 검증 후 완료 처리를 사용한다.
## 2026-08-01 실시간 미리보기·렌더 좌표·환경음 루프 보완

- 최신 패키지의 렌더 실패 로그를 추적해, 출력 검증 완료 뒤 `post_ui()`에 콜백 외 인자를 전달하던 오류를 수정했다.
- 효과 설정 변수는 공용 프로젝트 상태를 즉시 dirty 처리하고 180ms debounce 뒤 현재 `LiveFrameRenderer`를 재구성한다. 새 미리보기 요청은 generation으로 이전 결과를 폐기하며 수동 새로고침은 전체 준비 경로와 로딩 표시를 사용한다.
- 프로젝트 시각 값은 1920x1080 Render Space에 저장하고 preview/final renderer 진입 시 한 번만 대상 해상도로 변환한다. Preview Viewport는 완성 프레임 fit만 담당한다.
- Tk `Scale`의 Windows 기본 우클릭 이동 class binding을 차단했다. 좌클릭 조작은 유지하고 초기화는 `Alt+좌클릭`만 사용한다.
- 반복 영상의 화면 꺼짐은 최종 전체 타임라인을 사용하고, 미리보기에도 최종 반복 길이와 구간 offset을 전달한다.
- 알려진 길이의 환경음 파일에 적용되던 FFmpeg hard loop를 제거하고 교대 segment/crossfade만 사용한다. chunk 결합 뒤 최종 길이를 정확히 trim/pad한다.
- `D:\lullaby scene`의 코드·자산·QA 보고서를 조사했다. APM 원본과 SHA-256이 같고 QA를 통과했으며 실제 배포본이 존재하는 14개 가공 루프만 내부 `processed/loops`로 이식했다. CC0 근거는 프로젝트 소유자 확인으로 기록했다.
## 2026-08-02 최종 패키징 보정

- Lullaby Scene 원본과 SHA-256이 대응되고 루프 QA를 통과한 14개 가공본을 APM 내부 processed library로 이식했다.
- 사용자의 원본 CC0 확인에 따라 manifest의 라이선스를 `CC0-1.0`, 상태를 `user_confirmed`로 기록했다.
- 런타임 manifest에는 절대경로를 저장하지 않으며 APM은 `D:\lullaby scene`에 의존하지 않는다.
- 첫 빌드 후 processed loop와 manifest가 bundle에서 빠진 것을 검사로 발견했다.
- `build_windows_onedir.ps1`과 `build_mac.sh`에 processed 폴더와 `processed_loops.json` 수집을 추가하고 Windows package를 재생성했다.
- 최종 bundle에서 processed OGG 14개와 source/packed manifest 해시 일치를 확인했다.

## 2026-08-02 빌드 전 최종 안정화 및 리뷰

- 미리보기 해상도·범위·대상 곡이 바뀌면 이전 크기와 곡 목록을 가진 renderer를 재사용하지 않고 재생 위치를 보존해 다시 준비하도록 구조 signature를 연결했다.
- 전체 화면 clip 합성 뒤 album/logo/곡 정보/사용자 텍스트가 가려지던 순서를 수정하고, 사용자 텍스트의 투명도·외곽선·배경·표시 시간·대상 곡 옵션을 공용 상태와 렌더러에 연결했다.
- 사용자 텍스트 레이어를 프레임마다 재생성하지 않고 설정 변경 시 한 번만 캐시하며, 같은 파일명을 가진 곡의 배경·텍스트 캐시를 track index로 분리했다.
- beat shake의 난수를 제거하고 곡·시간 기준 결정적 이동으로 바꿔 미리보기와 실제 렌더의 재현성을 높였다.
- 렌더 취소 이벤트를 실제 frame encoder까지 전달하고, 그룹 예외 처리에서 취소를 실패로 삼키지 않도록 상태 전이를 수정했다.
- 렌더마다 고유 job ID와 상태별 로그를 만들고 비모달 오류 창에 로그 열기·폴더 열기·내용 복사·재시도 동작을 추가했다.
- 프로젝트 소유자의 확인에 따라 내장 원본 95개 전체를 `CC0-1.0 / user_confirmed`로 기록했다.
