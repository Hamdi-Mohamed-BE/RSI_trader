# Portfolio consistency audit — 2026-09-10

Evidence cutoff: **2026-09-05**. Four removals were applied after explicit user approval; DMC Current XAU was retained.

## Portfolio scenario comparison

| Scenario | Horizon | Return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|---:|
| Active 32 before Sell Nasdaq mode change | 6m | +276.44% | 1.68 | 43.11% | 12.73% | 863 |
| Active 32 before Sell Nasdaq mode change | 1y | +810.33% | 1.85 | 45.06% | 9.52% | 1720 |
| Active 32 before Sell Nasdaq mode change | 3y | +1855.11% | 1.65 | 45.42% | 12.29% | 4392 |
| Active 32 before Sell Nasdaq mode change | 5y | +1876.56% | 1.45 | 42.72% | 59.23% | 6842 |
| Recommended active 32 | 6m | +274.39% | 1.69 | 43.49% | 11.42% | 853 |
| Recommended active 32 | 1y | +818.88% | 1.88 | 45.53% | 7.99% | 1700 |
| Recommended active 32 | 3y | +1861.91% | 1.67 | 45.54% | 14.14% | 4328 |
| Recommended active 32 | 5y | +1893.47% | 1.47 | 42.88% | 49.88% | 6737 |

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
| News Pulse EURUSD | Mandatory News Pulse exposure retained at fixed risk, but the verified event ledger is short (35 trades). |
| US100 Selective ORB V3 | Only 34 trades exist in the 5Y view; retain as low-frequency evidence, not as a high-capacity core. |
| XAU Squeeze Momentum Standard | Safe mode has strong PF/DD but only 48 trades in 5Y and no trades in the latest six months. |

## Important limitation

The combined figures merge independently sized MT5 deal ledgers. They are useful for relative portfolio decisions, but they are not proof of future returns or an exact shared-margin equity simulation. Concurrent positions can create materially more account risk than any one EA's displayed drawdown.
