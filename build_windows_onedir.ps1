$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = "1.3.0"
$appName = "AutoPlaylistMaker_v$version"
$distRoot = Join-Path $PSScriptRoot "dist"
$bundleDir = Join-Path $distRoot $appName
$output = Join-Path $bundleDir "$appName.exe"
$coreOutput = Join-Path $bundleDir "$appName.core.exe"
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
    "--add-data", "app_icon.ico;.",
    "--add-data", "app_icon.png;.",
    "--add-data", "app_splash.png;.",
    "--add-data", "visual_config.json;.",
    "--add-data", "locales;locales",
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
    "--hidden-import", "ffmpeg_service",
    "--hidden-import", "project",
    "--hidden-import", "distributor",
    "--hidden-import", "audio_preview",
    "--hidden-import", "audio_pipeline",
    "--hidden-import", "render_jobs",
    "--hidden-import", "ui_state",
    "--hidden-import", "repeat_settings",
    "--hidden-import", "font_combo",
    "--hidden-import", "i18n",
    "--hidden-import", "stage4_design_effects",
    "--hidden-import", "stage5_render",
    "--hidden-import", "timeline_utils",
    "--hidden-import", "psutil",
    "app.py"
)

python -m PyInstaller @arguments
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller onedir build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $output)) {
    throw "Build completed without output: $output"
}
Move-Item -LiteralPath $output -Destination $coreOutput -Force
Copy-Item -LiteralPath "app_splash.png" -Destination $bundleDir -Force

$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path -LiteralPath $csc)) {
    throw "Windows C# compiler not found: $csc"
}
& $csc /nologo /target:winexe /optimize+ /win32icon:app_icon.ico `
    /reference:System.Windows.Forms.dll /reference:System.Drawing.dll `
    "/out:$output" native_launcher.cs
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $output)) {
    throw "Native launcher build failed with exit code $LASTEXITCODE"
}

$internalDir = Join-Path $bundleDir "_internal"
foreach ($dll in @($tclDll, $tkDll)) {
    $destInternal = Join-Path $internalDir (Split-Path $dll -Leaf)
    $destRoot = Join-Path $bundleDir (Split-Path $dll -Leaf)
    Copy-Item -LiteralPath $dll -Destination $destInternal -Force
    Copy-Item -LiteralPath $dll -Destination $destRoot -Force
    Write-Host ("Copied {0} to _internal and root" -f (Split-Path $dll -Leaf))
}

$tclRoot = Join-Path (python -c "import sys; print(sys.prefix)") "tcl"
$tclDataSrc = Join-Path $tclRoot "tcl8.6"
$tkDataSrc = Join-Path $tclRoot "tk8.6"
$tclDataDst = Join-Path $internalDir "_tcl_data"
$tkDataDst = Join-Path $internalDir "_tk_data"
if (Test-Path -LiteralPath $tclDataSrc) {
    if (-not (Test-Path -LiteralPath $tclDataDst)) {
        Copy-Item -LiteralPath $tclDataSrc -Destination $tclDataDst -Recurse -Force
        Write-Host "Copied tcl8.6 -> _tcl_data"
    } else { Write-Host "_tcl_data already exists" }
} else { Write-Host "WARNING: tcl8.6 not found at $tclDataSrc" }
if (Test-Path -LiteralPath $tkDataSrc) {
    if (-not (Test-Path -LiteralPath $tkDataDst)) {
        Copy-Item -LiteralPath $tkDataSrc -Destination $tkDataDst -Recurse -Force
        Write-Host "Copied tk8.6 -> _tk_data"
    } else { Write-Host "_tk_data already exists" }
} else { Write-Host "WARNING: tk8.6 not found at $tkDataSrc" }

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
