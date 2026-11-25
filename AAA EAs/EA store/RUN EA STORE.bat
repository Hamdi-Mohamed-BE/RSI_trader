@echo off
setlocal
cd /d "%~dp0"
rem 2026-11-25: a stale PYTHONHOME / PYTHONPATH breaks every Python ("Failed to import encodings module"); ignore them here.
set PYTHONHOME=
set PYTHONPATH=

where uv >nul 2>nul
if errorlevel 1 (
  echo ERROR: uv is not installed or is not available in PATH.
  echo Install uv, then run this file again.
  pause
  exit /b 1
)

echo Preparing Calyx...
uv sync
if not errorlevel 1 goto ready

rem 2026-11-25: the .venv was built on a Python that no longer starts. Keep it as a backup and rebuild on uv's own Python 3.12
rem (downloaded once by uv if missing), so a broken system Python cannot break the store again.
echo.
echo The Python environment is broken (its base Python no longer starts). Rebuilding it with uv's own Python 3.12...
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set STAMP=%%t
if exist ".venv" ren ".venv" ".venv.broken-%STAMP%"
uv python install 3.12
uv sync --python 3.12 --python-preference only-managed
if errorlevel 1 (
  echo.
  echo ERROR: The Python environment could not be prepared. The old one is kept as .venv.broken-%STAMP%.
  pause
  exit /b 1
)
echo Rebuilt OK. You can delete .venv.broken-%STAMP% later.

:ready
echo.
echo Local store: http://127.0.0.1:8080
echo Public store: http://YOUR-VPS-IP:8080
echo Press Ctrl+C in this window to stop the store.
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8080'"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080

endlocal
