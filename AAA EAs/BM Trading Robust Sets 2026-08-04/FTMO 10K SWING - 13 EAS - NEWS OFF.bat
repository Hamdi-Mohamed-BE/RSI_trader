@echo off
rem ADXDI-FINAL-20261003: final user selection, only USDJPY keeps added ADX/DI.
echo Entry filters: USDJPY ADX20 plus DI; EMA3, Asia Gold and Trend added ADX/DI removed. RSI VWAP unchanged.
echo Selected-preset evidence is retrospective: 1, 3 and 5 years. Previous FTMO forecasts are not revalidated.
setlocal
title Calyx FTMO 10K Swing - 17 EAs - All five ORBs 0.5R - News OFF
echo FTMO 2-Step Swing ONLY. 17 EAs, ALL five ORBs 0.5R. Fixed $50 maximum planned stop risk per trade. News OFF.
echo Nasdaq 5M: DI14 selectable ON/OFF, default ON. 0.60%% stop, no TP, ATR6 from +1R unchanged.
echo Previous fixed-target portfolio pass estimates are NOT validated for this new management.
echo No terminal is armed automatically. Start with Algo Trading OFF and a flat account.
echo.
set "FTMO_PHASE=Challenge"
set /p "FTMO_PHASE=Phase [Challenge / Verification / Funded] (default Challenge): "
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_00 Live profiles\Start-LiveProfile.ps1" -Portfolio ftmo -Phase "%FTMO_PHASE%" %*
if errorlevel 1 echo STOPPED. Read the error above; do not bypass the account checks.
pause
endlocal
