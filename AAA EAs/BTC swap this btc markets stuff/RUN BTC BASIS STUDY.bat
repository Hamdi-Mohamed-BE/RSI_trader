@echo off
setlocal EnableExtensions DisableDelayedExpansion
title BTC Spot - CME Futures Basis Research
cd /d "%~dp0"
echo.
echo BTC SPOT - CME FUTURES BASIS RESEARCH
echo -------------------------------------
echo This runs a historical research study only. It does not connect to a broker.
echo.
uv sync --dev
if errorlevel 1 goto :failed
uv run pytest
if errorlevel 1 goto :failed
uv run python scripts\run_study.py
if errorlevel 1 goto :failed
echo.
echo SUCCESS: review the Results folder.
pause
exit /b 0

:failed
echo.
echo FAILED: inspect the message above. No trades were placed.
pause
exit /b 1

