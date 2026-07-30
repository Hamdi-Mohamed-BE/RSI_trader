@echo off
cd /d "%~dp0"
uv run us100-bot --env .env discover
pause

