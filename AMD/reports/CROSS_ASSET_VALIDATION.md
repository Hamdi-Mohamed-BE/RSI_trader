# Expanded AMD Cross-Asset Validation

- Period: 2025-07-30 to 2026-07-30
- Source: connected MT5 account, MEXAtlantic-Demo
- Starting balance: $1,000 per symbol
- Risk: 3% of current balance per trade
- Entry model: confirmed M5 sweep/reclaim or breakout/retest
- Target: 1.5R
- Management: at +0.30R, stop advances to +0.15R

## Exact XAU-selected configuration

This is the configuration now stored in `.env`, including its absolute
volatility and relative Asia-range filters.

| Symbol | Trades | Win rate | PF | Net R | Max DD | Ending balance | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| XAUUSD | 67 | 85.07% | 1.97 | +10.70R | 6.66% | $1,359.44 | Keep |
| US30 | 19 | 84.21% | 2.08 | +3.45R | 5.06% | $1,104.11 | Research only |
| US100 / NAS100U6 | 7 | 57.14% | 0.62 | -1.05R | 8.32% | $966.68 | Reject |
| BTCUSD | 47 | 61.70% | 0.74 | -4.20R | 23.55% | $868.17 | Reject |
| ETHUSD | 5 | 80.00% | 1.87 | +0.95R | 3.00% | $1,027.40 | Insufficient sample |
| EURUSD | 0 | 0.00% | 0.00 | 0.00R | 0.00% | $1,000.00 | XAU gate incompatible |
| GBPJPY | 0 | 0.00% | 0.00 | 0.00R | 0.00% | $1,000.00 | XAU gate incompatible |
| XAGUSD | 19 | 31.58% | 0.28 | -9.40R | 28.71% | $748.28 | Reject |
| XPTUSD | 14 | 14.29% | 0.03 | -11.70R | 29.99% | $700.10 | Reject |

## Chronological robustness

The year was divided into 60% training, 20% validation and 20% final test.

| Symbol | Training | Validation | Final test |
|---|---|---|---|
| XAUUSD | 21 trades, PF 1.70, +2.40R | 19 trades, PF 2.51, +3.25R | 27 trades, PF 1.91, +5.05R |
| US30 | 6 trades, PF 2.01, +1.10R | 10 trades, PF 4.09, +3.05R | 3 trades, PF 0.29, -0.70R |
| BTCUSD | 25 trades, PF 0.50, -5.05R | 9 trades, PF 1.61, +1.95R | 13 trades, PF 0.75, -1.10R |
| ETHUSD | 1 trade, +0.15R | 3 trades, PF 1.58, +0.65R | 1 trade, +0.15R |

US100 history begins on 2026-06-15 because the connected broker exposes a
dated NAS100U6 futures contract. Its seven trades are not a one-year sample.

## Cross-asset normalized-gate diagnostic

Removing the XAU-specific absolute ATR gate increased frequency but destroyed
the edge. This diagnostic is saved as `.env.cross_asset` and remains dry-run
only.

| Symbol | Trades | PF | Max DD | Ending balance |
|---|---:|---:|---:|---:|
| XAUUSD | 100 | 1.51 | 9.46% | $1,354.44 |
| US30 | 119 | 0.49 | 48.15% | $518.47 |
| US100 / NAS100U6 | 7 | 0.62 | 8.32% | $966.68 |
| BTCUSD | 116 | 0.69 | 44.04% | $674.59 |
| ETHUSD | 111 | 0.40 | 66.81% | $331.86 |
| EURUSD | 157 | 0.39 | 87.62% | $139.99 |
| GBPJPY | 148 | 0.27 | 83.14% | $169.37 |
| XAGUSD | 103 | 0.54 | 47.74% | $546.09 |
| XPTUSD | 121 | 0.06 | 92.87% | $72.23 |

## Decision

Keep XAUUSD as the only default symbol. Do not add another market until a
symbol-specific configuration passes chronological selection and a fresh
forward sample. More signals alone did not improve this strategy.
