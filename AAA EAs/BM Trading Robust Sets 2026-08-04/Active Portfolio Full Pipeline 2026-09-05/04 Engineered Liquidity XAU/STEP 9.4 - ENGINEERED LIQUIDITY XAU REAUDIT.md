# Step 9.4 — Engineered Liquidity XAU Re-audit

## Goal and controls

Re-test the active XAUUSD H1 strategy at a fixed 1% risk using broker-cost-inclusive MT5 evidence. Development used 2023-09-01 through 2025-08-31; the untouched locked year used 2025-09-01 through 2026-09-01; final validation used exact three-year Every Tick history. Monte Carlo uses 10,000 five-calendar-day block-bootstrap paths.

## Recommendation

**Research recommendation: 2.5 minimum setup-RR gate, 0.03 ATR structural-stop buffer, Dynamic 60/20, long-only, all day, 24-bar maximum hold, two trades/day, fixed 1% risk.** Keep Safe as an optional per-EA switch, off by default.

This is not a literal 2.5R take-profit: the EA targets opposing liquidity and rejects entries whose projected target is below 2.5R. The 0.03 buffer is preferred to the zero-buffer development winner because it held up better in the untouched year. Long-only materially improves three-year PF and drawdown, but it remains exposed to a change in gold's long-term regime; Safe improves PF further while cutting trades and return.

No BAT, selected preset, EA binary, or website record was changed during this audit. Deployment remains pending user approval.

## Untouched locked-year MT5 results

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Deployed: 2.0 gate, 0.08 buffer, dynamic 50/20, both | +30.30% | 1.53 | 42.50% | 10.09% | 80 | 5.76 | 2.29 |
| Current rules, native exit | +22.97% | 1.37 | 35.00% | 13.21% | 80 | 3.91 | 1.30 |
| Deployed base + Safe D1 regime gate | +19.81% | 1.37 | 39.73% | 12.82% | 73 | 4.47 | 1.14 |
| 2.5 gate, 0.00 buffer, dynamic 60/20, long | +19.53% | 1.80 | 41.03% | 8.68% | 39 | 8.35 | 1.91 |
| 2.5 gate, 0.03 buffer, dynamic 60/20, both | +29.63% | 1.57 | 39.44% | 8.83% | 71 | 6.02 | 2.52 |
| 2.5 gate, 0.03 buffer, dynamic 60/20, long | +24.00% | 1.92 | 41.46% | 7.46% | 41 | 9.75 | 2.76 |
| 2.5 gate, 0.03 buffer, dynamic 60/20, long + Safe | +24.00% | 1.92 | 41.46% | 7.46% | 41 | 9.75 | 2.76 |

## Exact three-year Every Tick results

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Deployed: 2.0 gate, 0.08 buffer, dynamic 50/20, both | +73.70% | 1.39 | 38.60% | 12.69% | 228 | 4.38 | 4.00 |
| Current rules, native exit | +62.23% | 1.31 | 31.86% | 13.44% | 226 | 3.40 | 2.61 |
| Deployed base + Safe D1 regime gate | +53.99% | 1.48 | 41.04% | 13.09% | 134 | 5.53 | 2.37 |
| 2.5 gate, 0.00 buffer, dynamic 60/20, long | +121.61% | 1.82 | 40.00% | 9.07% | 150 | 8.49 | 6.15 |
| 2.5 gate, 0.03 buffer, dynamic 60/20, both | +103.46% | 1.55 | 37.50% | 9.05% | 200 | 5.86 | 5.47 |
| 2.5 gate, 0.03 buffer, dynamic 60/20, both + Safe | +58.49% | 1.55 | 39.47% | 12.66% | 114 | 6.47 | 2.64 |
| 2.5 gate, 0.03 buffer, dynamic 60/20, long | +116.18% | 1.81 | 40.26% | 7.46% | 154 | 8.32 | 7.65 |
| 2.5 gate, 0.03 buffer, dynamic 60/20, long + Safe | +73.20% | 1.99 | 43.48% | 8.03% | 92 | 9.56 | 5.20 |

## Monte Carlo

| Configuration | P(profit) | Return P5 / median / P95 | Median / P95 DD | P(DD ≥10%) | P(DD ≥20%) | Ruin |
|---|---:|---:|---:|---:|---:|---:|
| Deployed: 2.0 gate, 0.08 buffer, dynamic 50/20, both | 98.09% | +10.68% / +73.30% / +180.88% | 14.10% / 24.38% | 87.57% | 14.50% | 0.00% |
| 2.5 gate, 0.03 buffer, dynamic 60/20, both | 99.49% | +27.20% / +101.32% / +234.44% | 13.00% / 22.23% | 81.30% | 9.04% | 0.00% |
| 2.5 gate, 0.03 buffer, dynamic 60/20, long | 99.82% | +40.16% / +115.72% / +243.03% | 9.93% / 16.99% | 49.08% | 1.80% | 0.00% |
| 2.5 gate, 0.03 buffer, dynamic 60/20, long + Safe | 99.64% | +20.88% / +71.52% / +155.98% | 8.01% / 14.23% | 26.63% | 0.45% | 0.00% |

## Development — minimum projected RR gate

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| rr-050 | +14.70% | 1.10 | 40.00% | 15.76% | 220 | 1.42 | 0.70 |
| rr-075 | +15.46% | 1.11 | 39.91% | 16.01% | 218 | 1.50 | 0.71 |
| rr-100 | +15.13% | 1.11 | 39.05% | 15.93% | 210 | 1.50 | 0.70 |
| rr-125 | +14.43% | 1.11 | 37.95% | 14.46% | 195 | 1.48 | 0.75 |
| rr-150 | +11.72% | 1.09 | 36.02% | 12.62% | 186 | 1.25 | 0.73 |
| rr-200 | +32.50% | 1.29 | 36.49% | 12.62% | 148 | 3.57 | 1.77 |
| rr-250 | +47.36% | 1.49 | 38.89% | 8.99% | 126 | 5.45 | 4.08 |
| rr-300 | +27.19% | 1.34 | 34.31% | 11.97% | 102 | 4.22 | 1.78 |
| rr-400 | +15.72% | 1.29 | 29.41% | 10.29% | 68 | 3.80 | 1.28 |
| rr-500 | +8.09% | 1.22 | 28.26% | 11.37% | 46 | 2.93 | 0.58 |

## Development — stop buffer

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| stop-buffer-000 | +45.28% | 1.38 | 36.67% | 10.04% | 150 | 4.56 | 3.20 |
| stop-buffer-003 | +38.08% | 1.32 | 36.77% | 10.43% | 155 | 3.91 | 2.49 |
| stop-buffer-005 | +34.17% | 1.29 | 36.77% | 10.71% | 155 | 3.61 | 2.23 |
| stop-buffer-008 | +32.50% | 1.29 | 36.49% | 12.62% | 148 | 3.57 | 1.77 |
| stop-buffer-012 | +22.66% | 1.21 | 36.49% | 12.70% | 148 | 2.65 | 1.32 |
| stop-buffer-020 | +22.07% | 1.23 | 38.62% | 10.46% | 145 | 2.68 | 1.60 |
| stop-buffer-030 | +18.40% | 1.20 | 38.57% | 10.38% | 140 | 2.35 | 1.54 |

## Development — management

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| manage-native | +32.28% | 1.28 | 30.14% | 10.97% | 146 | 3.17 | 2.50 |
| manage-dynamic5020 | +32.50% | 1.29 | 36.49% | 12.62% | 148 | 3.57 | 1.77 |
| manage-dynamic5010 | +29.03% | 1.26 | 36.49% | 14.27% | 148 | 3.11 | 1.41 |
| manage-dynamic5030 | +29.35% | 1.27 | 36.49% | 11.96% | 148 | 3.43 | 1.74 |
| manage-dynamic6020 | +48.77% | 1.41 | 36.05% | 11.13% | 147 | 4.81 | 2.75 |
| manage-dynamic7525 | +36.95% | 1.31 | 31.29% | 9.41% | 147 | 3.66 | 2.71 |

## Development — sessions

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| session-all | +32.50% | 1.29 | 36.49% | 12.62% | 148 | 3.57 | 1.77 |
| session-asia | +5.03% | 1.14 | 36.54% | 13.61% | 52 | 2.02 | 0.30 |
| session-london | +9.32% | 1.44 | 44.74% | 11.04% | 38 | 4.68 | 0.82 |
| session-new-york | +0.03% | 1.00 | 28.81% | 9.75% | 59 | 0.01 | 0.00 |
| session-overlap | -10.18% | 0.53 | 20.69% | 10.89% | 29 | -5.00 | -0.93 |

## Development — direction

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| direction-both | +32.50% | 1.29 | 36.49% | 12.62% | 148 | 3.57 | 1.77 |
| direction-long-only | +41.28% | 1.38 | 37.88% | 13.19% | 132 | 4.78 | 2.00 |
| direction-short-only | -7.30% | 0.38 | 25.00% | 10.25% | 16 | -5.00 | -0.69 |

## Interpretation

- All day is retained. London-only raised PF but left only 38 development trades and much less return; New York and overlap failed.
- Dynamic 60/20 means that after a completed M15 candle reaches 60% of the original path to target, the stop locks 20% of that path. It beat native and Dynamic 50/20 in development.
- Safe is a completed-D1 Markov regime gate layered onto this EA alone, with no look-ahead. It is useful as a cautious option, not the Standard default.
- The short side was negative in development; the long-only recommendation is evidence-driven, but requires demo forward monitoring because directional edges can be regime-dependent.
- Historical and simulated results are not a promise of future profit.
