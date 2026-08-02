@echo off
setlocal
cd /d "%~dp0"
uv sync
uv run amd-bot live
pause
