# EMA + VWAP trend-pullback (US100, M3) — raw test report (2026-09-25)

User request: "try good strategy of the EMA and VWAP strategy on the 3 min time frame for US100". Classic VWAP + 9/21 EMA
trend-pullback, rules fixed before testing (`run-config.json`). **Result: FAIL (both targets).** Research only.
Full tables: `RESULTS.md`.

## Rules (EA/EMA VWAP Pullback Research EA.mq5, 0 errors / 0 warnings)

M3; session VWAP from 09:30 NY (typical price × tick volume); long when close > VWAP and EMA9 > EMA21 (short mirror);
pullback touching EMA21 within the last 3 bars while closes hold beyond VWAP; trigger = close back beyond EMA9; stop
beyond the 4-bar extreme + 0.1 ATR (skip > 3 ATR); target 2R or 1R; entries 09:45–15:30 NY, flat 15:55, max 2 trades/day.
Control: first trend bar (no pullback). Isolated tester, Exness USTEC, $10,000, 1% risk, Model 4, 150 ms delay;
windows 6m/1y/3y/5y ending 2026-09-25. 12 runs (interrupted once by a session end and resumed).

## Results (trades, per month, per trading day)

| Window | 2R target | 1R target |
|---|---|---|
| 6m | 221 (36.6/mo, 1.67/day) −27.3% PF 0.81 win 32% | 228 (37.7/mo, 1.73/day) −11.6% PF 0.91 win 49% |
| 1y | 445 (37.1/mo, 1.70/day) −20.6% PF 0.93 win 35% | 457 (38.1/mo, 1.75/day) −12.6% PF 0.95 win 50% |
| 3y | 1,322 (36.7/mo, 1.69/day) −83.2% PF 0.76 win 31% | 1,364 (37.9/mo, 1.74/day) −79.5% PF 0.75 win 46% |
| 5y | 2,183 (36.4/mo, 1.67/day) −95.1% PF 0.80 win 31%, loss streak up to 23 | 2,267 (37.8/mo, 1.74/day) −95.9% PF 0.72 win 45% |
| Control 5y (no pullback) | 2,503, −37.6%, PF 0.97 | 2,561, −67.0%, PF 0.92 |

## Findings

1. Negative in every window on both targets; on M3 the spread/commission over ~37 trades/month outweighs any edge.
2. The pullback trigger is worse than the plain trend entry (control), so the "pullback to EMA21" timing destroys value.
3. Consistent with the earlier VWAP studies in this repo (only XAU RSI VWAP survived). 1,214 "[Market closed]" journal
   lines are end-of-day close retries on holidays/early closes; they do not change the result.

## Decision

Fails the pre-registered gate; no optimization.
