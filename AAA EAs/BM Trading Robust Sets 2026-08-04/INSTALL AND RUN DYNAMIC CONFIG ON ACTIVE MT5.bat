@echo off
setlocal
title Calyx - Dynamic 31-EA Portfolio Configuration
echo Configuring the current 31-EA portfolio. DMC Current XAU is retained; approved removals are excluded.
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
