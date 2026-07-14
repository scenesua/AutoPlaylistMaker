#!/bin/bash
# Auto Playlist Maker - macOS 빌드 스크립트
set -e

echo ""
echo "  Auto Playlist Maker - macOS 빌드"
echo "  ================================="
echo ""

# 사전 확인
echo "  [확인] 사전 요구사항 체크..."
echo ""

# Python
if ! command -v python3 &>/dev/null; then
    echo "  ✗ Python3가 설치되어 있지 않습니다."
    echo "    brew install python3 또는 https://python.org"
    exit 1
fi
echo "  ✓ Python3: $(python3 --version)"

# pip packages
echo ""
echo "  [1/4] 의존성 설치 중..."
pip3 install --quiet pyinstaller moviepy imageio imageio-ffmpeg numpy scipy librosa soundfile pydub pillow tkinterdnd2 2>/dev/null || true
echo "  ✓ 의존성 설치 완료"

# ffmpeg 확인
echo ""
echo "  [2/4] ffmpeg 확인 중..."
if ! command -v ffmpeg &>/dev/null; then
    echo "  ✗ ffmpeg가 설치되어 있지 않습니다."
    echo "    ./setup.sh 를 먼저 실행해주세요."
    exit 1
fi
echo "  ✓ ffmpeg: $(ffmpeg -version 2>&1 | head -1)"

# 빌드
echo ""
echo "  [3/4] PyInstaller 빌드 중..."
echo "  (처음 빌드 시 시간이 오래 걸릴 수 있습니다)"
echo ""

pyinstaller \
    --name AutoPlaylistMaker \
    --onefile \
    --windowed \
    --collect-all moviepy \
    --collect-all imageio_ffmpeg \
    --collect-all imageio \
    --hidden-import tkinterdnd2 \
    --add-data "visual_config.json:." \
    app.py \
    --noconfirm

# 완료
echo ""
echo "  [4/4] 빌드 완료!"
echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║  ✓ 빌드 성공!                                ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""
echo "  실행 파일: dist/AutoPlaylistMaker"
echo ""
echo "  배포 시 함께 제공:"
echo "    - AutoPlaylistMaker 실행 파일"
echo "    - setup.sh (ffmpeg 자동 설치)"
echo ""
echo "  ※ macOS에서 실행 파일에 실행 권한이 필요할 수 있습니다:"
echo "    chmod +x dist/AutoPlaylistMaker"
echo ""

# setup.sh 복사
cp setup.sh dist/setup.sh 2>/dev/null || true
chmod +x dist/setup.sh 2>/dev/null || true
