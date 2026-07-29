# 버전 문서 사용법

- 사용자가 현재 채팅에서 버전을 직접 명시한 경우에만 `docs/versions/[VERSION]/`을 만든다.
- 공통 문서를 복사하지 말고 요구사항·결정·문제 ID로 참조한다.
- 이전 버전 폴더는 수정하지 않는다. 사실 오류를 고칠 때는 정정 사유와 원문을 함께 남긴다.

## 새 버전 시작 예시

아래 `[VERSION]`과 `[PREVIOUS_VERSION]`은 사용자가 지정한 값으로 직접 바꾼다.

```powershell
$version = '[VERSION]'
$dir = Join-Path 'docs\versions' $version
New-Item -ItemType Directory -Path $dir
Copy-Item 'docs\templates\VERSION_OVERVIEW_TEMPLATE.md' (Join-Path $dir 'VERSION_OVERVIEW.md')
Copy-Item 'docs\templates\VERSION_CHANGELOG_TEMPLATE.md' (Join-Path $dir 'CHANGELOG.md')
Copy-Item 'docs\templates\VERSION_HANDOFF_TEMPLATE.md' (Join-Path $dir 'HANDOFF.md')
New-Item -ItemType File (Join-Path $dir 'IMPLEMENTATION_LOG.md')
New-Item -ItemType File (Join-Path $dir 'TEST_RESULTS.md')
New-Item -ItemType File (Join-Path $dir 'KNOWN_ISSUES.md')
```

생성 직후 모든 placeholder를 채우고 `docs/VERSION_INDEX.md`와 `.codex/CURRENT_CONTEXT.md`를 갱신한다. 빈 문서 상태로 작업을 시작하지 않는다.
