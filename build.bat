@echo off
REM Music Mixer - PyInstaller 빌드 스크립트
REM 이번 세션에서 확인된 문제 반영:
REM   - "'NoneType' object has no attribute 'write'" 렌더링 오류
REM     -> --collect-data 로는 ffmpeg 바이너리가 번들에 안 들어감
REM        --collect-all imageio_ffmpeg 로 바이너리 포함
REM   - moviepy 관련 ModuleNotFoundError 예방을 위해 --collect-all moviepy 추가
REM   - tkinterdnd2 크래시 방지를 위한 hidden-import 유지
REM   - video_gen.py에서 _ensure_ffmpeg_for_moviepy()로 import 시점 캐싱 문제 해결

pyinstaller ^
    --name AutoPlaylistMaker ^
    --onefile ^
    --windowed ^
    --collect-all moviepy ^
    --collect-all imageio_ffmpeg ^
    --collect-all imageio ^
    --hidden-import tkinterdnd2 ^
    --add-data "visual_config.json;." ^
    app.py

echo.
echo 빌드 완료: dist\AutoPlaylistMaker.exe
echo.
echo [확인할 것]
echo  1) dist\AutoPlaylistMaker.exe --safe 로 tkinterdnd2 없이도 실행되는지
echo  2) 실제로 영상 렌더링까지 끝까지 되는지 (ffmpeg 번들 확인용)
echo  3) 실행 파일 더블클릭 후 화면이 뜨기까지 걸리는 시간
echo.
echo [실행 속도가 여전히 느리다면]
echo  --onefile 대신 --onedir 로 바꿔서 실행마다 압축 해제하는 과정을 없애보세요.
echo  (배포 시엔 dist\AutoPlaylistMaker 폴더 전체를 zip으로 압축해서 공유하면 됩니다)
echo.
echo  또는 네이티브 스플래시를 쓰려면 splash 이미지 파일을 준비한 뒤
echo  위 pyinstaller 명령에 --splash splash_image.png 를 추가하고,
echo  app.py의 main() 맨 위에 있는 pyi_splash.close() 호출을 그대로 두세요
echo  (이미 추가되어 있습니다).
pause
