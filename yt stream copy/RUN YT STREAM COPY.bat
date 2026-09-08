@echo off
title YT STREAM COPY - LIVE MONITOR
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call "INSTALL.bat"
start "" "http://127.0.0.1:8765"
uv run python run.py
pause

