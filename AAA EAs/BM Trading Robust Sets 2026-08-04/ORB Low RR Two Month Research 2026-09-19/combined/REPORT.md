# Combined seven-ORB reconstruction

19 July–18 September 2026. Three separate shared $10,000 portfolios; 1% equity risk per entry, broker lot rounding up, adaptive off. Native MT5 historical quotes mark the saved fills to market; this is NOT a fresh multi-EA strategy backtest or verified FTMO execution.

| Portfolio | Final balance | Net return | Trades | Net win rate | PF | Sampled equity DD | Worst daily equity loss | Max concurrent trades | Maximum initial-stop exposure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Current RR settings | $10,504.83 | +5.05% | 39 | 43.59% | 1.43 | 5.62% | $319.90 | 4 | $451.12 |
| All seven at 0.5R | $10,765.49 | +7.65% | 39 | 76.92% | 1.97 | 4.42% | $338.33 | 3 | $340.82 |
| All seven at 0.75R | $10,534.87 | +5.35% | 39 | 61.54% | 1.57 | 4.46% | $319.90 | 3 | $342.51 |

These balances assume uninterrupted trading. Challenge phases are instead evaluated below with a fresh $10K Verification balance from the next business day after passing Phase 1. No administrative delay is modeled.

| Portfolio | Phase 1 reached +10%, flat and four entry days | Verification final balance | Verification closed trades | Verification reached +5% | Loss breach in either phase replay |
|---|---|---:|---:|---|---|
| Current RR settings | 2026-08-10T20:00:00+00:00 | $9,495.29 | 23 | No | None observed |
| All seven at 0.5R | 2026-09-11T15:12:58+00:00 | $9,654.90 | 9 | No | None observed |
| All seven at 0.75R | Not reached | Not started | — | No | None observed |

## Uninterrupted monthly net USD

| Portfolio | July 19–31 | August | September 1–18 |
|---|---:|---:|---:|
| Current RR settings | $-16.86 | $+945.81 | $-424.12 |
| All seven at 0.5R | $+252.65 | $+481.06 | $+31.78 |
| All seven at 0.75R | $+312.36 | $+285.04 | $-62.53 |

## Limitations and evidence

- All 39 signals per portfolio come from the seven standalone native tests. Fills, entry timing and exit timing are held constant; new lot sizes use shared marked-to-market equity. Broker-valid lots round up. Historical commissions are scaled by volume, swaps are zero in the source ledgers.
- Simultaneous timestamps process existing closes first, then new entries by EA identifier. Saved timestamps have second precision. This ordering and reuse of fills introduce reconstruction uncertainty.
- Equity is sampled on USTEC ticks and timer callbacks using historical XAUUSD/USTEC bid/ask quotes. No future quotes or margin-calculation errors were observed. Secondary quotes were up to six seconds old in the full-window replay; this is not a merged, every-symbol-tick equity path.
- Original Exness history used generated ticks on September 14–15. Spread is reflected in fills and bid/ask marking; no additional latency/slippage stress was added.
- Exness symbol specifications and tester 1:30 leverage were used for available-margin checks, not validated FTMO symbol margins. No entry was skipped for margin in the full-window replay.
- Maximum initial-stop exposure sums original stop risks of concurrently open trades; it does not assume later trailing stops remain at their original levels.
- FTMO 2-Step loss checks use $500 daily equity loss from Prague-midnight balance and $9,000 static equity floor. Phase targets require flat positions and four entry days. Phase transition assumes the next business day with no administrative wait. This is historical evidence, not a passing probability or payout guarantee. [Official objectives](https://ftmo.com/en/trading-objectives/)
- Research files only. No live trade, active EA, installer/BAT, or website setting changed.

Inputs, per-trade cash flows, daily equity minima and native journals are saved under `combined/` and `combined-verification/`.
