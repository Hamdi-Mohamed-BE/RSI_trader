# XAU London Opening Sweep + FVG — raw timeframe comparison

Native MT5 test of the frozen transcript interpretation in RAW RULES.md. The only compared strategy setting is M1, M5 or M15 FVG entry timeframe; stop is one tick beyond the FVG, and target is the opposite opening-range boundary.

USD 10,000 initial balance; Exness-MT5Trial16 XAUUSD CFD, tester leverage 1:2000; 1% requested equity risk, rounded up to broker volume step/minimum. Recorded commission, variable spread and swaps are included. The native journal confirms a FIXED 1 ms execution delay, not a random-delay stress test. Stop fills use simulated available quotes; this does not reproduce all live slippage, liquidity or market impact. Risk to the initial stop excludes additional transaction costs and gaps.

PF below is recomputed from net closed trades including fees. It can differ slightly from the rounded native headline PF. Drawdown is native relative EQUITY drawdown, including floating P/L.

| Period | Entry | Return | PF | Win rate | Max equity DD | Trades | Max W/L streak | Commission | Swap |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6m | M1 | -35.20% | 0.51 | 8.93% | 38.43% | 56 | 2/14 | $-975.84 | $0.00 |
| 6m | M5 | +11.61% | 1.48 | 19.05% | 13.11% | 21 | 2/11 | $-388.02 | $0.00 |
| 6m | M15 | -3.05% | 0.42 | 16.67% | 6.30% | 6 | 1/4 | $-16.18 | $0.00 |
| 1y | M1 | -47.25% | 0.60 | 9.01% | 58.54% | 111 | 2/24 | $-2,017.12 | $0.00 |
| 1y | M5 | -17.11% | 0.61 | 8.89% | 29.58% | 45 | 2/24 | $-643.24 | $0.00 |
| 1y | M15 | -8.78% | 0.37 | 16.67% | 12.77% | 12 | 1/6 | $-241.59 | $0.00 |
| 3y | M1 | -99.63% | 0.03 | 4.39% | 99.69% | 319 | 2/102 | $-2,592.55 | $0.00 |
| 3y | M5 | -75.20% | 0.24 | 6.80% | 77.94% | 147 | 2/40 | $-1,911.22 | $0.00 |
| 3y | M15 | -32.22% | 0.11 | 5.88% | 32.81% | 34 | 1/22 | $-627.34 | $0.00 |
| 5y | M1 | -99.99% | 0.04 | 0.79% | 99.99% | 254 | 1/115 | $-2,559.81 | $0.00 |
| 5y | M5 | -94.23% | 0.34 | 7.87% | 95.82% | 254 | 3/40 | $-3,315.15 | $0.00 |
| 5y | M15 | -50.34% | 0.16 | 7.69% | 51.19% | 65 | 1/25 | $-1,045.54 | $0.00 |

## Exact date ranges

- 6m: 2026-03-05 through 2026-09-05 (end exclusive).
- 1y: 2025-09-05 through 2026-09-05 (end exclusive).
- 3y: 2023-09-05 through 2026-09-05 (end exclusive).
- 5y: 2021-09-05 through 2026-09-05 (end exclusive).

## Verification

All trade ledgers reconcile to native MT5 net P/L and trade counts. The audit independently checks Europe/London DST, completed H1 sweeps, at least three completed lower-timeframe candles after confirmation, correct stop/target direction, entry after FVG confirmation and no more than one fill per London date. No trades are removed from the results.

| Period | Entry | MT5 history quality | EA placement/close errors | Margin rejections at activation | Overnight trades |
|---|---|---|---:|---:|---:|
| 6m | M1 | 100% real ticks | 0 | 2 | 0 |
| 6m | M5 | 100% real ticks | 0 | 0 | 0 |
| 6m | M15 | 100% real ticks | 0 | 0 | 0 |
| 1y | M1 | 67% real ticks | 0 | 3 | 0 |
| 1y | M5 | 67% real ticks | 0 | 0 | 0 |
| 1y | M15 | 67% real ticks | 0 | 0 | 0 |
| 3y | M1 | 22% real ticks | 0 | 13 | 0 |
| 3y | M5 | 22% real ticks | 0 | 5 | 0 |
| 3y | M15 | 22% real ticks | 0 | 0 | 0 |
| 5y | M1 | 13% real ticks | 0 | 283 | 0 |
| 5y | M5 | 13% real ticks | 0 | 9 | 0 |
| 5y | M15 | 13% real ticks | 0 | 0 | 0 |

An accepted pending order is not a guaranteed fill. The tester journal separately records margin failures when orders activate; these are included above and must not be confused with zero EA placement/close errors. M1 five-year balance falls to $1.02 and its last filled trade is 2024-03-22: later signals still occur but the account cannot finance the minimum lot. Consequently, five-year counts are not directly comparable with shorter runs restarted at $10,000.

Occasional gaps in older quotes delay observation of an already closed range or sweep. These are retained and recorded as late_range_observations / late_sweep_observations in VERIFIED RESULTS.json, rather than filled in using future data.

## Five-year detail

| Entry | Final balance | Wins / losses | Average win | Average loss | Expected net / trade | Long net | Short net | Median planned RR of fills |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 | $1.02 | 2 / 252 | $233.77 | $-41.53 | $-39.37 | $-4,732.22 | $-5,266.76 | 23.29R |
| M5 | $577.44 | 20 / 234 | $247.56 | $-61.43 | $-37.10 | $-2,565.82 | $-6,856.74 | 11.38R |
| M15 | $4,966.17 | 5 / 60 | $197.16 | $-100.33 | $-77.44 | $-2,795.82 | $-2,238.01 | 8.85R |

## Five-year calendar breakdown

| Entry | Calendar year | Trades | Net P/L |
|---|---|---:|---:|
| M1 | 2021 | 27 | $-5,729.47 |
| M1 | 2022 | 96 | $-3,697.89 |
| M1 | 2023 | 114 | $-565.41 |
| M1 | 2024 | 17 | $-6.21 |
| M5 | 2021 | 14 | $-1,047.22 |
| M5 | 2022 | 53 | $-5,025.62 |
| M5 | 2023 | 60 | $-2,047.13 |
| M5 | 2024 | 45 | $-812.64 |
| M5 | 2025 | 48 | $-455.32 |
| M5 | 2026 | 34 | $-34.63 |
| M15 | 2021 | 6 | $-189.89 |
| M15 | 2022 | 9 | $-1,043.98 |
| M15 | 2023 | 24 | $-2,263.11 |
| M15 | 2024 | 5 | $-416.80 |
| M15 | 2025 | 14 | $-917.74 |
| M15 | 2026 | 7 | $-202.31 |

Calendar amounts come from the continuously compounded five-year run; 2021 and 2026 are partial years. They are not independent annual restarts.

The actual real-tick percentage is reported above. Missing broker tick history can be replaced with generated ticks by MT5 even when Model=4 is requested; see https://www.metatrader5.com/en/terminal/help/algotrading/testing_features .

Native HTML reports and plots are in Backtest Reports. Audit contains every signal event, each native tester journal and the complete closed trade JSON ledgers. This is research only; no website, installer or live EA was updated.

## Conclusion and review decision

No timeframe is a robust winner under this raw interpretation. M5 is the only positive six-month candidate (+11.61%, 21 trades, 19.05% wins), but loses over one, three and five years. M15 has smaller losses and far fewer trades; that is not evidence of a profitable edge. Do not deploy or call this a high-win-rate strategy.

The one-tick-beyond-FVG stop can be much narrower than spread. Example: M1 on 2026-03-09 had a planned $0.030 stop distance and 32.98 lots; the actual trade lost $1,830.39 including $181.39 commission. A nominal 1% risk calculation does not cap realized loss.

Recommendation: do not run broad parameter optimization yet. If the user approves a further experiment, first test practical spread-aware minimum FVG width, cost/margin-aware sizing, and clarify whether the intended FVG may form during the H1 sweep rather than only after its close. These change the present raw rules and have NOT been applied or tested here.
