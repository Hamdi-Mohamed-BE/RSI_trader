# XAUUSD Cross-Session Momentum — Full Locked Pipeline

Research only. No EA, BAT, website or live-account change was made.

## Decision

**FAIL — do not add to the system.**

Gate notes: Monte Carlo P5 <= 0, fewer than 60% profitable neighbours

## Selected configuration

- Prior-session return threshold: **0.0 bps**
- Sessions traded: **Europe+US**
- Weekdays: **no-monday**
- Trend filter: **price above 50-day M30 SMA proxy**
- Stop: **1.00 × M30 ATR(14)**
- Target: **session close**
- Management: **none**
- Sizing: **1% current-equity risk, capped at 5× effective leverage**

## Locked results

| Segment | Return | CAGR | PF | Win rate | Max DD | Sharpe | Recovery | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Train | 76.14% | 22.57% | 1.33 | 28.91% | 16.74% | 1.06 | 4.55 | 339 |
| Validation | 44.77% | 44.96% | 1.47 | 38.51% | 8.24% | 1.70 | 5.43 | 161 |
| Locked | 17.70% | 17.82% | 1.21 | 31.36% | 13.88% | 0.66 | 1.28 | 118 |
| Locked extra-cost stress | 16.03% | 16.14% | 1.19 | 31.36% | 14.25% | 0.61 | 1.13 | 118 |
| Full five years | 200.14% | 25.77% | 1.33 | 31.88% | 16.74% | 1.08 | 11.95 | 618 |

## Corrected raw baseline

The raw continuous-position baseline below now includes recorded spread, commission **and XAU rollover swap**. The earlier raw report omitted that swap charge.

| Window | Return | PF | Win rate | Max DD | Sharpe | Trades |
|---|---:|---:|---:|---:|---:|---:|
| Train | 14.93% | 1.16 | 35.47% | 13.25% | 0.47 | 547 |
| Validation | 24.17% | 1.56 | 40.11% | 8.27% | 1.72 | 177 |
| Locked | 14.46% | 1.26 | 38.46% | 15.51% | 0.83 | 182 |
| Full five years | 63.34% | 1.26 | 36.98% | 15.51% | 0.81 | 906 |

## Robustness

- 10,000-path five-trade block bootstrap on the locked trades: P5 return **-16.29%**, median **20.51%**, P95 **85.46%**, P95 drawdown **27.04%**, probability of profit **78.88%**.
- Parameter neighbours: **50.0% profitable**, median PF **0.97**, median return **-1.34%** in the locked year.
- Winner concentration: the best locked trade was **12.19R** and supplied **70.6%** of compounded log gain. Removing it leaves **+4.91%**; capping all winners at 5R leaves **+4.37%**, while a 3R cap gives **-9.14%**.
- Search control: **1830 unique staged candidates** were ranked using train and validation only; the locked year was opened once after selection.
- Cost stress adds one further recorded round-trip spread and raises commission by 50%.

## Annual stability

| From | To | Return | PF | Win rate | DD | Trades |
|---|---|---:|---:|---:|---:|---:|
| 2021-09-13 | 2022-09-13 | 11.39% | 1.30 | 30.30% | 7.93% | 66 |
| 2022-09-13 | 2023-09-13 | 15.32% | 1.25 | 27.62% | 12.33% | 105 |
| 2023-09-13 | 2024-09-13 | 38.33% | 1.40 | 29.24% | 16.74% | 171 |
| 2024-09-13 | 2025-09-13 | 41.92% | 1.45 | 38.12% | 8.24% | 160 |
| 2025-09-13 | 2026-09-11 | 19.02% | 1.23 | 31.90% | 13.88% | 116 |

## Evidence

- `results.json`: complete selection, locked, stress, neighbour and Monte Carlo evidence.
- `configuration-audit.csv`: every staged development result.
- `selected-trades.csv`: full-history trade list.
- `neighbour-stability.csv` and `annual-stability.csv`: robustness evidence.
- `Charts/xau-cross-session-full-pipeline.png`: equity and comparison chart.

Historical results are diagnostics, not a guarantee of future profitability.