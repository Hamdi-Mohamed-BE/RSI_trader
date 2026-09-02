# Decision

Do not deploy the historical weekend-reopen strategy live.

The locked historical test was positive, but the evidence contains only 13 untouched validation trades. More importantly, CME expanded cryptocurrency futures to 24/7 trading on 29 May 2026, so the approximately 50-hour Friday-to-Sunday closure that created the signal no longer exists.

## Best historical reconstruction

The market-neutral version trades CME futures against a spot leg and deducts 32 basis points per round trip.

| Period | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development | +0.54% | 2.20 | 57.14% | 0.33% | 7 | 2.26 | 1.64 |
| Locked validation | +3.14% | 6.36 | 69.23% | 0.41% | 13 | 4.51 | 7.62 |
| Full legacy period | +3.70% | 4.53 | 65.00% | 0.41% | 20 | 3.84 | 8.97 |

The 10,000-trial bootstrap of the 20 full-period trades produced a +1.21% P5 return, +3.67% median return, +6.33% P95 return, 0.92% P95 drawdown, and 0.57% loss probability. These figures describe resampling uncertainty only; they cannot solve the obsolete market premise or the small sample.

## Architecture decision

Python is the correct primary implementation because this is a synchronized two-market strategy with contract rolls and separate execution venues. MT5 could later be used only as an execution bridge. A current maintenance-window study needs individual CME BTC or MBT contracts plus timestamp-aligned executable spot quotes from a licensed source such as Databento/CME and a real spot venue.
