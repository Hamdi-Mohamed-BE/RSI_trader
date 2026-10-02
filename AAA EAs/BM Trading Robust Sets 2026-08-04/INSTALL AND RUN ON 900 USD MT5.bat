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
