# Noise Boundary VWAP Momentum - raw MT5 results

This is an unoptimized reconstruction of the published Zarattini-Aziz-Barbon final model. US500 is the closest Exness proxy for SPY; USTEC is included only as a fixed-rule transfer test.

| Symbol | Window | Net P/L | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| US500 | latest-1y | $-1,026.89 | -10.27% | 0.86 | 37.21% | 15.18% | 215 | -2.68 | -0.66 |
| US500 | recent-3y | $-615.39 | -6.15% | 0.97 | 37.40% | 23.87% | 639 | -0.54 | -0.22 |
| US500 | full-5y | $-451.41 | -4.51% | 0.99 | 37.53% | 28.21% | 1079 | -0.23 | -0.15 |
| USTEC | latest-1y | $+564.38 | +5.64% | 1.09 | 39.80% | 12.34% | 201 | 1.45 | 0.45 |
| USTEC | recent-3y | $+2,783.42 | +27.83% | 1.14 | 40.00% | 17.69% | 590 | 2.24 | 1.20 |
| USTEC | full-5y | $+4,986.25 | +49.86% | 1.14 | 39.28% | 17.66% | 1026 | 2.17 | 1.83 |

## Raw verdict

US500 FAILS. The closest available S&P 500 CFD proxy is negative in the latest year, recent three years and full five years. It does not reproduce the paper's SPY edge with Exness CFD prices, tick-volume VWAP and native trading costs.

USTEC PASSES THE RAW RESEARCH SCREEN, but only as a pipeline candidate. It is positive in all three windows and retains a strong MT5 Sharpe ratio, while PF remains a weak 1.09-1.14 and drawdown reaches 17.69%. The correct next action is a locked Calyx pipeline on USTEC only; it is not ready for system integration or demo deployment.

## Fidelity notes

- 14 prior regular NYSE sessions and volatility multiplier 1.0.
- 30-minute decisions from 10:00 through 15:30 New York; forced flat at 16:00.
- Gap-adjusted noise bands and HLC3 session VWAP confirmation.
- Dynamic 2% daily-volatility target, capped at 4x notional, as published.
- MT5 broker tick volume substitutes for consolidated exchange volume, so VWAP is not perfectly equivalent to SPY VWAP.

No website, BAT, installer, recommended-system or active-portfolio file was changed.
