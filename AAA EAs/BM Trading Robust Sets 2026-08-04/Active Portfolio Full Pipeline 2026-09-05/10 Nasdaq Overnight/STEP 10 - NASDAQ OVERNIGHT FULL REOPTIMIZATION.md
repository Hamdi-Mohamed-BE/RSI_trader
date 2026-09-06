# Step 10 — Nasdaq Overnight Full Re-optimization

## Goal

Re-audit the active USTEC overnight strategy with native MT5 Every Tick tests, compare the existing implementation with the video-style futures-reopen variants, optimize the signal threshold, emergency stop, reward/risk target, trailing logic and Friday handling on development data only, then validate Standard and Safe modes on an untouched final year and an exact three-year window. Every run used 1% risk.

## Deployment decision

Keep **Current Standard, all day** as the live/recommended configuration.

- It produced the highest untouched-year return and the strongest Monte Carlo return floor while retaining 72 trades.
- The optimized high-win version is useful research evidence, but only produced 26 untouched-year trades.
- The native Markov Safe filter reduced the active configuration from 72 to 30 untouched-year trades and made its Monte Carlo P5 return negative. Safe mode is therefore intentionally disabled for this EA; the Full Safe portfolio preserves its Standard inputs.
- A CPU defect in the optional Safe filter was fixed. The regime calculation now runs only after the once-per-day time, calendar and signal gates, instead of on every tick. Standard trading logic and historical results are unchanged.

## Untouched locked-year comparison

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Current Standard — selected** | **+8.67%** | **1.84** | **63.89%** | 2.36% | **72** | 4.66 | 3.36 |
| High-win Standard | +4.14% | 3.36 | 76.92% | **0.88%** | 26 | **7.62** | **4.62** |
| Current Safe | +3.50% | 1.89 | 66.67% | 1.98% | 30 | 4.90 | 1.70 |
| High-win Safe | +2.61% | 9.66 | 90.00% | 0.66% | 10 | 2.33 | 3.91 |
| Video negative reopen | -0.22% | 0.91 | 48.39% | 1.52% | 31 | -0.60 | -0.14 |
| Video Go Long reopen | -1.99% | 0.71 | 44.29% | 2.25% | 70 | -2.86 | -0.89 |

Locked period: 2025-09-01 through 2026-09-01.

## Exact three-year comparison

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Current Standard — selected** | **+7.81%** | 1.29 | 55.93% | 4.86% | **177** | 1.94 | 1.56 |
| High-win Standard | +7.00% | 2.35 | 69.01% | 2.12% | 71 | 5.10 | 3.21 |
| Current Safe | +4.14% | 1.57 | 57.81% | 2.03% | 64 | 3.21 | 1.95 |
| High-win Safe | +3.60% | 10.03 | 85.00% | **0.65%** | 20 | **8.58** | **5.40** |

The very high Safe profit factors come from only 10 locked-year and 20 three-year trades. They are not reliable enough for promotion.

## Monte Carlo — untouched year, 10,000 bootstrap paths

| Configuration | Profitable paths | Return P5 | Median return | Return P95 | Median max DD | Max DD P95 | Ruin |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Current Standard — selected** | 99.22% | **+2.97%** | **+8.74%** | **+14.47%** | 1.83% | 3.50% | 0.00% |
| High-win Standard | 99.96% | +2.21% | +4.15% | +6.02% | **0.66%** | **0.95%** | 0.00% |
| Current Safe | 93.93% | -0.24% | +3.61% | +7.05% | 1.35% | 2.77% | 0.00% |
| High-win Safe | 100.00% | +1.44% | +2.61% | +3.78% | **0.29%** | **0.30%** | 0.00% |

## Development-selected high-win research preset

- Signal: previous close-to-close decline of at least 1.0%.
- Entry: 16:00 New York.
- Calendar exit: 09:29 New York.
- Emergency stop: 3.0%.
- Target: 0.75R.
- Dynamic 50/20 stop: enabled.
- Friday trades: enabled.

This preset reached +2.73%, PF 1.83, 64.44% wins, 2.12% max DD and 45 trades on the development window. It was not promoted because the untouched-year trade sample was too small and its Monte Carlo return distribution was materially below the current configuration.

## Evidence and integrity

- 40 Standard optimization tests plus four native Safe validations were completed.
- Selection used 2023-09-01 through 2025-08-31 only.
- The final year was not used to choose parameters.
- Tests used the broker's USTEC history, spread, commission, swap and random execution delay.
- MT5 compilation completed with 0 errors and 0 warnings.
- The active set explicitly disables the rejected Markov gate.

