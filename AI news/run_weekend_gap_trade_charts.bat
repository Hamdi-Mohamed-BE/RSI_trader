@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run uv sync first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" render_weekend_gap_trade_charts.py
if errorlevel 1 (
  echo Chart generation failed.
  pause
  exit /b 1
)
start "" "%CD%\charts\weekend-gap-best-1y\index.html"
