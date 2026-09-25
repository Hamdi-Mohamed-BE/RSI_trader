@echo off
title Calyx - Nasdaq 5M native comparison 2021-01-01 to now (isolated research terminal only)
cd /d "%~dp0"
echo Runs 2 MT5 Strategy Tester tests (current, DI) ONE AT A TIME in _Backtests\MT5-DMC-20260811.
echo Your normal MT5, live charts, AutoTrading and orders are not touched.
set "PY=C:\Program Files\Python313\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" run_native_compare.py since2021
echo.
echo Exit code %ERRORLEVEL%. Progress and evidence: native\status.json
pause
