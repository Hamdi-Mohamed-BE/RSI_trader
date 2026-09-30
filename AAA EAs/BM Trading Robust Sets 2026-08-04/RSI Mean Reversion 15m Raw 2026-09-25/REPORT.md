# RSI Mean Reversion 15m — raw test report (2026-09-25)

Idea #3 from heyastral.ai/u/lucas_lalk ("High Win-Rate RSI Mean Reversion BTC 15m": 32 trades, 93.8% win, +9.5%,
DD 7.3%, about a 5-day window). Their rules are owner-only; ours are a standard RSI(2) reading fixed before testing.
Pipeline steps 1–4. **Result: FAIL on all 9 symbol/variant combinations — stops before optimization.** Nothing
installed, deployed or published. Full tables: `RESULTS.md`.

## Raw rules (EA/RSI Mean Reversion 15m Research EA.mq5, 0 errors / 0 warnings)

- M15. Buy when RSI(2) of the just-closed bar < 10 (sell when > 90); trend filter variants trade only on the EMA200 side.
- Exit at the next bar after RSI(2) crosses back past 50, or after 16 bars (4 h). No take profit.
- Stop 3 × ATR(14) (TF3, NF3) or 1.5 × ATR (TF15). One position at a time; 1% risk to the stop (lots rounded up).
- Control CT: trend-side entry on ~5% of bars chosen by a deterministic hash, 3 ATR stop, exit after 4 bars.
- Indicators created once in OnInit (the shared helpers recreate handles per call, too slow for EMA200 on M15 × 5y).
- Isolated tester, Exness-MT5Trial16, $10,000, Model 4 (real ticks from 2026-01), 150 ms delay; windows 6m/1y/3y/5y
  ending 2026-09-01. 42 native runs, none failed.

## Results (3y / 5y; full tables with streaks in RESULTS.md)

| Variant | XAUUSD | USTEC | BTCUSD |
|---|---|---|---|
| TF3 trend + 3 ATR | −52.1% PF 0.86 / −78.3% PF 0.84 | −64.0% / −92.9% | −40.4% / −89.8% |
| NF3 no filter | −100% / −100% | −96.2% / −100% | −97.8% / −100% |
| TF15 trend + 1.5 ATR | −80.3% / −94.0% | −90.1% / −100% | −81.9% / −100% |
| Random control | −40.9% / −63.4% | −44.8% / −72.5% | −54.7% / −90.0% |

Short-window bright spots (BTC 1y TF15 +50.2%, TF3 +20.5%; US100 6m +4–14%) do not survive 3y/5y.

## Findings

1. **No edge:** PF 0.63–0.90 over 3y/5y everywhere; the RSI signal loses more than random trend-side entries in
   8 of 9 cases.
2. **The high win rate is real but not the claimed one:** 54–66% (not 94%), average win streaks ~2.5–2.9 (longest
   10–19), average loss streak ~1.6 — but thousands of small wins are outweighed by stop-outs and costs
   (3,000–12,000 trades over 3y/5y).
3. **Their 94% was a ~5-day, 32-trade sample.** This test covers up to 5 years; the short-window numbers are not
   representative.
4. Journal lines: "[No money]" only after an account was already wiped out; "[Market closed]" = a time-stop exit
   retried at the next open bar. Neither changes the conclusion.

## Decision

Fails the pre-registered gate; per the pipeline it does not go to optimization.

## Files

`run-config.json`, `run_rsi15.py`, `make_report.py`, `EA/`, `native/build.json`, `native/rsi15-*/` (SET, tester.ini,
run.json, trades.json.gz, report .htm.gz, journal.txt.gz), `RESULTS.md`.
