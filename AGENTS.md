# Auto Playlist Maker 작업 규칙

## 작업 시작 순서

1. 이 파일
2. `docs/PROJECT_OVERVIEW.md`
3. `docs/REQUIREMENTS.md`
4. `docs/FEATURE_STATUS.md`
5. `docs/DECISIONS.md`
6. `docs/KNOWN_ISSUES.md`
7. `docs/UI_SPEC.md`
8. `docs/VERSION_INDEX.md`
9. `.codex/CURRENT_CONTEXT.md`
10. `.codex/CURRENT_HANDOFF.md`
11. 사용자가 이번 채팅에서 명시한 버전의 `docs/versions/[VERSION]/`
12. `git status --short`, `git diff --stat`, 관련 diff
13. 이번 작업과 직접 관련된 코드와 테스트

## 버전 규칙

- 프로그램 버전은 사용자가 현재 채팅에서 직접 명시한 값만 사용한다.
- 코드, 폴더명, Git 기록 또는 이전 문서만 보고 버전을 추정하거나 올리지 않는다.
- 사용자가 버전을 명시하지 않았다면 새 버전 폴더와 `VERSION_INDEX` 항목을 만들지 않는다.
- 기존 버전 기록을 새 버전의 현재 상태로 덮어쓰지 않는다.

## 개발 규칙

- 사용자가 폐기하지 않은 요구사항과 기존 동작을 임의로 삭제하지 않는다.
- `project.json` 호환성, 미디어 백업·재연결, 미리보기와 출력의 좌표 일치, 반복 시 마지막 플레이리스트 보존을 회귀시키지 않는다.
- UI 문자열 선택값은 번역 문구가 아니라 안정적인 내부 ID로 저장한다.
- 자동 생성물, `build/`, `dist/`, 외부 라이브러리 코드는 수정하지 않는다.
- 기존 사용자 변경이 많은 작업 트리이므로 관련 없는 변경을 되돌리거나 일괄 포맷하지 않는다.
- 새 요구사항은 `docs/REQUIREMENTS.md`, 구현 상태는 `docs/FEATURE_STATUS.md`, 결정은 `docs/DECISIONS.md`, 문제는 `docs/KNOWN_ISSUES.md`에 먼저 연결한다.

## 실행·검사·빌드

```powershell
python app.py
python -m unittest discover -s tests -v
python check_locales.py
python -m ruff check . --exclude build --exclude dist --exclude .git --select F,B
python -m pip check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_windows_onedir.ps1
```

- GUI가 없는 환경에서는 Tk 기반 UI 테스트가 skip될 수 있으므로 결과를 통과로 위장하지 않는다.
- `tests/verify_layout_fidelity.py`는 실제 미리보기/출력 캡처 입력이 필요한 수동 보조 검사다.
- macOS 빌드는 GitHub Actions ZIP 생성만으로 실제 실행 검증으로 간주하지 않는다. `docs/KNOWN_ISSUES.md`의 `ISSUE-BUILD-003`을 별도로 확인한다.

## 문서 갱신 규칙

- 새 사용자 요구사항 → `docs/REQUIREMENTS.md`
- 구현 상태 변경 → `docs/FEATURE_STATUS.md`
- 새 설계 결정 또는 기존 결정 대체 → `docs/DECISIONS.md`
- 새 버그 또는 해결 결과 → `docs/KNOWN_ISSUES.md`
- UI 동작 변경 → `docs/UI_SPEC.md`
- 저장 형식 변경 → `docs/DATA_FORMATS.md`
- 버전별 구현·검증 → 해당 버전의 `IMPLEMENTATION_LOG.md`, `TEST_RESULTS.md`
- 최신 작업 상태 → `.codex/CURRENT_CONTEXT.md`
- 다른 작업으로 인계 → `.codex/CURRENT_HANDOFF.md`와 해당 버전 `HANDOFF.md`
- 완료된 핵심 변경 → 루트와 해당 버전의 `CHANGELOG.md`

과거 사실은 삭제하지 않는다. 변경된 요구사항이나 결정은 변경 버전·이유와 대체 ID를 남긴다.

## 새 버전 시작

1. 사용자가 버전을 명시했는지 확인한다.
2. `docs/templates/`의 버전 템플릿을 `docs/versions/[VERSION]/`에 복사한다.
3. 플레이스홀더를 실제 정보로 채운다.
4. `docs/VERSION_INDEX.md`에 사용자 지정 버전 한 행만 추가한다.
5. `.codex/CURRENT_CONTEXT.md`와 `.codex/CURRENT_HANDOFF.md`를 새 현재 상태로 갱신한다.

전체 공통 문서 구조를 다시 만들거나 이전 버전 문서를 복사해 현재 사실처럼 쓰지 않는다.

## 버전 종료·인수인계

1. 요구사항·기능·결정·문제 상태를 실제 코드와 다시 대조한다.
2. 버전 `CHANGELOG.md`, `IMPLEMENTATION_LOG.md`, `TEST_RESULTS.md`, `KNOWN_ISSUES.md`를 갱신한다.
3. 버전 `HANDOFF.md`와 `.codex/CURRENT_HANDOFF.md`에 Git 상태, 미완료 작업, 다음 순서를 기록한다.
4. 배포가 확인된 경우에만 `VERSION_INDEX`와 루트 `CHANGELOG.md`를 배포 완료로 바꾼다.
