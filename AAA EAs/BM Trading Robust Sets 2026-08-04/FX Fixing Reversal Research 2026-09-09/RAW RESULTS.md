# FX Fixing Reversal — raw CFD results

Status: **raw test complete; rejected; no production action**

## Paper and exact rules tested

Krohn, Mueller and Whelan's 2024 paper, *Foreign Exchange Fixings and Returns around the Clock*, documents predictable US-dollar movements around the Tokyo, ECB and London fixes. The raw rules were reproduced without optimization:

- Tokyo pre-fix: long USD from 17:00 New York on the prior day to 09:55 Tokyo.
- Tokyo post-fix: short USD from 09:55 Tokyo to 02:00 New York.
- ECB pre-fix: long USD from 02:00 New York to 14:15 Frankfurt.
- London post-fix: short USD from 16:00 London to 17:00 New York.
- The three-hour interval between the ECB and London fixes is not traded.
- All local clocks use daylight-saving-aware time zones.
- No stop, take-profit, trailing rule, regime filter or parameter search was introduced.

Source: https://onlinelibrary.wiley.com/doi/10.1111/jofi.13306

## Test context

| Field | Value |
|---|---|
| Broker data | Exness demo/read-only M5 |
| Test dates | 2021-09-01 to 2026-08-31 |
| Assets | EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCHF, USDCAD |
| Allocation | Equal weight; paper-style 1x notional |
| Cost tests | Gross, 50% of observed spread, 100% of observed spread |
| Missing spread bars | Replaced with each symbol's positive hour-of-day median |
| Swap/commission | Not added; the paper's cost test is spread-based |
| Production changes | None |

The raw result is already negative without swap. Adding any applicable rollover charge would not rescue it.

## Equal-weight seven-pair portfolio

Returns and drawdowns are reconstructed at portfolio level. PF and win rate pool component trades.

| Period | Cost | Return | Annualized | PF | Win rate | Max DD | Sharpe | Recovery | Trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 years | Gross | +16.52% | +3.01% | 1.05 | 50.48% | 6.95% | 0.58 | 2.38 | 31,895 |
| 5 years | 50% spread | -12.71% | -2.60% | 0.97 | 48.76% | 13.87% | -0.47 | -0.92 | 31,895 |
| 5 years | Full spread | **-34.60%** | -7.91% | **0.89** | **46.95%** | **34.60%** | **-1.52** | **-1.00** | **31,895** |
| 3 years | Full spread | -22.86% | -8.08% | 0.88 | 47.10% | 24.05% | -1.76 | -0.95 | 18,810 |
| 1 year | Full spread | -9.98% | -9.72% | 0.83 | 46.10% | 10.63% | -2.35 | -0.94 | 6,009 |

The gross PF is only 1.05. Half the observed spread makes it negative, and the latest year is negative even before spread.

## Five-year pair results — all four legs, full spread

| Pair | Return | PF | Win rate | Max DD | Sharpe | Recovery | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | -27.59% | 0.90 | 46.95% | 28.09% | -1.02 | -0.98 | 4,586 |
| GBPUSD | -28.68% | 0.91 | 47.06% | 28.84% | -0.93 | -0.99 | 4,486 |
| USDJPY | -39.98% | 0.88 | 47.54% | 40.02% | -1.24 | -1.00 | 4,514 |
| AUDUSD | -21.73% | 0.95 | 48.47% | 25.46% | -0.53 | -0.85 | 4,566 |
| NZDUSD | -53.04% | 0.86 | 46.66% | 53.33% | -1.68 | -0.99 | 4,589 |
| USDCHF | -50.78% | 0.81 | 44.55% | 50.78% | -2.16 | -1.00 | 4,557 |
| USDCAD | -12.14% | 0.95 | 47.42% | 18.21% | -0.51 | -0.67 | 4,597 |

No complete pair implementation is profitable after the full observed spread.

## Five-year fixing-leg breakdown — full spread

| Pair | Fixing leg | Return | PF | Win rate | Max DD | Sharpe | Trades |
|---|---|---:|---:|---:|---:|---:|---:|
| EURUSD | Tokyo pre | -16.04% | 0.62 | 41.37% | 16.63% | -2.52 | 996 |
| EURUSD | Tokyo post | -8.97% | 0.86 | 47.53% | 8.97% | -0.85 | 1,296 |
| EURUSD | ECB pre | +1.03% | 1.01 | 49.61% | 7.54% | 0.07 | 1,296 |
| EURUSD | London post | -6.23% | 0.93 | 48.30% | 7.64% | -0.45 | 998 |
| GBPUSD | Tokyo pre | -14.17% | 0.64 | 41.86% | 14.40% | -2.31 | 946 |
| GBPUSD | Tokyo post | -8.88% | 0.87 | 48.23% | 9.96% | -0.78 | 1,296 |
| GBPUSD | ECB pre | -1.05% | 1.00 | 48.34% | 9.82% | -0.02 | 1,297 |
| GBPUSD | London post | -7.84% | 0.91 | 48.89% | 8.69% | -0.55 | 947 |
| USDJPY | Tokyo pre | -13.46% | 0.80 | 47.40% | 20.01% | -1.25 | 960 |
| USDJPY | Tokyo post | -3.64% | 0.97 | 48.23% | 11.18% | -0.15 | 1,296 |
| USDJPY | ECB pre | +1.92% | 1.02 | 53.01% | 6.89% | 0.10 | 1,296 |
| USDJPY | London post | -29.38% | 0.62 | 39.40% | 29.52% | -2.42 | 962 |
| AUDUSD | Tokyo pre | -11.07% | 0.83 | 45.74% | 13.06% | -1.10 | 986 |
| AUDUSD | Tokyo post | +3.44% | 1.03 | 51.16% | 9.23% | 0.17 | 1,296 |
| AUDUSD | ECB pre | -0.73% | 1.00 | 49.19% | 9.30% | -0.00 | 1,297 |
| AUDUSD | London post | -14.28% | 0.87 | 46.71% | 15.82% | -0.79 | 987 |
| NZDUSD | Tokyo pre | -19.43% | 0.72 | 43.33% | 22.19% | -1.89 | 997 |
| NZDUSD | Tokyo post | -13.15% | 0.91 | 48.53% | 18.51% | -0.57 | 1,296 |
| NZDUSD | ECB pre | -10.19% | 0.94 | 48.65% | 11.33% | -0.37 | 1,297 |
| NZDUSD | London post | -25.28% | 0.76 | 44.94% | 25.76% | -1.52 | 999 |
| USDCHF | Tokyo pre | -28.49% | 0.43 | 36.49% | 28.55% | -4.54 | 981 |
| USDCHF | Tokyo post | -12.90% | 0.81 | 45.33% | 12.90% | -1.26 | 1,295 |
| USDCHF | ECB pre | -4.98% | 0.97 | 49.65% | 9.86% | -0.19 | 1,297 |
| USDCHF | London post | -16.84% | 0.80 | 44.82% | 17.38% | -1.25 | 984 |
| USDCAD | Tokyo pre | -7.66% | 0.76 | 44.56% | 8.09% | -1.39 | 1,001 |
| USDCAD | Tokyo post | -3.12% | 0.95 | 47.07% | 8.12% | -0.33 | 1,296 |
| USDCAD | ECB pre | +7.84% | 1.09 | 49.34% | 4.00% | 0.50 | 1,297 |
| USDCAD | London post | -8.93% | 0.88 | 48.26% | 9.90% | -0.72 | 1,003 |

USDCAD before the ECB fix is the best isolated leg, but it falls from +7.84%, PF 1.09 over five years to -1.45%, PF 0.97 over three years and -1.40%, PF 0.90 in the latest year. It is not a production candidate.

## Yearly stability — full-spread portfolio

| Year | Return | PF | Win rate | Max DD | Sharpe | Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 2021 partial | -3.11% | 0.86 | 47.78% | 3.23% | -2.36 | 2,206 |
| 2022 | -5.32% | 0.95 | 47.32% | 7.64% | -0.70 | 6,494 |
| 2023 | -11.59% | 0.85 | 46.00% | 12.19% | -2.40 | 6,420 |
| 2024 | -5.35% | 0.92 | 47.64% | 9.11% | -1.16 | 6,473 |
| 2025 | -6.87% | 0.91 | 47.95% | 8.28% | -1.31 | 6,325 |
| 2026 through Aug | -8.53% | 0.79 | 44.68% | 10.37% | -2.84 | 3,977 |

Every observed calendar segment is negative after full spread.

## Verification and decision

The independent verifier checked 95,685 rows representing 31,895 unique trades. It confirmed DST-aware endpoints, pair directions, cost monotonicity and exact reconstruction of the reported five-year portfolio return.

**Reject and do not run the optimization pipeline.** The edge exists only before realistic costs, all complete pair versions lose, the latest year is negative even gross, and the only positive full-spread component decays. Optimizing offsets, pairs or fixes now would mainly create selection bias.

No EA, website, BAT installer, set file, recommended portfolio or terminal was changed.
