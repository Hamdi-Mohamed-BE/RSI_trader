# US100 M15 close-confirmed ORB — raw six-month test

27 September 2026. Research only: no production EA, BAT, website, live terminal or account changes.

## Rules frozen before testing

- US100 via the isolated Exness tester's USTEC symbol. New York time with US DST, broker history clock UTC.
- Opening range is the high/low of 09:30–09:45. Wait for the first LATER completed M15 close strictly above/below it. Earliest signal confirmation is 10:00 NY, not 09:45.
- Market entry on the next available tick after confirmation. Long stop exactly at that breakout candle's low; short stop at its high. No additional buffer, EMA/DI/news filter, retest, trailing or breakeven.
- Two alternatives, separately tested: +0.50R profit target and +1/3R. These are small positive targets, not negative profits. Cost-free two-outcome breakeven win rates are 66.67% and 75.00%, respectively.
- Defaults supplied by us: one qualifying signal attempt / at most one filled trade per New York date; remaining positions close requested from 15:55 NY; no fresh entry at/after that time. Invalid stops/session unavailability are skipped, never widened. Exit attempts check session availability and are throttled to once per minute; unavailable markets can delay an exit.
- Native starting capital $10,000, risk target 1% of equity, existing upward broker-lot rounding convention (actual rounded risk may exceed 1%), real-tick Model 4, 150 ms delay, native spread/commission/swap. Isolated tester leverage is 1:2000; these native returns are not FTMO account tests.
- Two strategy configurations only; no parameter search. Smoke check plus two full windows per target. One initial smoke run required a report-parser datetime-format correction; EA logic was unchanged.

## Latest six calendar months — native MT5

**27 March–26 September 2026 inclusive** (end-exclusive 27 September). Native maximum relative equity drawdown below includes floating equity. PF is calculated from complete trade net P&L including commission/swap; the native report's deal-based PF is retained separately in RESULTS.json.

| Target | Trades | /30 days | /weekday | Net USD | Return | Win rate | Net PF | Max equity DD | Max win/loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50R | 129 | 21.03 | 0.98 | −$225.28 | -2.25% | 66.67% | 0.95 | 8.37% | 8/4 |
| 1/3R | 129 | 21.03 | 0.98 | −$244.82 | -2.45% | 74.42% | 0.93 | 9.19% | 21/4 |

### Latest-window monthly native results

| Month | 0.50R trades | 0.50R win rate | 0.50R net | 1/3R trades | 1/3R win rate | 1/3R net |
|---|---:|---:|---:|---:|---:|---:|
| 2026-03 | 3 | 33.33% | −$154.60 | 3 | 66.67% | −$35.02 |
| 2026-04 | 21 | 85.71% | +$569.62 | 21 | 100.00% | +$688.39 |
| 2026-05 | 21 | 57.14% | −$329.59 | 21 | 61.90% | −$402.85 |
| 2026-06 | 22 | 68.18% | +$20.40 | 22 | 68.18% | −$226.65 |
| 2026-07 | 23 | 65.22% | −$144.32 | 23 | 82.61% | +$194.29 |
| 2026-08 | 20 | 60.00% | −$218.58 | 20 | 60.00% | −$423.81 |
| 2026-09 | 19 | 68.42% | +$31.79 | 19 | 73.68% | −$39.17 |

March and September are partial months. Native profits compound at the stated sizing; monthly cash figures are not payout income.

Execution exception: the 0.50R version had one position carried across a market closure, opened 3 July at 14:15 UTC and stopped out on 5 July at 22:00:02 UTC for −$141.88. A requested 15:55 New York exit cannot execute while the market is unavailable. The 1/3R version had no overnight holds. The loss is included, not removed from these results.

### Latest-window cost sensitivity at portfolio sizing

Each ORB alone, fixed-dollar ceiling $71.43, strict lot rounding down and the existing internal admission guards. This is an offline ledger overlay, not a fresh native run. Stress assumptions are illustrative, not measured FTMO fill calibration.

| Target | Cost case | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Reserve DD proxy | Max win/loss |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| half | Reference | 128 | 20.87 | 0.98 | −$85.10 | -0.85% | 67.19% | 0.97 | 5.92% | 8/4 |
| half | Stress | 75 | 12.23 | 0.57 | −$730.58 | -7.31% | 65.33% | 0.66 | 8.57% | 7/3 |
| third | Reference | 128 | 20.87 | 0.98 | −$107.44 | -1.07% | 75.00% | 0.95 | 6.40% | 21/4 |
| third | Stress | 115 | 18.75 | 0.88 | −$748.08 | -7.48% | 74.78% | 0.68 | 10.73% | 21/4 |

## Effect on the current eight-EA setup

The control remains Gold Value Area raw, Nasdaq Overnight, EMA3 Safe, ORB Volume Profile 0.75R, News Pulse XAU/XAG, plus the separate EMA M15 ATR and ORB Volume Profile 0.50R copies. Nasdaq 5M DI remains excluded. O50/O33 add ONE new US100 ORB version each; neither replaces the existing gold ORBs, and the two US100 variants are not combined.

**Matched comparison window: 4 March–30 August 2026**, the prior portfolio study's 180 days / 128 weekdays. This differs from the latest six-month standalone window above. The new ORB has fresh aligned native runs from 2 March for the same 26-week Monte Carlo pool; no September-only ORB trades are added to an August-ending portfolio.

Same fixed-dollar ordinary risk ceiling $71.43, $10/news side, strict 0.01-lot rounding down, $300 daily admission budget, $225 open initial-risk cap, $150 correlated-metal/per-symbol cap, $9,200 projected buffer, maximum seven entries/day, three-loss admission stop and 80% margin ceiling. Both news sides remain possible with full risk/margin reservations. USTEC margin modeled 1:15; actual FTMO platform fills/margin are not verified here. Original strategies retain priority on simultaneous admissions.

### Stressed costs

| Portfolio | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD proxy | Max win/loss |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| J | 237 | 39.50 | 1.85 | +$3,411.28 | 34.11% | 70.04% | 2.17 | 3.11% | 4.51% | 12/3 |
| O50 | 358 | 59.67 | 2.80 | +$2,430.49 | 24.30% | 68.99% | 1.39 | 4.09% | 6.11% | 15/5 |
| O33 | 362 | 60.33 | 2.83 | +$2,786.24 | 27.86% | 72.38% | 1.52 | 4.19% | 5.94% | 16/5 |
### Reference costs

| Portfolio | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD proxy | Max win/loss |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| J | 239 | 39.83 | 1.87 | +$4,954.71 | 49.55% | 70.29% | 3.00 | 2.06% | 3.02% | 12/3 |
| O50 | 362 | 60.33 | 2.83 | +$4,604.29 | 46.04% | 68.51% | 1.83 | 2.89% | 4.27% | 16/4 |
| O33 | 363 | 60.50 | 2.84 | +$4,844.65 | 48.45% | 71.90% | 2.04 | 3.02% | 4.16% | 16/4 |

Portfolio DD is an initial-stop-reserve approximation, NOT actual combined tick equity. Native standalone equity DD and portfolio reserve DD are different measures.

## Modeled FTMO challenge outcomes — stressed costs

1,000 matched 180-day paths per portfolio/cost case; 6,000 total. Joint-week sampling with replacement, 26 source weeks, unchanged seed 20260926. Start-date timing and administration assumptions are the same as the previous study.

| Portfolio | Funded 30d | Paid 60d | Paid 120d | Funded 180d | Paid 180d | Breached before first reward | Median P1 days* | Median P2 days* | Median funded days* | Median paid days* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| J | 0.9% | 3.4% | 48.3% | 94.0% | 88.1% | 0.0% | 51.8 | 28.0 | 94.6 | 114.6 |
| O50 | 0.8% | 2.8% | 37.1% | 81.5% | 71.0% | 0.0% | 57.6 | 24.1 | 98.6 | 115.9 |
| O33 | 0.7% | 3.4% | 42.3% | 86.0% | 76.8% | 0.0% | 51.8 | 26.1 | 93.8 | 113.8 |

*Conditional on milestone completion within 180 days. Phase 2 starts at account availability; others from purchase. Zero observed breaches is not zero real risk. Unfinished or risk-blocked accounts are not counted as blown.

| Portfolio | Payout delta at 180d versus J | Matched MC-only 95% interval | Paths touching internal buffer | P95 reserve DD |
|---|---:|---:|---:|---:|
| J | 0.0 pp | 0.0 to 0.0 pp | 1/1000 | 6.39% |
| O50 | -17.1 pp | -19.6 to -14.6 pp | 119/1000 | 9.80% |
| O33 | -11.3 pp | -13.5 to -9.1 pp | 89/1000 | 9.57% |

## Marginal US100 trades in the combined account — stress

| Addition | Admitted trades | /30 days | /weekday | Net USD | Win rate | PF | Max win/loss |
|---|---:|---:|---:|---:|---:|---:|---:|
| O50 | 125 | 20.83 | 0.98 | −$921.58 | 67.20% | 0.73 | 8/3 |
| O33 | 126 | 21.00 | 0.98 | −$648.55 | 76.19% | 0.74 | 21/3 |

The total portfolio change can differ from the added ORB's own profit because it consumes shared risk/margin and can displace other trades. Full per-EA contributions and rejected-admission counts are in RESULTS.json.

## Important limits

- This is a two-preset raw test, not full optimization or pipeline validation. No out-of-sample claim and no production promotion.
- FTMO overlay retains 10%/5% targets, four entry days per phase, 5% daily and 10% static loss, Prague reset; two business days between phases, five to funded activation, reward at least 14 days after first funded entry when flat and $25 profitable, four business days to receipt, 80% share. Administrative timing is assumed.
- Reference retains native fills with commission floors. Stress reduces gross winners 10%, worsens gross losses 10%, adds two Nasdaq points / $0.20 ordinary gold / $1 gold news / $0.04 silver, doubles negative swaps and adds carry reserve. This is an unchanged hypothetical stress scenario, not measured FTMO slippage.
- Saved Exness native ledgers resized/gated together are not a native FTMO multi-EA test. Skipping an entry may change an EA's later state, which the overlay does not re-simulate.
- The existing news presets were fitted to this history; 26 weekly blocks are a small selected sample. Monte Carlo repetitions are not independent new market evidence, and do not preserve the actual future macro release calendar.
- Outcomes stop at first reward request or day 180, not lifetime funded-account survival. Reserve DD is not observed floating-equity DD, and gaps can exceed planned stop risk.
- News straddle eligibility still needs FTMO clarification under forbidden gap-trading practices. No regulatory/contract disqualification probability is modeled.

## Evidence

run-config.json freezes rules; BUILD.json captures the compiled source/binary hashes. native/* retains compressed reports/journals, native trades, exported M15 bars and independent AUDIT.json files. Every entry is checked against an independent Python reconstruction of the first completed M15 breakout, opening range, stop, target, New York DST and one-trade-per-day rule. PORTFOLIO_FROZEN.json records comparison evidence, RESULTS.json stores all compact paths and detailed historical ledgers; CHECKS.json records exact eight-EA baseline parity and validation.

- [FTMO objectives and account comparison](https://ftmo.com/en/comparison-table/)
- [FTMO prohibited practices](https://ftmo.com/en/forbidden-trading-practices/)
