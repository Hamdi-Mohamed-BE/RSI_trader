# US Stock / S&P 500 Auction-Market Backtest

Run date: 2026-08-14  
Broker feed: MEXAtlantic-Demo  
Account model: USD 10,000 starting balance, 1% risk per trade  
History: 2022-01-03 through 2026-08-13/14 (META begins 2022-06-12)  
Direction: long only  
Deployment status: research only; the active BAT/portfolio was not changed

## Honest result

No tested stock or index passed the predeclared gate of at least 15% CAGR with positive locked 2026 confirmation. Total return is not annual return. The strongest research candidate is AMD, but its 2026 result contains only three trades and is not sufficient evidence for deployment.

| Asset | MEXAtlantic symbol | TF | Trades | Win rate | PF | Total return | CAGR | Max DD | 2026 trades | 2026 PF | 2026 return | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| S&P 500 | US500 | D1 | 32 | 53.12% | 4.04 | +32.76% | 6.34% | 4.50% | 6 | 0.99 | -0.08% | REJECT |
| NVDA | NVDA.OQ | D1 | 22 | 63.64% | 3.35 | +21.11% | 4.24% | 5.15% | 2 | 1.99 | +0.97% | REJECT |
| AAPL | AAPL.OQ | H4 | 24 | 37.50% | 2.12 | +17.38% | 3.54% | 7.77% | 1 | 999.00* | +0.15% | REJECT |
| MSFT | MSFT.OQ | D1 | 24 | 25.00% | 2.89 | +13.73% | 2.83% | 5.74% | 3 | 0.00 | -2.00% | REJECT |
| AMZN | AMZN.OQ | H4 | 23 | 30.43% | 2.22 | +13.52% | 2.79% | 6.22% | 4 | 0.33 | -2.02% | REJECT |
| GOOGL | GOOGL.OQ | H4 | 16 | 50.00% | 2.81 | +15.34% | 3.15% | 6.71% | 1 | 0.00 | -1.01% | REJECT |
| META | META.OQ | D1 | 21 | 57.14% | 3.96 | +30.07% | 6.51% | 5.01% | 1 | 0.00 | -1.00% | REJECT |
| AVGO | AVGO.OQ | D1 | 21 | 61.90% | 2.88 | +16.57% | 3.38% | 6.22% | 0 | n/a | 0.00% | REJECT |
| AMD | AMD.OQ | D1 | 22 | 54.55% | 3.47 | +23.53% | 4.69% | 5.10% | 3 | 8.62 | +4.72% | REJECT |
| INTC | INTC.OQ | H4 | 33 | 36.36% | 2.38 | +32.86% | 6.36% | 12.02% | 6 | 0.00 | -5.90% | REJECT |
| TSLA | TSLA.OQ | H4 | 40 | 17.50% | 3.11 | +46.99% | 8.72% | 22.14% | 8 | 0.94 | -0.24% | REJECT |
| JPM | JPM.N | H4 | 19 | 57.89% | 3.22 | +11.78% | 2.45% | 2.00% | 1 | 999.00* | +1.50% | REJECT |

*PF 999 is the program's finite display value for a period with no gross loss. With only one confirmation trade, it is not meaningful evidence.

## Candidate ranking

1. **AMD — watchlist only.** Best locked-2026 result (+4.72%, PF 8.62), 5.10% full-sample DD, but only 22 total and 3 confirmation trades.
2. **NVDA — watchlist only.** Positive full sample and confirmation, but only 2 confirmation trades and 4.24% CAGR.
3. **S&P 500 — diversification/watchlist only.** Best broad exposure and 4.50% DD, but locked 2026 was slightly negative and CAGR was 6.34%.
4. **JPM — low-drawdown watchlist only.** Only 2.00% full DD, but just 2.45% CAGR and 19 trades.

Do not add INTC or TSLA in their tested configurations: their drawdowns were materially worse. The other candidates did not provide enough annual return or confirmation evidence.

## Test design

- Parameter development: 2022-2024.
- Out-of-sample validation used during selection: 2025.
- Locked confirmation, not retuned: 2026 through the latest available broker minute.
- Strategy family: 70% volume-value area built from 64 price bins; H4/D1 failed-auction and breakout/retest entries; 10/20/40/80-day composite profiles.
- Execution: recorded historical CFD spread, plus slippage equal to 25% of the instrument's median spread.
- Risk: equity compounded at 1% per trade. Max drawdown is calculated from minute-level marked equity; the charts show closed equity.
- Volume: MEXAtlantic supplies quote-tick volume, not consolidated exchange share volume.

## Data audit

All 12 requested candidate aliases resolved without a missing-symbol error. The resolver is non-fatal by design: an absent or unusable symbol is logged as MISSING/INCOMPLETE and the remaining candidates continue.

The raw MEXAtlantic stock files contained mechanical split gaps. Before any optimization, pre-split OHLC and spread were normalized to the current share basis:

- AMZN: 20:1, first split-adjusted session 2022-06-06.
- GOOGL: 20:1, first split-adjusted session 2022-07-18.
- TSLA: 3:1, first split-adjusted session 2022-08-25.
- NVDA: 10:1, first split-adjusted session 2024-06-10.
- AVGO: 10:1, first split-adjusted session 2024-07-15.

The remaining maximum daily gaps were reviewed and are plausible market/earnings gaps, not corporate-action discontinuities.

## Important limitations

- This is a research-engine backtest on broker M1 history, not a MetaTrader Strategy Tester report from a compiled stock EA.
- CFD overnight financing, dividend cash adjustments, exchange fees, rejected orders, and changing broker margin were not modeled.
- Individual-stock sample sizes are small; high full-sample PF values are therefore fragile.
- Results are from MEXAtlantic symbols and may not transfer to another broker's prices, trading hours, spreads, or stock-CFD contract rules.
- The current BAT and active portfolio remain unchanged. If candidates are approved later, the production installer should reuse the alias resolver and warn/skip missing symbols without stopping other EAs.

## Files

- `Data/manifest.json`: resolved broker symbols, coverage, spreads, and checksums.
- `Results/summary.csv`: complete numeric summary.
- `Results/all-results.json`: selected parameters and yearly metrics.
- `Results/all-markets-equity.png`: all 12 equity curves.
- `Results/<ASSET>-equity.png`: individual equity curves.
- `Results/<ASSET>-selected-result.json`: full result and selected configuration per asset.
- `Results/<ASSET>-selected-trades.csv`: trade-level evidence per asset.

