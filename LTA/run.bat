@echo off
setlocal

cd /d "%~dp0"
title LTA A+ Setup Research Platform

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    py -3 -m venv .venv 2>NUL
    if errorlevel 1 (
        python -m venv .venv
    )
)

echo Checking dependencies...
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, jinja2, pandas, numpy, matplotlib" >NUL 2>NUL
if errorlevel 1 (
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo.
echo LTA platform is starting.
echo Open http://127.0.0.1:8000
echo Press Ctrl+C in this window to stop the server.
echo.

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
