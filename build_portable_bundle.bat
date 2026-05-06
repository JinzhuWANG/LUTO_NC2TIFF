@echo off
setlocal

cd /d "%~dp0"

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --clean --noconfirm LUTO_NC2TIFF_GUI.spec

if exist "dist\LUTO_NC2TIFF_GUI.zip" del "dist\LUTO_NC2TIFF_GUI.zip"
powershell -NoProfile -Command "Compress-Archive -Path '.\dist\LUTO_NC2TIFF_GUI\*' -DestinationPath '.\dist\LUTO_NC2TIFF_GUI.zip' -Force"

echo.
echo Portable bundle created:
echo   dist\LUTO_NC2TIFF_GUI\
echo Zip created:
echo   dist\LUTO_NC2TIFF_GUI.zip
