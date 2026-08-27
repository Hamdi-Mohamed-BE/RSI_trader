# Active BAT session and weekday filter research

Research date: 2026-08-25

Decision: **keep every active EA's existing schedule. Do not add a portfolio-wide or per-EA session/day filter from this test.**

## Method

- Parsed the native MT5 deal history of all 15 EAs currently represented in the installer research set.
- Reconstructed closed trades with commissions, swaps and realized profit included.
- Sessions tested in UTC: Asia 00-08, London 07-16, New York 13-21, London+NY 07-21, London/NY overlap 13-16 and off-hours 21-07.
- Tested every non-empty Monday-Friday combination.
- Selected candidates only on 2025-08-11 through 2026-04-10.
- Held 2026-04-11 through 2026-08-10 locked as an unseen check.
- This is a historical cash-trade overlay. It does not rerun an EA after removing trades and does not recalculate later position sizes, shared margin or floating-equity interaction.

## Combined portfolio

These figures are an arithmetic cash overlay starting from USD 10,000; they are not a simultaneous native multi-EA MT5 simulation.

| Test | Return | PF | Max realized DD | Trades |
|---|---:|---:|---:|---:|
| Baseline, full year | +304.75% | 1.30 | 7.91% | 1,854 |
| One global training-selected filter, full year | +304.75% | 1.30 | 7.91% | 1,854 |
| Per-EA training-selected filters, full year | +298.42% | 1.62 | 4.83% | 911 |
| Baseline, locked check | **+112.89%** | **1.28** | **10.09%** | 649 |
| One global filter, locked check | **+112.89%** | **1.28** | **10.09%** | 649 |
| Per-EA filters, locked check | +52.65% | 1.26 | 12.55% | 306 |

The best global choice is **all hours and all weekdays**, which means no filter. The attractive full-year PF/DD from individual filters does not hold up: locked return falls by more than half and locked drawdown becomes worse.

## One-by-one locked check

The filter column shows what the first eight months selected. “Base” and “Filtered” are returns during the untouched final four months.

| EA | Training-selected filter | Locked base | Locked filtered | Filtered PF | Filtered DD | Filtered trades | Result |
|---|---|---:|---:|---:|---:|---:|---|
| LTA Volume Profile | All hours; Mon/Tue/Thu/Fri | +45.98% | +46.93% | 1.64 | 6.81% | 69 | Small pass, but not enough independent evidence to deploy |
| ORB Volume Profile | All hours; Tue/Fri | +12.57% | +1.28% | 1.68 | 1.03% | 8 | Reject: return destroyed |
| ATR Candle Breakout | Asia; Mon/Tue/Fri | +1.58% | -2.57% | 0.00 | 2.57% | 3 | Reject |
| Asia Breakout | New York; Mon/Fri | -8.34% | -10.67% | 0.37 | 11.15% | 19 | Reject |
| DmC | Asia; Mon/Wed/Fri | +12.58% | -3.00% | 0.87 | 11.50% | 32 | Reject |
| Go Long | All hours; Mon/Tue/Wed | +14.84% | +8.29% | 1.62 | 3.16% | 51 | Reject: weaker than baseline |
| EMA3 | All hours; Wed/Fri | +2.09% | -2.04% | 0.17 | 2.46% | 4 | Reject |
| XAU Weakness | All hours; Mon/Fri | -9.64% | -4.06% | 0.84 | 8.52% | 35 | Reject: still losing |
| Nasdaq Overnight | All hours; Fri | +3.77% | +2.75% | no losses | 0.00% | 5 | Too few trades; weaker than baseline |
| Turnaround Tuesday | Asia; all days | +1.77% | +1.77% | 1.35 | 1.99% | 7 | No meaningful change |
| US100 Weakness | All hours; Wed/Thu/Fri | -3.20% | -0.78% | 0.87 | 3.30% | 17 | Reject: still losing |
| News Pulse | All hours; Thu/Fri | +42.78% | +19.54% | no losses | 0.00% | 2 | Too few trades; weaker than baseline |
| US100 ORB 0.5R | Existing schedule | +1.00% | +1.00% | no losses | 0.00% | 2 | No filter tested credibly |
| US100 ORB 2R | Existing schedule | +1.98% | +1.98% | no losses | 0.00% | 1 | No filter tested credibly |
| Nasdaq 5M Open EMA ATR | All hours; Wed/Thu/Fri | -6.86% | -7.77% | 0.77 | 15.16% | 51 | Reject |

Only LTA improved in the locked segment, and only slightly. Because it was selected from many alternatives and has only one locked segment, this is a hypothesis for a future walk-forward test—not a safe production change.

## Files

- `session-day-filter-results.json`: full statistics and balance series.
- `per-ea-filter-results.csv`: compact per-EA table.
- `analyze_session_day_filters.py`: reproducible analysis.

The active EA sources, SET files and `INSTALL AND RUN ON ACTIVE MT5.bat` were not changed.
