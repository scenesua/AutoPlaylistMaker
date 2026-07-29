# 🎵 Auto Playlist Maker v1.3.0

Windows와 macOS 패키지, FFmpeg 설치 스크립트가 포함되어 있습니다.

---

## 🇰🇷 한국어

1.3.0은 단순한 테마 변경이 아니라, **음원 편집 → 분배 → 클립 구성 → 디자인·효과 → 렌더**의 전체 작업 흐름을 실제 편집 프로그램처럼 다시 정리한 대규모 업데이트입니다.

### ✨ 새로 추가된 기능

- **파형에서 직접 트림 편집** — 음원의 시작·끝 핸들을 파형 위에서 바로 드래그할 수 있습니다. 최소 길이 제한, 범위 밖 드래그 캡처, Shift/Alt 미세 조절, 볼륨·페이드 설정과 프로젝트 저장을 지원합니다.
- **더 강력한 수동 분배** — 곡을 그룹 사이로 드래그하고, 그룹 안의 순서를 바꾸고, 그룹 자체도 위아래로 이동할 수 있습니다. 아직 그룹이 없으면 첫 이동 때 `Mix 1`이 자동으로 만들어집니다.
- **필요한 효과만 추가하는 효과 목록** — 새 프로젝트는 빈 효과 목록으로 시작합니다. `+ 효과 추가` 메뉴에서 카테고리와 검색으로 실제 구현된 효과만 골라 추가할 수 있습니다.
  - 배경, 앨범 이미지, 로고
  - 곡 정보, 사용자 텍스트
  - 비주얼라이저
  - 페이드, 비트 효과, CRT, 화면 표시 시간
  - 각 효과 카드는 접기·펼치기, 순서 이동, 개별 섹션 초기화, 삭제를 지원합니다.
- **전역 오디오 섹션** — 시각 효과와 분리된 전용 오디오 영역에서 음악 마스터 볼륨, 트랙 음량 정규화, 환경음 믹서, 환경음 마스터, True Peak 제한과 실시간 L/R 미터를 조절할 수 있습니다.
- **트랙별 음량 분석과 정규화** — BS.1770 기준의 Integrated LUFS, True Peak, LRA를 분석해 곡마다 다른 체감 음량을 맞출 수 있습니다. 과도한 증폭과 피크를 제한하는 설정도 함께 제공합니다.
- **환경음 믹서** — 여러 환경음을 추가하고 각각의 볼륨·페이드·반복을 설정할 수 있습니다. 완성 영상을 여러 번 반복할 때도 마지막까지 끊기지 않도록 전체 타임라인 기준으로 합성됩니다.
- **두 곡 전환 미리보기** — 곡 경계 앞뒤를 빠르게 확인해 크로스페이드와 전환 결과를 점검할 수 있습니다. 미리보기와 최종 출력은 같은 해상도·FPS·렌더 설정을 공유합니다.
- **완성 영상 반복 계획** — 반복 횟수를 직접 지정하거나 목표 재생 시간을 입력할 수 있습니다. 예상 반복 수, 최종 길이와 목표 초과 시간을 미리 보여주며, 마지막 반복을 임의로 잘라내지 않습니다.
- **프로젝트 포맷 v4** — 편집 위치, 음량·페이드, 그룹 순서, 클립, 효과, 전역 오디오, 반복, 렌더 설정과 현재 단계를 함께 저장합니다. 원자적 저장, 미디어 백업, 누락 파일 재연결과 이전 프로젝트 마이그레이션도 지원합니다.
- **11개 언어** — 한국어, 영어, 일본어, 중국어 간체·번체, 스페인어, 프랑스어, 이탈리아어, 아랍어에 **독일어와 러시아어**를 추가했습니다. 언어를 바꿔도 선택값과 프로젝트 상태가 바뀌지 않도록 내부 ID를 분리했습니다.
- **두 단계 시작 화면** — Windows에서 실행 직후 투명 네이티브 아이콘 스플래시가 먼저 나타나고, 이어서 현재 작업과 진행률이 보이는 로딩 스플래시가 표시됩니다. 메인 창이 준비되면 자동으로 닫힙니다.

### 🎨 UI·UX 개선

- **Stage 4 재배치** — 큰 미리보기는 왼쪽, 효과 목록과 세부 설정은 오른쪽에 배치해 결과를 보면서 조정하기 쉬워졌습니다.
- **디자인/효과와 렌더 단계 분리** — 한 화면에 섞여 있던 디자인 설정과 최종 출력 설정을 Stage 4와 Stage 5로 분리했습니다. 반복 설정은 편집 단계에서 관리하고 렌더 단계에서는 요약만 확인합니다.
- **전문 소프트웨어형 디자인 시스템** — Noto Sans KR 우선 글꼴, 명확한 정보 위계, 일관된 간격과 패널, 입력 포커스, 비활성·선택·hover 상태를 적용했습니다.
- **다크·라이트 모드 일관성** — 밝은 모드 상단 바와 Stage 5에 남던 어두운 배경·회색 외곽을 제거했습니다. 삭제·초기화 같은 위험 동작은 빨간 hover, 추가 동작은 초록 hover로 구분했습니다.
- **반응형 패널과 스크롤** — 최소 창, 최대화, 긴 효과·파일 목록과 빈 상태에서 요소가 겹치거나 잘리지 않도록 패널 크기, 내부 스크롤과 리사이즈 동작을 정리했습니다.
- **작업 진행 피드백** — 분석, 프로젝트 불러오기, 미리보기와 렌더 작업에 실제 진행 상태와 취소 경로를 표시합니다.
- **검색형 폰트 선택기** — 시스템 글꼴을 검색하고 키보드로 이동·선택할 수 있으며, 메뉴 밖 클릭과 Esc로 닫을 수 있습니다.
- **정밀 슬라이더 조작** — Alt+클릭으로 정의된 기본값을 복원하고, 값 표시와 조작 피드백을 개선했습니다.

### 🎶 비주얼라이저·미리보기 개선

- **5가지 비주얼라이저 유지·개선** — EQ 바, 미니멀 파형, 스펙트럼, 원형, 방사형 스타일을 제공합니다.
- **세부 조절 확대** — 개수, 높이, 간격, 감도, 스무딩, 감쇠, 투명도, 모서리, 글로우, 선 두께, 미러, 반전, 그라데이션, 색상과 X/Y/너비를 조절할 수 있습니다.
- **실제 오디오 동기화 복구** — 트림 시작점과 곡별 분석 데이터를 정확히 따라가며, 두 곡 전환에서도 각 곡의 파형·FFT 캐시를 따로 사용합니다.
- **캐시 안정성 개선** — 파일명이 같은 다른 음원이 충돌하지 않도록 하고, 구형 프로젝트의 불완전한 분석 캐시는 필요한 파일만 다시 분석합니다.
- **클립 미리보기 개선** — 이미지·영상 썸네일과 리사이즈 가능한 미리보기 영역을 제공하고, 사용자가 조절한 분할 비율을 복원합니다.

### 🐛 수정된 문제

- FFmpeg `asplit`의 `music_bus_main` 출력이 연결되지 않아 미리보기가 실패하던 문제
- 트림 드래그를 끝낸 뒤에도 핸들이 마우스를 따라가던 문제
- 빈 그룹 또는 그룹이 없는 상태에서 첫 곡 이동이 막히던 문제
- 언어 변경 후 코덱·비주얼라이저·반복 선택의 의미가 달라지던 문제
- 패키지에서 미리보기와 최종 렌더가 서로 다른 FFmpeg를 찾던 문제
- 메타데이터 자동 저장이 기존 분석 캐시를 덮어쓰던 문제
- 렌더 큐의 코덱 표시가 다른 작업의 값으로 바뀌던 문제
- 앱 종료 후 미리보기·렌더 하위 프로세스가 남던 문제
- 밝은 모드 버튼 대비, 상단 내비게이션 색상, Stage 5 회색 테두리 문제
- 반복 영상 전체 길이에 환경음이 이어지지 않던 문제

### ⚠️ 릴리스 후 확인된 주요 문제

아래 문제는 v1.3.0 배포 후 일부 작업 흐름에서 확인됐으며, 현재 정확한 재현 범위를 점검하고 있습니다. 프로젝트 진행을 막을 수 있는 항목부터 v1.3.1에서 우선 수정할 예정입니다.

- 다크 모드와 라이트 모드를 서로 전환한 뒤 일부 화면 요소가 사라지거나 다시 그려지지 않을 수 있습니다.
- 새 프로젝트에서 프로젝트 이름을 확정하지 못하거나 저장이 정상적으로 완료되지 않을 수 있습니다.
- 상단의 `다음` 동작이 반응하지 않아 다음 작업 단계로 이동하지 못할 수 있습니다.
- 음원 분석을 시작하면 진행 상황을 보여주는 창이 먼저 닫히고, 분석만 백그라운드에서 계속되어 진행 상태와 취소 여부를 확인하기 어려울 수 있습니다.

### 📦 다운로드 및 설치

- **Windows**: `AutoPlaylistMaker_v1.3.0_windows_x64.zip`
  1. ZIP 압축을 풉니다.
  2. FFmpeg가 없다면 `setup.bat`을 한 번 실행합니다.
  3. 폴더 안의 `AutoPlaylistMaker_v1.3.0.exe`를 실행합니다.
- **macOS**: `AutoPlaylistMaker_v1.3.0_macos.zip`
  1. ZIP 압축을 풀고 `.app`을 실행합니다.
  2. FFmpeg가 없다면 터미널에서 `bash setup_mac.sh`를 실행합니다.
  3. 서명되지 않은 앱 경고가 나오면 Finder에서 앱을 우클릭한 뒤 **열기**를 선택합니다.

### ✅ 검증 및 참고

- 자동 테스트 **63개 통과**
- 11개 locale key·placeholder 검사 **0 errors / 0 warnings**
- Windows와 macOS GitHub Actions 빌드 및 ZIP 생성 성공
- 최소·기본·대형 창, 다크·라이트 모드, 긴 목록과 빈 상태 레이아웃 확인
- 대형 오디오·과학 라이브러리를 처음 불러오는 콜드 스타트는 PC 환경에 따라 시간이 걸릴 수 있습니다.

---

## 🇺🇸 English

Version 1.3.0 is a major workflow update across music editing, distribution, clip design, effects, global audio, project persistence, and rendering—not just a visual refresh.

### ✨ New Features

- **Waveform trim editing** — Drag in/out handles directly on the waveform, with minimum-length protection, captured dragging outside the control, Shift/Alt fine adjustment, volume/fade controls, and project persistence.
- **Expanded manual distribution** — Move tracks between groups, reorder tracks within a group, reorder whole groups, and automatically create `Mix 1` on the first move when no group exists.
- **Add-only effects workflow** — New projects start with no effect cards. A searchable categorized picker exposes only implemented effects: background, album art, logo, track information, custom text, visualizer, fade, beat effects, CRT, and visibility timing. Cards can be collapsed, reordered, reset by section, or removed.
- **Dedicated global audio section** — Control music master level, track normalization, ambient mixing, ambient master, True Peak limiting, and real-time L/R meters independently from visual effects.
- **Per-track loudness analysis** — BS.1770 Integrated LUFS, True Peak, and LRA measurements help match perceived loudness while configurable gain and peak limits prevent excessive amplification.
- **Ambient sound mixer** — Add multiple ambient tracks with per-item volume, fades, and looping. Ambient audio now continues across the complete repeated video timeline.
- **Two-track transition preview** — Quickly inspect the area around a song boundary. Preview and final render share resolution, FPS, and renderer state.
- **Final-video repeat planning** — Repeat by count or target duration, with an estimated count, final length, and overrun shown before rendering. The last repetition is never silently truncated.
- **Project format v4** — Saves trim, volume, fades, group order, clips, effects, global audio, repeat, render settings, and the current stage. Atomic saves, media backup, missing-file relinking, and migration from older projects are included.
- **11 languages** — German and Russian join Korean, English, Japanese, Simplified/Traditional Chinese, Spanish, French, Italian, and Arabic. Stable internal IDs keep settings unchanged when the UI language changes.
- **Two-stage Windows startup** — An immediate transparent native icon splash hands off to a progress/status loading splash, which closes when the main window is ready.

### 🎨 UI/UX Improvements

- Stage 4 now uses a large preview on the left and the effects inspector on the right.
- Design/effects and final rendering are separated into Stage 4 and Stage 5.
- A consistent professional design system improves typography, hierarchy, spacing, panels, focus, selection, hover, disabled, and validation states.
- Light mode no longer leaves dark navigation surfaces or the gray Stage 5 outer gutter.
- Responsive panels, independent scrolling, long lists, and empty states behave cleanly from the minimum window size to maximized layouts.
- Real progress and cancellation feedback is shown for analysis, project loading, preview, and rendering.
- The searchable font picker supports keyboard navigation, outside-click close, and Esc.
- Alt-click restores defined slider defaults.

### 🎶 Visualizer and Preview Improvements

- Five visualizer styles: EQ bars, minimal waveform, spectrum, circles, and radial.
- Expanded controls for count, height, gap, sensitivity, smoothing, decay, opacity, corner radius, glow, line width, mirror, inversion, gradient, color, and position.
- Visualizers now follow the correct trimmed source time and keep separate waveform/FFT state for each track during transitions.
- Cache keys no longer collide for different files with the same filename; incomplete legacy analysis is rebuilt only where needed.
- Image/video thumbnails and a resizable clip preview preserve the chosen split ratio.

### 🐛 Fixes

- Unconnected FFmpeg `asplit` output causing preview preparation to fail
- Trim handles continuing to follow the pointer after release
- First move failing when groups were empty or absent
- Codec, visualizer, and repeat meanings changing after a locale switch
- Preview and render resolving different FFmpeg executables in packaged builds
- Metadata autosave overwriting analysis cache entries
- Render queue codec labels capturing another job's value
- Preview/render child processes remaining after application shutdown
- Light-mode button contrast, navigation colors, and Stage 5 gray border
- Ambient audio ending before the full repeated video timeline

### ⚠️ Known Issues Identified After Release

The following issues were reported in some v1.3.0 workflows after release. Their exact scope is being reproduced, and fixes that block normal project progression will take priority in v1.3.1.

- Switching between dark and light modes may leave some controls or panels missing until the affected view is rebuilt.
- A new project may fail to accept its project name or complete a save.
- The top-level **Next** action may not advance to the following workflow stage.
- The analysis progress window may close too early while analysis continues in the background, leaving progress and cancellation state unavailable.

### 📦 Downloads and Installation

- **Windows**: Extract `AutoPlaylistMaker_v1.3.0_windows_x64.zip`, run `setup.bat` if FFmpeg is missing, then launch `AutoPlaylistMaker_v1.3.0.exe`.
- **macOS**: Extract `AutoPlaylistMaker_v1.3.0_macos.zip`, run `bash setup_mac.sh` if FFmpeg is missing, then open the `.app`. If macOS warns about an unsigned app, right-click it in Finder and choose **Open**.

### ✅ Validation and Notes

- 63 automated tests passed
- 11-locale key and placeholder validation: 0 errors / 0 warnings
- Windows and macOS GitHub Actions builds completed successfully
- Minimum, standard, and large layouts checked in light/dark modes with long lists and empty states
- The first cold start can take longer while large audio and scientific libraries are loaded.

---

## 🇯🇵 日本語

1.3.0 は見た目だけではなく、音源編集、曲の分配、クリップ構成、デザイン・エフェクト、グローバルオーディオ、保存、レンダーまでの作業全体を改善した大型アップデートです。

### ✨ 新機能

- **波形上でのトリム編集** — 開始・終了ハンドルを直接ドラッグできます。最小長、範囲外ドラッグ、Shift/Alt の微調整、音量・フェード、プロジェクト保存に対応しました。
- **手動分配の強化** — 曲をグループ間で移動し、グループ内の順番とグループ自体の順番を変更できます。グループがない場合は最初の移動で `Mix 1` を自動作成します。
- **追加式エフェクト一覧** — 新規プロジェクトは空の一覧で始まります。検索可能なカテゴリメニューから、背景、アルバム画像、ロゴ、曲情報、ユーザーテキスト、ビジュアライザー、フェード、ビート効果、CRT、表示時間を追加できます。カードごとの折りたたみ、移動、セクション初期化、削除に対応します。
- **グローバルオーディオ** — 音楽マスター、トラック音量正規化、環境音ミキサー、環境音マスター、True Peak、リアルタイム L/R メーターを独立した領域で調整できます。
- **トラック別ラウドネス解析** — BS.1770 の Integrated LUFS、True Peak、LRA を解析し、増幅量とピークを制限しながら曲ごとの体感音量をそろえられます。
- **環境音ミキサー** — 複数の環境音に個別の音量、フェード、ループを設定できます。完成動画を繰り返しても最後まで連続して合成されます。
- **2曲トランジションプレビュー** — 曲の境界前後を素早く確認できます。プレビューと最終出力は同じ解像度、FPS、レンダー状態を共有します。
- **完成動画の繰り返し計画** — 回数または目標時間を指定し、予想回数、最終時間、超過時間を事前に確認できます。最後の繰り返しを無断で切りません。
- **プロジェクト形式 v4** — トリム、音量、フェード、グループ順、クリップ、エフェクト、グローバルオーディオ、繰り返し、レンダー設定、現在の段階を保存します。アトミック保存、メディアバックアップ、欠落ファイルの再リンク、旧形式の移行にも対応します。
- **11言語** — 既存9言語にドイツ語とロシア語を追加しました。表示言語を変更しても設定の意味が変わらない安定した内部 ID を使用します。
- **Windows 2段階起動** — 透明なネイティブアイコンをすぐに表示し、進行率と作業内容を表示するローディング画面を経てメイン画面へ移行します。

### 🎨 UI・UX 改善

- Stage 4 は左側に大きなプレビュー、右側にエフェクト一覧と設定を配置しました。
- デザイン・エフェクトと最終レンダーを Stage 4 / Stage 5 に分離しました。
- タイポグラフィ、情報階層、余白、パネル、フォーカス、選択、hover、無効状態を統一しました。
- ライトモードの暗いナビゲーション背景と Stage 5 の灰色外枠を修正しました。
- 最小サイズ、最大化、長い一覧、空の状態でもパネルとスクロールが重ならないよう改善しました。
- 解析、プロジェクト読み込み、プレビュー、レンダーに実際の進行状況とキャンセル操作を表示します。
- 検索型フォント選択と Alt+クリックによるスライダー初期値復元を追加しました。

### 🎶 ビジュアライザー・プレビュー改善

- EQバー、ミニマル波形、スペクトラム、サークル、ラジアルの5種類を提供します。
- 個数、高さ、間隔、感度、スムージング、減衰、透明度、角丸、グロウ、線幅、ミラー、反転、グラデーション、色、位置を調整できます。
- トリム開始位置と曲ごとの解析データに正しく同期し、2曲の切り替えでも波形・FFT状態を分離します。
- 同名ファイルのキャッシュ衝突と旧プロジェクトの不完全な解析キャッシュを修正しました。
- 画像・動画サムネイルとサイズ変更可能なクリッププレビューの分割比率を保存します。

### 🐛 修正

- FFmpeg `asplit` の未接続出力によるプレビュー準備失敗
- ドラッグ終了後もトリムハンドルがカーソルを追い続ける問題
- 空のグループやグループなしの状態で最初の移動が失敗する問題
- 言語変更後にコーデック、ビジュアライザー、繰り返し設定の意味が変わる問題
- パッケージ内でプレビューとレンダーが別の FFmpeg を参照する問題
- メタデータ自動保存が解析キャッシュを上書きする問題
- 終了後にプレビュー・レンダーの子プロセスが残る問題
- ライトモードのボタン視認性、上部ナビゲーション、Stage 5 の灰色枠
- 環境音が完成動画の繰り返し全体まで続かない問題

### ⚠️ リリース後に確認された主な問題

以下は v1.3.0 の公開後、一部の作業フローで報告された問題です。現在、正確な再現範囲を確認しており、通常のプロジェクト進行を妨げる項目から v1.3.1 で優先的に修正します。

- ダークモードとライトモードを切り替えた後、一部の操作項目やパネルが表示されなくなる場合があります。
- 新規プロジェクトでプロジェクト名を確定できない、または保存が完了しない場合があります。
- 上部の「次へ」が反応せず、次の作業ステージへ進めない場合があります。
- 音源解析中に進行状況ウィンドウが先に閉じ、解析だけがバックグラウンドで続くため、進行状況やキャンセル状態を確認できない場合があります。

### 📦 ダウンロードとインストール

- **Windows**: `AutoPlaylistMaker_v1.3.0_windows_x64.zip` を展開し、FFmpeg がない場合は `setup.bat` を実行してから `AutoPlaylistMaker_v1.3.0.exe` を起動してください。
- **macOS**: `AutoPlaylistMaker_v1.3.0_macos.zip` を展開し、FFmpeg がない場合は `bash setup_mac.sh` を実行して `.app` を開いてください。未署名アプリの警告が出る場合は Finder で右クリックして **開く** を選択します。

### ✅ 検証と注意

- 自動テスト 63件成功
- 11言語の key・placeholder 検査: 0 errors / 0 warnings
- Windows / macOS の GitHub Actions ビルド成功
- 最小・標準・大型画面、ライト・ダーク、長い一覧と空状態を確認
- 大きなオーディオ・科学計算ライブラリを最初に読み込む際は、環境によって起動に時間がかかる場合があります。
