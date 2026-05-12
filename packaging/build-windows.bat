@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
set "ROOT=%cd%\.."
set "DIST=%ROOT%\packaging\dist"
set "BUILD=%ROOT%\packaging\build"
set "APP_NAME=Log Viewer"

:: Parse args
set "CLEAN=0"
:parse_args
if "%~1"=="" goto :done_args
if /i "%~1"=="--clean" (
    set "CLEAN=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--help" (
    echo Usage: build-windows.bat [--clean]
    exit /b 0
)
echo Unknown arg: %~1
exit /b 1
:done_args

:: Clean
if "%CLEAN%"=="1" (
    if exist "%DIST%" rmdir /s /q "%DIST%"
    if exist "%BUILD%" rmdir /s /q "%BUILD%"
    echo Cleaned build artifacts
)

:: Build .exe
echo Building Windows .exe...
uv run --with pyinstaller python -m PyInstaller ^
    --noconfirm ^
    --distpath "%DIST%" ^
    --workpath "%BUILD%" ^
    "%ROOT%\packaging\log-viewer-windows.spec"

echo.
echo EXE: "%DIST%\%APP_NAME%.exe"
echo Done.
