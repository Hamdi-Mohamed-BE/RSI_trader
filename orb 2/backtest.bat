@echo off
setlocal
cd /d "%~dp0"
title ORB2 Playbook Optimizer
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
echo Running walk-forward optimization...
uv run orb2-backtest
echo.
echo Optimization finished. Reports are in the reports folder.
pause
