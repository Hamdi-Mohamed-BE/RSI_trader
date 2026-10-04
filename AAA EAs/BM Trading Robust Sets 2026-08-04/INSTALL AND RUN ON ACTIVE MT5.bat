@echo off
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
title Calyx managed EA Portfolio - Any Balance Auto Risk
echo Applying the current managed EA Standard portfolio. Gold News V9 and DMC Current XAU are retained; approved removals are excluded.
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
