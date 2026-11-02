@echo off
rem ADXDI-FINAL-20261003: final user selection, only USDJPY keeps added ADX/DI.
echo Entry filters: USDJPY ADX20 plus DI; EMA3, Asia Gold and Trend added ADX/DI removed. RSI VWAP unchanged.
echo Selected-preset evidence is retrospective: 1, 3 and 5 years. Previous FTMO forecasts are not revalidated.
setlocal
title Calyx FTMO 10K Swing - 17 EAs - All five ORBs 0.5R - News OFF
echo FTMO 2-Step Swing ONLY. 17 EAs, ALL five ORBs 0.5R. Fixed $50 maximum planned stop risk per trade. News OFF.
echo Nasdaq 5M: DI14 selectable ON/OFF, default ON. ATR14 x6 initial stop (2026-11-02), no TP, ATR6 trail from +1R.
echo Previous fixed-target portfolio pass estimates are NOT validated for this new management.
echo No terminal is armed automatically. Start with Algo Trading OFF and a flat account.
echo.
set "FTMO_PHASE=Challenge"
set /p "FTMO_PHASE=Phase [Challenge / Verification / Funded] (default Challenge): "
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_00 Live profiles\Start-LiveProfile.ps1" -Portfolio ftmo -Phase "%FTMO_PHASE%" %*
if errorlevel 1 echo STOPPED. Read the error above; do not bypass the account checks.
pause
endlocal
