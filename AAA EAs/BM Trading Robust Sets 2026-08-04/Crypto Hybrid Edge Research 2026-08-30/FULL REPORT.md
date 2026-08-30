# Crypto hybrid edge — MT5 walk-forward validation

Published evidence supports both momentum and conditional intraday reversal in liquid cryptocurrencies. This test compared trend pullbacks, confirmed volatility extremes and breakout-retests using fixed 0.5R, 0.7R and 1R targets.

| Symbol | Selected strategy | Development return / PF | Locked return / PF | Win rate | Equity DD | Trades | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| BTCUSD | trend-liquid-r10 | +9.41% / 1.05 | +0.01% / 1.00 | 50.79% | 15.07% | 443 | REJECT |
| ETHUSD | revert-all-r10 | +8.97% / 1.71 | -19.88% / 0.58 | 37.65% | 22.02% | 85 | REJECT |

- Exness MT5 Trial 16, native Every Tick model, random delay, spread, commission and swap included.
- $10,000 initial balance and 1% equity risk per trade.
- Development: 2024-08-29 to 2025-08-28; untouched locked test: 2025-08-29 to 2026-08-28.
- Only BTCUSD and ETHUSD are tradable crypto CFDs on the connected Exness account.
- No active BAT or website file was changed.
