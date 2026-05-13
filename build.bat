@echo off
setlocal

REM ----------------------------------------------------------------------
REM Build ShooApp.exe with the requireAdministrator manifest baked in.
REM Output goes to .\dist\ShooApp.exe and is also copied to the project
REM root so the Inno Setup script can pick it up.
REM ----------------------------------------------------------------------

cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python launcher 'py' not found. Install Python 3.10+ first.
    exit /b 1
)

echo.
echo === Installing build dependencies ===
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m pip install pyinstaller

echo.
echo === Cleaning previous build ===
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
if exist ShooApp.spec del ShooApp.spec

echo.
echo === Building ShooApp.exe ===
py -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --uac-admin ^
    --name ShooApp ^
    --icon=shooapp.ico ^
    --hidden-import=win32com ^
    --hidden-import=win32com.client ^
    --hidden-import=pywintypes ^
    shoo.py

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)

echo.
echo Build OK -^> dist\ShooApp.exe
endlocal
