@echo off
setlocal
cd /d "%~dp0"
title US100 London Midpoint Backtest

where uv >nul 2>&1
if errorlevel 1 (
    echo uv is required. Install it from https://docs.astral.sh/uv/
    pause
    exit /b 1
)

uv sync --quiet
if errorlevel 1 (
    echo Setup failed.
    pause
    exit /b 1
)

uv run orb-london-backtest
pause

