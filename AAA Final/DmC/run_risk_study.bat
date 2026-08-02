@echo off
cd /d "%~dp0"
uv run dmc-bot risk-study --days 60 --balance 1000
pause
