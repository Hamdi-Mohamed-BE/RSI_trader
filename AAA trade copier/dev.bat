@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "AAA_COMMAND=%~1"
if "%AAA_COMMAND%"=="" goto help

where uv >nul 2>nul
if errorlevel 1 (
  echo [ERROR] uv is required. Install it from https://docs.astral.sh/uv/
  exit /b 1
)

if /I "%AAA_COMMAND%"=="setup" goto setup
if /I "%AAA_COMMAND%"=="web" goto web
if /I "%AAA_COMMAND%"=="core" goto core
if /I "%AAA_COMMAND%"=="start" goto start
if /I "%AAA_COMMAND%"=="create-admin" goto create_admin
if /I "%AAA_COMMAND%"=="init-db" goto init_db
if /I "%AAA_COMMAND%"=="seed-demo" goto seed_demo
if /I "%AAA_COMMAND%"=="css" goto css
if /I "%AAA_COMMAND%"=="compile-mt5" goto compile_mt5
if /I "%AAA_COMMAND%"=="test" goto test
if /I "%AAA_COMMAND%"=="check" goto check
if /I "%AAA_COMMAND%"=="docker-up" goto docker_up
if /I "%AAA_COMMAND%"=="docker-down" goto docker_down
echo [ERROR] Unknown command: %AAA_COMMAND%
goto help

:setup
if not exist ".env" copy /Y ".env.example" ".env" >nul
uv sync --extra dev --extra windows || exit /b 1
where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo [WARN] Node.js was not found. The committed CSS will be used.
) else (
  call npm.cmd install || exit /b 1
  call npm.cmd run build || exit /b 1
)
uv run aaa-trade-copier init-db || exit /b 1
uv run aaa-trade-copier seed-demo || exit /b 1
echo.
echo Setup is ready. Run: dev.bat create-admin
exit /b 0

:web
uv run aaa-trade-copier-web
exit /b %errorlevel%

:core
uv run aaa-trade-copier-core
exit /b %errorlevel%

:start
start "AAA Trade Copier Core" /D "%CD%" cmd /k call "%~f0" core
start "AAA Trade Copier Web" /D "%CD%" cmd /k call "%~f0" web
if "%WEB_HOST%"=="0.0.0.0" (
  echo Open http://YOUR-VPS-IP:8100 remotely
) else (
  echo Open http://127.0.0.1:8100
)
exit /b 0

:create_admin
uv run aaa-trade-copier create-admin
exit /b %errorlevel%

:init_db
uv run aaa-trade-copier init-db
exit /b %errorlevel%

:seed_demo
uv run aaa-trade-copier seed-demo
exit /b %errorlevel%

:css
call npm.cmd run build
exit /b %errorlevel%

:compile_mt5
set "AAA_METAEDITOR=C:\Program Files\MetaTrader 5\MetaEditor64.exe"
if not exist "%AAA_METAEDITOR%" set "AAA_METAEDITOR=C:\Program Files\JustMarkets MetaTrader 5\MetaEditor64.exe"
if not exist "%AAA_METAEDITOR%" (
  echo [ERROR] MetaEditor64.exe was not found in a supported default location.
  exit /b 1
)
"%AAA_METAEDITOR%" /compile:"%CD%\mt5\Experts\AAA_Master_Publisher.mq5" /inc:"%CD%\mt5" /log
powershell -NoProfile -Command "if (-not (Select-String -LiteralPath 'mt5\Experts\AAA_Master_Publisher.log' -SimpleMatch 'Result: 0 errors, 0 warnings')) { exit 1 }" || exit /b 1
"%AAA_METAEDITOR%" /compile:"%CD%\mt5\Experts\AAA_Follower_Executor.mq5" /inc:"%CD%\mt5" /log
powershell -NoProfile -Command "if (-not (Select-String -LiteralPath 'mt5\Experts\AAA_Follower_Executor.log' -SimpleMatch 'Result: 0 errors, 0 warnings')) { exit 1 }" || exit /b 1
echo Both MT5 agents compiled with zero errors and zero warnings.
exit /b 0

:test
uv run pytest -W error
exit /b %errorlevel%

:check
uv run ruff check . || exit /b 1
uv run mypy src tests || exit /b 1
uv run pytest -W error
exit /b %errorlevel%

:docker_up
docker compose up --build
exit /b %errorlevel%

:docker_down
docker compose down
exit /b %errorlevel%

:help
echo AAA Trade Copier development commands
echo.
echo   dev.bat setup         Install dependencies and initialize safe demo data
echo   dev.bat create-admin  Create a dashboard administrator interactively
echo   dev.bat start         Start the web dashboard and monitor in two windows
echo   dev.bat web           Start only the web dashboard
echo   dev.bat core          Start only the copier monitor
echo   dev.bat test          Run the automated tests
echo   dev.bat check         Run lint, type, and test checks
echo   dev.bat css           Rebuild Tailwind CSS
echo   dev.bat compile-mt5   Compile both MQL5 integration agents
echo   dev.bat docker-up     Run the demo control plane in Docker
echo   dev.bat docker-down   Stop the Docker demo
exit /b 1
