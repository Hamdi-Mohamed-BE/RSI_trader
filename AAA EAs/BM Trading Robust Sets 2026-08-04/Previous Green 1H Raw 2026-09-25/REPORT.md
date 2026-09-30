# Previous-Green 1H — raw test report (2026-09-25)

Idea #1 from heyastral.ai/u/lucas_lalk ("Previous-Green 1H 3R Portfolio - Validated", "Diversified Leaders 1H 3R–15R").
Their rules are owner-only; the public page shows names and headline metrics only. The rules below are our own
interpretation, fixed before testing. Pipeline steps 1–4 (spec, research EA, raw native test, gate). **Result: FAIL —
stops before optimization.** Nothing installed, deployed or published. Full tables: `RESULTS.md`.

## Raw rules (EA/Previous Green 1H Research EA.mq5, compiled 0 errors / 0 warnings)

- H1 candle closes green → buy at the next bar; stop at that candle's low; target = R × stop distance.
  Both-directions variants also sell after a red candle (stop at its high).
- One position at a time; no trailing, time exit or session filter; skip if the stop is < 3× spread.
- Variants: L3 long-only 3R, L1 long-only 1R, B3 both 3R, B1 both 1R.
- Controls (3y/5y): identical stop/target but the entry ignores candle colour (long after any candle; alternating
  direction for the both-direction controls).
- Isolated tester, Exness-MT5Trial16, $10,000, 1% risk (lots rounded up per portfolio policy), Model 4 (real ticks from
  2026-01, bars-generated before), 150 ms delay; windows 6m/1y/3y/5y ending 2026-09-01. 72 native runs, none failed.

## Gate (fixed before testing)

Positive on 3y and 5y, PF ≥ 1.15 on 3y and 5y, ≥ 30 trades per window, and better than its colour-blind control.
**0 of 12 symbol/variant combinations pass.**

| Variant | XAUUSD 3y / 5y | USTEC 3y / 5y | BTCUSD 3y / 5y |
|---|---|---|---|
| L3 long 3R | +361.4% PF 1.18 / +15.3% PF 1.02, DD 84.9% | −36.8% / −81.8% | −35.8% / −89.0% |
| L1 long 1R | −40.2% / −93.0% | −84.3% / −97.5% | −92.2% / −100% |
| B3 both 3R | +72.3% PF 1.06 / +32.6% PF 1.02 | −78.7% / −88.7% | −53.8% / −90.6% |
| B1 both 1R | −64.4% / −80.6% | −91.1% / −100% | −100% / −100% |

## Findings

1. **The candle-colour signal has no durable edge on these CFDs.** Profit factors sit at 0.8–1.06 almost everywhere; the
   1R variants win ~50% (a coin flip) and lose to spread/commission over 3,000–5,800 trades.
2. **XAU long-only 3R is gold's bull trend, not the signal.** It made +211% (1y) and +361% (3y) during the 2023–2026 gold
   rally, but over 5y PF is 1.02 with an 84.9% equity drawdown and losing streaks up to 19. Green does beat buying after
   any candle on XAU (3y +361% vs +28%), but not enough to survive 2021–2023.
3. **Risk profile is unsuitable for prop accounts:** 23–33% win rate at 3R, average losing streaks 3–4, longest 12–25;
   the 1R versions have ~50% win rate but still deep drawdowns.
4. BTC runs that reached −100% show "not enough money"/"size below minimum" journal lines after equity was exhausted —
   a consequence of the wipe-out, not a separate error.
5. This does not disprove the author's private version (US equities in regular hours, a 7-instrument portfolio, possibly
   other filters/exits and much lower costs); it shows our mechanical reading of the name does not work on XAU/US100/BTC.

## Decision

Per the pipeline, a failed raw test does not go to optimization. Recommendation: stop idea #1 and move to idea #2
(30m order block) unless the user wants a specific variant explored (e.g. XAU long-only restricted to the NY session),
which would be a new pre-registered hypothesis, not a rescue of this result.

## Files

`run-config.json`, `run_pg1h.py`, `make_report.py`, `EA/` (source, EX5, compile log), `native/build.json`,
`native/pg1h-*/` (SET, tester.ini, run.json, trades.json.gz, report .htm.gz, journal.txt.gz), `RESULTS.md`.
