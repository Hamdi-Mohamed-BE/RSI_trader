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
echo Nasdaq 5M DI14 filter is selectable below: ON by default, or OFF. Wider stop and ATR trailing stay unchanged.
echo News risk is asked SEPARATELY per order. Both News Pulse triggers can double event exposure.
rem Includes Gold Overnight Value Area RAW via the shared normal-MT5 installer.
echo Gold Overnight Value Area RAW included: M5, overnight extreme TP, opposite value-area SL.
title BM Trading - Best Recommended 2026-09-01

echo Applying the locked managed EA recommended portfolio...
echo - 8 EAs use Dynamic 50-20 stop management
echo - 1 EA uses its optimized Dynamic 60-20 stop management
echo - Sell Nasdaq 15min now defaults to evidence-selected Dynamic London exits
echo - 21 EAs retain their optimized native exits
echo - XAU New York, XAU overlap, US100 New York, US100 H1 and US100 Selective V3 standalone ORBs are included
echo - BTC POC Fibonacci keeps its optimized New York session; no master session filter is added
echo - BTC Top Down FVG defaults to all-day 2R; its session and embedded Safe filter remain per-EA inputs
echo - XAU Elliott Wave uses H4 EMA50 confirmation, signal-candle stop, fixed 3R and no trailing
echo - LTA Volume Profile, EMA3, XAU Weakness and XAU Squeeze Momentum default to their evidence-selected Safe mode
echo - XAU Slow Trend uses H4 1/3/6-month momentum, EMA100, 1.5 ATR stop and fixed 1R
echo - XAU Trend Progression targets 0.6R; separate FTMO BAT uses Slow 0.5R
echo - XAU Regime Switch is DEMO-STAGE: H4 6R slow trend in directional regimes and M5 3R overlap VWAP snapback in sideways regimes
echo - US100 Month-End Flow uses M30, first 3 business days, NY first-hour entry, 1.5 ATR stop, fixed 2.5R and a 6-hour exit
echo - Sell Nasdaq 15min defaults to Dynamic London: bearish London confirmation, ATR14 x2.5 stop, fixed 3R target and a 60-minute entry window
echo - USDJPY London Open Momentum trades Wednesday-Friday after the 08:00-09:00 London move, uses a 5 ATR stop, breakeven at 0.75R and exits at 16:00 London
echo - XAU Squeeze Momentum Standard uses BB24/KC24, momentum 28, SMA200, a 3.5 ATR stop, 1.5R target and 3.5 ATR ratchet; Best Recommended selects its Safe D1 gate
echo - DMC Current XAU retains the H1 Asia baseline with fixed 22.5 stop, 3R and Dynamic 50-20
echo - DMC Fresh Reaction XAU adds M15 freshness plus W1/MN1 proximity, fixed 30 stop, 3R and Dynamic 50-20
echo - DMC Fresh Reaction US100 uses the same freshness logic in New York with 1.5 ATR stop, 2R and Dynamic 50-20
echo - Full Safe switches Sell Nasdaq 15min to the original London-confirmed 600/1000 preset
echo - XAU Weakness uses M30 structure stops, 4R and Dynamic 50-20 with its D1 Safe gate enabled
echo - All News Pulse assets keep their event-specific exits/risk and both directions; fresh-quote order repair enabled.
echo - Choose the news percentage separately below: PER ORDER, not per event; two triggers can double exposure
echo - Gold News V9 Direction runs on XAUUSD M1 with the local prediction service and remains attached after every shared install
echo - Every non-News EA follows the risk selected below; pressing Enter defaults to 1%%
echo - Entry lots round UP to the broker step; below-minimum requests use minimum lot and are never skipped for sizing
echo - Actual stop risk can exceed the selected target when the broker lot step or minimum requires it
echo - Approved portfolio audit removals: Engineered Liquidity XAU, ORB Volume High Win 0.75R, XAG VWAP Snapback and XAU Squeeze High Win 0.75R
echo - DMC Current XAU was explicitly retained after review
echo - Earlier rejected research builds such as Engineered Liquidity BTC, US100 Fabio ORB and XAU Markov remain excluded
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Start-Dynamic-Portfolio.ps1" -SafetyMode STANDARD -UseRecommendedSelections -PromptNasdaqDIFilter %*
set "BM_EXIT=%ERRORLEVEL%"

echo.
if not "%BM_EXIT%"=="0" (
  echo The best-recommended installer stopped without starting the portfolio.
) else (
  echo Best Recommended 2026-09-01 installation finished.
)

if /I not "%~1"=="-ValidateOnly" pause
exit /b %BM_EXIT%
