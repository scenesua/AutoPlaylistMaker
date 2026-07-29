# 1.3.0 Changelog

실제 작업 트리에 존재하고 자동 또는 직접 검증한 변경을 기록한다. 상세 요구사항은 공통 ID를 참조한다.

## Added

- 11개 언어 리소스, 언어 팝업, 안정적 선택 ID: I18N-001, UI-001
- Python 초기화 전 투명 아이콘 런처와 진행 로딩 스플래시: UI-002, UI-006
- DAW형 파형 trim과 정밀 drag: AUDIO-002
- 그룹 간 DnD indicator와 최초 `Mix N` 자동 생성: DIST-002, DIST-003
- 검색형 공통 폰트 selector: FONT-001
- 두 곡 전환 preview: PREVIEW-002
- 반복 횟수·목표 시간 계획과 전체 영상 반복: REPEAT-001
- 공통 FFmpeg resolver: RENDER-002
- 프로젝트 전체 상태·missing media relink: SAVE-001, SAVE-002
- 프로젝트 기억·버전 인수인계 체계: DOC-001

## Changed

- 디자인·효과와 render 화면을 별도 Stage로 분리: CORE-001, DEC-007
- 반복 편집은 디자인/효과 Stage가 소유하고 render Stage는 요약만 표시
- preview와 output 해상도·FPS·renderer 공유: PREVIEW-001
- 프로젝트 형식을 v4로 확장하고 atomic save 적용: SAVE-001
- packaged 실행에서 후속 Stage를 지연 생성: PERF-001

## Fixed

- trim release 후 handle이 cursor를 계속 따라가던 회귀
- 빈 그룹과 그룹 없는 상태의 drag/button 이동
- 언어 변경 후 UI state와 codec/visualizer/repeat 의미가 바뀌던 회귀
- FFmpeg preview/render 탐색 경로 불일치
- output queue의 codec label late binding
- 앱 종료 후 preview/render child process 잔류
- metadata-only autosave가 analysis cache를 덮어쓰던 문제

## Performance

- FFmpeg streaming mix와 frame pipe 유지
- waveform peak 계산 중복 통합
- repeat 필드 변경 시 불필요한 preview 재렌더 제거
- packaged Stage lazy creation

## UI/UX

- transparent native icon splash, 진행 로딩 패널, 단색 재생·목록 icon
- 전문 도구형 3단계 표면, Noto Sans KR, 공통 컨트롤 상태와 입력 focus
- 상단 진행 내비게이션, 프로젝트 설정, 빈 상태와 Stage 4·5 패널 위계 개선
- 첫 단계 coffee donation link
- font popup 내부 scroll·keyboard·outside close
- DnD insertion line·empty group target
- 반복 예상 횟수·출력·초과 시간 표시

## Deprecated

- 번역된 UI label을 저장값으로 사용하는 방식
- 단일 대형 `Stage3VideoEdit`

## Removed

- PC 종료 예약 요구사항
- render Stage의 중복 반복 편집기

## Known Issues

- ISSUE-BUILD-001, ISSUE-PERF-001, ISSUE-ARCH-001, ISSUE-DATA-001, ISSUE-TEST-001, ISSUE-I18N-001, ISSUE-BUILD-002, ISSUE-WORK-001

## 2026-07-29 final UI/audio additions

- Added opt-in effect cards with themed searchable category menu, empty new-project state, and card/section reset.
- Added independent global music/ambient/master buses, per-track loudness analysis, normalization limits, True Peak limiting and selectable real L/R meter stems.
- Added continuous ambient mixing across the final repeated media timeline.
- Changed Stage 4 to preview-left/inspector-right and grouped global audio controls into compact accordions.
- Added red danger hover and green add hover states.
- Fixed Stage 5 light-mode gray outer gutter.
- Fixed unconnected `music_bus_main` after FFmpeg `asplit`; this was a filtergraph wiring bug, not a timeout.

## 2026-07-30 native splash and German/Russian

- Added `de-DE` and `ru-RU`; the 11-locale grid preserves stage and project state.
- Added the 29KB Windows native launcher, which shows a transparent icon before PyInstaller/Python initialization.
- Handed off from native icon to the Tk progress/status splash, then from loading splash to the actual main window.
- Replaced legacy logo/icon assets with a flat RGBA mark without background, gradient, shadow, or halo.
- Verified native 2.53s, loading 53.09s, main 87.24s, sub-0.2s handoffs, and no residual splash.
