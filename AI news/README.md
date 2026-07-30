# Gold News AI

Prediction-only research and query application for the immediate XAUUSD reaction
to high-impact USD releases. It cannot place, modify, or manage trades.

The complete specification is saved in
`NEWS_IMPACT_PREDICTION_PROMPT.md`.

The concise initial validation report is saved in `FINAL_RESULTS.md`; complete
metrics and individual holdout predictions remain available in the JSON and CSV
outputs listed below.

## Current model coverage

- CPI
- PPI
- Nonfarm Payrolls
- Advance GDP
- FOMC statements

The local archive contains 716 release records and XAUUSD M1 bid/ask data from
2011-07-30 through 2026-07-29. Models are trained independently for predictions
made 15 and 30 minutes before release. The historical target is the sustained
release-minute direction; one-minute OHLC cannot establish the ordering of a
sub-minute spike.

## Run

1. Run `train_model.bat` to rebuild the walk-forward models and report.
2. Run `run.bat` to open the query application at `http://127.0.0.1:8799`.
3. Query only 8-40 minutes before a release. Every result is permanently saved
   under `predictions/` before the release.
4. Run `monitor_release.bat` with that saved JSON file to capture ticks for the
   first 30 seconds and sustained movement through 15 minutes.

Automatic upcoming-event discovery is available through `/api/upcoming` after
setting a licensed `TRADING_ECONOMICS_API_KEY`. Without that key, event and UTC
release time are entered manually and the missing provider is reported clearly.

## Honest limitations

- The current archive has one-minute prices, so it cannot report a genuine
  millisecond or 30-second impulse.
- Point-in-time consensus, actual, revisions, DXY, Treasury yields, and
  positioning are not present locally. The application marks these inputs
  missing rather than inventing them.
- Unsupported events return `NO TRADE`.
- A licensed historical calendar feed is required before surprise features can
  be trained without look-ahead bias.

## Outputs

- `models/gold_news_impulse_15m.joblib`
- `models/gold_news_impulse_30m.joblib`
- `backtest_report.json`
- `backtest_validation_predictions.csv`
- `predictions/*.json`
