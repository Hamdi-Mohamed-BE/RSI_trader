@echo off
setlocal
title XAU M1 OCO - Verified MT5 Backtest
cd /d "%~dp0"

echo This runs the OCO EA on XAUUSD M1 in an isolated Exness MT5 tester.
echo It does not use the symbol currently selected in the MT5 Strategy Tester UI.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-Verified-Backtest.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
  echo BACKTEST FAILED. Read the exact reason above.
) else (
  echo BACKTEST COMPLETE. The MT5 report is in the Backtest Reports folder.
)
pause
exit /b %EXIT_CODE%
