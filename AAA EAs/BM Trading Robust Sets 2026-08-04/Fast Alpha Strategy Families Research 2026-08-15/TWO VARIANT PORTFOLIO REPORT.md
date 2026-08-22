# XAU Trend Baseline + Fast-Alpha Portfolio

## Important interpretation

These are two versions of the same XAU trend signal, not two independent strategies. Their monthly returns correlate at 0.90 and 85.7% of baseline entries have a fast-alpha entry within 35 minutes. Running both mostly doubles the same idea.

The preferred comparison assigns 0.5% risk to each version, keeping combined planned risk near 1% when both trades are open. Results are reconstructed as two equal virtual sleeves. Drawdown below is closed-trade drawdown; conservative live planning should allow 10–12% marked-equity drawdown because both positions may move against the account simultaneously.

## Preferred risk: 0.5% + 0.5%

| Metric | Available history | Locked last year |
|---|---:|---:|
| Period | 2021-08-10 to 2026-08-07 | 2025-08-08 to 2026-08-07 |
| Initial balance | $10,000.00 | $10,000.00 |
| Final balance | $14,912.02 | $12,274.99 |
| Net profit | $4,912.02 | $2,274.99 |
| Return | +49.12% | +22.75% |
| Profit factor | 1.59 | 2.35 |
| Closed-trade max DD | 6.98% | 4.80% |
| Conservative marked-DD planning | 10–12% | 7–9% |
| Trades | 235 | 53 |
| Wins / losses | 89 / 146 | 24 / 29 |
| Win rate | 37.87% | 45.28% |
| Gross profit | $13,271.82 | $3,961.29 |
| Gross loss | -$8,359.80 | -$1,686.31 |
| Largest win | $224.04 | $188.42 |
| Largest loss | -$120.99 | -$101.76 |
| Average win | $149.12 | $165.05 |
| Average loss | -$57.26 | -$58.15 |

## Calendar returns at 0.5% + 0.5%

2021 and 2026 are partial years.

| Year | Return |
|---|---:|
| 2021* | -3.97% |
| 2022 | -0.25% |
| 2023 | +14.56% |
| 2024 | +6.83% |
| 2025 | +18.28% |
| 2026* | +7.65% |

## Aggressive comparison: 1% + 1%

This creates roughly 2% planned risk on one highly correlated XAU idea.

| Metric | Available history | Locked last year |
|---|---:|---:|
| Return | +98.24% | +45.50% |
| Profit factor | 1.59 | 2.35 |
| Closed-trade max DD | 13.97% | 8.04% |
| Conservative marked-DD planning | 20–24% | 14–18% |

The aggressive version is not recommended for the active multi-EA portfolio.

## Decision

Running both at 0.5% each produces less return than running the fast-alpha version alone at 1% (+49.12% versus +52.89%) and does not provide meaningful diversification. The preferred design remains one fast-alpha EA at 0.5% while other portfolio bots are active. If both versions are deliberately deployed for live comparison, cap them at 0.5% each and treat them as one XAU risk bucket.
