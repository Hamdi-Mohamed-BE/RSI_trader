# US100 Weakness Exact — Exness USTEC M15

Initial balance: USD 10,000  
Risk: 1% total, split 0.5% + 0.5% between the two legs  
Model: every tick, random execution delay, Exness history  
Bracket: 60.0-point stop and 100.0-point fixed target

| Configuration and period | Quality | Net result | Return | Max equity DD | PF | Win rate | MT5 trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline, 2025-08-05 to 2026-08-04 | 100% | -$71.85 | -0.72% | 10.21% | 0.95 | 49.09% | 55 |
| Baseline, 2023-08-05 to 2026-08-04 | 98% | +$1,426.61 | +14.27% total | 14.75% | 1.25 | 53.25% | 231 |
| Strict close above reference high, latest year | 100% | -$137.34 | -1.37% | 8.54% | 0.86 | 47.37% | 38 |

The MT5 trade count includes both legs and runner partial exits. The baseline
created 23 two-leg setups in the latest one-year test and 95 setups in the
three-year test.

## Decision

Failed the active-portfolio gate. The most recent year was negative and the
three-year return remained below the previously agreed +20% requirement, with
14.75% maximum equity drawdown. The EA is installed for research but was not
added to the synchronized BAT or active portfolio.
