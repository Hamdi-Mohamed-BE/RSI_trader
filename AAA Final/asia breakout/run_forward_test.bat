@echo off
cd /d "%~dp0"
uv run asia-breakout live --env .env.forward
pause
