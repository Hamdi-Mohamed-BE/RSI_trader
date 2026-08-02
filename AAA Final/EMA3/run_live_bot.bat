@echo off
cd /d "%~dp0"
uv sync
uv run ema3-live
pause
