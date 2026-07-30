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

if not exist "node_modules\dukascopy-node" (
  where npm >nul 2>nul
  if errorlevel 1 (
    echo npm is required only when the market-data cache must be rebuilt.
  ) else (
    call npm ci
    if errorlevel 1 goto :failed
  )
)

uv run python official_release_text_collector.py
if errorlevel 1 goto :failed
uv run python news_ml_model_comparison.py
if errorlevel 1 goto :failed
uv run python official_text_hybrid_model.py
if errorlevel 1 goto :failed

echo.
echo Full research run completed.
pause
exit /b 0

:failed
echo.
echo Research run failed. Review the message above.
pause
exit /b 1
