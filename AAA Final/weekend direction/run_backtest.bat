@echo off
title AAA FINAL - WEEKEND DIRECTION BACKTEST
setlocal
cd /d "%~dp0"
uv sync --extra dev
uv run weekend-direction backtest
pause
