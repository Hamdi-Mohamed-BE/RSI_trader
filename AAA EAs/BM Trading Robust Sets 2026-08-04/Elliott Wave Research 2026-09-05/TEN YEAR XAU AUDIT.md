# XAU Elliott Wave 1-2-3 — ten-year audit

Tested the exact locked configuration without re-optimizing it on the older period.

- Symbol and timeframe: XAUUSD H4
- Period: 2016-09-01 to 2026-09-01
- Initial balance: $10,000
- Risk: 1% per trade
- Model: MT5 Every Tick with Exness broker history and costs
- History quality: 93%

## Headline performance

| Metric | Result |
|---|---:|
| Net profit | $3,756.23 |
| Net return | +37.56% |
| Final balance | $13,756.23 |
| CAGR | 3.24% |
| Profit factor | 1.26 |
| Win rate | 29.36% |
| Trades | 235 |
| Max equity drawdown | 26.32% |
| Sharpe ratio | 0.90 |
| Recovery factor | 1.41 |
| Expected payoff | $15.98 per trade |
| Average winner / loser | 3.07 |

## Calendar-year breakdown

2016 and 2026 are partial years.

| Year | Return | Net P/L | PF | Win rate | Trades |
|---:|---:|---:|---:|---:|---:|
| 2016* | -1.88% | -$187.59 | 0.00 | 0.00% | 2 |
| 2017 | -2.48% | -$243.30 | 0.85 | 22.73% | 22 |
| 2018 | -3.57% | -$341.64 | 0.80 | 21.74% | 23 |
| 2019 | -7.85% | -$724.08 | 0.64 | 17.86% | 28 |
| 2020 | -8.89% | -$755.88 | 0.45 | 13.64% | 22 |
| 2021 | -0.35% | -$27.03 | 0.98 | 25.00% | 24 |
| 2022 | +0.48% | +$37.05 | 1.02 | 25.00% | 28 |
| 2023 | +16.74% | +$1,298.43 | 3.62 | 53.33% | 15 |
| 2024 | +9.74% | +$882.31 | 2.04 | 41.18% | 17 |
| 2025 | +20.90% | +$2,077.19 | 2.05 | 40.00% | 35 |
| 2026* | +14.49% | +$1,740.77 | 2.51 | 47.37% | 19 |

## Robustness interpretation

The configuration is profitable over the complete decade, but the path is not consistent. It lost money in six consecutive calendar periods from late 2016 through 2021, was almost flat in 2022, and generated its edge primarily from 2023 onward. The balance remained below the original $10,000 until early 2025.

The recent period is much stronger: the three-year test returned +69.85% with PF 2.47 and 6.83% drawdown, while the untouched last year returned +23.82% with PF 3.15 and 3.77% drawdown. This large regime difference is evidence that the strategy currently fits the recent XAU market structure better than the older one.

## Monte Carlo context

A 10,000-path bootstrap of the 235 closed-trade cash outcomes produced a 93.79% profitable-path rate, a -2.42% P5 return, a +37.39% median return, and 26.28% P95 maximum drawdown. This resamples the observed trade outcomes; it does not model future regime changes or missing tick history.

## Decision

Keep it in demo/live-forward observation at the existing 1% maximum risk, but do not treat the recent one-year PF 3.15 as the strategy's long-run expectation. The decade result supports a more conservative expectation near PF 1.26 with potentially prolonged stagnation and drawdown.
