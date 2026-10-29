# ORB Paper Ideas 2026-10-24 — REPORT

Owner request: read three SSRN papers, turn them into ideas to improve every ORB EA at 0.5R and at full RR, and show
what improved and what did not.

- **Plan:** predeclared in `PLAN.md`.
- **Runs:** 51 native MT5 Model-4 runs (5 years, $10k, 1% risk, 0 failed runs) plus two ledger filters.
- **Files:** `RESULTS.md` (every table), `STREAKS.md` (win rate and streaks before → after), `RESULTS.json`.
- **Parity:** the research copy with the new input off reproduced production exactly (82/82 identical trades).

## Verdict: no paper idea improved any ORB. Keep the current settings.
Verdict rule: IMPROVED = more total R in all three windows (dev 2021–23, validation 2023–24, OOS 2024–26) and a
higher 5-year PF.

| Idea (paper) | Versions tested | IMPROVED | MIXED | NOT | Main effect |
|---|---:|---:|---:|---:|---|
| EARLY — entries only in the first third of the window (Ladia) | 10 | 0 | 1 | 9 | Higher R per trade on gold, but cuts 55–75% of trades, so total R falls everywhere (US100 H1 full: +60.9R → +29.9R) |
| BE60 — break-even at 60% of the target (Levine) | 10 | 0 | 1 | 9 | At 0.5R the win rate falls 16–26 points; best case XAU NY full +2.3R (2 of 3 windows); US100 H1 full identical (BE at 3.6R never triggers) |
| RETEST — enter on the retest (Levine) | 8 | 0 | 0 | 8 | The EA's retest mode almost never triggers with these SETs (1–23 trades in 5 years): **not a valid test** of the idea |
| STOPENTRY — resting stop at the range boundary (Subhani) | 8 | 0 | 3 | 5 | The EA's paper-stop path **skips the volume / range / body filters** and trades nearly every day (700–1,000 trades), so it is not the paper's single filtered order. XAU London-NY −48% / −35%, US100 NY −58% / −23%. US100 H1 full +145% but PF 1.21 vs 1.46 and a dev loss |
| LADDER — no target, whole-R stepped trail, flat at the close (Subhani) | 4 | 0 | 0 | 4 | Worse on all four full-RR ORBs (−1.2R to −18.7R) |
| EVENTFREE — skip NFP / CPI / FOMC days (Subhani; ledger filter) | 10 | 0 | 5 | 5 | Within ±3R of the baseline. XAU NY's news days are its best trades (+0.27 to +0.33R mean) |
| FRIDAY — Fridays only (Subhani; ledger filter) | 10 | 0 | 1 | 9 | 7–52 trades in 5 years; Friday is a losing day for both US100 NY versions |

## Baselines (5 years, 1% risk)

| ORB | Target | Trades | / month | / day | Return | PF | Win % | Eq DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| XAU NY M30 | 0.5R / 1.5R | 82 | 1.37 | 0.045 | +8.9% / +9.7% | 1.46 / 1.49 | 68.3 / 37.8 | 3.95% / 5.47% |
| XAU London-NY M30 | 0.5R / 1.0R | 121 | 2.02 | 0.066 | +3.5% / +19.3% | 1.10 / 1.50 | 67.8 / 47.9 | 8.22% / 6.04% |
| US100 NY M30 | 0.5R / 4R | 51 | 0.85 | 0.028 | +1.8% / +37.7% | 1.11 / 2.51 | 68.6 / 52.9 | 4.37% / 6.81% |
| US100 H1 13UTC | 0.5R / 6R | 295–296 | 4.93 | 0.162 | +14.5% / +77.8% | 1.17 / 1.46 | 68.8 / 47.0 | 14.35% / 17.98% |
| US100 Selective V3 | 0.5R / 2R | 35 | 0.58 | 0.019 | +11.8% / +17.3% | 4.69 / 3.15 | 88.6 / 62.9 | 1.51% / 3.55% |

**Side finding:** on every ORB except XAU NY, the full-RR target earned more than the 0.5R target on the same signals.
XAU NY is nearly equal at both targets (+8.7R vs +9.6R).

## What the diagnostics say about the papers
- **Entry timing (Ladia).** It holds only for XAU NY: +0.24R in the first hour after the range, −0.05R after two hours.
  XAU London-NY shows the opposite, and US100 has no clear pattern. Not general enough to impose a cutoff.
- **Weekday (Subhani's Friday).** Friday is the best weekday only for XAU NY 0.5R. On US100 NY it is a loser (−0.26R and
  −0.10R).
- **Filters are what make our ORBs work.** STOPENTRY, which bypasses them, loses heavily on 4 of 5 ORBs.

## Limits
- **In-sample:** these EAs were built on this history, so the windows are chronological checks, not untouched data.
  Ticks before 2026 are generated.
- **Two ideas were not testable as written:** RETEST and STOPENTRY could not be tested faithfully with the existing EA
  options. A faithful version needs new code; this is offered, not done.
- **Missing filter data:** mega-cap earnings weeks (part of Subhani's filter) were not available.

Nothing installed, changed or pushed.
