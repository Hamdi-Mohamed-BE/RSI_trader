@echo off
setlocal
title Calyx - Dynamic 32-EA Portfolio Configuration
echo Configuring the current 32-EA portfolio. Gold News V9 and DMC Current XAU are retained; approved removals are excluded.
echo Entry lots round UP to the broker step; below-minimum requests use minimum lot and are never skipped for sizing.
echo.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Start-Dynamic-Portfolio.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo The dynamic installer stopped without starting the portfolio.
)
echo.
pause
exit /b %EXIT_CODE%
