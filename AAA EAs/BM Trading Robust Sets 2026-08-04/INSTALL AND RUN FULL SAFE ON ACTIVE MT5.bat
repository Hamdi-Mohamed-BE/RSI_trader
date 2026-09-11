@echo off
setlocal
title Calyx Full Safe 32-EA Portfolio - Per-EA Regime Gates
echo Applying Full Safe to the current 32-EA portfolio. Gold News V9 and DMC Current XAU are retained; approved removals are excluded.
echo Entry lots round UP to the broker step; below-minimum requests use minimum lot and are never skipped for sizing.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Start-Dynamic-Portfolio.ps1" -SafetyMode SAFE %*
set "BM_EXIT=%ERRORLEVEL%"

echo.
if not "%BM_EXIT%"=="0" (
  echo The Full Safe installer stopped without starting the portfolio.
) else (
  echo Full Safe installer finished.
)

if /I not "%~1"=="-ValidateOnly" pause
exit /b %BM_EXIT%
