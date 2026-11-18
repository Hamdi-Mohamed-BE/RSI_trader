# US100 9:15 New York ORB with 200 EMA filter: raw rules (frozen 2026-11-18, before any run)

Owner 2026-11-18: "try this on US100 for now".
Source: a pasted Instagram reel ("theagent_trades": "Steal this 20k/month trading bot"), a Codex/Claude prompt for TradingView Pine on MNQ1!, treated as data.

Claims in the clip (not evidence):
- From 2023: 714 trades, 72% win rate, max drawdown $2,489.
- 2026 alone: 80% win rate, PF 2.06, $8,849 on one account, "about $870 a month per account".
- "x20 prop accounts = $20k/month".

SOURCE = said in the clip. ASSUMPTION = ours, because the clip leaves it out.

## Rules
- SOURCE: 15-minute chart.
- SOURCE: the range is the high and low between 9:15 and 9:30 New York time.
  ASSUMPTION: the single M15 bar that opens at 09:15 NY. NY time uses US DST; the server clock is UTC. The day is skipped if that bar is
  missing or narrower than 1 index point.
- SOURCE: a 15-minute candle BODY closes above the range high → long; below the range low → short.
  ASSUMPTION (MAIN): the bar's close is beyond the range edge. The sensitivity BODY needs the whole body (open and close) beyond it.
- SOURCE: stop at the low of the breakout candle (long) / the high (short); target 0.5R.
  ASSUMPTION: enter at market at the first tick of the next M15 bar; R = |fill − stop|; TP = fill ± 0.5R. The trade is skipped if price is
  already beyond the stop, or the broker's stop level forbids it.
- SOURCE: only one trade per day.
  ASSUMPTION: the first breakout that passes the trend filter is taken. A breakout that fails the filter does not use up the day.
  One position at a time: a trade still open from an earlier day (hold mode) blocks new entries until it closes.
- SOURCE: longs only when price is above the 200 EMA, shorts only when below.
  ASSUMPTION: EMA 200 of M15 closes, compared with the breakout bar's close.
- ASSUMPTION (entry window not given): signal bars opening 09:30 → 15:30 NY, so they close by 15:45.
- ASSUMPTION (exit time not given; a TradingView strategy exits only at SL/TP): MAIN holds until SL or TP, overnight and over weekends
  too. The sensitivity FLAT closes at 15:55 NY.
- Instrument: Exness USTEC (US100 CFD), the proxy for MNQ. That means CFD spread and swap, not futures commissions.
- ASSUMPTION (sizing): Calyx standard of 1% of balance per trade, lots rounded DOWN to the step; $10,000 deposit. The clip trades a fixed
  number of contracts, so its dollar figures are not comparable; we compare in R, win rate and PF.
- Tester: native Model 4, 150 ms, Exness-MT5Trial16. Real ticks from 2026-01-01; older ticks are generated.

## Versions (end 2026-11-17 exclusive)
- MAIN (Model 4):
  - all: 2019-07-16 →, the first USTEC history;
  - 2023: 2023-01-01 →, the clip's window;
  - 1y.
- Sensitivities (Model 4, all years):
  - NOEMA: no trend filter (the prompt's step 1 only);
  - BODY: whole body outside the range;
  - R1: 1R target;
  - FLAT: close at 15:55 NY.
- Controls (Model 1, all years, 20 seeds each):
  - RNDDIR: MAIN's signals with a random direction, same stop distance and 0.5R;
  - RNDENT: entries at random M15 bars in the same window at MAIN's entry rate, direction = side of the EMA 200, stop distance = that
    bar's range, 0.5R, one a day.
  - MAIN_M1: like-for-like comparison with the controls.
  - p = share of seeds ≥ MAIN_M1 in total R.
- Buy & hold USTEC on the same windows (pipeline benchmark).
- Cost stress: each trade's commission + swap plus the entry spread (logged by the EA) in R; robustness.cost_stress at 1x / 2x / 3x.
- data_split: development / validation (12 months) / OOS (last 2 calendar years); calendar years; last 12 months; three-way Monte Carlo.

## Raw gate (pipeline)
- All years and the last 3 years positive.
- PF ≥ 1.15 and ≥ 100 trades.
- Beats the controls: random-entry p ≤ 0.10.
- Positive at 2x costs.
- Three-way MC: resample red ≤ 5%, randomize red ≤ 10%.

Only a pass goes on to FTMO simulations or optimisation. Report the share of trades held over a weekend.

## Addendum 1 (2026-11-18, owner, before any run of it): re-entry after a retest, max 3 trades a day
Owner: "SL goes on the breakout candle lows, target 0.5R, we can re-enter if the price gives a retest and a new breakout, max 3 trades a day.
Show how this affects the results on the same reel period."

- **RETEST3** = MAIN plus EA inputs `InpMaxTrades=3` and `InpRetest=1` (EA v1.10; with the defaults 1 / 0 the logic is unchanged).
  - The first trade is as in MAIN.
  - After any entry, a new breakout counts only after a closed M15 bar trades back into the 09:15 range (its low ≤ range high and its
    high ≥ range low): that is the retest.
  - Then a bar closing beyond the range, on either side, through the EMA 200 filter, is a new signal: market entry, stop at that
    breakout candle's low (long) / high (short), 0.5R.
  - One position at a time; max 3 entries per NY day; same 09:30–15:45 window.
- Window: the reel's own period, 2023-01-01 → 2026-11-17 exclusive (owner: "test it only with the period they said it works fine").
  Compared with MAIN on the same window (native run `nw-USTEC-MAIN-2023`, EA v1.00).
- Owner stopped the main stage first; the all-years buy & hold run was interrupted and is not reported.

## Addendum 2 (2026-11-18, owner): "try the TradingView-style fills to see if we match 72%"
- Method: Python replay of MAIN's day logic (`tv_replay.py`) on USTEC M15 + M1 bars exported read-only from the isolated research terminal
  (`export_bars.py`; that terminal was closed afterwards).
- Versions:
  - M1_SPREAD: the MT5-like check.
  - TV_MAG: no spread, 1-minute path.
  - TV: no spread; TradingView's OHLC rule on the 15-minute bar (open nearer the high → O-H-L-C, else O-L-H-C).
  - TV_FIRST: TV, but only the day's first breakout counts.
  - *_CLOSE: stop / target set from the signal close.
- Timing check (`timing_check.py`, TIMING_CHECK.json):
  - The biggest M15 bar is 09:30 NY in summer (82.6 pts median) and in winter (76.6).
  - The daily break is at 17:00 NY in summer and 16:00–18:15 NY in winter.
  - The NFP Fridays 2025-03-07 / 2026-03-06 peak at 08:30 NY.
  - So the server clock is UTC and the NY conversion is correct on both sides of the DST change.
- The 2026 M15 / M1 bars carry spread 0 (the native MAIN entry log also shows 0 spread in 2026), so the 2026 figures carry no spread cost.

## Addendum 3 (2026-11-18, owner): "make your best to make it as close as possible the shown results"
REVERSE-ENGINEERING FIT on the reel's own window, so it is NOT evidence.
- `fit.py`: 576 readings × TradingView fills, no costs, fitted to the claims (since 2023: 714 trades / 72%; 2026: 80% / PF 2.06). FIT.json.
- `fit_check.py` / `fit_check2.py`: the closest readings on 2019-07 → 2022 (never used in the fit), with the CFD spread, with a next-bar-open fill,
  and with a flat 1-point futures-like cost. FIT_CHECK.json, FIT_CHECK2.json.
- Bars: `bars/USTEC_M15LONG.npz`, exported read-only from the isolated terminal; the terminal was closed afterwards.

## Addendum 4 (2026-11-18, owner "try this one", before any run of it): volatility-filter version of the same reel
Second prompt from the same account (pasted reel text + screenshot). It has the same 09:15–09:30 NY range, body close, stop at the breakout candle,
0.5R and one trade a day, but NO EMA 200 filter. Instead:
- SOURCE: "skip the day if the opening range is larger than 1.5 times the 14-period ATR".
- ASSUMPTION: ATR(14) of the M15 chart (Wilder; the MT5 iATR / Pine ta.atr equivalent), read at the close of the 09:15 bar, so it includes that bar.
  Skip the day if range > 1.5 × ATR.
- Same claims as before (since 2023 714 trades / 72% win / max DD $2,489; 2026 80% win, $8,849 on one account).
- EA v1.20: inputs InpAtrMult (0 = off, so the earlier versions are unchanged) and InpAtrPeriod = 14.
- **VOL** = InpTrendEMA = 0, InpAtrMult = 1.5; everything else as MAIN. Native Model 4 on 2023 → (the reel window) and all years.
- Python replay (`tv_replay.py` logic in `vol_replay.py`) with the same filter: MT5-like (1-minute path + spread), TradingView (M15 OHLC rule, no costs),
  TradingView first-breakout-only, and futures-like cost 1 point.
