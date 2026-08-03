@echo off
title AAA FINAL - NEWS PULSE PAPER
setlocal
cd /d "%~dp0"
echo ============================================================
echo  AAA FINAL - XAUUSD NEWS PULSE (SAFE PAPER CYCLE)
echo ============================================================
uv sync
uv run news-pulse paper
pause
