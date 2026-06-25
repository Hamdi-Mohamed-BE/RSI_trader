@echo off
setlocal EnableExtensions

cd /d "%~dp0"
title LTA All Bots Launcher

echo.
echo LTA All Bots Launcher
echo =====================
echo This starts each bot in its own visible terminal window.
echo Close a bot window or use the matching stop_*.bat file to stop that bot.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    py -3 -m venv .venv 2>NUL
    if errorlevel 1 (
        python -m venv .venv
    )
)

echo Checking dependencies...
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, jinja2, pandas, numpy, MetaTrader5" >NUL 2>NUL
if errorlevel 1 (
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo.
echo Live risk note:
echo LIVE_TRADING / strategy-specific .env switches control whether each bot can place MT5 orders.
echo The News bot is configured to place pending news straddles when NEWS_PLACE_PENDING=true.
echo.

set "MODE=%~1"
if /I "%MODE%"=="--enabled" goto :enabled_only

echo Starting all bot windows...
call :start_bot "LTA A+ Bot" "run_lta_bot.bat"
call :start_bot "ORB Bot" "run_orb_bot.bat"
call :start_bot "20 Pip Challenge Bot" "run_20pip_bot.bat"
call :start_bot "Grid Range Bot" "run_grid_bot.bat"
call :start_bot "Trend Following Bot" "run_trend_bot.bat"
call :start_bot "Mean Reversion Bot" "run_mean_reversion_bot.bat"
call :start_bot "DCA Dip Bot" "run_dca_bot.bat"
call :start_bot "News Pulse Bot" "run_news_bot.bat"
call :start_bot "Arbitrage Framework" "run_arbitrage_bot.bat"
call :start_bot "Sniper Bot" "run_sniper_bot.bat"
goto :done

:enabled_only
echo Starting production/enabled bot windows only...
call :start_bot "LTA A+ Bot" "run_lta_bot.bat"
call :start_bot "ORB Bot" "run_orb_bot.bat"
call :start_bot "20 Pip Challenge Bot" "run_20pip_bot.bat"
call :start_bot "Grid Range Bot" "run_grid_bot.bat"
call :start_bot "News Pulse Bot" "run_news_bot.bat"
call :start_bot "Sniper Bot" "run_sniper_bot.bat"
goto :done

:start_bot
set "BOT_NAME=%~1"
set "BOT_FILE=%~2"
if not exist "%BOT_FILE%" (
    echo [MISSING] %BOT_NAME% - %BOT_FILE%
    exit /b 0
)
echo [START] %BOT_NAME%
start "%BOT_NAME%" /normal cmd /k ""%~dp0%BOT_FILE%" --visible"
timeout /t 2 /nobreak >NUL
exit /b 0

:done
echo.
echo Launch requests sent.
echo Default mode starts every bot launcher.
echo Use run_all_bots.bat --enabled to start only the currently useful production/enabled set.
echo.
pause
