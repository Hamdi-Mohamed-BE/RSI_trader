@echo off
cd /d "%~dp0\.."
title NAW LTA Scheduler
echo NAW LTA scheduler is starting.
echo Closing this window stops periodic scan scheduling.
uv run celery -A naw_lta.celery_app:celery_app beat --loglevel=INFO --schedule=data\celerybeat-schedule
echo.
echo Scheduler stopped.
pause

