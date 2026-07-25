$ErrorActionPreference = "Stop"

$version = "1.2.0"
$appName = "AutoPlaylistMaker_v$version"
$distRoot = Join-Path $PSScriptRoot "dist"
$bundleDir = Join-Path $distRoot $appName
$output = Join-Path $bundleDir "$appName.exe"
$zipOutput = Join-Path $distRoot "${appName}_windows_x64.zip"

$pythonDlls = Join-Path (python -c "import sys; print(sys.prefix)") "DLLs"
$tclDll = Join-Path $pythonDlls "tcl86t.dll"
$tkDll = Join-Path $pythonDlls "tk86t.dll"

$arguments = @(
    "--noconfirm",
    "--clean",
    "--onedir",
    "--windowed",
    "--name", $appName,
    "--icon", "app_icon.ico",
    "--splash", "brand_splash.png",
    "--add-data", "app_icon.ico;.",
    "--add-data", "app_icon.png;.",
    "--add-data", "visual_config.json;.",
    "--add-binary", "$tclDll;.",
    "--add-binary", "$tkDll;.",
    "--collect-all", "imageio_ffmpeg",
    "--collect-all", "tkinterdnd2",
    "--copy-metadata", "imageio",
    "--copy-metadata", "imageio-ffmpeg",
    "--copy-metadata", "moviepy",
    "--copy-metadata", "librosa",
    "--copy-metadata", "soundfile",
    "--exclude-module", "torch",
    "--exclude-module", "torchvision",
    "--exclude-module", "torchaudio",
    "--exclude-module", "tensorflow",
    "--exclude-module", "sklearn",
    "--exclude-module", "pandas",
    "--exclude-module", "matplotlib",
    "--exclude-module", "IPython",
    "--exclude-module", "notebook",
    "--hidden-import", "analyzer",
    "--hidden-import", "transition",
    "--hidden-import", "video_gen",
    "--hidden-import", "project",
    "--hidden-import", "distributor",
    "--hidden-import", "audio_preview",
    "--hidden-import", "audio_pipeline",
    "--hidden-import", "render_jobs",
    "--hidden-import", "ui_state",
    "--hidden-import", "repeat_settings",
    "--hidden-import", "font_combo",
    "app.py"
)

python -m PyInstaller @arguments
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller onedir build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $output)) {
    throw "Build completed without output: $output"
}

if (Test-Path -LiteralPath $zipOutput) {
    Remove-Item -LiteralPath $zipOutput -Force
}
Compress-Archive -LiteralPath $bundleDir -DestinationPath $zipOutput `
    -CompressionLevel Optimal

$bundleSize = (
    Get-ChildItem -LiteralPath $bundleDir -File -Recurse |
    Measure-Object -Property Length -Sum
).Sum
$fileCount = (
    Get-ChildItem -LiteralPath $bundleDir -File -Recurse |
    Measure-Object
).Count
$zipItem = Get-Item -LiteralPath $zipOutput

Write-Host ("Built Auto Playlist Maker v{0} onedir" -f $version)
Write-Host ("Executable: {0}" -f $output)
Write-Host ("Bundle: {0} files, {1:N1} MB" -f $fileCount, ($bundleSize / 1MB))
Write-Host ("ZIP: {0} ({1:N1} MB)" -f $zipOutput, ($zipItem.Length / 1MB))
