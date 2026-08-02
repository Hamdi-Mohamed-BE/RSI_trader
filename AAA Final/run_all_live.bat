@echo off
title AAA FINAL - LIVE BOT CONTROL
setlocal
cd /d "%~dp0"

if /i "%~1"=="stop" (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_all_bots.ps1"
    set "EXIT_CODE=%ERRORLEVEL%"
    echo.
    pause
    exit /b %EXIT_CODE%
)

echo ============================================================
echo  AAA FINAL - START ALL LIVE WORKERS
echo ============================================================
echo.

set "DISPLAY_OPTION="
if /i "%~1"=="hidden" set "DISPLAY_OPTION=-HiddenTerminals"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_all_live.ps1" %DISPLAY_OPTION%
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo STARTUP FAILED. No additional workers should be started until the error is fixed.
) else (
    echo STARTUP CHECK COMPLETED.
    echo Each bot has its own named terminal window.
    echo Use stop_all_bots.bat to stop every AAA Final worker safely.
)
echo.
pause
exit /b %EXIT_CODE%
