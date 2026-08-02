# 0.5% loss-progression and 1.7R target study

Rule tested:

- Start every new sequence at 0.50% account risk.
- After a closed loss: next risk = 0.50% × 1.6^loss streak.
- After a closed win: reset to 0.50%.
- Breakeven does not change the streak.
- Research progression is uncapped to measure the exact requested rule.
- Every strategy has a hard 1.7R maximum take-profit.
- Trailing variants keep the hard 1.7R target.

## Results

| Bot | Test period | Scenario | Trades | Win rate | Cash PF | Return | Max DD | Peak risk / exposure |
|---|---|---|---:|---:|---:|---:|---:|---:|
| AMD (XAU) | 365d | Flat, fixed | 31 | 83.87% | 2.63 | +4.16% | 1.49% | 0.50% |
| AMD (XAU) | 365d | Flat, trailing | 31 | 83.87% | 2.77 | +4.52% | 1.49% | 0.50% |
| AMD (XAU) | 365d | Progression, fixed | 31 | 83.87% | 2.04 | +3.79% | 2.56% | 2.05% |
| AMD (XAU) | 365d | Progression, trailing | 31 | 83.87% | 2.14 | +4.15% | 2.56% | 2.05% |
| Asia Breakout basket | 60d | Flat, fixed | 81 | 55.56% | 1.24 | +3.65% | 3.15% | 2.00%* |
| Asia Breakout basket | 60d | Flat, trailing | 81 | 60.49% | 1.32 | +4.34% | 1.93% | 2.00%* |
| Asia Breakout basket | 60d | Progression, fixed | 81 | 55.56% | 1.15 | +3.53% | 7.36% | 5.32%* |
| Asia Breakout basket | 60d | Progression, trailing | 81 | 60.49% | 1.44 | +8.26% | 3.23% | 5.32%* |
| DmC (US100 + XAU) | 60d | Flat, fixed | 18 | 50.00% | 1.51 | +2.34% | 1.99% | 0.50% |
| DmC (US100 + XAU) | 60d | Flat, trailing | 18 | 66.67% | 1.68 | +2.09% | 1.49% | 0.50% |
| DmC (US100 + XAU) | 60d | Progression, fixed | 18 | 50.00% | 1.92 | +6.98% | 4.55% | 3.28% |
| DmC (US100 + XAU) | 60d | Progression, trailing | 18 | 66.67% | 1.69 | +2.53% | 1.78% | 1.28% |
| EMA3 (XAU H4) | 365d | Flat, fixed | 43 | 58.14% | 2.15 | +10.97% | 2.62% | 0.50% |
| EMA3 (XAU H4) | 365d | Flat, trailing | 46 | 58.70% | 1.95 | +9.59% | 2.62% | 0.50% |
| EMA3 (XAU H4) | 365d | Progression, fixed | 43 | 58.14% | 2.56 | +20.81% | 2.57% | 2.05% |
| EMA3 (XAU H4) | 365d | Progression, trailing | 46 | 58.70% | 2.40 | +19.52% | 2.57% | 2.05% |
| US100 Weakness | available 47d | Flat, fixed | 8 | 62.50% | 4.17 | +3.21% | 1.00% | 0.50% |
| US100 Weakness | available 47d | Flat, trailing | 8 | 62.50% | 4.17 | +3.21% | 1.00% | 0.50% |
| US100 Weakness | available 47d | Progression, fixed | 8 | 62.50% | 4.17 | +4.75% | 1.30% | 1.28% |
| US100 Weakness | available 47d | Progression, trailing | 8 | 62.50% | 4.17 | +4.75% | 1.30% | 1.28% |

\* Asia values show peak basket planned exposure, not risk on one order.

## Decision

- Do not enable the 1.6x progression globally. It changes cash sizing, not signal quality, and its outcome depends heavily on the order of wins and losses.
- Keep progression disabled in every live `.env` for now. The implementation is ready and each bot has a configurable live safety cap if it is deliberately enabled later.
- Use trailing for AMD, Asia Breakout, and DmC. These tests improved PF and/or reduced drawdown.
- Keep fixed 1.7R management for EMA3. It beat trailing on return and PF.
- US100 trailing made no difference in the eight-trade sample; the sample is too small for a management decision.

The strongest progression result was EMA3 fixed 1.7R, but 43 trades are not enough to establish that a loss-multiplier is robust. The clearest rejection is AMD: progression reduced return while raising drawdown. Asia fixed also received almost no extra return for more than twice the drawdown.

## Detailed reports

- `AMD/reports/risk_progression_1_7r/REPORT.md`
- `asia breakout/reports/risk_progression_1_7r/REPORT.md`
- `DmC/reports/risk_progression_1_7r/summary.csv`
- `EMA3/reports/risk_progression_1_7r/REPORT.md`
- `US100 weekness/reports/risk_progression_1_7r/REPORT.md`
