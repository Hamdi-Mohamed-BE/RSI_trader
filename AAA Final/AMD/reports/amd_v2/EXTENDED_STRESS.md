# AMD v2 Extended Stress Test

The v2 parameters were frozen before these extra checks.

## Older broker history

| Sample | Trades | Win rate | PF | Net R | Return | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2020-07-30_to_2023-07-30 | 45 | 37.78% | 1.11 | +5.00 | +11.52% | 19.42% |
| 2020-07-30_to_2021-07-30 | 4 | 50.00% | 1.89 | +2.00 | +5.72% | 3.00% |
| 2021-07-30_to_2022-07-30 | 19 | 47.37% | 1.60 | +7.00 | +21.06% | 8.73% |
| 2022-07-30_to_2023-07-30 | 22 | 27.27% | 0.73 | -4.00 | -12.87% | 19.42% |

The frozen model is positive over the older three-year aggregate, but the 2022-2023 regime loses money and exceeds the preferred 15% drawdown ceiling.

## Session-extension check

| Variant | Trades | Win rate | PF | Net R | Return | Max DD | Positive folds |
|---|---:|---:|---:|---:|---:|---:|---:|
| London only | 35 | 45.71% | 1.70 | +13.28 | +43.82% | 11.94% | 4/4 |
| New York only | 25 | 36.00% | 0.95 | +0.00 | -2.01% | 19.49% | 3/4 |
| London + New York, max 1/day | 55 | 43.64% | 1.54 | +15.28 | +50.17% | 19.30% | 3/4 |
| London + New York, max 2/day | 60 | 41.67% | 1.39 | +13.28 | +41.17% | 21.72% | 3/4 |

New York adds frequency but weakens stability. The max-one two-session variant raises trades from 35 to 55, while PF falls from 1.70 to 1.54, drawdown rises from 11.94% to 19.30%, and positive folds fall from 4/4 to 3/4.

## Combined six-year result

| Trades | Win rate | PF | Net R | Return | Max DD |
|---:|---:|---:|---:|---:|---:|
| 89 | 41.57% | 1.38 | +21.28 | +73.87% | 22.04% |

## Decision

**REJECTED FOR LIVE TRADING.** The v2 reversal is materially better than the original model, but its sample remains small and the older stress sample includes a losing regime (aggregate PF 1.11, max DD 19.42%). Keep it paper-only.
