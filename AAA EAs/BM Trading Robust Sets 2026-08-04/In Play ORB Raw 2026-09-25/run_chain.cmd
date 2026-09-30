@echo off
rem 2026-09-25: in-play ORB study. Waits for the EMA/VWAP chain to finish (one tester at a time), then
rem screen (Model 1) -> report/gate (writes native\ADVANCE.json) -> Model 4 confirmation of survivors -> report.
rem Detached so it survives the Claude session ending. Isolated tester only.
set EA_STORE_DISABLE_MT5=1
set PYTHONIOENCODING=utf-8
set B=C:\Users\hama101\Desktop\geek\ai trader\AAA EAs\BM Trading Robust Sets 2026-08-04
set PREV=%B%\Nasdaq 5M Index Transfer 2026-09-25\native\chain.log
:wait
findstr /C:"CHAIN DONE" "%PREV%" >nul 2>&1
if errorlevel 1 (timeout /t 30 /nobreak >nul & goto wait)
timeout /t 20 /nobreak >nul
cd /d "%B%\In Play ORB Raw 2026-09-25"
python run_ip.py screen summary >> native\run.log 2>&1
python make_report.py > native\report-screen.log 2>&1
python run_ip.py confirm summary >> native\run.log 2>&1
python make_report.py > native\report-final.log 2>&1
echo IP CHAIN DONE >> native\chain.log
