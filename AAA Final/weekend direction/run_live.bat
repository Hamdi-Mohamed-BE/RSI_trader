@echo off
title AAA FINAL - WEEKEND DIRECTION
setlocal
cd /d "%~dp0"
echo ============================================================
echo  AAA FINAL - XAUUSD WEEKEND DIRECTION
echo ============================================================
uv sync
uv run weekend-direction live
pause
