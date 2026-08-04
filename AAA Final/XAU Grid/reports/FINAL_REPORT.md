# XAU Safe Grid — selected configuration

## Configuration

| Item | Selected value |
|---|---:|
| Grid type | Positive momentum grid (stop entries) |
| Levels | 3 equal legs |
| Basket risk | 0.50% |
| Entry offsets | 0.10 / 0.35 / 0.60 M15 ATR |
| Common stop | 1.00 ATR behind anchor |
| Target | 2.00 ATR past deepest level |
| Session | 06:00–19:00 UTC |
| Break-even / trailing | Off |

## Chronological testing — $10,000 start

| Window | Dates (UTC) | Trades | Win rate | PF | Return | Max equity DD |
|---|---|---:|---:|---:|---:|---:|
| Training | 2025-01-31 to 2026-02-04 | 210 | 36.19% | 1.30 | +11.64% | 3.39% |
| Validation | 2026-02-04 to 2026-05-05 | 30 | 43.33% | 1.53 | +2.96% | 1.38% |
| Final holdout | 2026-05-05 to 2026-08-03 | 43 | 30.23% | 1.12 | +0.91% | 2.95% |
| Full 550 days | 2025-01-31 to 2026-08-03 | 290 | 35.52% | 1.23 | +12.64% | 3.39% |

Full-period ending balance: **$11,263.74**; net: **+$1,263.74**.

The holdout passed the defined gate (positive return, PF at least 1.10, at least
four trades, and DD below 8%). Its edge is thin, so live scaling should require a
forward sample. "Safe DD" here means historically bounded by the risk model; it
does not guarantee future drawdown.

## Scaling check

| Start | Risk | Trades | PF | Return | Max DD | End |
|---:|---:|---:|---:|---:|---:|---:|
| $5,000 | 0.50% | 150 | 1.27 | +7.57% | 2.98% | $5,378.70 |
| $10,000 | 0.25% | 146 | 1.27 | +3.64% | 1.55% | $10,364.09 |
| $10,000 | 0.50% | 290 | 1.23 | +12.64% | 3.39% | $11,263.74 |
| $10,000 | 1.00% | 295 | 1.21 | +29.19% | 7.92% | $12,918.75 |
| $25,000 | 0.50% | 307 | 1.23 | +15.88% | 4.62% | $28,969.81 |
| $100,000 | 0.50% | 307 | 1.23 | +17.25% | 4.72% | $117,251.71 |

Trade counts differ at smaller balances because setups are skipped whenever the
broker's 0.01 minimum lot would exceed the risk cap. The selected 0.50% setting is
the best balance of opportunity and drawdown from this test; 1.00% nearly doubles
historical DD and is not the default.
