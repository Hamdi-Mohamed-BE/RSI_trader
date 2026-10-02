@echo off
rem Nasdaq 5M: DI14 + EMA12, 0.60%% price SL, no TP, ATR6 trail from +1R; risk policies unchanged.
rem Nasdaq may hold overnight/weekends. Old fixed-target FTMO estimates do not apply.
rem For FTMO use "FTMO 10K SWING - 13 EAS - NEWS OFF.bat", not this unrestricted portfolio.
rem XAU News Pulse v2.16 event settings retained; v2.18 adds standalone user-selected percentage per order.
rem Gold-only news policy: XAG/BTC/EURUSD News Pulse disabled in the shared installer.
echo News EAs: XAU News Pulse and Gold News V9 only. All non-gold news OFF.
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
echo - Only XAU News Pulse and Gold News V9 bypass adaptive entry stops and risk tapers. Other news assets OFF.
echo - The XAU News Pulse straddle plans 2x your selected news percentage; Gold News V9 adds exposure.
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
