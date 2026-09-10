@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "backtest_news_v8_dynamic_compounding_3m.py"
) else (
  py "backtest_news_v8_dynamic_compounding_3m.py"
)
pause
