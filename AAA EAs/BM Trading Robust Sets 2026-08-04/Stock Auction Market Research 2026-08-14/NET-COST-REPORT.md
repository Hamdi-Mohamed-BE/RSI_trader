# Net-Cost Stock / S&P 500 Backtest

Run date: 2026-08-14  
Starting balance: USD 10,000  
Risk: 1% of current equity per trade  
Data: MEXAtlantic-Demo M1, 2022 through 2026-08-13/14  
Deployment: no BAT or active portfolio change

## Cost assumptions actually applied

- **Spread:** the exact historical M1 broker spread at each entry was already included in the original execution engine.
- **Slippage:** 25% of the instrument's median spread was charged at entry and again at exit.
- **Commission:** USD 0. MEXAtlantic-Demo account history contained zero commission and zero separate fees across all 140 audited trade deals. The broker also advertises zero-commission Standard/Pro accounts and 0% index commission.
- **US500 financing:** the current MEXAtlantic MT5 long-swap specification of **-6.93181% annual interest / 360** was charged using every trade's actual calendar holding time.
- **Share-CFD financing:** the current MEXAtlantic-Demo stock specifications report zero long swap for the tested `.OQ` and `.N` symbols, so no invented charge was added.
- **Dividend cash adjustments:** unavailable in the broker M1 files and therefore not modeled.

MEXAtlantic does not provide historical swap-rate snapshots through the downloaded M1 files. Consequently, the 2026-08-14 swap specification was applied consistently across the full history. This is a transparent estimate, not proof of the exact financing charged in 2022-2025.

The strategy configurations and trades were kept locked. They were not reselected after adding the cost layer.

## Revised net results

| Asset | Return before all costs | After spread + slippage | Final net return | Total cost impact | PF | Win rate | Max DD | Modeled debit costs | 2026 net return |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S&P 500 | +34.19% | +32.76% | **+27.43%** | -6.76 pp | 3.29 | 53.13% | 4.51% | $600.53 | -0.71% |
| NVDA | +22.91% | +21.11% | **+21.11%** | -1.80 pp | 3.35 | 63.64% | 5.15% | $158.34 | +0.97% |
| AAPL | +18.43% | +17.38% | **+17.38%** | -1.05 pp | 2.12 | 37.50% | 7.77% | $93.36 | +0.15% |
| MSFT | +14.39% | +13.73% | **+13.73%** | -0.67 pp | 2.89 | 25.00% | 5.74% | $62.59 | -2.00% |
| AMZN | +14.92% | +13.52% | **+13.52%** | -1.40 pp | 2.22 | 30.43% | 6.22% | $128.59 | -2.02% |
| GOOGL | +16.94% | +15.34% | **+15.34%** | -1.60 pp | 2.81 | 50.00% | 6.71% | $147.16 | -1.01% |
| META | +31.53% | +30.07% | **+30.07%** | -1.47 pp | 3.96 | 57.14% | 5.01% | $124.73 | -1.00% |
| AVGO | +19.24% | +16.57% | **+16.57%** | -2.67 pp | 2.88 | 61.90% | 6.22% | $226.63 | 0.00% |
| AMD | +24.02% | +23.53% | **+23.53%** | -0.49 pp | 3.47 | 54.55% | 5.10% | $42.44 | +4.72% |
| INTC | +40.26% | +32.86% | **+32.86%** | -7.39 pp | 2.38 | 36.36% | 12.02% | $651.12 | -5.90% |
| TSLA | +49.40% | +46.99% | **+46.99%** | -2.41 pp | 3.11 | 17.50% | 22.14% | $193.90 | -0.24% |
| JPM | +13.54% | +11.78% | **+11.78%** | -1.76 pp | 3.22 | 57.89% | 2.00% | $160.55 | +1.50% |

`pp` means percentage points. Modeled debit costs are the sum of spread, slippage, commission and negative swap along the compounded $10,000 test path. They do not equal the return impact exactly because earlier costs also reduce the capital available for later trades.

## Cost breakdown

| Asset | Embedded spread | Embedded slippage | Commission | Swap cash flow | Total debit cost |
|---|---:|---:|---:|---:|---:|
| S&P 500 | $80.91 | $38.53 | $0.00 | -$481.09 | $600.53 |
| NVDA | $45.52 | $112.82 | $0.00 | $0.00 | $158.34 |
| AAPL | $62.74 | $30.62 | $0.00 | $0.00 | $93.36 |
| MSFT | $46.52 | $16.06 | $0.00 | $0.00 | $62.59 |
| AMZN | $90.14 | $38.45 | $0.00 | $0.00 | $128.59 |
| GOOGL | $99.63 | $47.53 | $0.00 | $0.00 | $147.16 |
| META | $95.19 | $29.54 | $0.00 | $0.00 | $124.73 |
| AVGO | $134.99 | $91.64 | $0.00 | $0.00 | $226.63 |
| AMD | $29.42 | $13.02 | $0.00 | $0.00 | $42.44 |
| INTC | $433.44 | $217.68 | $0.00 | $0.00 | $651.12 |
| TSLA | $141.92 | $51.98 | $0.00 | $0.00 | $193.90 |
| JPM | $115.76 | $44.78 | $0.00 | $0.00 | $160.55 |

## Interpretation

- All 12 configurations remain **REJECTED** under the 15% annual CAGR gate.
- AMD remains the best research/watchlist candidate, but its locked 2026 evidence contains only three trades.
- US500 is materially affected by overnight financing: total return falls from +32.76% after spread/slippage to +27.43% after financing.
- INTC has the highest embedded execution cost and still has unacceptable 2026 behavior and drawdown.
- TSLA still has unacceptable 22.14% maximum drawdown.
- Before any live deployment, the installer must read the live account's commission and symbol swap values again. The demo values are not a guarantee of live pricing.

## Output files

- `Results Net Costs 2026-08-14/summary-net-costs.csv`
- `Results Net Costs 2026-08-14/all-net-cost-results.json`
- `Results Net Costs 2026-08-14/all-net-cost-equity.png`
- `Results Net Costs 2026-08-14/<ASSET>-net-cost-result.json`
- `Results Net Costs 2026-08-14/<ASSET>-net-cost-trades.csv`
- `Results Net Costs 2026-08-14/<ASSET>-net-cost-equity.png`
