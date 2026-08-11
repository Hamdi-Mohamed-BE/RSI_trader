@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=help"

if /I "%ACTION%"=="help" goto help
if /I "%ACTION%"=="setup" goto setup
if /I "%ACTION%"=="web" goto web
if /I "%ACTION%"=="worker" goto worker
if /I "%ACTION%"=="css" goto css
if /I "%ACTION%"=="css-watch" goto css_watch
if /I "%ACTION%"=="all" goto all
if /I "%ACTION%"=="test" goto test
if /I "%ACTION%"=="check" goto check
if /I "%ACTION%"=="migrate" goto migrate
if /I "%ACTION%"=="migrations" goto migrations
if /I "%ACTION%"=="superuser" goto superuser
if /I "%ACTION%"=="seed" goto seed
if /I "%ACTION%"=="sync-ai" goto sync_ai
if /I "%ACTION%"=="docker-up" goto docker_up
if /I "%ACTION%"=="docker-down" goto docker_down
if /I "%ACTION%"=="docker-logs" goto docker_logs

echo Unknown command: %ACTION%
goto help_error

:ensure_uv
where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required. Install it from https://docs.astral.sh/uv/
  exit /b 1
)
exit /b 0

:ensure_node
where npm >nul 2>nul
if errorlevel 1 (
  echo Node.js and npm are required to build the Tailwind assets.
  exit /b 1
)
exit /b 0

:ensure_env
if not exist ".env" copy /Y ".env.example" ".env" >nul
exit /b 0

:setup
call :ensure_uv || exit /b 1
call :ensure_node || exit /b 1
call :ensure_env || exit /b 1
uv sync || exit /b 1
call npm ci || exit /b 1
call npm run assets:build || exit /b 1
uv run python manage.py migrate || exit /b 1
uv run python manage.py sync_llm_config || exit /b 1
uv run python manage.py seed_demo || exit /b 1
echo.
echo Setup complete. Run: dev.bat web
exit /b 0

:web
call :ensure_uv || exit /b 1
call :ensure_env || exit /b 1
uv run python manage.py sync_llm_config || exit /b 1
uv run python manage.py runserver
exit /b %errorlevel%

:worker
call :ensure_uv || exit /b 1
call :ensure_env || exit /b 1
uv run celery -A config worker --loglevel=INFO --pool=solo
exit /b %errorlevel%

:css
call :ensure_node || exit /b 1
call npm run css:build
exit /b %errorlevel%

:css_watch
call :ensure_node || exit /b 1
call npm run css:watch
exit /b %errorlevel%

:all
call :ensure_env || exit /b 1
start "AAA Tailwind" cmd /k call "%~f0" css-watch
start "AAA Celery" cmd /k call "%~f0" worker
call "%~f0" web
exit /b %errorlevel%

:test
call :ensure_uv || exit /b 1
uv run pytest
exit /b %errorlevel%

:check
call :ensure_uv || exit /b 1
uv run ruff check . || exit /b 1
uv run mypy apps config || exit /b 1
uv run python manage.py check || exit /b 1
uv run pytest
exit /b %errorlevel%

:migrate
call :ensure_uv || exit /b 1
call :ensure_env || exit /b 1
uv run python manage.py migrate
exit /b %errorlevel%

:migrations
call :ensure_uv || exit /b 1
call :ensure_env || exit /b 1
uv run python manage.py makemigrations
exit /b %errorlevel%

:superuser
call :ensure_uv || exit /b 1
call :ensure_env || exit /b 1
uv run python manage.py createsuperuser
exit /b %errorlevel%

:seed
call :ensure_uv || exit /b 1
call :ensure_env || exit /b 1
uv run python manage.py seed_demo
exit /b %errorlevel%

:sync_ai
call :ensure_uv || exit /b 1
call :ensure_env || exit /b 1
uv run python manage.py sync_llm_config
exit /b %errorlevel%

:docker_up
where docker >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop is not installed or is not available in PATH.
  exit /b 1
)
call :ensure_env || exit /b 1
docker compose up --build -d
exit /b %errorlevel%

:docker_down
where docker >nul 2>nul || exit /b 1
docker compose down
exit /b %errorlevel%

:docker_logs
where docker >nul 2>nul || exit /b 1
docker compose logs -f web worker
exit /b %errorlevel%

:help
echo AAA EAs Builder
echo.
echo   dev.bat setup         Install dependencies, migrate, and seed demo data
echo   dev.bat web           Start the website at http://127.0.0.1:8000
echo   dev.bat worker        Start the Windows Celery worker
echo   dev.bat css-watch     Watch Tailwind styles
echo   dev.bat all           Start styles, worker, and website
echo   dev.bat test          Run tests
echo   dev.bat check         Run code and application checks
echo   dev.bat migrate       Apply database migrations
echo   dev.bat migrations    Create database migrations
echo   dev.bat superuser     Create a staff administrator
echo   dev.bat seed          Load safe fictional marketplace demo data
echo   dev.bat sync-ai       Sync the default Gemini gateway and model
echo   dev.bat docker-up     Build and start the Docker stack
echo   dev.bat docker-down   Stop the Docker stack without deleting data
echo   dev.bat docker-logs   Follow website and worker logs
exit /b 0

:help_error
call :help
exit /b 1
