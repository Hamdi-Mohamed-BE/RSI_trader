# Step 5 — Month-End Institutional Flow

> Deployment update (2026-09-06): the validated US100 M30 configuration was promoted to every portfolio BAT at a hard 1% risk. US30 remains rejected and is not installed.

## Decision

**Recommend US100 for a separate fixed-1% demo-forward allocation; keep US30 out of the active system for now.** US100 passes every locked gate with contained drawdown. US30 is profitable in native MT5, but its 13.53% locked drawdown and negative Monte Carlo downside make it too fragile for promotion.

The calendar rule is known before entry and uses Monday-Friday calendar positions, so it does not inspect future bars to discover the final trading day. The research basis is the documented turn-of-the-month return concentration from the last business day through the first three business days; institutional liquidity and portfolio rebalancing are plausible mechanisms, not guarantees.

## Native MT5 locked-year results

| Asset | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| USTEC | +5.53% | 1.34 | 47.06% | 5.74% | 34 | 5.33 | 0.95 |
| US30 | +7.02% | 1.30 | 30.77% | 13.53% | 39 | 2.66 | 0.52 |

Period: 2025-09-01 to 2026-09-01. Native MT5 generated Every Tick, random execution delay, broker spread, commission and swap; USD 10,000 start and fixed 1% equity risk.

## Frozen configurations

### USTEC

- timeframe=M30, window=first3, entry_time=ny-first-hour, confirmation=none, trend=none, direction=long-only, max_hold_hours=6, stop_mode=atr, stop_value=1.5, rr=2.5, management=none

### US30

- timeframe=H1, window=classic, entry_time=ny-first-hour, confirmation=none, trend=none, direction=long-only, max_hold_hours=24, stop_mode=atr, stop_value=1.5, rr=6.0, management=none

## Three-year native context

| Asset | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| USTEC | +36.49% | 1.61 | 50.00% | 9.12% | 104 | 9.29 | 2.95 |
| US30 | +31.15% | 1.42 | 37.07% | 13.16% | 116 | 3.15 | 1.91 |

The three-year rows include the development period and are context, not independent validation.

## Native locked-trade Monte Carlo

| Asset | Profit probability | Return P5 | Median return | Return P95 | Median DD | DD P95 | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| USTEC | 78.38% | -5.24% | +5.36% | +18.77% | 4.84% | 9.20% | 34 |
| US30 | 67.37% | -13.92% | +6.80% | +38.21% | 9.69% | 18.32% | 39 |

Bootstrap: 10,000 three-trade moving-block resamples of the same locked native trades. It estimates sequencing risk but cannot create new market regimes or solve a small sample.

## Pipeline coverage

The pre-lock search tested M5/M15/M30/H1, London open/New York open/first-hour/power-hour entries, eight turn-of-month windows, three direction modes, seven daily filters, three candle confirmations, 6/12/24/72/120-hour holds, seven stop variants, RR 0.5/0.75/1/1.5/2/2.5/3/4/6, and no management/break-even/ATR trail/Dynamic M15 50/20. The selected configurations both retained no trailing.

## Evidence limits

- CFD broker hours and D1 candles differ from exchange futures sessions.
- The effect is calendar-based and can weaken as flows, index composition and execution costs change.
- Native MT5 Sharpe can look unusually high on sparse event trades; PF, drawdown, trade count and Monte Carlo downside carry more decision weight.
- US100 should remain demo-only until at least 30-50 forward trades confirm implementation and slippage.

## Files

- `selection-lock.json`: frozen pre-lock choices.
- `all-screen-results.csv`: every staged pre-lock configuration.
- `rr-sensitivity.csv`, `stop-sensitivity.csv`, `management-sensitivity.csv`, `calendar-session-timeframe-sensitivity.csv`: pipeline comparisons.
- `native-results.csv`, `native-monte-carlo-summary.csv`, `rolling-stability.csv`: final evidence tables.
- `Charts/`: locked equity, metrics, RR, rolling and Monte Carlo graphs.
