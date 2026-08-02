@echo off
title AAA FINAL - AMD
setlocal
cd /d "%~dp0"
echo ============================================================
echo  AAA FINAL - AMD BOT
echo ============================================================
echo.
uv sync
uv run amd-bot live
pause
