# 1.3.1 Changelog

## 미리보기·렌더 기준·입력·환경음 루프

- 효과 설정이 설정창을 닫지 않아도 현재 미리보기에 반영되도록 실시간 재구성과 debounce를 복구했습니다.
- 1920x1080 Render Space를 도입해 저해상도 미리보기와 최종 출력의 위치·크기 비율을 일치시켰습니다.
- 슬라이더는 좌클릭/드래그로 조작하고 `Alt+좌클릭`으로만 초기화됩니다. 우클릭 이동과 더블클릭 초기화는 사용하지 않습니다.
- 화면 끄기/복귀 설정을 반복 후 최종 전체 시간축에 적용하고 검은 화면 중 오디오는 유지합니다.
- Lullaby Scene에서 검증된 CC0 가공 루프 14개를 원본 해시와 QA 결과를 대조한 뒤 APM 내부 자산으로 이식했습니다.
- 렌더 완료 직후 발생하던 `post_ui()` 인자 오류를 수정했습니다.


## 프로젝트·분석 진행 창 복귀

- 다른 앱을 확인한 뒤 APM으로 돌아왔을 때 프로젝트 로딩·음원 분석 진행 창이 메인 창 뒤로 사라지던 문제를 수정했다.
- 진행 중인 기존 창을 다시 표시하므로 작업 상태와 진행률이 유지된다.

## 효과 랙 공간·미리보기·프로젝트 복구 보완

- 효과 랙과 하단 기본 설정 사이를 사용자가 세로로 조절할 수 있게 했다. 기본값은 랙이 남는 공간을 사용하고 하단 설정은 약 150px이다.
- 전역 오디오와 미리보기 해상도 설정을 기본 접힘 섹션으로 변경했다.
- 완성된 0초 시작 WAV 미리보기를 다시 FFmpeg 변환하지 않고 즉시 재생한다.
- 그룹 미디어는 남았지만 최상위 `files`·분석 캐시가 빈 프로젝트를 그룹 트랙과 클립에서 복구한다.
- 미리보기 준비 완료 후 상태 문구가 연결 중으로 남던 문제를 수정했다.

## 최종 시작 및 레이아웃 개선

- 동일 프로세스 Win32 네이티브 시작 스플래시를 추가해 Tk 초기화 전에도 시작 상태가 보이도록 했다.
- packaged 단계·분석·디자인·렌더 모듈의 지연 로딩을 유지하고 사용하지 않는 패키징 모듈을 제외했다.
- 효과 화면의 기본 분할을 미리보기 3 : 효과 랙 1로 조정했다.
- Windows 단일 EXE onedir를 재빌드하고 정상 시작·단일 프로세스·정상 종료를 검증했다.

실제로 완료하고 검증한 변경만 기록한다.

## Added

- 효과 선택기의 카테고리 hover/click 하위 메뉴와 화면 경계 반전 배치를 추가했다.
- background 작업이 Tk를 직접 호출하지 않도록 앱 공통 `post_ui()` 큐를 추가했다.
- Stage 4 미리보기 오른쪽에 고정된 단일 효과 랙과 효과별 독립 설정 창을 추가했다.
- 효과 랙에 활성화, 경고, 설정, 실제 합성 단계 내 순서 변경, 삭제를 추가했다.

## Changed

- 새 프로젝트 기본 저장 위치를 사용자 `Documents/AutoPlaylistMaker`로 변경했다.
- 앱·Windows/macOS 빌드 버전을 지정값 1.3.1로 맞췄다.
- 그룹 길이 계산을 trim·crossfade를 반영하는 공통 렌더 기준으로 통일했다.
- Stage 4·5와 NumPy를 실제 필요 시 import하고 Python 로딩 스플래시의 Tk root를 메인 창에 재사용한다.
- GitHub Actions를 `checkout@v7`, `setup-python@v6`, `upload-artifact@v7`, `download-artifact@v8`로 갱신했다.
- Stage 4를 미리보기 왼쪽·효과 랙 오른쪽의 조절 가능한 고정 패널로 개편했다.
- 효과 순서·활성 상태·단일 인스턴스 ID를 project format v4의 기존 확장 필드로 저장한다.

## 2026-08-01 Final corrections

- Removed the separate Windows launcher/core executable split; the onedir package now exposes one application EXE with a PyInstaller splash.
- Kept the analysis progress window alive until the worker exits and added real phase/file progress.
- Invalidated in-memory analysis cache entries when the source file changes.
- Fixed scene-transition video blending, window resize/maximize/fullscreen behavior, custom resolution synchronization, and clean shutdown.

## Fixed

- 새 프로젝트 생성 성공 표시 후 `project.json`이 존재하지 않던 문제를 수정했다.
- 잘못된 프로젝트 이름·기존 프로젝트 중복·쓰기 실패가 예외나 덮어쓰기로 이어지지 않도록 했다.
- 같은 이름의 기존 일반 폴더와 앞뒤 공백 이름도 프로젝트 생성 대상으로 사용하지 않도록 했다.
- 패키지 lazy Stage가 첫 진입 전 저장·테마/언어 재구성에서 최신 page·legacy 상태를 잃거나 덮어쓰던 문제를 수정했다.
- 분석 worker가 Tk `after()`를 직접 호출하고 진행 창이 worker보다 먼저 닫힐 수 있던 문제를 수정했다.
- 렌더 worker가 Tk 변수를 직접 읽는 경로와 render 중 Stage 재구성, 지연 progress 값 덮어쓰기, 입력 오류 뒤 취소 버튼 잔류를 수정했다.
- 수동 편집·그룹 drag·trim·자동 분배의 `total_duration` 계산 불일치를 수정했다.
- Windows/macOS 빌드에서 사용하지 않는 Numba TBB/OpenMP pool 경고를 제거했다.
- 잘린 트랙과 같은 파일이 반복된 그룹에서 비트 시간이 잘못 매핑되던 문제를 수정했다.
- 미리보기 오디오 설정 갱신 시 재생 위치와 재생 여부가 사라지던 문제를 수정했다.
- 효과 설정 창 내부 슬라이더의 실제 마우스 조작 경로를 회귀 테스트로 고정했다.
- 비주얼라이저가 배경을 덮는 회귀가 없도록 알파 합성 픽셀 검증을 추가했다.
- 독립 설정 창에서 글꼴 선택기 바깥 클릭 닫기가 메인 창 클릭에도 반응하도록 수정했다.

## Performance

- source `import app` 누적 시간을 약 4.419초에서 2.331초로 줄였다.
- Windows 최종 onedir를 단일 EXE로 통합했다. 최종 main window 측정은 64.536초이며 추가 cold-start 최적화는 남아 있다.

## Validation

- 전체 92 tests 통과(환경 제한 21 skipped), locale 0/0, Ruff F/B, py_compile, pip check 통과.
- 네 해상도 preview/output 픽셀 비교 통과.
- Windows 1.3.1 onedir/ZIP 빌드와 GUI 시작·정상 종료·잔류 프로세스 0 확인.
- 96×64, 1초 합성 오디오/비주얼라이저/비트 flash MP4 실제 렌더를 완료했다.

## Startup, rack, preview, and render completion

- 투명 가장자리 color-key 번짐을 피하도록 빌드 스플래시를 불투명 다크 카드로 합성하고 `bootstrap.py`를 패키지 진입점으로 사용한다.
- 시작 구간별 timing marker와 FFmpeg 인코더 PID를 로그에 남긴다.
- 효과 랙 기본 폭을 280px(최소 220px)로 줄이고 기본 슬롯을 전역 오디오, 장면 전환, 기본 배경으로 고정했다.
- 완료 영상 반복 편집기를 효과 단계에서 제거하고 렌더 단계가 단독 소유하도록 변경했다.
- 미리보기 기본 범위를 2곡으로 하고, `auto/low/medium/high/custom` 품질을 최종 출력 해상도와 독립시켰다.
- 미리보기 로딩은 첫 프레임과 오디오 준비가 모두 끝날 때까지 유지하며 오래된 비동기 콜백을 무시한다.
- 렌더는 실제 산출물이 없으면 실패하고 FFprobe로 파일 크기, 영상·오디오 스트림, 해상도, 길이를 확인한 뒤에만 완료된다.

## Known Issues

- macOS `.app` 실제 실행은 Windows 환경에서 검증할 수 없었다.
- 이 장비의 NVENC/QSV/AMF encoder는 목록에는 있으나 실제 encoder open에 실패해 GPU 렌더 실기기 검증은 남아 있다.
- 번역 의미 품질의 원어민 검수와 모든 DPI·장문 UI 수동 검수는 남아 있다.
- Windows package 절대 시작 시간은 여전히 길다.

## Built-in ambient library

- `sound_effect_library`의 ZIP 4개와 직접 음원 18개를 안전 검사한 뒤 정리했다.
- 총 96개 후보 중 95개를 매니페스트에 등록하고, 너무 짧은 1개는 `unclassified/rejected`에 보존했다.
- Stage 4에 카테고리·소스 선택, 미리듣기, 밀도·변형·구간·페이드·mute/solo 및 재검색 UI를 추가했다.
- 미리보기와 최종 반복 렌더가 같은 결정적 환경음 계획과 FFmpeg 믹싱 경로를 사용한다.
- 폴더형 패키지에 라이브러리·매니페스트·라이선스를 포함하도록 빌드 스크립트를 갱신했다.

## Ambience effect structure correction

- 환경음을 전역 오디오 레이어에서 제거하고 효과 랙의 단일 `ambience_mixer` 효과로 이동했다.
- 환경음 설정은 실제 파일 대신 14개 환경음 종류의 활성 상태와 볼륨만 표시·저장한다.
- 환경음 버스를 120초 chunk, 최대 8개 입력 batch, filter script와 concat 목록으로 먼저 렌더해 `WinError 206`을 방지한다.

## Preview, text and render reliability

- 효과 설정의 180ms 실시간 미리보기 갱신을 복구하고 해상도·범위·대상 곡 변경 시 renderer를 안전하게 다시 생성한다.
- 전체 화면 clip 위에서 album/logo/곡 정보/사용자 텍스트를 보존하고 사용자 텍스트의 스타일·시간·대상 곡 옵션을 추가한다.
- 렌더 취소를 encoder까지 전달하고 작업별 상태 로그와 비모달 오류 작업 창을 제공한다.
- 같은 파일명 곡의 시각 cache 충돌과 비결정적 beat shake를 수정한다.
