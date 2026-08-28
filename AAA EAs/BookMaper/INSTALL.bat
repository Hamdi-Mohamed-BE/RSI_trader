@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo ERROR: uv is not installed or is not on PATH.
  echo Install it from https://docs.astral.sh/uv/getting-started/installation/
  pause
  exit /b 1
)
uv sync --locked --group dev
if errorlevel 1 (
  echo ERROR: Dependency installation failed.
  pause
  exit /b 1
)
if not exist ".env" copy /y ".env.example" ".env" >nul
echo.
echo BookMaper Markov research environment is ready.
echo Live trading remains disabled.
pause
