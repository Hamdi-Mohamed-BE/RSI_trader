# Portfolio consistency audit — 2026-09-12

Evidence cutoff: **2026-09-05**. Four removals were applied after explicit user approval; DMC Current XAU was retained.

## Portfolio scenario comparison

| Scenario | Horizon | Return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|---:|
| Active 33 before Sell Nasdaq mode change | 6m | +1394.94% | 3.80 | 43.57% | 10.56% | 902 |
| Active 33 before Sell Nasdaq mode change | 1y | +10127.48% | 6.60 | 45.36% | 5.06% | 1788 |
| Active 33 before Sell Nasdaq mode change | 3y | +51828.26% | 7.81 | 45.62% | 13.54% | 4790 |
| Active 33 before Sell Nasdaq mode change | 5y | +92002.22% | 7.37 | 43.10% | 37.74% | 7550 |
| Recommended active 33 | 6m | +1392.88% | 3.86 | 43.95% | 9.42% | 892 |
| Recommended active 33 | 1y | +10136.03% | 6.67 | 45.81% | 4.54% | 1768 |
| Recommended active 33 | 3y | +51835.07% | 7.90 | 45.73% | 15.39% | 4726 |
| Recommended active 33 | 5y | +92019.13% | 7.42 | 43.25% | 37.04% | 7445 |

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
