#!/bin/bash
set -e

cd "$(dirname "$0")"

version="1.3.1"
appName="AutoPlaylistMaker_v$version"
distRoot="./dist"
bundleDir="$distRoot/$appName.app"
output="$bundleDir/Contents/MacOS/$appName"
zipOutput="$distRoot/${appName}_macos.zip"

arguments=(
    "--noconfirm"
    "--clean"
    "--onedir"
    "--windowed"
    "--name" "$appName"
    "--icon" "app_icon.png"
    "--add-data" "app_icon.png:."
    "--add-data" "app_splash.png:."
    "--add-data" "visual_config.json:."
    "--add-data" "locales:locales"
    "--add-data" "sound_effect_library/library:sound_effect_library/library"
    "--add-data" "sound_effect_library/processed:sound_effect_library/processed"
    "--add-data" "sound_effect_library/manifests/sound_library.json:sound_effect_library/manifests"
    "--add-data" "sound_effect_library/manifests/category_presets.json:sound_effect_library/manifests"
    "--add-data" "sound_effect_library/manifests/processed_loops.json:sound_effect_library/manifests"
    "--add-data" "sound_effect_library/licenses:sound_effect_library/licenses"
    "--collect-all" "imageio_ffmpeg"
    "--collect-all" "tkinterdnd2"
    "--copy-metadata" "imageio"
    "--copy-metadata" "imageio-ffmpeg"
    "--copy-metadata" "moviepy"
    "--copy-metadata" "librosa"
    "--copy-metadata" "soundfile"
    "--exclude-module" "torch"
    "--exclude-module" "torchvision"
    "--exclude-module" "torchaudio"
    "--exclude-module" "tensorflow"
    "--exclude-module" "sklearn"
    "--exclude-module" "pandas"
    "--exclude-module" "matplotlib"
    "--exclude-module" "IPython"
    "--exclude-module" "notebook"
    "--exclude-module" "numba.np.ufunc.tbbpool"
    "--exclude-module" "numba.np.ufunc.omppool"
    "--hidden-import" "analyzer"
    "--hidden-import" "transition"
    "--hidden-import" "video_gen"
    "--hidden-import" "ffmpeg_service"
    "--hidden-import" "project"
    "--hidden-import" "distributor"
    "--hidden-import" "audio_preview"
    "--hidden-import" "audio_pipeline"
    "--hidden-import" "ambient_library"
    "--hidden-import" "ambient_engine"
    "--hidden-import" "render_jobs"
    "--hidden-import" "ui_state"
    "--hidden-import" "repeat_settings"
    "--hidden-import" "font_combo"
    "--hidden-import" "i18n"
    "--hidden-import" "stage4_design_effects"
    "--hidden-import" "stage5_render"
    "--hidden-import" "timeline_utils"
    "app.py"
)

python3 -m PyInstaller "${arguments[@]}"

if [ $? -ne 0 ]; then
    echo "PyInstaller build failed"
    exit 1
fi

if [ ! -d "$bundleDir" ]; then
    echo "Build completed without .app bundle: $bundleDir"
    exit 1
fi

# Copy tcl/tk data if missing
internalDir="$bundleDir/Contents/Resources"
tclLib=$(python3 -c "import tkinter; import os; print(os.path.dirname(os.__file__))")
tclData="$tclLib/tcl8.6"
tkData="$tclLib/tk8.6"
if [ -d "$tclData" ] && [ ! -d "$internalDir/_tcl_data" ]; then
    cp -R "$tclData" "$internalDir/_tcl_data"
    echo "Copied tcl data"
fi
if [ -d "$tkData" ] && [ ! -d "$internalDir/_tk_data" ]; then
    cp -R "$tkData" "$internalDir/_tk_data"
    echo "Copied tk data"
fi

# Zip the .app bundle
if [ -f "$zipOutput" ]; then
    rm "$zipOutput"
fi
ditto -c -k --sequesterRsrc --keepParent "$bundleDir" "$zipOutput"

bundleSize=$(du -sm "$bundleDir" | cut -f1)
fileCount=$(find "$bundleDir" -type f | wc -l)
zipSize=$(du -sm "$zipOutput" | cut -f1)

echo "Built Auto Playlist Maker v${version} .app"
echo "Bundle: ${bundleDir} (${bundleSize} MB, ${fileCount} files)"
echo "ZIP: ${zipOutput} (${zipSize} MB)"
