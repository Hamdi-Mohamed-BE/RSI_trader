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
7. For FOMC only, combine the validated five-meeting history rule with a
   dedicated T-30 ExtraTrees model trained on prior FOMC meetings.
8. Mark history/model agreement as high confidence, capped at 65%. Mark
   disagreements as low confidence.
9. Optionally resolve an FOMC disagreement with a point-in-time FedWatch
   distribution from a 50bp cut through a 50bp hike. The modal target is
   compared with the probability-weighted target; this resolver is capped at
   60% and refuses near-tied distributions.
10. Treat the statement and the press conference 30 minutes later as separate
    shocks. A deterministic post-release statement diff can compare two
    official Federal Reserve statement URLs.
11. Audit FOMC behavior against the official San Francisco Fed U.S. Monetary
    Policy Event-Study Database. Current-meeting shock values are labels only;
    the model can use earlier shocks, never the shock it is trying to predict.

The deployed V2 policy uses anti-persistence for NFP and expanding event
history for GDP, CPI, and PPI. FOMC uses its isolated ensemble. Larger
market-feature models remain disabled for the other events because they did
not beat the compact rules on frozen data.

## Results

| Window | Events | Correct | Accuracy | 95% interval |
|---|---:|---:|---:|---:|
| Previous five-year baseline | 234 | 132 | 56.41% | 50.00-62.61% |
| V2 five-year replay | 234 | 143 | 61.11% | 54.73-67.13% |
| V2 recent untouched 2024-2026 | 92 | 59 | 64.13% | 53.95-73.18% |

FOMC agreement calls were 13/17 correct (76.47%) in the 2021-2026 rolling
replay, covering 42.5% of meetings. The stricter frozen-block test produced
24/36 (66.67%) with 45.57% coverage, including one weak 45.45% block. The
live confidence cap is therefore 65%. A complete
point-in-time FedWatch history is not bundled; the pricing resolver is
implemented but is not presented as historically validated.

The added policy-regime candidate reached 18/25 (72.00%) in frozen blocks at
31.65% coverage, compared with 24/36 (66.67%) for the deployed agreement rule.
It was not promoted: its 2019-2021 block was only 40.00%, and its expanding
walk-forward replay fell to 13/23 (56.52%). The deployed FOMC rule therefore
remains unchanged. This avoids replacing a modest edge with a result that only
looks better under one test schedule.

The FOMC architecture was designed after reviewing the July 29, 2026 miss.
Historical events are still replayed without future-event leakage, but this is
a retrospective test rather than a pristine untouched holdout.

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
- `FOMC_PIPELINE_RESULTS.md`
- `fomc_pipeline_backtest.json`
- `fomc_pipeline_backtest.csv`
- `FOMC_FROZEN_HOLDOUT.md`
- `fomc_frozen_holdout.json`
- `fomc_frozen_holdout.csv`
- `FOMC_REGIME_BACKTEST.md`
- `fomc_regime_backtest.json`
- `FOMC_REGIME_WALKFORWARD.md`
- `fomc_regime_walkforward.json`
- `NEWS_V3_RESULTS.md`
- `news_v3_results.json`
- `news_v3_results.csv`

## V3 impulse-gate research

V3 fixes a structural research flaw in the older selective-call experiment:
`UNCERTAIN` releases are now included when fitting a dedicated
`IMPULSE`/`NO IMPULSE` model. Direction remains a separate BUY/SELL model.

The strict two-stage candidate was rejected because it made zero calls in the
frozen May 30-July 30, 2026 test. A safer hybrid was then tested:

- The validated V2 direction policy decides whether a call exists.
- The impulse model may veto a call, but can never create one.
- A veto requires at least 20 historical direction calls, at least a
  7.5-percentage-point accuracy lift, and retention of at least 90% of calls.
- An out-of-distribution distance gate is evaluated before deployment.
- T-30 remains context; T-15 remains the final decision.
- Five- and fifteen-minute outcomes are stored only as diagnostics.

Those safeguards left every veto disabled. The frozen result therefore matched
V2 exactly: 2/8 calls, 2/2 correct, and +8,680 XAUUSD pips. V3 is not promoted
because it did not strictly improve a frozen metric. Its candidate artifact is
saved separately at `models/gold_news_v3_candidate.joblib`.

## Run

1. Run `train_model.bat` to rebuild models and reports.
2. Run `run.bat` to open `http://127.0.0.1:8799`.
3. Query a supported event 8-30 minutes before its UTC release time.
4. For FOMC, optionally enter the current target range and the point-in-time
   probabilities from a 50bp cut through a 50bp hike.

Run `uv run python refresh_usmpd.py` to refresh the official SF Fed event-study
workbook and monetary-policy-surprise history before rerunning FOMC research.

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
- FedWatch snapshots must be observed before the meeting. Same-meeting survey
  results or revised probabilities collected after publication are prohibited.
- SF Fed statement and press-conference surprises are post-release outcomes.
  They are used for labels and lagged regime history, not current predictions.
- The included July 29, 2026 pricing row is a forensic example, not a
  validation sample.

## Main artifacts

- `models/gold_news_direction.joblib`
- `backtest_gold_direction.py`
- `backtest_gold_direction_v2.py`
- `gold_direction_rules.py`
- `fomc_pipeline.py`
- `backtest_fomc_pipeline.py`
- `backtest_fomc_frozen_holdout.py`
- `fomc_regime.py`
- `backtest_fomc_regime.py`
- `backtest_fomc_regime_walkforward.py`
- `refresh_usmpd.py`
- `economic_context.py`
- `official_nowcasts.py`
- `macro_regime.py`
- `news_v3.py`
- `backtest_news_v3.py`
- `gold_direction_backtest.json`
- `GOLD_DIRECTION_RESULTS.md`
- `NEWS_IMPACT_PREDICTION_PROMPT.md`
- `CODEX_ANALYST_WORKFLOW.md`
