# LTA mechanical EA — honest one-year results

## Test design

- Initial deposit: USD 10,000 per independent test
- Optimization/training window: 2024-08-05 through 2025-08-04
- Final untouched test window: 2025-08-05 through 2026-08-04
- Final model: MT5 Every Tick (generated ticks), random execution delay, MEXAtlantic-Demo contract specifications
- Position sizing: 2.5% of current equity at the initial stop; the EA skips a trade if the broker's minimum lot would exceed that risk
- Risk control: one position per symbol and stop for the day after two consecutive losing exits
- No final-year settings were selected using final-year results

## Final out-of-sample results

| Verdict | Market / broker symbol | Best training TF | Entry configuration | RR | Trades | Win rate | PF | Net profit | Return | Final balance | Max equity DD | History quality |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PASS, research only | XAU / `XAUUSD..` | M15 | EM1 + EM4, SD + PD/PW, no swing profile, volume >= 1.0x | 3.0 | 216 | 33.80% | 1.32 | $37,792.29 | +377.92% | $47,792.29 | 26.66% | 100% |
| FAIL | BTC / `BTCUSD` | M30 | EM1 + EM3 + EM4, SD + PD/PW, no swing profile, volume >= 1.2x | 3.0 | 132 | 25.00% | 0.92 | -$1,630.32 | -16.30% | $8,369.68 | 50.95% | 94% |
| FAIL | EURUSD / `EURUSD..` | H1 | EM1, SD + PD/PW, no swing profile, volume >= 1.2x | 3.0 | 89 | 19.10% | 0.62 | -$4,894.79 | -48.95% | $5,105.21 | 51.44% | 100% |
| FAIL | GBPJPY / `GBPJPY..` | M30 | EM3 + EM4, SD + PD/PW + swing profile, volume >= 0.8x | 2.5 | 106 | 26.42% | 0.86 | -$2,970.46 | -29.70% | $7,029.54 | 48.46% | 100% |
| FAIL | US30 / `US30` | M15 | EM1, SD + PD/PW + swing profile, volume >= 1.2x | 2.5 | 234 | 29.06% | 0.95 | -$2,029.12 | -20.29% | $7,970.88 | 40.76% | 100% |
| FAIL | US100 / `UT100` | M15 | EM4, SD + PD/PW + swing profile, volume >= 0.8x | 2.5 | 208 | 26.92% | 0.86 | -$4,202.74 | -42.03% | $5,797.26 | 59.18% | 100% |

## Interpretation

Only XAU was profitable in the untouched year. It also carried 26.66% maximum equity drawdown, so it is not a low-drawdown or prop-firm-safe result. The +377.92% return is a compounded historical simulation at an aggressive 2.5% risk per trade; it is not a forecast or guarantee.

XAU sensitivity tests using the independently selected training winners on M30 and H1 remained profitable (+56.96% and +36.20%), but their profit factors were only 1.09 and 1.10 and their drawdowns were 52.38% and 47.97%. M15 was therefore the only reasonable research candidate.

A separate XAU “real ticks” sensitivity run produced +$32,707.30 (+327.07%), PF 1.27, 33.49% wins, 215 trades and 26.92% max equity drawdown. The broker report contained only **28% real-tick coverage**, so this is supporting evidence, not a valid complete real-tick-year result. Its native report is saved beside the main reports.

The five failed presets are saved only so the work is reproducible. Their filenames contain `OOS FAIL`; do not run them live.
