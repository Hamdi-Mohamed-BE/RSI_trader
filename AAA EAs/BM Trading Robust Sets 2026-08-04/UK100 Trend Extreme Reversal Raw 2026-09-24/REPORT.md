# UK 100 trend + extreme-move reversal — raw native test (2026-09-24)

Research only. Nothing deployed; no BAT, installer or website change.

## Idea and frozen rules

Source: a short-video transcript (UK 100, "779 trades, 57% win rate, PF 1.3 over 8 years"). The transcript gives no
exact rules, so the user chose options and every combination was tested (2 × 3 × 3 × 3 = 54):

- Trend (last completed D1 bar): close vs **SMA(200)** or close vs **EMA(50)**. Long setups only in an uptrend,
  short setups only in a downtrend.
- Extreme (last completed signal bar): **RSI(2) < 10 / > 90**; **close ≥ 2 ATR(14) beyond the 10-bar high/low**;
  or **3 consecutive closes** against the trend.
- Signal timeframe: **H1, H4, D1**.
- Exit: **RSI(2) back across 50 with a 2 ATR stop**; **close back across SMA(5), no stop** (sized as if 2 ATR);
  or **fixed 1:1 at 1.5 ATR**.
- Market entry on the first in-session tick after the signal bar; one position; 1% equity risk, lots rounded up.

EA `EA/Trend Extreme Reversal.mq5` v1.02 (v1.01: retry when the market is closed; v1.02: process a new bar only once
the broker session is open — both found and fixed during the smoke test, results identical after the fix).

## Evidence type

Native MT5 Strategy Tester, isolated portable terminal `_Backtests/MT5-DMC-20260811`, profile "Calyx Research Empty",
`[Experts] Enabled=0`. Exness-MT5Trial16 demo, UK100 (contract 1, tick 0.01, min 0.05 lot; history downloaded by the
tester from 2019-07), $10,000, 1:2000, Model=4, 150 ms delay, 2021-09-19 → 2026-09-19 (end exclusive). History
quality **14% real ticks** (real UK100 ticks only from 2026-01-02). One native 5y run per combination; all 54 exit 0
with matching reports and no init/history/critical errors. **6m / 1y / 3y figures are slices of each native 5y
ledger, recompounded from $10,000** — native trades, not separate native runs per window (`summarize.py`,
`RESULTS.json`). Two earlier smoke attempts failed with "tester agent authorization error" because another
process held port 3000; they are kept under `native/FAILED-*` and excluded.

## Results — best 10 by 5-year profit factor

| Combination | 5y trades | 5y win % | 5y PF | 5y return | 5y equity DD | 3y PF / return | 1y PF / return | 6m PF / return | Best win / worst loss streak |
|---|---:|---:|---:|---:|---:|---|---|---|---|
| H4 · EMA50 · RSI2 · 1:1 | 470 | 51.5 | 0.94 | −12.1% | 26.8% | 1.06 / +8.3% | 1.27 / +10.9% | 1.34 / +6.2% | 7 / 8 |
| H4 · EMA50 · RSI2 · SMA5 no stop | 407 | 60.7 | 0.90 | −9.5% | 26.1% | 1.06 / +3.2% | 1.48 / +6.8% | 2.48 / +7.3% | 19 / 5 |
| D1 · SMA200 · 2ATR · SMA5 no stop | 116 | 58.6 | 0.87 | −3.2% | 11.8% | 1.04 / +0.5% | 2.12 / +3.4% | 2.71 / +2.7% | 7 / 5 |
| H4 · SMA200 · RSI2 · 1:1 | 491 | 49.9 | 0.87 | −27.0% | 43.0% | 1.04 / +5.7% | 1.29 / +11.6% | 1.34 / +6.0% | 7 / 9 |
| H4 · EMA50 · 3 closes · SMA5 no stop | 439 | 64.2 | 0.86 | −14.6% | 28.3% | 0.90 / −5.2% | 1.41 / +6.2% | 2.24 / +6.2% | 27 / 5 |
| D1 · SMA200 · 2ATR · 1:1 | 96 | 50.0 | 0.85 | −7.2% | 14.6% | 1.28 / +6.7% | 1.56 / +4.8% | 1.99 / +4.2% | 5 / 8 |
| H4 · EMA50 · RSI2 · RSI50 + stop | 473 | 59.6 | 0.85 | −15.2% | 28.5% | 1.01 / +0.4% | 1.38 / +6.7% | 2.09 / +5.9% | 23 / 8 |
| H4 · SMA200 · RSI2 · RSI50 + stop | 483 | 59.2 | 0.83 | −18.6% | 33.3% | 1.00 / +0.1% | 1.50 / +8.5% | 2.59 / +7.4% | 23 / 10 |
| H4 · SMA200 · RSI2 · SMA5 no stop | 391 | 61.4 | 0.81 | −18.5% | 36.2% | 0.96 / −2.0% | 1.58 / +7.6% | 3.46 / +8.4% | 19 / 5 |
| H4 · EMA50 · 3 closes · RSI50 + stop | 497 | 61.4 | 0.80 | −20.0% | 29.5% | 0.89 / −6.0% | 1.44 / +6.7% | 2.35 / +6.4% | 21 / 6 |

All 54 rows: `RESULTS.json`. By timeframe: **H1** 5y returns −84% to −100% (PF 0.52–0.75); **H4** −9.5% to −53%
(PF 0.72–0.94); **D1** −3% to −17% (PF 0.19–0.87, only 40–130 trades in 5 years).

## Findings

1. **No combination is profitable over 5 years** (best PF 0.94). The video's "PF 1.3 over 8 years" is not reproduced
   by any of these faithful interpretations on Exness UK100 CFD data.
2. **The last 12 months look good for most H4 versions** (1y PF 1.27–1.75, 6m PF up to 3.46) — the same pattern as
   Gold Overnight IVB: a recent regime lifts results that fail over the longer window.
3. **Costs matter:** on the best H4 row, swap −$1,588 and commission −$445 over 5 years are larger than its −$1,213
   total loss; before costs it is roughly break-even. H1 versions trade 1,500–3,300 times and costs destroy them.
4. **High win streaks exist** (no-stop and RSI-50 exits: 60–65% wins, best streaks 19–27) but the losses are larger
   than the wins, so the streaks do not produce profit.
5. Execution notes: a few entries per run were rejected with "invalid stops" at session/weekly-open gaps.

## Recommendation

**SKIP** in raw form. If revisited, the only direction with some support is H4 with RSI(2) and a cost-aware rule
(no overnight holds, or a minimum expected move vs. swap), tested on a period not used for choosing it.
Historical results are not a forecast.
