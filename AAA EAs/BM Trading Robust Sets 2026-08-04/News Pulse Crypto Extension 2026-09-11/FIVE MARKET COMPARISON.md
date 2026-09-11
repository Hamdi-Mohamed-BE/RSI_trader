# News Pulse five-market comparison — review only

No BAT, website profile, active MT5 chart or production EA was changed by this research.

## Recommended order

1. **XAGUSD** — strongest return, profit factor and execution-stress stability.
2. **XAUUSD** — best low-drawdown consistency after XAG and extremely stable under random delay.
3. **BTCUSD candidate** — materially improved by the tighter geometry; passed the locked quarter and verified replay, but still needs demo-forward validation.
4. **EURUSD** — lower return than BTC but mature and exceptionally stable under execution stress.
5. **ETHUSD candidate** — highest raw crypto return, but the largest random-delay haircut and Monte Carlo drawdown; most execution-sensitive candidate.

## Comparable one-year results

Period: 2025-09-01 through 2026-09-01. MT5 Every Tick, Exness broker costs, hard 0.75% risk per enabled stop and up to 1.50% planned event risk in two-sided mode.

| Rank | Market | Direction | Entry / stop | Trail | Lead / forced exit | Return | PF | Win rate | Max DD | Trades | Random-delay return / PF | MC P5 return | MC P95 DD |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | XAGUSD | two-sided | 0.08 / 0.08 | 0.20 | 30s / 60s | +221.04% | 13.46 | 62.16% | 2.52% | 37 | +216.93% / 11.35 | +127.73% | 4.81% |
| 2 | XAUUSD | two-sided | 6 / 6 | 15 | 30s / 60s | +55.04% | 9.00 | 63.64% | 1.79% | 33 | +57.53% / 9.43 | +30.35% | 3.14% |
| 3 | BTCUSD | two-sided | 75 / 75 | 112.5 | 30s / 60s | +91.07% | 6.98 | 74.42% | 3.40% | 43 | +61.32% / 5.53 | +55.63% | 4.49% |
| 4 | EURUSD | two-sided | 0.0006 / 0.0006 | 0.0015 | 30s / 60s | +50.46% | 7.81 | 67.65% | 2.85% | 34 | +50.71% / 7.59 | +28.86% | 3.11% |
| 5 | ETHUSD | two-sided | 3 / 3 | 4.5 | 30s / 60s | +193.89% | 6.77 | 66.67% | 3.52% | 45 | +109.04% / 5.75 | +110.84% | 7.48% |

## Current verified-calendar replay

Period: 2026-06-12 through 2026-09-10. The generated FXMacroData manifest contains seven exact NFP/CPI/FOMC timestamps. The current v2.13 EA processed all seven releases for both crypto symbols.

| Market | Return | PF | Win rate | Max DD | Trades | History quality | Processed events |
|---|---:|---:|---:|---:|---:|---:|---:|
| XAGUSD | +93.34% | 43.43 | 88.89% | 2.51% | 9 | 100% | 7/7 |
| XAUUSD | +35.32% | 20.82 | 77.78% | 1.78% | 9 | 100% | 7/7 |
| BTCUSD | +27.67% | 22.98 | 87.50% | 1.12% | 8 | 100% | 7/7 |
| EURUSD | +24.90% | 12.65 | 77.78% | 1.37% | 9 | 100% | 7/7 |
| ETHUSD | +27.23% | 12.92 | 75.00% | 1.38% | 8 | 100% | 7/7 |

## Decision

- **BTCUSD:** worth a demo-forward candidate at the selected settings. Do not promote directly to real capital.
- **ETHUSD:** demo-forward only and lower priority than BTC because of its larger execution sensitivity.
- Running all five together would create up to **7.50% planned exposure around the same USD release**, before gaps and slippage. The five bots must not be treated as independent diversification.
- If either crypto candidate is eventually approved, use a shared News Pulse portfolio cap rather than adding another independent 1.50% event budget.

The one-year event schedule provides more observations for selection, while the seven-event FXMacroData replay verifies exact current timestamps. Neither sample is large enough to guarantee future profitability.
