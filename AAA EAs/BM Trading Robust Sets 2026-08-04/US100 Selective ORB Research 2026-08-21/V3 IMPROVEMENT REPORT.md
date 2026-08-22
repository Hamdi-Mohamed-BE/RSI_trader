# US100 Selective ORB V3 — improvement report

## Decision

**V3 supersedes V1 as the best research configuration. Paper-trade first; not added to the active BAT.**

V3 improves full-period return, profit factor, win rate, recovery factor, and the latest-year result. Full-period max equity drawdown increased by only 0.10 percentage point, while latest-year drawdown decreased materially.

## Direct comparison

Both versions used Exness `USTEC`, M5, USD 10,000 initial balance, 1% equity risk per trade, the MT5 Every Tick model, recorded spread, random execution delay, commission, and swap.

| Metric | V1 | V3 | Change |
|---|---:|---:|---:|
| Full return | +15.59% | **+18.70%** | +3.11 pp |
| Full profit factor | 1.61 | **2.16** | +0.55 |
| Full win rate | 55.56% | **60.38%** | +4.82 pp |
| Full max equity DD | **4.02%** | 4.12% | +0.10 pp |
| Full recovery factor | 3.77 | **4.37** | +0.60 |
| Full trades | 81 | 53 | -28 |
| Latest-year return | +1.05% | **+1.54%** | +0.49 pp |
| Latest-year PF | 1.31 | **1.53** | +0.22 |
| Latest-year max equity DD | 3.20% | **2.73%** | -0.47 pp |

## V3 native MT5 results

| Segment | Period | Final balance | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| Training | 2020-01-01 to 2023-12-31 | $11,294.84 | +12.95% | 2.02 | 61.54% | 4.12% | 39 |
| Validation | 2024-01-01 to 2025-06-30 | $10,281.36 | +2.81% | 43.57* | 50.00% | 2.02% | 8 |
| Later chronological check | 2025-07-01 to 2026-08-20 | $10,221.33 | +2.21% | 1.75 | 66.67% | 2.75% | 6 |
| Exact latest year | 2025-08-21 to 2026-08-20 | $10,153.76 | +1.54% | 1.53 | 60.00% | 2.73% | 5 |
| Full continuous test | 2020-01-01 to 2026-08-20 | **$11,870.41** | **+18.70%** | **2.16** | **60.38%** | **4.12%** | **53** |

`*` Validation PF is inflated because eight trades produced only $6.61 of gross losses. It must not be interpreted as a sustainable PF of 43.

The full-period CAGR is approximately 2.62%. The strategy remains intentionally selective and is not a high-frequency or high-return system.

### V3 full-period detail

| Metric | Result |
|---|---:|
| Initial / final balance | $10,000.00 / $11,870.41 |
| Net profit | $1,870.41 |
| Gross profit / loss | $3,489.34 / -$1,618.93 |
| Profit factor | 2.16 |
| Max equity drawdown | $427.57 / 4.12% |
| Max balance drawdown | $411.61 / 3.97% |
| Wins / losses | 32 / 21 |
| Long trades | 23; 73.91% won |
| Short trades | 30; 50.00% won |
| Largest win / loss | $230.43 / -$224.98 |
| Average win / loss | $109.04 / -$75.31 |
| Commission / swap | -$37.40 / -$33.45 |
| Recovery factor | 4.37 |

Spread and random execution-delay effects are embedded in the deal results.

## What changed

The core ORB logic, volume normalization, VWAP confirmation, retest, stop, target, and risk calculation did not change. V3 adds an optional New York time/direction schedule:

- 10:00–10:29: long and short setups are allowed.
- 10:30–10:59: only long setups are allowed.
- 11:00–11:29: only short setups are allowed.

The rule removes the direction/time combinations that repeatedly diluted the edge while retaining later trades that were useful in validation and the recent period.

## Boundary robustness

Seven neighboring schedules were tested by shifting the two boundaries by one M5 bar:

- Long-only transition: 10:25, 10:30, or 10:35.
- Short-only transition: 10:55, 11:00, or 11:05.

All tested neighbors remained profitable in the training and validation screens. Training PF ranged from 1.73 to 3.06. This indicates a local plateau rather than dependence on one exact timestamp. The final preset keeps the neutral 10:30 and 11:00 boundaries.

## Important limitations

- The time/direction hypothesis was discovered while examining the complete research history, including the recent segment. V3 therefore represents iterative research, not a pristine untouched holdout result.
- Only five trades occurred during the exact latest year. The positive latest-year result is encouraging but statistically weak.
- Exness `tick_volume` is broker quote activity, not centralized Nasdaq exchange volume or Level 2 order-book volume.
- Complete-period tests use MT5 Every Tick generated from Exness M1 broker history. Exness's downloadable real-tick archive in this tester did not cover the complete multi-year period.
- A demo forward test of at least 20–30 V3 trades should be completed before live use.

## Final files

- `EA/US100 Selective ORB Retest EA.mq5` — version 1.10 source
- `EA/US100 Selective ORB Retest EA.ex5` — compiled EA
- `Sets/BEST V3 - US100 USTEC M5 - TIME DIRECTION OR30 - 1pct.set` — promoted V3 preset
- `Backtest Reports/v3-time-direction/` — native MT5 reports and terminal graphs
- `native-v3-time-direction-results.json` and `.csv` — parsed results
- `US100 Selective ORB V3 - Full Equity and Drawdown.png` — V3 graph
