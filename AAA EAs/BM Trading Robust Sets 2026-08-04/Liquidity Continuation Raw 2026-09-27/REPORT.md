# Calyx Liquidity Continuation — raw results

Completed: **80/80** frozen native tests. No optimization or deployment.

Independent reconstruction, NOT T-812. The source keeps its profitable rules private: [Telonics research](https://www.telonicstrading.com/research-liquidity-sweeps.html).

## Decision

**Do not deploy or optimize this raw version without a new research decision. All ten real-level variants fail the frozen 3y + 5y gate.** The strongest recent result alone is not evidence of a durable edge.

## At a glance: real levels only

| Asset | Entry | 6m return | 1y return | 3y return | 5y return |
|---|---|---:|---:|---:|---:|
| US30 | touch | -12.28% | +45.57% | -96.95% | -99.96% |
| US30 | retest | -0.59% | -2.76% | -93.13% | -99.96% |
| US100 | touch | -25.89% | -24.29% | -99.05% | -99.98% |
| US100 | retest | -9.29% | -19.26% | -95.00% | -100.00% |
| US500 | touch | -50.26% | -79.11% | -99.99% | -99.99% |
| US500 | retest | -14.65% | -48.08% | -99.14% | -100.00% |
| XAU | touch | -21.63% | +1.96% | -51.43% | -95.11% |
| XAU | retest | +5.56% | +12.51% | -43.20% | -86.71% |
| BTC | touch | +41.64% | +109.18% | -86.02% | -99.99% |
| BTC | retest | -26.83% | -38.43% | -94.45% | -100.01% |

## Read this first

- Separate $10,000 accounts per asset/entry/window, 1% current-equity target stop risk, upward broker lot rounding. Results are not a combined portfolio or FTMO simulation.
- Exness isolated CFD research, Model 4 + 150 ms delay. Native spread, commissions and swaps; not exchange futures prints, guaranteed fills or exact FTMO costs.
- Native journals report real ticks beginning 2026-01-01 for all five symbols. Earlier periods use generated ticks. None of the quote streams supplies nonzero contract volume or aggressor buy/sell flags, so the video's 8x volume / 70% directional-contract observation cannot be replicated with this data.
- An extra 300 calendar days warms up controls without trading. Report-native history-quality percentages include that warmup, NOT just the requested trade window. Journal real-tick start dates and data warnings are retained.
- First touch versus completed-M5 breakout then a later retest; both 1 ATR(14) M5 stop and target, 60-minute time exit. No order-flow or volume filter. See RULES.md for exact UTC sessions and expiry.
- All PF and win rates below are recalculated NET of deal commission/swap. Equity DD comes from the native floating-equity report; the figure shows CLOSED balance only.
- /day divides by all weekdays for indices/gold and all calendar days for BTC, including days with no trades; not just active trading days. /month uses elapsed calendar time.
- Severely depleted long-run accounts may stop taking signals when minimum lots cannot be margined. This can make a five-year run contain fewer executed trades than a three-year run. No capital resets or deposits are used; minimum-lot rounding can exceed the intended 1% risk.
- A few terminal balances slightly below zero are native tester loss/cost overshoots near account depletion. They are reported without clipping, not a claim about a live broker's negative-balance protection or a debt owed.
- Control = past-donor synthetic levels, formation-clock/direction/ATR-distance matched approximately. Not exact matched touch times, not paired trade counts, not proof of causality. Warmup failures and missing profiles are not zero risk.
- 1y / 6m / 3y / 5y are overlapping descriptive windows, not untouched out-of-sample tests. Choosing the best of ten real variants itself introduces selection bias.

## Gate

| Asset / model | 3y + 5y raw gate |
|---|---|
| US30-touch | FAIL |
| US30-retest | FAIL |
| US100-touch | FAIL |
| US100-retest | FAIL |
| US500-touch | FAIL |
| US500-retest | FAIL |
| XAU-touch | FAIL |
| XAU-retest | FAIL |
| BTC-touch | FAIL |
| BTC-retest | FAIL |

## 1y: 2025.09.27 to 2026.09.27 (end exclusive)

| Asset | Entry | Return | Trades | /mo | /day | Win | Net PF | Equity DD | Balance DD | Max W/L |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| US30 | touch | +45.57% | 1110 | 92.6 | 4.27 | 53.42% | 1.05 | 33.27% | 32.82% | 13/7 |
| US30 | retest | -2.76% | 456 | 38.0 | 1.75 | 50.88% | 0.99 | 19.02% | 18.49% | 8/7 |
| US30 | touch-control | +92.58% | 1122 | 93.6 | 4.32 | 55.08% | 1.13 | 18.59% | 18.18% | 15/6 |
| US30 | retest-control | -3.37% | 454 | 37.9 | 1.75 | 51.32% | 0.99 | 24.73% | 24.22% | 9/7 |
| US100 | touch | -24.29% | 1119 | 93.3 | 4.30 | 51.39% | 0.95 | 43.10% | 42.98% | 8/9 |
| US100 | retest | -19.26% | 475 | 39.6 | 1.83 | 49.26% | 0.91 | 23.58% | 23.10% | 7/7 |
| US100 | touch-control | -53.59% | 1105 | 92.1 | 4.25 | 48.78% | 0.88 | 59.71% | 59.71% | 8/11 |
| US100 | retest-control | -15.54% | 443 | 36.9 | 1.70 | 50.11% | 0.93 | 23.33% | 22.90% | 9/6 |
| US500 | touch | -79.11% | 1100 | 91.7 | 4.23 | 47.45% | 0.72 | 81.39% | 81.18% | 7/15 |
| US500 | retest | -48.08% | 451 | 37.6 | 1.73 | 47.45% | 0.73 | 51.16% | 50.83% | 8/6 |
| US500 | touch-control | -81.77% | 1088 | 90.7 | 4.18 | 46.60% | 0.70 | 82.37% | 82.28% | 7/8 |
| US500 | retest-control | -54.71% | 439 | 36.6 | 1.69 | 45.33% | 0.69 | 55.67% | 55.38% | 7/7 |
| XAU | touch | +1.96% | 979 | 81.6 | 3.77 | 53.32% | 1.00 | 30.07% | 30.07% | 9/6 |
| XAU | retest | +12.51% | 373 | 31.1 | 1.43 | 52.82% | 1.06 | 14.74% | 13.67% | 10/8 |
| XAU | touch-control | +13.93% | 975 | 81.3 | 3.75 | 52.31% | 1.03 | 30.74% | 30.63% | 10/9 |
| XAU | retest-control | +3.39% | 366 | 30.5 | 1.41 | 50.82% | 1.02 | 30.00% | 29.60% | 12/7 |
| BTC | touch | +109.18% | 1338 | 111.6 | 3.67 | 57.77% | 1.11 | 27.29% | 26.61% | 14/6 |
| BTC | retest | -38.43% | 496 | 41.4 | 1.36 | 47.38% | 0.82 | 38.70% | 38.43% | 10/11 |
| BTC | touch-control | -53.62% | 1347 | 112.3 | 3.69 | 50.63% | 0.90 | 56.70% | 56.34% | 11/13 |
| BTC | retest-control | -19.14% | 528 | 44.0 | 1.45 | 50.19% | 0.92 | 32.52% | 32.10% | 7/8 |

## 6m: 2026.03.27 to 2026.09.27 (end exclusive)

| Asset | Entry | Return | Trades | /mo | /day | Win | Net PF | Equity DD | Balance DD | Max W/L |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| US30 | touch | -12.28% | 546 | 90.3 | 4.17 | 50.37% | 0.96 | 33.28% | 32.82% | 7/6 |
| US30 | retest | -0.59% | 223 | 36.9 | 1.70 | 51.57% | 0.99 | 11.87% | 11.84% | 8/7 |
| US30 | touch-control | +44.42% | 559 | 92.5 | 4.27 | 55.10% | 1.13 | 18.60% | 18.19% | 15/5 |
| US30 | retest-control | -3.59% | 226 | 37.4 | 1.73 | 50.88% | 0.97 | 24.72% | 24.20% | 8/7 |
| US100 | touch | -25.89% | 561 | 92.8 | 4.28 | 49.20% | 0.90 | 43.13% | 43.01% | 6/9 |
| US100 | retest | -9.29% | 220 | 36.4 | 1.68 | 49.09% | 0.92 | 22.03% | 21.71% | 5/7 |
| US100 | touch-control | -41.51% | 563 | 93.1 | 4.30 | 46.89% | 0.83 | 52.99% | 52.99% | 8/11 |
| US100 | retest-control | -2.51% | 219 | 36.2 | 1.67 | 51.14% | 0.98 | 22.93% | 21.99% | 9/6 |
| US500 | touch | -50.26% | 541 | 89.5 | 4.13 | 47.69% | 0.79 | 57.32% | 56.85% | 7/15 |
| US500 | retest | -14.65% | 215 | 35.6 | 1.64 | 51.16% | 0.87 | 24.81% | 24.24% | 8/6 |
| US500 | touch-control | -45.93% | 542 | 89.7 | 4.14 | 48.15% | 0.81 | 53.74% | 53.70% | 7/8 |
| US500 | retest-control | -29.91% | 214 | 35.4 | 1.63 | 45.33% | 0.73 | 32.62% | 32.59% | 7/7 |
| XAU | touch | -21.63% | 491 | 81.2 | 3.75 | 51.12% | 0.91 | 30.39% | 30.39% | 9/6 |
| XAU | retest | +5.56% | 183 | 30.3 | 1.40 | 52.46% | 1.06 | 11.91% | 10.71% | 8/8 |
| XAU | touch-control | +4.75% | 497 | 82.2 | 3.79 | 51.91% | 1.02 | 20.44% | 20.40% | 10/6 |
| XAU | retest-control | +29.19% | 177 | 29.3 | 1.35 | 57.06% | 1.33 | 9.42% | 9.38% | 12/7 |
| BTC | touch | +41.64% | 681 | 112.6 | 3.70 | 59.03% | 1.11 | 14.07% | 14.07% | 13/6 |
| BTC | retest | -26.83% | 245 | 40.5 | 1.33 | 46.53% | 0.78 | 27.68% | 27.68% | 10/11 |
| BTC | touch-control | -34.36% | 665 | 110.0 | 3.61 | 50.98% | 0.89 | 34.45% | 34.36% | 8/9 |
| BTC | retest-control | -9.15% | 260 | 43.0 | 1.41 | 50.38% | 0.93 | 21.91% | 21.41% | 7/8 |

## 3y: 2023.09.27 to 2026.09.27 (end exclusive)

| Asset | Entry | Return | Trades | /mo | /day | Win | Net PF | Equity DD | Balance DD | Max W/L |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| US30 | touch | -96.95% | 3356 | 93.2 | 4.29 | 47.02% | 0.56 | 98.97% | 98.93% | 16/18 |
| US30 | retest | -93.13% | 1387 | 38.5 | 1.77 | 42.61% | 0.49 | 94.03% | 93.97% | 8/19 |
| US30 | touch-control | -99.95% | 2201 | 61.1 | 2.81 | 40.85% | 0.46 | 99.95% | 99.95% | 8/20 |
| US30 | retest-control | -89.01% | 1343 | 37.3 | 1.72 | 44.15% | 0.58 | 90.27% | 90.24% | 9/13 |
| US100 | touch | -99.05% | 3343 | 92.8 | 4.27 | 46.13% | 0.44 | 99.28% | 99.28% | 10/15 |
| US100 | retest | -95.00% | 1384 | 38.4 | 1.77 | 41.91% | 0.46 | 95.28% | 95.25% | 8/16 |
| US100 | touch-control | -100.00% | 3031 | 84.2 | 3.87 | 43.02% | 0.46 | 100.00% | 100.00% | 8/16 |
| US100 | retest-control | -90.10% | 1324 | 36.8 | 1.69 | 44.18% | 0.57 | 90.78% | 90.73% | 9/11 |
| US500 | touch | -99.99% | 1607 | 44.6 | 2.05 | 36.03% | 0.33 | 99.99% | 99.99% | 7/15 |
| US500 | retest | -99.14% | 1333 | 37.0 | 1.70 | 37.73% | 0.27 | 99.21% | 99.21% | 8/15 |
| US500 | touch-control | -99.99% | 1470 | 40.8 | 1.88 | 34.01% | 0.34 | 99.99% | 99.99% | 9/16 |
| US500 | retest-control | -99.20% | 1336 | 37.1 | 1.71 | 37.65% | 0.25 | 99.20% | 99.20% | 7/16 |
| XAU | touch | -51.43% | 3013 | 83.7 | 3.85 | 51.24% | 0.96 | 62.95% | 62.76% | 9/10 |
| XAU | retest | -43.20% | 1169 | 32.5 | 1.49 | 49.36% | 0.89 | 55.57% | 55.29% | 10/9 |
| XAU | touch-control | -81.49% | 3050 | 84.7 | 3.90 | 49.48% | 0.85 | 87.58% | 87.54% | 10/11 |
| XAU | retest-control | -41.29% | 1160 | 32.2 | 1.48 | 49.14% | 0.89 | 58.28% | 58.07% | 12/10 |
| BTC | touch | -86.02% | 4043 | 112.3 | 3.69 | 51.03% | 0.81 | 95.64% | 95.60% | 14/14 |
| BTC | retest | -94.45% | 1561 | 43.4 | 1.42 | 43.50% | 0.65 | 94.49% | 94.49% | 10/13 |
| BTC | touch-control | -99.99% | 1540 | 42.8 | 1.41 | 36.95% | 0.52 | 99.99% | 99.99% | 6/11 |
| BTC | retest-control | -95.37% | 1645 | 45.7 | 1.50 | 43.47% | 0.59 | 96.00% | 95.98% | 11/12 |

## 5y: 2021.09.27 to 2026.09.27 (end exclusive)

| Asset | Entry | Return | Trades | /mo | /day | Win | Net PF | Equity DD | Balance DD | Max W/L |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| US30 | touch | -99.96% | 2528 | 42.1 | 1.94 | 40.86% | 0.62 | 99.96% | 99.96% | 7/14 |
| US30 | retest | -99.96% | 1458 | 24.3 | 1.12 | 34.22% | 0.52 | 99.96% | 99.96% | 7/19 |
| US30 | touch-control | -99.96% | 2302 | 38.4 | 1.76 | 39.79% | 0.63 | 99.96% | 99.96% | 7/12 |
| US30 | retest-control | -99.49% | 2214 | 36.9 | 1.70 | 41.33% | 0.54 | 99.76% | 99.76% | 9/13 |
| US100 | touch | -99.98% | 2616 | 43.6 | 2.00 | 41.67% | 0.76 | 99.98% | 99.98% | 17/14 |
| US100 | retest | -100.00% | 1507 | 25.1 | 1.15 | 34.51% | 0.50 | 100.00% | 100.00% | 8/16 |
| US100 | touch-control | -99.98% | 2127 | 35.5 | 1.63 | 38.22% | 0.55 | 99.98% | 99.98% | 7/20 |
| US100 | retest-control | -99.98% | 1598 | 26.6 | 1.22 | 35.86% | 0.50 | 99.98% | 99.98% | 6/18 |
| US500 | touch | -99.99% | 1983 | 33.1 | 1.52 | 38.17% | 0.59 | 99.99% | 99.99% | 8/16 |
| US500 | retest | -100.00% | 1236 | 20.6 | 0.95 | 29.77% | 0.42 | 100.00% | 100.00% | 5/23 |
| US500 | touch-control | -99.99% | 1630 | 27.2 | 1.25 | 35.09% | 0.34 | 99.99% | 99.99% | 7/17 |
| US500 | retest-control | -99.98% | 1238 | 20.6 | 0.95 | 29.24% | 0.39 | 99.98% | 99.98% | 5/16 |
| XAU | touch | -95.11% | 5108 | 85.1 | 3.91 | 49.61% | 0.82 | 97.23% | 97.14% | 9/10 |
| XAU | retest | -86.71% | 1987 | 33.1 | 1.52 | 47.01% | 0.77 | 90.23% | 90.15% | 10/9 |
| XAU | touch-control | -100.00% | 3447 | 57.5 | 2.64 | 46.01% | 0.77 | 100.00% | 100.00% | 9/11 |
| XAU | retest-control | -87.42% | 1999 | 33.3 | 1.53 | 46.97% | 0.77 | 92.27% | 92.26% | 12/12 |
| BTC | touch | -99.99% | 3065 | 51.1 | 1.68 | 45.51% | 0.74 | 99.99% | 99.99% | 8/16 |
| BTC | retest | -100.01% | 1540 | 25.7 | 0.84 | 37.86% | 0.58 | 100.01% | 100.01% | 7/13 |
| BTC | touch-control | -100.00% | 1931 | 32.2 | 1.06 | 38.68% | 0.53 | 100.00% | 100.00% | 9/18 |
| BTC | retest-control | -99.99% | 1517 | 25.3 | 0.83 | 36.45% | 0.55 | 99.99% | 99.99% | 10/15 |

## One-year uncertainty, costs and sizing

| Asset | Model | Win rate 95% interval | Average W/L streak | Commission | Swap | Median / max risk multiplier | Trades above 1.1% planned-stop risk |
|---|---|---|---|---:|---:|---|---:|
| BTC | retest | 43.0–51.8% | 2.08/2.29 | $-1493.40 | $0.00 | 1.01x / 1.06x | 0 |
| BTC | touch | 55.1–60.4% | 2.25/1.65 | $-9982.18 | $0.00 | 1.00x / 1.04x | 0 |
| US100 | retest | 44.8–53.7% | 1.98/2.04 | $-1356.85 | $-74.76 | 1.00x / 1.01x | 0 |
| US100 | touch | 48.5–54.3% | 2.09/1.98 | $-3555.69 | $0.00 | 1.00x / 1.01x | 0 |
| US30 | retest | 46.3–55.4% | 1.90/1.84 | $-1222.61 | $0.00 | 1.00x / 1.01x | 0 |
| US30 | touch | 50.5–56.3% | 2.22/1.94 | $-5095.43 | $0.00 | 1.00x / 1.01x | 0 |
| US500 | retest | 42.9–52.1% | 1.80/1.98 | $-2224.12 | $0.00 | 1.00x / 1.00x | 0 |
| US500 | touch | 44.5–50.4% | 1.91/2.10 | $-3912.84 | $0.00 | 1.00x / 1.00x | 0 |
| XAU | retest | 47.7–57.8% | 2.19/1.96 | $-399.30 | $0.00 | 1.03x / 1.33x | 16 |
| XAU | touch | 50.2–56.4% | 2.17/1.90 | $-1342.36 | $0.00 | 1.02x / 1.33x | 7 |

Wilson intervals treat trades as independent and are descriptive; serial dependence makes them optimistic. Risk is at submission quote, excluding costs/slippage; not a hard loss cap.

## One-year fills and execution limitations

| Asset | Model | Failed entries | Failed timed-close attempts | Mean entry slippage, USD | Largest adverse entry slip, USD |
|---|---|---:|---:|---:|---:|
| BTC | retest | 0 | 0 | -0.02 | 31.80 |
| BTC | touch | 6 | 0 | 10.71 | 191.75 |
| US100 | retest | 1 | 0 | 0.03 | 11.89 |
| US100 | touch | 7 | 0 | 1.85 | 60.18 |
| US30 | retest | 0 | 50 | -0.43 | 29.51 |
| US30 | touch | 10 | 57 | 1.28 | 128.87 |
| US500 | retest | 1 | 45 | 0.02 | 13.90 |
| US500 | touch | 4 | 57 | 0.27 | 30.76 |
| XAU | retest | 1 | 48 | 0.38 | 15.54 |
| XAU | touch | 5 | 0 | 6.07 | 116.90 |

Positive slippage means adverse entry price versus submission quote; negative means improvement. Already reflected in native returns, not added/subtracted twice. Exit slippage is not measured separately. Native journal flag occurrences below can repeat between agent/terminal logs; EA counters above are the actual attempt counts. Missing-profile and setup-expiry counters include warmup.

## One-year level-family breakdown (descriptive, not separately tested variants)

| Asset | Model | Family | Trades | Win | Net PF | Net P/L USD |
|---|---|---|---:|---:|---:|---:|
| BTC | retest | PD | 104 | 46.15% | 0.81 | -855.62 |
| BTC | retest | AS | 179 | 50.84% | 0.92 | -568.16 |
| BTC | retest | LD | 201 | 45.77% | 0.78 | -2035.96 |
| BTC | retest | PW | 12 | 33.33% | 0.38 | -383.60 |
| BTC | touch | PD | 284 | 64.08% | 1.43 | +7430.92 |
| BTC | touch | AS | 470 | 58.51% | 1.16 | +5117.84 |
| BTC | touch | LD | 549 | 53.73% | 0.96 | -1893.92 |
| BTC | touch | PW | 35 | 60.00% | 1.10 | +262.67 |
| US100 | retest | PD | 127 | 60.63% | 1.48 | +2133.53 |
| US100 | retest | AS | 163 | 49.08% | 0.90 | -756.64 |
| US100 | retest | LD | 168 | 42.86% | 0.71 | -2592.86 |
| US100 | retest | PW | 17 | 29.41% | 0.38 | -710.33 |
| US100 | touch | PD | 289 | 59.52% | 1.34 | +3746.18 |
| US100 | touch | AS | 380 | 49.74% | 0.87 | -2441.93 |
| US100 | touch | LD | 412 | 47.57% | 0.83 | -3454.95 |
| US100 | touch | PW | 38 | 47.37% | 0.85 | -277.89 |
| US30 | retest | PD | 111 | 50.45% | 1.00 | +7.97 |
| US30 | retest | AS | 162 | 48.77% | 0.89 | -983.13 |
| US30 | retest | LD | 164 | 53.05% | 1.08 | +634.37 |
| US30 | retest | PW | 19 | 52.63% | 1.08 | +64.69 |
| US30 | touch | PD | 262 | 54.20% | 1.15 | +2705.63 |
| US30 | touch | AS | 394 | 50.76% | 0.94 | -1792.23 |
| US30 | touch | LD | 418 | 55.74% | 1.15 | +4448.14 |
| US30 | touch | PW | 36 | 50.00% | 0.74 | -804.46 |
| US500 | retest | PD | 108 | 48.15% | 0.75 | -1034.13 |
| US500 | retest | AS | 175 | 48.00% | 0.72 | -1923.13 |
| US500 | retest | LD | 149 | 46.98% | 0.75 | -1455.80 |
| US500 | retest | PW | 19 | 42.11% | 0.52 | -394.94 |
| US500 | touch | PD | 286 | 46.85% | 0.76 | -1759.74 |
| US500 | touch | AS | 372 | 48.12% | 0.73 | -2624.31 |
| US500 | touch | LD | 404 | 47.03% | 0.69 | -3310.97 |
| US500 | touch | PW | 38 | 50.00% | 0.75 | -216.14 |
| XAU | retest | PD | 111 | 49.55% | 0.97 | -162.13 |
| XAU | retest | AS | 103 | 56.31% | 1.17 | +866.10 |
| XAU | retest | LD | 149 | 52.35% | 1.04 | +366.30 |
| XAU | retest | PW | 10 | 60.00% | 1.38 | +180.90 |
| XAU | touch | PD | 259 | 57.14% | 1.15 | +2213.81 |
| XAU | touch | AS | 293 | 53.24% | 1.02 | +438.35 |
| XAU | touch | LD | 388 | 48.71% | 0.83 | -4346.03 |
| XAU | touch | PW | 39 | 74.36% | 2.45 | +1890.24 |

PD = previous day, AS = completed Asia, LD = completed London, PW = previous week. Family counts reflect fixed collision priority and the combined one-position cap; they are NOT results of standalone family EAs.

## Native data and execution audit

### BTC / retest / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-retest-1y forms=4167 missing=5 noDonor=0 touches=1431 orders=496 busy=26 skips=0 entryFails=0 closeFails=0 retestExpired=1628 quotes=181980574 volumeQuotes=0 tradeFlags=0
### BTC / retest / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-retest-3y forms=8757 missing=5 noDonor=0 touches=4321 orders=1561 busy=102 skips=2 entryFails=0 closeFails=0 retestExpired=3446 quotes=291577609 volumeQuotes=0 tradeFlags=0
### BTC / retest / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-retest-5y forms=13337 missing=6 noDonor=0 touches=7262 orders=1540 busy=99 skips=984 entryFails=0 closeFails=0 retestExpired=5364 quotes=372678012 volumeQuotes=0 tradeFlags=0
### BTC / retest / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-retest-6m forms=3034 missing=3 noDonor=0 touches=729 orders=245 busy=10 skips=0 entryFails=0 closeFails=0 retestExpired=1192 quotes=96801840 volumeQuotes=0 tradeFlags=0
### BTC / retest-control / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-retest-control-1y forms=3996 missing=5 noDonor=171 touches=1399 orders=528 busy=19 skips=0 entryFails=0 closeFails=0 retestExpired=1518 quotes=181980628 volumeQuotes=0 tradeFlags=0
### BTC / retest-control / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-retest-control-3y forms=8482 missing=5 noDonor=275 touches=4278 orders=1645 busy=83 skips=0 entryFails=0 closeFails=0 retestExpired=3292 quotes=291577657 volumeQuotes=0 tradeFlags=0
### BTC / retest-control / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-retest-control-5y forms=12974 missing=6 noDonor=363 touches=7210 orders=1517 busy=79 skips=1172 entryFails=0 closeFails=0 retestExpired=5077 quotes=372678033 volumeQuotes=0 tradeFlags=0
### BTC / retest-control / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-retest-control-6m forms=2895 missing=3 noDonor=139 touches=692 orders=260 busy=9 skips=0 entryFails=0 closeFails=0 retestExpired=1105 quotes=96801870 volumeQuotes=0 tradeFlags=0
### BTC / touch / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 36, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-touch-1y forms=4167 missing=5 noDonor=0 touches=1431 orders=1338 busy=87 skips=0 entryFails=6 closeFails=0 retestExpired=0 quotes=181977568 volumeQuotes=0 tradeFlags=0
### BTC / touch / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 36, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-touch-3y forms=8757 missing=5 noDonor=0 touches=4321 orders=4043 busy=269 skips=3 entryFails=6 closeFails=0 retestExpired=0 quotes=291574012 volumeQuotes=0 tradeFlags=0
### BTC / touch / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-touch-5y forms=13337 missing=6 noDonor=0 touches=7262 orders=3065 busy=189 skips=4008 entryFails=0 closeFails=0 retestExpired=0 quotes=372677972 volumeQuotes=0 tradeFlags=0
### BTC / touch / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 24, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-touch-6m forms=3034 missing=3 noDonor=0 touches=729 orders=681 busy=44 skips=0 entryFails=4 closeFails=0 retestExpired=0 quotes=96799674 volumeQuotes=0 tradeFlags=0
### BTC / touch-control / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-touch-control-1y forms=3996 missing=5 noDonor=171 touches=1399 orders=1347 busy=52 skips=0 entryFails=0 closeFails=0 retestExpired=0 quotes=181978286 volumeQuotes=0 tradeFlags=0
### BTC / touch-control / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-touch-control-3y forms=8482 missing=5 noDonor=275 touches=4278 orders=1540 busy=88 skips=2650 entryFails=0 closeFails=0 retestExpired=0 quotes=291577965 volumeQuotes=0 tradeFlags=0
### BTC / touch-control / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-touch-control-5y forms=12974 missing=6 noDonor=363 touches=7210 orders=1931 busy=102 skips=5177 entryFails=0 closeFails=0 retestExpired=0 quotes=372678012 volumeQuotes=0 tradeFlags=0
### BTC / touch-control / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=BTC-touch-control-6m forms=2895 missing=3 noDonor=139 touches=692 orders=665 busy=27 skips=0 entryFails=0 closeFails=0 retestExpired=0 quotes=96800219 volumeQuotes=0 tradeFlags=0
### US100 / retest / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 6, "margin_call": 0}`
- LC_SUMMARY tag=US100-retest-1y forms=3156 missing=201 noDonor=0 touches=1177 orders=475 busy=27 skips=0 entryFails=1 closeFails=0 retestExpired=1231 quotes=166983348 volumeQuotes=0 tradeFlags=0
### US100 / retest / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 18, "margin_call": 0}`
- LC_SUMMARY tag=US100-retest-3y forms=6648 missing=409 noDonor=0 touches=3588 orders=1384 busy=95 skips=5 entryFails=3 closeFails=0 retestExpired=2698 quotes=197804300 volumeQuotes=0 tradeFlags=0
### US100 / retest / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 12, "margin_call": 0}`
- LC_SUMMARY tag=US100-retest-5y forms=10128 missing=618 noDonor=0 touches=5997 orders=1507 busy=117 skips=815 entryFails=2 closeFails=0 retestExpired=4162 quotes=225931367 volumeQuotes=0 tradeFlags=0
### US100 / retest / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US100-retest-6m forms=2306 missing=146 noDonor=0 touches=590 orders=220 busy=14 skips=0 entryFails=0 closeFails=0 retestExpired=899 quotes=124397210 volumeQuotes=0 tradeFlags=0
### US100 / retest-control / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 6, "margin_call": 0}`
- LC_SUMMARY tag=US100-retest-control-1y forms=3051 missing=201 noDonor=105 touches=1164 orders=443 busy=24 skips=0 entryFails=1 closeFails=0 retestExpired=1245 quotes=166983542 volumeQuotes=0 tradeFlags=0
### US100 / retest-control / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 46, "margin_call": 0}`
- LC_SUMMARY tag=US100-retest-control-3y forms=6501 missing=409 noDonor=147 touches=3577 orders=1324 busy=95 skips=6 entryFails=5 closeFails=4 retestExpired=2682 quotes=197804500 volumeQuotes=0 tradeFlags=0
### US100 / retest-control / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 40, "margin_call": 0}`
- LC_SUMMARY tag=US100-retest-control-5y forms=9905 missing=618 noDonor=223 touches=5974 orders=1598 busy=94 skips=713 entryFails=4 closeFails=4 retestExpired=4139 quotes=225931331 volumeQuotes=0 tradeFlags=0
### US100 / retest-control / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US100-retest-control-6m forms=2225 missing=146 noDonor=81 touches=594 orders=219 busy=12 skips=0 entryFails=0 closeFails=0 retestExpired=906 quotes=124397259 volumeQuotes=0 tradeFlags=0
### US100 / touch / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 36, "invalid_volume": 0, "market_closed": 6, "margin_call": 0}`
- LC_SUMMARY tag=US100-touch-1y forms=3156 missing=201 noDonor=0 touches=1177 orders=1119 busy=51 skips=0 entryFails=7 closeFails=0 retestExpired=0 quotes=166979479 volumeQuotes=0 tradeFlags=0
### US100 / touch / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 36, "invalid_volume": 0, "market_closed": 30, "margin_call": 0}`
- LC_SUMMARY tag=US100-touch-3y forms=6648 missing=409 noDonor=0 touches=3588 orders=3343 busy=209 skips=25 entryFails=11 closeFails=0 retestExpired=0 quotes=197799992 volumeQuotes=0 tradeFlags=0
### US100 / touch / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 18, "margin_call": 0}`
- LC_SUMMARY tag=US100-touch-5y forms=10128 missing=618 noDonor=0 touches=5997 orders=2616 busy=219 skips=3159 entryFails=3 closeFails=0 retestExpired=0 quotes=225931396 volumeQuotes=0 tradeFlags=0
### US100 / touch / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 12, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US100-touch-6m forms=2306 missing=146 noDonor=0 touches=590 orders=561 busy=27 skips=0 entryFails=2 closeFails=0 retestExpired=0 quotes=124394326 volumeQuotes=0 tradeFlags=0
### US100 / touch-control / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 18, "invalid_volume": 0, "market_closed": 6, "margin_call": 0}`
- LC_SUMMARY tag=US100-touch-control-1y forms=3051 missing=201 noDonor=105 touches=1164 orders=1105 busy=55 skips=0 entryFails=4 closeFails=0 retestExpired=0 quotes=166980846 volumeQuotes=0 tradeFlags=0
### US100 / touch-control / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 132, "margin_call": 0}`
- LC_SUMMARY tag=US100-touch-control-3y forms=6501 missing=409 noDonor=147 touches=3577 orders=3031 busy=176 skips=366 entryFails=4 closeFails=27 retestExpired=0 quotes=197803310 volumeQuotes=0 tradeFlags=0
### US100 / touch-control / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 6, "margin_call": 0}`
- LC_SUMMARY tag=US100-touch-control-5y forms=9905 missing=618 noDonor=223 touches=5974 orders=2127 busy=86 skips=3760 entryFails=1 closeFails=0 retestExpired=0 quotes=225931398 volumeQuotes=0 tradeFlags=0
### US100 / touch-control / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 18, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US100-touch-control-6m forms=2225 missing=146 noDonor=81 touches=594 orders=563 busy=28 skips=0 entryFails=3 closeFails=0 retestExpired=0 quotes=124395325 volumeQuotes=0 tradeFlags=0
### US30 / retest / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 200, "margin_call": 0}`
- LC_SUMMARY tag=US30-retest-1y forms=3164 missing=200 noDonor=0 touches=1190 orders=456 busy=34 skips=0 entryFails=0 closeFails=50 retestExpired=1286 quotes=112249242 volumeQuotes=0 tradeFlags=0
### US30 / retest / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 234, "margin_call": 0}`
- LC_SUMMARY tag=US30-retest-3y forms=6652 missing=408 noDonor=0 touches=3649 orders=1387 busy=88 skips=7 entryFails=3 closeFails=54 retestExpired=2753 quotes=135107372 volumeQuotes=0 tradeFlags=0
### US30 / retest / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 24, "margin_call": 0}`
- LC_SUMMARY tag=US30-retest-5y forms=10130 missing=617 noDonor=0 touches=6072 orders=1458 busy=112 skips=836 entryFails=4 closeFails=0 retestExpired=4216 quotes=157191642 volumeQuotes=0 tradeFlags=0
### US30 / retest / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US30-retest-6m forms=2307 missing=145 noDonor=0 touches=589 orders=223 busy=12 skips=0 entryFails=0 closeFails=0 retestExpired=953 quotes=79811030 volumeQuotes=0 tradeFlags=0
### US30 / retest-control / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 200, "margin_call": 0}`
- LC_SUMMARY tag=US30-retest-control-1y forms=3042 missing=200 noDonor=122 touches=1196 orders=454 busy=29 skips=0 entryFails=0 closeFails=50 retestExpired=1244 quotes=112249231 volumeQuotes=0 tradeFlags=0
### US30 / retest-control / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 232, "margin_call": 0}`
- LC_SUMMARY tag=US30-retest-control-3y forms=6477 missing=408 noDonor=175 touches=3592 orders=1343 busy=79 skips=6 entryFails=2 closeFails=55 retestExpired=2737 quotes=135107378 volumeQuotes=0 tradeFlags=0
### US30 / retest-control / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 232, "margin_call": 0}`
- LC_SUMMARY tag=US30-retest-control-5y forms=9873 missing=617 noDonor=257 touches=5979 orders=2214 busy=129 skips=9 entryFails=2 closeFails=55 retestExpired=4113 quotes=157190738 volumeQuotes=0 tradeFlags=0
### US30 / retest-control / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US30-retest-control-6m forms=2222 missing=145 noDonor=85 touches=607 orders=226 busy=18 skips=0 entryFails=0 closeFails=0 retestExpired=920 quotes=79810999 volumeQuotes=0 tradeFlags=0
### US30 / touch / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 48, "invalid_volume": 0, "market_closed": 240, "margin_call": 0}`
- LC_SUMMARY tag=US30-touch-1y forms=3164 missing=200 noDonor=0 touches=1190 orders=1110 busy=70 skips=0 entryFails=10 closeFails=57 retestExpired=0 quotes=112246876 volumeQuotes=0 tradeFlags=0
### US30 / touch / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 48, "invalid_volume": 0, "market_closed": 322, "margin_call": 0}`
- LC_SUMMARY tag=US30-touch-3y forms=6652 missing=408 noDonor=0 touches=3649 orders=3356 busy=247 skips=35 entryFails=11 closeFails=76 retestExpired=0 quotes=135104635 volumeQuotes=0 tradeFlags=0
### US30 / touch / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US30-touch-5y forms=10130 missing=617 noDonor=0 touches=6072 orders=2528 busy=192 skips=3352 entryFails=0 closeFails=0 retestExpired=0 quotes=157191650 volumeQuotes=0 tradeFlags=0
### US30 / touch / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 36, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US30-touch-6m forms=2307 missing=145 noDonor=0 touches=589 orders=546 busy=37 skips=0 entryFails=6 closeFails=0 retestExpired=0 quotes=79809579 volumeQuotes=0 tradeFlags=0
### US30 / touch-control / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 48, "invalid_volume": 0, "market_closed": 240, "margin_call": 0}`
- LC_SUMMARY tag=US30-touch-control-1y forms=3042 missing=200 noDonor=122 touches=1196 orders=1122 busy=66 skips=0 entryFails=8 closeFails=60 retestExpired=0 quotes=112247104 volumeQuotes=0 tradeFlags=0
### US30 / touch-control / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 38, "margin_call": 0}`
- LC_SUMMARY tag=US30-touch-control-3y forms=6477 missing=408 noDonor=175 touches=3592 orders=2201 busy=144 skips=1246 entryFails=1 closeFails=8 retestExpired=0 quotes=135107869 volumeQuotes=0 tradeFlags=0
### US30 / touch-control / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 6, "margin_call": 0}`
- LC_SUMMARY tag=US30-touch-control-5y forms=9873 missing=617 noDonor=257 touches=5979 orders=2302 busy=120 skips=3556 entryFails=1 closeFails=0 retestExpired=0 quotes=157191650 volumeQuotes=0 tradeFlags=0
### US30 / touch-control / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 30, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US30-touch-control-6m forms=2222 missing=145 noDonor=85 touches=607 orders=559 busy=43 skips=0 entryFails=5 closeFails=0 retestExpired=0 quotes=79809706 volumeQuotes=0 tradeFlags=0
### US500 / retest / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 186, "margin_call": 0}`
- LC_SUMMARY tag=US500-retest-1y forms=3157 missing=200 noDonor=0 touches=1168 orders=451 busy=29 skips=0 entryFails=1 closeFails=45 retestExpired=1229 quotes=73977580 volumeQuotes=0 tradeFlags=0
### US500 / retest / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 216, "margin_call": 0}`
- LC_SUMMARY tag=US500-retest-3y forms=6639 missing=410 noDonor=0 touches=3593 orders=1333 busy=97 skips=60 entryFails=6 closeFails=45 retestExpired=2664 quotes=88765737 volumeQuotes=0 tradeFlags=0
### US500 / retest / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 6, "margin_call": 0}`
- LC_SUMMARY tag=US500-retest-5y forms=10106 missing=620 noDonor=0 touches=5979 orders=1236 busy=97 skips=1088 entryFails=1 closeFails=0 retestExpired=4146 quotes=105047133 volumeQuotes=0 tradeFlags=0
### US500 / retest / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US500-retest-6m forms=2305 missing=145 noDonor=0 touches=581 orders=215 busy=16 skips=0 entryFails=0 closeFails=0 retestExpired=914 quotes=50062098 volumeQuotes=0 tradeFlags=0
### US500 / retest-control / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 6, "margin_call": 0}`
- LC_SUMMARY tag=US500-retest-control-1y forms=3032 missing=200 noDonor=125 touches=1146 orders=439 busy=25 skips=0 entryFails=1 closeFails=0 retestExpired=1205 quotes=73977582 volumeQuotes=0 tradeFlags=0
### US500 / retest-control / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 24, "margin_call": 0}`
- LC_SUMMARY tag=US500-retest-control-3y forms=6468 missing=410 noDonor=171 touches=3542 orders=1336 busy=80 skips=56 entryFails=4 closeFails=0 retestExpired=2609 quotes=88765742 volumeQuotes=0 tradeFlags=0
### US500 / retest-control / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 6, "margin_call": 0}`
- LC_SUMMARY tag=US500-retest-control-5y forms=9850 missing=620 noDonor=256 touches=5903 orders=1238 busy=73 skips=1146 entryFails=1 closeFails=0 retestExpired=3942 quotes=105047133 volumeQuotes=0 tradeFlags=0
### US500 / retest-control / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US500-retest-control-6m forms=2217 missing=145 noDonor=88 touches=574 orders=214 busy=11 skips=0 entryFails=0 closeFails=0 retestExpired=891 quotes=50062091 volumeQuotes=0 tradeFlags=0
### US500 / touch / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 24, "invalid_volume": 0, "market_closed": 228, "margin_call": 0}`
- LC_SUMMARY tag=US500-touch-1y forms=3157 missing=200 noDonor=0 touches=1168 orders=1100 busy=64 skips=0 entryFails=4 closeFails=57 retestExpired=0 quotes=73976306 volumeQuotes=0 tradeFlags=0
### US500 / touch / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 30, "margin_call": 0}`
- LC_SUMMARY tag=US500-touch-3y forms=6639 missing=410 noDonor=0 touches=3593 orders=1607 busy=102 skips=1879 entryFails=5 closeFails=0 retestExpired=0 quotes=88766128 volumeQuotes=0 tradeFlags=0
### US500 / touch / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US500-touch-5y forms=10106 missing=620 noDonor=0 touches=5979 orders=1983 busy=169 skips=3827 entryFails=0 closeFails=0 retestExpired=0 quotes=105047133 volumeQuotes=0 tradeFlags=0
### US500 / touch / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 18, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US500-touch-6m forms=2305 missing=145 noDonor=0 touches=581 orders=541 busy=37 skips=0 entryFails=3 closeFails=0 retestExpired=0 quotes=50061275 volumeQuotes=0 tradeFlags=0
### US500 / touch-control / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 6, "invalid_volume": 0, "market_closed": 80, "margin_call": 0}`
- LC_SUMMARY tag=US500-touch-control-1y forms=3032 missing=200 noDonor=125 touches=1146 orders=1088 busy=57 skips=0 entryFails=1 closeFails=20 retestExpired=0 quotes=73976370 volumeQuotes=0 tradeFlags=0
### US500 / touch-control / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 60, "margin_call": 0}`
- LC_SUMMARY tag=US500-touch-control-3y forms=6468 missing=410 noDonor=171 touches=3542 orders=1470 busy=82 skips=1986 entryFails=4 closeFails=9 retestExpired=0 quotes=88766202 volumeQuotes=0 tradeFlags=0
### US500 / touch-control / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 6, "margin_call": 0}`
- LC_SUMMARY tag=US500-touch-control-5y forms=9850 missing=620 noDonor=256 touches=5903 orders=1630 busy=76 skips=4196 entryFails=1 closeFails=0 retestExpired=0 quotes=105047133 volumeQuotes=0 tradeFlags=0
### US500 / touch-control / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 6, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=US500-touch-control-6m forms=2217 missing=145 noDonor=88 touches=574 orders=542 busy=31 skips=0 entryFails=1 closeFails=0 retestExpired=0 quotes=50061330 volumeQuotes=0 tradeFlags=0
### XAU / retest / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 198, "margin_call": 0}`
- LC_SUMMARY tag=XAU-retest-1y forms=3175 missing=200 noDonor=0 touches=1041 orders=373 busy=23 skips=0 entryFails=1 closeFails=48 retestExpired=1165 quotes=151108684 volumeQuotes=0 tradeFlags=0
### XAU / retest / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 198, "margin_call": 0}`
- LC_SUMMARY tag=XAU-retest-3y forms=6670 missing=408 noDonor=0 touches=3199 orders=1169 busy=73 skips=0 entryFails=1 closeFails=48 retestExpired=2530 quotes=215981136 volumeQuotes=0 tradeFlags=0
### XAU / retest / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 276, "margin_call": 0}`
- LC_SUMMARY tag=XAU-retest-5y forms=10169 missing=616 noDonor=0 touches=5445 orders=1987 busy=127 skips=0 entryFails=2 closeFails=66 retestExpired=3896 quotes=266777420 volumeQuotes=0 tradeFlags=0
### XAU / retest / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=XAU-retest-6m forms=2311 missing=145 noDonor=0 touches=516 orders=183 busy=9 skips=0 entryFails=0 closeFails=0 retestExpired=850 quotes=119292144 volumeQuotes=0 tradeFlags=0
### XAU / retest-control / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 178, "margin_call": 0}`
- LC_SUMMARY tag=XAU-retest-control-1y forms=3075 missing=200 noDonor=100 touches=1023 orders=366 busy=14 skips=0 entryFails=1 closeFails=43 retestExpired=1149 quotes=151108682 volumeQuotes=0 tradeFlags=0
### XAU / retest-control / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 310, "margin_call": 0}`
- LC_SUMMARY tag=XAU-retest-control-3y forms=6529 missing=408 noDonor=141 touches=3213 orders=1160 busy=73 skips=0 entryFails=1 closeFails=76 retestExpired=2501 quotes=215981153 volumeQuotes=0 tradeFlags=0
### XAU / retest-control / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 542, "margin_call": 0}`
- LC_SUMMARY tag=XAU-retest-control-5y forms=9979 missing=616 noDonor=190 touches=5462 orders=1999 busy=119 skips=2 entryFails=1 closeFails=134 retestExpired=3861 quotes=266777435 volumeQuotes=0 tradeFlags=0
### XAU / retest-control / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=XAU-retest-control-6m forms=2223 missing=145 noDonor=88 touches=519 orders=177 busy=6 skips=0 entryFails=0 closeFails=0 retestExpired=823 quotes=119292104 volumeQuotes=0 tradeFlags=0
### XAU / touch / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 6, "invalid_volume": 0, "market_closed": 24, "margin_call": 0}`
- LC_SUMMARY tag=XAU-touch-1y forms=3175 missing=200 noDonor=0 touches=1041 orders=979 busy=57 skips=0 entryFails=5 closeFails=0 retestExpired=0 quotes=151103043 volumeQuotes=0 tradeFlags=0
### XAU / touch / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 6, "invalid_volume": 0, "market_closed": 24, "margin_call": 0}`
- LC_SUMMARY tag=XAU-touch-3y forms=6670 missing=408 noDonor=0 touches=3199 orders=3013 busy=181 skips=0 entryFails=5 closeFails=0 retestExpired=0 quotes=215975098 volumeQuotes=0 tradeFlags=0
### XAU / touch / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 6, "invalid_volume": 0, "market_closed": 178, "margin_call": 0}`
- LC_SUMMARY tag=XAU-touch-5y forms=10169 missing=616 noDonor=0 touches=5445 orders=5108 busy=330 skips=1 entryFails=6 closeFails=37 retestExpired=0 quotes=266771133 volumeQuotes=0 tradeFlags=0
### XAU / touch / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=XAU-touch-6m forms=2311 missing=145 noDonor=0 touches=516 orders=491 busy=25 skips=0 entryFails=0 closeFails=0 retestExpired=0 quotes=119288694 volumeQuotes=0 tradeFlags=0
### XAU / touch-control / 1y

- Native quality (including warmup): 40% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 6, "invalid_volume": 0, "market_closed": 20, "margin_call": 0}`
- LC_SUMMARY tag=XAU-touch-control-1y forms=3075 missing=200 noDonor=100 touches=1023 orders=975 busy=47 skips=0 entryFails=1 closeFails=5 retestExpired=0 quotes=151105346 volumeQuotes=0 tradeFlags=0
### XAU / touch-control / 3y

- Native quality (including warmup): 19% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 6, "invalid_volume": 0, "market_closed": 26, "margin_call": 0}`
- LC_SUMMARY tag=XAU-touch-control-3y forms=6529 missing=408 noDonor=141 touches=3213 orders=3050 busy=161 skips=0 entryFails=2 closeFails=5 retestExpired=0 quotes=215977406 volumeQuotes=0 tradeFlags=0
### XAU / touch-control / 5y

- Native quality (including warmup): 12% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 12, "margin_call": 0}`
- LC_SUMMARY tag=XAU-touch-control-5y forms=9979 missing=616 noDonor=190 touches=5462 orders=3447 busy=192 skips=1821 entryFails=2 closeFails=0 retestExpired=0 quotes=266778088 volumeQuotes=0 tradeFlags=0
### XAU / touch-control / 6m

- Native quality (including warmup): 55% real ticks
- Flags: `{"init_failed": 0, "critical": 0, "invalid_stops": 6, "invalid_volume": 0, "market_closed": 0, "margin_call": 0}`
- LC_SUMMARY tag=XAU-touch-control-6m forms=2223 missing=145 noDonor=88 touches=519 orders=497 busy=21 skips=0 entryFails=1 closeFails=0 retestExpired=0 quotes=119290201 volumeQuotes=0 tradeFlags=0

## Verification

Helper tests: 13, failures: 0. Retained native cases checked: 84 (including smoke tests); reconciled orders/deals: 106,972. Full case-by-case evidence: `VERIFICATION.json`.

Independent native M5/D1 bar rebuild: **0 discrepancies** across 80 retained cases. Full counts and any examples: `BAR_VERIFICATION.json`.

## Evidence

BUILD.json freezes source, binary, config and rules hashes. native/<case>/ stores inputs, native report (gzip), deals, journal (gzip), order audit and run metadata. RESULTS.json additionally holds per-level-family and monthly breakdowns. No installer, active terminal, website, or FTMO package changed.

No forward return, pass rate or payout probability follows from these raw results.
