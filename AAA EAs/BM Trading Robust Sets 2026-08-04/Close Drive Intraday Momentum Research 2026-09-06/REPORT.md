# Step 1 — Close-Drive Intraday Momentum

Decision: keep both tested candidates out of the active system. Both selected configurations lost money in the held-out year, with PF below 1. Their small positive three-year returns include the optimization sample and do not establish a reliable edge.

Completed: 68 native MT5 runs (31 development configurations per market plus baseline/selected held-out tests and selected three-year context). Research only. Default risk: 1% of equity per trade. No production installer or website selection changed.

Development: 2023-09-01 to 2025-09-01 (M1 OHLC, 1ms execution). Selection frozen before held-out testing: 2025-09-01 to 2026-09-01 (MT5 generated Every Tick, random delay / ExecutionMode=-1). Full three-year runs include the optimization sample and are descriptive. This is not a real-tick test.

Signal variants: previous cash close to 10:00 New York (paper definition) and 09:30–10:00 only; entries 14:30/15:00/15:30 NY. Exit 15:55 to precede broker break. New York DST handled. Broker clock assumed UTC, following this Exness research environment. July 2–5, December 23–26 and Friday after Thanksgiving excluded conservatively; this is not a full exchange holiday calendar.

Stops: prior completed candle, M15 ATR, opening-range boundary; all stop distances capped at 3 ATR and broker minimum enforced. Targets: timed close or 0.5/1/2/4R. ATR distances 0.5/1/1.5/2; management none/BE/ATR trail/M15 50–20. Five- and fifteen-/thirty-minute decision bars compared. Sequential search is not an exhaustive joint optimization.

| Asset | Period | Config | Return | PF | Win rate | Equity DD | Trades | MT5 Sharpe | Recovery |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| USTEC | locked | baseline | +2.76% | 1.04 | 51.27% | 17.14% | 197 | 1.93 | 0.16 |
| USTEC | locked | selected | -1.39% | 0.92 | 65.38% | 5.97% | 52 | -4.80 | -0.22 |
| USTEC | full | selected | +3.54% | 1.07 | 66.27% | 9.41% | 169 | 3.67 | 0.35 |
| US30 | locked | baseline | -19.35% | 0.69 | 39.59% | 20.68% | 197 | -5.00 | -0.93 |
| US30 | locked | selected | -0.77% | 0.91 | 46.58% | 3.17% | 73 | -2.63 | -0.24 |
| US30 | full | selected | +2.21% | 1.07 | 46.77% | 4.80% | 201 | 2.36 | 0.46 |

## Selected settings

| Asset | Opening signal | NY entry | Direction | Stop | TP | Management |
|---|---|---|---|---|---|---|
| USTEC | 09:30 to 10:00 | 15:00 | Short only | M15 ATR x 1.0 | 0.5R | None |
| US30 | Previous cash close to 10:00 | 15:30 | Long only | Opening-range boundary | 2.0R | None |

Exact remaining thresholds and settings are in selection.json and Sets/*-locked-selected.set. All positions have a timed close at 15:55 NY or five minutes before the current broker session ends. The 3-ATR structural-stop cap is a deliberate research adaptation.

For a 0.5R target, BE at 0.5R, Dynamic 50–20 and trailing activation at 0.75R can be non-binding: the target is reached before management can help. Identical results in those comparisons do not show that trailing never matters on other targets.

DD above is the native percentage at MT5’s maximal cash equity drawdown event. The plotted lines are realized balance, not reconstructed floating equity.

## Additional execution-cost stress

| Asset | Extra cost | Stressed return | Stressed PF | Closed-balance DD |
|---|---|---:|---:|---:|
| USTEC | 0.05R/trade | -3.93% | 0.77 | 5.89% |
| US30 | 0.05R/trade | -4.32% | 0.60 | 5.27% |

The stress is hypothetical extra friction deducted from held-out trade returns and compounded; it is not a second MT5 execution test.

## Monte Carlo

| Asset | Return P5 | Median return | Return P95 | DD P95 | Profitable samples |
|---|---:|---:|---:|---:|---:|
| USTEC | -10.20% | -1.55% | +7.95% | 12.29% | 39.3% |
| US30 | -4.88% | -0.93% | +3.84% | 5.77% | 36.4% |

Monte Carlo resamples five-trade blocks of held-out net returns with compounding. It does not model unrealized drawdown, changing spreads or future regimes, and its profitable fraction is not a forecast probability. Native MT5 equity DD is reported separately.

Research basis: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866 . Published ETF evidence motivates this CFD test; it does not establish an edge in these broker instruments.

See Charts/held-out-comparison.png and the per-asset development and Monte Carlo charts. All native reports and exact inputs are retained.
