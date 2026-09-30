@echo off
rem 2026-09-25: resume the Nasdaq 5M index-transfer study, then the EMA/VWAP US100 M3 study, one after another.
rem Detached so it survives the Claude session ending. Isolated tester only; runners skip completed cases.
set EA_STORE_DISABLE_MT5=1
set PYTHONIOENCODING=utf-8
set B=C:\Users\hama101\Desktop\geek\ai trader\AAA EAs\BM Trading Robust Sets 2026-08-04
cd /d "%B%\Nasdaq 5M Index Transfer 2026-09-25"
python run_idx.py main summary >> native\run.log 2>&1
echo index exit %ERRORLEVEL% >> native\chain.log
cd /d "%B%\EMA VWAP Pullback Raw 2026-09-25"
python run_ev.py main control summary >> native\run.log 2>&1
echo emavwap exit %ERRORLEVEL% >> "%B%\Nasdaq 5M Index Transfer 2026-09-25\native\chain.log"
echo CHAIN DONE >> "%B%\Nasdaq 5M Index Transfer 2026-09-25\native\chain.log"
