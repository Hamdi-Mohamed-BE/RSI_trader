# Gold News AI

Prediction-only application for the immediate XAUUSD effect of high-impact USD
releases. Every supported release receives one result:

- `POSITIVE`: expected immediate effect on gold is upward.
- `NEGATIVE`: expected immediate effect on gold is downward.

It does not produce trade calls and cannot place, modify, or manage orders.

## Coverage

- Nonfarm Payrolls
- Advance GDP
- CPI
- PPI
- FOMC statements

The local archive contains XAUUSD M1 bid/ask release data from 2011 through
2026. The historical target is the sign of the release-minute midpoint move.
M1 data cannot identify the exact ordering of a sub-minute spike.

## Pipeline

1. Build canonical T-30 and T-15 XAUUSD features from completed M1 candles.
2. Compare four compact event-history rules on data before July 2021.
3. Approve a non-baseline event rule only when it also beats the baseline on
   the separate July 2021-July 2024 guard window.
4. Keep July 2024-July 2026 untouched as the final recent test.
5. Load Cleveland Fed inflation nowcasts and Atlanta Fed GDPNow history as
   context. Their decision weight remains zero until paired point-in-time
   consensus history proves an improvement.
6. Score every release as positive or negative; no selective abstention.

The deployed V2 policy uses anti-persistence for NFP and FOMC, and expanding
event history for GDP, CPI, and PPI. Larger market-feature models remain
disabled because they did not beat these compact rules on frozen data.

## Results

| Window | Events | Correct | Accuracy | 95% interval |
|---|---:|---:|---:|---:|
| Previous five-year baseline | 234 | 132 | 56.41% | 50.00-62.61% |
| V2 five-year replay | 234 | 143 | 61.11% | 54.73-67.13% |
| V2 recent untouched 2024-2026 | 92 | 59 | 64.13% | 53.95-73.18% |

The recent result is encouraging but not statistically conclusive. Full event
rows and model comparisons are in:

- `GOLD_DIRECTION_RESULTS.md`
- `gold_direction_backtest.json`
- `gold_direction_recent.csv`
- `GOLD_DIRECTION_5Y.md`
- `gold_direction_5y.json`
- `gold_direction_5y.csv`
- `GOLD_DIRECTION_V2.md`
- `gold_direction_v2.json`
- `gold_direction_v2.csv`

## Run

1. Run `train_model.bat` to rebuild models and reports.
2. Run `run.bat` to open `http://127.0.0.1:8799`.
3. Query a supported event 8-30 minutes before its UTC release time.

Each prediction is saved under `predictions/`. The optional post-release form
can compare actual, forecast, previous, revisions, and official release text.

## Data integrity

- Historical splits are chronological.
- Macro regime observations must be dated before the release day.
- Missing series are marked missing rather than backfilled from the future.
- Forecast/previous values entered live are stored point-in-time, but they are
  not used as historical model features until a licensed vintage archive exists.
- `economic_context.py` can cache Trading Economics point-in-time consensus
  history when `TRADING_ECONOMICS_API_KEY` is configured.
- `official_nowcasts.py` caches official Cleveland Fed and Atlanta Fed context.
- Unreleased statement text cannot improve a genuine pre-release prediction.

## Main artifacts

- `models/gold_news_direction.joblib`
- `backtest_gold_direction.py`
- `backtest_gold_direction_v2.py`
- `gold_direction_rules.py`
- `economic_context.py`
- `official_nowcasts.py`
- `macro_regime.py`
- `gold_direction_backtest.json`
- `GOLD_DIRECTION_RESULTS.md`
- `NEWS_IMPACT_PREDICTION_PROMPT.md`
- `CODEX_ANALYST_WORKFLOW.md`
