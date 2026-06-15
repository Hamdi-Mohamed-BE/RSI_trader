@echo off
cd /d "%~dp0"
python parabolic_sar_bot.py --once --dry-run --no-state-write
pause
