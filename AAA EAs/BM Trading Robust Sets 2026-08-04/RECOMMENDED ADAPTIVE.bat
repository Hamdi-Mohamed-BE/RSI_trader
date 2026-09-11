@echo off
setlocal
title Calyx - Recommended Adaptive

echo Applying the approved Recommended Adaptive portfolio...
echo - Every EA keeps its evidence-selected Standard, Safe or Dynamic preset.
echo - Every non-News EA follows the risk you select; pressing Enter defaults to 1%%.
echo - Entry lots round UP to the broker step; below-minimum requests use minimum lot and are never skipped for sizing.
echo - Actual stop risk can exceed the selected target when the broker lot step or minimum requires it.
echo - News Pulse v2.15 uses only high-impact primary NFP, CPI and FOMC events and uses at most 0.75%% per pending stop before adaptive tapering.
echo - Nasdaq 5M Candle Momentum is installed at 0.25x your selected risk.
echo - The compiled EAs natively enforce the approved daily-entry stop, drawdown taper and per-EA loss-streak taper on new entries.
echo - Existing positions and their protective stops are never changed by the shared portfolio governor.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Start-Dynamic-Portfolio.ps1" -SafetyMode STANDARD -UseRecommendedSelections -UseAdaptiveProfile %*
set "CALYX_EXIT=%ERRORLEVEL%"

echo.
if not "%CALYX_EXIT%"=="0" (
  echo The Recommended Adaptive installer stopped without starting the portfolio.
) else (
  echo Recommended Adaptive installation finished.
)

if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
