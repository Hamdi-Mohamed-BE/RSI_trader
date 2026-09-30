# Order Block 30m — raw test report (2026-09-25)

Idea #2 from heyastral.ai/u/lucas_lalk ("JPM 30m Order Block - Validated": 121 trades, 72.1% win, +37.4%, DD 7.9%;
"AEP 30m Order Block - Validated"). Their rules are owner-only; ours are a common mechanical SMC reading fixed before
testing. Pipeline steps 1–4. **Result: FAIL on all 9 symbol/target combinations — stops before optimization.**
Nothing installed, deployed or published. Full tables: `RESULTS.md`.

## Raw rules (EA/Order Block 30m Research EA.mq5, 0 errors / 0 warnings)

- M30. Swing = 3-bar fractal confirmed before the break. Break = first close beyond the latest swing high/low.
- Impulse leg (leg extreme → break close) ≥ 1.5 × ATR(14).
- Order block = last opposite-colour candle at or ≤ 5 bars before the leg extreme; size 0.2–2.0 ATR.
- Limit at the near edge of the block (first return); cancelled after 48 bars; one setup/position at a time.
- Stop = far edge ∓ 0.1 ATR. Targets 0.5R / 1R / 2R. Skip if stop < 3× spread.
- Control: same break and impulse, limit at the 50% pullback of the leg, stop beyond the leg extreme.
- Isolated tester, Exness-MT5Trial16, $10,000, 1% risk (lots rounded up), Model 4 (real ticks from 2026-01),
  150 ms delay; windows 6m/1y/3y/5y ending 2026-09-01. 54 native runs.

## Results (3y / 5y; full tables with streaks in RESULTS.md)

| Target | XAUUSD | USTEC | BTCUSD |
|---|---|---|---|
| 0.5R | −48.4% PF 0.79 / −71.7% PF 0.78 (win 62%) | −54.6% / −83.5% (win 59–61%) | −55.8% / −92.8% (win 61–64%) |
| 1R | −47.3% PF 0.85 / −69.9% PF 0.85 | −65.8% / −88.0% | −51.2% / −91.8% |
| 2R | −48.6% PF 0.87 / −67.3% PF 0.88 | −63.0% / −84.6% | −57.5% / −91.7% |

Only the most recent year is mildly positive on XAU (+11–16%) and US100 (+1–11%), which does not survive 3y/5y.

## Findings

1. **No edge on any asset or target:** profit factor 0.68–0.88 over 3y/5y everywhere.
2. **The order-block location adds nothing over a generic pullback:** it failed to beat the 50%-pullback control in
   5 of 9 cases (all 0.5R cases); where it did, both lost heavily.
3. **The high win rate is real but not profitable:** 0.5R wins 59–68% with average win streaks of ~2.5–3 (longest
   9–15), but the losses outweigh the small winners after costs over 800–2,200 trades.
4. **Execution notes:** journals contain "[Market closed]" cancellation retries (expired limits are removed at the next
   open bar), 80 "invalid price" limits too close to market (not placed) and 12 "invalid request" lines — none change
   the conclusion. The first US100 run failed because a Remotion render (another project) held port 3000, the MT5
   agent port; it is kept as `native/FAILED-port3000-*` and was rerun. The runner now waits for port 3000 instead of failing.
5. As with idea #1, this does not disprove the author's private rules (US single stocks, their own definitions and
   costs); it shows our mechanical order-block definition has no edge on XAU/US100/BTC CFDs.

## Decision

Fails the pre-registered gate; per the pipeline it does not go to optimization.

## Files

`run-config.json`, `run_ob30.py`, `make_report.py`, `EA/`, `native/build.json`, `native/ob30-*/` (SET, tester.ini,
run.json, trades.json.gz, report .htm.gz, journal.txt.gz), `RESULTS.md`.
