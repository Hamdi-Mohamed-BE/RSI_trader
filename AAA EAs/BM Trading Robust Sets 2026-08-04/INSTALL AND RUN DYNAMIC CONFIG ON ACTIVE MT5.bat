@echo off
setlocal
title BM Trading - Dynamic MT5 Portfolio Configuration
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
