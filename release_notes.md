# Auto Playlist Maker v1.3.0

## 한국어

1.3.0은 편집 화면, 오디오 처리, 비주얼라이저, 프로젝트 저장과 시작 화면을 함께 다듬은 대규모 안정화 릴리즈입니다.

### 주요 변경 사항

- **전문 작업 도구형 UI**: Noto Sans KR 기반 타이포그래피, 일관된 다크·라이트 테마, 명확한 정보 위계와 입력 상태를 적용했습니다. 최소 크기, 최대화, 긴 목록과 빈 상태에서도 패널·스크롤·버튼이 겹치거나 잘리지 않도록 정리했습니다.
- **효과 편집 구조 개편**: Stage 4에서 미리보기를 왼쪽, 효과 목록과 설정을 오른쪽에 배치했습니다. 새 프로젝트는 빈 효과 목록으로 시작하며, 검색 가능한 카테고리 메뉴에서 실제 구현된 효과만 추가할 수 있습니다. 효과 카드는 개별 접기·펼치기와 초기화를 지원합니다.
- **전역 오디오 시스템**: 음악 마스터, 환경음 믹서, 트랙 음량 정규화, True Peak 설정과 실시간 L/R 미터를 독립 섹션으로 구성했습니다. 미리보기와 최종 렌더가 같은 master/music/ambient 버스 구조를 사용합니다.
- **오디오·렌더 안정성**: BS.1770 기반 Integrated LUFS, True Peak, LRA 분석을 적용하고 짧은 환경음 반복과 전체 반복 타임라인을 안정화했습니다. 연결되지 않은 FFmpeg `asplit` 출력으로 미리보기가 실패하던 문제도 수정했습니다.
- **비주얼라이저와 타임라인**: 실제 오디오에 동기화되는 비주얼라이저 스타일과 조작 범위를 개선하고, 파형 캐시·트림·페이드·슬라이더 피드백을 정리했습니다.
- **프로젝트 저장**: 프로젝트 포맷 v4, 원자적 저장, 미디어 백업·재연결, 언어가 바뀌어도 유지되는 안정적 ID와 편집·오디오·효과·렌더 상태 복원을 지원합니다.
- **11개 언어**: 한국어, 영어, 일본어, 중국어 간체·번체, 스페인어, 프랑스어, 이탈리아어, 아랍어에 독일어와 러시아어를 추가했습니다.
- **Windows 시작 화면**: 실행 직후 투명 네이티브 아이콘 스플래시를 표시하고, 이어서 현재 작업과 진행률이 보이는 로딩 스플래시를 거쳐 메인 창으로 자연스럽게 전환합니다.

### 다운로드

- Windows: `AutoPlaylistMaker_v1.3.0_windows_x64.zip`
- macOS: `AutoPlaylistMaker_v1.3.0_macos.zip`
- FFmpeg 설치 도우미: Windows `setup.bat`, macOS `setup_mac.sh`

압축을 푼 뒤 앱을 실행하세요. FFmpeg가 설치되어 있지 않다면 운영체제에 맞는 setup 스크립트를 먼저 실행하면 됩니다.

### 참고

- 대형 오디오·과학 라이브러리를 처음 불러오는 콜드 스타트는 PC 환경에 따라 시간이 걸릴 수 있습니다.
- Windows 패키지는 실제 실행·종료까지 검증했습니다. macOS 패키지는 GitHub Actions의 macOS 환경에서 생성됩니다.

---

## English

Version 1.3.0 is a major usability and reliability update covering the editor UI, audio pipeline, visualizers, project persistence, and startup experience.

### Highlights

- **Professional desktop UI**: Refined typography, information hierarchy, spacing, input states, and consistent light/dark themes. Panels, scrolling, buttons, long lists, and empty states now adapt cleanly from the minimum window size to maximized layouts.
- **Redesigned effects workflow**: Stage 4 now places the preview on the left and the effects inspector on the right. New projects start with an empty effects list, and a searchable categorized picker exposes only effects that are actually implemented. Each effect card can be collapsed and reset independently.
- **Global audio controls**: Music master level, ambient mixing, track loudness normalization, True Peak settings, and real-time L/R meters live in a dedicated section. Preview and final render share the same master/music/ambient bus structure.
- **Audio and render reliability**: Added BS.1770 Integrated LUFS, True Peak, and LRA analysis; stabilized short ambient loops and full-playlist repetition; and fixed preview failures caused by an unconnected FFmpeg `asplit` output.
- **Visualizers and timeline**: Improved audio-synchronized visualizer styles and controls, waveform caching, trim/fade display, slider feedback, and preview behavior.
- **Project persistence**: Project format v4 adds atomic saves, media backup and relinking, locale-independent IDs, and restoration of editor, audio, effects, and render state.
- **11 languages**: Added German and Russian to Korean, English, Japanese, Simplified and Traditional Chinese, Spanish, French, Italian, and Arabic.
- **Windows startup sequence**: A transparent native icon splash appears immediately, hands off to a progress-aware loading splash, and closes when the main window is ready.

### Downloads

- Windows: `AutoPlaylistMaker_v1.3.0_windows_x64.zip`
- macOS: `AutoPlaylistMaker_v1.3.0_macos.zip`
- FFmpeg setup helpers: `setup.bat` for Windows and `setup_mac.sh` for macOS

Extract the archive and launch the app. If FFmpeg is not installed, run the setup helper for your operating system first.

### Notes

- The first cold start can take longer while large audio and scientific libraries are loaded.
- The Windows package was validated through real startup and shutdown. The macOS package is produced on a GitHub Actions macOS runner.

---

## 日本語

1.3.0 は、編集 UI、オーディオ処理、ビジュアライザー、プロジェクト保存、起動体験をまとめて改善した大規模な安定化リリースです。

### 主な変更

- **プロ向けデスクトップ UI**: タイポグラフィ、情報階層、余白、入力状態、ライト／ダークテーマを統一しました。最小サイズ、最大化、長いリスト、空の状態でもパネルやスクロール、ボタンが重ならないレイアウトになりました。
- **エフェクト編集の再設計**: Stage 4 は左側にプレビュー、右側にエフェクト一覧と設定を配置します。新規プロジェクトは空のエフェクト一覧で始まり、検索可能なカテゴリメニューには実装済みのエフェクトだけが表示されます。各カードは個別に折りたたみ、初期化できます。
- **グローバルオーディオ**: 音楽マスター、環境音ミキサー、トラック音量正規化、True Peak、リアルタイム L/R メーターを独立したセクションにまとめました。プレビューと最終レンダーは同じ master/music/ambient バス構成を使用します。
- **オーディオとレンダーの安定化**: BS.1770 の Integrated LUFS、True Peak、LRA 解析を追加し、短い環境音ループとプレイリスト全体の繰り返しを安定化しました。未接続の FFmpeg `asplit` 出力によるプレビュー失敗も修正しました。
- **ビジュアライザーとタイムライン**: 実際の音声に同期するスタイルと操作範囲、波形キャッシュ、トリム／フェード表示、スライダーのフィードバックを改善しました。
- **プロジェクト保存**: プロジェクト形式 v4、アトミック保存、メディアのバックアップと再リンク、言語に依存しない ID、編集・オーディオ・エフェクト・レンダー状態の復元に対応しました。
- **11 言語**: 韓国語、英語、日本語、中国語（簡体字・繁体字）、スペイン語、フランス語、イタリア語、アラビア語にドイツ語とロシア語を追加しました。
- **Windows 起動シーケンス**: 透明なネイティブアイコンスプラッシュをすぐに表示し、作業内容と進行率が見えるローディング画面を経てメイン画面へ切り替わります。

### ダウンロード

- Windows: `AutoPlaylistMaker_v1.3.0_windows_x64.zip`
- macOS: `AutoPlaylistMaker_v1.3.0_macos.zip`
- FFmpeg セットアップ: Windows `setup.bat`、macOS `setup_mac.sh`

アーカイブを展開してアプリを起動してください。FFmpeg が未導入の場合は、先に OS 用の setup スクリプトを実行してください。

### 注意

- 大きなオーディオ／科学計算ライブラリを初めて読み込む際は、環境によって起動に時間がかかることがあります。
- Windows パッケージは実際の起動と終了まで検証済みです。macOS パッケージは GitHub Actions の macOS 環境で生成されます。
