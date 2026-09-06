# Step 5 — Robust ORB Research

## Goal

Test the claimed 09:15–09:30 pre-open range against the official 09:30 New York opening range, then select range length, entry confirmation, relative-volume/trend filters, stop placement, RR, trade window and trailing behavior on development data only.

## Untouched locked-year results

| Decision | Market | Best configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | MC return P5 | MC DD P95 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| WATCH / insufficient robustness | Gold | 09:30 NY, OR15, 2.5R | +3.12% | 1.37 | 28.95% | 2.90% | 38 | 4.68 | 1.05 | -2.51% | 5.19% |
| REJECT | Silver | 09:30 NY, OR15, 4.0R | -0.92% | 0.90 | 44.83% | 7.00% | 29 | -1.63 | -0.13 | -9.03% | 10.61% |
| REJECT | Bitcoin | 09:15 NY, OR30, 1.0R | -7.73% | 0.72 | 44.83% | 9.92% | 58 | -5.00 | -0.77 | -17.14% | 18.51% |
| REJECT | US30 | 09:15 NY, OR15, 0.75R | -8.48% | 0.75 | 50.68% | 12.41% | 73 | -5.00 | -0.67 | -20.02% | 21.72% |
| REJECT | US100 | 09:30 NY, OR5, 1.5R | -4.49% | 0.90 | 41.25% | 10.97% | 80 | -2.90 | -0.40 | -18.10% | 21.30% |
| REJECT | GBPJPY | 03:00 NY, OR15, 1.5R | -3.94% | 0.86 | 37.78% | 11.23% | 45 | -3.01 | -0.34 | -15.84% | 18.04% |

## Three-year context

| Market | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gold | +25.73% | 1.58 | 33.33% | 5.72% | 150 | 8.26 | 3.88 |
| Silver | +4.47% | 1.36 | 43.90% | 6.72% | 41 | 4.95 | 0.61 |
| Bitcoin | +13.88% | 1.13 | 54.19% | 12.91% | 227 | 3.71 | 0.84 |
| US30 | +6.40% | 1.07 | 59.59% | 14.03% | 193 | 4.56 | 0.38 |
| US100 | +35.49% | 1.18 | 47.00% | 10.99% | 300 | 5.20 | 2.20 |
| GBPJPY | -3.20% | 0.96 | 40.16% | 13.04% | 127 | -0.97 | -0.24 |

## Timing verdict

09:15 New York is a pre-open range, not the official cash-market opening range. It was tested because of the supplied claim; the selected timing above is determined by development data and judged only by untouched locked-year performance.

## Integrity and execution

- Parameter selection used only 2023-09-01 through 2025-08-31 with MT5 1-minute OHLC.
- The untouched test is 2025-09-01 through 2026-09-01 and uses native MT5 Every Tick, Exness spread, commission, swap and random execution delay.
- The three-year run is context, not an independent validation because it includes development and locked data.
- All tests risk 1% of current equity, as required. One position maximum per session and the configured intraday flat time remain enforced.
- Exness volume is broker tick activity, not centralized futures/exchange volume. Relative-volume filters are therefore broker-specific.

## Research basis

- NYSE states that its opening auction process begins at 09:30 Eastern: https://www.nyse.com/trade/auctions
- Tsai et al. align index-futures ORB timing with the underlying stock-market open and report that shorter probing windows worked better in US markets: https://doi.org/10.1109/ACCESS.2019.2899177
- Mesfin's 2026 MNQ falsification study found no OHLCV signal family, including ORB, passed all cost-aware out-of-sample criteria. This is the reason for strict locked testing and rejection labels: https://arxiv.org/abs/2605.04004

Charts are under `Charts`, exact native reports under `Backtest Reports`, and the chosen 1% presets under `Sets`.
