# USD News Pending-Order Backtest

## Honest test design

- Window: 2024-07-31 through 2026-07-31 (93 scheduled events).
- Development/selection: 2024-07-31 through 2026-01-31.
- Locked holdout: 2026-01-31 through 2026-07-31.
- Event set: NFP, CPI, PPI, advance GDP, and FOMC statements.
- The range is the completed T-60 to T-31 window; orders are placed at T-30.
- Forecast BUY uses a buy-stop above the range; forecast SELL uses a broker-valid sell-stop at/below the 50% range level.
- OCO mode uses buy-stop above the range and sell-stop below the range; the first fill cancels the other side.
- Pending orders expire at T+15. Filled trades can run for at most 180 minutes.
- Bid/ask candles drive triggers and exits. Spread buffers move only farther from price before release.
- Same-minute ambiguity is pessimistic: SL wins ties and entry-bar TP is not credited.
- Metrics assume 1% compounded risk per filled leg from a normalized $10,000 account.
- EURUSD uses 1 pip = 0.0001. XAUUSD uses the common 0.10 quote convention, so 90 pips is a $9 stop.
- A literal XAU 0.01-pip/$0.90-stop stress test is retained separately; it is not used to select the strategy.
- Event families are retained using development data only: at least 8 trades, PF >= 1.30, and positive net R.

## Selected results

| Symbol | Period | Mode | RR | Re-entry | Trades | Win rate | PF | Net R | Max DD | Return |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EURUSD filter | all | NFP,CPI,PPI | - | - | - | - | - | - | - | - |
| EURUSD | development | forecast | 3 | no | 38 | 57.9% | 2.29 | 5.79 | 1.17% | 5.90% |
| EURUSD | holdout | forecast | 3 | no | 8 | 87.5% | 9.60 | 1.21 | 0.14% | 1.22% |
| EURUSD | full | forecast | 3 | no | 46 | 63.0% | 2.51 | 7.00 | 1.17% | 7.19% |
| EURUSD | unfiltered full | forecast | 3 | no | 66 | 56.1% | 1.67 | 6.13 | 2.66% | 6.24% |
| XAUUSD filter | all | PPI | - | - | - | - | - | - | - | - |
| XAUUSD | development | oco | 5 | yes | 20 | 45.0% | 3.07 | 16.05 | 3.09% | 16.87% |
| XAUUSD | holdout | oco | 5 | yes | 4 | 50.0% | 2.89 | 3.78 | 1.22% | 3.72% |
| XAUUSD | full | oco | 5 | yes | 24 | 45.8% | 3.03 | 19.83 | 3.09% | 21.21% |
| XAUUSD | unfiltered full | oco | 5 | yes | 106 | 23.6% | 1.03 | 1.91 | 12.89% | 0.06% |

## Gold pip-size stress test

The same selected XAUUSD rules with a literal 0.01 pip ($0.90 stop) produced 29 trades, 0.00 PF, -63.83R, and 47.82% maximum drawdown. That interpretation is rejected because news gaps and spread are too large relative to the stop.

## Combined selected configurations

- Trades: 70
- Win rate: 57.14%
- Profit factor: 2.87
- Net: 26.83R
- Maximum drawdown: 2.93%
- Normalized balance: $10,000.00 -> $12,993.38
- Locked holdout: 12 trades, 75.00% win rate, 3.33 PF, 5.00R, 1.13% max DD.

This is a historical execution simulation, not a guarantee. One-minute candles cannot reconstruct tick order inside a candle, so ambiguous fills are handled against the strategy.
