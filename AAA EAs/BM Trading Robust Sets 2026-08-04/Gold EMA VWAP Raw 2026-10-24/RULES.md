# Gold EMA + VWAP raw study 2026-10-24 — rules (frozen before any test)

**Owner request:** "I want to test a good strategy for EMA and VWAP combo on gold; can you find and backtest one?"
Research only. Native MT5, isolated tester `_Backtests/MT5-DMC-20260811`. Nothing installed or live.

## Sources found (descriptions only; neither Pine source could be read, so the gaps are filled by the assumptions below)
- **A. "EMA Crossover Strategy 15M"** (TradingView, built for XAUUSD on OANDA):
  - Signal: EMA 5 crosses EMA 13 on 15-minute bars.
  - Filters (all default On): VWAP (longs above, shorts below), ADX ≥ 20, EMA separation.
  - Stop at the "EMA intersection point"; take profit 2R.
  - https://www.tradingview.com/script/UEFr9IXn-EMA-Crossover-Strategy-15M/
- **B. "EMA + VWAP Strategy"** (TradingView, cryptocu84; described as designed for 5-minute charts):
  - Long when EMA 9 crosses above VWAP while EMA 9 > EMA 21 and VWAP is not flat (flat threshold 0.01%). Short is
    the mirror.
  - Stop 1.5 × ATR(14); take profit 2R; weekdays.
  - https://www.tradingview.com/script/2dvhxn9p-EMA-VWAP-Strategy

## Common rules
- **Symbol and costs:** XAUUSD on Exness-MT5Trial16. Model 4 (every tick; real ticks only from 2026-01-01), 150 ms,
  $10,000, 1:2000.
- **Sizing:** 1% of equity to the stop, rounded UP to the lot step (broker minimum if needed; Calyx standard).
- **Entry:** signals use closed bars (bar 1, with bar 2 for crosses). Entry is a market order on the first tick of the
  next bar. One position at a time; new signals are ignored while it is open.
- **Exits:** stop and take profit only. No time exit, no trailing. Positions may stay open overnight and over weekends,
  as in the sources.
- **VWAP:**
  - Price × volume = typical price (H+L+C)/3 × tick volume (MT5 has no exchange volume for this CFD).
  - Reset (anchor): on the first bar after a gap of ≥ 30 minutes between bars. That is the daily gold break, about
    17:00 New York, which approximates TradingView's "Session" anchor. The weekend gap also resets it.
  - A cross or slope is valid only if bars 1 and 2 are in the same VWAP session.
- **Indicators:** EMA on close, ATR(14) and ADX(14) on the strategy timeframe.
- **Windows:** separate native runs over the last 6 months, 1 year, 3 years and 5 years, ending 2026-10-24 (exclusive).
  The dev / validation / OOS windows inside the 5-year runs come from `data_split.py`.

## A15 — EMA 5/13 cross + VWAP filter, M15
- **Long:** EMA5 crosses above EMA13 (bar 2 EMA5 ≤ EMA13, bar 1 EMA5 > EMA13), close[1] > VWAP[1], ADX[1] ≥ 20, and
  EMA5 − EMA13 ≥ 0.10 × ATR. Short is the mirror.
- **Stop:** the price where the two EMA lines cross, interpolated linearly between bars 2 and 1.
  - If that is on the wrong side or closer than 0.25 × ATR, the stop is set to 0.25 × ATR.
  - The separation 0.10 × ATR, ADX length 14 and the 0.25 × ATR minimum are assumptions; the sources do not give them.
- **Take profit:** 2R.

## B5 — EMA 9 crosses VWAP, EMA 9/21 trend, VWAP slope, M5
- **Long:** EMA9 crosses above VWAP (bar 2 EMA9 ≤ VWAP, bar 1 EMA9 > VWAP), EMA9[1] > EMA21[1], and
  |VWAP[1] − VWAP[2]| / VWAP[2] ≥ 0.01%. Short is the mirror.
  - The slope is measured over one bar, in either direction (the source does not tie it to the trade direction).
- **Stop:** 1.5 × ATR. **Take profit:** 2R. Weekdays only (gold trades only on weekdays anyway).

## Controls (5 years)
- A15_NOVWAP: A without the VWAP filter.
- A15_NOFILT: A with no VWAP, ADX or separation filter (pure 5/13 cross).
- B5_NOSLOPE: B without the slope filter.
- RND{1,2,3}_A15 and RND{1,2,3}_B5: same signal times, stops and targets, but a coin-flip direction (seeds 1–3).

## Sensitivities (5 years, declared now; not used to pick a winner)
- TP 1.5R and 3R for both (the sources suggest testing them).
- B with ATR stop multiples of 1.0 and 2.5.
- VWAP reset at server midnight for both (the Calyx RSI VWAP convention).
- B on M15 (the source says it works on 5–15 minutes).

## Raw gate (PIPELINE.md stage 4)
- Positive and PF ≥ 1.15 on 3y and 5y, with ≥ 30 trades.
- Mean R above the random-direction control (and, for A, above the pure-cross control).
- Best day / best trade check PASS.
- A FAIL stops the study, with no optimisation. A PASS is reported and the owner is asked about stage 5 after a Bear
  review.
