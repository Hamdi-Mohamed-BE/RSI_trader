@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

echo.
echo ==========================================
echo  RSI Divergence MT5 Bot - Full Install
echo ==========================================
echo.

if not exist "runtime" (
    echo Creating runtime folder...
    mkdir "runtime"
)

if not exist "config.yaml" (
    if exist "config.example.yaml" (
        echo Creating config.yaml from config.example.yaml...
        copy "config.example.yaml" "config.yaml" >nul
    ) else (
        echo ERROR: config.yaml and config.example.yaml are missing.
        pause
        exit /b 1
    )
)

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
echo Checking uv...
call :ResolveUv
if not errorlevel 1 goto HaveUv

echo Installing uv...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression }"
if errorlevel 1 (
    echo.
    echo ERROR: uv install failed.
    pause
    exit /b 1
)

set "LOCAL_BIN=%USERPROFILE%\.local\bin"
if exist "%LOCAL_BIN%\uv.exe" set "PATH=%LOCAL_BIN%;%PATH%"
call :ResolveUv
if not errorlevel 1 goto HaveUv

echo.
echo ERROR: uv.exe was installed but cannot be found in this terminal.
echo Reopen the terminal and run install.bat again.
pause
exit /b 1

:HaveUv
echo uv found: %UV_EXE%
"%UV_EXE%" --version
if errorlevel 1 (
    echo ERROR: uv exists but cannot run.
    pause
    exit /b 1
)

echo.
echo Installing project dependencies with uv...
"%UV_EXE%" sync
if errorlevel 1 (
    echo.
    echo ERROR: Dependency install failed.
    echo If the dashboard is running, stop it first because Windows may lock rsi-bot.exe.
    pause
    exit /b 1
)

echo.
echo Installing Playwright Chromium for Telegram Web (default browser)...
"%UV_EXE%" run python -m playwright install chromium
if errorlevel 1 (
    echo.
    echo WARNING: Playwright Chromium install failed or timed out.
    echo Run manually: uv run python -m playwright install chromium
)

echo.
echo Verifying imports...
"%UV_EXE%" run python -c "import fastapi, pydantic, playwright, langchain_core, langchain_google_genai; print('imports ok')"
if errorlevel 1 (
    echo.
    echo ERROR: Import verification failed.
    pause
    exit /b 1
)

echo.
echo Install complete.
echo Next: open run.bat to start the web dashboard with config.yaml.
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

:ResolveUv
set "UV_EXE="
for /f "delims=" %%I in ('where uv 2^>nul') do if not defined UV_EXE set "UV_EXE=%%I"
if not defined UV_EXE if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
if defined UV_EXE exit /b 0
exit /b 1

:AppendPythonDirsToPath
for /f "delims=" %%D in ('dir /b /ad "%LocalAppData%\Programs\Python\Python3*" 2^>nul') do (
    set "PYTHON_DIR=%LocalAppData%\Programs\Python\%%D"
    if exist "!PYTHON_DIR!\python.exe" (
        set "PATH=!PYTHON_DIR!;!PYTHON_DIR!\Scripts;%PATH%"
    )
)
exit /b 0
