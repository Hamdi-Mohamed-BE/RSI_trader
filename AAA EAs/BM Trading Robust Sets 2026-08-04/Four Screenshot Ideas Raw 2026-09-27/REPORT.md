# Four screenshot strategies — raw last-year results

Completed September 27, 2026. Research only. No strategy optimization, portfolio changes, FTMO simulation, production EA/BAT/website edits or Git push.

## Interpretation and sizing

- Test period: September 27, 2025 through September 27, 2026 exclusive. Separate $10,000 USD accounts; Exness isolated native MT5 tester, Model 4, 150ms simulated execution delay, original bid/ask prices, commission and swaps.
- USDJPY morning breakout and US100 ORB target 1% CURRENT equity per stop, lots rounded UP using the established raw-study helper. This is not a hard loss cap; costs, gaps and rounding can exceed 1%.
- US30 Turnaround Tuesday and US100 daily long have NO STOP LOSS, as in the screenshots. Both use fixed initial $10,000 notional market exposure, lots rounded down (approximately 1x initial capital). Their returns/DD cannot be compared as if all four have the same risk budget. A much larger position would change their account risk materially.
- All broker-time rules use a synthetic GMT+2/+3 clock, defined as New York +7 hours with US DST, because Exness history is UTC. The source broker and its exact DST convention are unknown. The ORB uses New York time directly.
- Win rate, PF and streaks below use net completed-trade results AFTER commission/swap. Drawdown is native maximum relative floating-equity DD, not the closed-balance curve. Trades/day uses all 260 weekdays, including no-trade days; monthly frequency uses elapsed calendar time.
- Exactly four raw definitions, four predeclared controls and four short smoke runs. No parameters were searched. One year is descriptive and does not establish the 3y/5y pipeline gate, robustness, FTMO compliance or payout probability.

**Broker-constrained reproduction, not exact source-broker parity:** market-closed responses delayed 93 daily-long US100 exits, 13 US100 ORB exits and five filtered US30 exits in this run. Some are holidays; winter timing also depends on the native tester session specification. These realized native paths are retained, but the intended-clock versions require source-broker session validation before their edge can be judged reliably.

## Primary strategies — side by side

| Strategy | Trades | /month | /weekday | Net USD | Return | Net win | Net PF | Equity DD | Balance DD | Max W/L |
|---|---|---|---|---|---|---|---|---|---|---|
| USDJPY morning range breakout | 252 | 21.0 | 0.97 | $+2,523.78 | 25.24% | 42.86% | 1.21 | 32.21% | 31.38% | 17 / 10 |
| US30 Turnaround Tuesday | 16 | 1.3 | 0.06 | $+1,117.79 | 11.18% | 81.25% | 4.22 | 3.28% | 2.05% | 11 / 2 |
| US100 daily long | 258 | 21.5 | 0.99 | $+1,152.87 | 11.53% | 53.10% | 1.10 | 13.63% | 12.79% | 11 / 6 |
| US100 New York ORB | 256 | 21.3 | 0.98 | $-990.23 | -9.90% | 47.27% | 0.91 | 25.94% | 24.89% | 9 / 6 |

## Reading the result

- USDJPY has a positive annual net result, but $+2,501.45 of its $+2,523.78 profit came from the final partial September. It lost money in each of January–June. That concentration plus 32.21% equity DD makes the headline return misleading if viewed alone.
- US30 has the strongest raw win-rate/PF figures, but only 16 trades, with 11 consecutive wins. March contributed $866.41 of the $1,117.79 annual net profit. No stop and limited sample size mean this is a research lead, not a validated low-risk strategy.
- US100 daily long has a modest net PF and substantial scheduled-exit uncertainty. Its buy-and-hold control returned more with higher equity DD; that comparison has different overnight exposure.
- The requested US100 ORB lost money and underperformed its predeclared timed-entry control this year. Do not promote or optimize it solely to rescue this sample.

## What was actually tested

1. **USDJPY morning breakout:** 03:00–06:00 broker-time range; at 06:00 pending stops at high/low; SL opposite edge, no TP; first fill cancels the other order; close/cancel 18:00; one trade/day.
2. **US30 Turnaround Tuesday:** Monday 01:05 broker-time buy if current bid is below the mean of 25 completed synthetic broker-day closes; no SL/TP; Tuesday 23:50 exit.
3. **US100 daily long:** every broker weekday 01:05 buy; no SL/TP/filter; 23:50 exit.
4. **US100 NY ORB:** 09:30–09:45 range; completed M5 close outside it, entries 09:50–15:00; stop opposite edge plus 0.25 ATR(14,M5); target TWO RANGE HEIGHTS from the breakout boundary, not 2R from entry; one trade/day; close 15:55.

Broker-invalid orders are skipped rather than changing entry/stop/target levels. A scheduled close cannot execute during a closed market; the code retries on the next available minute. Late closures are retained below, not erased or moved earlier.

## Streaks, trade sizes and realized trade distribution

| Strategy | Avg winning streak | Avg losing streak | Avg win USD | Avg loss USD | Best trade | Worst trade | Largest initial SL risk | Notional range (no-stop) |
|---|---|---|---|---|---|---|---|---|
| USDJPY morning range breakout | 1.86 | 2.53 | 136.79 | -85.06 | 1,006.89 | -122.58 | 1.078% | Stop-sized |
| US30 Turnaround Tuesday | 4.33 | 1.50 | 112.69 | -115.74 | 320.35 | -206.21 | Undefined: no SL | 9,592.02–9,997.66 |
| US100 daily long | 2.17 | 1.95 | 92.53 | -95.23 | 360.44 | -507.36 | Undefined: no SL | 9,701.18–10,000.06 |
| US100 New York ORB | 1.92 | 2.11 | 86.30 | -84.69 | 216.23 | -253.66 | 1.066% | Stop-sized |

## Monthly closed-trade USD and counts

Each cell is net USD / number of trades closed. September 2025 and September 2026 are partial months. This is attribution of full trade P&L to its closing month, not a broker cash statement or monthly equity/payout series. Entry fees on trades spanning months are attributed with their eventual close.

| Month | USDJPY morning | US30 Tuesday | US100 daily | US100 ORB |
|---|---|---|---|---|
| 2025-09 | $+340.23 / 2 | $+0.00 / 0 | $+40.26 / 2 | $-201.60 / 2 |
| 2025-10 | $-265.41 / 23 | $+85.46 / 1 | $+103.64 / 23 | $+186.54 / 23 |
| 2025-11 | $+826.24 / 20 | $-63.38 / 2 | $-219.40 / 20 | $-386.58 / 19 |
| 2025-12 | $+599.33 / 20 | $+0.00 / 0 | $-36.84 / 21 | $+50.48 / 22 |
| 2026-01 | $-416.20 / 21 | $+31.51 / 1 | $+118.22 / 21 | $+324.39 / 20 |
| 2026-02 | $-265.76 / 20 | $+97.23 / 1 | $-424.76 / 20 | $+1,071.87 / 20 |
| 2026-03 | $-162.58 / 22 | $+866.41 / 5 | $-266.67 / 23 | $-345.41 / 23 |
| 2026-04 | $-836.75 / 22 | $+88.15 / 1 | $+1,457.39 / 22 | $-24.91 / 21 |
| 2026-05 | $-888.86 / 20 | $+0.00 / 0 | $+766.98 / 21 | $-170.74 / 21 |
| 2026-06 | $-614.36 / 21 | $+0.00 / 0 | $-207.94 / 22 | $-942.82 / 22 |
| 2026-07 | $+916.34 / 22 | $+122.31 / 2 | $-804.62 / 23 | $-406.82 / 23 |
| 2026-08 | $+790.11 / 20 | $+0.00 / 0 | $+172.41 / 21 | $-309.81 / 21 |
| 2026-09 | $+2,501.45 / 19 | $-109.90 / 3 | $+454.20 / 19 | $+165.18 / 19 |

## Monthly closed-balance returns

Return is attributed closed-trade P&L divided by the prior attributed closed balance; no withdrawals. Not a floating-equity monthly return.

| Month | USDJPY morning | US30 Tuesday | US100 daily | US100 ORB |
|---|---|---|---|---|
| 2025-09 | 3.40% | 0.00% | 0.40% | -2.02% |
| 2025-10 | -2.57% | 0.85% | 1.03% | 1.90% |
| 2025-11 | 8.20% | -0.63% | -2.16% | -3.87% |
| 2025-12 | 5.50% | 0.00% | -0.37% | 0.53% |
| 2026-01 | -3.62% | 0.31% | 1.20% | 3.36% |
| 2026-02 | -2.40% | 0.97% | -4.25% | 10.75% |
| 2026-03 | -1.50% | 8.54% | -2.78% | -3.13% |
| 2026-04 | -7.85% | 0.80% | 15.65% | -0.23% |
| 2026-05 | -9.05% | 0.00% | 7.12% | -1.60% |
| 2026-06 | -6.88% | 0.00% | -1.80% | -8.98% |
| 2026-07 | 11.02% | 1.10% | -7.10% | -4.25% |
| 2026-08 | 8.56% | 0.00% | 1.64% | -3.38% |
| 2026-09 | 24.96% | -0.98% | 4.25% | 1.87% |

## Predeclared controls

These are context comparisons, not optimized alternatives or proof of a causal edge. The buy-and-hold control has one trade, full-year overnight exposure and swaps; its win rate/PF are not statistical evidence. Alternating-direction controls can have different valid geometry and participation from breakout entries.

| Control | Trades | Net USD | Return | Net win | Net PF | Equity DD | Max W/L |
|---|---|---|---|---|---|---|---|
| USDJPY timed alternating control | 257 | $-876.72 | -8.77% | 27.63% | 0.95 | 55.11% | 8 / 15 |
| US30 unfiltered Monday control | 52 | $+1,688.94 | 16.89% | 61.54% | 2.20 | 3.73% | 9 / 3 |
| US100 buy-and-hold control | 1 | $+1,451.08 | 14.51% | 100.00% | n/a | 17.09% | 1 / 0 |
| US100 timed alternating control | 227 | $+1,670.33 | 16.70% | 33.92% | 1.10 | 19.69% | 3 / 12 |

## Costs, coverage and execution limitations

Spread is already in bid/ask entry/exit prices, so it is not subtracted again as a separate fee. Delay-induced slippage is simulated, not an empirical reconstruction of live fills. Broker historical contract/session/commission/swap schedules have NOT been independently reconstructed. In particular, winter scheduled exits can meet market-closed responses under the tester's available broker session specification. This is broker/tester-dependent evidence, not exact parity with the source broker.

| Strategy | Commission USD | Swap USD | Native coverage | Late scheduled exits | Max holding hours |
|---|---|---|---|---|---|
| USDJPY morning range breakout | -375.30 | 0.00 | 73% real ticks | 0 | 12.0 |
| US30 Turnaround Tuesday | -2.04 | -34.41 | 73% real ticks | 5 | 47.9 |
| US100 daily long | -59.44 | -702.79 | 73% real ticks | 93 | 71.9 |
| US100 New York ORB | -112.15 | -132.90 | 73% real ticks | 13 | 56.2 |
| USDJPY timed alternating control | -1,219.70 | 0.00 | 73% real ticks | 0 | 12.0 |
| US30 unfiltered Monday control | -6.52 | -109.33 | 73% real ticks | 18 | 47.9 |
| US100 buy-and-hold control | -0.25 | -1,004.09 | 73% real ticks | 0 | 8,686.9 |
| US100 timed alternating control | -448.24 | -120.77 | 73% real ticks | 9 | 56.2 |

Real ticks begin January 1, 2026 in these native journals. Earlier missing history is generated/mixed. Requesting Model 4 does not mean 100% real ticks. No out-of-sample claim is made.

The maximum initial SL risk is fill-to-original-stop before commission and swap, converted to USD. No-stop sizing has unlimited downside up to account/margin constraints; historical DD is not a future bound.

### Late scheduled exits — primary strategies

| Strategy | Entry UTC | Exit UTC | Intended exit (strategy local clock) |
|---|---|---|---|
| US30 Turnaround Tuesday | 2025-11-16T23:05:00 | 2025-11-18T23:00:00 | 2025-11-18 23:50:00 |
| US30 Turnaround Tuesday | 2025-11-23T23:05:00 | 2025-11-25T23:00:00 | 2025-11-25 23:50:00 |
| US30 Turnaround Tuesday | 2026-01-25T23:05:00 | 2026-01-27T23:00:02 | 2026-01-27 23:50:00 |
| US30 Turnaround Tuesday | 2026-02-01T23:05:00 | 2026-02-03T23:00:01 | 2026-02-03 23:50:00 |
| US30 Turnaround Tuesday | 2026-03-01T23:05:00 | 2026-03-03T23:00:00 | 2026-03-03 23:50:00 |
| US100 daily long | 2025-11-02T23:05:00 | 2025-11-03T23:00:00 | 2025-11-03 23:50:00 |
| US100 daily long | 2025-11-03T23:05:00 | 2025-11-04T23:00:00 | 2025-11-04 23:50:00 |
| US100 daily long | 2025-11-04T23:05:00 | 2025-11-05T23:00:00 | 2025-11-05 23:50:00 |
| US100 daily long | 2025-11-05T23:05:00 | 2025-11-06T23:00:00 | 2025-11-06 23:50:00 |
| US100 daily long | 2025-11-06T23:05:00 | 2025-11-09T23:00:00 | 2025-11-07 23:50:00 |
| US100 daily long | 2025-11-09T23:05:00 | 2025-11-10T23:00:00 | 2025-11-10 23:50:00 |
| US100 daily long | 2025-11-10T23:05:00 | 2025-11-11T23:00:00 | 2025-11-11 23:50:00 |
| US100 daily long | 2025-11-11T23:05:00 | 2025-11-12T23:00:00 | 2025-11-12 23:50:00 |
| US100 daily long | 2025-11-12T23:05:00 | 2025-11-13T23:00:00 | 2025-11-13 23:50:00 |
| US100 daily long | 2025-11-13T23:05:00 | 2025-11-16T23:00:00 | 2025-11-14 23:50:00 |
| US100 daily long | 2025-11-16T23:05:00 | 2025-11-17T23:00:00 | 2025-11-17 23:50:00 |
| US100 daily long | 2025-11-17T23:05:00 | 2025-11-18T23:00:00 | 2025-11-18 23:50:00 |
| US100 daily long | 2025-11-18T23:05:00 | 2025-11-19T23:00:00 | 2025-11-19 23:50:00 |
| US100 daily long | 2025-11-19T23:05:00 | 2025-11-20T23:00:00 | 2025-11-20 23:50:00 |
| US100 daily long | 2025-11-20T23:05:00 | 2025-11-23T23:00:00 | 2025-11-21 23:50:00 |
| US100 daily long | 2025-11-23T23:05:00 | 2025-11-24T23:00:00 | 2025-11-24 23:50:00 |
| US100 daily long | 2025-11-24T23:05:00 | 2025-11-25T23:00:00 | 2025-11-25 23:50:00 |
| US100 daily long | 2025-11-25T23:05:00 | 2025-11-26T23:00:00 | 2025-11-26 23:50:00 |
| US100 daily long | 2025-11-26T23:05:00 | 2025-11-27T23:00:00 | 2025-11-27 23:50:00 |
| US100 daily long | 2025-11-27T23:05:00 | 2025-11-30T23:00:00 | 2025-11-28 23:50:00 |
| US100 daily long | 2025-11-30T23:05:00 | 2025-12-01T23:00:00 | 2025-12-01 23:50:00 |
| US100 daily long | 2025-12-01T23:05:00 | 2025-12-02T23:00:00 | 2025-12-02 23:50:00 |
| US100 daily long | 2025-12-02T23:05:00 | 2025-12-03T23:00:00 | 2025-12-03 23:50:00 |
| US100 daily long | 2025-12-03T23:05:00 | 2025-12-04T23:00:00 | 2025-12-04 23:50:00 |
| US100 daily long | 2025-12-04T23:05:00 | 2025-12-07T23:00:00 | 2025-12-05 23:50:00 |
| US100 daily long | 2025-12-07T23:05:00 | 2025-12-08T23:00:00 | 2025-12-08 23:50:00 |
| US100 daily long | 2025-12-08T23:05:00 | 2025-12-09T23:00:00 | 2025-12-09 23:50:00 |
| US100 daily long | 2025-12-09T23:05:00 | 2025-12-10T23:00:00 | 2025-12-10 23:50:00 |
| US100 daily long | 2025-12-10T23:05:00 | 2025-12-11T23:00:00 | 2025-12-11 23:50:00 |
| US100 daily long | 2025-12-11T23:05:00 | 2025-12-14T23:00:00 | 2025-12-12 23:50:00 |
| US100 daily long | 2025-12-14T23:05:00 | 2025-12-15T23:00:00 | 2025-12-15 23:50:00 |
| US100 daily long | 2025-12-15T23:05:00 | 2025-12-16T23:00:00 | 2025-12-16 23:50:00 |
| US100 daily long | 2025-12-16T23:05:00 | 2025-12-17T23:00:00 | 2025-12-17 23:50:00 |
| US100 daily long | 2025-12-17T23:05:00 | 2025-12-18T23:00:00 | 2025-12-18 23:50:00 |
| US100 daily long | 2025-12-18T23:05:00 | 2025-12-21T23:00:00 | 2025-12-19 23:50:00 |
| US100 daily long | 2025-12-21T23:05:00 | 2025-12-22T23:00:00 | 2025-12-22 23:50:00 |
| US100 daily long | 2025-12-22T23:05:00 | 2025-12-23T23:00:00 | 2025-12-23 23:50:00 |
| US100 daily long | 2025-12-23T23:05:00 | 2025-12-25T23:00:00 | 2025-12-24 23:50:00 |
| US100 daily long | 2025-12-25T23:05:00 | 2025-12-28T23:00:00 | 2025-12-26 23:50:00 |
| US100 daily long | 2025-12-28T23:05:00 | 2025-12-29T23:00:00 | 2025-12-29 23:50:00 |
| US100 daily long | 2025-12-29T23:05:00 | 2025-12-30T23:00:00 | 2025-12-30 23:50:00 |
| US100 daily long | 2025-12-30T23:05:00 | 2026-01-01T23:00:02 | 2025-12-31 23:50:00 |
| US100 daily long | 2026-01-01T23:05:00 | 2026-01-04T23:00:02 | 2026-01-02 23:50:00 |
| US100 daily long | 2026-01-04T23:05:00 | 2026-01-05T23:00:01 | 2026-01-05 23:50:00 |
| US100 daily long | 2026-01-05T23:05:00 | 2026-01-06T23:00:01 | 2026-01-06 23:50:00 |
| US100 daily long | 2026-01-06T23:05:00 | 2026-01-07T23:00:03 | 2026-01-07 23:50:00 |
| US100 daily long | 2026-01-07T23:05:00 | 2026-01-08T23:00:01 | 2026-01-08 23:50:00 |
| US100 daily long | 2026-01-08T23:05:00 | 2026-01-11T23:00:02 | 2026-01-09 23:50:00 |
| US100 daily long | 2026-01-11T23:05:00 | 2026-01-12T23:00:01 | 2026-01-12 23:50:00 |
| US100 daily long | 2026-01-12T23:05:00 | 2026-01-13T23:00:02 | 2026-01-13 23:50:00 |
| US100 daily long | 2026-01-13T23:05:00 | 2026-01-14T23:00:02 | 2026-01-14 23:50:00 |
| US100 daily long | 2026-01-14T23:05:00 | 2026-01-15T23:00:02 | 2026-01-15 23:50:00 |
| US100 daily long | 2026-01-15T23:05:00 | 2026-01-18T23:00:10 | 2026-01-16 23:50:00 |
| US100 daily long | 2026-01-18T23:05:00 | 2026-01-19T23:00:02 | 2026-01-19 23:50:00 |
| US100 daily long | 2026-01-19T23:05:00 | 2026-01-20T23:00:03 | 2026-01-20 23:50:00 |
| US100 daily long | 2026-01-20T23:05:00 | 2026-01-21T23:00:01 | 2026-01-21 23:50:00 |
| US100 daily long | 2026-01-21T23:05:00 | 2026-01-22T23:00:05 | 2026-01-22 23:50:00 |
| US100 daily long | 2026-01-22T23:05:00 | 2026-01-25T23:00:01 | 2026-01-23 23:50:00 |
| US100 daily long | 2026-01-25T23:05:00 | 2026-01-26T23:00:02 | 2026-01-26 23:50:00 |
| US100 daily long | 2026-01-26T23:05:00 | 2026-01-27T23:00:02 | 2026-01-27 23:50:00 |
| US100 daily long | 2026-01-27T23:05:00 | 2026-01-28T23:00:02 | 2026-01-28 23:50:00 |
| US100 daily long | 2026-01-28T23:05:00 | 2026-01-29T23:00:01 | 2026-01-29 23:50:00 |
| US100 daily long | 2026-01-29T23:05:00 | 2026-02-01T23:00:03 | 2026-01-30 23:50:00 |
| US100 daily long | 2026-02-01T23:05:00 | 2026-02-02T23:00:02 | 2026-02-02 23:50:00 |
| US100 daily long | 2026-02-02T23:05:00 | 2026-02-03T23:00:01 | 2026-02-03 23:50:00 |
| US100 daily long | 2026-02-03T23:05:00 | 2026-02-04T23:00:01 | 2026-02-04 23:50:00 |
| US100 daily long | 2026-02-04T23:05:00 | 2026-02-05T23:00:01 | 2026-02-05 23:50:00 |
| US100 daily long | 2026-02-05T23:05:00 | 2026-02-08T23:00:02 | 2026-02-06 23:50:00 |
| US100 daily long | 2026-02-08T23:05:00 | 2026-02-09T23:00:01 | 2026-02-09 23:50:00 |
| US100 daily long | 2026-02-09T23:05:00 | 2026-02-10T23:00:05 | 2026-02-10 23:50:00 |
| US100 daily long | 2026-02-10T23:05:00 | 2026-02-11T23:00:01 | 2026-02-11 23:50:00 |
| US100 daily long | 2026-02-11T23:05:00 | 2026-02-12T23:00:01 | 2026-02-12 23:50:00 |
| US100 daily long | 2026-02-12T23:05:00 | 2026-02-15T23:00:01 | 2026-02-13 23:50:00 |
| US100 daily long | 2026-02-15T23:05:00 | 2026-02-16T23:00:02 | 2026-02-16 23:50:00 |
| US100 daily long | 2026-02-16T23:05:02 | 2026-02-17T23:00:01 | 2026-02-17 23:50:00 |
| US100 daily long | 2026-02-17T23:05:00 | 2026-02-18T23:00:02 | 2026-02-18 23:50:00 |
| US100 daily long | 2026-02-18T23:05:00 | 2026-02-19T23:00:01 | 2026-02-19 23:50:00 |
| US100 daily long | 2026-02-19T23:05:00 | 2026-02-22T23:00:01 | 2026-02-20 23:50:00 |
| US100 daily long | 2026-02-22T23:05:00 | 2026-02-23T23:00:00 | 2026-02-23 23:50:00 |
| US100 daily long | 2026-02-23T23:05:00 | 2026-02-24T23:00:00 | 2026-02-24 23:50:00 |
| US100 daily long | 2026-02-24T23:05:00 | 2026-02-25T23:00:01 | 2026-02-25 23:50:00 |
| US100 daily long | 2026-02-25T23:05:00 | 2026-02-26T23:00:01 | 2026-02-26 23:50:00 |
| US100 daily long | 2026-02-26T23:05:00 | 2026-03-01T23:00:01 | 2026-02-27 23:50:00 |
| US100 daily long | 2026-03-01T23:05:00 | 2026-03-02T23:00:02 | 2026-03-02 23:50:00 |
| US100 daily long | 2026-03-02T23:05:00 | 2026-03-03T23:00:00 | 2026-03-03 23:50:00 |
| US100 daily long | 2026-03-03T23:05:00 | 2026-03-04T23:00:02 | 2026-03-04 23:50:00 |
| US100 daily long | 2026-03-04T23:05:00 | 2026-03-05T23:00:03 | 2026-03-05 23:50:00 |
| US100 daily long | 2026-03-05T23:05:00 | 2026-03-08T22:00:02 | 2026-03-06 23:50:00 |
| US100 daily long | 2026-04-02T22:05:00 | 2026-04-05T22:00:02 | 2026-04-03 23:50:00 |
| US100 daily long | 2026-05-24T22:05:00 | 2026-05-25T22:00:00 | 2026-05-25 23:50:00 |
| US100 daily long | 2026-06-18T22:05:00 | 2026-06-21T22:00:01 | 2026-06-19 23:50:00 |
| US100 daily long | 2026-07-02T22:05:00 | 2026-07-05T22:00:02 | 2026-07-03 23:50:00 |
| US100 daily long | 2026-09-06T22:05:01 | 2026-09-07T22:00:03 | 2026-09-07 23:50:00 |
| US100 New York ORB | 2025-11-28T16:10:00 | 2025-11-30T23:00:00 | 2025-11-28 15:55:00 |
| US100 New York ORB | 2025-12-19T15:00:00 | 2025-12-21T23:00:00 | 2025-12-19 15:55:00 |
| US100 New York ORB | 2025-12-24T15:15:00 | 2025-12-25T23:00:00 | 2025-12-24 15:55:00 |
| US100 New York ORB | 2025-12-26T15:05:00 | 2025-12-28T23:00:00 | 2025-12-26 15:55:00 |
| US100 New York ORB | 2026-01-30T15:05:00 | 2026-02-01T23:00:02 | 2026-01-30 15:55:00 |
| US100 New York ORB | 2026-02-06T14:50:00 | 2026-02-08T23:00:02 | 2026-02-06 15:55:00 |
| US100 New York ORB | 2026-02-13T15:10:00 | 2026-02-15T23:00:01 | 2026-02-13 15:55:00 |
| US100 New York ORB | 2026-02-20T15:05:00 | 2026-02-22T23:00:01 | 2026-02-20 15:55:00 |
| US100 New York ORB | 2026-02-27T14:50:00 | 2026-03-01T23:00:01 | 2026-02-27 15:55:00 |
| US100 New York ORB | 2026-03-06T15:05:00 | 2026-03-08T22:00:02 | 2026-03-06 15:55:00 |
| US100 New York ORB | 2026-06-19T14:00:00 | 2026-06-21T22:00:01 | 2026-06-19 15:55:00 |
| US100 New York ORB | 2026-07-03T14:15:00 | 2026-07-05T22:00:02 | 2026-07-03 15:55:00 |
| US100 New York ORB | 2026-09-07T15:00:00 | 2026-09-07T22:00:03 | 2026-09-07 15:55:00 |

## Verification

Clean compile: zero errors and zero warnings. Each report is checked against frozen inputs, asset, dates, build hashes and execution delay. Native cash totals reconcile to trade ledgers. Every filled entry is checked against original orders and signal logs: local clocks, one-trade/day, completed candles, 25 past SMA closes, stop/target geometry, no-stop notional, costs and exit timing. Independent checks use Python zoneinfo for clock conversion. No live trading API was called.

Full specification: RULES.md. Frozen runs: run-config.json and BUILD.json. Audits: native/*/AUDIT.json. All raw histories, monthly values and metrics: RESULTS.json. FINAL_CHECKS.json records source/screenshot hashes, independent DST-transition checks and monthly ledger reconciliation.

Technical references: [MT5 testing and real ticks](https://www.mql5.com/en/docs/runtime/testing), [time-series access](https://www.mql5.com/en/docs/series/copyrates), [account-currency profit calculation](https://www.mql5.com/en/docs/trading/ordercalcprofit).
