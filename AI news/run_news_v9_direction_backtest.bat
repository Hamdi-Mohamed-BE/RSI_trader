@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "backtest_news_v9_direction_3m.py"
) else (
  py "backtest_news_v9_direction_3m.py"
)
pause
