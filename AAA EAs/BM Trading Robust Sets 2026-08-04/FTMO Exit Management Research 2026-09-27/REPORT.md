# FTMO exit-management comparison — 27 September 2026

Research only. No production EA, launcher, website, or live account settings changed. All six research EAs refuse to run outside the strategy tester.

## Main findings

- Current exits retained the strongest six-month modeled payout frequency under stress: 82.7%, versus 0.7% with all 0.75R and 0.0% with all 0.50R.
- Non-news M15 ATR improved the four-month payout frequency from 41.3% to 46.3%, but reduced six-month frequency to 80.2%, reduced win rate and increased modeled drawdown. This is a speed-versus-stability trade-off, not a clear overall upgrade.
- Target-proximity risk halving slowed completion in this test: current + protection reached 75.4% paid by six months versus 82.7% without it. The study does not establish that protection never helps in other conditions.
- Two isolated candidates merit fresh validation: EMA3 at 0.75R and ORB at 0.50R. They have not been combined into a post-hoc optimized portfolio in this report.
- Do not change raw Gold or news exits solely to chase win rate. The raw Gold target is often already below 0.75R, so this change can move its target farther away. News gains depend heavily on a few large winners.
- All modeled breach counts were zero under the admission gates and stop-reserve approximation. This is not a real-world zero-risk finding. All percentages are fitted-history scenario results, not independently validated FTMO forecasts.

## Scope and what was actually tested

Basket: raw Gold Overnight Value Area, News Pulse XAU, News Pulse XAG, Nasdaq Overnight, EMA3 Full Safe, and the saved ORB Volume Profile 0.75R configuration. Nasdaq 5M DI and RSI/VWAP are **not** in this six-EA test.

24 new native MT5 runs: 2 March through 30 August 2026 (end-exclusive 31 August), real ticks, $10,000 initial native balance, 150 ms fixed execution delay. Native quotes are from the isolated Exness research terminal, **not FTMO ticks**. Native leverage is 1:2000 only for generating individual strategy ledgers. Their original sizing is retained; the separate shared-account model imposes FTMO-like leverage and strict dollar risk.

Then 16,000 paired simulations: eight portfolios × reference/stressed costs × 1,000 paths. All alternatives use the same 26 sampled joint weeks and random seed. The chronological shared-account comparison covers 4 March–30 August (180 days).

This is exploratory re-use of previously examined history, including fitted news parameters. The simulated percentages are conditional scenario frequencies, **not independently validated real-world success probabilities**.

| Exit version | Frozen rule |
|---|---|
| Current | Original targets and management, freshly rerun at the same execution delay |
| Fixed 0.75R / 0.50R | Initial TP at requested entry ± stated multiple of original stop distance; original trailing disabled; original time exits retained |
| M15 ATR | No TP; activate after a completed M15 close reaches +1R; trail best completed close by 2×ATR(14), never widen |
| Profile | No TP; activate after +0.5R; trail behind crossed previous completed UTC-session low/VAL/POC/VAH/high, with 0.2 ATR buffer; completed M15 confirmation |

The profile uses 64 price bins, M1 typical-price tick-volume, 70% value area and at least 300 bars in the prior eligible UTC day, searching back up to seven days. This is a broker tick-volume proxy, not centralized exchange volume. No forming-bar or future-day levels are used. Neither ATR nor profile parameters were optimized in this batch. Partial profit-taking was not tested.

Stops are not widened. Both pending sides remain enabled for news. A smaller/farther TP can change holding time, future entry availability and order acceptance, so trade counts need not be identical. Slippage makes achieved R differ from the requested target R.

## Portfolio definitions

| ID | Exit assignments |
|---|---|
| A | Current exits on all six |
| B | Fixed 0.75R on all six |
| C | Fixed 0.50R on all six |
| D | 0.75R on the four non-news EAs; news unchanged |
| E | Gold/ORB profile trailing; Overnight/EMA M15 ATR; news unchanged |
| F | E plus target-proximity risk reduction |
| G | M15 ATR on all four non-news EAs; news unchanged |
| H | A plus target-proximity risk reduction |

Target protection halves the next ordinary entry budget only when the phase balance is within two base-risk units ($142.86) of its profit target. It does not close a floating basket early, alter news risk, or change funded-stage risk. E is a preselected strategy-specific hypothesis, not a retrospectively optimized winner.

## Native per-EA results

These are independent MT5 runs at each saved source sizing, not additive shared-account dollar returns. Equity DD below is the native **maximum relative equity drawdown**, rather than the percentage attached to maximum cash drawdown. Frequency uses the 26-week source window.

| EA | Exit | Trades | /week | Net USD | Return | Win rate | PF | Equity DD | Max W/L streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Gold Overnight Value Area (raw) | Current/native | 100 | 3.8 | +$1,393.72 | 13.94% | 75.00% | 1.86 | 3.81% | 11/3 |
| Gold Overnight Value Area (raw) | Fixed 0.75R | 101 | 3.9 | +$1,008.17 | 10.08% | 50.50% | 1.33 | 6.53% | 4/7 |
| Gold Overnight Value Area (raw) | Fixed 0.50R | 101 | 3.9 | +$905.46 | 9.05% | 60.40% | 1.35 | 4.22% | 6/4 |
| Gold Overnight Value Area (raw) | M15 ATR trailing | 101 | 3.9 | +$1,164.16 | 11.64% | 46.53% | 1.36 | 8.87% | 4/7 |
| Gold Overnight Value Area (raw) | Previous-session profile trailing | 101 | 3.9 | +$908.91 | 9.09% | 47.52% | 1.29 | 7.10% | 4/7 |
| Nasdaq Overnight | Current/native | 57 | 2.2 | +$562.85 | 5.63% | 63.16% | 1.55 | 2.54% | 10/3 |
| Nasdaq Overnight | Fixed 0.75R | 57 | 2.2 | +$516.11 | 5.16% | 63.16% | 1.50 | 2.29% | 10/3 |
| Nasdaq Overnight | Fixed 0.50R | 57 | 2.2 | +$325.02 | 3.25% | 63.16% | 1.32 | 2.49% | 10/3 |
| Nasdaq Overnight | M15 ATR trailing | 57 | 2.2 | +$513.13 | 5.13% | 63.16% | 1.50 | 2.52% | 10/3 |
| EMA3 Full Safe | Current/native | 19 | 0.7 | −$128.04 | -1.28% | 47.37% | 0.92 | 7.40% | 2/3 |
| EMA3 Full Safe | Fixed 0.75R | 26 | 1.0 | +$243.22 | 2.43% | 76.92% | 1.20 | 6.13% | 10/2 |
| EMA3 Full Safe | Fixed 0.50R | 36 | 1.4 | −$157.52 | -1.58% | 75.00% | 0.91 | 6.63% | 7/2 |
| EMA3 Full Safe | M15 ATR trailing | 25 | 1.0 | −$472.94 | -4.73% | 56.00% | 0.76 | 10.27% | 3/4 |
| ORB Volume Profile (saved 0.75R) | Current/native | 36 | 1.4 | +$353.50 | 3.54% | 63.89% | 1.30 | 4.84% | 6/3 |
| ORB Volume Profile (saved 0.75R) | Fixed 0.75R | 36 | 1.4 | +$353.50 | 3.54% | 63.89% | 1.30 | 4.84% | 6/3 |
| ORB Volume Profile (saved 0.75R) | Fixed 0.50R | 36 | 1.4 | +$380.02 | 3.80% | 72.22% | 1.41 | 3.08% | 9/2 |
| ORB Volume Profile (saved 0.75R) | M15 ATR trailing | 36 | 1.4 | +$1,025.28 | 10.25% | 52.78% | 1.67 | 6.58% | 6/3 |
| ORB Volume Profile (saved 0.75R) | Previous-session profile trailing | 36 | 1.4 | +$1,088.40 | 10.88% | 52.78% | 1.71 | 6.79% | 6/3 |
| News Pulse XAU | Current/native | 20 | 0.8 | +$12,043.09 | 120.43% | 60.00% | 12.81 | 6.65% | 8/4 |
| News Pulse XAU | Fixed 0.75R | 20 | 0.8 | +$611.08 | 6.11% | 80.00% | 2.72 | 1.14% | 9/1 |
| News Pulse XAU | Fixed 0.50R | 20 | 0.8 | +$463.28 | 4.63% | 80.00% | 2.69 | 1.00% | 9/1 |
| News Pulse XAG | Current/native | 16 | 0.6 | +$25,731.05 | 257.31% | 43.75% | 7.66 | 8.29% | 2/4 |
| News Pulse XAG | Fixed 0.75R | 16 | 0.6 | +$151.55 | 1.52% | 68.75% | 1.11 | 4.21% | 3/3 |
| News Pulse XAG | Fixed 0.50R | 16 | 0.6 | −$140.90 | -1.41% | 62.50% | 0.90 | 5.45% | 2/3 |

## Shared $10K account — chronological 180-day replay

All EAs share the same balance, margin and admission limits. This continuous P&L is **not payout income**: it has no evaluation resets or withdrawals. The DD column is a modeled stop-reserve estimate, **not reconstructed native portfolio tick-equity DD**. Actual native equity DD is reported above per EA.

### Reference costs

| Portfolio | Trades | /week | Net USD | Return | Win rate | PF | Closed DD | Stop-reserve DD | Worst modeled day | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A Current exits | 208 | 8.1 | +$4,673.65 | 46.74% | 70.67% | 3.31 | 1.77% | 2.26% | $209.64 | 9/3 |
| B All 0.75R | 211 | 8.2 | +$1,565.43 | 15.65% | 61.14% | 1.63 | 2.62% | 3.73% | $209.64 | 9/4 |
| C All 0.50R | 210 | 8.2 | +$1,209.03 | 12.09% | 65.24% | 1.54 | 2.00% | 2.82% | $207.26 | 9/3 |
| D Non-news 0.75R | 211 | 8.2 | +$4,558.81 | 45.59% | 60.66% | 2.74 | 1.96% | 2.88% | $209.64 | 9/4 |
| E Strategy-specific | 212 | 8.2 | +$4,828.42 | 48.28% | 56.60% | 2.63 | 2.28% | 3.76% | $230.95 | 8/5 |
| F Strategy-specific + target protection | 212 | 8.2 | +$4,828.42 | 48.28% | 56.60% | 2.63 | 2.28% | 3.76% | $230.95 | 8/5 |
| G Non-news M15 ATR | 212 | 8.2 | +$4,879.27 | 48.79% | 56.13% | 2.58 | 2.35% | 3.76% | $230.95 | 9/5 |
| H Current + target protection | 208 | 8.1 | +$4,673.65 | 46.74% | 70.67% | 3.31 | 1.77% | 2.26% | $209.64 | 9/3 |
### Stressed costs

| Portfolio | Trades | /week | Net USD | Return | Win rate | PF | Closed DD | Stop-reserve DD | Worst modeled day | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A Current exits | 207 | 8.0 | +$3,229.57 | 32.30% | 69.57% | 2.32 | 2.32% | 2.98% | $261.60 | 9/3 |
| B All 0.75R | 209 | 8.1 | +$379.34 | 3.79% | 57.89% | 1.13 | 6.20% | 7.01% | $251.92 | 9/4 |
| C All 0.50R | 208 | 8.1 | +$144.84 | 1.45% | 62.02% | 1.05 | 4.89% | 5.74% | $239.66 | 9/4 |
| D Non-news 0.75R | 210 | 8.2 | +$3,011.80 | 30.12% | 60.00% | 1.97 | 2.65% | 3.92% | $251.92 | 9/4 |
| E Strategy-specific | 210 | 8.2 | +$3,250.54 | 32.51% | 56.19% | 1.94 | 2.82% | 4.81% | $295.94 | 6/5 |
| F Strategy-specific + target protection | 210 | 8.2 | +$3,250.54 | 32.51% | 56.19% | 1.94 | 2.82% | 4.81% | $295.94 | 6/5 |
| G Non-news M15 ATR | 210 | 8.2 | +$3,270.65 | 32.71% | 55.71% | 1.90 | 3.23% | 4.81% | $295.94 | 9/5 |
| H Current + target protection | 207 | 8.0 | +$3,229.57 | 32.30% | 69.57% | 2.32 | 2.32% | 2.98% | $261.60 | 9/3 |

## Conditional FTMO outcomes — 1,000 paths per row

Pass/funding/payment are distinct. Unfinished accounts are not counted as blown. Breaches refer only to the evaluation and funded stage up to the first reward request or day 180, not lifetime funded-account survival. Days are calendar days and conditional on completion within 180 days.

### Reference costs

| Portfolio | Funded 60d | Paid 60d | Funded 120d | Paid 120d | Funded 180d | Paid 180d | Breached by 180d | Median days to funded / paid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A Current exits | 27.5% | 6.8% | 87.9% | 71.0% | 98.8% | 98.2% | 0.0% | 79.8 / 100.6 |
| B All 0.75R | 0.0% | 0.0% | 7.6% | 1.2% | 50.0% | 30.3% | 0.0% | 150.5 / 156.7 |
| C All 0.50R | 0.0% | 0.0% | 0.4% | 0.0% | 17.6% | 9.2% | 0.0% | 157.6 / 168.4 |
| D Non-news 0.75R | 26.5% | 7.2% | 84.2% | 66.9% | 98.5% | 96.6% | 0.0% | 80.6 / 101.4 |
| E Strategy-specific | 35.4% | 10.3% | 87.5% | 71.7% | 98.1% | 96.1% | 0.0% | 73.6 / 95.6 |
| F Strategy-specific + target protection | 29.3% | 7.4% | 83.0% | 66.5% | 97.5% | 93.9% | 0.0% | 79.8 / 100.6 |
| G Non-news M15 ATR | 36.2% | 9.7% | 88.3% | 74.0% | 98.1% | 96.8% | 0.0% | 72.9 / 94.6 |
| H Current + target protection | 23.5% | 5.9% | 79.1% | 61.9% | 97.5% | 95.4% | 0.0% | 86.8 / 107.6 |
### Stressed costs

| Portfolio | Funded 60d | Paid 60d | Funded 120d | Paid 120d | Funded 180d | Paid 180d | Breached by 180d | Median days to funded / paid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A Current exits | 13.9% | 3.0% | 59.8% | 41.3% | 90.7% | 82.7% | 0.0% | 100.8 / 120.6 |
| B All 0.75R | 0.0% | 0.0% | 0.3% | 0.1% | 1.5% | 0.7% | 0.0% | 151.6 / 144.6 |
| C All 0.50R | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | — / — |
| D Non-news 0.75R | 12.9% | 2.5% | 53.7% | 35.8% | 86.2% | 76.0% | 0.0% | 101.6 / 121.7 |
| E Strategy-specific | 19.3% | 4.3% | 61.9% | 43.9% | 88.7% | 79.4% | 0.0% | 93.8 / 114.6 |
| F Strategy-specific + target protection | 16.4% | 3.1% | 57.2% | 38.4% | 86.0% | 74.5% | 0.0% | 99.6 / 115.6 |
| G Non-news M15 ATR | 20.2% | 4.5% | 63.0% | 46.3% | 88.9% | 80.2% | 0.0% | 92.6 / 112.9 |
| H Current + target protection | 11.1% | 2.3% | 52.7% | 34.1% | 86.2% | 75.4% | 0.0% | 107.8 / 122.8 |

## Phase timing and first-reward size — stressed cases

| Portfolio | Phase 1 median days | Phase 2 median days from availability | Median first reward if paid | First-payment change vs A (paired, percentage points) |
|---|---:|---:|---:|---|
| A Current exits | 57.6 | 30.2 | $144.19 | 0.0 pp (MC-only interval 0.0 to 0.0) |
| B All 0.75R | 136.6 | 33.5 | $97.72 | -82.0 pp (MC-only interval -84.4 to -79.6) |
| C All 0.50R | 162.3 | — | $— | -82.7 pp (MC-only interval -85.0 to -80.4) |
| D Non-news 0.75R | 59.6 | 30.0 | $159.34 | -6.7 pp (MC-only interval -8.6 to -4.8) |
| E Strategy-specific | 50.6 | 26.0 | $235.07 | -3.3 pp (MC-only interval -5.7 to -0.9) |
| F Strategy-specific + target protection | 52.6 | 28.0 | $221.84 | -8.2 pp (MC-only interval -10.7 to -5.7) |
| G Non-news M15 ATR | 50.9 | 24.2 | $231.39 | -2.5 pp (MC-only interval -5.1 to 0.1) |
| H Current + target protection | 59.6 | 33.2 | $146.98 | -7.3 pp (MC-only interval -9.0 to -5.6) |

## Historical monthly breakdown — stressed costs

Cash is grouped by close month. March and August are partial calendar months. All values are continuous-account trading P&L, not payouts.

| Portfolio | Month | Closed trades | Net USD |
|---|---|---:|---:|
| A Current exits | 2026-03 | 33 | +$150.41 |
| A Current exits | 2026-04 | 26 | +$203.90 |
| A Current exits | 2026-05 | 31 | +$344.59 |
| A Current exits | 2026-06 | 37 | +$728.30 |
| A Current exits | 2026-07 | 46 | +$1,545.01 |
| A Current exits | 2026-08 | 34 | +$257.37 |
| B All 0.75R | 2026-03 | 33 | +$148.89 |
| B All 0.75R | 2026-04 | 28 | +$118.43 |
| B All 0.75R | 2026-05 | 31 | +$414.70 |
| B All 0.75R | 2026-06 | 38 | +$253.71 |
| B All 0.75R | 2026-07 | 46 | −$318.76 |
| B All 0.75R | 2026-08 | 33 | −$237.64 |
| C All 0.50R | 2026-03 | 33 | +$113.88 |
| C All 0.50R | 2026-04 | 27 | +$42.36 |
| C All 0.50R | 2026-05 | 32 | +$270.33 |
| C All 0.50R | 2026-06 | 37 | +$82.43 |
| C All 0.50R | 2026-07 | 46 | −$231.63 |
| C All 0.50R | 2026-08 | 33 | −$132.53 |
| D Non-news 0.75R | 2026-03 | 33 | +$175.44 |
| D Non-news 0.75R | 2026-04 | 28 | +$143.76 |
| D Non-news 0.75R | 2026-05 | 31 | +$346.75 |
| D Non-news 0.75R | 2026-06 | 38 | +$781.71 |
| D Non-news 0.75R | 2026-07 | 46 | +$1,377.37 |
| D Non-news 0.75R | 2026-08 | 34 | +$186.76 |
| E Strategy-specific | 2026-03 | 33 | +$24.74 |
| E Strategy-specific | 2026-04 | 27 | +$40.61 |
| E Strategy-specific | 2026-05 | 32 | +$615.91 |
| E Strategy-specific | 2026-06 | 38 | +$1,053.89 |
| E Strategy-specific | 2026-07 | 46 | +$1,313.63 |
| E Strategy-specific | 2026-08 | 34 | +$201.78 |
| F Strategy-specific + target protection | 2026-03 | 33 | +$24.74 |
| F Strategy-specific + target protection | 2026-04 | 27 | +$40.61 |
| F Strategy-specific + target protection | 2026-05 | 32 | +$615.91 |
| F Strategy-specific + target protection | 2026-06 | 38 | +$1,053.89 |
| F Strategy-specific + target protection | 2026-07 | 46 | +$1,313.63 |
| F Strategy-specific + target protection | 2026-08 | 34 | +$201.78 |
| G Non-news M15 ATR | 2026-03 | 33 | −$31.97 |
| G Non-news M15 ATR | 2026-04 | 27 | +$16.85 |
| G Non-news M15 ATR | 2026-05 | 32 | +$695.95 |
| G Non-news M15 ATR | 2026-06 | 38 | +$1,049.85 |
| G Non-news M15 ATR | 2026-07 | 46 | +$1,207.17 |
| G Non-news M15 ATR | 2026-08 | 34 | +$332.80 |
| H Current + target protection | 2026-03 | 33 | +$150.41 |
| H Current + target protection | 2026-04 | 26 | +$203.90 |
| H Current + target protection | 2026-05 | 31 | +$344.59 |
| H Current + target protection | 2026-06 | 37 | +$728.30 |
| H Current + target protection | 2026-07 | 46 | +$1,545.01 |
| H Current + target protection | 2026-08 | 34 | +$257.37 |

## EA contributions — stressed costs

| Portfolio | EA | Trades | Win rate | PF | Net USD |
|---|---|---:|---:|---:|---:|
| A Current exits | Gold Overnight Value Area (raw) | 85 | 78.82% | 1.88 | +$541.01 |
| A Current exits | News Pulse XAG | 16 | 43.75% | 4.19 | +$1,444.89 |
| A Current exits | Nasdaq Overnight | 57 | 61.40% | 1.16 | +$116.68 |
| A Current exits | ORB Volume Profile (saved 0.75R) | 35 | 65.71% | 1.36 | +$203.74 |
| A Current exits | EMA3 Full Safe | 4 | 75.00% | 2.52 | +$72.95 |
| A Current exits | News Pulse XAU | 10 | 90.00% | 48.36 | +$850.29 |
| B All 0.75R | Gold Overnight Value Area (raw) | 86 | 54.65% | 1.26 | +$330.95 |
| B All 0.75R | News Pulse XAG | 16 | 25.00% | 0.06 | −$329.10 |
| B All 0.75R | Nasdaq Overnight | 57 | 61.40% | 1.12 | +$92.52 |
| B All 0.75R | ORB Volume Profile (saved 0.75R) | 34 | 64.71% | 1.35 | +$197.28 |
| B All 0.75R | EMA3 Full Safe | 6 | 83.33% | 2.87 | +$89.39 |
| B All 0.75R | News Pulse XAU | 10 | 80.00% | 0.91 | −$1.70 |
| C All 0.50R | Gold Overnight Value Area (raw) | 86 | 65.12% | 1.32 | +$338.93 |
| C All 0.50R | News Pulse XAG | 16 | 18.75% | 0.04 | −$364.46 |
| C All 0.50R | Nasdaq Overnight | 57 | 61.40% | 0.98 | −$16.32 |
| C All 0.50R | ORB Volume Profile (saved 0.75R) | 34 | 73.53% | 1.45 | +$194.37 |
| C All 0.50R | EMA3 Full Safe | 7 | 71.43% | 0.94 | −$6.84 |
| C All 0.50R | News Pulse XAU | 8 | 62.50% | 0.90 | −$0.84 |
| D Non-news 0.75R | Gold Overnight Value Area (raw) | 86 | 54.65% | 1.26 | +$330.95 |
| D Non-news 0.75R | News Pulse XAG | 16 | 43.75% | 4.19 | +$1,444.89 |
| D Non-news 0.75R | Nasdaq Overnight | 57 | 61.40% | 1.12 | +$92.52 |
| D Non-news 0.75R | ORB Volume Profile (saved 0.75R) | 35 | 65.71% | 1.36 | +$203.74 |
| D Non-news 0.75R | EMA3 Full Safe | 6 | 83.33% | 2.87 | +$89.39 |
| D Non-news 0.75R | News Pulse XAU | 10 | 90.00% | 48.36 | +$850.29 |
| E Strategy-specific | Gold Overnight Value Area (raw) | 86 | 51.16% | 1.20 | +$266.16 |
| E Strategy-specific | News Pulse XAG | 16 | 43.75% | 4.19 | +$1,444.89 |
| E Strategy-specific | Nasdaq Overnight | 57 | 61.40% | 1.12 | +$88.73 |
| E Strategy-specific | ORB Volume Profile (saved 0.75R) | 35 | 54.29% | 1.75 | +$594.14 |
| E Strategy-specific | EMA3 Full Safe | 8 | 62.50% | 0.97 | −$5.67 |
| E Strategy-specific | News Pulse XAU | 8 | 100.00% | — | +$862.28 |
| F Strategy-specific + target protection | Gold Overnight Value Area (raw) | 86 | 51.16% | 1.20 | +$266.16 |
| F Strategy-specific + target protection | News Pulse XAG | 16 | 43.75% | 4.19 | +$1,444.89 |
| F Strategy-specific + target protection | Nasdaq Overnight | 57 | 61.40% | 1.12 | +$88.73 |
| F Strategy-specific + target protection | ORB Volume Profile (saved 0.75R) | 35 | 54.29% | 1.75 | +$594.14 |
| F Strategy-specific + target protection | EMA3 Full Safe | 8 | 62.50% | 0.97 | −$5.67 |
| F Strategy-specific + target protection | News Pulse XAU | 8 | 100.00% | — | +$862.28 |
| G Non-news M15 ATR | Gold Overnight Value Area (raw) | 86 | 50.00% | 1.22 | +$311.96 |
| G Non-news M15 ATR | News Pulse XAG | 16 | 43.75% | 4.19 | +$1,444.89 |
| G Non-news M15 ATR | Nasdaq Overnight | 57 | 61.40% | 1.12 | +$88.73 |
| G Non-news M15 ATR | ORB Volume Profile (saved 0.75R) | 35 | 54.29% | 1.72 | +$568.45 |
| G Non-news M15 ATR | EMA3 Full Safe | 8 | 62.50% | 0.97 | −$5.67 |
| G Non-news M15 ATR | News Pulse XAU | 8 | 100.00% | — | +$862.28 |
| H Current + target protection | Gold Overnight Value Area (raw) | 85 | 78.82% | 1.88 | +$541.01 |
| H Current + target protection | News Pulse XAG | 16 | 43.75% | 4.19 | +$1,444.89 |
| H Current + target protection | Nasdaq Overnight | 57 | 61.40% | 1.16 | +$116.68 |
| H Current + target protection | ORB Volume Profile (saved 0.75R) | 35 | 65.71% | 1.36 | +$203.74 |
| H Current + target protection | EMA3 Full Safe | 4 | 75.00% | 2.52 | +$72.95 |
| H Current + target protection | News Pulse XAU | 10 | 90.00% | 48.36 | +$850.29 |

## Risk and execution assumptions

- $10,000 FTMO 2-Step Swing model: +$1,000 Phase 1, +$500 Phase 2, four entry days each phase, $500 daily limit, $1,000 static loss floor, Prague midnight reset; no Best Day Rule for 2-Step and no evaluation deadline.
- Ordinary entries: maximum $71.43 initial planned risk, round lots down to 0.01; skip if the minimum lot exceeds budget. News: $10 per pending side, reserve both sides.
- Internal admission: $300 daily loss budget, $225 aggregate planned risk, $150 correlated-metal/per-symbol risk, $9,200 projected equity buffer, max seven fills/day and no new ordinary entries after three closed losses.
- Margin model: 1:15 metals and Nasdaq, at most 80% of modeled available equity. Instrument specifications are modeled assumptions, not a fresh FTMO server verification.
- Reference uses native fills and commission floors ($7 gold, $47.50 silver, $0.70 Nasdaq per lot). Stress reduces positive gross returns by 10%, expands negative gross by 10%, adds adverse price cost (gold ordinary $0.20, gold news $1, silver $0.04, Nasdaq 2 points), doubles negative swaps and includes carry reserve.
- Stop-reserve equity uses ordinary initial risk 1R/1.25R and news 1.25R/2R (reference/stress). It does not track actual combined bid/ask floating equity, tighten this reserve as stops trail, or model unbounded gap losses. Zero modeled breaches does not establish zero actual risk.
- Assumed administration: two business days between phases, five until funded activation, first reward eligibility 14 calendar days after first funded trade while flat and positive by at least $25, four business days for receipt; 80% reward share. These waiting periods are assumptions, not service guarantees.
- Weekly joint resampling preserves within-week cross-EA clustering, but breaks multi-week dependence and has only 26 source weeks. Fitted news settings, parameter selection and broker transfer risk are not cured by more Monte Carlo draws.
- Independent native opportunity ledgers are resized and gated in the shared-account overlay. Skipping a trade can alter later native opportunities; this is not a fully integrated native FTMO portfolio backtest.
- Native baseline may differ from the previous report because it is a fresh six-month run at 150 ms, with current source snapshots and a different warm-up/initial-position context. Compare alternatives to fresh A, not to unrelated prior headline values.

## Eligibility caveat

FTMO Swing generally permits news trading, but its general forbidden-practices rules still apply. Pre-news two-sided stop/gap trading requires explicit clarification from FTMO before deployment. This study does not model rejection/disqualification risk or imply the news implementation is approved.

## Audit

All production source snapshot hashes remained unchanged. Native trade counts, initial stops, prices, costs, gross/net cash and portfolio ledgers were reconciled. Check details are saved in CHECKS.json. Native tester inputs, reports, journals, source snapshots and binary hashes are retained.

### Fresh baseline vs earlier cached ledgers

| EA | Earlier trades | Fresh trades | Matched entry times | Exact entry/exit price & close-time matches |
|---|---:|---:|---:|---:|
| Gold Overnight Value Area (raw) | 99 | 99 | 99 | 99 |
| Nasdaq Overnight | 56 | 57 | 56 | 0 |
| EMA3 Full Safe | 17 | 18 | 10 | 0 |
| ORB Volume Profile (saved 0.75R) | 37 | 36 | 36 | 0 |
| News Pulse XAU | 20 | 20 | 20 | 15 |
| News Pulse XAG | 17 | 16 | 16 | 10 |

### Native management diagnostics

| Case | Manager summary | Journal flags |
|---|---|---|
| gold-native | ["EM_SUMMARY|mode=0|mods=0|rejects=0", "EM_SUMMARY|mode=0|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 6, "invalid_volume": 0, "market_closed": 12236, "no_history": 0} |
| gold-rr075 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 13892, "no_history": 0} |
| gold-rr050 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| gold-atr | ["EM_SUMMARY|mode=2|mods=146|rejects=0", "EM_SUMMARY|mode=2|mods=146|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 38356, "no_history": 0} |
| gold-profile | ["EM_SUMMARY|mode=3|mods=90|rejects=4", "EM_SUMMARY|mode=3|mods=90|rejects=4"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 38372, "no_history": 0} |
| overnight-native | ["EM_SUMMARY|mode=0|mods=0|rejects=0", "EM_SUMMARY|mode=0|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 18, "no_history": 0} |
| overnight-rr075 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 18, "no_history": 0} |
| overnight-rr050 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 18, "no_history": 0} |
| overnight-atr | ["EM_SUMMARY|mode=2|mods=5|rejects=0", "EM_SUMMARY|mode=2|mods=5|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 18, "no_history": 0} |
| ema-native | ["EM_SUMMARY|mode=0|mods=0|rejects=0", "EM_SUMMARY|mode=0|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| ema-rr075 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| ema-rr050 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| ema-atr | ["EM_SUMMARY|mode=2|mods=78|rejects=0", "EM_SUMMARY|mode=2|mods=78|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| orb-native | ["EM_SUMMARY|mode=0|mods=0|rejects=0", "EM_SUMMARY|mode=0|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| orb-rr075 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| orb-rr050 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| orb-atr | ["EM_SUMMARY|mode=2|mods=95|rejects=0", "EM_SUMMARY|mode=2|mods=95|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| orb-profile | ["EM_SUMMARY|mode=3|mods=33|rejects=0", "EM_SUMMARY|mode=3|mods=33|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| xau-native | ["EM_SUMMARY|mode=0|mods=0|rejects=0", "EM_SUMMARY|mode=0|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| xau-rr075 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| xau-rr050 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| xag-native | ["EM_SUMMARY|mode=0|mods=0|rejects=0", "EM_SUMMARY|mode=0|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| xag-rr075 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |
| xag-rr050 | ["EM_SUMMARY|mode=1|mods=0|rejects=0", "EM_SUMMARY|mode=1|mods=0|rejects=0"] | {"init_failed": 0, "critical": 0, "invalid_stops": 0, "invalid_volume": 0, "market_closed": 0, "no_history": 0} |

### Evidence files

- RESULTS.json: full simulations, chronological ledgers, phase funnels and paired differences.
- FTMO Exit Comparison.xlsx: native, shared-account and funding comparison tables.
- NATIVE_AUDIT.json, BASELINE_PARITY.json, CHECKS.json: reconciliation and validation.
- run-config.json and PORTFOLIOS_FROZEN.json: frozen test rules.
- native/: compressed native reports/journals, closed trades and metadata for all 24 runs.

### Official rules checked

- [FTMO 1-Step / 2-Step comparison](https://ftmo.com/en/comparison-table/)
- [FTMO objectives](https://ftmo.com/en/trading-objectives/)
- [Swing account](https://ftmo.com/en/faq/ftmo-swing-account-type/)
- [Reward withdrawals](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/)
- [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/)

No deployment recommendation follows automatically from a highest in-sample return or win rate. Fresh holdout and broker-specific execution validation remain necessary.
