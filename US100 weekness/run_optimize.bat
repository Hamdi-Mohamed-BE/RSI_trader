@echo off
cd /d "%~dp0"
uv run nasdaq-weakness optimize
pause
