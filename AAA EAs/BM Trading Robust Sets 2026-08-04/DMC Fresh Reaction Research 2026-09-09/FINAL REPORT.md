# DMC Fresh-Reaction Filter — Full Native MT5 Pipeline

Research was completed before deployment. On 2026-09-09 the user approved the current XAU control plus the Fresh-Reaction XAU and US100 candidates as three separate recommended-system entries. The shared installer, every active BAT, production EA files, website catalogue and fixed-period evidence caches are now synchronized at 33 EAs.
All cases used real-cost native MT5 testing and 1% dynamic equity risk.

## Step-by-step development decisions

| Step | Selected setting | Return | PF | Win rate | Max DD | Trades | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| Baseline | XAU H1, Asia, fixed 22.5, 3R, Dynamic 50/20 | +27.40% | 1.33 | 41.04% | 11.70% | 134 | Control reproduced: identical trade count and win rate to the archived run |
| Freshness | Allow one prior M15 touch | +25.06% | 1.76 | 47.54% | 6.27% | 61 | Keep |
| Reaction type | Rejection only | +25.06% | 1.76 | 47.54% | 6.27% | 61 | Regain modes added no value; reject them |
| Structural room | Off | +25.06% | 1.76 | 47.54% | 6.27% | 61 | 1.7R–3R gates destroyed the sample; reject them |
| LTF confirmation | H1 close | +25.06% | 1.76 | 47.54% | 6.27% | 61 | M15 break/retest left 6–9 trades; reject it |
| HTF confluence | W1/MN1 body within 0.25 D1 ATR | +33.78% | 2.57 | 56.52% | 4.67% | 46 | Keep as a filter only |
| Stop | Fixed 30.0 | +26.63% | 2.89 | 65.00% | 4.08% | 40 | Keep for XAU candidate |
| Reward/risk | 3R | +26.63% | 2.89 | 65.00% | 4.08% | 40 | Keep existing 3R |
| Management | Dynamic 50/20 | +26.63% | 2.89 | 65.00% | 4.08% | 40 | Keep existing management |

## XAU baseline versus selected candidate

| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current baseline — locked | +12.08% | 1.18 | 40.52% | 9.96% | 116 | 1.80 | 1.01 |
| Fresh Reaction — locked | +6.88% | 1.90 | 46.67% | 3.11% | 15 | 2.62 | 2.03 |
| Current baseline — 3 years | +46.72% | 1.27 | 40.80% | 12.49% | 250 | 1.52 | 2.89 |
| Fresh Reaction — 3 years | +36.18% | 2.49 | 60.00% | 4.08% | 55 | 3.77 | 7.24 |

## Frozen configuration selected from development data

```json
{
  "InpEnableTrading": true,
  "InpRiskPercent": 1.0,
  "InpRewardRisk": 3.0,
  "InpMagic": 1090901,
  "InpMaxSpreadPoints": 0,
  "InpTesterServerClockMode": 1,
  "InpUseMarkovRegimeFilter": false,
  "InpUseTrailing": true,
  "InpDmCSignalTimeframe": 16385,
  "InpDmCStopMode": 0,
  "InpDmCFixedStopPrice": 30.0,
  "InpDmCATRPeriod": 14,
  "InpDmCStopATR": 1.0,
  "InpDmCSignalBufferATR": 0.1,
  "InpUseDynamicTrailingSL": true,
  "InpDynamicTriggerFraction": 0.5,
  "InpDynamicLockFraction": 0.2,
  "InpResearchSession": 1,
  "InpResearchBrokerUtcOffsetMinutes": 180,
  "InpDmCFreshMode": 2,
  "InpDmCFreshTouchTimeframe": 15,
  "InpDmCFreshToleranceATR": 0.05,
  "InpDmCSignalMode": 0,
  "InpDmCRegainMaxBars": 1,
  "InpDmCRoomGateEnabled": false,
  "InpDmCMinimumRoomR": 2.0,
  "InpDmCRoomRequireMappedLevel": false,
  "InpDmCUseWeeklyMonthlyLevels": true,
  "InpDmCHTFProximityEnabled": true,
  "InpDmCHTFProximityATR": 0.25,
  "InpDmCConfirmMode": 0,
  "InpDmCM15StructureLookback": 4,
  "InpDmCConfirmExpiryHours": 2,
  "InpDmCWeekdaysOnly": false
}
```

## Cross-asset transfer

| Asset / version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| US100 legacy — locked | -9.31% | 0.85 | 36.84% | 25.34% | 95 | -1.86 | -0.31 |
| US100 candidate — locked | +3.68% | 1.88 | 66.67% | 2.99% | 12 | 1.38 | 1.18 |
| US100 legacy — 3 years | -34.89% | 0.79 | 34.17% | 43.26% | 319 | -2.42 | -0.81 |
| US100 candidate — 3 years | +17.94% | 1.99 | 65.22% | 4.39% | 46 | 6.15 | 3.93 |
| US30 legacy — locked | +4.49% | 1.07 | 40.82% | 13.40% | 98 | 0.72 | 0.31 |
| US30 candidate — locked | -7.37% | 0.48 | 28.57% | 10.34% | 14 | -4.70 | -0.69 |
| US30 legacy — 3 years | +0.22% | 1.00 | 37.58% | 26.56% | 330 | 0.01 | 0.01 |
| US30 candidate — 3 years | -3.30% | 0.90 | 46.15% | 10.36% | 52 | -1.74 | -0.30 |
| BTC legacy — locked | -16.07% | 0.91 | 35.42% | 35.43% | 319 | -0.97 | -0.43 |
| BTC candidate — locked | -9.30% | 0.86 | 34.34% | 23.27% | 99 | -0.95 | -0.34 |
| BTC legacy — 3 years | -57.86% | 0.85 | 34.59% | 66.30% | 954 | -1.59 | -0.87 |
| BTC candidate — 3 years | -4.44% | 0.98 | 37.73% | 30.06% | 273 | -0.15 | -0.11 |

## Monte Carlo — selected XAU 3-year trades

- Simulations: 10,000
- Probability of profit: 99.99%
- End return P5 / median / P95: +16.83% / +35.90% / +59.61%
- Max drawdown median / P95: 3.48% / 5.59%

## Deployment status — updated after user approval

- **DMC Current XAU: DEPLOYED AS A SEPARATE CONTROL.** The original H1 Asia/fixed-22.5/3R/Dynamic-50/20 model remains available and was not overwritten.
- **DMC Fresh Reaction XAU: DEPLOYED AS A SEPARATE WATCH EA.** PF, win rate and drawdown improved strongly, but the locked sample is only 15 trades and total three-year return is lower than the current baseline.
- **DMC Fresh Reaction US100: DEPLOYED AS A SEPARATE WATCH EA.** The transfer reverses a losing portable baseline, but the locked sample is only 12 trades.
- **US30: REJECT.** The locked candidate lost 7.37% with PF 0.48.
- **BTC: REJECT.** Weekdays reduced drawdown versus all-days, but both the locked and three-year candidates remained negative.
- **Risk:** all three non-News DMC entries follow the percentage selected by the user in every BAT and default to the tested 1%.
- **Website cache:** independent 6-month, 1-year, 3-year and 5-year native MT5 evidence and trade ledgers were saved for all three entries; the 33-EA portfolio caches were rebuilt.
