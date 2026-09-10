# DMC H4 Fresh-Ladder — Native MT5 XAU and US100 Research

Research only. No active EA, recommended installer, website data or live terminal was changed.
All results use Exness native MT5 real ticks, modeled costs and 1% dynamic equity risk.

## Rule definition

- Levels: completed H4 candle-body highs and lows, clustered within 0.10 H4 ATR.
- Freshness: strict first M15 touch after the H4 level becomes available.
- Target: next rail on the same H4 ladder.
- Maximum frequency: two trades per UTC day.
- No-lookahead stop variants: immediate touch with a known ATR/prior-bar stop, or entry after the M15 touch bar closes with its now-known extreme.

## XAU development screen — 2023-09-01 to 2025-08-31

| Variant | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| touch-atr-0p75 | -91.80% | 0.72 | 36.02% | 92.08% | 1227 | -5.00 | -0.98 |
| touch-atr-1p00 | -81.32% | 0.79 | 43.92% | 83.08% | 1225 | -5.00 | -0.92 |
| touch-prior-m15 | -98.12% | 0.49 | 26.02% | 98.12% | 1126 | -5.00 | -1.00 |
| confirmed-touchbar | -69.19% | 0.82 | 41.17% | 70.79% | 1144 | -5.00 | -0.97 |

Frozen XAU selection: **confirmed-touchbar**.

## Frozen version validation

| Market / period | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| XAU locked — 2025-09-01 to 2026-09-01 | -30.14% | 0.91 | 39.16% | 41.81% | 572 | -3.78 | -0.61 |
| XAU full — 2023-09-01 to 2026-09-01 | -76.23% | 0.84 | 40.39% | 76.98% | 1711 | -5.00 | -0.98 |
| US100 development — frozen XAU rules | -97.11% | 0.49 | 32.52% | 97.14% | 1104 | -5.00 | -1.00 |
| US100 locked — frozen XAU rules | -70.78% | 0.67 | 37.04% | 75.01% | 575 | -5.00 | -0.94 |
| US100 full — frozen XAU rules | -99.16% | 0.50 | 30.91% | 99.30% | 1524 | -5.00 | -1.00 |

## Monte Carlo — frozen three-year trades

| Market | Trades | P(profit) | Return P5 / median / P95 | DD median / P95 |
|---|---:|---:|---:|---:|
| XAU | 1711 | 0.48% | -90.34% / -76.56% / -42.10% | 80.55% / 91.50% |
| US100 | 1524 | 0.00% | -99.68% / -99.16% / -97.83% | 99.21% / 99.69% |

## Frozen configuration

```json
{
  "InpEnableTrading": true,
  "InpRiskPercent": 1.0,
  "InpMagic": 1091001,
  "InpMaxTradesPerDay": 2,
  "InpMaxSpreadPoints": 0,
  "InpH4LookbackBars": 360,
  "InpATRPeriod": 14,
  "InpDuplicateLevelH4ATR": 0.1,
  "InpTouchToleranceM15ATR": 0.05,
  "InpMaximumPriorM15Touches": 0,
  "InpEntryMode": 1,
  "InpStopMode": 2,
  "InpStopM15ATR": 1.0,
  "InpStopBufferM15ATR": 0.02,
  "InpConfirmedRequireOpenOnApproachSide": true,
  "InpTargetFrontRunM15ATR": 0.0,
  "InpMinimumRR": 0.0,
  "InpMaximumRR": 20.0,
  "InpMaximumStopM15ATR": 8.0,
  "InpUseUTCSession": false,
  "InpSessionStartHourUTC": 0,
  "InpSessionEndHourUTC": 24
}
```

## Decision

- **XAU: reject.** Every no-lookahead raw implementation lost money in development. The least-bad confirmed version also failed the untouched year and the full three-year period.
- **US100: reject.** The XAU-frozen rule transfer lost money in development, the untouched year and the full three-year period.
- **Do not optimize this raw strategy.** PF below 1.0 in every relevant window indicates a missing entry edge, not merely an imperfect stop or session.
- **Do not change the current DMCs.** The existing XAU baseline and separate Fresh Reaction candidates remain the supported versions.

These results test the transparent Calyx interpretation of the screenshot: completed H4 candle-body rails. The screenshot does not disclose how its proprietary levels are generated, so this rejects that mechanical interpretation rather than independently reproducing the creator's unpublished backtest.
