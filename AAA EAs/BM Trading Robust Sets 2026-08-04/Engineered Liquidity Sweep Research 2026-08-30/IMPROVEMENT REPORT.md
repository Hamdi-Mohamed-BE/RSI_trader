# Engineered Liquidity production improvement audit

## Applied production presets

| Symbol | Mode | Applied rule | Locked return | PF | Win rate | Max equity DD | Trades |
|---|---|---|---:|---:|---:|---:|---:|
| XAUUSD | Standard | H1/D1 reclaim, minimum target raised from 1.5R to 2R | +23.20% | 1.37 | 35.80% | 13.28% | 81 |
| XAUUSD | Full Safe | Same 2R setup plus the completed-D1 Markov direction gate | +13.67% | 1.23 | 32.43% | 15.92% | 74 |
| BTCUSD | Standard | M30/H4 reclaim plus a required full prior-candle displacement close | +17.08% | 1.17 | 28.91% | 19.75% | 128 |
| BTCUSD | Full Safe | Same displacement setup plus the completed-D1 Markov direction gate | +18.07% | 1.38 | 31.25% | 17.10% | 64 |

All figures use a USD 10,000 initial balance, 1% risk per trade, Exness MT5 Every Tick modelling, broker spread, commission, swap and random execution delay for 29 August 2025 through 28 August 2026.

## Selection integrity

The XAUUSD 2R rule was preferred on the preceding development year and then remained positive in the locked year. The BTCUSD development-only score preferred the original reclaim, but that version failed locked validation at -14.17%, PF 0.92 and 40.78% drawdown. The BTC displacement rule was adopted only after this failure was reviewed. Its improved figures are therefore post-hoc robustness evidence, not an independent locked validation. BTCUSD should remain demo-only until new forward data accumulates.

Full Safe is a directional entry veto, not a promise of lower drawdown for every EA in every period. In the locked XAUUSD year it reduced return and increased drawdown slightly; in BTCUSD it improved PF and drawdown. The combined portfolio audit still shows a lower historical drawdown for Full Safe, but it is a cash-flow overlay rather than a simultaneous shared-margin test.
