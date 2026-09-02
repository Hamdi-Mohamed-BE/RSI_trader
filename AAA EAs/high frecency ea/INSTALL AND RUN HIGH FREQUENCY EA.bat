@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Install XAUUSD M1 High Frequency OCO EA

echo.
echo XAUUSD M1 HIGH FREQUENCY OCO EA
echo --------------------------------
echo Open and log into the target MT5 before continuing.
echo The installer will close and restart that MT5 on a dedicated one-chart profile.
echo This package is separate from the main portfolio BAT and website.
echo.
echo SAFER RECOMMENDED PRESET WILL BE APPLIED AUTOMATICALLY:
echo   Fixed lot: 0.01 ^(dynamic scaling disabled^)
echo   Session: 13:00-21:00 server time
echo   Previous-M1 breakout with range and volume confirmation
echo   Virtual one-shot OCO ^(prevents two broker orders filling together^)
echo   Entry / SL / trail: 0.40 / 0.50 / 0.80 start, 0.45 distance
echo   5-minute cooldown after a loss, 12 trades/day, $3 daily loss guard
echo WARNING: the EA can place real trades immediately after MT5 restarts.
echo.

"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-HighFrequencyEA.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo Installation failed. No main portfolio BAT or website file was changed.
) else (
    echo Standalone high-frequency EA installation completed.
)
pause
exit /b %EXIT_CODE%
