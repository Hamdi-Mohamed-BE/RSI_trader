# Gold capped recovery — optimization and validation results

## Verdict: NOT APPROVED FOR DEPLOYMENT

Four raw starts previously reached insolvency. The capped alternative limits exposure and introduces protective exits, but survival alone does not establish a profitable strategy. No live trades, deployment, website/BAT changes or Git push were made.

## Tested settings

**Initial candidate:** gap $10; net basket target $20; basket loss $60; daily loss $90; daily profit cap $60; lot 0.01; multiplier 1; maximum 3 legs.

**Selected by the declared development/validation ranking:** gap $10; net basket target $20; basket loss $60; daily loss $90; daily profit cap $60; lot 0.01; multiplier 1; maximum 3 legs.

Dollar risk limits are fixed, not compounded percentages. $60/$90 are initially 2%/3% of $3,000; those percentages rise if the balance falls. Additions tighten a common protective stop and are rejected if risk distance or margin is insufficient. Targets and losses include loaded commission/swap; stop fills can overshoot.

## Side-by-side standard windows

Each row starts with a fresh $3,000, ends 2026-09-05 exclusive unless it fails earlier, and uses native MT5 model 4. These windows overlap; do not add their profits together or call every window out-of-sample.

| Window | Initial capped net | Return | Equity DD | Selected capped net | Return | Equity DD |
|---|---|---|---|---|---|---|
| 6m | -$1,914.97 | -63.83% | 67.96% | -$1,914.97 | -63.83% | 67.96% |
| 1y | -$228.04 | -7.60% | 44.69% | -$228.04 | -7.60% | 44.69% |
| 3y | $410.55 | 13.69% | 39.46% | $410.55 | 13.69% | 39.46% |
| 5y | $589.04 | 19.63% | 38.21% | $589.04 | 19.63% | 38.21% |

### Selected version: full statistics

| Window | Final balance | Positions | Net position WR | Net PF | Baskets | Basket WR | Worst basket | $6,000 first reached | Insolvency |
|---|---|---|---|---|---|---|---|---|---|
| 6m | $1,085.03 | 1149 | 49.26% | 0.804 | 565 | 66.37% | -$67.66 | Not reached | No |
| 1y | $2,771.96 | 2114 | 54.21% | 0.986 | 1067 | 71.23% | -$67.66 | Not reached | No |
| 3y | $3,410.55 | 3542 | 55.19% | 1.015 | 1803 | 72.16% | -$112.05 | Not reached | No |
| 5y | $3,589.04 | 4218 | 55.55% | 1.019 | 2132 | 72.37% | -$112.05 | Not reached | No |

Individual position win rates can be lower than basket win rates because an averaged basket may close one losing position together with profitable additions. All displayed win rates/PF are recomputed after recorded fees. Positions closed at the testing boundary are included, and boundary closure is not an ordinary strategy signal.

### Costs and actual loss-limit overshoot

| Window | Commission | Swap | Max lots | Daily loss locks | Daily profit locks | Basket overshoots | Largest overshoot | Fixed-path cost stress net |
|---|---|---|---|---|---|---|---|---|
| 6m | -$68.94 | -$19.15 | 0.03 | 62 | 60 | 99 | $7.66 | -$3,241.90 |
| 1y | -$126.84 | -$61.18 | 0.03 | 91 | 130 | 133 | $7.66 | -$2,685.08 |
| 3y | -$212.52 | -$578.33 | 0.03 | 136 | 177 | 167 | $52.05 | -$4,251.94 |
| 5y | -$253.08 | -$1,141.69 | 0.03 | 148 | 184 | 189 | $52.05 | -$5,455.55 |

Fixed-path stress subtracts one additional observed entry spread, another copy of commission and negative swap, and $0.50 per ounce adverse execution at BOTH entry and exit. It preserves the recorded trades: it is a cost sensitivity calculation, not a native strategy rerun, and it does not reproduce earlier risk limits or a changed trading path.

## Chronological selection and later validation

Development: 2021-09-05 to 2023-09-05 (12 cases). Validation: 2023-09-05 to 2024-09-05 (top 3). The final choice was frozen before the later 2024-09-05 to 2026-09-05 check. Ranking prefers non-insolvent, profitable, sufficiently active cases, then net profit / (1 + maximum equity drawdown dollars). Repeated prior inspection means historical validation is not equivalent to unseen forward-demo evidence.

| Segment | Net | Net PF | Equity DD | Baskets |
|---|---|---|---|---|
| Selected: development | $160.13 | 1.033 | 19.06% | 331 |
| Selected: validation | $608.95 | 1.181 | 9.06% | 255 |
| Selected: later check | -$159.93 | 0.993 | 44.07% | 1551 |
| Selected: latest 6m | -$1,914.97 | 0.804 | 67.96% | 565 |

### All development cases

| Case | Net | Net PF | Equity DD | Baskets |
|---|---|---|---|---|
| g10-p20-dev-d1 | $160.13 | 1.033 | 19.06% | 331 |
| g20-p20-dev-d1 | -$110.35 | 0.964 | 21.78% | 199 |
| g20-p30-dev-d1 | -$168.51 | 0.943 | 28.21% | 147 |
| g30-p30-dev-d1 | -$234.84 | 0.898 | 21.51% | 114 |
| g30-p20-dev-d1 | -$300.57 | 0.893 | 21.74% | 170 |
| g30-p10-dev-d1 | -$327.77 | 0.903 | 23.13% | 322 |
| g20-p10-dev-d1 | -$361.58 | 0.919 | 24.34% | 437 |
| g10-p30-dev-d1 | -$656.27 | 0.861 | 32.81% | 217 |
| gatr-p30-dev-d1 | -$682.42 | 0.901 | 35.25% | 334 |
| g10-p10-dev-d1 | -$817.63 | 0.881 | 32.66% | 669 |
| gatr-p20-dev-d1 | -$884.65 | 0.892 | 40.21% | 516 |
| gatr-p10-dev-d1 | -$984.43 | 0.901 | 45.10% | 1036 |

### Top-three validation

| Case | Net | Net PF | Equity DD | Baskets |
|---|---|---|---|---|
| g10-p20-val-d1 | $608.95 | 1.181 | 9.06% | 255 |
| g20-p20-val-d1 | $486.27 | 1.236 | 7.37% | 164 |
| g20-p30-val-d1 | $398.16 | 1.191 | 8.33% | 121 |

## One-at-a-time diagnostics

These change one setting relative to the frozen selected case. They were not used to replace that case after seeing the later check.

| Variant / segment | Net | Net PF | Equity DD | Worst basket |
|---|---|---|---|---|
| capped-double-dev-d1 | -$1,154.07 | 0.848 | 45.30% | -$62.65 |
| original-exit-dev-d1 | -$388.70 | 0.940 | 29.80% | -$61.17 |
| loss30-dev-d1 | -$590.65 | 0.891 | 27.04% | -$30.51 |
| daily30-dev-d1 | -$320.21 | 0.939 | 21.53% | -$63.32 |
| daily-none-dev-d1 | -$49.57 | 0.990 | 19.94% | -$60.27 |
| capped-double-val-d1 | $801.57 | 1.180 | 10.41% | -$60.42 |
| original-exit-val-d1 | $394.44 | 1.091 | 10.32% | -$60.32 |
| loss30-val-d1 | $297.97 | 1.086 | 8.61% | -$30.92 |
| daily30-val-d1 | $416.12 | 1.126 | 12.51% | -$60.16 |
| daily-none-val-d1 | $309.24 | 1.085 | 11.28% | -$60.93 |

## Native execution and margin stress

| Run | Net | Net PF | Equity DD | Worst basket |
|---|---|---|---|---|
| selected-slow-6m-d1000 | -$1,721.43 | 0.823 | 61.39% | -$74.20 |
| selected-low-margin-6m-d1 | -$1,914.97 | 0.804 | 67.96% | -$67.66 |

The slow run uses 1,000 ms fixed delay on EA trade requests and stop modifications, not an artificial delay on broker-side SL/TP triggering. It recorded 12 failed stop updates (price moved or the position had already closed); the verified fail-safe flattened those baskets and did not add more exposure. The ordinary 1 ms runs had no such failures. The margin stress uses a conservative pre-entry 1:200 leverage cap; native account leverage remains 1:2000. It is not a reconstruction of historical news-margin schedules. [MetaQuotes execution-delay rules](https://www.metatrader5.com/en/terminal/help/algotrading/strategy_optimization).

## Reliability and scope

- Real ticks start on 2026-01-01 in the connected broker history. Earlier periods use generated ticks. The latest six-month run is the most directly supported real-tick comparison, not a five-year real-tick guarantee.
- Current native fees and virtual equity-dependent leverage tiers are used; historical fee, swap, liquidity and high-margin changes are not fully reconstructed. [Exness leverage rules](https://get.exness.help/hc/en-us/articles/360014529380-Leverage).
- Every-tick equity is monitored; a nonpositive reading ends the test. Native protective SLs are also attached. We do not allow the post-insolvency recoveries found in the original raw test to count as survival.
- Neither win rate nor the daily profit cap guarantees income. The account can suffer a large cumulative drawdown through repeated limited losses.
- No rolling-start probability or cash-withdrawal result is claimed unless a separate result file documents that exact simulation.
- 5 risk-arithmetic tests passed; 32 unique native runs were independently reconciled against their position/deal ledgers. The batch core was mechanically verified against the single-run source. When the selected preset exactly matches the initial candidate, its four standard-window results are reused, not counted as new tests.

## Files

[Frozen rules and protocol](RULES.md) · [Selection](selection.json) · [Full result data](final.json) · [Verification](verification.json)

- [6m native report, including every deal](Backtest%20Reports/selected-6m-d1.htm)
- [1y native report, including every deal](Backtest%20Reports/selected-1y-d1.htm)
- [3y native report, including every deal](Backtest%20Reports/selected-3y-d1.htm)
- [5y native report, including every deal](Backtest%20Reports/selected-5y-d1.htm)
