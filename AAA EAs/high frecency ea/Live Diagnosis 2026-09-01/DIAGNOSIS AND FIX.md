# XAUUSD M1 OCO — live diagnosis and Live Guard v1.20

## Decision

The old OCO build failed its first meaningful live-demo check. It must not be traded live. Live Guard v1.20 fixes the execution and runaway-trading defects, but the underlying strategy is still **research/demo only** because the latest valid real-tick test remains negative.

## 2026-09-01 demo result

Timezone: Africa/Lagos. Account: 472646916 on Exness-MT5Trial16 (demo). Balance operations and demo resets are excluded; open positions are reported separately.

| Metric | Result |
|---|---:|
| Closed trades | 891 |
| Wins / losses / breakeven | 258 / 631 / 2 |
| Win rate | 28.96% |
| Profit factor | 0.48 |
| Gross profit | $195.66 |
| Gross loss | -$410.61 |
| Realized P/L | **-$214.95** |
| Closed-balance max drawdown | $219.89 / 11.57% |
| Open positions at extraction | 0 |

The OCO magic number 864011 produced 889 of the 891 trades. Buys lost $136.77 and sells lost $78.08. Average duration was 20.6 seconds (median 9 seconds); 856 trades closed within one minute. There were 423 re-entries within five seconds and a maximum 18-loss streak.

## Root causes

1. **Invalid validation model.** The former “PF 4+” audit used MT5 `Model=0`, where intra-minute ticks are generated from M1 bars. A strategy with a median nine-second holding time can exploit the synthetic tick path without having the same edge on live ticks.
2. **Runaway re-entry.** The old build re-armed roughly five seconds after a close and had no daily trade limit, cooldown or loss guard.
3. **Non-atomic OCO.** Two independent pending orders were sent to the broker. The sibling was cancelled only after the first fill was reported, leaving a race window in a fast move.
4. **Execution mismatch.** The terminal logs show roughly 190–240 ms order/cancel round trips, hundreds of pending-order deletion/invalid-request events and repeated invalid-stop modifications. This is poor terrain for pseudo-HFT.
5. **The edge itself was weak.** Actual wins averaged about $0.76 and losses about $0.65, requiring a 46.15% breakeven win rate before further slippage. The live win rate was only about 29%.

## Live Guard v1.20 changes

- Replaced the two broker pending orders with one virtual OCO; only the first crossed side can send a market order.
- Uses the completed previous M1 high/low rather than repeatedly straddling the current quote.
- Requires previous-bar range >= 0.5 ATR and tick volume >= its 20-bar average.
- Maximum spread reduced from $0.50 to $0.25.
- 60-second cooldown after a win and 300 seconds after a loss.
- Maximum 12 trades per server day.
- Stops placing entries when daily realized P/L reaches -$3 at the fixed 0.01 lot.
- Adds a $0.10 broker stop/freeze safety buffer and a $0.10 minimum trailing-step change.
- The official package backtest runner now uses MT5 `Model=4` (Every tick based on real ticks).

The EA compiled with 0 errors and 0 warnings.

## Honest real-tick validation

| Test | History quality | Net | PF | Win rate | Max equity DD | Trades | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| 2026-06-01 to 2026-07-31 | 100% real ticks | -$33.89 | 0.82 | 36.20% | 0.43% | 453 | Valid, negative |
| July 2026 | 100% real ticks | -$9.37 | 0.90 | 39.32% | 0.29% | 234 | Valid, negative |
| August 2026 | n/a | +$317.78 | 6.64 | 65.83% | 0.03% | 240 | Rejected: not real-tick quality |
| 2025-08-01 to 2026-07-31 | 57% | +$743.53 | 1.75 | 45.22% | 0.77% | 2,793 | Rejected: mixed tick quality |

Amounts use a $10,000 report deposit but fixed 0.01 lot, so percentage return is not a useful comparison to the $50 experiment. Spread, commission and execution mode are included by the Exness tester.

## Broker conclusion

Do not change broker expecting that alone to fix this EA. A Raw/Zero account, stable VPS close to the trade server and lower latency can reduce spread and cancellation races, but the latest 100%-real-tick PF is only 0.82. First require at least four weeks of positive demo forward trading with zero duplicate fills, then compare the same build on Exness Raw/Zero and one other broker using identical fixed-lot settings.

## Files

- Updated source: `EA\XAU M1 OCO Core.mqh`
- Compiled EA: `EA\XAU M1 Current Price OCO EA.ex5`
- Live-guard set: `Settings\LAST INSTALLED - XAUUSD M1 - Current Price OCO.set`
- Installer: `INSTALL AND RUN HIGH FREQUENCY EA.bat`
- Real-tick runner: `RUN VERIFIED XAU BACKTEST.bat`
- MT5 reports: `Backtest Reports`

