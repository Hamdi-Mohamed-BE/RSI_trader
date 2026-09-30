# No-wick candle entry model — raw test report (2026-09-25)

Source: Instagram reel instagram.com/reels/DdpQBspxhmS (@italian_founder, "88%+ winrate entry model in 1 minute"),
transcript supplied by the user. Rules and our fill-in choices are in `run-config.json` (fixed before testing).
**Result: FAIL on all 8 symbol/timeframe combinations.** Research only; nothing deployed. Full tables: `RESULTS.md`.

## Rules tested (EA/No Wick Candle Research EA.mq5, 0 errors / 0 warnings)

Trend = close vs EMA200 and EMA50 vs EMA200. Bullish trend: bullish candle with no bottom wick (≤ max(1 point, 2% of
range)); bearish mirror. Limit at the candle open (20-bar expiry), stop beyond the most recent 10-bar swing + 0.2 ATR,
target 1:1, one setup at a time. M15 and H1. Control: any trend-direction candle (wick ignored).
Isolated tester, Exness-MT5Trial16, $10,000, 1% risk, Model 4 (real ticks from 2026-01), 150 ms delay; windows
6m/1y/3y/5y ending 2026-09-25. 48 native runs (the run was interrupted once by a session end and resumed; completed
cases were kept, the interrupted case was rerun).

## Results (5y; trades per month / per trading day)

| Symbol | M15 | H1 |
|---|---|---|
| XAUUSD | 2,063 (34/mo, 1.58/day) −97.5% PF 0.78 win 46% | 491 (8/mo, 0.38/day) +9.0% PF 1.03 win 52%, DD 21.5% |
| USTEC | 1,889 (31/mo, 1.45/day) −78.7% PF 0.84 win 47% | 497 (8/mo, 0.38/day) −30.1% PF 0.87 win 48% |
| BTCUSD | 2,787 (46/mo, 2.14/day) −97.4% PF 0.77 win 46% | 622 (10/mo, 0.48/day) −24.1% PF 0.92 win 49% |
| EURUSD | 2,463 (41/mo, 1.89/day) −96.8% PF 0.74 win 46% | 600 (10/mo, 0.46/day) −47.7% PF 0.81 win 46% |

Short-window positives (e.g. XAU H1 1y +6.4%, USTEC H1 6m +4.5%, BTC H1 1y +4.9%) do not survive 3y/5y.

## Findings

1. **The win rate is 42–55%, not 88%.** At 1:1 after spread/commission that is a losing system on every market.
2. **"No wick" does add something vs any candle** (the control loses even more in almost every case), but not enough
   to turn it profitable; the best case (XAU H1, 5y PF 1.03) is far below the gate.
3. The reel itself ends by showing its own AI-built bot on a 5-year tick backtest — consistent with this result.
4. Journal lines: 1,634 "[Market closed]" (expired limits removed at the next open bar), 432 "invalid price" (limits too
   close to market, not placed). None changes the conclusion.

## Decision

Fails the pre-registered gate; no optimization.
