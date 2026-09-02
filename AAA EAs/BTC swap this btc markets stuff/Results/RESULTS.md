# BTC spot–CME futures basis validation

The model was selected only on the development period and then frozen for the locked validation period.
The Yahoo continuous futures series is a screening proxy, not institutional execution evidence.

| Version | Period | Trades | Return | PF | Win rate | Max DD | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Directional | Development | 7 | +4.73% | 3.33 | 57.14% | 1.96% | 2.74 | 2.41 |
| Directional | Locked validation | 13 | +2.87% | 1.60 | 53.85% | 2.23% | 1.30 | 1.29 |
| Directional | Full legacy | 20 | +7.74% | 2.11 | 55.00% | 2.23% | 1.94 | 3.47 |
| Hedged | Development | 7 | +0.54% | 2.20 | 57.14% | 0.33% | 2.26 | 1.64 |
| Hedged | Locked validation | 13 | +3.14% | 6.36 | 69.23% | 0.41% | 4.51 | 7.62 |
| Hedged | Full legacy | 20 | +3.70% | 4.53 | 65.00% | 0.41% | 3.84 | 8.97 |

## Important limitation

CME launched 24/7 crypto futures trading on 2026-05-29. The historical weekend-reopen premise therefore no longer exists in the same form.
The present-day maintenance-pause variant needs licensed, contract-level CME and spot data before it can be judged.
