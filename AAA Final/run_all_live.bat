@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  AAA FINAL - START ALL LIVE WORKERS
echo ============================================================
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_all_live.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo STARTUP FAILED. No additional workers should be started until the error is fixed.
) else (
    echo STARTUP CHECK COMPLETED.
)
echo.
pause
exit /b %EXIT_CODE%
