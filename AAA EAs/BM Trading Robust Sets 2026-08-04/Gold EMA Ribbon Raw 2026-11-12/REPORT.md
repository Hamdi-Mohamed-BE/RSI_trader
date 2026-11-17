# Gold EMA Ribbon - RAW result (2026-11-12) - REJECTED at the raw gate

Source: owner-pasted clip "Gold EMA Ribbon Strategy" (claims 2 years, 293 trades, 31% win, avg win ~$2,400 / loss ~$600 at $750 risk, worst day -2%, DD 9.1%,
89% of 1,000 simulated FTMO challenges passed). Rules frozen in RULES.md before any run. EA `EA/Gold EMA Ribbon Research EA.mq5`, XAUUSD H1, EMA 8/13/21/34/55 + EMA200,
CROSS trigger, stop 1.5 x ATR14, no target, exit on an H1 close beyond EMA55, 0.75% of balance rounded DOWN, $100k, native Model 4, 150 ms, end 2026-11-12 excl.
Older ticks are generated (real ticks from 2026-01-01).

## MAIN by window (each window = separate $100k run)
| Window | Trades | /month | /day | Net | R | PF | Win | Avg win | Avg loss | Closed DD | Worst day | Held over weekend |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6m | 66 | 10.9 | 0.52 | +13.9% | +18.7 | 1.48 | 28.8% | $2,410 | -$679 | 8.6% | -2.15% | 13 |
| 1y | 128 | 10.7 | 0.51 | +43.8% | +52.4 | 1.70 | 29.7% | $3,013 | -$785 | 8.6% | -2.71% | 22 |
| 2y (clip span) | 239 | 10.0 | 0.48 | +105.5% | +103.7 | 1.75 | 31.0% | $3,491 | -$926 | 8.7% | -3.93% | 47 |
| 3y | 362 | 10.1 | 0.48 | +110.9% | +110.5 | 1.49 | 27.6% | $3,327 | -$846 | 19.5% | -4.03% | 72 |
| 5y | 620 | 10.3 | 0.49 | +102.8% | +112.1 | 1.27 | 24.8% | $2,868 | -$727 | 31.0% | -3.87% | 118 |
| all 2019-01 -> | 995 | 10.6 | 0.50 | +90.8% | +116.1 | 1.17 | 22.2% | $2,803 | -$683 | 39.0% | -3.65% | 185 |

Split (data_split, from the all-years run): dev 2019-01 -> 2023-11 633 trades +6.4R PF 1.01 (net -$9.1k), DD 39%; val 124 trades +7.7R PF 1.09; OOS (last 2 y) 238 trades +102.1R PF 1.74.
Years (R): 2019 -2.0, 2020 +11.1, 2021 -17.2, 2022 +15.1, 2023 +8.1, 2024 -0.2, 2025 +52.6, 2026 +48.5. 85% of the all-years R comes from 2025-26 (gold rally).

## Sensitivities (all years, Model 4)
| Version | Trades | /month | /day | R | PF | Win | Closed DD | Worst day |
|---|---|---|---|---|---|---|---|---|
| MAIN (CROSS 8-55) | 995 | 10.6 | 0.50 | +116.1 | 1.17 | 22.2% | 39.0% | -3.65% |
| STATE trigger | 1,383 | 14.7 | 0.70 | +169.7 | 1.19 | 22.3% | 43.9% | -5.18% |
| RIB2 5/10/20/30/50 | 1,135 | 12.0 | 0.57 | +191.2 | 1.25 | 24.2% | 25.1% | -6.14% |
| RIB3 10/20/30/40/50 | 914 | 9.7 | 0.46 | +118.2 | 1.19 | 22.6% | 35.8% | -3.79% |
| LONG only | 554 | 5.9 | 0.28 | +96.4 | 1.24 | 22.7% | 37.1% | -2.67% |

## Gate checks
- Random direction (20 seeds, Model 1; MAIN Model 1 +122.4R): mean +56.9R, p = 0.095 (passes, barely).
- Random ENTRY (20 seeds, same rate, side of EMA200, same stop + exit): mean +83.8R, 5/20 seeds beat MAIN, p = 0.286 -> FAIL. The ribbon trigger adds little;
  the profit comes from "be on the EMA200 side of gold and trail with EMA55" in a trending market.
- Three-way MC (1,000 runs): resample red 10.3% -> FAIL (limit 5%); randomize 2.7% (pass); real DD worse than 53.6% of shuffles (not clumped).
- Cost stress (spread logged per entry, XAUUSD point 0.001, median spread $0.125 = 0.038R/trade, + recorded commission/swap): 1x +116.1R PF 1.17, 2x +8.0R PF 1.01 (PASS, barely),
  3x -100.1R; break-even multiple 2.07. (A first pass used point 0.01 and wrongly showed a 2x fail; corrected in RESULTS.json.)
- Buy & hold XAUUSD CFD (same windows, incl. swap): 6m -18.1%, 1y -8.0%, 2y +35.4%, 3y +66.6%, 5y +47.1%, all +67.7% (DD 60.6%). MAIN beats it on every window.

## Verdict
The clip's 2-year numbers are roughly reproduced (239 vs 293 trades, 31% win, DD 8.7% vs 9.1%; worst day -3.9% vs -2%), but that span is gold's best trend regime.
REJECTED at the raw gate: random-entry control p 0.286 (> 0.10) and resample MC 10.3% (> 5%); development 2019-23 is flat (PF 1.01, -$9.1k, DD 39%).
185/995 trades are held over a weekend (FTMO 1-Step / Standard forbid it; the Calyx Weekend Flat helper would cut them - not simulated).
No optimisation, no FTMO simulation (gate failed). Nothing installed, deployed or pushed.
