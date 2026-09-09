@echo off
setlocal
title Calyx - Ava EAs
echo.
echo ============================================================
echo   CALYX AVA EAS - PF 1.40+ WITH DMC FUTURES DEMO
echo ============================================================
echo   Minimum broker contract sizing. No 1%% risk is forced.
echo   Ava netting protection is enabled.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Ava Futures Portfolio Research 2026-09-09\Install-AvaFuturesTop10.ps1"
if errorlevel 1 (
  echo.
  echo Ava EAs installation did not finish. Read the message above.
) else (
  echo.
  echo Ava EAs installation finished successfully.
)
pause
endlocal
