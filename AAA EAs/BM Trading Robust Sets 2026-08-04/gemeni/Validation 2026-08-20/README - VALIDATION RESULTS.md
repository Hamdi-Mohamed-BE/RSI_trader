# Gemini BOS Retest EA — Native MT5 Validation

Completed: 2026-08-20

## Verdict

**REJECT — do not add this EA to the active BAT and do not use it on a live or prop-firm account.**

All 72 true 1%-risk training configurations lost money during 2020–2024. The least-bad training configuration still lost 81.23% with PF 0.92 and 86.74% maximum equity drawdown. Locked validation did not rescue the strategy: the nominal document configuration lost 20.22%, while the least-bad training candidate produced PF 1.01 with 29.23% drawdown.

The original default fixed-lot configuration made 15.32% during locked validation, but it lost 3.65% during the five-year training period and uses a hard-coded 0.01 lot instead of percentage risk. Its recent performance is a regime-dependent reversal, not a robust pass.

## Test protocol

- Instrument: Exness XAUUSD
- Timeframe: H1
- Account: simulated USD 10,000, 1:2000 leverage
- Training: 2020-01-01 through 2024-12-31, native MT5 M1-based modelling
- Locked validation: 2025-01-01 through 2026-08-19, native MT5 every-tick modelling
- Execution: randomized delay
- Costs: spread through broker bid/ask ticks; commission and swap included in net results
- History quality: 98%
- Training matrix: 72 true-risk cases plus the untouched original default
- Risk cases: `InpFixedLot=0`, `InpRiskPercent=1`
- Active BAT: unchanged

Returns are total for each period, not annualized.

## Training versus locked validation

| Candidate | Training return | Training PF | Training win rate | Training equity DD | Training trades | Locked return | Locked PF | Locked win rate | Locked equity DD | Locked trades | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Original default, fixed 0.01 lot | -3.65% | 0.94 | 31.95% | 5.92% | 1,537 | +15.32% | 1.24 | 37.15% | 4.76% | 498 | Reject: inconsistent and not percentage risk |
| Least-bad training candidate, true 1% risk | -81.23% | 0.92 | 32.48% | 86.74% | 2,300 | +5.70% | 1.01 | 34.94% | 29.23% | 810 | Reject: no meaningful edge |
| Nominal document candidate, true 1% risk | -87.80% | 0.89 | 32.61% | 89.67% | 3,008 | -20.22% | 0.97 | 33.81% | 37.59% | 1,041 | Reject |

## Locked validation — complete statistics

| Metric | Original fixed 0.01 | Least-bad training candidate | Nominal document candidate |
|---|---:|---:|---:|
| Initial balance | $10,000.00 | $10,000.00 | $10,000.00 |
| Final balance | $11,531.74 | $10,569.92 | $7,977.65 |
| Net profit | +$1,531.74 | +$569.92 | -$2,022.35 |
| Total return | +15.32% | +5.70% | -20.22% |
| Max equity drawdown | $571.70 / 4.76% | $3,872.84 / 29.23% | $4,621.91 / 37.59% |
| Max balance drawdown | $520.60 / 4.35% | $3,707.15 / 28.27% | $4,576.46 / 37.26% |
| Profit factor | 1.24 | 1.01 | 0.97 |
| Win rate | 37.15% | 34.94% | 33.81% |
| Wins / losses | 185 / 313 | 283 / 527 | 352 / 689 |
| Trades | 498 | 810 | 1,041 |
| Gross profit | $7,954.28 | $57,333.67 | $62,283.98 |
| Gross loss | -$6,422.54 | -$56,763.75 | -$64,306.33 |
| Largest win | $294.15 | $303.50 | $303.50 |
| Largest loss | -$150.75 | -$436.59 | -$363.83 |
| Average win | $43.00 | $202.59 | $176.94 |
| Average loss | -$20.42 | -$106.65 | -$92.40 |
| Expected payoff / trade | +$3.08 | +$0.70 | -$1.94 |
| Sharpe ratio | 2.07 | 0.15 | -0.50 |
| Recovery factor | 2.68 | 0.15 | -0.44 |
| Commission | -$29.88 | -$558.28 | -$643.76 |
| Swap | -$87.48 | -$945.35 | -$983.08 |

## Implementation audit

The source compiles with zero errors and zero warnings, but it does not fully implement the supplied strategy document.

1. `InpFixedLot` defaults to 0.01, so `InpRiskPercent` is ignored unless fixed lot is manually set to zero.
2. The default pin-bar ratio is 1.0. A normal candle cannot have one wick equal to 100% of its total range, so the default effectively disables pin-bar signals.
3. The document recommends ATR(14), while the source defaults to ATR(21).
4. H4 support/resistance is calculated but never used by either entry condition.
5. The documented HH/HL versus LL/LH context filter is not implemented.
6. The documented choppy-market and abnormal-stop filters are not implemented.
7. The retest check is one-sided. A buy candle only has to trade below `swing high + tolerance`; it is not required to stay near or above `swing high - tolerance`. The sell condition has the mirrored defect. Deep structure failures can therefore be misclassified as retests.

These are not cosmetic differences. The EA should be corrected for fidelity before any new strategy-level validation is attempted.

## Locked equity graphs

### Original fixed 0.01 lot

![Original locked equity](Reports/Locked%20Validation/original-default-fixed001.png)

### Least-bad training candidate at true 1% risk

![Least-bad locked equity](Reports/Locked%20Validation/risk1-left3-tol300-pin055-rr2-atr14.png)

### Nominal document candidate at true 1% risk

![Nominal locked equity](Reports/Locked%20Validation/risk1-left5-tol150-pin04-rr2-atr14.png)

## Saved artifacts

- Original source and compiled EA remain unchanged in the parent `gemeni` folder.
- Training reports, graphs, generated sets and CSV/JSON summaries are in `Reports/Training`.
- Locked reports, graphs, generated sets and CSV/JSON summaries are in `Reports/Locked Validation`.
- Clearly labelled rejected settings are in `Sets/Rejected Candidates`.

