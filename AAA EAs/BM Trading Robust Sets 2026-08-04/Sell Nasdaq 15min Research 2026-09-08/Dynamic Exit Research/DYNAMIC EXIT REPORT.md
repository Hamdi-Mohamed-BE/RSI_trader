# Sell Nasdaq 15min — dynamic SL/TP research

Research-only audit. The deployed 450/1000 Standard and original London-confirmed 600/1000 Safe presets were not changed.

## Test design

- Development selection: 2023-09-01 to 2025-09-01, native MT5 one-minute OHLC.
- Untouched validation: 2025-09-01 to 2026-09-01, native MT5 Every Tick with broker costs and random delay.
- Full reference: 2023-09-01 to 2026-09-01, native MT5 Every Tick.
- Dynamic SL families: setup-candle high plus buffer, opening-range multiple, ATR multiple, and max(opening range, ATR).
- Dynamic TP families: original-risk multiple, opening-range multiple, ATR multiple, plus fixed-TP controls.
- Evidence inventory: 136 native MT5 reports across discovery, local robustness and final validation.
- Risk remains 1% of dynamic equity to the actual calculated stop.
- Break-even, trailing and Dynamic 50/20 remain off so this audit isolates initial SL/TP behavior.

## Untouched locked-year comparison

| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current Standard 450/1000 | +7.07% | 1.14 | 35.62% | 8.75% | 73 | 6.24 | 0.70 |
| Dynamic Standard candidate | +16.47% | 1.27 | 27.40% | 14.46% | 73 | 6.44 | 0.84 |
| Current London Safe 600/1000 | +10.54% | 1.33 | 46.30% | 4.52% | 54 | 12.22 | 2.14 |
| Dynamic London candidate | +15.44% | 1.49 | 46.30% | 7.79% | 54 | 7.71 | 1.82 |

## Full three-year comparison

| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current Standard 450/1000 | +90.16% | 1.42 | 42.22% | 11.57% | 225 | 14.87 | 4.10 |
| Dynamic Standard candidate | +112.38% | 1.43 | 31.11% | 18.04% | 225 | 9.41 | 3.03 |
| Current London Safe 600/1000 | +32.62% | 1.33 | 45.62% | 6.07% | 160 | 9.33 | 5.23 |
| Dynamic London candidate | +95.36% | 1.78 | 44.38% | 7.82% | 160 | 11.25 | 6.62 |

## Standard selection

- Selected dynamic stop: `atr-stop-2x`
- Selected target: `target-range-2.5x`
- Selected local robustness point: `atr14-sl1.6-range2.5`
- Locked Monte Carlo return P5: -18.57%
- Locked Monte Carlo max-DD P95: 29.34%

Top development candidates:

| Candidate | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| atr14-sl1.6-range2.5 | +88.85% | 1.61 | 32.89% | 15.87% | 152 | 11.38 | 2.69 |
| atr20-sl2.4-range2.5 | +83.03% | 1.68 | 41.45% | 14.24% | 152 | 11.10 | 2.89 |
| atr10-sl1.6-range2.5 | +87.22% | 1.62 | 36.18% | 16.47% | 152 | 11.36 | 2.53 |
| atr14-sl2-range2.5 | +81.58% | 1.63 | 39.47% | 15.05% | 152 | 11.06 | 2.69 |
| atr10-sl2.4-range2.5 | +71.51% | 1.73 | 47.37% | 9.62% | 152 | 10.23 | 4.23 |

## London Safe selection

- Selected dynamic stop: `atr-stop-2.5x`
- Selected target: `target-3r`
- Selected local robustness point: `atr14-sl2.5-r3`
- Locked Monte Carlo return P5: -2.69%
- Locked Monte Carlo max-DD P95: 13.27%

Top development candidates:

| Candidate | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| atr14-sl2.5-r3 | +65.63% | 1.99 | 43.40% | 7.31% | 106 | 12.13 | 6.43 |
| atr20-sl2.5-r3.6 | +65.65% | 1.90 | 41.51% | 7.30% | 106 | 10.52 | 5.17 |
| atr10-sl2.5-r3.6 | +61.58% | 2.03 | 46.23% | 7.85% | 106 | 10.22 | 5.81 |
| atr20-sl2.5-r3 | +61.63% | 1.87 | 41.51% | 7.80% | 106 | 11.52 | 5.73 |
| atr14-sl2.5-r3.6 | +61.65% | 1.92 | 43.40% | 8.32% | 106 | 10.04 | 5.26 |

## Review recommendation

- Keep the current fixed 450/1000 Standard preset. The adaptive Standard candidate raised return but materially worsened win rate, drawdown, Sharpe/recovery quality and Monte Carlo downside.
- Do not replace London Safe automatically. The ATR(14) 2.5x stop with 3R target is a strong isolated demo candidate because its PF and return improved, but its untouched drawdown rose from 4.52% to 7.79% and its untouched Sharpe/recovery weakened.
- If approved later, expose the adaptive London configuration as a separate selectable mode first; preserve the current fixed London Safe preset until forward evidence confirms the trade-off.

## Deployment status

Nothing from this experiment is deployed. Promotion requires explicit user review and approval after the untouched evidence is compared with the current presets.
