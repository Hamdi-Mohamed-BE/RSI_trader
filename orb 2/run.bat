@echo off
setlocal
cd /d "%~dp0"
title ORB2 Playbook Live Worker
where uv >nul 2>nul
if errorlevel 1 (
    echo uv is required. Install it from https://docs.astral.sh/uv/
    pause
    exit /b 1
)
echo Syncing ORB2 environment...
uv sync
if errorlevel 1 (
    echo Setup failed.
    pause
    exit /b 1
)
echo Starting visible ORB2 worker. Press Ctrl+C to stop.
uv run orb2-live
echo.
echo ORB2 worker stopped.
pause
