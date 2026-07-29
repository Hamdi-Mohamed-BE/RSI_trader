# PF >= 3 Asian-breakout basket

Test window: 2026-05-29 through 2026-07-29  
Starting balance: $1,000  
Risk model: 3% of current balance per entered trade  
Data: broker-recorded MT5 M1 bars with recorded spread

| Symbol | Entry | Stop | Target/exit | Trades | Win rate | PF | Max DD | Ending balance |
|---|---|---|---|---:|---:|---:|---:|---:|
| XAUUSD | Confirmed close | Midpoint | 3R cap; trail from 2R at 0.5R | 18 | 77.8% | 4.48 | 5.3% | $1,493.85 |
| BTCUSD | Confirmed close | Midpoint | 1R cap; trail from 0.5R at 0.5R | 27 | 85.2% | 4.66 | 5.3% | $1,330.39 |
| EURJPY | Mechanical OCO | Midpoint | 6R cap; trail from 2R at 1R | 13 | 61.5% | 4.32 | 9.2% | $1,591.24 |
| AUDCAD | Close + retest | Midpoint | 5R cap; trail from 2R at 1R | 12 | 75.0% | 6.22 | 5.7% | $1,376.28 |
| AUDCHF | Confirmed close | Midpoint | Fixed 1.5R | 17 | 76.5% | 3.54 | 7.6% | $1,276.53 |
| GBPJPY | Confirmed close | Opposite edge | Fixed 0.5R | 26 | 84.6% | 4.86 | 5.1% | $1,271.54 |

Combined event-sequenced result:

- Trades: 113
- Win rate: 78.8%
- Profit factor: 4.53
- Net result: 67.83R
- Ending balance: $6,991.41
- Maximum realized drawdown: 8.91%
- Maximum concurrent positions: 5
- Maximum planned risk at 3% each: 15%

The combined balance is not the sum of the individual ending balances. Trades
are sequenced by timestamp against one shared compounded account. Drawdown is
based on realized balance only; it does not reconstruct simultaneous floating
equity. The result is in-sample and highly selection-sensitive. Freeze these
settings and run an unseen walk-forward period before live use.
