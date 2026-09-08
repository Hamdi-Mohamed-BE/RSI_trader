# Step 1 — Volatility-Regime Switch: Final Report

## Decision

**Do not replace the live portfolio defaults. XAUUSD qualifies only for a demo-forward test of the true switch; XAGUSD, BTCUSD and USTEC are rejected for deployment.**

The overlay was selected without reading the latest year. It used completed UTC daily bars only, fixed 1% risk, native MT5 component ledgers, and 10,000 Monte Carlo paths.

## Primary selection: best rule across all regime modes

| Asset | Locked return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | MC P5 | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| XAUUSD | 27.34% | 2.47 | 35.71% | 7.75% | 28 | 1.50 | 3.53 | -3.93% | Research only |
| XAGUSD | 12.39% | 4.76 | 25.00% | 2.85% | 4 | 1.08 | 4.35 | -3.87% | Reject |
| BTCUSD | 0.69% | 1.69 | 66.67% | 0.99% | 3 | 0.36 | 0.70 | -1.52% | Reject |
| USTEC | -3.29% | 0.90 | 27.27% | 17.49% | 44 | -0.23 | -0.19 | -22.05% | Reject |

## Frozen baseline versus selected overlay

| Asset | Baseline return | Baseline PF | Baseline DD | Baseline trades | Overlay return | Overlay PF | Overlay DD | Overlay trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | 28.62% | 2.17 | 7.43% | 35 | 27.34% | 2.47 | 7.75% | 28 |
| XAGUSD | 10.63% | 3.10 | 4.37% | 6 | 12.39% | 4.76 | 2.85% | 4 |
| BTCUSD | -5.88% | 0.22 | 7.45% | 10 | 0.69% | 1.69 | 0.99% | 3 |
| USTEC | -10.64% | 0.90 | 25.47% | 141 | -3.29% | 0.90 | 17.49% | 44 |

## The actual momentum / mean-reversion switch

| Asset | Train return / PF / trades | Validation return / PF / trades | Locked return | PF | Win rate | DD | Trades (Mom/MR) | Sharpe | Recovery | MC P5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | 16.53% / 1.87 / 31 | 17.88% / 1.59 / 43 | 34.74% | 2.85 | 37.93% | 4.68% | 29 (29/0) | 1.73 | 7.42 | 5.98% |
| XAGUSD | -1.58% / 0.44 / 6 | -0.61% / 0.81 / 11 | 14.43% | 12.59 | 33.33% | 0.99% | 3 (2/1) | 0.80 | 14.58 | -2.07% |
| USTEC | 1.75% / 2.56 / 8 | -0.05% / 0.99 / 21 | 2.53% | 1.25 | 52.00% | 2.40% | 25 (12/13) | 0.38 | 1.05 | -2.63% |

## Recommendation

- **XAUUSD:** demo-forward test the true switch only. Its frozen rule used a 40-day return, ±2% state threshold, 126-transition history, no directional signal buffer, and a 50% Sideways-probability requirement. Locked evidence was +34.74%, PF 2.85, 37.93% wins, 4.68% DD, 29 trades; Monte Carlo P5 was +5.98% and DD P95 was 8.30%.
- **XAGUSD:** reject. The locked result is based on only three trades and its pre-lock train and validation returns were both negative.
- **BTCUSD:** reject. The filtered locked result has only three trades and no separately validated BTC mean-reversion leg exists.
- **USTEC:** reject. The globally selected overlay remained negative. The true switch became +2.53% in the locked year, but its pre-lock validation was slightly negative and its Monte Carlo P5 was negative; selecting it now would be post-lock cherry-picking.

## Native combined-EA confirmation

The frozen XAU switch was subsequently implemented as `Calyx XAU Regime Switch EA`, compiled with **0 errors and 0 warnings**, and rerun in native MT5 Every Tick mode with broker spread, commission, swap and random execution delay. Risk remained hard-locked at 1%.

| Window | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| 6 months | -4.95% | 0.43 | 13.33% | 6.25% | 15 | -0.76 | -0.78 |
| 1 year | +29.28% | 2.09 | 30.56% | 8.43% | 36 | 2.44 | 2.48 |
| 3 years | +88.30% | 1.93 | 30.77% | 10.39% | 117 | 1.86 | 4.08 |
| 5 years | +96.19% | 1.59 | 27.96% | 10.21% | 211 | 1.25 | 4.34 |

The native implementation supports the longer-term edge, but the most recent six months are materially weak. Therefore the decision remains **demo forward test only**. It is included in the portfolio installers and website with that warning; it is not approved for real capital.

## Important limitation

The original selection stage was a causal overlay on separate native-MT5 component ledgers. The new combined EA has now passed native historical confirmation, but historical agreement does not remove model risk, the recent negative six-month slice, or the need for independent demo-forward evidence.

## Files

- `results.json`: complete selected, baseline, per-mode and trade-level results.
- `all-screen-results.csv`: all 5,380 tested configurations.
- `true-switch-monte-carlo.json`: 10,000-path robustness results.
- `EA/Calyx XAU Regime Switch EA.mq5` and `.ex5`: compiled combined EA.
- `EA/Calyx XAU Regime Switch EA.demo-lock.compile.log`: clean final compiler evidence, including the real-account safety lock.
- `Charts/`: locked comparison, equity, full configuration screen and true-switch charts.
