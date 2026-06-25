@echo off
setlocal

if /I "%~1" NEQ "--visible" (
    start "ORB Bot" /normal cmd /k ""%~f0" --visible"
    exit /b
)

cd /d "%~dp0"
title ORB Bot

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    py -3 -m venv .venv 2>NUL
    if errorlevel 1 (
        python -m venv .venv
    )
)

echo Checking dependencies...
".venv\Scripts\python.exe" -c "import pandas, numpy, MetaTrader5" >NUL 2>NUL
if errorlevel 1 (
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo.
echo ORB bot is starting.
echo It uses a separate ORB magic number, state file, and live switches.
echo Live order sending requires ORB_LIVE_TRADING=true and ORB_PLACE_TRADES=true in .env.
echo Pending stop sending also requires ORB_PLACE_PENDING=true.
echo This window is the ORB process. Closing it stops the visible bot session.
echo Press Ctrl+C in this window to stop.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$lock = Join-Path (Get-Location) 'reports\orb_bot\orb.lock'; if (Test-Path -LiteralPath $lock) { $payload = Get-Content -LiteralPath $lock -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue; $lockPid = [int]($payload.pid); $cmd = if ($lockPid -gt 0) { (Get-CimInstance Win32_Process -Filter \"ProcessId = $lockPid\" -ErrorAction SilentlyContinue).CommandLine } else { $null }; if (-not $cmd -or ($cmd -notlike '*app.orb_bot*' -and $cmd -notlike '*orb_bot.py*')) { Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue; Write-Host 'Removed stale ORB lock.' } }"

".venv\Scripts\python.exe" -m app.orb_bot

pause
