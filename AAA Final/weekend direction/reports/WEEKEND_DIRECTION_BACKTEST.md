# XAUUSD Friday Weekend-Direction Backtest

## Rejected selected ML model

| Sample | Trades | Win rate | PF | Net | Max DD |
|---|---:|---:|---:|---:|---:|
| Development | 38 | 34.21% | 1.711 | +17.51R | 5.00R |
| Untouched holdout | 13 | 15.38% | 0.248 | -13.46R | 13.90R |
| Full | 51 | 29.41% | 1.095 | +4.05R | 16.75R |

## Provisional momentum research

This mode follows strong Friday 24-hour momentum four minutes before the inferred close and exits at the first weekly reopen tick.

| Sample | Trades | Win rate | PF | Net | Max DD |
|---|---:|---:|---:|---:|---:|
| Development | 24 | 41.67% | 1.411 | +0.54R | 0.61R |
| Holdout | 21 | 80.95% | 5.780 | +8.69R | 1.52R |
| Full | 45 | 60.00% | 3.944 | +9.23R | 1.52R |

**Deployment verdict: NO_TRADE.** The ML model failed its untouched holdout. The momentum result is selection-biased and demo-only when explicitly enabled.

Gap losses are executed at unfavorable reopen prices. Historical M1 simulation is not a guarantee.
