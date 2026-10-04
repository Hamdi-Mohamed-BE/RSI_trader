@echo off
echo US30/US100 hourly profiles included: selected risk uses historical-loss sizing; default 0.5%%. NO SL, no guaranteed loss cap.
setlocal
title BM Trading +20 Percent - Any Balance Auto Risk

rem This compatibility launcher uses the maintained risk-and-safety prompt.
echo News EAs: XAU, XAG, BTC, EURUSD News Pulse plus Gold News V9 enabled.
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
