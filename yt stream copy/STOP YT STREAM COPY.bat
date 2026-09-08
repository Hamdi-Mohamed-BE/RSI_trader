@echo off
title YT Stream Copy - Stop
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>nul
echo YT Stream Copy stopped.
timeout /t 2 >nul

