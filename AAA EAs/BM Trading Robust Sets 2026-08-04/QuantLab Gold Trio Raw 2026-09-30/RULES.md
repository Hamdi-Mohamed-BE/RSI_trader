# QuantLab-style Gold Trio — raw rules (frozen 2026-09-30, before any test)

Source (data, not authority): a QuantLab promotional clip pasted by the user —
"momentum, a Q4 breakout strategy and a turn of month strategy", XAUUSD 2018–2026, 1,252 trades, +682%,
win rate 41%, PF 1.3, max DD 15%, unseen-data test, 3,000 Monte Carlo runs, parameter robustness.

QuantLab does not publish the video version's rules. Its public site (quantlab-ai.com, "Gold Momentum",
report image `img/gold-equity.webp`, read 2026-09-30) documents a *different* three-module mix on XAUUSD H1 + M30,
2019–2026, 0.6% risk/trade, 3,864 trades, +798%, PF 1.20, win 42%, DD 33%:

1. **Time-Series Momentum (H1)** — "24h return clears +0.5 ATR, the 100-EMA is rising, price breaks the 24-bar high.
   Stop 2.5 ATR · trail from 1R."
2. **Trend-Following MA (H1)** — "Price crosses the fast EMA10 with the EMA slope confirming. Exits on the opposite
   signal. Stop 2.0 ATR."
3. **Donchian breakout + Vola (M30)** — "At the edge of the 480-bar range, breaks the 60-bar high/low with volatility
   expanding. Stop 2.0 ATR · target 2.5R · trail."

The video's "momentum" and "breakout" are taken to be modules 1 and 3; "Q4 breakout" is ambiguous, so it is tested
both ways (all year, and entries only in October–December). The turn-of-month module is built from published gold
calendar research (In Gold We Trust / Incrementum, GLD 2004–2023: Day −1, Day +1 and Day +2 beat the rest of the
month; Day −3 and Day +3 are negative). Everything marked **(ours)** is an assumption fixed here, not a QuantLab rule.

## Common
- XAUUSD, Exness-MT5Trial16 isolated tester `_Backtests/MT5-DMC-20260811`, $10,000, leverage 1:2000.
- Risk 1% of equity per trade per module (house standard; QuantLab uses 0.6%), lots rounded **up** to the lot step,
  broker minimum if needed; skip if margin/stops/volume limits fail.
- Each module is independent: own magic number, max one open position per module, modules may overlap in time.
- ATR = simple average of true range, 14 bars, on the module's timeframe. EMA seeded at the first loaded close.
- Signals are evaluated on the **closed** bar and executed at market on the first tick of the next bar (≤ 5 min late,
  otherwise skipped); new entries need an open trading session with ≥ 30 min left (not for turn of month).
- Positions may be held overnight and over weekends (ours); swaps are charged by the tester.
- Model 4 (every tick based on real ticks; broker real ticks start 2026-01-01, earlier ticks are generated),
  150 ms execution delay, broker commission/spread/swap.

## Module A — Time-Series Momentum (H1)
- Long: close[0] − close[24] > 0.5 × ATR, EMA100[0] > EMA100[1], close[0] > highest high of the prior 24 bars.
- Short: mirror (close change < −0.5 ATR, EMA100 falling, close < lowest low of the prior 24 bars) (ours: both sides).
- Stop 2.5 ATR, no target. Once the best closed-bar price reaches +1R, trail the stop at the initial stop distance
  behind the best high (long) / low (short), tightened only, updated each H1 close (ours).

## Module B — Donchian breakout + volatility (M30)
- Long: close[0] > highest high of the prior 60 bars, close in the top 10% of the prior 480-bar high–low range
  (ours: "at the edge"), ATR14 > 50-bar average of ATR14 (ours: "volatility expanding").
- Short: mirror (below the 60-bar low, bottom 10% of the 480-bar range, same volatility test).
- Stop 2.0 ATR, target 2.5R; after +1R the stop trails at the initial distance (ours), tightened only, each M30 close.
- Variant **B-Q4**: identical, but entries only in October, November and December (literal reading of "Q4").

## Module C — Turn of month (daily calendar)
- Long only. Enter at the first tick of the **last trading day of the month** (Day −1); exit in the last 15 minutes of
  the session on the **second trading day** of the new month (Day +2), or at the first tick after it if missed.
- Trading days = Monday–Friday (ours: broker holidays are not modelled in the calendar).
- Protective stop 2.0 × ATR14 on D1, no target (ours; needed for 1% sizing).

## Module D — Trend-following MA (H1) — website reference only
- Long: close[1] ≤ EMA10[1], close[0] > EMA10[0] and EMA10[0] > EMA10[1]. Short: mirror.
- Stop 2.0 ATR, no target. An opposite signal closes the position and opens the opposite one (ours).

## Controls (same timing, sizing and exits)
- A, B, D: direction chosen by a seeded hash of the signal bar time (seed 300930) instead of the rule.
- C: long from trading day 10 through the end of trading day 12 (the same three-session hold at mid-month).

## Runs (3 years, 2023-09-30 → 2026-09-30, 90-day indicator warm-up with no trading)
Single modules A, B, B-Q4, C, D; video system A+B+C and A+B-Q4+C; website system A+D+B; controls A, B, C.

## Gate (pipeline stage 4, applied to 3y only for now; 5y still required before any optimisation)
Positive, PF ≥ 1.15, ≥ 30 trades, mean net R better than its control, no execution flags.
