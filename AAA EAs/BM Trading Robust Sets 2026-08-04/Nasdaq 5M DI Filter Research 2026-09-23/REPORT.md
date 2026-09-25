# Nasdaq 5M Candle Momentum — ADX/DMI filter study (last year)

Date: 2026-09-23. Research only. No production EA, SET, BAT, website cache or MT5 chart was changed.

## Evidence type — read first

- **Current version** = the native MT5 Every Tick ledger already on disk:
  `Active Portfolio Full Pipeline 2026-09-05/11 Nasdaq 5M Candle Momentum/Reports/locked/ustec-locked-fixed-rr2.5-trades.json`
  (Exness USTEC, $10,000, 1% equity risk, 2025-09-01 → 2026-09-01, 100% history quality, 256 trades).
  Recompounding its per-trade returns reproduces the native report exactly: $13,811.80, +38.12%, PF 1.21.
- **New version** = the same native trades, keeping only those that pass the new filter, recompounded at 1%.
  This is a **ledger filter replay, not a new native MT5 run**. The filter removes trades only; it never
  changes an entry, stop, target or exit, and the EA takes at most one signal per day, so a skipped signal
  does not create a different later trade. Two Monday signals (2025-12-08, 2026-02-23) were blocked in the
  native run by a still-open Friday position; they could not be reconstructed here.
- Indicator values were computed from USTEC bars on the connected Exness demo account (Exness-MT5Trial16),
  not the tester's own feed. Signal parity check: EMA12 direction on those bars matched the side of **256/256**
  native trades. The +DI/−DI formula follows MT5's built-in `iADX`; exact MT5 buffer values were not
  compared bar by bar, so a native confirmation run is still required.

## Rule added

For a long signal (09:30 NY M5 close above EMA12) require **+DI(14) > −DI(14)** on that closed M5 bar;
for a short require **−DI > +DI**. Everything else is unchanged: 4 ATR stop, fixed 2.5R, flat 15:55 NY,
1% risk. Implemented as `InpRequireDIAgreement` (default **false**, so the new EA behaves exactly like the
current one unless the research SET enables it).

## Selection protocol

- Development: 2025-09-01 → 2026-04-30 (169 trades). Holdout: 2026-05-01 → 2026-08-31 (87 trades).
- 26 ADX/DI configurations tried (ADX ≥ 15/20/25/30, ADX rising, ADX ≥ 20 and rising, DI agreement,
  DI + ADX ≥ 20 on M5/H1/D1, plus two inverse checks). All in `Data/development_search_26_configs.csv`.
- Rule fixed before looking at the holdout: highest development PF, keeping ≥ 60% of trades and
  development return ≥ baseline. Frozen in `selection-frozen.json`.
- The earlier Step 11 optimisation (82 configurations, same EA) used this year as its locked test year,
  so this year has now been used for selection once. It is no longer untouched evidence.

## Results (1% risk, $10,000 start, closed-balance drawdown)

See `RESULTS.json`. Full year: current 256 trades, PF 1.21, +38.12%, 41.41% win rate, 10.99% DD →
new 188 trades, PF 1.42, +55.86%, 44.15% win rate, 9.82% DD. Holdout only: current PF 1.11, +5.56% →
new PF 1.38, +12.82%, DD 9.88% → 5.66%.

Random-removal check (20,000 draws removing the same number of trades): holdout p ≈ 0.09 for PF, full
year p ≈ 0.02 (optimistic, includes the development months). Suggestive, not conclusive: 57 holdout trades.
The gain is concentrated in longs (PF 1.09 → 1.52); shorts are roughly unchanged (1.40 → 1.42).

## Separate defect found (not fixed here)

36 of 256 native trades exited after the intended 15:55 NY flat. Most Mondays and some Fridays closed at
the next session (17:00/18:00 NY), 10 Friday positions were held over a weekend and 1 over the Christmas
holiday (longest hold 80.4 hours). This also blocked the two Monday signals above. Those 36 late trades
contributed **+18.55R of the year's +34.92R**, so a large part of the current result depends on holding past
the intended exit; fixing the defect could lower returns. Cause not yet diagnosed (needs the tester
journal). This matters for prop-firm weekend/overnight rules.

The DI filter's improvement does not come from those late trades: on the 220 on-time trades the current
version has PF 1.12 (+16.38R) and the new version, on its 162 on-time trades, PF 1.32 (+29.70R).

## Next steps before any deployment

1. Compile this EA and run native MT5 Every Tick with the research SET for the same year: must reproduce
   188 trades and these figures.
2. Validate on 2023-09 → 2025-09 (never used by this selection) using the existing 3-year native ledger.
3. Investigate the session-close defect.
4. Only then consider changing the portfolio selection (requires user approval).

Historical results are not a forecast.

## Addendum — 5-minute candle trailing stop (requested 2026-09-23 20:24)

Tested on the same 188 DI-filtered entries. Exits were **simulated on M5 bars** (Exness demo USTEC,
bid bars + recorded spread for shorts, stop assumed before target inside one bar, exact stop fills with
no slippage, flat at 15:55 NY, 0.006R commission per trade). Trailing rule: after each closed M5 candle,
move a buy's stop to that candle's low (a sell's to its high), only if tighter.

Simulator check against native MT5 on the 220 on-time current trades: 99.1% same win/loss sign,
correlation 0.98, but the simulator is **optimistic** (+24.45R vs native +16.38R). Compare variants with
each other inside the simulator, not with native figures.

| Simulated, 188 DI trades | Return | PF | Win rate | Avg win / loss | Closed DD | Win / loss streak | Median hold |
|---|---:|---:|---:|---:|---:|---:|---:|
| A. Current exits (4 ATR stop, 2.5R, flat 15:55) | +73.12% | 1.56 | 45.2% | +1.78R / −0.92R | 9.37% | 11 / 10 | 125 min |
| B. Candle trail + 2.5R target | +13.74% | 1.29 | 50.0% | +0.62R / −0.47R | 5.45% | 8 / 6 | 20 min |
| C. Candle trail, no target | +17.45% | 1.36 | 50.0% | +0.65R / −0.47R | 5.45% | 8 / 6 | 20 min |
| D. Trail only after +1R, 2.5R target (extra) | +22.69% | 1.24 | 50.5% | +1.12R / −0.91R | 9.68% | 12 / 9 | 50 min |

Holdout May–Aug 2026: A +15.6% (PF 1.46), B +0.98% (1.06), C +1.68% (1.11), D +6.1% (1.22).

Conclusion: trailing on every M5 candle stops most trades out within about 20 minutes and cuts the
average winner from about 1.8R to about 0.6R. Keep the current exits with the DI entry filter.
Real stop slippage would make B and C worse than shown. Full metrics in `TRAIL_RESULTS.json`.

## Native MT5 confirmation — current vs DI filter, 6m / 1y / 3y / 5y (run 2026-09-23 19:50–19:59 UTC)

Evidence type: **native MT5 Strategy Tester** (not replay, not simulation). Isolated portable terminal
`_Backtests/MT5-DMC-20260811`, profile "Calyx Research Empty", `[Experts] Enabled=0`, Model=4 (every tick
based on real ticks), ExecutionMode=150 ms, USTEC M5, Exness-MT5Trial16, $10,000, 1:2000, 1% risk, adaptive
portfolio controls off, server UTC offset 0. End date 2026-09-23 (exclusive). Runner `run_native_compare.py`;
DI EA compiled by MetaEditor64 (0 errors, 0 warnings, EX5 SHA c16a8cad7954…). All 8 runs: exit 0, fresh
matching report, no init/history/critical errors. Full metrics: `NATIVE_RESULTS.json`; reports under `native/`.

| | 6m cur | 6m DI | 1y cur | 1y DI | 3y cur | 3y DI | 5y cur | 5y DI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Return | +8.42% | +15.34% | +39.68% | +55.15% | +118.99% | +129.05% | +125.62% | +177.21% |
| Profit factor | 1.11 | 1.27 | 1.22 | 1.39 | 1.18 | 1.28 | 1.13 | 1.21 |
| Trades | 131 | 92 | 256 | 191 | 762 | 575 | 1272 | 969 |
| Win rate | 39.7% | 41.3% | 41.4% | 43.5% | 40.7% | 41.7% | 39.1% | 40.5% |
| Max win / loss streak | 7 / 11 | 3 / 10 | 11 / 11 | 11 / 10 | 11 / 12 | 11 / 12 | 11 / 12 | 11 / 12 |
| Balance DD | 10.35% | 9.44% | 11.88% | 10.08% | 19.25% | 19.66% | 22.30% | 19.69% |
| Equity DD | 11.40% | 10.50% | 12.89% | 10.92% | 20.23% | 20.22% | 24.61% | 20.59% |
| Commission / swap $ | −70 / −52 | −53 / −55 | −186 / −219 | −153 / −163 | −836 / −560 | −622 / −407 | −1359 / −632 | −1174 / −533 |
| History quality | 100% real | 100% real | 72% real | 72% real | 24% real | 24% real | 14% real | 14% real |

Calendar years (5y run): 2021 (Q4 only) −3.7% vs −4.0%; 2022 +18.7% vs +27.4%; 2023 −9.4% vs +1.2%;
2024 +27.9% vs +16.3%; 2025 +43.6% vs +51.9%; 2026 YTD +18.6% vs +26.8%. DI is better in 4 of 6, worse in 2024.

Caveats: the tester has real ticks only from 2026-01-01, so earlier months use ticks generated from bars.
The 1y window was already used to select the filter; 2021-09 → 2025-08 was never used for selection and DI
still improved PF there. Results are historical, not a forecast.

### Session-close defect — native cause found

Every journal failure in all 8 runs is `[Market closed]` on the 15:55 NY flat close, and all 27 affected days
in 5 years are **winter Fridays**: 15:55 NY = 20:55 server time, after Exness USTEC's Friday trading session
ends. The EA retries on every tick until Sunday's reopen, so those positions are held over the weekend
(up to ~80 h). Holiday early closes (e.g. 2026-06-19, 2026-07-03) cause the same kind of overnight hold.
In these native runs the overnight holds are a small part of results (5y current +$1,052 of +$12,562), and
DI still improves same-day-only PF (5y 1.12 → 1.21). Fix to test next: close at the earlier of 15:55 NY or
a few minutes before `SymbolInfoSessionTrade` end for that day.
