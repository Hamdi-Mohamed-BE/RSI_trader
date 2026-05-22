@echo off
setlocal

cd /d "%~dp0"

echo.
echo ==========================================
echo  RSI Divergence MT5 Bot - Web Dashboard
echo ==========================================
echo.

if not exist "config.yaml" (
    echo ERROR: config.yaml was not found.
    echo Run install.bat first.
    pause
    exit /b 1
)

set "UV_EXE="
for /f "delims=" %%I in ('where uv 2^>nul') do if not defined UV_EXE set "UV_EXE=%%I"
if not defined UV_EXE if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"

if not defined UV_EXE (
    echo ERROR: uv was not found.
    echo Run install.bat first.
    pause
    exit /b 1
)

if not exist "runtime" (
    mkdir "runtime"
)

echo Starting dashboard with config.yaml...
echo Open this in the VPS browser:
echo http://127.0.0.1:8787
echo.
echo Keep this window open while the bot is running.
echo Press Ctrl+C to stop.
echo.

"%UV_EXE%" run rsi-bot web --config config.yaml

echo.
echo Dashboard stopped.
pause
