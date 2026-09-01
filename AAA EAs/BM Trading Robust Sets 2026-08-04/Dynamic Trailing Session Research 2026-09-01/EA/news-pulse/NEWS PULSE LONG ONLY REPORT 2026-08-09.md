# News Pulse long-only validation — 9 August 2026

The long-only configuration uses News Pulse v2.11 with the buy side enabled and sell side disabled. NFP, CPI and FOMC remain enabled.

## Applied inputs

- XAUUSD M1
- Buy side: enabled
- Sell side: disabled
- 1% planned risk
- Place the buy-stop 30 seconds before release
- $6 entry offset and $6 stop
- Start trailing at 1.5R with a $15 trailing distance
- Force-close at 60 seconds after release

## Exact generated-tick test

Exness XAUUSD, 7 August 2025 through 8 August 2026, USD 10,000 initial balance, 99% history quality.

| Statistic | Result |
|---|---:|
| Final balance | $16,251.23 |
| Net profit / return | $6,251.23 / +62.51% |
| Profit factor | 41.00 |
| Maximal equity drawdown | $225.72 / 1.46% |
| Maximal balance drawdown | $105.66 / 1.03% |
| Win rate | 84.21% |
| Wins / losses | 16 / 3 |
| Trades | 19 |
| Gross profit | $6,407.51 |
| Gross loss | -$156.28 |
| Largest win | $1,177.00 |
| Largest loss | -$103.84 |

## Random execution-delay stress

The same settings returned +62.66%, PF 42.76, 89.47% wins, 1.98% maximal equity drawdown and 19 trades.

These tests use ticks reconstructed from Exness M1 history rather than broker real-tick history. The sample contains only 19 trades and came from a bullish gold year, so PF 41.00 is not a reliable long-term expectation or a guarantee of live profit.
