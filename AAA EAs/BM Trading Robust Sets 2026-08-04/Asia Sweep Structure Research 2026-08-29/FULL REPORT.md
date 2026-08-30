# Asia Sweep + Structure Shift — MT5 walk-forward validation

This is an objective implementation of the supplied rules, not the private LuxAlgo indicator. The Asia range is anchored to New York time with automatic US daylight-saving conversion.

## Locked last-year results

| Pair | Selected variant | Development return / PF | Locked return / PF | Win rate | Equity DD | Trades | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| AUDCHF | fast-20-00-max6-rr15 | -1.75% / 0.81 | +10.83% / 1.83 | 57.69% | 3.71% | 26 | WATCH — NOT ROBUST |
| GBPJPY | literal-20-00-max12-rr20 | +3.45% / 1.51 | +4.48% / 1.18 | 39.47% | 7.69% | 38 | WATCH — NOT ROBUST |
| AUDUSD | early-19-00-max12-rr15 | +1.74% / 1.42 | +0.71% / 1.07 | 43.75% | 4.09% | 16 | WATCH — NOT ROBUST |
| EURUSD | late-20-01-max12-rr15 | +12.74% / 3.15 | -0.31% / 0.95 | 45.45% | 3.20% | 11 | REJECT |
| NZDUSD | late-20-01-max12-rr15 | -1.06% / 0.00 | -1.94% / 0.75 | 36.36% | 5.86% | 11 | REJECT |
| GBPUSD | literal-20-00-be1-rr15 | +2.43% / 1.27 | -5.14% / 0.89 | 40.26% | 11.96% | 77 | REJECT |
| USDJPY | late-20-01-max12-rr15 | +21.82% / 1.54 | -10.98% / 0.72 | 36.51% | 13.46% | 63 | REJECT |
| USDCAD | fast-20-00-max6-rr15 | +3.17% / 1.40 | -18.18% / 0.64 | 32.86% | 22.59% | 70 | REJECT |
| USDCHF | fast-20-00-max6-rr15 | -7.10% / 0.69 | -27.71% / 0.69 | 35.51% | 27.93% | 138 | REJECT |

## Rules tested

- Build the Asia range from the selected New York evening window.
- Require a closed M5 candle to sweep an Asia boundary and reclaim it.
- Record the most recent confirmed internal swing, then enter only after a directional close breaks that structure within the allowed bar count.
- Stop beyond the sweep extreme plus 0.05 ATR; target 1.5R or 2R depending on the development variant.
- At most one trade per pair per day; close any remainder at 12:00 New York.

## Test integrity

- Broker: Exness MT5 Trial 16; native MT5 Every Tick model with random execution delay.
- Initial balance: $10,000; leverage 1:2000; calculated risk: 1% of current equity per trade.
- Development selection: 2024-08-29 through 2025-08-28. Untouched locked test: 2025-08-29 through 2026-08-28.
- MT5 spread, commission and swap are included. Results are historical research, not a profit guarantee.
- No active BAT or website file was changed by this research.
