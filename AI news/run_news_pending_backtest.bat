@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Python environment was not found at:
    echo %CD%\.venv
    echo.
    echo Run train_model.bat once to prepare the environment, then try again.
    pause
    exit /b 1
)

echo Running the two-year EURUSD and XAUUSD news pending-order backtest...
echo This does not connect to MT5 or place live orders.
echo.

".venv\Scripts\python.exe" backtest_news_pending.py
if errorlevel 1 (
    echo.
    echo Backtest failed. Review the error above.
    pause
    exit /b 1
)

echo.
echo Backtest complete.
echo Report: %CD%\NEWS_PENDING_2Y_RESULTS.md
echo Trades: %CD%\news_pending_2y_trades.csv
pause
