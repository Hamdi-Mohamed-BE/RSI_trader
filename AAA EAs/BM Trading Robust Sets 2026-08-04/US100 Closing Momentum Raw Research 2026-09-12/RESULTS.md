# US100 Closing Momentum — raw comparison

## Decision

Do not run the full pipeline yet. The raw closing-momentum signal is mildly profitable in the latest six and twelve months, but it is negative over the valid three- and five-year samples. The active Nasdaq Overnight strategy is stronger in every tested window.

## Raw rule

- Instrument: Exness `USTEC` (US100 CFD).
- At 15:30 New York, calculate the return from the previous 16:00 New York cash close.
- Buy when that return is positive and sell when it is negative.
- Exit at 16:00 New York on the same day.
- No take profit, trailing stop, breakeven, trend filter, regime filter, weekday optimization, or parameter optimization.
- Common Calyx execution wrapper: USD 10,000 initial balance, 1% equity risk sized against a 2% emergency price stop, broker spread and commission, and random execution delay.
- Exness `USTEC` does not provide the required 15:30–16:00 New York trading window during New York standard-time months, so those dates are skipped instead of being converted accidentally into overnight positions.

The signal comes from Baltussen, Da, Lammers and Martens (2021), *Hedging demand and market intraday momentum*: https://academicweb.nd.edu/~zda/intramom.pdf

## Side-by-side results

| Window | Closing momentum return | PF | Win rate | Max DD | Trades | Nasdaq Overnight return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 months | +1.83% | 1.48 | 59.41% | 0.90% | 101 | +5.88% | 1.63 | 62.07% | 2.38% | 58 |
| 1 year | +1.29% | 1.24 | 52.99% | 1.13% | 134 | +8.28% | 1.80 | 62.50% | 2.40% | 72 |
| 3 years | -2.72% | 0.84 | 50.60% | 4.82% | 334 | +7.77% | 1.29 | 55.62% | 4.86% | 178 |
| 5 years | -3.20% | 0.83 | 49.86% | 5.64% | 369 | +8.40% | 1.28 | 56.28% | 4.83% | 199 |

## Evidence quality and costs

| Window | Closing-momentum basis | History quality | Commission | Swap | Data-quality exclusions |
|---|---|---:|---:|---:|---:|
| 6 months | Native MT5 Every Tick | 100% | -$11.70 | $0.00 | 0 |
| 1 year | Native MT5 Every Tick | 100% | -$15.97 | $0.00 | 0 |
| 3 years | Native MT5 M1 OHLC; valid same-session trades only | 98% | -$48.31 | $0.00 | 47 stale-exit artifacts |
| 5 years | Native MT5 M1 OHLC; valid same-session trades only | 98% | -$54.95 | $0.00 | 59 stale-exit artifacts |

Spread is embedded in MT5 entry and exit prices, so it is not reported as a separate cash line. The long-window Exness real-tick archive has gaps. When a test position could not receive a quote for its scheduled close within one hour, that position was excluded from the clean intraday sample; otherwise a missing-data artifact would masquerade as an overnight trade and add swap. The active Overnight figures are the website's saved native MT5 Every Tick evidence for the same date windows.

## Interpretation

- Closing momentum has lower drawdown in the recent six- and twelve-month windows, but the return advantage is far too small to compensate for the weaker PF and unstable long-window edge.
- The three- and five-year valid samples lose after costs, with PF below 1.00.
- Nasdaq Overnight wins all four windows on return, PF, win rate, and long-window consistency.
- No website, BAT, portfolio, or active MT5 configuration was changed.
