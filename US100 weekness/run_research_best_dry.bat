@echo off
cd /d "%~dp0"
uv run us100-bot --env .env.research_best live
pause
