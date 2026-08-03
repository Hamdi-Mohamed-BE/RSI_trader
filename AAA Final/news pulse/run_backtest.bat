@echo off
title AAA FINAL - NEWS PULSE BACKTEST
setlocal
cd /d "%~dp0"
uv sync --extra dev
uv run news-pulse backtest
pause
