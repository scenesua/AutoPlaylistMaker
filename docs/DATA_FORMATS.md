# 데이터 형식

## 프로젝트 폴더

```text
projects/[project name]/
├─ project.json
├─ audio/
├─ images/
├─ video/
├─ drafts/
└─ analysis_cache/*.npz
```

- 원본 미디어를 타입별 하위 폴더에 복사한다.
- 프로젝트 안의 경로는 가능한 상대 경로로 저장한다.
- 같은 원본 경로를 반복 추가하면 기존 백업을 재사용한다.
- basename 충돌은 `_1`, `_2` suffix로 피한다.

## `project.json`

현재 형식 버전은 `4`다. 저장은 임시 파일을 fsync한 뒤 `os.replace()`하는 원자적 교체다.

### 최상위 필드

| 필드 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `format_version` | 예 | 4 | 프로젝트 스키마 버전 |
| `name` | 예 | `""` | 프로젝트명 |
| `created` | 예 | `""` | ISO 생성 시각 |
| `saved` | 저장 시 | 현재 시각 | ISO 마지막 저장 시각 |
| `target_duration` | 예 | `3600.0` | 자동 분배 목표 초 |
| `tolerance` | 예 | `0.10` | 목표 허용 오차 |
| `files` | 예 | `[]` | original/backup/type 미디어 목록 |
| `video_groups` | 예 | `[]` | 그룹·트랙·클립·그룹 설정 |
| `track_analyses` | 예 | `{}` | 분석 metadata와 NPZ cache 경로 |
| `app_state` | 예 | `{}` | 전체 UI·디자인·렌더·반복 상태 |

알 수 없는 필드는 현재 저장 과정에서 모두 보존된다고 보장하지 않는다. 외부 도구가 임의 필드를 넣는 형식은 공개 확장 인터페이스가 아니다.

### `files[]`

```json
{
  "original": "C:/source/song.wav",
  "backup": "audio/song.wav",
  "type": "audio"
}
```

- 원본이 없으면 backup을 선택한다.
- 원본과 backup이 모두 없으면 항목을 삭제하지 않고 누락 상태로 유지한다.

### `video_groups[]`

주요 필드:

- `name`, `total_duration`
- `tracks[]`
- `bg_image`
- `clips[]`
- `clip_enabled`, `clip_interval`, `clip_interval_unit`
- `clip_random`, `clip_random_base`
- `design`, `settings`

`clip_interval_unit`은 `seconds|beat|per_track`, `clip_random_base`는 `bpm|key|camelot|order`의 안정적 ID다.

### `tracks[]`

```json
{
  "filename": "song.wav",
  "filepath": "audio/song.wav",
  "trim_start": 0.0,
  "trim_end": 180.0,
  "volume": 1.0,
  "fade_in": 0.01,
  "fade_out": 0.01,
  "effects": {},
  "metadata": {},
  "missing": false,
  "bpm": 120.0,
  "key": "C",
  "mode": "major",
  "camelot": "8B",
  "duration": 180.0
}
```

분석 객체는 JSON에 직접 직렬화하지 않고 metadata와 NPZ cache로 분리한다.

### `clips[]`

```json
{
  "filepath": "images/cover.png",
  "type": "image"
}
```

지원 type은 현재 `image`, `video`다.

### `app_state`

```json
{
  "current_step": 4,
  "step_complete": {},
  "pages": [],
  "distribution": {},
  "design": {},
  "visualizer": {},
  "render": {},
  "repeat": {
    "enabled": true,
    "mode": "target",
    "count": 1,
    "target_h": 2,
    "target_m": 0,
    "target_s": 0
  },
  "visibility": {},
  "ui": {
    "dark_mode": true
  }
}
```

- `pages[]`는 Stage class 이름, Tk variable 값과 허용된 plain state를 가진다.
- 선택값은 번역 문자열이 아니라 안정적 ID를 사용한다.
- `render.output_dir`은 마지막 출력 폴더다.
- panel 접힘·scroll 위치는 현재 별도 저장하지 않는다.
- `design.active_effects`와 Stage 4의 `active_effect_ids`는 추가된 효과 카드의 안정적 ID 목록이다. 이 필드가 없는 구형 프로젝트는 기존 효과 전체를 활성 상태로 마이그레이션한다.
- `design.global_audio`는 음악 master gain, 정규화/target/True Peak, 환경음 master gain과 환경음 레이어 목록을 저장한다.
- 환경음 레이어는 `filepath`, `enabled`, `volume_db`, `pan`, `width`를 포함하며 프로젝트 안으로 백업된 상대 경로를 사용할 수 있다.
- page plain state는 capture 시 deep copy하여 환경음 레이어나 효과 목록의 이후 변경이 저장 스냅샷을 오염시키지 않는다.

## 분석 캐시

`analysis_cache/[safe basename]_[path hash].npz`에 다음 NumPy 배열을 압축 저장한다.

- `energy_profile`
- `beat_times`
- `chroma`
- `rms`
- `stft_magnitudes`
- `stft_times`
- `waveform`

메타데이터만 자동 저장할 때 기존 `track_analyses`를 지우지 않는다. 캐시가 손상되면 기본 빈 배열로 복원하며 분석 재실행이 필요할 수 있다.

## 설정 저장

- 언어 환경 설정: 사용자 홈의 `.autoplaylistmaker_lang`, JSON `{"lang":"ko-KR"}`.
- 기본 시각 설정: 저장소·번들의 `visual_config.json`.
- 렌더 중 그룹별 시각 설정: 임시 작업 폴더 `_visual.json`.
- 렌더 완료 checkpoint: `RenderJob`이 그룹별 출력 파일 존재로 판단한다.

언어 환경 설정은 프로젝트 파일과 분리된 전역 사용자 설정이다. 지원 코드는 `ko-KR`, `en-US`, `ja-JP`, `zh-CN`, `zh-TW`, `es-ES`, `fr-FR`, `it-IT`, `ar`, `de-DE`, `ru-RU`다.

## 내보내기

- 혼합 오디오: WAV 중간 파일
- 최종 영상: MP4
- track timestamp: TXT
- Windows 배포: `dist/AutoPlaylistMaker_v[VERSION]/`와 `_windows_x64.zip`
- macOS 배포: `AutoPlaylistMaker_v1.3.0.app`과 `AutoPlaylistMaker_v1.3.0_macos.zip`. GitHub Actions 빌드·ZIP 내부 검사는 통과했지만 실제 macOS 실행·종료는 ISSUE-BUILD-003으로 남아 있다.

## 마이그레이션·호환성

- `Project._migrate_app_state()`가 오래된 프로젝트에 `current_step`, `step_complete`, `distribution`, `design`, `visualizer`, `render`, `repeat`, `ui` 기본 분기를 채운다.
- v2 프로젝트의 트랙 trim/volume/fade/effects/metadata를 보존하는 테스트가 있다.
- 과거 localized clip/repeat/visualizer/codec 값은 `choice_id()`와 legacy mapping을 통해 안정적 ID로 바꾼다.
- `repeat.target_seconds`는 현재 H/M/S 필드로 복원할 수 있다.
- 과거 original path가 사라지면 backup 또는 alias 분석 cache를 사용한다.
- page audio state가 없는 구형 프로젝트는 `design.global_audio`를 우선 복원하고, 그것도 없으면 legacy `render.normalize_loudness`와 target 값을 전역 오디오 설정으로 옮긴다.

형식 변경 시 `PROJECT_FORMAT_VERSION`을 변경하고 migration, 실패 복구, 이전 프로젝트 회귀 테스트와 버전 `DATA_FORMAT_CHANGES` 기록을 먼저 추가해야 한다.

## 손상·누락 처리

- 잘못된 기존 JSON으로 저장할 때는 이전 데이터를 빈 dict로 간주하지만 원자적 새 파일을 쓴다.
- load 시 JSON 파싱 오류는 호출자에게 전달해 명확한 열기 실패로 처리한다.
- 누락 미디어는 `missing_paths()`로 수집하고 `relink_missing()`으로 basename 재검색한다.
- 분석 NPZ 읽기 실패는 로그를 남기고 빈 분석 배열을 사용한다.
- 저장 실패 시 temp 파일을 지우고 원본 `project.json`을 유지한다.
