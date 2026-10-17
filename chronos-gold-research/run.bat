@echo off
cd /d "%~dp0"
uv run --python 3.11 --with chronos-forecasting==2.3.2 --with pandas==3.0.6 --with torch==2.14.1 --with transformers==5.19.0 python benchmark.py
pause
