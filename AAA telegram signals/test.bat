@echo off
echo ==============================================
echo Running Unit Tests for Telegram-MT5 Copier
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
    
    echo Running pytest via uv...
    uv run pytest
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
    
    echo Running pytest...
    pytest
)

pause
