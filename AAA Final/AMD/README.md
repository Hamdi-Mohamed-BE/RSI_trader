# AMD Session Bot

An XAUUSD MT5 research implementation of mechanical
Accumulation-Manipulation-Distribution ideas.

## Current status

**Not approved for live trading.**

The original model looked strong in the latest year but failed the immediately
preceding year. A second rebuild added:

- ATR normalized to its own trailing history instead of a fixed gold-price era;
- Asia-range normalization;
- directional candle, body, close-location and stop-size filters;
- H1 EMA trend alignment;
- sweep followed by an optional M5 market-structure shift;
- six chronological half-year development folds;
- a separate untouched-year validation;
- a hard live-execution approval flag.

None of the immediate-entry, H1-aligned, or MSS variants produced a durable
positive edge across the full three-year broker sample.

| Test | Trades | Win rate | PF | Net R | Max DD |
|---|---:|---:|---:|---:|---:|
| Best 2024-2026 development model | 76 | 84.21% | 2.18 | +14.25R | 8.73% |
| Same frozen model, untouched 2023-2024 | 43 | 44.19% | 0.12 | -21.15R | 47.81% |
| Best full three-year rebuild candidate | 119 | 69.75% | 0.72 | -6.90R | 47.81% |

An additional v2 research engine now models a stricter AMD reversal:

1. sweep the Asia high or low and close back inside;
2. break local M5 structure;
3. print a directional displacement candle and fair-value gap;
4. fill a limit order on the gap retest within 30 minutes;
5. place the stop beyond the sweep and target 2R.

This removed the misleading early break-even behavior. It materially improved
the result, but is still **not live-approved**:

| Frozen v2 test | Trades | Win rate | PF | Net R | Max DD |
|---|---:|---:|---:|---:|---:|
| Development, 2024-2026 | 35 | 45.71% | 1.70 | +13.28R | 11.94% |
| Untouched holdout, 2023-2024 | 9 | 44.44% | 1.54 | +3.00R | 8.73% |
| Extra older stress, 2020-2023 | 45 | 37.78% | 1.11 | +5.00R | 19.42% |
| Combined six years, 2020-2026 | 89 | 41.57% | 1.38 | +21.28R | 22.04% |

The older aggregate stayed positive, but 2022-2023 alone produced `-4R`,
`PF 0.73`, and `19.42%` drawdown. Adding New York raised frequency but reduced
development PF to `1.54`, raised drawdown to `19.30%`, and reduced positive
half-year folds from `4/4` to `3/4`. These are rejection results, not deployable
defaults.

The high recent win rate was mostly produced by small `+0.15R` protected-stop
exits. One full `-1R` loss needs almost seven such exits to recover, so win rate
alone materially overstated quality.

`.env` is deliberately set to:

```text
ENABLE_TRADING=false
DRY_RUN=true
MODEL_APPROVED=false
```

Even if the first two flags are changed, live execution remains blocked while
`MODEL_APPROVED=false`.

## Research profile

The paper-only profile keeps the least-bad, conceptually defensible candidate
for continued observation:

1. Build the full-wick Asia range from 00:00-08:00 UTC.
2. Scan the first three London hours for an M5 liquidity sweep and close back
   inside the range.
3. Trade fades only; breakout/retest continuation is disabled.
4. Allow signals only when 5-day ATR is 0.65-1.00 times its prior 30-day median.
5. Allow Asia ranges only when they are 0.60-1.00 times their prior 20-day
   median.
6. Enter no earlier than the next M1 candle, target 2R, and at +0.30R protect
   +0.15R.
7. Take at most one signal per day and force-exit at 21:00 UTC.

This profile is for forward research, not a recommendation to trade.

## Run

```powershell
cd "C:\Users\hama101\Desktop\geek\ai trader\AMD"
uv sync
uv run amd-bot backtest --days 365
uv run amd-bot live --once
```

`run_live.bat` is safe: it uses the dry-run flags above and submits no order.

## Validation commands

```powershell
uv run python -m amd_bot.article_walk_forward
uv run python -m amd_bot.article_oos_validate
uv run python -m amd_bot.article_rebuild_v2
uv run python -m amd_bot.article_v2_research
uv run python -m amd_bot.article_v2_stress
uv run pytest -q
```

## Reports

- `reports/robust_rebuild/development_search.csv`
- `reports/robust_rebuild/development_winner.json`
- `reports/robust_rebuild/unseen_2023_2024_metrics.csv`
- `reports/robust_rebuild/unseen_2023_2024_monthly.csv`
- `reports/robust_rebuild/unseen_2023_2024_trades.csv`
- `reports/robust_rebuild/frozen_model_validation.json`
- `reports/robust_rebuild/three_year_rebuild.csv`
- `reports/robust_rebuild/three_year_winner.json`
- `reports/robust_rebuild/ROBUSTNESS_AUDIT.md`
- `reports/amd_v2/REPORT.md`
- `reports/amd_v2/EXTENDED_STRESS.md`
- `reports/amd_v2/frozen_model.json`
- `reports/amd_v2/older_stress_metrics.csv`
- `reports/amd_v2/session_extension_metrics.csv`
- `reports/amd_v2/six_year_metrics.csv`

## Operational safeguards

- connects to the account already open in MT5;
- dynamically discovers the broker's gold symbol;
- uses broker-compatible filling modes;
- sizes down to the broker volume step without exceeding configured risk;
- uses completed M5 signals and next-M1 execution;
- permits at most one bot trade per day;
- manages only positions carrying its own magic number;
- rejects live execution for an unapproved model.

Historical results are not a guarantee of future performance.
