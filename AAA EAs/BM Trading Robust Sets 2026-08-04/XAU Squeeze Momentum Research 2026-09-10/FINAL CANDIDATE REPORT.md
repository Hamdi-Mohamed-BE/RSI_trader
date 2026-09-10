# XAU Squeeze Momentum — final full-pipeline candidates

Research only. No website, BAT installer, active profile, or live account was changed.

Position-level win rate and trade count are used below. This prevents partial exits from inflating MT5's deal-level figures.

| Version / period | Return | PF | Position win rate | Max equity DD | Positions | Sharpe | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|
| Literal raw 5% — 3Y | +217.69% | 1.50 | 40.74% | 32.32% | 162 | 3.49 | 98% |
| Literal raw 5% — locked real ticks | +0.00% | 0.00 | 0.00% | 0.00% | 0 | 0.00 | 67% |
| Recommended 1.25% — 3Y | +30.27% | 1.83 | 44.83% | 7.05% | 87 | 6.16 | 98% |
| Recommended 1.25% — locked real ticks | +2.79% | 1.37 | 42.86% | 5.31% | 21 | 4.43 | 67% real ticks |
| Recommended — random delay | +30.27% | 1.82 | 44.83% | 7.07% | 87 | 6.13 | 98% |
| Recommended — 500 ms | +30.24% | 1.82 | 44.83% | 7.07% | 87 | 6.14 | 98% |
| Markov safe — 3Y | +31.05% | 3.91 | 65.79% | 4.58% | 38 | 13.77 | 98% |
| Markov safe — locked real ticks | +4.62% | 2.10 | 53.33% | 2.59% | 15 | 6.69 | 67% real ticks |
| High-WR markov-safe — 3Y | +31.05% | 3.91 | 65.79% | 4.58% | 38 | 13.77 | 98% |
| High-WR markov-safe — locked real ticks | +4.62% | 2.10 | 53.33% | 2.59% | 15 | 6.69 | 67% real ticks |
| XAG frozen — 3Y | +18.80% | 1.94 | 50.82% | 3.18% | 61 | 5.30 | 98% |
| XAG frozen — locked real ticks | +0.00% | 0.00 | 0.00% | 0.00% | 0 | 0.00 | 67% |

## Chronological gate

| Recommended development | +25.25% | 2.35 | 50.00% | 2.73% | 74 | 7.02 | 98% |
| Recommended purged validation | +3.63% | 1.38 | 34.38% | 4.99% | 32 | 2.79 | 99% |
| Recommended locked real ticks | +2.79% | 1.37 | 42.86% | 5.31% | 21 | 4.43 | 67% real ticks |

## Selected configurations

### Best overall

```json
{
  "InpUseMarkovRegimeFilter": false,
  "InpMarkovReturnWindow": 40,
  "InpMarkovThreshold": 0.05,
  "InpMarkovSignalGate": 0.05,
  "InpMarkovMinLabels": 252,
  "InpMarkovHistoryBars": 2600,
  "InpEnableTrading": true,
  "InpRiskPercent": 1.25,
  "InpMaximumEffectiveLeverage": 9.8,
  "InpMagic": 1091010,
  "InpMaximumSpreadPoints": 0,
  "InpSqueezeLength": 24,
  "InpBollingerMultiplier": 1.8,
  "InpKeltnerMultiplier": 1.3,
  "InpMomentumLength": 28,
  "InpTrendSMAPeriod": 200,
  "InpRequireMomentumRising": true,
  "InpATRPeriod": 14,
  "InpATRMethod": 0,
  "InpStopATR": 3.5,
  "InpTargetR": 1.5,
  "InpTrailingMode": 1,
  "InpTrailATR": 3.5,
  "InpBreakEvenAtR": 0.0,
  "InpPartialExitAtR": 0.0,
  "InpPartialExitFraction": 0.5,
  "InpMomentumExitMode": 2,
  "InpMomentumFadeFraction": 0.5,
  "InpMaximumHoldH1Bars": 0,
  "InpDynamicTriggerFraction": 0.5,
  "InpDynamicLockFraction": 0.2,
  "InpSessionStartHourUTC": 0,
  "InpSessionEndHourUTC": 24,
  "InpWeekdayMask": 62
}
```

### Highest defensible win rate

```json
{
  "InpUseMarkovRegimeFilter": true,
  "InpMarkovReturnWindow": 40,
  "InpMarkovThreshold": 0.05,
  "InpMarkovSignalGate": 0.05,
  "InpMarkovMinLabels": 252,
  "InpMarkovHistoryBars": 2600,
  "InpEnableTrading": true,
  "InpRiskPercent": 1.25,
  "InpMaximumEffectiveLeverage": 9.8,
  "InpMagic": 1091010,
  "InpMaximumSpreadPoints": 0,
  "InpSqueezeLength": 24,
  "InpBollingerMultiplier": 1.8,
  "InpKeltnerMultiplier": 1.3,
  "InpMomentumLength": 28,
  "InpTrendSMAPeriod": 200,
  "InpRequireMomentumRising": true,
  "InpATRPeriod": 14,
  "InpATRMethod": 0,
  "InpStopATR": 3.5,
  "InpTargetR": 1.5,
  "InpTrailingMode": 1,
  "InpTrailATR": 3.5,
  "InpBreakEvenAtR": 0.0,
  "InpPartialExitAtR": 0.0,
  "InpPartialExitFraction": 0.5,
  "InpMomentumExitMode": 2,
  "InpMomentumFadeFraction": 0.5,
  "InpMaximumHoldH1Bars": 0,
  "InpDynamicTriggerFraction": 0.5,
  "InpDynamicLockFraction": 0.2,
  "InpSessionStartHourUTC": 0,
  "InpSessionEndHourUTC": 24,
  "InpWeekdayMask": 62
}
```

Enhanced verdicts: recommended **WATCH_ONLY**, high-WR **WATCH_ONLY**, XAG **REJECT**.

No backtest can guarantee future profitability. A candidate is considered defensible only if it remains positive in both the purged validation year and locked real-tick year with position-level PF above 1.
