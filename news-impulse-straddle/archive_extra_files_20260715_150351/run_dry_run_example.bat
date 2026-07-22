@echo off
cd /d "%~dp0"
python news_straddle_bot.py --news-time "2026-07-15 12:30" --dry-run
pause

