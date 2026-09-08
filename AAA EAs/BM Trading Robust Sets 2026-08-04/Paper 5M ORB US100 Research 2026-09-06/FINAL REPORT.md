# US100 paper-style 5-minute ORB — native MT5 audit

## Decision

**WATCH ONLY — positive, but not robust enough for the active portfolio.**

The exact paper cannot be reproduced on one US100 CFD because its strongest rule ranks the top 20 stocks cross-sectionally by opening relative volume. This audit tests the portable single-instrument analogue on Exness USTEC using broker tick activity.

## Test design

- Development: 2023-09-01 to 2025-08-31, MT5 1-minute OHLC, sequential parameter selection.
- Locked test: 2025-09-01 to 2026-09-01, MT5 Every Tick, broker spread/costs and random delay.
- Full reference: 2023-09-01 to 2026-09-01, MT5 Every Tick.
- Risk: exactly 1% of dynamic equity per trade. One trade maximum per session.
- Monte Carlo: 10,000 five-trade block-bootstrap paths from untouched locked-year trades.

## Locked-year comparison

| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Raw paper analogue | +17.80% | 1.09 | 21.34% | 24.59% | 239 | 1.48 | 0.68 |
| Paper + relative volume | -16.37% | 0.82 | 16.13% | 22.16% | 124 | -3.39 | -0.74 |
| Development-selected | +15.61% | 1.72 | 30.77% | 10.60% | 26 | 11.44 | 1.14 |

## Selected three-year reference

| Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---:|---:|---:|---:|---:|---:|---:|
| +62.53% | 1.88 | 33.33% | 10.60% | 78 | 12.75 | 3.25 |

## Selected inputs

- open-volume: `rv150`
- range: `or5-paper`
- entry: `close-m15`
- stop: `dailyatr15`
- exit: `eod-paper`
- management: `none-paper`
- window: `window180`
- direction: `both`
- session: `ny-0930-paper`
- filter: `none`

## Monte Carlo

- Chance of profit: 82.29%
- Return P5 / median / P95: -9.69% / +14.55% / +44.18%
- Max drawdown median / P95: 7.20% / 15.35%

## Interpretation

The paper's reported stock-universe result must not be presented as a US100 CFD expectation. Only the locked MT5 line above is the honest evidence for this implementation. No portfolio, BAT, or website files were changed by this research run.

## Existing US100 ORB comparison

| Version | Locked return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | 3-year return | 3-year PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Existing safer NY ORB | +9.66% | 1.68 | 48.15% | 4.76% | 27 | 10.26 | 1.87 | +36.94% | 2.15 |
| New paper-derived ORB | +15.61% | 1.72 | 30.77% | 10.60% | 26 | 11.44 | 1.14 | +62.53% | 1.88 |

The new version makes more in this sample, but the existing ORB has materially lower drawdown, higher win rate and stronger recovery. Keep the existing ORB in the active system; forward-test the new version separately.
