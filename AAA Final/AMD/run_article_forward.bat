@echo off
cd /d "%~dp0"
uv run amd-bot live --env .env.article
pause
