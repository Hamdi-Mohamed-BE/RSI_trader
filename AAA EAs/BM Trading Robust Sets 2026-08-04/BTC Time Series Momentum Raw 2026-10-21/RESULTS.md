# BTC time-series momentum + volatility targeting — raw results (generated)

Equity-based metrics from the daily EA equity log (00:00 UTC). Sharpe = daily, √365. Exposure = share of days in a position; Avg size = notional ÷ equity when in.
Positions = closed positions incl. rebalance legs; Episode = one signal period, flip to flip. Consistency = profitable months.

## Gate runs — native MT5 Model 4, separate windows

| Version | Window | Return | CAGR | Sharpe | Max DD | Exposure | Avg size | Positions | / month | / day | Position PF / win | Episodes | Episode PF / win | Consistency | Costs $ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|---:|
| **LF** | 6m | +14.42% | 31.03% | 1.49 | 9.46% | 69.4% | 0.552 | 16 | 2.66 | 0.087 | 3.8 / 37.5% | 6 | 4.43 / 16.7% | 42.9% | -1,900 | native eq DD 10.41%
| **LF** | 1y | +1.87% | 1.88% | 0.19 | 18.55% | 51.0% | 0.545 | 31 | 2.59 | 0.085 | 1.1 / 29.0% | 20 | 1.1 / 25.0% | 23.1% | -2,391 | native eq DD 19.59%
| **LF** | 3y | +60.46% | 17.09% | 0.97 | 20.83% | 59.5% | 0.495 | 96 | 2.67 | 0.088 | 1.75 / 45.8% | 54 | 1.77 / 35.2% | 43.2% | -12,473 | native eq DD 22.0%
| **LF** | 5y | +60.90% | 9.99% | 0.65 | 25.01% | 53.3% | 0.476 | 148 | 2.47 | 0.081 | 1.53 / 43.2% | 82 | 1.56 / 32.9% | 37.7% | -22,296 | native eq DD 22.07%
| **LS** | 6m | +21.80% | 48.55% | 1.8 | 12.49% | 100.0% | 0.565 | 26 | 4.32 | 0.142 | 2.84 / 42.3% | 11 | 3.11 / 27.3% | 71.4% | -2,032 | native eq DD 13.81%
| **LS** | 1y | +15.23% | 15.28% | 0.73 | 16.8% | 100.0% | 0.51 | 63 | 5.25 | 0.173 | 1.39 / 39.7% | 40 | 1.4 / 30.0% | 53.8% | -2,721 | native eq DD 18.28%
| **LS** | 3y | +37.67% | 11.25% | 0.58 | 30.69% | 100.0% | 0.482 | 184 | 5.11 | 0.168 | 1.27 / 43.5% | 107 | 1.27 / 32.7% | 56.8% | -10,968 | native eq DD 32.98%
| **LS** | 5y | +79.17% | 12.38% | 0.63 | 30.68% | 100.0% | 0.456 | 296 | 4.93 | 0.162 | 1.32 / 45.3% | 163 | 1.33 / 34.4% | 57.4% | -26,309 | native eq DD 32.97%

## Comparison screen — native MT5 Model 1, 5 years (like for like)

| Version | Window | Return | CAGR | Sharpe | Max DD | Exposure | Avg size | Positions | / month | / day | Position PF / win | Episodes | Episode PF / win | Consistency | Costs $ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|---:|
| LF — Main (spot): long if 30-day return > 0 else flat, 20% vol target, weekly rebalance | 5y | +60.89% | 9.99% | 0.65 | 25.01% | 53.3% | 0.476 | 148 | 2.47 | 0.081 | 1.53 / 43.2% | 82 | 1.55 / 32.9% | 37.7% | -22,296 |
| LS — Main (perps): long if > 0, short if < 0, 20% vol target, weekly rebalance | 5y | +78.96% | 12.35% | 0.62 | 30.68% | 100.0% | 0.456 | 296 | 4.93 | 0.162 | 1.32 / 45.3% | 163 | 1.33 / 34.4% | 57.4% | -26,304 |
| BH — Benchmark: buy and hold 1x notional | 5y | -25.24% | -5.66% | 0.29 | 87.79% | 100.0% | 1.0 | 1 | 0.02 | 0.001 | 0.0 / 0.0% | 1 | 0.0 / 0.0% | 49.2% | -52,947 |
| VTL — Control: always long, 20% vol target, weekly rebalance (no signal) | 5y | +3.61% | 0.71% | 0.15 | 45.88% | 100.0% | 0.456 | 161 | 2.68 | 0.088 | 1.07 / 48.4% | 1 | — / 100.0% | 52.5% | -28,771 |
| FIX — Control: LF signal with fixed 1x notional (no vol targeting) | 5y | +44.81% | 7.69% | 0.39 | 51.27% | 53.3% | 1.0 | 82 | 1.37 | 0.045 | 1.2 / 32.9% | 82 | 1.2 / 32.9% | 37.7% | -39,527 |
| RND1 — Control: random long/flat, LF flip rate, vol-targeted, seed 1 | 5y | +11.80% | 2.26% | 0.22 | 22.89% | 48.0% | 0.467 | 155 | 2.58 | 0.085 | 1.11 / 51.0% | 88 | 1.11 / 53.4% | 50.8% | -16,766 |
| RND2 — Control: random long/flat, LF flip rate, vol-targeted, seed 2 | 5y | -3.97% | -0.81% | 0.04 | 41.45% | 53.5% | 0.468 | 149 | 2.48 | 0.082 | 0.97 / 45.6% | 77 | 0.97 / 49.4% | 42.6% | -17,724 |
| RND3 — Control: random long/flat, LF flip rate, vol-targeted, seed 3 | 5y | -4.85% | -0.99% | 0.02 | 28.33% | 51.5% | 0.435 | 156 | 2.6 | 0.085 | 0.95 / 52.6% | 87 | 0.95 / 56.3% | 44.3% | -14,803 |
| S_L20 — Sensitivity of LF: lookback 20 days | 5y | +48.77% | 8.28% | 0.57 | 28.68% | 51.4% | 0.465 | 168 | 2.8 | 0.092 | 1.44 / 42.9% | 103 | 1.46 / 31.1% | 34.4% | -19,377 |
| S_L60 — Sensitivity of LF: lookback 60 days | 5y | +31.32% | 5.6% | 0.4 | 31.29% | 51.3% | 0.482 | 119 | 1.98 | 0.065 | 1.36 / 46.2% | 43 | 1.4 / 30.2% | 36.1% | -17,574 |
| S_L90 — Sensitivity of LF: lookback 90 days | 5y | +6.17% | 1.2% | 0.15 | 34.02% | 52.3% | 0.477 | 123 | 2.05 | 0.067 | 1.09 / 45.5% | 38 | 1.09 / 28.9% | 34.4% | -15,597 |
| S_T10 — Sensitivity of LF: target vol 10% | 5y | +29.36% | 5.29% | 0.66 | 13.25% | 53.3% | 0.238 | 150 | 2.5 | 0.082 | 1.57 / 44.7% | 82 | 1.59 / 32.9% | 37.7% | -10,503 |
| S_T30 — Sensitivity of LF: target vol 30% | 5y | +72.99% | 11.59% | 0.58 | 35.72% | 53.3% | 0.701 | 141 | 2.35 | 0.077 | 1.41 / 41.1% | 82 | 1.43 / 32.9% | 37.7% | -32,960 |
| S_V60 — Sensitivity of LF: 60-day vol window | 5y | +53.80% | 9.0% | 0.65 | 20.8% | 53.3% | 0.441 | 127 | 2.12 | 0.07 | 1.54 / 44.9% | 82 | 1.55 / 32.9% | 37.7% | -20,084 |
| S_CAP2 — Sensitivity of LF: leverage cap 2x | 5y | +60.89% | 9.99% | 0.65 | 25.01% | 53.3% | 0.476 | 148 | 2.47 | 0.081 | 1.53 / 43.2% | 82 | 1.55 / 32.9% | 37.7% | -22,296 |
| S_D1 — Sensitivity of LF: rebalance daily | 5y | +45.30% | 7.76% | 0.55 | 25.27% | 53.3% | 0.476 | 252 | 4.2 | 0.138 | 1.4 / 49.6% | 82 | 1.43 / 32.9% | 39.3% | -20,797 |
| S_WK — Sensitivity of LF: signal checked weekly only | 5y | +60.97% | 10.0% | 0.66 | 22.33% | 52.2% | 0.483 | 95 | 1.58 | 0.052 | 2.0 / 49.5% | 30 | 2.16 / 40.0% | 45.9% | -21,404 |

Random-signal control mean (RND1–3, Model 1): Sharpe 0.09, return +1.0%, max DD 30.9%.

## Per calendar year (Model 1 screen; 2021 from 2021-10-20, 2026 to 2026-10-20)

| Version | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| LF | -2.1% (DD 4%) | -21.6% (DD 23%) | +61.7% (DD 7%) | +26.1% (DD 17%) | -0.4% (DD 9%) | +3.0% (DD 19%) |
| LS | +5.0% (DD 4%) | -10.9% (DD 23%) | +70.2% (DD 10%) | +3.3% (DD 31%) | +0.6% (DD 14%) | +6.9% (DD 17%) |
| BH | -28.9% (DD 33%) | -81.5% (DD 82%) | +229.7% (DD 40%) | +160.8% (DD 40%) | -16.5% (DD 42%) | -18.6% (DD 61%) |
| VTL | -9.8% (DD 12%) | -38.2% (DD 39%) | +42.4% (DD 20%) | +46.5% (DD 13%) | -5.0% (DD 19%) | -5.4% (DD 30%) |
| FIX | -7.4% (DD 12%) | -44.9% (DD 47%) | +121.6% (DD 14%) | +33.4% (DD 37%) | -1.2% (DD 21%) | -3.3% (DD 29%) |

## Raw gate

| Version | Positive 3y & 5y | Episode PF ≥ 1.15 3y & 5y | ≥ 30 positions | Sharpe > always-long VT (5y, M1) | Sharpe > random mean | Best day / trade | Verdict |
|---|---|---|---|---|---|---|---|
| LF | yes | yes | yes | yes | yes | yes | **PASS** |
| LS | yes | yes | yes | yes | yes | yes | **PASS** |

## Best-day dependence (Model 4, closed positions)

- LF|3y: total $+60,223; without best day $+43,565; without best trade $+43,008; without 5 best days $-6,748; without worst day $+72,446 → PASS
- LF|5y: total $+60,672; without best day $+42,151; without best trade $+42,349; without 5 best days $-8,397; without worst day $+73,024 → PASS
- LS|3y: total $+37,462; without best day $+20,804; without best trade $+21,008; without 5 best days $-26,053; without worst day $+48,780 → PASS
- LS|5y: total $+78,920; without best day $+55,036; without best trade $+55,296; without 5 best days $-6,210; without worst day $+93,612 → PASS
