@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

echo.
echo ==========================================
echo  HFT Scalper - Install
echo ==========================================
echo.

echo Checking Python...
call :AppendPythonDirsToPath
call :ResolvePython
if not errorlevel 1 goto HavePython

echo Python was not found.
where winget >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: winget was not found, so Python cannot be installed automatically.
    echo Install Python 3.12 from https://www.python.org/downloads/ and enable "Add python.exe to PATH".
    pause
    exit /b 1
)

echo Installing Python 3.12 with winget...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo.
    echo ERROR: Python install failed.
    pause
    exit /b 1
)

echo Refreshing PATH for this terminal...
call :AppendPythonDirsToPath
call :ResolvePython
if not errorlevel 1 goto HavePython

echo.
echo Python was installed, but this terminal cannot use it yet.
echo Close this window, open a new one, then run install.bat again.
pause
exit /b 1

:HavePython
echo Python found: %PY_CMD%
%PY_CMD% -c "import sys; print(sys.version)"
if errorlevel 1 (
    echo ERROR: Python exists but cannot run.
    pause
    exit /b 1
)

echo.
echo Installing/upgrading pip...
%PY_CMD% -m ensurepip --upgrade >nul 2>nul
%PY_CMD% -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo.
    echo ERROR: pip setup failed.
    pause
    exit /b 1
)

echo.
echo Installing dependencies from requirements.txt...
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Dependency install failed.
    pause
    exit /b 1
)

echo.
echo Verifying imports...
%PY_CMD% -c "import MetaTrader5, numpy; print('MetaTrader5 and numpy OK')"
if errorlevel 1 (
    echo.
    echo ERROR: Import verification failed.
    pause
    exit /b 1
)

echo.
echo Install complete.
echo Next: open MetaTrader 5, log in, then run run.bat to start the scalper.
echo Optional: %PY_CMD% diagnose.py
echo.
pause
exit /b 0

:ResolvePython
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=py -3"
        exit /b 0
    )
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=python"
        exit /b 0
    )
)
exit /b 1

:AppendPythonDirsToPath
for /f "delims=" %%D in ('dir /b /ad "%LocalAppData%\Programs\Python\Python3*" 2^>nul') do (
    set "PYTHON_DIR=%LocalAppData%\Programs\Python\%%D"
    if exist "!PYTHON_DIR!\python.exe" (
        set "PATH=!PYTHON_DIR!;!PYTHON_DIR!\Scripts;%PATH%"
    )
)
exit /b 0
