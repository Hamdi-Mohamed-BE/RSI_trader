@echo off
setlocal
title BM Trading Full Safe Portfolio - Per-EA Regime Gates

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Install-BMTradingPortfolio.ps1" -AccountProfile AUTO -SafetyMode SAFE %*
set "BM_EXIT=%ERRORLEVEL%"

echo.
if not "%BM_EXIT%"=="0" (
  echo The Full Safe installer stopped without starting the portfolio.
) else (
  echo Full Safe installer finished.
)

if /I not "%~1"=="-ValidateOnly" pause
exit /b %BM_EXIT%
