# 🎵 Auto Playlist Maker v1.3.1

Windows와 macOS 패키지, FFmpeg 설치 스크립트가 포함되어 있습니다.

---

## 🇰🇷 한국어

1.3.1은 1.3.0 배포 후 확인된 작업 중단 문제와 미리보기·분석·효과 편집 문제를 우선 해결하고, **효과 랙과 환경음 작업 흐름을 실제 편집 프로그램처럼 안정화한 업데이트**입니다.

### ✨ 새롭게 추가된 기능

- **확장된 사용자 텍스트** — 투명도, 외곽선, 배경 상자, 표시 시작·종료 시간과 대상 곡을 설정할 수 있으며 전체 화면 클립 위에서도 유지됩니다.
- **렌더 작업별 오류 기록** — 각 렌더에 고유 작업 번호와 단계별 로그가 생성되며, 실패 창에서 로그·폴더 열기, 내용 복사와 재시도를 바로 실행할 수 있습니다.
- **실시간 효과 갱신 복구** — 가벼운 시각 설정은 180ms 이내에 현재 미리보기를 다시 구성하고, 해상도·대상 곡·오디오 구조 변경은 재생 위치를 보존해 안전하게 다시 준비합니다.

### 🎨 효과 랙 재배치

- **미리보기 중심 화면** — 미리보기는 왼쪽, 효과 랙은 오른쪽에 고정됩니다. 기본 가로 비율은 약 3:1이며 경계를 직접 드래그해 바꿀 수 있습니다.
- **크기를 바꿀 수 있는 효과 랙** — 효과 목록과 아래 기본 설정 사이의 경계도 위아래로 조절할 수 있습니다. 기본 상태에서는 효과 목록이 더 넓게 보입니다.
- **접을 수 있는 기본 설정** — 전역 오디오와 미리보기 해상도 설정을 필요할 때만 펼칠 수 있어 작은 화면에서도 효과 목록을 가리지 않습니다.
- **정리된 기본 슬롯** — 전역 오디오, 장면 전환, 기본 배경은 기본 슬롯으로 유지하고, 사용자가 추가한 효과는 별도 순서로 관리합니다.
- **안정적인 효과 설정 창** — 같은 효과의 설정 창이 여러 개 열리지 않으며, 닫았다 다시 열어도 설정과 활성 상태가 유지됩니다.

### 🌧️ 하나로 통합된 환경음 효과

- 환경음은 비·천둥·바람을 각각 효과로 추가하는 방식이 아니라, 효과 랙의 **환경음 슬롯 하나**로 관리합니다.
- 환경음 설정 안에서 비, 천둥, 바람, 파도, 시냇물, 모닥불, 숲, 새소리, 귀뚜라미, 카페, 도시, 기차, 선풍기, 환풍기 등의 종류를 독립적으로 켜고 음량을 조절할 수 있습니다.
- 실제 WAV·OGG 파일은 사용자에게 나열하지 않고, 내부에서 순환·무작위 시작·크로스페이드와 사건형 배치를 조합해 장시간 반복감을 줄입니다.
- 음악과 환경음은 서로 다른 오디오 버스로 처리됩니다. 곡 정규화, 곡별 페이드, 곡 사이 크로스페이드와 반복 경계가 환경음을 끊지 않습니다.
- 여러 종류를 동시에 사용해도 Windows 명령줄 길이 제한에 걸리지 않도록 작업을 작은 단위로 나누고 filter script·concat 목록·중간 환경음 버스를 사용합니다.

### 🎬 미리보기와 렌더 안정화

- **두 곡 미리보기가 기본값** — 현재 곡과 다음 곡의 경계를 중심으로 크로스페이드와 장면 전환을 확인할 수 있습니다.
- **독립적인 미리보기 품질** — 최종 출력 해상도를 바꾸지 않고 낮음·중간·높음·사용자 지정 미리보기 해상도를 선택할 수 있습니다.
- **실제 준비 상태 표시** — 오디오 믹스, 효과 준비, 첫 프레임과 재생 준비가 완료될 때까지 로딩 상태를 유지하고 실패 원인을 표시합니다.
- **더 빠른 첫 재생** — 이미 완성된 WAV 미리보기는 다시 FFmpeg로 변환하지 않고 바로 재생합니다.
- **확실한 렌더 완료 판정** — 인코더 프로세스가 끝난 것만으로 성공 처리하지 않고, FFprobe로 영상·오디오 스트림과 길이를 확인한 뒤 완료로 표시합니다.
- 반복 횟수와 목표 재생 시간은 최종 렌더 단계에서 관리하며, 기존 프로젝트의 반복 설정도 그대로 복원합니다.

### 📊 분석과 프로젝트 복구

- 분석 진행 창은 전체 작업이 실제로 끝나거나 사용자가 취소할 때까지 유지됩니다.
- 현재 파일, 전체 파일 수, 파형·음량 등 내부 분석 단계를 따로 보여줍니다.
- 파일 크기나 수정 시간이 바뀌면 오래된 분석 캐시를 자동으로 무효화합니다.
- 이전 저장 오류로 최상위 파일 목록과 분석 캐시가 비어 있어도, 영상 그룹에 남은 음원·이미지 경로에서 프로젝트를 복구하고 필요한 음원만 다시 분석합니다.
- 실제 `short test 2`  프로젝트의 음원 3개와 이미지 4개를 복구하고, 분석·두 곡 미리보기까지 완료했습니다.

### ⚡ 시작과 패키지 구조

- Windows는 하나의 사용자용 EXE만 제공합니다. 별도의 launcher/core EXE로 나뉘지 않습니다.
- Tk가 준비되기 전에는 같은 프로세스의 네이티브 시작 화면을 표시해 앱이 실행 중임을 더 일찍 확인할 수 있습니다.
- 분석기, 영상 렌더러, 디자인·렌더 단계와 무거운 라이브러리는 실제로 필요한 단계에 들어갈 때만 불러옵니다.
- FFprobe와 앱 아이콘, 내장 환경음 라이브러리를 onedir 패키지에 포함합니다.

### 🐛 수정된 주요 문제

- 다른 앱을 확인한 뒤 APM으로 돌아오면 프로젝트 로딩·음원 분석 진행 창이 메인 창 뒤로 사라지던 문제
- 새 프로젝트 이름과 기본 저장 경로가 잘못 처리되던 문제
- 상단 `다음` 버튼이 현재 작업 상태와 맞지 않게 비활성화되던 문제
- 분석 진행 창이 첫 파일 또는 작업 도중 사라지고 분석만 계속되던 문제
- worker thread가 Tk UI를 직접 갱신하던 문제
- 효과 래프와 미리보기 위치가 바뀌거나 설정 창이 중복으로 열리던 문제
- 슬라이더 트랙 클릭·노브 드래그·Alt+클릭 초기화가 일부 화면에서 동작하지 않던 문제
- 전역 오디오 아래 설정이 효과 목록 공간을 과도하게 잡아 먹던 문제
- 미리보기 로딩이 끝나지 않거나 완료 후에도 “연결 중”으로 남던 문제
- 이전의 미리보기 frame/audio callback이 새 상태를 덮어쓰던 문제
- 환경음 여러 종류를 사용할 때 `WinError 206`이 발생하던 문제
- 결과 파일이 비어 있거나 손상됐는데도 렌더가 완료로 표시되던 문제
- 패키지에서 FFprobe를 찾지 못해 완료 검증이 실패하던 문제
- 종료 후 타이머·미리보기·렌더 관련 작업이 남던 문제

### 📦 Windows 설치

1. `AutoPlaylistMaker_v1.3.1_windows_x64.zip`을 원하는 폴더에 압축 해제합니다.
2. 폴더 안의 `AutoPlaylistMaker_v1.3.1.exe`를 실행합니다.
3. 폴더 안의 `_internal`과 환경음 라이브러리 파일은 EXE와 함께 두세요.

### ✅ 검증

- 자동 테스트 **116개 통과**(환경 제한 21개 skip)
- 11개 locale key·placeholder 검사 **0 errors / 0 warnings**, Ruff F/B, py_compile, pip check 통과
- 네 해상도 preview/output 픽셀 비교 및 추가 해상도(3840×2160~1080×1080) 실제 MP4 비교 통과
- 환경음 10분 실제 렌더 600.000초, 120초 청크 경계 무음·peak·WinError 발생 없음
- `short test 2` 실프로젝트 복구 · 분석 3/3 · 두 곡 미리보기 준비 완료
- Windows 최종 onedir/ZIP 빌드 · 단일 EXE · 실행 → 정상 종료 후 잔여 프로세스 0
- 자세한 검증 이력은 `docs/versions/1.3.1/TEST_RESULTS.md` 참고

### ⚠️ 참고

- 첫 실행은 Windows의 파일 검사와 Tcl/Tk 초기화 때문에 PC 환경에 따라 시간이 걸릴 수 있습니다. 시작 화면이 표시된 뒤 메인 창 준비가 계속됩니다.
- macOS 앱과 지원 GPU별 하드웨어 인코더는 해당 환경에서 별도 검증이 필요합니다.
- `forest`, `singing bowl`은 이번 내장 라이브러리에 원본이 없어 10분 실제 검증에서 제외됩니다.

---

## 🇺🇸 English

Version 1.3.1 is a stability-focused release that addresses the workflow-blocking issues found in 1.3.0 and stabilizes the effect rack and ambience workflow.

### ✨ New Features

- **Expanded user text** — Set transparency, outline, background box, display start/end times and target track; text is preserved over fullscreen clips.
- **Per-job render error logs** — Each render gets a unique job ID with per-step logs; the non-modal error window offers open log, open folder, copy text, and retry.
- **Live effect refresh restored** — Light visual changes rebuild the current preview within 180ms; resolution/target-track/audio-structure changes are re-prepared safely while preserving playback position.

### 🎨 Effect Rack and Layout

- A fixed split keeps the preview on the left and the effect rack on the right (about 3:1 by default, draggable).
- The boundary between the rack and its settings is vertically adjustable; text/rack gets more room by default.
- Global audio and preview resolution settings are collapsible so they never hide the effect list on small windows.
- Global audio, scene transition, and default background stay fixed slots; added effects keep their own order.
- Effect settings windows are singletons — no duplicates, and settings/active state persist across close/open.

### 🌧️ Unified Ambience Effect

- Rain, thunder, wind, etc. are no longer separate effects; they live in a single ambience effect in the rack.
- Enable and adjust per-type volume for rain, thunder, wind, waves, stream, fire, forest, birds, crickets, cafe, city, train, fan, ventilator inside the ambience settings.
- Real WAV/OGG files are not listed; an internal engine combines rotation, randomized starts, crossfades, and event placement to reduce long-run repetition.
- Music and ambience ride independent audio buses, so normalization, per-track fades, crossfades, and repeat boundaries never cut ambience.
- Long mixes are chunked (120s) and batched (max 8 inputs) with filter scripts and concat lists to avoid `WinError 206`.

### 🎬 Preview and Render Stability

- Default preview covers two tracks and their boundary, so crossfades and transitions are easy to inspect.
- Preview quality is independent from the final output resolution (auto/low/medium/high/custom).
- Loading state persists and lists failure causes until audio mix, effect preparation, first frame and playback are ready.
- Completed WAV previews play immediately without reconverting.
- A render is marked complete only after FFprobe verifies the file size, video/audio streams, resolution and duration — not just because the encoder exited.
- Repeat count/target playback time are managed at the final render stage, and existing repeat settings are restored.

### 📊 Analysis and Project Recovery

- The analysis progress window stays until the whole job finishes or you cancel it; current file, total file count and internal stages are shown.
- Changed file size or mtime automatically invalidates stale analysis cache.
- If the top-level file list and cache are empty after a save error, the project is rebuilt from remaining group media paths and only missing sources are re-analyzed.
- The real `short test 2` project (3 audio, 4 images) was recovered, analyzed (3/3) and previewed across two tracks.

### ⚡ Startup and Packaging

- Windows ships a single user EXE with no separate launcher/core executables.
- A native splash from the same process shows the app is running before Tk is ready.
- Lazy loading keeps the analyzer, video renderer and design/render stages plus large libraries until they are actually needed.
- FFprobe, the app icon and the bundled ambience library are included in the onedir package.

### 🐛 Fixes

- Analysis/loading progress windows disappearing behind the main window after returning to APM
- New project name handling and default save path
- Top-level **Next** being disabled inconsistently with the current state
- The analysis progress window closing while analysis kept running in the background
- Workers calling Tk/UI directly
- Effect rack/preview layout being swapped or duplicate settings windows
- Slider track click, knob drag and Alt+click reset not working in some views
- Settings under global audio taking excessive space
- Preview errors remaining stuck on “connecting” after loading finished
- Stale preview frame/audio callbacks overwriting the new preview state
- `WinError 206` when many ambience kinds were used at once
- Empty/corrupt output files reported as completed renders
- FFprobe not found in the package, failing completion validation
- Cleanup missing for timers/preview/render after shutdown

### 📦 Windows Install

1. Extract `AutoPlaylistMaker_v1.3.1_windows_x64.zip` to the folder of your choice.
2. Run `AutoPlaylistMaker_v1.3.1.exe` inside it.
3. Keep the `_internal` folder and the ambience library files next to the EXE.

### ✅ Validation

- 116 automated tests passed (21 environment-limited cases skipped)
- 11-locale validation: 0 errors / 0 warnings; Ruff F/B, py_compile, pip check passed
- Multi-resolution preview/output pixel comparisons and visual MP4 checks (11 sizes) passed
- 10-minute real ambience render exact 600.000s with no silent/peak/over-run at 120s chunk boundaries
- `short test 2` recovery: 3/3 audio, second-track preview ready
- Final Windows onedir/ZIP build, single EXE, clean GUI start, 0 leftover processes after normal exit
- See `docs/versions/1.3.1/TEST_RESULTS.md` for the full history

### ⚠️ Notes

- The first launch can be slow depending on the PC due to SmartScreen/SmartScreen file checks and Tcl/Tk initialization; the splash then the main window continue loading.
- macOS app and GPU encoders (NVENC/QSV/AMF) still need validation on the target hardware.
- `forest` and `singing bowl` have no bundled source assets, so they were excluded from long-duration real playback tests.

---

## 🇯🇵 日本語

1.3.1 は 1.3.0 の公開後に確認された作業を止める問題やプレビュー・分析・エフェクト編集の問題を優先的に修正し、エフェクト ラックと環境音の作業フローを安定化したアップデートです。

### ✨ 新機能

- **テキスト効果の拡張** — 透明度・枠線・背景ボックス・表示開始/終了時間・対象曲を設定でき、フル画面クリップの上でも維持されます。
- **レンダー単位のエラーログ** — 各レンダーにユニークな、ジョブ ID とステップ別ログを生成。失敗ウィンドウでログ・フォルダを開く、コピー、再試行をすぐ実行できます。
- **ライブ更新の復旧** — 軽い視覚設定は 180ms 以内にプレビューを再構成し、解像度・対象曲・オーディオ構造の変更は再生位置を保って安全に再準備します。

### 🎨 エフェクトラック・レイアウト

- プレビューを左、エフェクトラックを右に固定（既定で約 3:1、境界はドラッグで調整）。
- ラックと下部設定の境界も縦に調整可能。既定ではラックが広く表示されます。
- グローバルオーディオとプレビュー解像度設定は折りたたみ式で、小画面でもリストを隠しません。
- グローバルオーディオ・シーン選択・既定背景は固定スロットとして、ユーザーが追加したエフェクトは別の順序で管理します。
- 同じエフェクトの設定ウィンドウは重複しません。閉じても設定と有効状態は保持されます。

### 🌧️ アンビエンス効果（1つに統合）

- 雨・雷・風などを別々のエフェクトにするのではなく、ラックの**アンビエンススロット 1 つ**で管理します。
- 雨・雷・風・波・小川・焚き火・森・風・鳥・コオロギ・カフェ・都市・電車・扇風機などを個別にオン/音量調整できます。
- 実際の WAV/OGG は表示せず、内部でループ・ランダム開始・クロスフェードを組み合わせて高画 … 長い再生の飽きを減らします。
- 音楽と環境音は独立したオーディオ バス。ノーマライズ・曲フェード・クロスフェード・反復境界が環境音を切らない。
- 長いコマンドは 120 秒チャンク・8 入力バッチに分割し、filter script と concat リストで `WinError 206` を防止します。

### 🎬 プレビュー・レンダーの安定化

- 既定は 2 つの再生（現在+次）の境界でクロスフェードとシーン選択を確認できます。
- 最終出力解像度と独立した準備品質（auto/low/medium/high/custom）。
- オーディオ・エフェクト・初回フレーム・再生準備が終わるまでローディングを維持し、失敗原因を表示。
- 完成済み WAV は再変換せず即時再生。
- エンコード処理が終わったからだけでなく FFprobe で映像・音声ストリームと長さを確認してから完了と判定。
- 反復回数と再生時間の設定は最終レンダーで管理し、既存設定も復元。

### 📊 分析とプロジェクト復旧

- 分析ウィンドウは全作業が終わる、またはキャンセルされるまで維持し、現在ファイル・総数・内部分析段階を表示。
- ファイルサイズや更新時刻が変わると古い分析キャッシュを自動的に無効化。
- 保存エラーでファイル一覧/キャッシュが空でも、残っているグループから再構築し必要な音源だけ再分析。
- 実際の `short test 2` 提案（音声 3・画像 4）を復旧し、分析 3/3・第 2 プレビューまで完了。

### ⚡ 起動・パッケージ

- Windows は単一のユーザー EXE。launcher/core で別れません（ビルド 2 重化も解消）。
- Tk が準備される前から同一プロセスでネイティブ スプラッシュを表示。
- 分析器・映像レンダラー・デザイン/レンダー段階と重いライブラリは必要な時だけロード。
- FFprobe とアプリアイコン、環境音済みライブラリを onedir に同梱。

### 🐛 主な修正

- 他アプリから戻るとプロジェクト読み込み・分析ウィンドウが消える問題
- 新規プロジェクト名と既定保存先の誤処理
- 上部「次へ」が現在の状態と合わず無効になる問題
- 分析ウィンドウが途中で閉じるのに分析が続く問題
- worker が Tk/UI を直接更新する問題
- ラックとプレビューの位置入れ替え・ウィンドウ二重表示
- 一部のスライダーでトラッククリック・ドラッグ・Alt+クリック初期化が動かない問題
- グローバルオーディオ下の設定がリストを圧迫する問題
- プレビュー読み込みが終わらない、終了後も「接続中」問題
- 古い frame/audio コールバックが新状態を上書きする問題
- 複数系統の環境音時の `WinError 206`
- 空/壊れた出力が完了と 記録される問題
- パッケージ内で FFprobe が見つからず完了検証が失敗する問題
- 終了後のタイマー・プレビュー・レンダーの残存

### 📦 Windows インストール

1. `AutoPlaylistMaker_v1.3.1_windows_x64.zip` を任意のフォルダに展開します。
2. フォルダ内の `AutoPlaylistMaker_v1.3.1.exe` を実行します。
3. `_internal` フォルダと環境音ライブラリは EXE と一緒に置いてください。

### ✅ 検証

- 自動テスト 116 件成功（環境制限 21 件スキップ）
- 11 言語 key/placeholder 一致：0 errors / 0 warnings、Ruff F/B・py_compile・pip check 通過
- プレビュー・出力のピクセル比較と 11 サイズの実 MP4 比較通過
- 環境音 10 分実レンダー 600.000 秒で 120s チャンク境界にも無音・ピーク違反なし
- `short test 2` 復旧：音声 3/3・第 2 プレビュー
- Windows onedir/ZIP 単一 EXE、必要な GUI 起動、終了後の残存プロセス 0

### ⚠️ 注意

- 初回起動はファイルとしての検証と Tcl/Tk 初期化 のためマシンにより時間がかかります。スプラッシュ表示後にメインウィンドウが続きます。
- macOS アプリと GPU エンコーダ（NVENC/QSV/AMF）は実機での検証が必要です。
- 組み込み元音源を持たない `forest` / `singing bowl` は、今回の長期実再生検証から除外しています。