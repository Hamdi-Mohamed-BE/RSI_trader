@echo off
cd /d "%~dp0"
uv run python -m nasdaq_weakness.risk_study
pause
