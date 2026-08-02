@echo off
title AAA FINAL - STOP ALL BOTS
setlocal
cd /d "%~dp0"

echo ============================================================
echo  AAA FINAL - STOP ALL BOT WORKERS
echo ============================================================
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_all_bots.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo STOP FAILED. Review the error shown above.
) else (
    echo STOP COMPLETED. MT5 and existing trades were not changed.
)
echo.
pause
exit /b %EXIT_CODE%
