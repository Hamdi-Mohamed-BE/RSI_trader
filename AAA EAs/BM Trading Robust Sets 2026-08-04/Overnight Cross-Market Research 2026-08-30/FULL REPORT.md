# Nasdaq overnight rule — cross-market MT5 audit

The original Nasdaq Overnight Negative Day logic was transferred without optimization. A broker-session probe was used to avoid market-closed orders: indices enter at 16:00 New York in summer and 15:59 in winter; stocks enter at 15:44 in summer and 14:44 in winter. Only data completed before the entry minute is used.

## Results

| Verdict | Market | Type | Dev return | Dev PF | Locked return | Locked PF | Win rate | Equity DD | Trades | Final |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| REJECT | AMD | Stock | -15.92% | 0.68 | +26.77% | 1.40 | 52.07% | 10.18% | 121 | $12,676.76 |
| REJECT | AVGO | Stock | -2.70% | 0.95 | +12.65% | 1.28 | 56.41% | 5.43% | 117 | $11,264.94 |
| REJECT | NVDA | Stock | -13.79% | 0.69 | +10.27% | 1.33 | 57.94% | 5.98% | 126 | $11,026.68 |
| KEEP CANDIDATE | USTEC | Index control | +2.09% | 1.16 | +6.89% | 1.45 | 57.14% | 2.82% | 105 | $10,689.36 |
| WATCH | US500 | Index | +3.74% | 1.41 | +4.93% | 1.57 | 64.00% | 2.21% | 100 | $10,493.20 |
| WATCH | US30 | Index | +0.24% | 1.02 | +4.78% | 1.67 | 60.19% | 2.25% | 103 | $10,477.87 |
| REJECT | TSLA | Stock | -4.96% | 0.91 | +4.21% | 1.13 | 57.85% | 7.28% | 121 | $10,420.63 |
| REJECT | AAPL | Stock | -9.05% | 0.59 | +2.42% | 1.13 | 58.12% | 6.68% | 117 | $10,241.92 |
| WATCH | JPM | Stock | +1.15% | 1.05 | +2.12% | 1.11 | 58.72% | 5.05% | 109 | $10,211.95 |
| REJECT | AMZN | Stock | -3.78% | 0.89 | +1.52% | 1.05 | 52.85% | 9.85% | 123 | $10,152.33 |
| REJECT | INTC | Stock | -38.42% | 0.33 | -1.82% | 0.97 | 42.62% | 23.98% | 122 | $9,817.56 |
| REJECT | META | Stock | +0.74% | 1.03 | -2.95% | 0.92 | 45.31% | 7.34% | 128 | $9,704.86 |
| REJECT | GOOGL | Stock | -7.46% | 0.76 | -4.96% | 0.87 | 40.98% | 15.45% | 122 | $9,504.12 |
| REJECT | MSFT | Stock | +0.64% | 1.03 | -6.06% | 0.75 | 45.76% | 7.22% | 118 | $9,394.02 |
| REJECT | NFLX | Stock | -9.05% | 0.64 | -24.46% | 0.32 | 34.62% | 24.95% | 130 | $7,553.96 |

## Honest decision

- Strict keep candidates: 1/15.
- Profitable with PF above 1 in both periods: 4/15.
- Equal-weight locked overlay return: +2.42%.
- Equal-weight realized drawdown from the overlay: 4.28 percentage points.
- Development: 2024-08-29 to 2025-08-28.
- Untouched locked test: 2025-08-29 to 2026-08-28.
- $10,000 initial balance per market; 1% risk per entry; Exness MT5 Every Tick; random execution delay; broker spread, commission and swap included.
- Index execution: 16:00 New York in DST months and 15:59 in standard-time months, then exit at 09:29 the following session; 2% emergency stop; Friday entries allowed.
- Stock execution: 15:44 New York in DST months and 14:44 in standard-time months, immediately before Exness's 19:45 UTC stock CFD close; the exit remains 09:29 New York.
- These one-minute/session adaptations avoid known market-closed rejections. They are broker compatibility fixes, not performance optimization.
- The 300-M1-bar cash-session completeness check and DST/time handling remain enabled.
- These are separate single-market MT5 tests. The equal-weight curve is a cash-flow overlay, not a simultaneous shared-margin portfolio simulation.
- No active installation BAT or website file was changed.
