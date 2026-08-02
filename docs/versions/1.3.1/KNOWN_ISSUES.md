# 1.3.1 알려진 문제

- 현재 버전: 1.3.1
- 이전 버전: 1.3.0
- 상태: 확인 가능한 내부 문제 수정 완료, 외부 검증 잔여

## 해결

- ISSUE-PROJECT-001 프로젝트 이름 지정·생성 즉시 저장
- ISSUE-UI-004 packaged lazy Stage 상태 소실
- ISSUE-ANALYSIS-001 분석 진행 창 조기 종료와 worker Tk 직접 호출
- ISSUE-DATA-001 그룹 길이 계산 경로 불일치
- ISSUE-ARCH-001 반복 길이 계산 구현 중복
- ISSUE-TEST-001 네 해상도 preview/output 자동 비교
- ISSUE-BUILD-002 선택적 Numba backend 빌드 경고
- ISSUE-UI-003 효과 category submenu
- ISSUE-CI-001 workflow action 버전은 코드 수정 완료
- ISSUE-UI-005 긴 인라인 효과 목록과 효과 설정 창 수명주기
- ISSUE-UI-006 효과 슬라이더 마우스 조작 회귀
- ISSUE-PREVIEW-001 설정 갱신 후 미리보기 오디오 상태 소실
- ISSUE-BEAT-001 trim/중복 파일의 비트 전역 시간 매핑
- ISSUE-VIZ-001 비주얼라이저 배경 보존 검증 부재

## 독립 결함 미재현

- ISSUE-NAV-001: 분석된 트랙이 있는 Stage 0에서 `다음` 활성화와 Stage 1 이동이 자동 테스트와 패키지 시작 경로에서 정상이다. 선행 프로젝트 생성 실패와 함께 보고된 회귀로 판단하며 새 재현 정보가 있으면 재개한다.

## 남음

- ISSUE-PERF-001: 단일 EXE 최종 패키지에서 main window 64.536초로 측정되어 추가 cold-start 최적화가 필요하다.
- ISSUE-BUILD-003: macOS `.app` 실제 실행·종료 미검증.
- RENDER-001: 현 장비에 사용 가능한 NVENC/QSV/AMF 장치가 없어 실제 GPU encode 미검증.
- ISSUE-I18N-001: 11개 언어 의미 품질의 원어민 검수 미완료.
- 모든 DPI·장문 locale·미적 품질의 수동 UI 검수.
- CI workflow 최신 action은 YAML만 검증했으며 원격 run은 아직 실행하지 않았다.
- 효과 설정 창은 Stage 4 생성 시 widget tree를 만들고 처음 열 때 표시한다. 완전한 lazy widget 생성은 시작 구조 변경 금지 범위 때문에 보류했다.
- 랙의 실제 DPI·키보드 탐색·장문 번역 미적 품질은 수동 검수가 남아 있다.

세부 이력과 재현 조건은 공통 `docs/KNOWN_ISSUES.md`를 기준으로 한다.

## 환경음 잔여 사항

- 27개 `unclassified` 자산은 오분류 방지를 위해 비활성화되어 수동 검토가 필요하다.
- 프로젝트 소유자가 내장 원본 95개 전체를 CC0로 확인해 manifest와 제3자 자산 목록을 `CC0-1.0 / user_confirmed`로 갱신했다.
- 한국어 외 10개 locale의 새 환경음 문구는 영어 기본 문구이며 자연어 번역 검토가 남아 있다.
- `forest` 카테고리는 현재 등록 자산이 없어 활성화해도 소리가 나지 않는다.
- 13개 실제 카테고리 동시 6초 렌더와 8-input 상한은 검증했다. 수 시간 최대 밀도의 총 렌더 시간은 별도 성능 측정이 필요하다.

## 2026-08-01 잔여 검증

- Windows 단일 EXE는 실행·최대화·전체 화면·정상 종료를 검증했지만, 패키지 내부 Stage 4 슬라이더 자동 드래그는 별도 UI 자동화 환경에서 재검증할 수 있다. 동일 소스 UI의 실제 좌표 드래그는 통과했다.
- 전체 UI 테스트를 한 Python/Tk 인터프리터에서 누적 실행하면 네이티브 Tk menu command 한도 때문에 일부가 skip된다. 개별 회귀 테스트와 11개 locale 재생성 테스트는 통과한다.
## 2026-08-01 남은 검증

- 환경음 종류별 볼륨 변경은 deterministic 계획을 같은 재생 위치에서 다시 준비한다. 현재 Windows WAV 미리보기 백엔드는 재생 중 개별 category gain을 in-place로 변경할 수 없어 완전한 무중단 gain 변경은 미검증이다.
- Lullaby Scene의 birds/stream/ventilation/wind 후보와 일부 후보는 QA 실패 또는 실제 배포 가공본 부재로 이식하지 않았다.
- `forest`와 `singing bowl`은 현재 APM 정식 category/가공본이 없어 10분 실제 테스트 대상에 포함하지 못했다.
- 새 변경을 포함한 Windows 패키지 실제 마우스/최종 짧은 렌더 smoke와 전체 UI suite 재실행이 남아 있다.
## 최종 검증 후 남은 제한

- Windows WAV 미리보기 백엔드는 환경음 종류별 gain을 재생 중인 플레이어에 직접 바꾸지 못한다. 현재는 180ms debounce 후 가장 최근 설정으로 믹스를 재구성하고 저장한 재생 위치를 복원한다.
- forest, singing bowl 등 원본 또는 QA 통과 processed 자산이 없는 종류는 이번 이식에 포함하지 않았다.
- Lullaby Scene 후보 중 원본 대응이 없거나 stream/ventilation/wind 루프 QA에 실패한 파일은 제외했다.
- 패키지의 모든 실제 마우스 조합과 10분 결과의 주관적 이음새 청취는 최종 사용자 수동 확인이 필요하다.
- macOS package와 실제 GPU encoder는 이 Windows 환경에서 검증하지 않았다.
