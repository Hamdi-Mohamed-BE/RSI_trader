@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title XAU M1 GRID - PREREQUISITE INSTALLER

echo ============================================================
echo XAU M1 Buy-Stop Grid - One-Time Prerequisite Installer
echo ============================================================
echo This installs a local Python environment and Node packages.
echo It does NOT start the bot and does NOT place any orders.
echo.

call :find_python
if defined PYTHON_EXE goto python_ready

echo [1/5] Python was not found. Installing Python 3.13...
where winget >nul 2>&1
if errorlevel 1 goto no_winget
winget install --exact --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto failed
set "PATH=%LocalAppData%\Programs\Python\Python313;%LocalAppData%\Programs\Python\Python313\Scripts;C:\Program Files\Python313;%PATH%"
call :find_python
if not defined PYTHON_EXE goto restart_required

:python_ready
echo [1/5] Python found: %PYTHON_EXE% %PYTHON_ARGS%

echo [2/5] Creating the project virtual environment...
if not exist ".venv\Scripts\python.exe" (
  %PYTHON_EXE% %PYTHON_ARGS% -m venv ".venv"
  if errorlevel 1 goto failed
) else (
  echo       Existing .venv will be reused.
)

echo [3/5] Installing Python dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install --requirement requirements.txt
if errorlevel 1 goto failed

where node >nul 2>&1
if not errorlevel 1 goto node_ready
echo [4/5] Node.js was not found. Installing Node.js LTS...
where winget >nul 2>&1
if errorlevel 1 goto no_winget
winget install --exact --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto failed
set "PATH=C:\Program Files\nodejs;%PATH%"
where node >nul 2>&1
if errorlevel 1 goto restart_required

:node_ready
echo [4/5] Installing locked Node dependencies...
call npm.cmd ci --no-audit --no-fund
if errorlevel 1 goto failed

echo [5/5] Verifying the installation...
".venv\Scripts\python.exe" -c "import MetaTrader5 as mt5; print('MetaTrader5 Python package:', mt5.__version__)"
if errorlevel 1 goto failed
call npm.cmd --version >nul
if errorlevel 1 goto failed

echo.
echo ============================================================
echo INSTALLATION COMPLETE
echo ============================================================
echo Next: keep your logged-in MT5 terminal open, review .env,
echo and run run.bat when you intentionally want to run the bot.
echo.
pause
exit /b 0

:find_python
set "PYTHON_EXE="
set "PYTHON_ARGS="
where py >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_EXE=py"
  set "PYTHON_ARGS=-3"
  exit /b 0
)
where python >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_EXE=python"
  exit /b 0
)
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
  set PYTHON_EXE="%LocalAppData%\Programs\Python\Python313\python.exe"
  exit /b 0
)
if exist "C:\Program Files\Python313\python.exe" (
  set PYTHON_EXE="C:\Program Files\Python313\python.exe"
)
exit /b 0

:no_winget
echo.
echo ERROR: Windows Package Manager was not found.
echo Install Python 3.13 and Node.js LTS, then run this file again.
goto failed

:restart_required
echo.
echo Python or Node was installed, but Windows has not refreshed PATH yet.
echo Close this window and run pre_install.bat one more time.
pause
exit /b 2

:failed
echo.
echo INSTALLATION FAILED. Review the error shown above.
pause
exit /b 1
