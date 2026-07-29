@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo FX News Pulse - Two Month MT5 Backtest
echo ============================================================
echo This is read-only. It does not place or modify live orders.
echo.

python news_pulse_backtest.py
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
  echo Backtest failed. Review the message above.
) else (
  echo Backtest complete. Reports were saved in this folder.
)
pause
exit /b %EXIT_CODE%
