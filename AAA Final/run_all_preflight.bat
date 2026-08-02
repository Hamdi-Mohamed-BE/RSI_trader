@echo off
cd /d "%~dp0"

echo ============================================================
echo  ALL BOT PREFLIGHT - NO ORDERS WILL BE SUBMITTED
echo ============================================================
uv run --project "asia breakout" python audit_all_bots.py
if errorlevel 1 (
    echo.
    echo PREFLIGHT FAILED. Do not start the bots until the issue is fixed.
    pause
    exit /b 1
)

echo.
echo PREFLIGHT PASSED.
pause
