# US100 Asia–London Continuation Research Report

## Locked interpretation

- Asia: 18:00 previous day–03:00 New York.
- London: 03:00–09:30 New York.
- First New York range: 09:30–09:45 New York.
- Direction: sign of the move from the Asia open to the 09:30 New York open.
- Bullish sessions compare the New York range high to the Asia high; bearish sessions use the symmetric low-to-low comparison.
- Entry: market at 09:45 in the continuation direction.
- M1 same-bar ambiguity is resolved against the strategy: stop before target.

## Broker units

- `USTEC` tick size: `0.01` index point.
- 2,000 broker ticks: `20.00` index points.
- The original user threshold is therefore 20.00 index points.

## Selected configuration

- proximity_threshold: `200.0`
- minimum_trend: `50.0`
- require_london_agreement: `False`
- direction_mode: `long`
- maximum_opening_range: `400.0`
- stop_range_multiple: `1.0`
- minimum_stop_points: `40.0`
- reward_risk: `4.0`
- trailing_mode: `be_1r`
- exit_minute: `960`

## Full-period result

- Trades: 498
- Return at 1% risk: 30.25%
- Profit factor: 1.13
- Win rate: 32.13%
- Closed-balance maximum drawdown: 20.02%
- Mean trade: 0.062R

## Untouched 2025–2026 holdout

- Trades: 141
- Return at 1% risk: -16.12%
- Profit factor: 0.77
- Win rate: 29.79%
- Closed-balance maximum drawdown: 19.74%

## Limitations

- This is an M1 broker-history research test, not an exchange-tick reconstruction.
- The drawdown is based on closed trade balance; MT5 tick replay is required for exact floating-equity drawdown.
- The 2025–2026 holdout was not used to choose the configuration.
- A final EA preset should only be deployed after an independent MT5 tester run and cross-broker check.
