# Portfolio consistency audit — 2026-09-11

Evidence cutoff: **2026-09-05**. Four removals were applied after explicit user approval; DMC Current XAU was retained.

## Portfolio scenario comparison

| Scenario | Horizon | Return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|---:|
| Active 32 before Sell Nasdaq mode change | 6m | +291.82% | 1.71 | 43.78% | 12.15% | 868 |
| Active 32 before Sell Nasdaq mode change | 1y | +850.93% | 1.89 | 45.34% | 8.19% | 1729 |
| Active 32 before Sell Nasdaq mode change | 3y | +1890.86% | 1.66 | 45.52% | 12.29% | 4400 |
| Active 32 before Sell Nasdaq mode change | 5y | +1912.31% | 1.46 | 42.79% | 59.23% | 6850 |
| Recommended active 32 | 6m | +289.76% | 1.73 | 44.17% | 10.87% | 858 |
| Recommended active 32 | 1y | +859.48% | 1.92 | 45.82% | 7.42% | 1709 |
| Recommended active 32 | 3y | +1897.67% | 1.68 | 45.64% | 14.14% | 4336 |
| Recommended active 32 | 5y | +1929.22% | 1.48 | 42.95% | 49.88% | 6745 |

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
| News Pulse XAU | Mandatory News Pulse exposure retained at fixed risk, but the verified event ledger is short (34 trades). |
| News Pulse XAG | Mandatory News Pulse exposure retained at fixed risk, but the verified event ledger is short (38 trades). |
| News Pulse BTC | Mandatory News Pulse exposure retained at fixed risk; the 43-trade historical sample passed locked, delay-stress and current seven-event FXMacroData verification, but remains small. |
| US100 Selective ORB V3 | Only 34 trades exist in the 5Y view; retain as low-frequency evidence, not as a high-capacity core. |
| XAU Squeeze Momentum Standard | Safe mode has strong PF/DD but only 48 trades in 5Y and no trades in the latest six months. |

## Important limitation

The combined figures merge independently sized MT5 deal ledgers. They are useful for relative portfolio decisions, but they are not proof of future returns or an exact shared-margin equity simulation. Concurrent positions can create materially more account risk than any one EA's displayed drawdown.
