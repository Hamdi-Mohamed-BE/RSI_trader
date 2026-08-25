# US100 5-Minute Open EMA/ATR — Literal Hold Validation

## Honest decision

The literal strategy is profitable on the available Exness `USTEC` history, but the advertised **+406% return with roughly 19% drawdown was not reproduced**. Its edge is thin: the full-history profit factor is only **1.04**, while maximum equity drawdown reaches **34.61%** at 1% risk per entry.

The literal hold-until-stopped variant should **not replace the current session-close variant in the active BAT**. The BAT was not changed by this validation.

## Exact rule tested

- Chart: Exness `USTEC`, M5.
- At 09:35 New York time, inspect the completed 09:30–09:35 candle.
- If its close is above EMA(12), buy; if below EMA(12), sell.
- Maximum one entry per New York trading day.
- ATR(14) volatility management.
- Initial stop: 3.0 ATR.
- Chandelier-style trailing distance: 4.0 ATR, active immediately.
- No fixed take profit and no end-of-day exit; the position remains open until its stop is hit.
- Both long and short signals enabled.
- Risk: 1.0% of current equity per entry.
- New York daylight-saving conversion is handled in the EA.

The source description does not disclose its proprietary volatility formula. ATR is therefore the explicit, reproducible interpretation. The 3.0 ATR initial stop and 4.0 ATR trail were selected using only the pre-2025 training results before running the post-2024 validation.

## Native Exness MT5 results

| Segment | Dates | History quality | Return | CAGR | PF | Win rate | Max equity DD | Trades | Final balance |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Locked validation | 2025-01-01 to 2026-08-22 | 100% | +23.40% | 13.70% | 1.09 | 32.07% | 21.08% | 421 | $12,339.66 |
| Full available history | 2019-07-16 to 2026-08-22 | 98% | +56.38% | 6.50% | 1.04 | 32.24% | 34.61% | 1,827 | $15,638.23 |

Both tests used MT5 synchronized **Every Tick**, a $10,000 initial deposit, 1% risk sizing, Exness spread, reported commission and swap, and random execution delay.

## Full-history statistics

| Metric | Result |
|---|---:|
| Net profit | $5,638.23 |
| Gross profit | $130,947.40 |
| Gross loss | -$125,309.17 |
| Profit factor | 1.04 |
| Wins / losses | 589 / 1,238 |
| Long trades / win rate | 917 / 35.11% |
| Short trades / win rate | 910 / 29.34% |
| Largest win / loss | $1,341.29 / -$190.46 |
| Average win / loss | $222.32 / -$98.53 |
| Maximum balance DD | $4,818.80 / 33.52% |
| Maximum equity DD | $5,021.68 / 34.61% |
| Recovery factor | 1.12 |
| Sharpe ratio reported by MT5 | 1.05 |
| Commission | -$3,331.43 |
| Swap | -$374.86 |

## Comparison with the current BAT variant

| Variant | Full-history return | PF | Max equity DD | Conclusion |
|---|---:|---:|---:|---|
| Literal hold until ATR stop | +56.38% | 1.04 | 34.61% | Profitable, but fragile and high-DD |
| Current BAT session-close variant | +155.35% | 1.12 | 27.10% | Better historical result, but still not low-DD |
| Advertised claim | About +406% | Not disclosed | About 19% | Not reproduced |

## Saved evidence

- EA source/binary: `EA/Nasdaq 5M Open EMA ATR EA.mq5` and `.ex5`
- Literal settings: `Sets/LITERAL - USTEC M5 - 1pct - EMA12 ATR3 Trail4 HOLD.set`
- Native reports and graphs: `Backtest Reports/Literal Hold/`
- Parsed result data: `literal-hold-results.csv` and `literal-hold-results.json`
- Re-run script: `Run-Nasdaq-5M-Literal-Hold.ps1`
