# Previous-day sweep rejection — frozen raw protocol

Frozen before results, 2026-09-28. User requested US30, US100, XAU and BTC and
explicitly requested both M5 and M15 after the timeframe clarification.

## Source versus our assumptions

Source: the user's supplied Instagram/RoboQuant transcript. Explicit signal:
take the previous day's high and close back inside -> short; take its low and
close back inside -> long. The advertised weekly income and optimized two-year
result are unverified marketing claims, not expected results. The transcript
does not supply the timeframe, stop, target, sizing, session or detailed code.
This is our disclosed raw interpretation, NOT an exact RoboQuant replication.

All rules below other than that directional signal are our assumptions.

- Run M5 and M15 separately with identical risk/exits, no tuning or selection
  between other stop/target alternatives. Four native broker symbols: US30,
  USTEC (US100), XAUUSD, BTCUSD, verified in each native journal.
- Isolated Exness CFD research history, not the active/FTMO terminal. Previous
  day means the previous available completed broker D1 candle, including a
  weekend candle when the broker supplies one. No Monday/Friday substitution.
  The retained Exness data use UTC daily boundaries. This is not NY-close FX
  data or centralized futures volume; no liquidity/stop inventory is measured.
- On a newly opened signal-timeframe bar, use only the immediately preceding
  completed bar. Its high must be strictly above PDH (or low strictly below
  PDL), and its close must be strictly INSIDE the prior day's entire range.
  Equal touches/closes do not qualify. A candle sweeping both boundaries is
  ambiguous and skipped. The sweep and rejection occur in the SAME candle;
  no separate multi-candle return variant is tested.
- Enter at the first available next-bar quote, only if it arrives less than
  60 seconds after nominal bar close, remains inside the prior day's range,
  and the signal candle opened on the current broker day. No midnight carryover
  of yesterday's signal; no historical-bar retroactive fills. There is no
  requirement that the signal candle opened inside the previous-day range.
- Long entry uses ask; short uses bid. Stop is one tick below the rejection
  candle's bid low for buys, one tick above its bid high for sells. No extra
  spread buffer. Broker-invalid or already-crossed stops/targets are skipped,
  not widened. Target is 2 times submission-quote stop distance, nearest tick.
  Native 150 ms execution delay means actual filled RR can differ.
- No trailing, breakeven, trend/news/volume/spread filters. One open position.
  Maximum one signal ATTEMPT per level per broker day (at most two fills/day).
  A first qualifying rejection is consumed even if busy, rejected or invalid;
  it is not re-entered later that day. Warmup does not trade.
- At/after 23:50 broker time close at the first tradable quote and block new
  orders; retry failed closes no more than once/minute. If there is no tradable
  late quote, carry the protective SL/TP and close at the first quote of the
  next available day. A day-end exit is therefore NOT a guaranteed no-gap rule.
- Separate $10,000 accounts per run, 1% current equity planned initial stop
  risk. Preserve existing raw sizing: round UP to broker lot step/minimum,
  capped at volume max, check free margin. Actual risk may exceed 1% due to
  minimum lots, rounding, costs, slippage/gaps; record the difference. No
  martingale, risk escalation, deposits or capital resets. Research leverage
  1:2000 is NOT an FTMO simulation or live recommendation.

## Fixed-seed directional control (ours)

Same qualifying sweep/rejection conditions and per-level/day limits, but choose
buy versus sell using a deterministic 32-bit hash of completed-bar timestamp,
level side and seed 9282026; roughly 50/50, independent of future outcomes.
Place the stop beyond the candle extreme appropriate to the CHOSEN direction,
using the same 2R target, sizing and close rules. Never select a seed on results.
This tests the reversal direction against arbitrary direction at sweep events;
it does NOT establish that previous-day levels beat non-key levels. Different
stops, holding times, invalid orders and occupancy can alter matched trade
counts, so this is an approximate directional control, not a paired causal test.

## Runs, data, and gates

- End 2026-09-27 exclusive; 6m/1y/3y/5y windows in run-config.json. Overlapping
  windows are descriptive, not out-of-sample validation. Both timeframes were
  predeclared. No parameter optimization. 4 assets x 2 TF x 2 variants x 4
  windows = 64 main tests, plus four XAU smoke tests. Run native Model 4 directly
  for every period instead of claiming an OHLC screen is tick validation.
- Real-tick mode + 150 ms delay, native broker spread/commission/swap. Retain
  journal coverage and fallback warnings; existing broker real ticks begin in
  January 2026. Earlier generated ticks are not measured historical live fills.
  Broker symbol specifications/fees may not reproduce every historical change.
  Reference: https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation
- Each real timeframe/asset must be positive, net PF >=1.15, >=30 trades, and
  beat its fixed control in net PF AND net return on BOTH 3y/5y to pass the raw
  review gate. A pass only invites review; optimization/MC/promotion need the
  next authorized pipeline stage. Failure stops this raw version.
- Preserve source/binary/config/rules hashes, exact inputs, native reports,
  journals, full position-ID deal ledgers, signal/order logs, and exported
  historical bars. Independently rebuild PD levels and sweep conditions.
- Show returns, trades/month/day, net PF, net win rate, native floating-equity
  DD versus balance DD, longest/average streaks, monthly consistency, costs,
  fills and sizing overshoot. Weekdays denominator for US30/US100/XAU; all
  calendar days for BTC. No predictive pass/payout probability inferred.

No live EAs, BATs, website, account, orders or remote deployment are changed.
