@echo off
title YT Stream Copy - Install
cd /d "%~dp0"
where uv >nul 2>nul || (echo uv is required. Install it from https://docs.astral.sh/uv/ & pause & exit /b 1)
where ffmpeg >nul 2>nul || (echo ffmpeg is required and was not found in PATH. & pause & exit /b 1)
uv sync
if errorlevel 1 (echo Installation failed. & pause & exit /b 1)
echo Installation completed.
pause

