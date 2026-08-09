@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" news_event_offset_study.py --years 5 --horizon-minutes 30
) else (
  python news_event_offset_study.py --years 5 --horizon-minutes 30
)

echo.
echo Results: reports\news-offset-study\REPORT.md
pause
