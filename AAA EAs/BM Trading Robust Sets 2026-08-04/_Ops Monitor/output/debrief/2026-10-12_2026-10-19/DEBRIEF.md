# Weekly live debrief 2026-10-12 → 2026-10-19 (end exclusive, server time)

Demo account Exness-MT5Trial15 ****7938 (trade_mode 0, 0 = demo). Snapshot 2026-10-20T15:10 UTC. Last EA-opened entry: **2026-10-20T15:00 UTC** (the MT5 API's terminal trade_allowed flag read False; EA entries are the reliable evidence that Algo Trading is on).

Judges execution against the same week's native backtest of the same frozen EX5/SET (isolated tester, Exness-MT5Trial16, Model 4), never the result. The demo runs on Exness-MT5Trial15: quotes and spreads differ, so small timing differences are expected.

## 1. Counts

- Live positions opened in the window: **30**. Backtest trades (non-news EAs): **101**.
- Matched (same side, entry within one bar, same exit type): **19**; extra on demo: **2**.
- Missed on demo: **73** = **53** for live-phase EAs (a fault to explain) + **20** for paused/review EAs (expected: they should not trade).
- Live-roster EAs that traded in the backtest but not on the demo: **5**.
- EAs trading on the demo that are NOT in the live phase: **1** (3 Way Gold [paused]).
- Manual / mobile / web closes of positions in the window: **10** (nasdaq-5m-candle-momentum USTEC Mon 10-12 17:35 client; dmc-current-xau XAUUSD Mon 10-12 17:35 client; ema3 XAUUSD Mon 10-12 17:35 client; gold-overnight-value-area XAUUSD Mon 10-12 17:35 client; us100-h1-orb-13utc USTEC Mon 10-12 17:35 client; us100-hourly-profiles USTEC Mon 10-12 17:34 client; nasdaq-overnight USTEC Wed 10-14 12:39 mobile; 3-way-gold XAUUSD Wed 10-14 16:15 mobile; ema3 XAUUSD Wed 10-14 16:15 mobile; nasdaq-overnight USTEC Wed 10-14 20:13 mobile).

## 2. Per EA

| Phase | EA | Live | Backtest | Match | Timing | Exit diff | Missed | Extra | Result sign agrees | Kill switch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| live | BTC Top Down FVG Liquidity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | OK |
| live | DMC Current XAU | 4 | 4 | 3 | 0 | 1 | 0 | 0 | 4/4 | OK |
| live | DMC Fresh Reaction US100 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0/0 | OK |
| live | DMC Fresh Reaction XAU | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 0/0 | OK |
| live | EMA3 | 3 | 2 | 0 | 0 | 2 | 0 | 1 | 0/2 | OK |
| live | Gold Overnight Value Area | 5 | 5 | 4 | 0 | 1 | 0 | 0 | 5/5 | OK |
| live | Nasdaq 5M Candle Momentum | 4 | 5 | 4 | 0 | 0 | 1 | 0 | 4/4 | OK |
| live | Nasdaq Overnight | 5 | 5 | 2 | 0 | 3 | 0 | 0 | 5/5 | OK |
| live | ORB Volume Profile | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 0/0 | OK |
| live | ORB Volume Profile Volume Confirmed | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | OK |
| live | US100 H1 ORB 13UTC | 2 | 2 | 1 | 0 | 1 | 0 | 0 | 1/2 | OK |
| live | US100 Hourly Profiles | 1 | 23 | 0 | 0 | 1 | 22 | 0 | 1/1 | NO_THRESHOLD |
| live | US100 Month End Flow | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | OK |
| live | US100 ORB New York M30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | OK |
| live | US100 Selective ORB V3 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0/0 | — |
| live | US30 Hourly Profiles | 0 | 24 | 0 | 0 | 0 | 24 | 0 | 0/0 | NO_THRESHOLD |
| live | USDJPY London Open Momentum | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 2/2 | OK |
| live | XAU ORB London NY Overlap M30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | OK |
| live | XAU ORB New York M30 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 2/2 | OK |
| live | XAU RSI VWAP | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1/1 | OK |
| live | XAU Trend Progression | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | — |
| live | XAU Weakness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | — |
| paused | 3 Way Gold | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0/0 | OK |
| paused | BTC POC Fibonacci | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | — |
| paused | LTA Volume Profile | 0 | 6 | 0 | 0 | 0 | 6 | 0 | 0/0 | OK |
| paused | XAU Regime Switch | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0/0 | OK |
| paused | XAU Slow Trend | 0 | 5 | 0 | 0 | 0 | 5 | 0 | 0/0 | OK |
| review | Asia Breakout | 0 | 3 | 0 | 0 | 0 | 3 | 0 | 0/0 | OK |
| review | ETH Top Down FVG Liquidity | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0/0 | OK |
| review | Sell Nasdaq 15min | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 0/0 | OK |
| review | XAU Elliott Wave 1-2-3 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 0/0 | OK |
| review | XAU Squeeze Momentum Standard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | — |

## 3. Kill-switch status (all live history of each EA, R at the assumed risk)

R = net / (1.0% × balance before entry). Live BAT risk, adaptive tapers and news percentages can differ per EA, so treat R as approximate.

| EA | Live closed trades | Live total R | Live max DD R | WATCH / KILL DD R | Current losing streak | WATCH / KILL streak | Status |
|---|---:|---:|---:|---|---:|---|---|
| 3 Way Gold | 1 | +0.04 | 0.0 | 6.97 / 9.02 | 0 | 6 / 9 | **OK** |
| Asia Breakout | 2 | +0.28 | 0.07 | 7.57 / 9.67 | 1 | 6 / 8 | **OK** |
| BTC Top Down FVG Liquidity | 2 | -1.51 | 1.51 | 4.95 / 6.14 | 2 | 4 / 9 | **OK** |
| DMC Current XAU | 12 | -0.94 | 3.4 | 9.83 / 16.49 | 3 | 8 / 12 | **OK** |
| DMC Fresh Reaction US100 | 1 | +0.28 | 0.0 | 3.68 / 5.04 | 0 | 3 / 4 | **OK** |
| DMC Fresh Reaction XAU | 1 | +0.36 | 0.0 | 3.73 / 5.58 | 0 | 4 / 11 | **OK** |
| EMA3 | 7 | +0.98 | 0.74 | 7.01 / 9.28 | 0 | 5 / 6 | **OK** |
| ETH Top Down FVG Liquidity | 2 | -1.46 | 1.46 | 3.14 / 4.22 | 2 | 3 / 6 | **OK** |
| Gold Overnight Value Area | 18 | -0.07 | 1.51 | 7.7279 / 16.4 | 1 | 5 / 6 | **OK** |
| LTA Volume Profile | 14 | -2.88 | 6.22 | 15.09 / 19.89 | 5 | 13 / 17 | **OK** |
| Nasdaq 5M Candle Momentum | 18 | +11.16 | 1.08 | 15.13 / 19.81 | 1 | 10 / 12 | **OK** |
| Nasdaq Overnight | 10 | -0.38 | 1.02 | 2.75 / 4.67 | 0 | 5 / 7 | **OK** |
| ORB Volume Profile | 4 | -0.23 | 1.11 | 6.32 / 7.94 | 1 | 7 / 9 | **OK** |
| ORB Volume Profile Volume Confirmed | 1 | +0.40 | 0.0 | 3.92 / 5.17 | 0 | 5 / 7 | **OK** |
| Sell Nasdaq 15min | 1 | +0.45 | 0.0 | 7.55 / 10.9 | 0 | 7 / 11 | **OK** |
| US100 H1 ORB 13UTC | 8 | -1.20 | 2.08 | 7.31 / 11.9 | 0 | 6 / 8 | **OK** |
| US100 Hourly Profiles | 22 | -0.29 | 0.48 | — / — | 1 | — / — | **NO_THRESHOLD** |
| US100 Month End Flow | 3 | +0.14 | 0.71 | 6.06 / 7.76 | 0 | 5 / 7 | **OK** |
| US100 ORB New York M30 | 2 | +0.92 | 0.69 | 4.03 / 5.14 | 1 | 4 / 6 | **OK** |
| US30 Hourly Profiles | 23 | -0.24 | 0.51 | — / — | 7 | — / — | **NO_THRESHOLD** |
| USDJPY London Open Momentum | 10 | -1.73 | 2.7 | 6.24 / 8.16 | 2 | 7 / 8 | **OK** |
| XAU Elliott Wave 1-2-3 | 1 | -0.37 | 0.37 | 4.97 / 9.35 | 1 | 5 / 8 | **OK** |
| XAU ORB London NY Overlap M30 | 1 | -0.73 | 0.73 | 3.07 / 5.55 | 1 | 4 / 7 | **OK** |
| XAU ORB New York M30 | 3 | -1.93 | 1.93 | 2.28 / 3.35 | 2 | 4 / 6 | **OK** |
| XAU RSI VWAP | 4 | +1.88 | 0.0 | 4.82 / 6.45 | 0 | 3 / 4 | **OK** |
| XAU Regime Switch | 6 | +0.69 | 1.23 | 8.65 / 11.23 | 0 | 9 / 12 | **OK** |
| XAU Slow Trend | 11 | +2.70 | 1.49 | 13.369 / 17.16 | 1 | 8 / 10 | **OK** |

## 4. One change for next week (proposal; the owner decides)

- Check that the reviewed profile is attached on the demo (EAs are opening trades, last EA entry 2026-10-20T15:00 UTC): 5 live-roster EAs traded in the backtest but not on the demo (DMC Fresh Reaction US100, DMC Fresh Reaction XAU, ORB Volume Profile, US100 Selective ORB V3, US30 Hourly Profiles).

## 5. What this does NOT show

- Whether any EA has an edge: one week is far too short. This checks execution and wiring only.
- News EAs: no tester evidence after 2026-09-11; only their entry times versus official event times are listed.
- Backtest and demo use different Exness servers; a TIMING or EXIT_DIFF can be a quote difference, not a fault.
- Live R uses one assumed risk %, not each EA's actual planned stop risk.
