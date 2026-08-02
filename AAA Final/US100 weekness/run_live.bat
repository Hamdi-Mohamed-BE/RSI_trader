@echo off
cd /d "%~dp0"

echo ============================================================
echo  CHECKING CONNECTED MT5 ACCOUNT AND AUTO-DISCOVERING US100
echo ============================================================
uv run nasdaq-weakness account
if errorlevel 1 (
    echo.
    echo ERROR: MT5 account connection or symbol discovery failed.
    echo Keep the Exness MT5 terminal open and logged in, then try again.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  ACCOUNT CHECK PASSED - STARTING LIVE WORKER
echo ============================================================
uv run nasdaq-weakness live
pause
