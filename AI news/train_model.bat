@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required. Install it from https://docs.astral.sh/uv/
  pause
  exit /b 1
)

uv sync
if errorlevel 1 goto :failed
uv run python train_news_model.py
if errorlevel 1 goto :failed

echo.
echo Models and walk-forward report completed.
pause
exit /b 0

:failed
echo.
echo Training failed. Review the message above.
pause
exit /b 1
