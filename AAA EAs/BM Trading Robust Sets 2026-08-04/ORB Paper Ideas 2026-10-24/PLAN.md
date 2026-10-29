# ORB Paper Ideas 2026-10-24 — plan (written before any result)

**Owner request:** "read all these 3 papers and come up with ideas to improve all the ORB EAs we have now and show me new
results for it and what was improved and what was not — all ORB versions 0.5 RR and full RR."
Research only. Native MT5 (isolated tester) plus ledger filters. Nothing installed and no live SET changed.

## Papers (data, not authority)
1. **Levine, "Day Trading: Adapting to Change"** (SSRN 6833239). Discretionary ES paper trading, Oct–Dec, tiny
   sample.
   - Takes the 08:00–08:15 ET ORB on a pullback to the range middle after the breakout, in the breakout direction.
   - Moves the stop to break-even once price is a bit over halfway to the target.
2. **Ladia, "Opening-Range Reversal in Dow Futures"** (SSRN 7124578). YM short-side opening reversal, 194 trades,
   rules withheld.
   - The edge sits in the earliest entry windows: 9:35–9:49 wins 65.6%, 9:50–9:59 wins 39.5%.
   - Gap-up days are stronger (not significant). Weak before 2023.
3. **Subhani, "ORB on Event-Free Fridays"** (SSRN 7589980). QQQ 30-minute ORB.
   - Entry: a resting stop order at the range boundary (gap-aware fill).
   - Stop: one range width. No target; stepped trail (+1R → break-even, +2R → +1R, …); flat at the close.
   - Skips NFP/CPI/FOMC days and mega-cap earnings weeks; Friday only. Deflated Sharpe 0.67 (not significant after
     search). Monday–Thursday earned nothing.

## Ideas tested (declared now; one change at a time against a fresh baseline)

| Code | Idea | From | How |
|---|---|---|---|
| EARLY | Only take early breakouts | Ladia (+ Subhani's cutoff) | Generic M30 ORBs: entry window 180 → 60 min. US100 H1 13UTC: 60 → 30 min. Selective V3: cutoff 11:30 → 10:30 |
| BE60 | Break-even once 60% of the way to the target | Levine | `InpBreakEvenAtR` = 0.6 × target R |
| RETEST | Enter on the retest, not the breakout | Levine | Generic `InpEntryMode` = 1 (break-and-retest). V3 is already a retest EA: N/A |
| STOPENTRY | Resting stop order at the range boundary | Subhani | Generic `InpUsePaperStopEntry` = true. V3: N/A |
| LADDER | No target, stepped whole-R trail, flat at session end | Subhani | Research copy of the generic EA, with one new input `InpStepTrailR` (off = byte-identical behaviour; parity-checked). Target set to 20R. Full-RR versions only; V3: N/A |
| EVENTFREE | Skip NFP / CPI / FOMC days | Subhani | Ledger filter on the baseline trades. Calendar: `Portfolio Long History 2026-10-08/Calendar.json` (source-receipted; mega-cap earnings weeks not available) |
| FRIDAY | Fridays only | Subhani | Ledger filter on the baseline trades, with a weekday table as a diagnostic |

Ledger filters remove whole trading days. Each ORB takes at most one trade per day, so the other trades are unchanged.
Results are compared in R per trade (net ÷ 1% of balance at entry). This is a ledger overlay, not a native run.

## Base versions (10)
The four generic `ORB Volume Data EA` ORBs plus US100 Selective V3, each in two versions:
- **0.5R:** `_00 Live profiles/ORB05 Sets`.
- **Full RR** (original installer SETs): XAU NY 1.5R, XAU London-NY 1.0R, US100 NY 4R, US100 H1 13UTC 6R, V3 2R.

Inputs are unchanged except the one tested change.

## Native protocol
- Production EX5s (`ORB Volume Data EA.ex5` 67ee6976…, `US100 Selective ORB Retest EA.ex5` ca4bb883…); LADDER uses the
  research copy.
- Exness-MT5Trial16, Model 4 (real ticks from 2026-01-01; earlier generated), 150 ms, $10,000, 1% risk.
- One run per version: 2021-10-24 → 2026-10-24.
- Windows by trade open date from `data_split.py`:

  | Window | Dates |
  |---|---|
  | Dev | 2021-10-24 → 2023-10-24 |
  | Val | 2023-10-24 → 2024-10-24 |
  | OOS | 2024-10-24 → 2026-10-24 |

  These EAs were built on this history, so the windows are chronological checks, not untouched data.

## Verdict per idea × version
Total net R and PF are compared with the fresh baseline in each of dev, val and OOS.
- **IMPROVED:** total R higher in all three windows and the 5-year PF higher.
- **MIXED:** total R higher in exactly two windows.
- **NOT IMPROVED:** one window or none.
- **Thin sample:** under 30 trades in 5 years is flagged as thin, whatever the result.
- Every table shows trades, trades/month and trades/day.
- Nothing is deployed. Any adoption needs the owner's decision and the pipeline.
