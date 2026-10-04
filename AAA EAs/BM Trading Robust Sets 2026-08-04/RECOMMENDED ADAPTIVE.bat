@echo off
echo US30/US100 hourly profiles included: selected risk uses historical-loss sizing; default 0.5%%. NO SL, no guaranteed loss cap.
rem ADXDI-FINAL-20261003: final user selection, only USDJPY keeps added ADX/DI.
echo Entry filters: USDJPY ADX20 plus DI; EMA3, Asia Gold and Trend added ADX/DI removed. RSI VWAP unchanged.
echo Selected-preset evidence is retrospective: 1, 3 and 5 years. Previous FTMO forecasts are not revalidated.
rem Nasdaq 5M: DI14 + EMA12, 0.60%% price SL, no TP, ATR6 trail from +1R; risk policies unchanged.
rem Nasdaq may hold overnight/weekends. Old fixed-target FTMO estimates do not apply.
rem For FTMO use "FTMO 10K SWING - 13 EAS - NEWS OFF.bat", not this unrestricted portfolio.
rem News Pulse v2.21: same exits/risk; definitive failures repair from fresh quotes, then same-direction market fallback.
rem All five selected news EAs restored by owner 2026-10-03; FTMO and Ava remain separate.
echo News EAs: XAU, XAG, BTC, EURUSD News Pulse plus Gold News V9 enabled.
setlocal
echo News risk is asked SEPARATELY per order. Both News Pulse triggers can double event exposure.
rem Includes Gold Overnight Value Area RAW via the shared normal-MT5 installer.
echo Gold Overnight Value Area RAW included: M5, overnight extreme TP, opposite value-area SL.
title Calyx - Recommended Adaptive

echo Applying the approved Recommended Adaptive portfolio...
echo - Every EA keeps its evidence-selected Standard, Safe or Dynamic preset.
echo - Every non-News EA follows the risk you select; pressing Enter defaults to 1%%.
echo - Entry lots round UP to the broker step; below-minimum requests use minimum lot and are never skipped for sizing.
echo - Actual stop risk can exceed the selected target when the broker lot step or minimum requires it.
echo - All four News Pulse assets plus Gold News V9 bypass adaptive entry stops and risk tapers.
echo - Four simultaneous News Pulse straddles plan 8x your selected news percentage; Gold News V9 adds exposure.
echo - Event-specific News Pulse results are hindsight optimized, not a forecast or proof of prop-firm safety.
echo - News uses its own selected percentage per order, recalculated at placement; it does not follow the non-News risk.
echo - Default news risk is 0.75%% per order only if you press Enter. Signal and broker checks remain active.
echo - News Pulse XAU uses the approved event-specific NFP/CPI/FOMC settings and retains both pending sides.
echo - Nasdaq 5M Candle Momentum is installed at 0.25x your selected risk.
echo - Non-News EAs block new entries after a 5%% daily closed loss and enforce the approved drawdown and per-EA loss-streak tapers.
echo - News profits and losses still count toward account-wide controls for non-News EAs.
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
