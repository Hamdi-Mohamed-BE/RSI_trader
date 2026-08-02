@echo off
cd /d "%~dp0"
uv run --extra dev python -m amd_bot.risk_study
pause
