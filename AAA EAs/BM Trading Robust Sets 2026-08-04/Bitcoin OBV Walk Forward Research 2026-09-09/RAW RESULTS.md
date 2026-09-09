# Step 10 — Bitcoin OBV walk-forward paper

## Goal

Reproduce the strongest implementable family in Deprez & Frömmel (2024) as
published, then decide whether it deserves the Calyx optimization pipeline.
Nothing in the EA, website, BAT installers, or recommended portfolio was
changed.

## Paper and raw rule

- **Paper:** Niek Deprez and Michael Frömmel, “Are simple technical trading
  rules profitable in bitcoin markets?”, *International Review of Economics &
  Finance* 93 (2024), DOI 10.1016/j.iref.2024.05.003.
- **Signal:** on-balance volume (OBV), followed by fast/slow moving-average
  rules.
- **Published universe reproduced:** 2,475 OBV parameter combinations at each
  of M10, M30, H1 and D1 — 9,900 rules total.
- **Selection:** every month, rank rules using only the preceding 12 calendar
  months; trade the chosen rule(s) during the next month.
- **Portfolio variants:** the paper's Best 1 and Best 50, ranked by after-cost
  mean return or Sharpe ratio. The more complex FDR+ stationary-bootstrap
  portfolio is not approximated or mislabeled.
- **Direction:** long/flat, matching the paper's primary “in-or-out” test.
- **Execution:** next bar after the signal; no lookahead.

## Data and costs

- Exness demo BTCUSD M5, 490,205 bars, 2022-01-01 through 2026-08-31 UTC.
- Untouched walk-forward test: 2023-01-01 through 2026-08-31 (44 monthly
  decisions).
- The paper uses Bitstamp traded volume. Exness supplies no real-volume field,
  so MT5 tick volume is the unavoidable transfer proxy.
- **Broker case:** half the observed spread per one-way transaction.
- **Paper-cost stress:** broker spread plus the paper's current-sample 0.10%
  fee per one-way transaction.
- Returns are the paper-style long/flat allocation, not Calyx's later 1%-risk EA
  model. That risk model belongs only in a user-approved optimization stage.

## Raw out-of-sample results

| Published variant | Costs | Return | PF | Win rate | Max DD | Sharpe | Recovery | Trades / basis |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Best 1 / Sharpe | Broker | +127.44% | 1.77 | 45.83% | 20.66% | 0.98 | 6.17 | 96 closed trades |
| **Best 1 / Sharpe** | **Paper stress** | **+87.33%** | **1.56** | **43.75%** | **21.84%** | **0.78** | **4.00** | **96 closed trades** |
| Best 1 / Mean | Broker | +86.70% | 1.46 | 49.18% | 38.25% | 0.71 | 2.27 | 122 closed trades |
| Best 1 / Mean | Paper stress | +46.13% | 1.30 | 46.72% | 42.65% | 0.49 | 1.08 | 122 closed trades |
| Best 50 / Mean | Broker | +160.41% | 1.24* | 49.12%* | 26.25% | 1.12 | 6.11 | ensemble |
| Best 50 / Mean | Paper stress | +103.23% | 1.18* | 46.92%* | 27.95% | 0.86 | 3.69 | ensemble |
| Best 50 / Sharpe | Broker | +125.11% | 1.22* | 49.03%* | 25.55% | 1.00 | 4.90 | ensemble |
| Best 50 / Sharpe | Paper stress | +79.81% | 1.16* | 47.27%* | 27.90% | 0.75 | 2.86 | ensemble |
| BTC buy and hold | Paper stress | +374.16% | — | — | 53.06% | 1.14 | 7.05 | one holding period |

`*` Best-50 is an ensemble with fractional exposure, so PF is calculated from
daily portfolio outcomes and win rate means positive active days. Best-1 PF and
win rate are calculated from its 96 closed trades.

## Stability of the strongest raw variant

Best 1 / Sharpe with paper-cost stress:

| Period | Return | PF | Win rate | Max DD | Sharpe | Recovery | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | +24.72% | 3.15 | 45.00% | 8.37% | 1.17 | 2.95 | 20 |
| 2024 | +49.58% | 1.76 | 47.37% | 21.84% | 1.28 | 2.27 | 38 |
| 2025 | +7.05% | 1.25 | 37.04% | 14.46% | 0.40 | 0.49 | 27 |
| 2026 YTD | **-6.20%** | **0.75** | **45.45%** | **14.98%** | **-0.43** | **-0.41** | **11** |

The monthly Sharpe selector chose D1 rules in 33 months and H1 rules in 11;
M10 and M30 were never selected. This independently supports the paper's
warning that higher-frequency results are fragile to costs.

## Decision

**Do not add it to Calyx and do not optimize it yet.** The raw result has a real
risk-control effect — maximum drawdown was roughly 22% instead of buy-and-hold's
53% — but it earned far less, had a lower Sharpe, and deteriorated monotonically
from 2023 to a losing 2026. The latest-year PF of 0.75 fails the continuation
gate. Its low correlation/exposure benefit is not enough to justify production
without a fresh locked validation period.

The research is retained because the walk-forward design is useful and the
paper itself is credible. Recommended production action remains **none**.
