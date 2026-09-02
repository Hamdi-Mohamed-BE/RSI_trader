@echo off
setlocal
title BM Trading +20 Percent - Any Balance Auto Risk

rem This compatibility launcher now delegates to the maintained parent installer.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\_Auto Deploy\Install-BMTradingPortfolio.ps1" -AccountProfile AUTO %*
set "BM_EXIT=%ERRORLEVEL%"

echo.
if not "%BM_EXIT%"=="0" (
  echo The installer stopped without starting the portfolio.
) else (
  echo Installer finished.
)

if /I not "%~1"=="-ValidateOnly" pause
exit /b %BM_EXIT%
