@echo off
echo ==============================================
echo Starting Telegram to MT5 Signal Copier
echo ==============================================

where uv >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] uv is installed. Checking virtual environment...
    if not exist .venv (
        echo Creating virtual environment via uv...
        uv venv
    )
    echo Installing/Updating dependencies via uv...
    uv pip install -e .
    
    if not exist storage (
        mkdir storage
    )
    if not exist storage\logs (
        mkdir storage\logs
    )
    
    echo Starting FastAPI server via uv...
    uv run uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload
) else (
    echo [WARN] uv not found. Falling back to standard python pip.
    if not exist .venv (
        echo Creating virtual environment...
        python -m venv .venv
    )
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo Installing/Updating dependencies...
    pip install -e .
    
    if not exist storage (
        mkdir storage
    )
    if not exist storage\logs (
        mkdir storage\logs
    )
    
    echo Starting FastAPI server...
    uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload
)

pause
