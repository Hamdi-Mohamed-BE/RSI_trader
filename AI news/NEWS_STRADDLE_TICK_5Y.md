# XAUUSD Tick-Level News Straddle Study

## Honest answer first

No pending-order offset can guarantee a win on every news release. A stop order becomes a market order after triggering, so a release gap can fill beyond the requested price. Fast reversals can also fill both sides before the second order is cancelled.

## Test design

- Window: 2021-08-01 through 2026-08-01.
- Usable tick windows: 227 of 236 scheduled events; 9 windows had no tick data.
- Development: 2021-08-01 through 2025-08-01; locked holdout: 2025-08-01 through 2026-08-01.
- Events: NFP, CPI, PPI, advance GDP, and FOMC statements.
- Both buy-stop and sell-stop are placed from the latest bid/ask at T-60s, T-30s, or T-10s.
- The first fill attempts to cancel the other order after 250 ms. Both fills count when the opposite trigger occurs first.
- Dukascopy bid/ask ticks drive placement, triggers, spread, slippage, OCO collisions, and exits through T+5. Bid/ask M1 extends exits to T+60; same-bar ties lose.
- Parameters were selected only on the first four years. The last year was not used for selection.

## One configuration across all events

- Overall verdict: **REJECTED - no universal edge survived the locked holdout**
- Placement: **T-10 seconds**
- Buy stop: **max($0.25, live spread x 1.5) above ask**
- Sell stop: **max($1.00, live spread x 1.5) below bid**
- Stop loss: **$12.00**
- Take profit: **$7.00** (0.58R)
- Unfilled-order expiry: **T+30 seconds**
- Development-only robustness gate: **passed**

| Period | Events traded | Fill rate | Win rate | Target hit | PF | Net R | Max DD | Dual fill | Pre-release fill |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Development | 181 | 97.8% | 60.8% | 53.6% | 1.21 | 8.64 | 4.41R | 2.8% | 21.0% |
| Locked holdout | 40 | 95.2% | 45.0% | 47.5% | 0.36 | -14.96 | 16.35R | 2.5% | 37.5% |
| Full five years | 221 | 97.4% | 57.9% | 52.5% | 0.90 | -6.33 | 17.38R | 2.7% | 24.0% |

## Universal configuration by event

| Event | Trades | Win rate | PF | Net R | Max DD | Dual fill |
|---|---:|---:|---:|---:|---:|---:|
| NFP | 54 | 70.4% | 1.28 | 3.66 | 3.46R | 1.9% |
| CPI | 58 | 55.2% | 0.78 | -4.76 | 10.09R | 6.9% |
| PPI | 56 | 39.3% | 0.45 | -9.89 | 10.48R | 0.0% |
| GDP | 18 | 66.7% | 2.94 | 3.87 | 0.54R | 5.6% |
| FOMC | 35 | 68.6% | 1.08 | 0.79 | 4.47R | 0.0% |

## Event-specific development selections

These are research comparisons, not five independent promises. GDP has the smallest sample and the greatest overfitting risk.

| Event | Lead | Buy offset | Sell offset | SL | TP | Holdout trades | Holdout PF | +$0.25 slip PF | Holdout net R | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| NFP | T-10s | $4.00 | $1.50 | $12.00 | $7.00 | 9 | 1.27 | 1.14 | 0.76 | paper-test only |
| CPI | T-10s | $0.50 | $4.00 | $12.00 | $4.00 | 11 | 0.88 | 0.77 | -0.40 | reject |
| PPI | T-30s | $0.25 | $0.75 | $5.00 | $5.00 | 11 | 0.70 | 0.58 | -2.36 | reject |
| GDP | T-60s | $1.00 | $0.50 | $5.00 | $5.00 | 3 | 0.44 | 0.37 | -1.33 | reject |
| FOMC | T-10s | $0.25 | $1.50 | $7.00 | $30.00 | 7 | 0.00 | 0.00 | -11.02 | reject |

## Timing sensitivity on the locked holdout

| Placement | Trades | Win rate | PF | Net R | Max DD |
|---|---:|---:|---:|---:|---:|
| T-60s | 41 | 63.4% | 1.09 | 1.36 | 3.89R |
| T-30s | 41 | 68.3% | 0.99 | -0.11 | 4.82R |
| T-10s | 40 | 45.0% | 0.36 | -14.96 | 16.35R |

## Execution stress on the locked holdout

| Stress | Trades | Win rate | PF | Net R | Max DD | Dual fill |
|---|---:|---:|---:|---:|---:|---:|
| $0.25 adverse entry and exit slippage | 40 | 45.0% | 0.32 | -16.67 | 17.93R | 2.5% |
| $0.50 adverse entry and exit slippage | 40 | 42.5% | 0.28 | -18.38 | 19.52R | 2.5% |
| 500 ms opposite-order cancellation | 40 | 45.0% | 0.36 | -15.21 | 16.60R | 5.0% |

## Interpretation

The locked holdout is the result that matters. If it is weak, the attractive development result is curve fitting. Even a positive holdout is only one year and must be forward-tested on the intended broker because release spread, stop-order slippage, minimum stop distance, and OCO cancellation latency differ from Dukascopy.

The universal configuration failed that test: its locked-holdout PF was below 1, its stress results worsened, and only NFP and GDP were profitable over the full sample. There is no deployable all-event straddle in this search space.

NFP is the only event-specific candidate that remained positive in the locked holdout, but its edge fell to approximately break-even under $0.50 adverse entry and exit slippage. It is suitable only for broker-specific paper testing, not live promotion.
