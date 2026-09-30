@echo off
setlocal
title Calyx FTMO 10K Swing - 14 EAs (incl. 3 Way Gold) - News OFF
echo FTMO 2-Step Swing ONLY. 14 EAs incl. 3 Way Gold (market entries). Fixed $50 maximum planned stop risk per trade. News OFF.
echo Nasdaq 5M: DI14 selectable ON/OFF, default ON. 0.60%% stop, no TP, ATR6 from +1R unchanged.
echo Previous fixed-target portfolio pass estimates are NOT validated for this new management.
echo No terminal is armed automatically. Start with Algo Trading OFF and a flat account.
echo.
set "FTMO_PHASE=Challenge"
set /p "FTMO_PHASE=Phase [Challenge / Verification / Funded] (default Challenge): "
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Install-FTMO13.ps1" -Phase "%FTMO_PHASE%" -PromptNasdaqDIFilter %*
if errorlevel 1 echo STOPPED. Read the error above; do not bypass the account checks.
pause
endlocal
