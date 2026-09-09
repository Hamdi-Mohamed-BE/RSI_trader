# Step 1B — Raw Cross-Asset Check

## Goal

Apply the paper's main, unoptimized rest-of-day (ROD) rule to the other Calyx markets using the market hours stated by the paper.

## Paper session definitions

- Gold: 08:20–13:30 Eastern time; enter at 13:00.
- Silver: 08:25–13:25 Eastern time; enter at 12:55.
- Euro FX and British pound: 07:20–14:00 Eastern time; enter at 13:30.
- Dow Jones: 09:30–16:00 Eastern time; enter at 15:30.
- GBPJPY uses the currency-futures clock as an explicit cross-rate extension; the paper tested GBP and JPY futures separately, not GBPJPY.
- BTC was not tested because a 24/7 cryptocurrency has no paper-defined cash-market close.

## Results

| Period | Asset | Return | Net P/L | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Expected payoff |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 years | XAUUSD | -1.83% | -$183.23 | 0.81 | 48.78% | 2.22% | 449 | -5.00 | -0.82 | -$0.41 |
| 3 years | XAGUSD | -13.12% | -$1,311.56 | 0.21 | 29.81% | 13.20% | 520 | -5.00 | -0.99 | -$2.52 |
| 3 years | EURUSD | -8.68% | -$867.94 | 0.60 | 43.54% | 9.00% | 774 | -5.00 | -0.96 | -$1.12 |
| 3 years | GBPUSD | -9.53% | -$953.08 | 0.57 | 42.19% | 9.92% | 775 | -5.00 | -0.96 | -$1.23 |
| 3 years | GBPJPY* | -11.26% | -$1,125.98 | 0.52 | 42.97% | 11.38% | 775 | -5.00 | -0.99 | -$1.45 |
| 3 years | US30† | -6.63% | -$663.40 | 0.70 | 46.22% | 7.40% | 450 | -5.00 | -0.89 | -$1.47 |
| 1 year | XAUUSD | -0.33% | -$32.81 | 0.74 | 51.85% | 0.55% | 54 | -5.00 | -0.59 | -$0.61 |
| 1 year | XAGUSD | +0.15% | +$15.33 | 1.21 | 48.72% | 0.36% | 39 | 5.78 | 0.43 | +$0.39 |
| 1 year | EURUSD | -3.20% | -$319.91 | 0.60 | 40.70% | 3.37% | 258 | -5.00 | -0.95 | -$1.24 |
| 1 year | GBPUSD | -4.08% | -$407.61 | 0.49 | 40.15% | 4.21% | 259 | -5.00 | -0.97 | -$1.57 |
| 1 year | GBPJPY* | -4.38% | -$437.76 | 0.46 | 42.47% | 4.42% | 259 | -5.00 | -0.99 | -$1.69 |
| 1 year | US30† | -2.86% | -$285.79 | 0.59 | 44.08% | 3.40% | 152 | -5.00 | -0.84 | -$1.88 |

\* GBPJPY is an extension, not a directly tested instrument in the paper.

† The Exness US30 feed does not consistently provide an executable final 30-minute cash-session window. Monday and Friday were removed, but 18 irregular early-close sessions still had delayed exits. US30 is therefore exploratory and not a clean paper replication. It is negative regardless.

## Controls and limitations

- 1% maximum equity risk through a 10× M15 ATR emergency stop.
- No TP, trailing, breakeven, trend/regime condition, session optimization, or parameter search.
- Native MT5 Every Tick with broker spread, commission, swap and random execution delay.
- XAU Monday and US30 Monday/Friday were skipped because this broker cannot execute the complete paper window on those sessions.
- Recent XAU/XAG trade counts are limited because their calculated 1% volume sometimes falls below the broker's minimum lot. The EA skips those trades rather than exceeding the selected risk.
- History quality: 98–100%.

## Verdict

The raw edge did not transfer to these CFD instruments. XAG has a small positive last-year result, but it is only 39 trades and is overwhelmed by the three-year loss. None qualifies for the recommended portfolio in raw form.
