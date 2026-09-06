# Step 9.2 — BTC Top Down FVG Liquidity Re-audit

## Goal

Validate the deployed BTCUSD M15 configuration using the agreed pipeline: RR from 0.5R upward, structural-stop alternatives, break-even/holding/dynamic trailing, standalone sessions, a locked Every Tick year, a combined three-year Every Tick test, 1% equity risk, and 10,000-path Monte Carlo analysis.

## Work already completed and reused

The original 2026-08-27 research optimized 96 parameter passes on 2021-2024 data and selected H4 EMA bias, a 12-bar liquidity sweep, 0.9 ATR displacement, a six-bar FVG retest expiry, 2R target, no break-even and the structural sweep stop. The locked year subsequently returned +12.74% with PF 1.92 and 3.84% maximum equity drawdown.

The 2026-09-01 dynamic/session study was also reused as corroborating evidence. The new tests below fill the missing 0.5R/0.75R cases, stop-placement sensitivity and exact three-year comparison.

## Development — 2023-09-01 to 2025-08-31

Development used MT5 one-minute OHLC with broker costs and random execution delay. It was used only to select finalists.

### Reward/risk

| RR | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50R | -1.91% | 0.88 | 65.22% | 7.88% | 46 | -4.86 | -0.24 |
| 0.75R | -3.03% | 0.86 | 54.35% | 8.68% | 46 | -5.00 | -0.34 |
| 1.00R | +1.00% | 1.05 | 52.17% | 6.26% | 46 | 1.32 | 0.16 |
| 1.25R | +2.20% | 1.09 | 47.83% | 7.53% | 46 | 2.42 | 0.28 |
| 1.50R | +2.56% | 1.10 | 43.48% | 7.41% | 46 | 2.33 | 0.33 |
| **2.00R** | **+6.78%** | **1.23** | **39.13%** | **6.71%** | **46** | **5.00** | **0.95** |
| 2.50R | -4.24% | 0.87 | 28.26% | 13.82% | 46 | -2.43 | -0.29 |
| 3.00R | -8.02% | 0.75 | 23.91% | 14.95% | 46 | -3.85 | -0.53 |
| 4.00R | -8.30% | 0.75 | 21.74% | 14.78% | 46 | -3.50 | -0.55 |

The edge is concentrated around 2R. Lower headline RR raises the win rate but produces negative or marginal expectancy; RR above 2R fails sharply.

### Structural stop

| Buffer / minimum stop | Return | PF | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|
| 0.02 / 0.20 ATR | +5.29% | 1.18 | 7.77% | 47 | 3.79 | 0.64 |
| 0.05 / 0.30 ATR | +5.34% | 1.18 | 7.75% | 47 | 3.89 | 0.65 |
| **0.10 / 0.30 ATR — current** | **+6.78%** | **1.23** | **6.71%** | **46** | **5.00** | **0.95** |
| 0.10 / 0.50 ATR | +6.78% | 1.23 | 6.71% | 46 | 5.00 | 0.95 |
| 0.15 / 0.50 ATR | +3.35% | 1.11 | 7.12% | 46 | 2.54 | 0.44 |
| 0.25 / 0.50 ATR | +0.75% | 1.02 | 9.38% | 46 | 0.52 | 0.07 |
| 0.20 / 0.75 ATR | +6.71% | 1.23 | 7.08% | 46 | 4.78 | 0.86 |

The existing stop beyond the sweep extreme plus 0.10 ATR remains the best choice. The 0.30 versus 0.50 ATR minimum made no difference because the natural structural distances already exceeded both thresholds.

### Management and session candidates

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current exits, all day | +6.78% | 1.23 | 39.13% | 6.71% | 46 | 5.00 | 0.95 |
| Break-even at 1R | +7.08% | 1.31 | 52.17% | 6.40% | 46 | 6.03 | 1.06 |
| Dynamic 50%→20% | +7.93% | 1.30 | 45.65% | 6.58% | 46 | 6.57 | 1.11 |
| Asia only, current exits | +7.48% | 1.71 | 47.37% | 4.83% | 19 | 8.93 | 1.47 |
| Asia + dynamic 50%→20% | +7.36% | 1.76 | 52.63% | 4.61% | 19 | 9.57 | 1.50 |
| **Asia + break-even at 1R** | **+8.62%** | **2.14** | **63.16%** | **4.63%** | **19** | **11.67** | **1.76** |

## Locked year — 2025-09-01 to 2026-09-01

Finalists were fixed before this MT5 Every Tick test.

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Current exits, all day** | **+12.74%** | 1.92 | 50.00% | 3.84% | 26 | 17.20 | 3.15 |
| Break-even at 1R, all day | +9.47% | 1.74 | 40.74% | 3.93% | 27 | 15.16 | 2.31 |
| Dynamic 50%→20%, all day | +8.95% | 1.70 | 53.85% | 3.60% | 26 | 13.00 | 2.37 |
| **Asia only, current exits** | +8.83% | **2.65** | **58.33%** | **2.46%** | 12 | 7.89 | **3.41** |
| Asia + dynamic 50%→20% | +5.43% | 2.02 | 58.33% | 3.85% | 12 | 5.21 | 1.34 |
| Asia + break-even at 1R | +6.80% | 2.28 | 50.00% | 4.20% | 12 | 6.63 | 1.54 |

## Exact combined three years — 2023-09-01 to 2026-09-01

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current exits, all day | +15.41% | 1.29 | 41.57% | 8.05% | 89 | 5.01 | 1.87 |
| Break-even at 1R, all day | +14.38% | 1.33 | 32.22% | 6.49% | 90 | 5.99 | 2.19 |
| Dynamic 50%→20%, all day | +15.97% | 1.32 | 48.31% | 6.78% | 89 | 6.55 | 2.12 |
| **Asia only, current exits** | **+18.08%** | **2.03** | **51.52%** | **4.57%** | **33** | **17.37** | **3.74** |

## Monte Carlo — 10,000 five-day block-bootstrap paths

| Configuration | Profit probability | Return P5 / median / P95 | Median / P95 max DD | P(DD ≥10%) | P(DD ≥20%) | Ruin |
|---|---:|---:|---:|---:|---:|---:|
| Current exits, all day | 82.98% | -8.45% / +13.52% / +41.35% | 9.53% / 17.99% | 42.85% | 2.79% | 0% |
| Break-even at 1R, all day | 84.42% | -7.01% / +12.26% / +36.78% | 7.98% / 15.47% | 28.29% | 0.85% | 0% |
| Dynamic 50%→20%, all day | 86.72% | -5.82% / +13.83% / +39.78% | 8.16% / 15.44% | 30.46% | 0.84% | 0% |
| **Asia only, current exits** | **95.96%** | **+0.94% / +15.87% / +34.93%** | **4.10% / 8.27%** | **1.51%** | **0%** | **0%** |

## Recommendation for review

Use **Asia-only, current exits, 2R, structural sweep stop with 0.10 ATR buffer, no break-even and no dynamic trailing, at the fixed 1% risk** as the recommended/safe BTC configuration. It was profitable in development and locked data, and it leads the combined three-year and Monte Carlo risk-adjusted results.

Keep the existing all-day configuration available as the higher-frequency standard alternative. It has 89 three-year trades versus 33 for Asia-only, but materially weaker PF, drawdown, recovery and Monte Carlo downside.

The Asia result remains statistically modest at only 33 trades, so it should be classified as **keep cautiously / forward-test**, not a high-confidence core strategy.

## Configuration integrity

The exact three-year baseline report exposed and applied all 32 expected SET inputs. RR was 2.00, risk was 1.00%, dynamic trailing was false and research session was all-day. The only comparison mismatch was the intentionally unique research magic number. The production source and compiled EA do support the appended dynamic/session inputs; no executable repair was required.

Historical testing is not a guarantee of future performance.
