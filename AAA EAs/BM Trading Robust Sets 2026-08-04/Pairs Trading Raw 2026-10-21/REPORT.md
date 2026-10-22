# Pairs trading (spread z-score fade) — raw study report (2026-10-21/22)

**Verdict: 8 of 9 pairs REJECTED. EUR/GBP (P4) is the only pair that passes the raw gate.** Model 4 confirms it, but the
sample is thin: 30 pair trades in 5 years, about one every two months. It is a raw survivor, not a tradable result.
Research only. Isolated tester `_Backtests/MT5-DMC-20260811` (Exness-MT5Trial16). Nothing installed, deployed or pushed.

Rules: [RULES.md](RULES.md), frozen before any test. Full tables: [RESULTS.md](RESULTS.md) / `RESULTS.json`. Chart: `equity.png`.
EA: `EA/Pairs Zscore Research EA.mq5`. Native runs: `native/` (report, journal, trades and run.json per case).

## What was tested
- **Rule (from the clip):**
  - Spread s = ln A − ln B (dollar-neutral legs) on daily closes; z-score over 60 days.
  - At |z| ≥ 2, short the leg that ran up and buy the laggard.
  - Exit when z crosses back through 0; stop at |z| ≥ 3.5.
  - Risk is 1% of equity to the stop.
- **Pairs:** ETH/BTC, gold/silver, AUD/NZD, EUR/GBP, S&P/Dow, S&P/Nasdaq, GOOGL/META, AMD/NVDA, MSFT/AAPL.
  Coke/Pepsi are not in the tester.
- **Setup:**
  - Native MT5, $100k, 150 ms, end 2026-10-20 exclusive.
  - Separate 6m / 1y / 3y / 5y runs per pair, plus controls and sensitivities on 5y. That is 90 Model 1 runs and
    2 Model 4 confirmations, 0 run failures.
  - Model 1 was used for the screen. That revision was recorded in RULES.md after the smoke test, before any real run.
- **Trade count:** each pair trade counts once, both legs together. A pair still open at the end of a test is booked
  as a final trade, so the pair totals reconcile with native net profit (asserted for every run).

## Headline — 5 years, FADE (Model 1)
| Pair | Trades | / month | / day | Return | PF | Win % | Equity DD | Swap $ | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| P1 ETH/BTC | 32 | 0.53 | 0.018 | −12.73% | 0.57 | 50.0 | 25.72% | −6,975 | FAIL |
| P2 XAU/XAG | 31 | 0.52 | 0.020 | +5.47% | 1.30 | 61.3 | 11.35% | −5,409 | FAIL (3y −1.31%) |
| P3 AUD/NZD | 21 | 0.35 | 0.013 | −20.49% | 0.32 | 52.4 | 23.55% | −8,886 | FAIL |
| **P4 EUR/GBP** | **30** | **0.50** | **0.019** | **+13.19%** | **1.89** | **73.3** | **5.44%** | −5,068 | **PASS** |
| P5 S&P/Dow | 25 | 0.42 | 0.016 | −20.23% | 0.29 | 40.0 | 27.72% | −22,850 | FAIL |
| P6 S&P/Nasdaq | 24 | 0.40 | 0.015 | −30.60% | 0.14 | 33.3 | 34.43% | −22,436 | FAIL |
| P7 GOOGL/META | 21 | 0.35 | 0.017 | −20.93% | 0.29 | 57.1 | 26.14% | −8,414 | FAIL |
| P8 AMD/NVDA | 17 | 0.28 | 0.014 | −34.83% | 0.14 | 35.3 | 39.68% | −23,803 | FAIL |
| P9 MSFT/AAPL | 22 | 0.37 | 0.018 | −7.89% | 0.66 | 54.5 | 14.22% | −12,969 | FAIL |

Trades per day use calendar trading days of the pair's symbols (stock pairs trade fewer days a year).

## EUR/GBP — the only survivor
| Window | Model | Trades | / month | / day | Return | PF | Win % | Sharpe | Equity DD | Closed DD | Mean R |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 6m | 1 | 3 | 0.50 | 0.019 | −2.16% | 0.47 | 33.3 | −0.91 | 4.99% | 3.80% | — |
| 1y (last year) | 1 | 6 | 0.50 | 0.019 | +0.74% | 1.18 | 66.7 | 0.13 | 4.99% | 3.81% | 0.12 |
| 3y | 1 | 19 | 0.53 | 0.020 | +5.35% | 1.51 | 73.7 | 0.38 | 5.45% | 3.81% | 0.28 |
| 5y | 1 | 30 | 0.50 | 0.019 | +13.19% | 1.89 | 73.3 | 0.53 | 5.44% | 3.81% | 0.44 |
| 3y | **4** | 19 | 0.53 | 0.020 | +5.78% | 1.56 | 73.7 | 0.41 | 5.15% | 3.71% | — |
| 5y | **4** | 30 | 0.50 | 0.019 | +13.51% | 1.92 | 73.3 | 0.54 | 5.28% | 3.71% | — |

- **Exits (5y, closed trades):**
  - 27 gap-closed exits made +$21,934.
  - 2 stops lost −$4,254.
  - The pair open at test end was marked at −$4,488 (opened 2026-10-02, both legs losing). It explains the drop at the
    right edge of the chart.
- **Per year (5y run, closed pair trades):**

  | Year | Trades | Net |
  |---|---:|---:|
  | 2021 (Q4) | 2 | +$3,077 |
  | 2022 | 6 | +$6,437 |
  | 2023 | 5 | +$77 |
  | 2024 | 6 | +$1,223 |
  | 2025 | 6 | +$2,225 |
  | 2026 to date | 4 | +$4,640 (≈ +$152 after the open trade) |

  No losing calendar year on closed trades, but 2023 was flat and most of the profit came in 2021–2022.
- **Controls, 5y:**
  - Momentum (the opposite bet): PF 0.25, −22.5%.
  - Random direction (3-seed mean): PF 0.71, −6.7%.
  - The fade direction is what made the money.
- **Sensitivities, 5y — all positive:**

  | Change | Return | PF |
  |---|---:|---:|
  | 20-day window | +14.7% | 1.39 |
  | 120-day window | +5.4% | 1.55 |
  | Entry at 2.5σ | +5.4% | 1.44 |
  | Stop at 4σ | +12.1% | 2.55 |
  | No stop | +16.5% | 2.55 |
  | OLS β | +4.2% | 1.22 |

- **Best-day falsifier:**
  - 5y PASS: +$10,952 without the best day; +$3,458 without the 5 best days.
  - 3y PASS on the best day, but −$2,703 without the 5 best days.
- **Swap** cost −$5,068 over 5 years (~28-day average hold). It is about a quarter of the gross edge.

## Why the others failed
- **Stock and index pairs (P5–P9):**
  - Lost in 5y, PF 0.14–0.66.
  - The spreads trended: S&P vs Nasdaq, AMD vs NVDA, GOOGL vs META. That is the "breakup" risk the clip warns about.
  - Swap on two index legs cost $22–24k over 5 years.
- **ETH/BTC:** lost (PF 0.57). It trended apart, as the clip itself admits; the 2023 stop shows on the chart.
- **AUD/NZD:** lost heavily (PF 0.32). Momentum on it was positive (+4.8%), the reverse of the rule.
- **Gold/silver:** positive over 5y (+5.5%, PF 1.30) but negative over 3y (−1.3%). It fails the gate and fell
  without its best 5 days.

## Limitations
- **Thin sample:** 30 EUR/GBP pair trades. The 95% interval on a 73% win rate from 30 trades is about 56–86% (Wilson).
- **Recent performance is weak:** last 6 months −2.2%; last year +0.7%, PF 1.18.
- **Selection bias:** EUR/GBP was picked after testing 9 pairs. With one survivor out of nine, a chance pass is
  plausible. A deflated / multiple-testing view is needed before taking it seriously.
- **Generated ticks:** older ticks are generated; real ticks start in 2026-01. Model 1 and Model 4 agree within
  0.4% on P4.
- **No live fill check:** daily evaluation at the first in-session tick; no check of live fills at that time.
- **Not a qualification:** this is a raw stage-4 result. Stage 5 (dev/val/OOS search), plateau and Monte Carlo were
  not run.

## Recommendation
- Do not trade any of these pairs.
- If you want to take EUR/GBP further, the next step is the stage-5 pipeline on P4 only:
  - Use the `data_split.py` split: OOS = last 2 years, validation = the prior 12 months.
  - Expect very few trades per split (about 6 per year). A pass there would still rest on a small sample.
- The other 8 pairs are closed.
