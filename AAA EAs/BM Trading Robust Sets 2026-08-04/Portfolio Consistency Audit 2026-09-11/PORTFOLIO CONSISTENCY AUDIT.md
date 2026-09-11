# Portfolio consistency audit — 2026-09-12

Evidence cutoff: **2026-09-05**. Four removals were applied after explicit user approval; DMC Current XAU was retained.

## Portfolio scenario comparison

| Scenario | Horizon | Return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|---:|
| Active 32 before Sell Nasdaq mode change | 6m | +291.81% | 1.72 | 43.84% | 12.37% | 869 |
| Active 32 before Sell Nasdaq mode change | 1y | +871.32% | 1.91 | 45.38% | 8.18% | 1730 |
| Active 32 before Sell Nasdaq mode change | 3y | +2784.66% | 1.94 | 46.10% | 11.88% | 4482 |
| Active 32 before Sell Nasdaq mode change | 5y | +2806.11% | 1.66 | 43.19% | 59.23% | 6932 |
| Recommended active 32 | 6m | +289.75% | 1.73 | 44.24% | 11.08% | 859 |
| Recommended active 32 | 1y | +879.87% | 1.94 | 45.85% | 7.42% | 1710 |
| Recommended active 32 | 3y | +2791.47% | 1.97 | 46.22% | 13.73% | 4418 |
| Recommended active 32 | 5y | +2823.02% | 1.68 | 43.36% | 49.88% | 6827 |

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
| News Pulse XAU | Mandatory News Pulse exposure retained at fixed risk, but the release-verified schedule ledger is short (9 trades). |
| News Pulse XAG | Mandatory News Pulse exposure retained at fixed risk, but the release-verified schedule ledger is short (9 trades). |
| News Pulse BTC | Mandatory News Pulse exposure retained at fixed risk; the complete three-year native MT5 sample has 125 trades, but event execution remains high-slippage risk. |
| US100 Selective ORB V3 | Only 34 trades exist in the 5Y view; retain as low-frequency evidence, not as a high-capacity core. |
| XAU Squeeze Momentum Standard | Safe mode has strong PF/DD but only 48 trades in 5Y and no trades in the latest six months. |

## Important limitation

The combined figures merge independently sized MT5 deal ledgers. They are useful for relative portfolio decisions, but they are not proof of future returns or an exact shared-margin equity simulation. Concurrent positions can create materially more account risk than any one EA's displayed drawdown.
