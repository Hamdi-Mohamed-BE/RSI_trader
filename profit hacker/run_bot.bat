@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 exit /b %errorlevel%
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b %errorlevel%

".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 exit /b %errorlevel%

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Created .env. Fill TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, and broker settings, then run this file again.
    exit /b 1
)

".venv\Scripts\profit-hacker-bot.exe"
