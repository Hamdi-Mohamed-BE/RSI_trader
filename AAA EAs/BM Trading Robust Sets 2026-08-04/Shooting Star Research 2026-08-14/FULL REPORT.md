# Shooting-Star Reversal Research — Final Report

Date completed: 2026-08-14  
Starting balance: USD 10,000  
Risk: 1.00% of current balance per trade  
Data: MEXAtlantic-Demo M1 broker history, January 2022 through August 2026

## Decision

**REJECT on all six markets. Do not add this strategy to the active EA installer.**

The optimized shooting-star idea did not meet the agreed minimum of 15% annualized return with a positive, sufficiently populated 2026 confirmation. US100, BTC, and ETH exceeded 15% only as a *total* return over about 4.6 years—not per year.

## Honest results

All returns and drawdowns use 1% risk per trade. The 2026 segment was locked and was not used to choose parameters.

| Market | Best TF | Full trades | Win rate | Full PF | Full return | CAGR | Max equity DD | 2026 trades | 2026 PF | 2026 return | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| XAU | M30 | 84 | 51.19% | 1.01 | +0.08% | +0.02% | 8.48% | 8 | 0.59 | -2.06% | Reject |
| XAG | H4 | 63 | 39.68% | 1.39 | +10.05% | +2.10% | 6.37% | 8 | 0.99 | -0.07% | Reject |
| US30 | H1 | 59 | 40.68% | 1.07 | +1.50% | +0.32% | 10.10% | 12 | 0.49 | -3.60% | Reject |
| US100 | M15 | 60 | 35.00% | 1.57 | +24.21% | +4.83% | 7.73% | 5 | 0.73 | -1.14% | Reject |
| BTC | M30 | 87 | 33.33% | 1.40 | +16.95% | +3.46% | 6.34% | 13 | 1.87 | +3.65% | Reject: return too low |
| ETH | H1 | 48 | 37.50% | 1.63 | +20.62% | +4.16% | 9.26% | 4 | 2.73 | +3.68% | Reject: only 4 confirmation trades |

## Exact optimized definitions

| Market | Candle geometry | Trend/location/volume | Entry | Stop | Target / hold | Management |
|---|---|---|---|---|---|---|
| XAU | Body <=25%; upper wick >=3x body; lower wick <=10% range | 8-bar rise >=0.5 ATR; new 20-bar high; volume >=1.25x average | Sell-stop at star low | 1 ATR above entry | 1R / 2h | Fixed |
| XAG | Body <=40%; upper wick >=2x body; lower wick <=20% range | 8-bar rise >=1 ATR; new 10-bar high; no volume gate | Next-bar open | Star high +0.25 ATR | 1.5R / 48h | Break-even at +1R |
| US30 | Body <=40%; upper wick >=2x body; lower wick <=10% range | 8-bar rise >=0.5 ATR; new 20-bar high; volume >=1.25x average | Next-bar open | Star high +0.10 ATR | 1.5R / 6h | Fixed |
| US100 | Body <=40%; upper wick >=3x body; lower wick <=10% range | 8-bar rise >=0.5 ATR; new 20-bar high; volume >=1.25x average | Next open after close below star low | 1.25 ATR above entry | 3R / 24h | Fixed |
| BTC | Body <=25%; upper wick >=3x body; lower wick <=10% range | 3-bar rise >=0.5 ATR; new 20-bar high; no volume gate | Next open after close below star low | Star high | 2R / 48h | Break-even at +1R |
| ETH | Body <=40%; upper wick >=3x body; lower wick <=10% range | 8-bar rise >=1 ATR; new 20-bar high; no volume gate | Next open after close below star low | Star high | 3R / 48h | Fixed |

These are research finalists, not recommended live settings. Their machine-readable records are in `Results/<MARKET>-selected-result.json`.

## Optimization and validation flow

1. Screened 1,920 candle/trend/location/volume/entry definitions per market across M5, M15, M30, H1, and H4.
2. Retained the 15 best development definitions per market.
3. Screened 3,600 stop, buffer, reward/risk, maximum-hold, and break-even combinations per market.
4. Used 2022–2024 for development and 2025 for validation.
5. Chose the robust finalist without seeing 2026.
6. Ran the locked 2026 confirmation and then reported the untouched full-period result.
7. Required at least 8 confirmation trades, 2026 PF >=1.05, positive 2026 return, 2026 DD <15%, full PF >=1.05, and CAGR >=15% for deployment.

## Execution assumptions

- Entries and exits were simulated on M1 bars.
- Recorded broker spread was applied; median spreads ranged from 0.025 on XAG to 35.0 on BTC in price units.
- An additional 25% of median spread was charged as slippage on each fill.
- If stop and target were both reachable within the same M1 bar, the stop was assumed to occur first.
- Drawdown includes minute-by-minute marked-to-market equity, not only closed trades.
- Only one trade per market could be open at a time.
- Broker `real_volume` was zero on all six histories. The tested volume filter therefore used broker tick volume; it is not centralized exchange volume.

## Research basis

- Jamaloodeen et al. found little broad predictive reliability for hammer/shooting-star patterns using closing prices, with better evidence when the candle high was used. That motivated the local-high/location constraint: https://scholars.fhsu.edu/jiibr/vol5/iss1/5/
- Seth and Singh reported that smaller shooting stars and short holding periods performed better in their Nifty 50 sample. That motivated screening strict body/wick geometry and 2–48 hour exits: https://www.ijrte.org/wp-content/uploads/papers/v8i2/B3483078219.pdf
- The standard pattern category was cross-checked against TA-Lib's `CDLSHOOTINGSTAR`: https://ta-lib.github.io/ext-ta-lib/docs/api/functions/ta_cdlshootingstar.html

The empirical literature is mixed, which matches this test: isolated strong-looking periods did not generalize consistently across markets or into locked 2026.

## Files

- `Results/all-markets-equity.png` — combined six-panel equity graph
- `Results/<MARKET>-equity.png` — individual equity graph
- `Results/summary.csv` — compact comparison table
- `Results/<MARKET>-selected-result.json` — exact selected configuration and period metrics
- `Results/<MARKET>-selected-trades.csv` — complete selected trade list
- `Results/<MARKET>-development-screen.csv` — optimization candidates
- `Results/all-results.json` — combined machine-readable report
- `backtest_shooting_star.py` — reproducible research runner

## Deployment action

No EA was built, no `.set` was promoted, and `INSTALL AND RUN ON ACTIVE MT5.bat` was not changed because every market failed the acceptance gate.
