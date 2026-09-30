# No-wick retest: raw multi-asset protocol

Frozen before new results, 2026-09-30. Source is the transcript supplied in this chat. No claim that the omitted details reproduce the speaker's private method. No optimization or deployment.

## Transcript rules and explicit assumptions

- Bullish candle with flat bottom in an uptrend: buy a later return to its open. Bearish candle with flat top in a downtrend: sell a later return to its open.
- Flat means open equals low (long) or high (short) within 0.1 price tick for floating-point noise. No percentage-of-range wick allowance.
- Trend (ours, fixed): last completed close and EMA50 both above EMA200 for longs; both below for shorts. Indicators use completed bars only.
- Most recent swing (ours): latest strict two-left/two-right confirmed pivot low for longs or high for shorts within 100 bars. At signal close, pivot shifts start at 3, so both confirming bars are already closed. If the latest pivot gives invalid stop geometry, skip; do not search for a more convenient older pivot.
- Place a limit at the signal candle open on the next bar's first tick. A mere bid-chart touch is not assumed to fill a buy: native bid/ask execution applies.
- Stop one trade tick beyond that swing (ours); freeze stop and 1:1 price-distance target when placing the order. No ATR buffer, breakeven, trailing, scaling, or daily equity overlays.
- One pending order or position at a time per test. A signal is considered once, at the first tick after its close. No retry on rejected placement, no reuse after stop/target.
- Pending order expires after 20 signal-timeframe durations of wall-clock time (ours: 100 minutes on M5, five hours on M15); cancel on first available tick at/after expiry. This includes non-trading hours, not 20 printed trading bars. No entry during a gap before signal recognition; no market chasing. Existing positions may hold overnight/weekends until SL/TP or end of test. No forced intraday close because the transcript does not specify one.
- Market hours, minimum stop distance, volume/margin limits and real bid/ask are enforced. No profit-driven parameter changes.

## Frozen matrix

Gold XAUUSD and BTCUSD: M5 and M15. US100 CFD USTEC: M5 (not exchange NQ futures). Seven forex majors EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD: M15.

12 asset/timeframe combinations, one raw parameter vector. Native Model 4, 150 ms delay, Exness-MT5Trial16, isolated portable tester only. $10,000 USD, 1% equity target risk; standard shared helper rounds lots UP and applies broker minimum, so actual risk can exceed 1%, especially after losses. Broker spread/commission/swap are retained; zero recorded commission does not imply every broker is commission-free. Leverage follows the existing isolated research setting (1:2000), not FTMO.

Windows end 2026-09-30 exclusive: six months from 2026-03-30; one year from 2025-09-30; three years from 2023-09-30; five years from 2021-09-30. These overlap and are NOT four independent out-of-sample tests. Recorded real-tick availability is audited per run; generated older history is explicitly labelled. Both gold/BTC timeframes are reported, not cherry-picked.

Control: same trend, candle colour, limit, pivot stop, expiry and risk but ignore the flat-wick condition. Run on 3y and 5y. This control has a different trade count/exposure; it is not a matched-random statistical proof.

Raw screen (pre-registered): positive net return and net PF >=1.15 on BOTH 3y and 5y, at least 30 trades on each, and better return than the matching control on both. Recent windows are disclosed even if the long-window screen passes. A pass means only eligible for user-reviewed further research, not a live recommendation. Failure means stop, not optimize.

72 planned native runs (48 raw +24 control), plus a separately labelled 2026-09-01..2026-09-30 smoke test. Any infrastructure retry and implementation correction is logged. Preserve the September-25 near-wick/rolling-extreme study unchanged; its results are not substituted for these tests.

Outputs: native reports, input checks, source/build hashes, net trade-ledger reconciliation, return/PF/net win rate/equity DD/balance DD, trade count/month/day, net win/loss streaks, costs, quality and rejection diagnostics. BTC daily frequency uses calendar days; other assets use weekdays.

Reference for tick-data limitations: https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation
