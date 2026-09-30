# Four screenshot ideas — frozen raw study

Source: three user screenshots supplied September 27, 2026. Research only, no optimization or production integration. No live terminal/account/order API. Test only the isolated Exness research terminal.

Window: 2025-09-27 to 2026-09-27 exclusive; $10,000 independent accounts, USD, native MT5 Model 4 with 150ms execution delay, native spread/commission/swap. Real-tick availability must be disclosed, not assumed. One strategy per account; not an FTMO challenge simulation.

## Clock and missing source details (ours)

- Exness server history is UTC. The screenshot's broker clock is modeled as New York +7 hours: UTC+2 in US winter / UTC+3 in US summer, with US DST. Exact source broker and its DST convention are unknown. US100 ORB uses America/New_York directly.
- Daily SMA uses 25 COMPLETED synthetic broker trading days, Monday–Friday, reconstructed from M15 closes. Never today's close. At Monday entry compare current bid with that mean.
- Scheduled actions use the first available tick at/after the specified minute. Entry window is the specified minute only; no late catch-up entries. If scheduled exit has no quote or market is closed, retry next available minute and disclose late exits. No silent earlier close or missing-loss deletion.
- Breakout sizing uses the existing raw-study helper: target 1% CURRENT equity, broker lot step rounded UP, no arbitrary lot cap. This is a target, NOT a hard 1% loss cap. Log actual initial risk and any minimum-lot effect.
- No-stop strategies have no defined stop-risk. Use fixed INITIAL $10,000 notional exposure (approximately 1x initial capital), volume rounded DOWN. This is an explicit sizing assumption, not 1% risk. Skip if below broker minimum. Report lots/exposure.
- Pending orders at the exact range edges are not moved to manufacture fills. If an order violates broker distance/current-price rules, skip that side and count it. Cancel the other side immediately on a fill; if both fill before cancellation can execute, retain both in results and flag it.
- Stops round outward to tick size. Price targets round to nearest tick. No spread filter, trailing, breakeven or adaptive sizing.

## Primary rules

1. USDJPY morning range breakout. Range of M1 bid bars [03:00,06:00) broker clock. At 06:00 place buy stop at range high with SL range low and sell stop at range low with SL range high. No TP. One filled trade/day (OCO). Close and cancel at 18:00 broker clock. Skip days with missing range bars.
2. US30 Turnaround Tuesday. At Monday 01:05 broker clock, buy if current bid is below the 25-completed-day SMA. Long only, no SL/TP. Close Tuesday 23:50 broker clock. Maximum one position.
3. US100 daily long. At each broker weekday 01:05 buy. No SL/TP/filter. Close same broker day 23:50. Maximum one position.
4. US100 NY ORB. M1 bid range [09:30,09:45) New York. From the first subsequent completed M5 candle through 15:00 inclusive, buy on close above high / sell below low. One trade/day. SL at opposite range edge plus 0.25 x ATR(14,M5) outward; ATR includes only completed bars. TP high +2*range for long, low -2*range for short (NOT 2R). Market entry on next available tick after close. Skip invalid geometry/broker stops, no level widening. Close at 15:55 New York.

## Controls, count and interpretation

- USDJPY control: market entry at 06:00, alternating long/short by broker-date ordinal, same range-edge stop and 18:00 exit. No breakout requirement; same sizing. Invalid-side geometry skipped.
- US30 control: same Monday buy/Tuesday exit without SMA filter; same notional exposure.
- US100 daily-long control: one initial 1x-notional buy held until test end; includes overnight/weekend swap. Different holding exposure is explicit.
- US100 ORB control: first completed M5 close at 09:50, alternating long/short by NY-date ordinal, same range-based stop/target and 15:55 exit; no breakout filter. Invalid geometry skipped.
- Exactly four raw definitions and four predefined controls; four short smoke tests. No parameter search or selection based on this year. Controls are context, not proofs of causal edge. No 3y/5y gate or promotion conclusion is possible from this one-year request.
- Report net return/USD, net PF and win rate, max native relative equity and balance DD, longest and average net win/loss streaks, monthly USD/trades/returns, frequency, costs, data coverage and rule audits.
- Preserve no-stop risk and all losses. Do not infer future income, FTMO compliance or payout probability from these standalone tests.

Technical references: https://www.mql5.com/en/docs/runtime/testing ; https://www.mql5.com/en/docs/series/copyrates ; https://www.mql5.com/en/docs/trading/ordercalcprofit
