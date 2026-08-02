# XAUUSD News-Pulse Offset Study

## Test design

- Window: 2021-08-01 through 2026-08-01 (236 scheduled USD events).
- Development: 2021-08-01 through 2025-08-01 (192 events).
- Locked holdout: 2025-08-01 through 2026-08-01 (44 events).
- Events: NFP, CPI, PPI, advance GDP, and FOMC statements.
- Direction comes from the frozen T-30 gold-impact prediction archive.
- Entry is a stop in the predicted direction, anchored to the T-2 completed M1 close.
- Orders are armed at T-1, expire at T+3, use a 90-pip stop and 3R target, and close by T+60.
- Bid/ask candles model spread, gaps, fills, stops, and exits.
- Same-bar uncertainty is pessimistic: the stop wins and entry-bar TP is not credited.

## Selected offset

**Use max(8 gold pips, live spread x 1.0).**
With 1 gold pip = $0.10, the fixed floor is $0.80.
The actual median effective offset was 8.0 pips ($0.80).

## Results

| Period | Trades | Fill rate | Win rate | PF | Net R | Max DD | 1R continuation | Snapback |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Development | 140 | 86.4% | 50.0% | 1.27 | 14.62 | 10.40R | 40.0% | 21.4% |
| Locked holdout | 33 | 91.7% | 36.4% | 1.30 | 6.30 | 8.77R | 54.5% | 27.3% |
| Full five years | 173 | 87.4% | 47.4% | 1.28 | 20.91 | 10.40R | 42.8% | 22.5% |

## $800 account at 3% risk

- Ending balance: $1332.97
- Return: 66.62%
- Maximum compounded drawdown: 27.30%

## Event breakdown

| Event | Trades | Win rate | PF | Net R | Max DD |
|---|---:|---:|---:|---:|---:|
| NFP | 47 | 55.3% | 1.99 | 16.68 | 3.00R |
| CPI | 46 | 50.0% | 1.46 | 9.80 | 5.72R |
| PPI | 40 | 40.0% | 0.58 | -6.64 | 8.16R |
| GDP | 14 | 42.9% | 1.29 | 1.82 | 3.08R |
| FOMC | 26 | 42.3% | 0.95 | -0.73 | 6.00R |

## Neighboring offsets

| Fixed offset | Development PF | Development net R | Holdout PF | Holdout net R | Holdout snapback |
|---:|---:|---:|---:|---:|---:|
| 0 pips | 1.25 | 14.03 | 1.43 | 9.10 | 27.3% |
| 5 pips | 1.25 | 14.02 | 1.43 | 9.09 | 27.3% |
| 8 pips | 1.27 | 14.62 | 1.30 | 6.30 | 27.3% |
| 10 pips | 1.24 | 12.86 | 1.30 | 6.21 | 24.2% |
| 12 pips | 1.21 | 11.09 | 1.41 | 8.65 | 24.2% |
| 15 pips | 1.12 | 6.33 | 1.49 | 9.74 | 24.2% |
| 20 pips | 1.10 | 4.80 | 1.47 | 9.45 | 21.9% |
| 30 pips | 0.97 | -1.20 | 1.33 | 6.32 | 13.8% |
| 40 pips | 0.93 | -3.01 | 1.84 | 12.65 | 7.7% |

## Interpretation

Offsets around 5-10 pips formed the best development-period plateau. Larger fixed offsets reduced some snapbacks, but they entered after more of the impulse was already spent and lost money in development. Eight pips is the selected compromise, not a guarantee against reversal.

This remains an M1 historical simulation, not a guarantee. Tick data is required to know the exact order of prices inside the release candle.
