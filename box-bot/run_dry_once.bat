@echo off
setlocal
cd /d "%~dp0"
python box_bot.py --once --dry-run
endlocal
