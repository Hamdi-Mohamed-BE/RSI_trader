@echo off
setlocal
title BM Trading - Best Recommended 2026-09-01

echo Applying the locked 28-EA recommended portfolio...
echo - 8 EAs use Dynamic 50-20 stop management
echo - 19 EAs retain their optimized native exits
echo - XAU New York, XAU overlap, US100 New York, US100 H1 and US100 Selective V3 standalone ORBs are included
echo - BTC POC Fibonacci keeps its optimized New York session; no master session filter is added
echo - BTC Top Down FVG defaults to all-day 2R; its session and embedded Safe filter remain per-EA inputs
echo - XAU Elliott Wave uses H4 EMA50 confirmation, signal-candle stop, fixed 3R and no trailing
echo - LTA Volume Profile, EMA3 and XAU Weakness default to their evidence-selected Safe mode
echo - XAU Slow Trend uses H4 1/3/6-month momentum, EMA100, 1.5 ATR stop, fixed 6R and hard 1%% risk
echo - XAU Regime Switch is DEMO-STAGE: H4 6R slow trend in directional regimes and M5 3R overlap VWAP snapback in sideways regimes, hard 1%% risk
echo - XAG Session VWAP Snapback uses M30 New York, 2.5 sigma, ADX20, 1.25 ATR stop, fixed 1R and hard 1%% risk
echo - US100 Month-End Flow uses M30, first 3 business days, NY first-hour entry, 1.5 ATR stop, fixed 2.5R, 6-hour exit and hard 1%% risk
echo - XAU Weakness uses M30 structure stops, 4R and Dynamic 50-20 with its D1 Safe gate enabled
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
