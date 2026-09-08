# Weekend Gap Reversal — Raw Paper Backtest

Research only. Not added to the recommended BAT or website catalogue.

## Fixed rules

- W1 broker bars; current incomplete week excluded.
- Five-year (260-week) rolling gap distribution with no look-ahead.
- Trade against gaps in the bottom/top 5% and exit at the weekly close.
- 0.08% round-trip cost deducted from every trade.
- Raw paper rule has no stop-loss. Returns below use 1x notional exposure and are not a 1%-risk EA simulation.

## Results

| Pair | Test period | Trades | Win rate | PF | Return | CAGR | Max DD | Sharpe | Avg trade | Max W/L streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | 2019-01-13 to 2026-09-04 | 41 | 48.78% | 1.42 | +7.78% | +0.99% | 4.41% | 0.29 | +0.19% | 5/4 |
| GBPUSD | 2019-01-13 to 2026-09-04 | 41 | 48.78% | 1.44 | +10.12% | +1.27% | 6.83% | 0.29 | +0.26% | 7/4 |
| NZDUSD | 2019-01-13 to 2026-09-04 | 44 | 52.27% | 1.18 | +5.04% | +0.65% | 10.42% | 0.15 | +0.13% | 5/4 |
| GBPJPY | 2019-01-13 to 2026-09-04 | 36 | 44.44% | 0.55 | -9.57% | -1.31% | 13.43% | -0.42 | -0.27% | 5/5 |

## Decision

The raw rule is not deployment-ready because it has no stop-defined 1% risk model and the sample is small. Pairs with PF above 1 may proceed to a separate MT5 EA engineering and walk-forward stage only after review; failing pairs stay excluded.
