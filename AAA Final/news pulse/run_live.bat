@echo off
title AAA FINAL - NEWS PULSE
setlocal
cd /d "%~dp0"
echo ============================================================
echo  AAA FINAL - XAUUSD NEWS PULSE
echo ============================================================
uv sync
uv run news-pulse live
pause
