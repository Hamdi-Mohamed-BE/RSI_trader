@echo off
title AAA FINAL - WEEKEND DIRECTION PAPER
setlocal
cd /d "%~dp0"
echo ============================================================
echo  AAA FINAL - XAUUSD WEEKEND DIRECTION (SAFE PAPER CYCLE)
echo ============================================================
uv sync
uv run weekend-direction paper
pause
