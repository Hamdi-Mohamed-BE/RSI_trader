@echo off
setlocal
title BM Trading - Best Recommended 2026-09-01

echo Applying the locked 24-EA recommended portfolio...
echo - 8 EAs use Dynamic 50-20 stop management
echo - 15 EAs retain their optimized native exits
echo - XAU New York, XAU overlap, US100 New York, US100 H1 and US100 Selective V3 standalone ORBs are included
echo - BTC POC Fibonacci keeps its optimized New York session; no master session filter is added
echo - BTC Top Down FVG defaults to all-day 2R; its session and embedded Safe filter remain per-EA inputs
echo - XAU Elliott Wave uses H4 EMA50 confirmation, signal-candle stop, fixed 3R and no trailing
echo - XAU Weakness uses M30 structure stops, 4R and Dynamic 50-20; Full Safe adds its D1 regime gate
echo - News Pulse XAU, XAG and EURUSD use two stops at 0.75%% each, hard-capped at 1.50%% total
echo - Engineered Liquidity BTC, US100 Fabio ORB and XAU Markov are excluded
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Start-Dynamic-Portfolio.ps1" -SafetyMode STANDARD -UseRecommendedSelections %*
set "BM_EXIT=%ERRORLEVEL%"

echo.
if not "%BM_EXIT%"=="0" (
  echo The best-recommended installer stopped without starting the portfolio.
) else (
  echo Best Recommended 2026-09-01 installation finished.
)

if /I not "%~1"=="-ValidateOnly" pause
exit /b %BM_EXIT%
