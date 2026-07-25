
---

# 🎵 Auto Playlist Maker v1.2.0

## 🇰🇷 한국어

### ✨ 새로 추가된 기능
- **스트리밍 오디오 파이프라인** — FFmpeg 기반 스트리밍 오디오 처리, 전체 오디오를 RAM에 로드하지 않고 실시간 믹싱
- **라우드니스 정규화** — LUFS 기반 음량 정규화 (통합/단기/순간), 배포용 출력 지원
- **오디오 미리듣기** — 타임라인 편집기에서 비블로킹 실시간 미리듣기 (재생/정지/스크러빙)
- **검색 가능한 폰트 선택기** — 검색 입력과 라이브 미리보기로 시스템 폰트 필터링
- **반복 설정** — 횟수 기반 또는 목표 시간 기반 반복 재생 계획
- **렌더 작업 큐** — 취소 가능한 렌더 큐 + 작업 완료 추적
- **UI 상태 관리** — 페이지 간 상태 저장/복원

### 🔧 개선된 기능
- **트림 편집 모달** — MM:SS:ms 정밀 시간 입력 모달 창으로 변경
- **클립 목록 자동 분배** — 가져온 이미지/영상이 그룹별 클립 목록에 자동 포함
- **프로젝트 저장 강화** — 클립 목록, 클립 설정, 배경 이미지, 총 길이 전체 저장/복원
- **텍스트 폰트 선택** — 일반/커스텀 텍스트 폰트를 Listbox + 스크롤바로 선택
- **수동 분배 순서 표시** — 드래그 시 삽입 위치 하이라이트 + 라벨

### 🎶 기존 기능
- **음악 분석** — BPM, 키, 캠롯 심벌, 코드 자동 감지
- **스마트 트랙 분배** — 목표 시간에 맞춰 곡을 여러 영상으로 자동 분할
- **수동 분배** — 드래그로 곡을 그룹에 배치하고 순서 변경
- **크로스fade 엔진** — 곡 간 부드러운 전환 (WAV 출력)
- **영상 생성** — 5가지 비주얼라이저 모드 (EQ 바, 파형, 스펙트럼, 서클, 래디얼)
- **GPU 인코딩** — NVENC (NVIDIA), VideoToolbox (Mac), VAAPI (Intel)
- **tkinter GUI** — 다크/라이트 테마 토글
- **비트 이펙트** — 바운스, 쉐이크, 줌, 플래시 + CRT 효과
- **커스텀 텍스트** — 폰트, 크기, 색상, 위치 자유 설정
- **미리보기** — 실시간 스크러버 미리보기 + 렌더링 재생

---

## 🇺🇸 English

### ✨ New Features
- **Streaming Audio Pipeline** — FFmpeg-based streaming audio processing, real-time mixing without loading full audio into RAM
- **Loudness Normalization** — LUFS-based loudness normalization (integrated/short-term/momentary), broadcast-ready output
- **Audio Preview** — Non-blocking real-time audio preview in the timeline editor (play/stop/scrubbing)
- **Searchable Font Selector** — System font filtering via search input and live preview
- **Repeat Settings** — Count-based or target time-based repeat scheduling
- **Render Job Queue** — Cancelable render queue with completion tracking
- **UI State Management** — Page state save/restore

### 🔧 Improvements
- **Trim Edit Modal** — Changed to modal dialog with MM:SS:ms precise time input
- **Auto-distribute Clips** — Imported images/videos automatically included in per-group clip lists
- **Project Save Enhanced** — Full save/restore of clip lists, clip settings, background images, total duration
- **Font Selection** — Normal/custom text font selection via Listbox + scrollbar
- **Manual Distribute Order Display** — Insert position highlight + labels during drag

---

## 🇯🇵 日本語

### ✨ 新機能
- **ストリーミングオーディオパイプライン** — FFmpegベースのストリーミング処理、RAMに全オーディオを読み込まずにリアルタイムミキシング
- **ラウドネス正規化** — LUFSベースのラウドネス正規化（統合/短期/瞬間）、配信用出力対応
- **オーディオプレビュー** — タイムラインエディタでのノンブロッキングリアルタイムプレビュー（再生/停止/スクラブ）
- **検索可能なフォントセレクター** — 検索入力とライブプレビューでシステムフォントをフィルタリング
- **リピート設定** — 回数ベースまたは目標時間ベースのリピート再生計画
- **レンダリングジョブキュー** — キャンセル可能なレンダリングキュー + 完了追跡
- **UI状態管理** — ページ状態の保存/復元

### 🔧 改善点
- **トリム編集モーダル** — MM:SS:ms 精密時間入力モーダルダイアログに変更
- **クリップ自動分配** — インポートした画像/動画がグループ別クリップリストに自動追加
- **プロジェクト保存強化** — クリップリスト、クリップ設定、背景画像、総再生時間を完全保存/復元
- **フォント選択** — 通常/カスタムテキストフォントをListbox + スクロールバーで選択
- **手動分配順序表示** — ドラッグ時に挿入位置のハイライト + ラベル表示

---
