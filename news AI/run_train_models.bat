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
if errorlevel 1 (
  echo Dependency setup failed.
  pause
  exit /b 1
)

uv run python news_ml_model_comparison.py
if errorlevel 1 goto :failed
uv run python official_text_hybrid_model.py
if errorlevel 1 goto :failed
echo.
echo Models and reports completed.
pause
exit /b 0

:failed
echo.
echo Model training failed. Review the message above.
pause
exit /b 1
