# Top-Down FVG Liquidity — native MT5 validation

Research date: 2026-08-27

## Scope warning

This EA tests only a mechanical technical proxy. The transcript's macro, fundamental and crypto on-chain/order-book filters are not present in MT5 price history, so these results do not validate the speaker's full discretionary method.

## Results

| Symbol | Segment / model | Return | PF | Win rate | Equity DD | Trades | Quality |
|---|---|---:|---:|---:|---:|---:|---:|
| XAUUSD | Training / 1-minute OHLC | +13.44% | 1.40 | 50.00% | 8.32% | 62 | 98% |
| USTEC | Training / 1-minute OHLC | +13.86% | 1.83 | 61.36% | 4.79% | 44 | 98% |
| BTCUSD | Training / 1-minute OHLC | +18.44% | 1.70 | 47.73% | 6.83% | 44 | 100% |
| ETHUSD | Training / 1-minute OHLC | +27.00% | 3.73 | 57.89% | 6.34% | 19 | 100% |
| XAUUSD | Locked year / Every Tick | -6.48% | 0.45 | 20.00% | 9.49% | 25 | 99% |
| USTEC | Locked year / Every Tick | -8.18% | 0.45 | 15.38% | 8.42% | 26 | 100% |
| BTCUSD | Locked year / Every Tick | +12.74% | 1.92 | 50.00% | 3.84% | 26 | 100% |
| ETHUSD | Locked year / Every Tick | +11.46% | 1.67 | 40.00% | 6.68% | 25 | 100% |

## Selected parameters

| Symbol | Bias | Sweep bars | Displacement | Retest bars | RR | Break-even |
|---|---:|---:|---:|---:|---:|---:|
| XAUUSD | 1 | 12 | 0.9 ATR | 3 | 3R | 1R |
| USTEC | 1 | 36 | 0.6 ATR | 6 | 2R | 1R |
| BTCUSD | 1 | 12 | 0.9 ATR | 6 | 2R | 0R |
| ETHUSD | 1 | 24 | 0.6 ATR | 3 | 3R | 0R |

## Mechanical rules tested

1. H4 or H4+D1 EMA alignment is used as an objective proxy for the transcript's manually formed macro/fundamental bias.
2. An M15 candle must sweep a prior rolling extreme and close back through the swept liquidity level.
3. The next M15 candle must displace in the reversal direction by the configured ATR amount.
4. The third candle must leave a true three-candle fair-value gap; entry waits for a midpoint retest.
5. Stop loss is beyond the sweep extreme, the target is the selected fixed R multiple, and each trade risks 1% of current equity.

## Controls

- Per-symbol parameters were selected only on 2021-2024 1-minute-OHLC training history.
- The latest year, 2025-08-26 through 2026-08-26, was then run once with MT5 Every Tick and random execution delay.
- Native Exness symbol specifications, spread, commission and swap are included by the tester.
- The active BAT and website were not changed.

Equity graph: C:\Users\hama101\Desktop\geek\ai trader\AAA EAs\BM Trading Robust Sets 2026-08-04\Top Down FVG Liquidity Research 2026-08-27\Top Down FVG Liquidity - Locked Year Equity.png
