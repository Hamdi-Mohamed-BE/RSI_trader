@echo off
setlocal
cd /d "%~dp0"
set "PYTHONDONTWRITEBYTECODE=1"

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

if not exist "models\gold_news_v9_direction.joblib" (
  echo Required model is missing: models\gold_news_v9_direction.joblib
  pause
  exit /b 1
)

if not exist "models\gold_news_v8_move_range.joblib" (
  echo Required model is missing: models\gold_news_v8_move_range.joblib
  pause
  exit /b 1
)

if exist ".env" (
  for /f "tokens=2 delims==" %%A in ('findstr /b "APP_HOST=" .env') do set APP_HOST=%%A
  for /f "tokens=2 delims==" %%A in ('findstr /b "APP_PORT=" .env') do set APP_PORT=%%A
)
if not defined APP_HOST set APP_HOST=127.0.0.1
if not defined APP_PORT set APP_PORT=8799

echo Opening Gold News AI at http://%APP_HOST%:%APP_PORT%
uv run --quiet python -u -m uvicorn app:app --host %APP_HOST% --port %APP_PORT%
