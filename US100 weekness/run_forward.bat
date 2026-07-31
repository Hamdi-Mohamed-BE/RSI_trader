@echo off
cd /d "%~dp0"
uv run nasdaq-weakness forward
pause
