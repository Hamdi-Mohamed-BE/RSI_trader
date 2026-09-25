# US100 H1 ORB 13UTC — ADX/DMI filters and 5/15/30-minute 1:1 ranges (last year)

Date: 2026-09-23. Research only. No production EA, SET, BAT, website cache or live MT5 chart was changed.

## Evidence type — read first

- **Native MT5 Strategy Tester**, not a replay or simulation. Isolated portable terminal
  `_Backtests/MT5-DMC-20260811`, profile "Calyx Research Empty", `[Experts] Enabled=0`, AllowLiveTrading=0.
- Exness-MT5Trial16 (demo), USTEC, $10,000, 1:2000, 1% risk, adaptive controls off, tester server offset 0.
- Model=4 (every tick based on real ticks), ExecutionMode=150 ms, Optimization=0.
- Period 2025-09-23 → 2026-09-23. Report history quality: **72% real ticks**
  (real USTEC ticks only from 2026-01-01; Sep–Dec 2025 uses ticks generated from bars).
- Runner `run_native.py`, settings `run-config.json`, parser `parse_native.py`. 26 runs, all exit 0 with a fresh
  report matching EA, symbol, dates, range minutes, reward/risk and ADX mode; no init, history, rejected-order or
  critical lines in any journal. Full metrics: `NATIVE_RESULTS.json`; ledgers `native/trades.json`;
  subset/random-removal checks `FILTER_CHECKS.json`.
- Research EA `EA/ORB ADX Research EA.mq5` = production `ORB Volume Data EA.mq5` v1.20 plus an ADX/DMI filter
  input (default off). MetaEditor64: 0 errors, 0 warnings, EX5 SHA-256 cc9657d4b6e7…
- **Parity:** production EX5 and research EX5 with the filter off produced the identical 72 trades
  (same entry, exit and net P/L).

## What was tested

Base = installed SET `ORB H1 Range Research 2026-09-05/Sets/USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set`:
13:00 UTC range start, direct breakout on a closed candle, stop beyond the opposite side of the range,
range 0.35–4.0 ATR, max stop 3 ATR, 60-minute trade window after the range, flat 20:00 UTC.

| Variant | Range | Signal candles / range ATR | Target |
|---|---|---|---|
| H1-RR6 (current) | 60 min | M15 / H1 | 6R |
| H1-RR1 (reference) | 60 min | M15 / H1 | 1R |
| OR5-RR1 | 5 min | M5 / M5 | 1R |
| OR15-RR1 | 15 min | M15 / M15 | 1R |
| OR30-RR1 | 30 min | M30 / M30 | 1R |

Filters, read on the just-closed breakout candle: none; ADX(14) ≥ 20; ADX ≥ 25; +DI/−DI agrees with the trade;
DI agrees and ADX ≥ 20. 5 variants × 5 filters = 25 configurations on the same year.

## Results (1% risk, $10,000)

| Config | Trades | Win % | PF | Return | Equity DD | Balance DD | Loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| **H1-RR6 current** | 72 | 51.4 | 1.67 | +23.0% | 6.84% | 5.40% | 4 |
| H1-RR6 + ADX≥20 | 57 | 54.4 | 2.01 | +26.5% | 4.22% | 3.91% | 3 |
| H1-RR6 + ADX≥25 | 48 | 56.3 | 1.82 | +16.7% | 4.23% | 2.71% | 3 |
| H1-RR6 + DI | 61 | 49.2 | 1.65 | +18.8% | 7.63% | 6.19% | 5 |
| H1-RR6 + DI & ADX≥20 | 46 | 52.2 | 2.05 | +22.2% | 5.03% | 3.52% | 4 |
| H1-RR1 | 72 | 63.9 | 1.66 | +16.5% | 3.99% | 3.01% | 3 |
| H1-RR1 + ADX≥20 | 57 | 68.4 | 2.03 | +17.9% | 3.46% | 2.33% | 3 |
| H1-RR1 + ADX≥25 | 48 | 68.8 | 2.03 | +14.7% | 3.46% | 2.32% | 3 |
| H1-RR1 + DI | 61 | 60.7 | 1.44 | +9.9% | 3.60% | 3.03% | 4 |
| H1-RR1 + DI & ADX≥20 | 46 | 65.2 | 1.74 | +11.2% | 4.30% | 3.08% | 3 |
| OR5-RR1 | 197 | 52.3 | 1.02 | +2.2% | 11.08% | 10.51% | 6 |
| OR5-RR1 + ADX≥20 | 165 | 51.5 | 0.98 | −1.3% | 13.63% | 12.93% | 5 |
| OR5-RR1 + ADX≥25 | 125 | 53.6 | 1.11 | +6.7% | 10.57% | 9.84% | 4 |
| OR5-RR1 + DI | 175 | 50.9 | 0.97 | −3.1% | 14.24% | 13.40% | 6 |
| OR5-RR1 + DI & ADX≥20 | 144 | 50.7 | 0.95 | −3.5% | 16.53% | 15.42% | 10 |
| OR15-RR1 | 114 | 44.7 | 0.75 | −15.5% | 21.83% | 21.17% | 7 |
| OR15-RR1 + ADX≥20 | 94 | 47.9 | 0.84 | −8.1% | 15.27% | 14.71% | 9 |
| OR15-RR1 + ADX≥25 | 67 | 44.8 | 0.78 | −8.5% | 13.70% | 13.33% | 8 |
| OR15-RR1 + DI | 89 | 47.2 | 0.83 | −8.2% | 14.84% | 14.59% | 6 |
| OR15-RR1 + DI & ADX≥20 | 74 | 51.4 | 0.97 | −1.1% | 12.95% | 12.62% | 9 |
| OR30-RR1 | 44 | 40.9 | 0.65 | −9.5% | 14.62% | 13.86% | 6 |
| OR30-RR1 + ADX≥20 | 39 | 38.5 | 0.56 | −11.0% | 15.08% | 14.47% | 6 |
| OR30-RR1 + ADX≥25 | 31 | 38.7 | 0.59 | −7.9% | 11.36% | 10.56% | 6 |
| OR30-RR1 + DI | 33 | 39.4 | 0.59 | −8.9% | 13.90% | 13.28% | 6 |
| OR30-RR1 + DI & ADX≥20 | 31 | 38.7 | 0.57 | −8.9% | 13.02% | 12.40% | 6 |

Costs (commission / swap, $): H1-RR6 −38 / 0; H1-RR1 −37 / 0; OR5 −347 / −46; OR15 −113 / −33; OR30 −33 / −34.

## Findings

1. **ADX ≥ 20 is the only filter that clearly helped, and only on the 60-minute range.** It removes 15 of 72
   trades and changes nothing else (all 57 kept trades are identical to the current run). PF 1.67 → 2.01 at 6R
   and 1.66 → 2.03 at 1R; equity DD 6.84% → 4.22% (6R). Random-removal check (20,000 draws removing 15
   trades): p ≈ 0.11 (6R) and 0.07 (1R). Suggestive, **not** significant, and chosen as the best of 25
   configurations on this same year.
2. **DI agreement (the Nasdaq 5M winner) did not help this ORB.** H1 PF 1.67 → 1.65 (6R), 1.66 → 1.44 (1R).
3. **The installed 6R target almost never fills.** Only 3 of 72 current trades hit 6R; 44 exit at the
   20:00 UTC time exit and 25 at the stop. In practice the strategy is a "hold the breakout until the time
   exit" system. 1R trades that return for a higher win rate (63.9%) and lower DD (3.99%).
4. **The 5/15/30-minute ranges at 1:1 did not work in this window.** 5-min is flat after costs (PF 1.02,
   commission $347 on 197 trades), 15-min loses −15.5%, 30-min loses −9.5%. No ADX/DI filter turns them
   into a credible edge (best: 5-min ADX ≥ 25, PF 1.11 +6.7%; 15-min DI&ADX≥20, PF 0.97).
   Note these keep the 13:00 UTC anchor, which is before the US cash open (13:30 UTC summer / 14:30 UTC
   winter), so a 5–30-minute range here measures pre-market trade. A classic cash-open ORB is a different
   test and was not run.
5. **Holiday early-close defect.** On 2026-06-19 (Juneteenth early close) the 5- and 15-minute variants
   could not close by 20:00 UTC; the position was held over the weekend and stopped at the Sunday reopen
   (−$294 and −$224). Same mechanism as the Nasdaq 5M report. Not fixed here.

## Limitations

- One year, 72 current trades; 28% of the period uses generated ticks.
- 25 configurations tried on the same year: the best one is an in-sample pick, not validation.
- Closed-balance and equity DD are both from the native report; no Monte Carlo or cost stress yet.

## Next steps before any deployment

1. Validate H1 + ADX ≥ 20 on 2021-09 → 2025-09 native (never used for this selection), 6R and 1R.
2. If it holds, decide 6R vs 1R separately (the target barely matters at 6R; time exit dominates).
3. Optional: retest 5/15/30-minute ranges anchored at the 09:30 New York cash open.
4. Fix the holiday/Friday session-close handling in the ORB EA family.
5. Only then consider changing the installed SET (requires user approval).

Historical results are not a forecast.
