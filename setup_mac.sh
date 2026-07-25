#!/bin/bash
# Auto Playlist Maker - ffmpeg 자동 설치 (macOS)
set -e

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║  Auto Playlist Maker - ffmpeg 자동 설치     ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# Step 1: 확인
echo "  [1/3] ffmpeg 설치 확인 중..."
echo ""

if command -v ffmpeg &>/dev/null; then
    echo "  ╔══════════════════════════════════════════════╗"
    echo "  ║  ✓ ffmpeg가 이미 설치되어 있습니다!          ║"
    echo "  ╚══════════════════════════════════════════════╝"
    echo ""
    ffmpeg -version 2>&1 | head -1
    echo ""
    echo "  Auto Playlist Maker를 바로 실행할 수 있습니다."
    echo ""
    exit 0
fi

echo "  ffmpeg가 설치되어 있지 않습니다."
echo "  Auto Playlist Maker는 오디오/비디오 처리에 ffmpeg가 필요합니다."
echo ""

# Step 2: Homebrew 확인 / 설치
echo "  [2/3] ffmpeg 다운로드 중..."
echo ""

if command -v brew &>/dev/null; then
    echo "  Homebrew를 사용하여 ffmpeg를 설치합니다..."
    echo ""
    brew install ffmpeg
else
    echo "  Homebrew가 없습니다. 먼저 Homebrew를 설치합니다..."
    echo ""
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo ""

    # Apple Silicon 경로 추가
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif -f /usr/local/bin/brew; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi

    echo "  ffmpeg를 설치합니다..."
    echo ""
    brew install ffmpeg
fi

# Step 3: 확인
echo ""
echo "  [3/3] 설치 확인 중..."
echo ""

if command -v ffmpeg &>/dev/null; then
    echo "  ╔══════════════════════════════════════════════╗"
    echo "  ║  ✓ ffmpeg 설치 완료!                         ║"
    echo "  ╚══════════════════════════════════════════════╝"
    echo ""
    ffmpeg -version 2>&1 | head -1
    echo ""
else
    echo "  ╔══════════════════════════════════════════════╗"
    echo "  ║  ✗ 설치에 실패했습니다.                      ║"
    echo "  ╚══════════════════════════════════════════════╝"
    echo ""
    echo "  수동으로 설치해주세요:"
    echo "    brew install ffmpeg"
    echo "    또는 https://ffmpeg.org/download.html"
    echo ""
fi

echo "  ────────────────────────────────────────────────"
echo "  설정이 완료되면 Auto Playlist Maker를 실행하세요."
echo ""
