# CRT Alpha Sweep + Renko — RAW REPORT (2026-11-11): REJECTED

Source: NINZA Trading video "14 wins in 18 trades! Live CRT Scalping in a Volatile market" + ninza.co/access/crt-alpha (rules in RULES.md, frozen first).
USTEC (NQ proxy) M1, M15 reference candle, native Model 4, 150 ms, $10k, 1% risk rounded UP, end 2026-11-11 excl. 13 runs (1 smoke + 12), 0 failed runs.

Every version lost the account. R = net / 1% of the balance before the trade, counted while the balance was >= $2,000 (below that the 0.05-lot minimum oversizes risk).

| Run | Native return | PF | Trades | Counted | /month | /day | Win % | PF (R) | Avg R |
|---|---|---|---|---|---|---|---|---|---|
| MAIN 6m (100% real ticks) | -94.9% | 0.79 | 1,312 | 892 | 217 | 10.3 | 41.0 | 0.79 | -0.161 |
| MAIN 1y | -96.5% | 0.94 | 2,509 | 2,088 | 208 | 9.9 | 40.8 | 0.91 | -0.065 |
| MAIN 3y | -100% | 0.56 | 3,134 | 553 | 143 | 6.8 | 37.1 | 0.58 | -0.283 |
| MAIN 5y | -100% | 0.61 | 3,038 | 468 | 172 | 8.2 | 35.3 | 0.52 | -0.338 |
| MAIN NY 09:30-16:00, 5y | -93.1% | 0.88 | 3,788 | 1,543 | 65 | 3.1 | 39.1 | 0.86 | -0.093 |
| PLAIN (no Renko), 5y | -100% | 0.54 | 2,537 | 371 | 202 | 9.6 | 31.0 | 0.44 | -0.428 |
| PLAIN NY, 5y | -100% | 0.72 | 2,365 | 961 | 69 | 3.3 | 36.5 | 0.77 | -0.157 |
| Random direction seeds 1/2/3, 5y | -100% | 0.58-0.65 | 2,093-2,185 | 508-682 | 176-177 | 8.4-8.5 | 34.3-38.0 | 0.56-0.66 | -0.23 to -0.31 |
| Brick 3.0 / 9.0 points, 5y | -100% | 0.62 / 0.67 | 3,262 / 3,036 | 439 / 692 | 188 / 143 | 9.0 / 6.8 | 34.6 / 40.3 | 0.49 / 0.65 | -0.36 / -0.23 |

- MAIN is no better than random direction over 5 years (avg R -0.34 vs -0.23 to -0.31). The Renko filter helps vs PLAIN (-0.34 vs -0.43) but not enough.
- Best: New York hours (-0.09R) and the last year (-0.065R, PF 0.91) — still losing. Stops average ~31 points; the USTEC spread alone costs ~0.05R per trade,
  so even before costs the edge is about zero. Win rate 31-41% vs the video's 14/18 (78%) in one session.
- Buy & hold: not re-run (every version wiped out); USTEC buy & hold 2019-07 -> 2026-11 was +44.7% with a 75% drawdown (Overnight Bias ORB optimisation report).
- Limits: ticks before 2026-01-01 are generated (Renko path approximate); MT5 USTEC CFD costs differ from NQ futures; the indicator's code and the video's
  discretionary management are not reproducible. No optimisation (the raw gate failed in every version). Nothing installed or pushed.
