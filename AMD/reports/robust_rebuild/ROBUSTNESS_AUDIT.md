# AMD Robustness Audit

## Decision

The current strategy is **rejected for live trading**.

The codebase is improved and protected, but the trading hypothesis did not
survive untouched historical validation.

## Evidence

### Two-year chronological development

The selected candidate used fade signals only, relative ATR 0.65-1.00, Asia
range ratio 0.60-1.00, 2R targets, and the +0.30R to +0.15R protective stop.

| Metric | Result |
|---|---:|
| Trades | 76 |
| Win rate | 84.21% |
| Profit factor | 2.18 |
| Net | +14.25R |
| Return at 3% risk | +50.06% |
| Max drawdown | 8.73% |
| Positive half-year folds | 4 / 4 |

### Frozen untouched year

The parameters above were frozen before testing 2023-07-30 through
2024-07-30.

| Metric | Result |
|---|---:|
| Trades | 43 |
| Win rate | 44.19% |
| Profit factor | 0.12 |
| Net | -21.15R |
| Return at 3% risk | -47.57% |
| Max drawdown | 47.81% |

### Three-year redesign

The second pass tested immediate fades, distribution continuations, four H1
EMA trend filters, three MSS confirmation windows, multiple relative-volatility
regimes, several R targets, and protective-stop timings.

No candidate met the acceptance rule. The least-bad full-period candidate had
PF 0.72, -6.90R, and 47.81% drawdown. MSS confirmation did not repair the
edge; its best tested PF remained below 1.

## Root cause

The recent high win rate depended heavily on small +0.15R locked-stop exits.
The payoff distribution was fragile: a full -1R loss cancels approximately
6.67 protected wins. Earlier regimes produced too many full stops and too few
2R targets, making the recent result non-transferable.

## Changes retained

- relative-ATR regime calculation;
- candle and risk-quality controls;
- optional H1 trend alignment;
- optional sweep-to-MSS confirmation;
- rolling half-year research scripts;
- untouched-year validation;
- dry-run defaults and hard `MODEL_APPROVED=false` live lock;
- regression tests for signal timing and execution safety.

## Next valid research direction

Do not optimize more thresholds on these same years. A materially new entry
model is required, ideally using independent order-flow data or a verified
market-structure/FVG entry, and it must reserve another untouched year before
live approval.
