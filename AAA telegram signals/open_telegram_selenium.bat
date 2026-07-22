@echo off
setlocal
cd /d "%~dp0"

echo Opening Telegram Web with Selenium...
echo This uses storage\selenium_telegram_profile so the login can persist.
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" open_telegram_selenium.py
) else (
    python open_telegram_selenium.py
)

pause
