@echo off
setlocal
title BM Trading +20 Percent - Any Balance Auto Risk

rem This compatibility launcher uses the maintained risk-and-safety prompt.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\_Auto Deploy\Start-Dynamic-Portfolio.ps1" %*
set "BM_EXIT=%ERRORLEVEL%"

echo.
if not "%BM_EXIT%"=="0" (
  echo The installer stopped without starting the portfolio.
) else (
  echo Installer finished.
)

if /I not "%~1"=="-ValidateOnly" pause
exit /b %BM_EXIT%
