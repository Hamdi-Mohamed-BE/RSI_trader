@echo off
setlocal
cd /d "%~dp0"
set "PYTHONDONTWRITEBYTECODE=1"

where uv >nul 2>nul
if errorlevel 1 (
  echo Installing uv...
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
)

where uv >nul 2>nul
if errorlevel 1 (
  echo uv could not be installed automatically.
  echo Install uv and run this file again: https://docs.astral.sh/uv/
  pause
  exit /b 1
)

echo Installing and checking Python dependencies with uv...
uv sync
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-GoldNewsV9EA.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo Gold News V9 setup completed.
) else (
  echo Gold News V9 setup stopped with an error.
  if exist "%~dp0tmp\gold-news-v9-server.err.log" (
    echo.
    echo === Prediction server error log ===
    type "%~dp0tmp\gold-news-v9-server.err.log"
  )
  if exist "%~dp0tmp\gold-news-v9-server.out.log" (
    echo.
    echo === Prediction server output log ===
    type "%~dp0tmp\gold-news-v9-server.out.log"
  )
)
pause
exit /b %RESULT%
