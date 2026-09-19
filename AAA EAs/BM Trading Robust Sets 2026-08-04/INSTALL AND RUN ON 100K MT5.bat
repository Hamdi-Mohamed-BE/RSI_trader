@echo off
rem XAU News Pulse v2.16: NFP/CPI/FOMC event-specific settings via shared installer; both pending sides retained.
rem XAG/BTC/EURUSD News Pulse v2.17: approved full-year event combinations, adaptive exempt; no OCO.
setlocal
title Calyx 32-EA Portfolio - Any Balance Auto Risk
echo Applying the current 32-EA Standard portfolio. Gold News V9 and DMC Current XAU are retained; approved removals are excluded.
echo Entry lots round UP to the broker step; below-minimum requests use minimum lot and are never skipped for sizing.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Start-Dynamic-Portfolio.ps1" -SafetyMode STANDARD %*
set "BM_EXIT=%ERRORLEVEL%"

echo.
if not "%BM_EXIT%"=="0" (
  echo The installer stopped without starting the portfolio.
) else (
  echo Installer finished.
)

if /I not "%~1"=="-ValidateOnly" pause
exit /b %BM_EXIT%
