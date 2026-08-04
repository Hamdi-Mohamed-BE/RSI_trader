# EMA3 Timeframe Walk-Forward Comparison

Requested period: 2026-07-05T12:58:14.623539+00:00 to 2026-08-04T12:58:14.623539+00:00
The first 75% of each broker-history sample selects the setup; the final 25% is untouched validation.
Every result uses one leg, structural pivot stops, historical spread and percentage risk.

| Symbol | Broker symbol | TF | Coverage | Selected setup | Validation trades | WR | PF | Net R | DD | Confidence | Robust |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|---|
| XAUUSD | XAUUSD.. | M15 | 30d | d6, none, fixed_1R | 54 | 38.9% | 0.70 | -6.20 | 7.23% | limited | no |

## Standard-confidence robust ranking

No result passed the minimum untouched-validation rules.

## Data limitations

- XAUUSD M1: no training candidate passed minimum 120 trades
- XAUUSD M5: no training candidate passed minimum 60 trades

US100 may resolve to the broker's current Nasdaq futures contract. Its result must not be compared
as equal-confidence with instruments that have the full requested year.

Historical optimization is research, not a guarantee. Forward demo validation is required before
changing the live worker's symbol or timeframe.
