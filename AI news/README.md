# Gold News AI

## Weekend direction research

`run_weekend_direction_train.bat` builds a five-year XAUUSD weekend-direction
classifier. Model and threshold selection use expanding chronological folds in
the first four years; the final 52 weekends remain frozen for a one-time unseen
evaluation. `run_weekend_direction_predict.bat` produces an informational
Friday estimate and never sends an MT5 order.

Prediction-only application for the immediate XAUUSD effect of high-impact USD
releases. Every supported release receives one result:

- `POSITIVE`: expected immediate effect on gold is upward.
- `NEGATIVE`: expected immediate effect on gold is downward.
- `NO CALL`: the directional bias failed a confidence or agreement gate.

It does not produce trade calls and cannot place, modify, or manage orders.

## Weekend gap bot

The weekend-gap strategy is isolated from the prediction app. It places an OCO
buy-stop/sell-stop pair outside the final completed Friday M1 wick and removes
untriggered orders at the weekly reopen.

- Run the verified one-year optimization with `run_weekend_gap_backtest.bat`.
- Start the visible worker with `run_weekend_gap_bot.bat`.
- Its separate settings file is `.env.weekend-gap` (created from
  `.env.weekend-gap.example` on first launch).
- Both live switches default to `false`; test on demo before enabling them.

The current frozen-holdout defaults are a $1.50 offset, five-minute placement
lead, $20 stop, 4:1 reward/risk, and 720 market-minute maximum hold.

## Coverage

- Nonfarm Payrolls
- CPI
- FOMC statements

PPI and GDP remain in older research files but are intentionally disabled in
the live V5 predictor.

The local archive contains XAUUSD M1 bid/ask release data from 2011 through
2026. The historical target is the sign of the release-minute midpoint move.
M1 data cannot identify the exact ordering of a sub-minute spike.

## Pipeline

1. Build canonical T-30 and T-15 XAUUSD features from completed M1 candles.
2. Train expanding chronological price-action ensembles using NFP, CPI, and
   FOMC only.
3. Select NFP/CPI strategy, polarity, threshold, and optional history
   agreement on pre-2023 development data plus a separate 2023-May 2026 guard
   block.
4. Freeze May 8-August 7, 2026 as the three-month evaluation window.
5. Treat T-30 as preliminary context only. An active direction requires the
   final T-15 confidence and agreement gates.
6. Return `NO CALL` when any required gate fails.
7. For FOMC, combine the five-meeting history rule with a
   dedicated T-30 ExtraTrees model trained on prior FOMC meetings.
8. Call FOMC only when history and model agree, capped at 65% confidence.
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

The deployed V5 policy is event-specific. CPI can issue a `POSITIVE` gold call
only while both its long-run and recent positive regimes remain active. FOMC
keeps the isolated history/model agreement gate. NFP is shadow-bias only before
publication because no stable pre-release directional edge survived validation.
Forecast and previous values remain context-only because the repository does
not contain a licensed point-in-time historical consensus archive.

## Results

May 8-August 7, 2026 comparison:

| Policy | Events | Calls | Correct | Call accuracy | Coverage |
|---|---:|---:|---:|---:|---:|
| Legacy forced direction | 9 | 9 | 5 | 55.56% | 100.00% |
| V4 final T-15 | 9 | 1 | 1 | 100.00% | 11.11% |
| V5 final T-15 | 9 | 4 | 3 | 75.00% | 44.44% |

V5 improves practical coverage without reviving forced NFP guesses. Before the
three-month window, the CPI positive-regime rule was correct on 36/56 releases
and the frozen FOMC agreement rule on 23/35 calls, or 59/91 combined (64.84%).
In the recent replay V5 made four calls and won three. Its 95% interval remains
wide, so this is not proof of a stable 75% predictor.

V5 was designed after the May-August outcomes were available. The replay is
therefore retrospective rather than a pristine unseen holdout. Its next NFP,
CPI, and FOMC releases are the real forward validation.

The T-30 candidate scored 1/3 in this holdout and was not promoted.

Older V2 research results are retained below for comparison:

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

1. Run `run_news_v5_backtest.bat` to rebuild the V5 model and comparison report.
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

- `models/gold_news_v5.joblib`
- `news_v5.py`
- `backtest_news_v5.py`
- `NEWS_V5_3M_RESULTS.md`
- `news_v5_3m_results.json`
- `models/gold_news_v4.joblib`
- `news_v4.py`
- `backtest_news_v4.py`
- `NEWS_V4_3M_RESULTS.md`
- `news_v4_3m_results.json`
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

## Gold weekend direction V2

V2 is a prediction-only research model for the Friday-close to weekly-reopen
XAUUSD gap. It first estimates whether the gap will exceed the rolling 70th
percentile of the previous 26 weekend gaps, then estimates UP or DOWN.

Inputs are completed MT5 bars, lagged FRED macro observations, and CFTC gold
positioning lagged by a full week. The nested chronological replay independently
selects its feature set, regularization, and confidence gates in each unseen
block. A rejected model is hard-locked to `NO TRADE` in the live predictor.

- Run `run_weekend_direction_v2_backtest.bat` to refresh context and rebuild the report.
- Run `run_weekend_direction_v2_predict.bat` near Friday close for an estimate.
- Read `GOLD_WEEKEND_DIRECTION_V2.md` for the current validation verdict.
