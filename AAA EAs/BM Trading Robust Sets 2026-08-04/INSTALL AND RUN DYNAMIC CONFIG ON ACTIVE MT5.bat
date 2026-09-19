@echo off
rem XAU News Pulse v2.16: NFP/CPI/FOMC event-specific settings via shared installer; both pending sides retained.
rem XAG/BTC/EURUSD News Pulse v2.17: approved full-year event combinations, adaptive exempt; no OCO.
setlocal
rem Includes Gold Overnight Value Area RAW via the shared normal-MT5 installer.
echo Gold Overnight Value Area RAW included: M5, overnight extreme TP, opposite value-area SL.
title Calyx - Dynamic managed EA Portfolio Configuration
echo Configuring the current managed EA portfolio. Gold News V9 and DMC Current XAU are retained; approved removals are excluded.
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
