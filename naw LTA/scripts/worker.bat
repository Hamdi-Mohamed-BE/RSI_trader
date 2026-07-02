@echo off
cd /d "%~dp0\.."
title NAW LTA Celery Worker
echo NAW LTA background worker is starting.
echo Closing this window stops scans and backtests.
uv run celery -A naw_lta.celery_app:celery_app worker --loglevel=INFO --pool=solo --queues=celery
echo.
echo Worker stopped.
pause

