# US100 Momentum Continuation Improvement Test

## Decision

**Do not replace the active BAT EA.** The screenshot-derived H1 gate looked attractive in development but failed the untouched 2025–2026 holdout. The literal H1 strategy also failed. The current NY-open EA remains the strongest tested version.

## What was reconstructed

1. **Long-only:** exploit the positive long-run drift of the Nasdaq.
2. **24-hour momentum:** completed H1 close minus the close 24 bars earlier must exceed 0.5 ATR.
3. **Range leadership:** the completed close must be in the top 25% of its trailing 48-bar high-low range.
4. **Trend:** EMA(100) must be rising.
5. **Ride and trail:** enter the next H1 bar, use a 2.5 ATR initial/trailing stop and close after at most 120 H1 bars.

Two implementations were tested: the literal standalone H1 system and the same filters used only as a gate for the existing 09:30–09:35 New York M5 signal.

## Development screen — 2019-07-16 to 2024-12-31

| Variant | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|
| Current BAT EA | +138.07% | 1.10 | 38.27% | 29.04% | 1398 |
| Current entry, long only | +134.56% | 1.20 | 42.05% | 16.60% | 711 |
| Current entry + screenshot H1 gate | +61.58% | 1.37 | 45.59% | 12.05% | 261 |
| Literal screenshot H1 strategy | +48.38% | 1.11 | 38.47% | 25.35% | 1318 |

The exact gate appeared to improve PF from 1.10 to 1.37 and reduce drawdown from 29.04% to 12.05%. These results were used only to decide what to carry forward.

## Locked holdout — 2025-01-01 to 2026-08-27

| Variant | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|
| Current BAT EA | +50.84% | 1.17 | 41.47% | 17.18% | 422 |
| Current entry, long only | +19.42% | 1.15 | 43.07% | 13.01% | 202 |
| Current entry + screenshot H1 gate | -1.67% | 0.96 | 41.56% | 14.96% | 77 |
| Literal screenshot H1 strategy | -5.96% | 0.95 | 39.36% | 26.39% | 404 |

On untouched data, the exact H1 gate changed return from +50.84% to -1.67%, PF from 1.17 to 0.96, and trades from 422 to 77. This is a failed robustness test, not an improvement.

## Last year — 2025-08-28 to 2026-08-27

| Variant | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|
| Current BAT EA | +33.09% | 1.19 | 41.02% | 13.40% | 256 |
| Current entry, long only | -1.18% | 0.98 | 38.71% | 12.96% | 124 |
| Current entry + screenshot H1 gate | +2.99% | 1.12 | 42.00% | 6.66% | 50 |
| Literal screenshot H1 strategy | -0.08% | 1.00 | 40.82% | 23.89% | 245 |

The gate reduced last-year drawdown, but it discarded too many profitable signals: return fell from +33.09% to +2.99%.

## Bootstrap diagnostic — locked trades, 4,000 resamples

| Variant | Chance profitable | Median return | 5–95% return | Median max DD | 95th-percentile DD |
|---|---:|---:|---:|---:|---:|
| Current BAT EA | 90.5% | +51.5% | -9.5% to +151.2% | 19.3% | 34.2% |
| Screenshot H1 gate | 44.2% | -1.6% | -17.1% to +18.0% | 11.1% | 20.9% |

Bootstrap paths resample the same locked trade returns and therefore measure sequencing uncertainty, not future market-regime uncertainty.

## Test integrity

- Broker: Exness, USTEC CFD.
- Initial balance: $10,000.
- Risk: 1% of current equity per trade for apples-to-apples comparison.
- Development: MT5 1-minute OHLC screen, 98% broker history quality.
- Locked and last year: MT5 Every Tick, 100% history quality.
- Broker spread, commission, swap and random execution delay were included.
- Rules were frozen before the locked test.
- Active BAT, active preset and website were not changed.
