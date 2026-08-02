# EMA3 H1 versus H4 Walk-Forward Comparison

Requested period: 2025-08-02T02:10:09.993599+00:00 to 2026-08-02T02:10:09.993599+00:00
The first 75% of each broker-history sample selects the setup; the final 25% is untouched validation.
Every result uses one leg, structural pivot stops, historical spread and percentage risk.

| Symbol | Broker symbol | TF | Coverage | Selected setup | Validation trades | WR | PF | Net R | DD | Confidence | Robust |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|---|
| BTCUSD | BTCUSD | H1 | 365d | d10, ema200_slope/24, trail_start_1R_distance_1R | 31 | 35.5% | 0.92 | -1.52 | 10.38% | standard | no |
| BTCUSD | BTCUSD | H4 | 365d | d4, ema200_slope/6, fixed_4R | 9 | 33.3% | 1.44 | +2.48 | 2.97% | standard | yes |
| EURUSD | EURUSD.. | H1 | 364d | d10, ema200_slope/24, fixed_4R | 19 | 21.1% | 0.34 | -9.86 | 10.26% | standard | no |
| EURUSD | EURUSD.. | H4 | 364d | d4, none, trail_start_1R_distance_1R | 54 | 40.7% | 1.03 | +0.51 | 7.27% | standard | no |
| GBPJPY | GBPJPY.. | H4 | 364d | d6, none, fixed_4R | 40 | 32.5% | 1.00 | +0.01 | 8.13% | standard | no |
| US100 | NAS100U6 | H1 | 47d | d8, none, fixed_2R | 17 | 35.3% | 0.97 | -0.26 | 6.39% | limited | no |
| US100 | NAS100U6 | H4 | 47d | d5, none, fixed_3R | 7 | 57.1% | 1.27 | +0.81 | 2.86% | limited | yes |
| US30 | US30 | H1 | 364d | d6, ema200_slope/24, fixed_4R | 23 | 30.4% | 1.38 | +6.12 | 6.79% | standard | yes |
| US30 | US30 | H4 | 364d | d6, ema200_slope/6, fixed_4R | 0 | 0.0% | inf | +0.00 | 0.00% | limited | no |
| XAUUSD | XAUUSD.. | H1 | 364d | d10, ema200_slope/24, fixed_4R | 21 | 14.3% | 0.67 | -6.00 | 8.65% | standard | no |
| XAUUSD | XAUUSD.. | H4 | 364d | d5, ema200_slope/6, trail_start_1.5R_distance_1R | 14 | 57.1% | 1.80 | +4.82 | 2.97% | standard | yes |

## Standard-confidence robust ranking

| Rank | Symbol | TF | Validation trades | WR | PF | Net R | DD |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | XAUUSD | H4 | 14 | 57.1% | 1.80 | +4.82 | 2.97% |
| 2 | US30 | H1 | 23 | 30.4% | 1.38 | +6.12 | 6.79% |
| 3 | BTCUSD | H4 | 9 | 33.3% | 1.44 | +2.48 | 2.97% |

## Positive but limited-confidence results

- US100 H4: 7 validation trades, PF 1.27, +0.81R, DD 2.86%.

## Data limitations

- GBPJPY H1: no training candidate passed minimum 25 trades

US100 may resolve to the broker's current Nasdaq futures contract. Its result must not be compared
as equal-confidence with instruments that have the full requested year.

Historical optimization is research, not a guarantee. Forward demo validation is required before
changing the live worker's symbol or timeframe.
