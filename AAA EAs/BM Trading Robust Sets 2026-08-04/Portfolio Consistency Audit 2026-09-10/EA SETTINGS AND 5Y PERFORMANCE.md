# EA Settings and Five-Year Performance

Generated 2026-09-10 from the exact 31-EA Best Recommended mode selected by the Calyx installers and the cached native MT5 Every Tick evidence. DMC Current XAU is retained by explicit user decision; the four approved removals are documented below the active table.

- Standard evidence window: 2021-09-05 to 2026-09-05. Sell Nasdaq 15min uses 2021-09-07 to 2026-09-07.
- Return, profit factor, win rate, drawdown and trade count are per-EA results, not a simultaneous shared-margin portfolio test.
- `R` is the initial entry-to-stop risk. The target RR is nominal: trailing, break-even, momentum exits and timed exits can change realized R.
- Dynamic 50/20 means that after a completed M15 candle closes 50% of the way to the original target, the stop locks 20% of that target path. Dynamic 60/20 uses a 60% trigger.

| # | EA — selected mode | Initial stop loss | Target / RR | Trailing and other management | Return | PF | Win rate | Max DD | Trades |
|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | LTA Volume Profile — **Safe** | Beyond confirmation candles; also beyond zone for zone trades; +0.12 ATR buffer | 3R | No trail or BE; Safe D1 gate affects entries only | +128.30% | 1.23 | 29.23% | 20.52% | 609 |
| 2 | BTC Top Down FVG Liquidity — Standard | Beyond swept extreme +0.10 ATR; accept only 0.30–3.00 ATR | 2R | No trail/BE; close after 96 M15 bars | +14.91% | 1.21 | 40.17% | 10.25% | 117 |
| 3 | BTC POC Fibonacci — Standard | 1.5 ATR | 5R | No trail/BE; close after 96 M15 bars | +44.30% | 1.47 | 33.33% | 14.10% | 114 |
| 4 | ETH Top Down FVG Liquidity — Standard | Beyond swept extreme +0.10 ATR; accept only 0.30–3.00 ATR | 4R | Dynamic 50/20; close after 96 M15 bars | +22.93% | 1.54 | 38.98% | 7.45% | 59 |
| 5 | ORB Volume Profile — Standard | Opposite opening-range boundary +0.10 ATR; reject above 2 ATR | 2.5R | BE at +1R; Dynamic 50/20; flat 15:55 NY | +59.19% | 1.43 | 43.75% | 6.14% | 304 |
| 6 | ORB Volume Profile Volume Confirmed — Standard | Opposite opening-range boundary +0.10 ATR; reject above 2 ATR | 2.5R | BE at +1R; Dynamic 50/20; flat 15:55 NY | +34.62% | 1.69 | 43.33% | 5.67% | 120 |
| 7 | XAU ORB New York M30 — Standard | Opposite range boundary +0.10 ATR; reject above 2 ATR | 1.5R | BE at +0.5R; no trail; flat 15:55 NY | +12.14% | 1.67 | 39.29% | 6.14% | 84 |
| 8 | XAU ORB London NY Overlap M30 — Standard | Opposite five-minute range boundary +0.05 ATR; reject above 1.5 ATR | 1R | BE at +0.5R; no trail; flat 16:00 UTC | +24.31% | 1.62 | 49.25% | 6.12% | 134 |
| 9 | US100 ORB New York M30 — Standard | Opposite range boundary +0.10 ATR; reject above 2 ATR | 4R | No trail/BE; flat 15:55 NY | +40.09% | 1.78 | 48.96% | 8.02% | 96 |
| 10 | US100 H1 ORB 13UTC — Standard | Opposite H1 range boundary +0.10 ATR; reject above 3 H1 ATR | Nominal 6R | No trail/BE; flat 20:00 UTC | +92.93% | 1.57 | 48.79% | 17.82% | 289 |
| 11 | US100 Selective ORB V3 — Standard | Opposite range boundary +5% of range; reject above 0.8 D1 ATR | 2R | BE at +1R; no trail; flat 15:55 NY | +17.20% | 3.16 | 67.65% | 3.67% | 34 |
| 12 | Asia Breakout — Standard | Asian range midpoint | 3R | Dynamic 50/20 plus native trail from +2R at 0.5R distance | +45.50% | 1.40 | 43.85% | 6.27% | 187 |
| 13 | DMC Current XAU — **Retained** | Fixed 22.5 XAU price units | 3R | Dynamic 50/20 only; native trail off | +11.58% | 1.06 | 37.97% | 29.05% | 345 |
| 14 | DMC Fresh Reaction XAU — Standard | Fixed 30 XAU price units | 3R | Dynamic 50/20 only. The generic native-trail input is present but is not called by the DMC execution path | +21.68% | 1.53 | 49.41% | 15.18% | 85 |
| 15 | DMC Fresh Reaction US100 — Standard | 1.5 H1 ATR(14) | 2R | Dynamic 50/20 only. The generic native-trail input is present but is not called by the DMC execution path | +14.23% | 1.39 | 58.54% | 7.57% | 82 |
| 16 | EMA3 — **Safe** | Opposite extreme of the last five H4 bars | 1.7R | Dynamic 60/20 only; native trail off | +30.93% | 1.86 | 60.78% | 5.03% | 102 |
| 17 | XAU Weakness — **Safe** | Beyond the intervening pattern range +0.05 ATR | 4R | Dynamic 50/20; native trail off | +122.15% | 1.65 | 38.93% | 14.40% | 244 |
| 18 | Nasdaq Overnight — Standard | Emergency stop 2% below entry | No TP / variable realized RR | No trail/BE; time exit around 09:29 next NY date | +8.40% | 1.28 | 56.28% | 4.83% | 199 |
| 19 | Nasdaq 5M Candle Momentum — Standard | 4 × M5 ATR(14) | 2.5R | No trail/BE; flat 15:55 NY | +105.74% | 1.12 | 38.99% | 12.63% | 1,272 |
| 20 | Sell Nasdaq 15min — **Dynamic London** | 2.5 × M15 ATR(14) | 3R | No trail/BE; pending expires after 60 minutes; flat 15:55 NY | +106.38% | 1.52 | 41.42% | 17.87% | 268 |
| 21 | USDJPY London Open Momentum — Standard | 5 × M15 ATR(14) | No TP / variable realized RR | BE at +0.75R; time exit 15:59:30 London | +178.41% | 1.46 | 53.97% | 12.12% | 693 |
| 22 | XAU Squeeze Momentum Standard — **Safe** | 3.5 × H1 Wilder ATR(14) | 1.5R | 3.5 ATR ratchet below highest completed high; momentum-fade exit | +23.00% | 3.16 | 60.42% | 3.35% | 48 |
| 23 | News Pulse XAU — Standard | 6.0 XAU price units; entry offset also 6.0 | No TP / 60-second event exit | Native trail starts +1.5R, 15.0-unit distance; force close at +60s | +55.54% | 9.03 | 64.71% | 1.79% | 34 |
| 24 | News Pulse XAG — Standard | 0.08 XAG price units; entry offset also 0.08 | No TP / 60-second event exit | Native trail starts +1.5R, 0.20-unit distance; force close at +60s | +221.19% | 13.41 | 63.16% | 2.52% | 38 |
| 25 | News Pulse EURUSD — Standard | 0.0006 (6 pips); entry offset also 6 pips | No TP / 60-second event exit | Native trail starts +1.5R, 0.0015 (15-pip) distance; force close at +60s | +55.31% | 8.19 | 68.57% | 2.85% | 35 |
| 26 | XAU RSI VWAP — Standard | Below lowest of prior five H1 bars +0.10 ATR | 0.5R | +0.75R BE is configured but unreachable; no trail | +26.11% | 1.37 | 73.46% | 5.34% | 260 |
| 27 | XAU Trend Progression — Standard | Below lowest of latest five H4 bars +0.10 ATR | 3R | At +1R, lock +0.05R; no trail | +83.90% | 2.27 | 58.70% | 5.54% | 138 |
| 28 | XAU Elliott Wave 1-2-3 — Standard | Beyond breakout candle +0.10 ATR; reject above 5 ATR | 3R | No trail/BE/time exit | +72.30% | 1.88 | 37.93% | 10.59% | 116 |
| 29 | XAU Slow Trend — Standard | 1.5 × H4 ATR(14) | 6R | No trail/BE/time exit | +86.18% | 1.42 | 19.18% | 12.63% | 245 |
| 30 | XAU Regime Switch — Standard | Trend leg: 1.5 H4 ATR; sideways leg: 1.5 M5 ATR | Trend 6R; sideways 3R | No trail/BE; sideways leg closes 12:00 NY | +96.19% | 1.59 | 27.96% | 10.21% | 211 |
| 31 | US100 Month End Flow — Standard | 1.5 × M30 ATR(14) | 2.5R | No trail/BE; close after six hours | +37.84% | 1.37 | 44.57% | 9.13% | 175 |

## Important interpretation notes

1. News Pulse never uses the user-selected portfolio risk. It is hard-locked at 0.75% per pending direction, with a 1.50% planned two-sided event cap before gaps and slippage.
2. All other current installer entries follow the risk percentage entered by the user, defaulting to 1% when Enter is pressed.
3. The very high News Pulse profit factors come from only 34–38 event trades and need live/demo monitoring; they should not be compared naively with 600- or 1,200-trade systems.
4. DMC Current XAU remains installed by explicit user decision. Its PF 1.06 and 29.05% five-year drawdown make it a monitored retention, not a claim that it was the strongest consistency choice.

## Approved removals

These strategies remain archived in research folders and evidence caches, but are no longer in the website catalogue or any main portfolio BAT:

| EA | Reason |
|---|---|
| Engineered Liquidity XAU | Weak consistency: five-year PF 1.17 with 39.68% drawdown. |
| ORB Volume Profile High Win 0.75R | Duplicated the stronger base/confirmed ORB paths with weaker long-window quality. |
| XAG Session VWAP Snapback | No durable edge in the full cached window: PF 1.00 and +0.04% return. |
| XAU Squeeze Momentum High Win 0.75R | Duplicated the stronger evidence-selected Standard/Safe Squeeze entry. |
