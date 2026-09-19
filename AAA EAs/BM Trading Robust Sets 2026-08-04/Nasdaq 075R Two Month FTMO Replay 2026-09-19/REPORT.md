# Nasdaq 5M Candle Momentum — 0.75R, 1% risk, latest two months

## Result

**Not passed within the window. No modeled daily or total loss-limit breach. Still in Phase 1.**

The $10,000 simulated account finished at **$9,715.48**, a loss of **$284.52 (-2.85%)**.
It never reached the $11,000 Phase 1 target, so Verification did not start.
This is one chronological historical test, not a probability estimate or a prediction.

Requested window: **19 July 2026 through 18 September 2026**, with the native tester end exclusive at 19 September.
The first trading day was 20 July. No optimization or parameter selection was performed.

## Frozen strategy and sizing

- Same saved Nasdaq 5M development 0.75R configuration discussed in the conversation.
- One entry opportunity per New York trading day after the 09:30–09:35 candle closes.
- Direction: completed M5 candle close above/below EMA12; both directions enabled.
- Initial SL: 4 x ATR14. Fixed TP: 0.75 x initial stop distance.
- No ATR trailing, breakeven, dynamic trailing or adaptive risk reduction.
- Close any remaining position at 15:55 New York.
- Target price-to-stop risk: 1% of current equity, not a fixed $100 forever.
- The saved executable rounds lots down: actual initial price risk ranged from 0.9787% to 0.9999% before fees and stop slippage.
- Native test used Exness-MT5Trial16 USTEC and the existing isolated research executable, not the connected FTMO account.

## Monthly breakdown

| Period | Trades | Wins / losses | Net USD | Ending balance |
|---|---:|---:|---:|---:|
| 20–31 July 2026 | 10 | 5 / 5 | -$131.81 | $9,868.19 |
| August 2026 | 21 | 12 / 9 | -$127.99 | $9,740.20 |
| 1–18 September 2026 | 14 | 7 / 7 | -$24.72 | $9,715.48 |
| **Total** | **45** | **24 / 21** | **-$284.52** | **$9,715.48** |

Win rate: **53.33%**. Net-trade profit factor: **0.85**.
Longest winning streak: **7**. Longest losing streak: **4**.
Recorded commission: **-$22.21**, already included in net P/L. Recorded swap: **$0.00**.
All 45 positions opened and closed within the same Prague calendar day; maximum holding time was 380 minutes.

## FTMO 2-Step comparison

Rules checked on 19 September 2026 against [FTMO's official objectives](https://ftmo.com/en/trading-objectives/).

| Objective / limit on $10K | Observed | Outcome |
|---|---:|---|
| Phase 1: $1,000 profit, all positions closed | Final P/L -$284.52; highest balance $10,000 | Not reached |
| Verification: $500 profit on reset account | Phase 2 never started | Not reached |
| Minimum four entry days per evaluation phase | 45 distinct entry days in Phase 1 | Met for Phase 1 |
| Daily loss <= $500, including floating P/L and fees, reset at Prague midnight | Independent tick-path replay worst loss $101.21 (1.01% of initial capital) | No modeled breach |
| Static total equity floor $9,000 | Native minimum equity $9,447.76 | No native breach |

Native peak-to-trough maximum equity drawdown was **$582.73 (5.81%)** over the whole window.
That is not a 5.81% daily loss and is not, by itself, an FTMO daily-loss breach.
There is no automatic failure merely because two months elapsed without passing.

## Evidence quality and limits

1. This is a newly completed **native MT5 test**, Model 4 (real-tick mode), using the exact saved 0.75R parameters.
   It is **not an FTMO-feed backtest**. The FTMO MCP connection failed to initialize; the separate Exness research terminal successfully synchronized historical data.
2. During initial synchronization MT5 reported missing real ticks in 2,772 of 61,814 minute bars, including the whole days 14 and 15 September. MT5 used generated fallback ticks.
   A subsequent refresh added 97,035 ticks and the confirmation run processed 37,389,370 ticks.
   Its final balance changed by $0.75 from the initial $9,714.73 to $9,715.48; the conclusion did not change.
   **Final 100% real-tick coverage has not been independently certified**, regardless of the report's 100% history-quality label.
3. Recorded historical bid/ask spreads, native fill-price gaps, commission and swap are included.
   Added execution delay was zero. No additional latency/slippage stress was run.
4. Tester account leverage was set to 1:30, but the Exness instrument still uses Exness margin specifications.
   This does not reproduce FTMO Swing's exact symbol-specific margin rules.
   A separate simple notional/15 sensitivity peaked at 31.98% of the then-current balance; that is only a sensitivity, not a verified FTMO margin calculation.
5. The no-trading equity auditor replayed all 45 saved fills over tester ticks and reconciled the ending balance exactly.
   It found zero daily and total breaches. Its minimum equity was $9,437.86, $9.90 lower than the native report, with both comfortably above $9,000.
   Saved report fill timestamps have only second precision; this reconstruction is not identical to an account's millisecond-level execution/equity record.
   The native report remains the source for the quoted whole-run drawdown.

## Saved evidence

- `native/calyx-nasdaq075-confirm-20260919.htm`: confirmation MT5 report, inputs, orders and deals.
- `native/calyx-nasdaq075-recent-20260919.htm`: first run, retained for comparison.
- `native/tester-journal.txt`: tester diagnostics, including data-quality warnings and the equity-audit result.
- `summary.json`, `months.json`, `trades.json`: reconciled statistics and per-trade costs, stops, targets and risk.
- `ftmo-rule-audit.json`, `equity-audit-days.csv`: rule checks and daily floating-equity reconstruction.
- `analyze.py`: reproducible reconciliation and assertions.
- `Equity Path Audit.mq5`: research-only auditor; cannot run outside the tester and never sends an order.

No active EA, BAT, website or portfolio setting was changed. No live trades were placed.
