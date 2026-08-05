@echo off
setlocal
title BM Trading +20 Percent Auto-Selected 900 USD - MT5 Installer

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Install-BMTradingPortfolio.ps1" -AccountProfile 900 %*
set "BM_EXIT=%ERRORLEVEL%"

echo.
if not "%BM_EXIT%"=="0" (
  echo The installer stopped without starting the portfolio.
) else (
  echo Installer finished.
)

if /I not "%~1"=="-ValidateOnly" pause
exit /b %BM_EXIT%
