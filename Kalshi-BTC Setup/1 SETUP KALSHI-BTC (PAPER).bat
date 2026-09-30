@echo off
title Kalshi-BTC setup - PAPER MODE ONLY
setlocal
rem Installs https://github.com/J0shusmc/Kalshi-BTC (or your fork) into "..\Kalshi-BTC".
rem Creates a Python venv, installs requirements.txt, copies .env.example to .env if missing,
rem and runs the repo's own tests. It never enters credentials and never starts --live.
cd /d "%~dp0.."
set "TARGET=%CD%\Kalshi-BTC"
set "REPO=https://github.com/J0shusmc/Kalshi-BTC.git"
echo.
echo Paste your FORK URL (e.g. https://github.com/YOURNAME/Kalshi-BTC.git)
set /p "FORK=or press Enter to use the original repo: "
if not "%FORK%"=="" set "REPO=%FORK%"

set "PY=C:\Program Files\Python313\python.exe"
if not exist "%PY%" set "PY=py -3"

if exist "%TARGET%\.git" (
  echo Existing clone found at %TARGET% - pulling latest, local files kept.
  git -C "%TARGET%" pull --ff-only
) else (
  where git >nul 2>nul
  if errorlevel 1 (
    echo Git is not installed. Install it from https://git-scm.com/download/win and run this again.
    goto :end
  )
  echo Cloning %REPO% ...
  git clone "%REPO%" "%TARGET%" || goto :end
)

cd /d "%TARGET%"
if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment...
  "%PY%" -m venv venv || %PY% -m venv venv || goto :end
)
echo Installing requirements (this can take a few minutes)...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :end

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env from .env.example
) else (
  echo .env already exists - left unchanged.
)
if not exist "local" mkdir local

echo.
echo Running the repo's own tests...
"venv\Scripts\python.exe" -m pytest -q

echo.
echo ================= NEXT STEPS =================
echo 1. Create a Kalshi API key: kalshi.com - Account ^& security - API Keys - Create Key.
echo 2. Save the downloaded private key as:  %TARGET%\kalshi_private.key
echo 3. Open %TARGET%\.env in Notepad and set KALSHI_API_KEY to your Key ID.
echo    Do not paste the key or its contents into any chat.
echo 4. Run "2 RUN KALSHI-BTC PAPER.bat".
echo ==============================================
:end
echo.
pause
