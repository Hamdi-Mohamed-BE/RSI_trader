@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required. Install it from https://docs.astral.sh/uv/
  pause
  exit /b 1
)

uv sync
if errorlevel 1 goto :failed
uv run python train_news_model.py
if errorlevel 1 goto :failed
uv run python backtest_max_walkforward.py
if errorlevel 1 goto :failed
uv run python backtest_gold_direction.py
if errorlevel 1 goto :failed
uv run python backtest_gold_direction_5y.py
if errorlevel 1 goto :failed
uv run python backtest_gold_direction_v2.py
if errorlevel 1 goto :failed
uv run python backtest_fomc_pipeline.py
if errorlevel 1 goto :failed
uv run python backtest_fomc_frozen_holdout.py
if errorlevel 1 goto :failed
uv run python backtest_fomc_regime.py
if errorlevel 1 goto :failed
uv run python backtest_fomc_regime_walkforward.py
if errorlevel 1 goto :failed
uv run python backtest_news_v4.py
if errorlevel 1 goto :failed
uv run python backtest_news_v5.py
if errorlevel 1 goto :failed
uv run python official_nowcasts.py
if errorlevel 1 echo Official nowcast refresh skipped; the validated model is still ready.

echo.
echo V5 NFP/CPI/FOMC model and legacy research reports completed.
pause
exit /b 0

:failed
echo.
echo Training failed. Review the message above.
pause
exit /b 1
