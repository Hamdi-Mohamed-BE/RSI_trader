# Online research EAs — Exness backtest and 15% annual-return gate

## Verdict

**Accepted EAs: none.** Six dedicated EA entry points were created and compiled with zero errors/warnings, covering nine symbol tests. The only parameter set that exceeded 15% CAGR in the two-year training window was BTC `b07`; it then lost 20.60% in the untouched final year, so it was rejected as unstable/overfit. Nothing was added to the active BAT.

## Test protocol

- Broker/symbol history: Exness demo, synchronized locally.
- Account: USD 10,000, leverage 1:2000.
- Risk: 1% per initial trade. Published Donchian pyramids can add units, so campaign exposure can exceed 1%.
- Baseline/full period: 2023-08-10 through 2026-08-06.
- Training screen: 2023-08-10 through 2025-08-06; 104 bounded variants.
- Untouched validation: 2025-08-07 through 2026-08-06.
- Final model: MT5 Every Tick generated from synchronized Exness M1 bars. Reported history quality is 98–100%. Exness did not provide the required historical real-tick archive for XAU, indices, or BTC, so no report is labeled real-tick.
- Acceptance gate: at least 15% training CAGR and at least +15% return in the untouched final year; profitable PF required.

## Published/default baseline — full three years

| Strategy / case | Symbol / TF | Return | CAGR | PF | Win rate | Max equity DD | Trades |
|---|---|---:|---:|---:|---:|---:|---:|
| XAU Pullback Window | XAUUSD M5 | -1.80% | -0.61% | 0.63 | 37.50% | 3.68% | 8 |
| FX Keltner Breakout | EURUSD D1 | -13.37% | -4.69% | 0.20 | 8.70% | 13.91% | 23 |
| FX Keltner Breakout | GBPUSD D1 | -14.68% | -5.17% | 0.02 | 4.55% | 15.10% | 22 |
| FX Keltner Breakout | USDCAD D1 | -11.49% | -4.00% | 0.23 | 11.11% | 14.06% | 18 |
| FX Keltner Breakout | NZDUSD D1 | -18.14% | -6.48% | 0.09 | 8.33% | 19.97% | 24 |
| US100 Alt22 Donchian | USTEC D1 | -17.14% | -6.09% | 0.50 | 32.58% | 24.94% | 89 |
| US500 Alt31 Donchian | US500 D1 | -2.05% | -0.69% | 0.90 | 50.72% | 11.09% | 69 |
| BTC Four-SMA | BTCUSD M5 | -4.24% | -1.44% | 0.98 | 36.04% | 34.25% | 541 |
| US30 Supply/Demand ATR | US30 H1 | -22.56% | -8.19% | 0.86 | 31.56% | 38.00% | 301 |

## Best training variant for each strategy/symbol

| Strategy / case | Symbol / TF | Return | CAGR | PF | Win rate | Max equity DD | Trades |
|---|---|---:|---:|---:|---:|---:|---:|
| XAU Pullback Window (`x04`) | XAUUSD M5 | +19.23% | +9.24% | 1.53 | 50.77% | 5.17% | 65 |
| FX Keltner Breakout (`eurusd-k01`) | EURUSD D1 | +3.84% | +1.91% | 1.31 | 26.92% | 12.83% | 26 |
| FX Keltner Breakout (`gbpusd-k01`) | GBPUSD D1 | +4.41% | +2.19% | 1.55 | 31.82% | 6.88% | 22 |
| FX Keltner Breakout (`usdcad-k11`) | USDCAD D1 | -0.06% | -0.03% | 0.98 | 20.00% | 5.75% | 5 |
| FX Keltner Breakout (`nzdusd-k09`) | NZDUSD D1 | -2.97% | -1.50% | 0.62 | 18.18% | 9.82% | 11 |
| US100 Alt22 Donchian (`ustec-d01`) | USTEC D1 | +2.79% | +1.39% | 1.20 | 41.18% | 7.23% | 34 |
| US500 Alt31 Donchian (`us500-d09`) | US500 D1 | +8.34% | +4.11% | 1.68 | 61.22% | 10.80% | 49 |
| BTC Four-SMA (`b07`) | BTCUSD M5 | +50.67% | +22.87% | 1.17 | 37.50% | 16.60% | 640 |
| US30 Supply/Demand ATR (`u09`) | US30 H1 | -6.69% | -3.42% | 0.83 | 23.08% | 18.00% | 52 |

## BTC training winner — validation failure

| Strategy / case | Symbol / TF | Return | CAGR | PF | Win rate | Max equity DD | Trades |
|---|---|---:|---:|---:|---:|---:|---:|
| BTC b07 untouched OOS | BTCUSD M5 | -20.60% | -20.60% | 0.81 | 30.77% | 26.12% | 299 |
| BTC b07 full period | BTCUSD M5 | +16.61% | +5.27% | 1.04 | 35.18% | 28.41% | 938 |

The full-period BTC result (+16.61% total, about +5.26% CAGR) is not a pass: its final year was sharply negative, PF was only 1.04 over the full period, and max equity drawdown reached 28.41%.

## Implementation scope

- `Research FX Keltner Breakout EA`: direct implementation of the published daily Keltner/ATR/exit-MA rules; tested on EURUSD, GBPUSD, USDCAD, NZDUSD.
- `Research US100 Alt22 Donchian EA` and `Research US500 Alt31 Donchian EA`: dedicated entry points sharing the tested Donchian/pyramid/trailing core.
- `Research BTC Four SMA EA`: implements the paper's four-SMA crossover and trailing factor rules; the paper does not publish one transferable universal parameter vector.
- `Research XAU Pullback Window EA`: reproduces the public state-machine logic and exposes ambiguous thresholds as inputs.
- `Research US30 Supply Demand ATR EA`: labeled as a core reconstruction because the paper does not specify its passive filters sufficiently for an exact clone.

## Files

- `ALL 104 TRAINING RESULTS.csv`: every screened variant.
- `BASELINE AND FINAL RESULTS.csv`: default baselines plus final BTC validation.
- `Backtest Reports`: native MT5 HTML reports and equity charts.
- `EA Packages`: per-EA source, EX5, sets, reports, and charts.
