# Portfolio consistency audit — 2026-09-12

Evidence cutoff: **2026-08-30**. Four removals were applied after explicit user approval; DMC Current XAU was retained.

## Portfolio scenario comparison

| Scenario | Horizon | Return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|---:|
| Active 35 before Sell Nasdaq mode change | 6m | +1443.25% | 3.55 | 50.09% | 11.06% | 1106 |
| Active 35 before Sell Nasdaq mode change | 1y | +10180.17% | 6.28 | 51.62% | 5.52% | 2189 |
| Active 35 before Sell Nasdaq mode change | 3y | +51889.59% | 7.51 | 52.44% | 8.11% | 6096 |
| Active 35 before Sell Nasdaq mode change | 5y | +92163.18% | 7.07 | 50.46% | 33.07% | 9761 |
| Recommended active 35 | 6m | +1441.19% | 3.59 | 50.46% | 11.36% | 1096 |
| Recommended active 35 | 1y | +10188.72% | 6.34 | 52.05% | 5.02% | 2169 |
| Recommended active 35 | 3y | +51896.39% | 7.59 | 52.60% | 9.92% | 6032 |
| Recommended active 35 | 5y | +92180.09% | 7.12 | 50.65% | 32.51% | 9656 |

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
| Nasdaq 5M Candle Momentum | User-selected DI + wide price stop + ATR trail. 5Y PF 1.29 and equity DD 24.07% at 1% risk; retrospective selection, overnight/weekend exposure, not FTMO validation. Fixed-target pass forecasts are obsolete for this management. |
| XAU Regime Switch | Strong long history but last six months are -4.95% with PF 0.43. |
| XAU Trend Progression | User-selected 0.6R; retrospective sensitivity, five-year PF 1.156 fails the strict 1.20 screen. Not FTMO validation. |
| XAU Slow Trend | Normal BATs use 1R (one-year PF 1.198, five-year PF 1.134); FTMO target 0.5R has one-year PF 1.106. Strict cross-window screen failed; standalone tests are not guarded FTMO results. |
| News Pulse XAU | Required News Pulse exposure retained at fixed risk. Review the independent period's trade count and real-tick coverage; older generated ticks and live news slippage remain limitations. |
| News Pulse XAG | Required News Pulse exposure retained at fixed risk. Review the independent period's trade count and real-tick coverage; older generated ticks and live news slippage remain limitations. |
| News Pulse BTC | Required News Pulse exposure retained at fixed risk. Review the independent period's trade count and real-tick coverage; older generated ticks and live news slippage remain limitations. |
| News Pulse EURUSD | User-restored News Pulse with full-year hindsight-fitted event settings. Extremely tight stops, generated historical ticks and live news execution invalidate any guaranteed-risk or forward-return claim. |
| US100 Selective ORB V3 | Only 34 trades exist in the 5Y view; retain as low-frequency evidence, not as a high-capacity core. |
| XAU Squeeze Momentum Standard | Safe mode has strong PF/DD but only 48 trades in 5Y and no trades in the latest six months. |

## Important limitation

The combined figures merge independently sized MT5 deal ledgers. They are useful for relative portfolio decisions, but they are not proof of future returns or an exact shared-margin equity simulation. Concurrent positions can create materially more account risk than any one EA's displayed drawdown.
