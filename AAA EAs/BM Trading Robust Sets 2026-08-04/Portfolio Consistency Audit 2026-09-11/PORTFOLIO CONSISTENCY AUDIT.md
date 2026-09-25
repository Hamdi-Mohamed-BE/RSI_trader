# Portfolio consistency audit — 2026-09-12

Evidence cutoff: **2026-08-30**. Four removals were applied after explicit user approval; DMC Current XAU was retained.

## Portfolio scenario comparison

| Scenario | Horizon | Return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|---:|
| Active 34 before Sell Nasdaq mode change | 6m | +1413.52% | 3.86 | 46.83% | 10.78% | 963 |
| Active 34 before Sell Nasdaq mode change | 1y | +10170.24% | 6.64 | 48.80% | 5.07% | 1922 |
| Active 34 before Sell Nasdaq mode change | 3y | +51855.15% | 7.87 | 48.62% | 13.04% | 5206 |
| Active 34 before Sell Nasdaq mode change | 5y | +92065.22% | 7.34 | 46.53% | 35.56% | 8276 |
| Recommended active 34 | 6m | +1411.46% | 3.92 | 47.22% | 9.80% | 953 |
| Recommended active 34 | 1y | +10178.79% | 6.71 | 49.26% | 4.55% | 1902 |
| Recommended active 34 | 3y | +51861.95% | 7.95 | 48.76% | 14.89% | 5142 |
| Recommended active 34 | 5y | +92082.12% | 7.39 | 46.71% | 34.90% | 8171 |

## Applied mode recommendations

| EA | Current | Recommended | Reason |
|---|---|---|---|
| Sell Nasdaq 15min | Standard | Dynamic London | Better 1y/3y/5y return and PF with lower 3y/5y drawdown; last six months remain slightly negative. |

All other mode choices remain unchanged. Existing Safe defaults remain on LTA Volume Profile, EMA3, XAU Weakness and XAU Squeeze Momentum Standard.

## Approved removals

| EA | Reason |
|---|---|
| Engineered Liquidity XAU | Weak consistency: 5Y PF 1.17 with 39.68% drawdown. |
| ORB Volume Profile High Win 0.75R | Duplicate core ORB entries with materially weaker 5Y PF and return. |
| XAG Session VWAP Snapback | No demonstrated long-window edge: 5Y return +0.04% with PF 1.00. |
| XAU Squeeze Momentum High Win 0.75R | Near-duplicate squeeze exposure with weaker evidence than Standard Safe. |

DMC Current XAU remains active by explicit user decision.

## Watchlist — retained

| EA | Reason |
|---|---|
| BTC Top Down FVG Liquidity | 5Y PF is only 1.21, although recent performance improved. |
| Nasdaq 5M Candle Momentum | Large historical return but thin edge: PF 1.12 over 5Y and 1.18 over 3Y. |
| XAU Regime Switch | Strong long history but last six months are -4.95% with PF 0.43. |
| XAU Slow Trend | Strong 3Y/5Y evidence but last six months are -7.13% with PF 0.48. |
| News Pulse XAU | Required News Pulse exposure retained at fixed risk. Review the independent period's trade count and real-tick coverage; older generated ticks and live news slippage remain limitations. |
| News Pulse XAG | Required News Pulse exposure retained at fixed risk. Review the independent period's trade count and real-tick coverage; older generated ticks and live news slippage remain limitations. |
| News Pulse BTC | Required News Pulse exposure retained at fixed risk. Review the independent period's trade count and real-tick coverage; older generated ticks and live news slippage remain limitations. |
| News Pulse EURUSD | User-restored News Pulse with full-year hindsight-fitted event settings. Extremely tight stops, generated historical ticks and live news execution invalidate any guaranteed-risk or forward-return claim. |
| US100 Selective ORB V3 | Only 34 trades exist in the 5Y view; retain as low-frequency evidence, not as a high-capacity core. |
| XAU Squeeze Momentum Standard | Safe mode has strong PF/DD but only 48 trades in 5Y and no trades in the latest six months. |

## Important limitation

The combined figures merge independently sized MT5 deal ledgers. They are useful for relative portfolio decisions, but they are not proof of future returns or an exact shared-margin equity simulation. Concurrent positions can create materially more account risk than any one EA's displayed drawdown.
