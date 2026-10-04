# Nasdaq video rule matching — 2026-10-03

Nine years were requested, but this Exness USTEC feed begins 2019-07-16. The comparison trades from 2019-08-01 after warmup, through 2026-10-01: approximately 7.17 years. No missing years were fabricated.

All versions: $10,000, 1% equity risk target, existing upward lot rounding (can exceed target), 0.60% price stop, no TP, overnight/weekend holding, one position, native Model 4, 150ms delay, broker commission and swap.

## Six frozen versions

- **CURRENT**: Our selected DI14 + EMA12 entry, ATR6 trail from +1R; no candle-body requirement.
- **EMA_ONLY**: Our ATR exits, no DI and no candle-body requirement.
- **VIDEO_ATR**: Literal video entry: bullish long above EMA12; short below EMA12; DI off. Our ATR exit assumed.
- **VIDEO_ATR_DI**: Literal video entry with DI14 retained; same ATR exit.
- **SYMMETRIC_ATR**: Bullish long / bearish short with EMA12; DI off. Symmetric short rule is an assumption.
- **VIDEO_MA**: Literal entry without DI; closed-bar EMA200 trail from +0.5R. Exit formula is an assumption.

## Available history • Aug 2019 – Oct 2026

| Version | Return | Net PF | Net win | Equity DD | Trades | Trades/month / weekday | Daily Sharpe | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CURRENT | 141.57% | 1.190 | 42.97% | 40.77% | 1322 | 15.36 / 0.707 | 0.69 | 9 / 9 |
| EMA_ONLY | 79.77% | 1.093 | 42.10% | 49.76% | 1684 | 19.57 / 0.900 | 0.47 | 11 / 11 |
| VIDEO_ATR | 25.82% | 1.035 | 41.52% | 50.15% | 1592 | 18.50 / 0.851 | 0.25 | 11 / 11 |
| VIDEO_ATR_DI | 61.47% | 1.099 | 42.10% | 42.14% | 1240 | 14.41 / 0.663 | 0.43 | 9 / 10 |
| SYMMETRIC_ATR | -6.40% | 0.990 | 41.44% | 49.62% | 1489 | 17.30 / 0.796 | 0.05 | 11 / 12 |
| VIDEO_MA | 1.43% | 1.002 | 42.61% | 53.96% | 1577 | 18.33 / 0.843 | 0.10 | 10 / 14 |

Changes versus CURRENT:
- EMA_ONLY: return -61.80 pp; PF -0.098; win rate -0.86 pp; equity DD +8.99 pp.
- VIDEO_ATR: return -115.76 pp; PF -0.155; win rate -1.45 pp; equity DD +9.38 pp.
- VIDEO_ATR_DI: return -80.10 pp; PF -0.091; win rate -0.87 pp; equity DD +1.37 pp.
- SYMMETRIC_ATR: return -147.98 pp; PF -0.200; win rate -1.53 pp; equity DD +8.85 pp.
- VIDEO_MA: return -140.15 pp; PF -0.188; win rate -0.35 pp; equity DD +13.19 pp.

## Last five years

| Version | Return | Net PF | Net win | Equity DD | Trades | Trades/month / weekday | Daily Sharpe | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CURRENT | 220.90% | 1.302 | 44.47% | 23.98% | 922 | 15.37 / 0.707 | 1.15 | 9 / 9 |
| EMA_ONLY | 148.99% | 1.173 | 43.38% | 28.24% | 1194 | 19.90 / 0.916 | 0.87 | 11 / 11 |
| VIDEO_ATR | 73.13% | 1.105 | 42.57% | 29.30% | 1130 | 18.84 / 0.867 | 0.58 | 11 / 11 |
| VIDEO_ATR_DI | 115.34% | 1.198 | 43.25% | 31.33% | 867 | 14.45 / 0.665 | 0.81 | 9 / 10 |
| SYMMETRIC_ATR | 13.56% | 1.025 | 41.90% | 38.50% | 1055 | 17.59 / 0.809 | 0.22 | 11 / 12 |
| VIDEO_MA | -2.82% | 0.993 | 42.19% | 48.09% | 1114 | 18.57 / 0.854 | 0.06 | 10 / 14 |

Changes versus CURRENT:
- EMA_ONLY: return -71.91 pp; PF -0.129; win rate -1.08 pp; equity DD +4.26 pp.
- VIDEO_ATR: return -147.77 pp; PF -0.197; win rate -1.90 pp; equity DD +5.32 pp.
- VIDEO_ATR_DI: return -105.56 pp; PF -0.104; win rate -1.22 pp; equity DD +7.35 pp.
- SYMMETRIC_ATR: return -207.35 pp; PF -0.277; win rate -2.57 pp; equity DD +14.52 pp.
- VIDEO_MA: return -223.73 pp; PF -0.309; win rate -2.28 pp; equity DD +24.11 pp.

## Last year

| Version | Return | Net PF | Net win | Equity DD | Trades | Trades/month / weekday | Daily Sharpe | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CURRENT | 57.05% | 1.505 | 51.96% | 10.08% | 179 | 14.93 / 0.686 | 2.44 | 9 / 6 |
| EMA_ONLY | 34.46% | 1.221 | 48.32% | 15.05% | 238 | 19.85 / 0.912 | 1.49 | 7 / 7 |
| VIDEO_ATR | 24.31% | 1.163 | 47.14% | 17.95% | 227 | 18.93 / 0.870 | 1.15 | 6 / 7 |
| VIDEO_ATR_DI | 43.59% | 1.403 | 50.30% | 9.17% | 169 | 14.09 / 0.648 | 2.01 | 9 / 6 |
| SYMMETRIC_ATR | 11.33% | 1.085 | 46.45% | 21.66% | 211 | 17.60 / 0.808 | 0.65 | 6 / 6 |
| VIDEO_MA | 22.92% | 1.218 | 47.96% | 12.55% | 221 | 18.43 / 0.847 | 1.18 | 6 / 9 |

Changes versus CURRENT:
- EMA_ONLY: return -22.59 pp; PF -0.283; win rate -3.64 pp; equity DD +4.97 pp.
- VIDEO_ATR: return -32.74 pp; PF -0.342; win rate -4.82 pp; equity DD +7.87 pp.
- VIDEO_ATR_DI: return -13.47 pp; PF -0.102; win rate -1.66 pp; equity DD -0.91 pp.
- SYMMETRIC_ATR: return -45.73 pp; PF -0.420; win rate -5.51 pp; equity DD +11.58 pp.
- VIDEO_MA: return -34.13 pp; PF -0.287; win rate -3.99 pp; equity DD +2.47 pp.

## Last three months

| Version | Return | Net PF | Net win | Equity DD | Trades | Trades/month / weekday | Daily Sharpe | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CURRENT | 6.45% | 1.277 | 51.11% | 6.56% | 45 | 14.89 / 0.682 | 1.57 | 6 / 4 |
| EMA_ONLY | 1.63% | 1.049 | 47.54% | 11.54% | 61 | 20.18 / 0.924 | 0.41 | 7 / 4 |
| VIDEO_ATR | -4.13% | 0.870 | 44.64% | 14.67% | 56 | 18.53 / 0.848 | -0.81 | 6 / 4 |
| VIDEO_ATR_DI | -0.56% | 0.975 | 46.34% | 8.69% | 41 | 13.56 / 0.621 | -0.07 | 5 / 4 |
| SYMMETRIC_ATR | -7.04% | 0.757 | 42.00% | 12.85% | 50 | 16.54 / 0.758 | -1.68 | 5 / 4 |
| VIDEO_MA | 5.09% | 1.245 | 49.06% | 5.41% | 53 | 17.53 / 0.803 | 1.20 | 6 / 4 |

Changes versus CURRENT:
- EMA_ONLY: return -4.81 pp; PF -0.228; win rate -3.57 pp; equity DD +4.98 pp.
- VIDEO_ATR: return -10.58 pp; PF -0.407; win rate -6.47 pp; equity DD +8.11 pp.
- VIDEO_ATR_DI: return -7.01 pp; PF -0.302; win rate -4.77 pp; equity DD +2.13 pp.
- SYMMETRIC_ATR: return -13.48 pp; PF -0.520; win rate -9.11 pp; equity DD +6.29 pp.
- VIDEO_MA: return -1.36 pp; PF -0.032; win rate -2.05 pp; equity DD -1.15 pp.

## Year-by-year closing-trade returns

Available-history runs only. Yearly returns are grouped by trade close date on each continuous account, not fresh yearly backtests. 2019 and 2026 are partial years; open P&L is not included.

| Year | CURRENT | EMA_ONLY | VIDEO_ATR | VIDEO_ATR_DI | SYMMETRIC_ATR | VIDEO_MA |
|---|---:|---:|---:|---:|---:|---:|
| 2019 | -5.78% | -13.72% | -12.62% | -4.59% | -11.98% | -8.10% |
| 2020 | -25.85% | -18.62% | -18.55% | -26.50% | -12.15% | 11.62% |
| 2021 | 3.90% | -5.59% | -6.80% | 2.37% | -3.60% | -4.93% |
| 2022 | 32.01% | 17.66% | 9.05% | 19.77% | -6.06% | 2.69% |
| 2023 | -4.18% | -0.27% | -5.54% | -9.22% | -2.35% | -28.61% |
| 2024 | 6.01% | 5.65% | 0.03% | 1.02% | -3.35% | -2.71% |
| 2025 | 99.33% | 96.36% | 76.73% | 77.95% | 50.99% | 30.68% |
| 2026 | 24.50% | 11.38% | 4.15% | 15.06% | -6.21% | 11.59% |

## Conclusion

On available history, the literal VIDEO_ATR version changes return by -115.76 percentage points, net PF by -0.155, net win rate by -1.45 points and max equity DD by +9.38 points versus CURRENT. Best long-history PF among these fixed candidates: CURRENT; best return: CURRENT. These are descriptive ranks, not statistical proof or authorisation to replace the current EA.

## Limits

The 0.60% initial stop comes from the older supplied clip, not the current transcript. ATR6/+1R and EMA200/+0.5R are assumed exits, not known vendor settings. A bearish short candle is tested separately because the transcript explicitly requires a bullish body only for longs. Their 982%, 57%, PF 1.29 and 1,448 trades are advertised figures that were not independently verified, and their nine-year claim cannot be reproduced on this feed. Different position sizing or contract prices can alter return and PF. Older ticks are generated, not a nine-year real-tick test. These six configurations and recent windows were retrospectively compared; none is an untouched holdout or approved production winner. No daily loss cap or FTMO portfolio has been simulated here. Existing stop-modification rejections (market closed, invalid stops and any unmapped return codes) are counted, not mistaken for fills; the prior protective stop remains. Rejection reasons are retained per case in VERIFICATION.json and METRICS.json. Results reflect the inherited trailing implementation, not a repaired execution engine. Charts show independent closing balances, not a shared portfolio or floating equity; table equity DD comes from native MT5. Real-tick history quality for CURRENT: available 10% real ticks, 5y 15% real ticks, 1y 75% real ticks, 3m 100% real ticks. Costs are those charged by the native tester; historical changes to broker contract specifications or fee schedules were not separately reconstructed. The legacy cash-Sharpe diagnostic in the raw runner outputs is not used in this report; the displayed calendar-day return calculation includes all closing trades. The inherited entry logic has no stale-signal timeout. 1 long-history CURRENT entry was delayed beyond 09:35 NY: 2020-03-09 09:51:00-04:00. Its 09:30 signal and actual execution were recorded; no timing fix was introduced into this frozen comparison.

## Verification

Ten unit tests passed; original EX5 vs default-off research copy parity was checked trade-for-trade. Every completed signal, fill, candle body, EMA/DI condition, net P&L, commission, swap and streak was independently audited. No live terminal, installer, website or client EA was changed. Daily Sharpe uses realised calendar-day returns, zero nontrading days and sqrt(365.2425), including Sunday reopening exits. It is not the native MT5 report Sharpe or a forecast.