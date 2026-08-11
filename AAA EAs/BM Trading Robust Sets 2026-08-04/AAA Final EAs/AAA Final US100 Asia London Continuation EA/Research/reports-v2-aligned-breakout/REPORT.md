# US100 Asia–London Continuation V2

This version tests two wording-faithful alternatives: both Asia and London must align, and post-09:45 opening-range breakout entry.

## Selected signal

- proximity_threshold: `200.0`
- minimum_trend: `50.0`
- trend_definition: `total_move`
- proximity_relation: `absolute`
- direction_mode: `long`
- maximum_opening_range: `200.0`

## Selected execution

- entry_mode: `opening_range_breakout`
- entry_cutoff_minute: `690`
- stop_range_multiple: `1.0`
- minimum_stop_points: `40.0`
- reward_risk: `3.0`
- trailing_mode: `be_1r`
- exit_minute: `960`

## Full period

- Trades: 338
- Return: 58.33%
- PF: 1.33
- Win rate: 37.87%
- Closed-balance DD: 11.87%

## Untouched 2025–2026 holdout

- Trades: 90
- Return: -4.38%
- PF: 0.90
- Win rate: 34.44%
- Closed-balance DD: 11.87%

No EA should be deployed if the untouched holdout is not viable.
