# TrendSpider "QLD Claude AI Scalper": raw rules (frozen 2026-11-03, before any result)

**Owner request (2026-11-03):** "test this new idea on us100, us30, smp500 and gold".

**Source:** https://share.trendspider.com/strategies/6ae347ef49cf9f000952ed50. It is published for QLD (ProShares Ultra QQQ, a 2x Nasdaq ETF).

**Claim on the page:** +127% (buy & hold +105%), 62% winning trades, reward/risk 2.23, average position +1.24%, max drawdown −12.30%. No test period or trade count is given.

## Published rules (copied, not changed)
**Settings:** long only; 30-minute bars; regular-session data; "trade by open".

**Entry ("Breakout with volume")** — all three must hold:
1. `close > RANGE(30 bars).high, 1 candle ago`: the close is above the highest high of the 30 bars before the signal bar.
2. `VOLUME ≥ VOLUME SMA(20)` by at least 75%: volume ≥ 1.75 × the 20-bar simple average, which includes the signal bar.
3. `close > open`: a bullish candle.

**Exit:**
- after 16 candles, only if PnL < 0.5%;
- after 60 candles, regardless of PnL.

**Not given:** no stop loss, no take profit, no trailing stop, no sizing.

## Translation to our Exness CFDs (declared assumptions)
| Item | Choice |
|---|---|
| Assets | USTEC (US100), US30, US500 (S&P 500), XAUUSD; M30 |
| "Regular session" | Indices: only bars opening 09:30–15:30 New York (13 bars a day, DST-aware) count. That applies to the range, volume average, signal and hold count. Gold has no regular session, so all bars are used. |
| Entry fill | First tick of the next session bar after the signal bar ("trade by open"). For indices, a signal on the 15:30 bar fills at the next day's 09:30 open. |
| Exit rule | Checked on every completed session bar from the 16th held bar on (`bars ≥ 16` and close/entry − 1 < 0.5% → exit), and at bar 60. The exit fills at the next session bar's first tick. |
| Volume | MT5 tick volume (a CFD proxy, not exchange volume) |
| Positions | One per symbol; while in a position, no new signals are evaluated (same as a single-position TrendSpider strategy) |
| Sizing | **1x notional:** position value = 100% of equity at entry, lots rounded down, skipped if below the minimum lot. QLD itself is 2x, so 2x is a sensitivity. With no stop, "risk per trade" is the price move itself. |
| Costs | Native MT5 Model 4: recorded commission and **swap** (CFD overnight financing; QLD has no swap but carries an expense ratio and leverage decay), spread in fills, 150 ms delay; $100,000 per symbol (fine lot granularity for 1x notional on gold). |

**Test window:** 2019-01-01 → 2026-11-03, end exclusive. Split from `data_split.py`:
- development 2019-01-01 → 2023-11-03;
- validation → 2024-11-03;
- OOS 2024-11-03 → 2026-11-03.

The last 6 months / 1 year / 3 years / 5 years are sliced from the same native run by entry date, each from its own starting balance. Real ticks start 2026-01; earlier ticks are generated.

## Variants (all declared now)
- **MAIN:** the rules above.
- **Controls:**
  - `RND1`, `RND2`, `RND3`: random long entries with the same exits, same session and same sizing.
  - The probability per flat session bar is set from MAIN's own 5-year signal frequency, using three seeds.
- **Sensitivities** (none of them is a selection):
  - `S_SESS`: flip the session choice (indices on all bars; gold on 09:30–16:00 New York only).
  - `S_NOVOL`: no volume filter.
  - `S_2X`: 200% notional, like QLD.

## Raw gate (PIPELINE.md stage 4)
All of these, per asset:
- positive with PF ≥ 1.15 on both 3 years and 5 years;
- at least 30 trades;
- better than the mean of the random controls;
- passes the best-day check (the total stays positive without the best day and the best trade).

If an asset fails, it stops there: no optimisation.

## Addendum 1 (2026-11-03, after a 4-month smoke test and before any main run)
- **What the smoke test (2026-07-01 → 2026-11-03) showed:**
  - XAUUSD exit orders were rejected in the daily trading break, so exits slipped a bar.
  - $10k gave gold only 0.01-lot steps (≈ $4k each).
- **Fixes:**
  - exits now retry until filled (at most every 10 seconds);
  - entries retry within their own bar only (a missed open is not chased);
  - the deposit is $100k.
- **No rule changed.** The smoke results (USTEC −1.9%, 8 trades; XAUUSD −2.1%, 34 trades) are discarded and not used for any choice.
