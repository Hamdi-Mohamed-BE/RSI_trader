# Hybrid CVD EA — final research report

## Honest outcome

| Status | Market | Final | Net / return | Max equity DD | PF | Win rate | Wins / losses | Trades | Quality |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FAIL | XAUUSD M5 | $7,780.39 | -$2,219.61 / -22.20% | $3,127.49 / 29.22% | 0.82 | 40.59% | 97 / 142 | 239 | 99% |
| WATCH | US30 M5 | $11,905.53 | $1,905.53 / +19.06% | $2,975.81 / 24.59% | 1.15 | 46.67% | 105 / 120 | 225 | 100% |
| WATCH | USTEC M5 | $10,436.31 | $436.31 / +4.36% | $2,222.12 / 19.21% | 1.05 | 42.68% | 70 / 94 | 164 | 100% |

## Test design

- Broker: Exness `Exness-MT5Trial16`; independent USD 10,000 account simulation per market.
- Training/selection: 2023-08-11 through 2025-08-10. The final choices required positive results in both one-year training halves.
- Untouched final test: 2025-08-11 through 2026-08-10.
- MT5 model: Every Tick generated from synchronized broker M1 history, random execution delay.
- Risk: 1% of current equity per trade; one position at a time per chart and session trade limits.
- XAU and US30 use M5 signals. US100 runs on an M5 chart but uses M15 signal bars internally.
- The main BAT/install pipeline was not modified and this EA was not deployed live.

## What Hybrid CVD means here

The EA combines an intrabar tick-volume CVD proxy, session VWAP, relative volume, EMA structure, breakout or divergence context, ATR stops, R-multiple targets, break-even, and ATR trailing. Exness CFD history does not contain exchange aggressor-tagged buy/sell volume. Therefore this is not true futures CVD; it estimates pressure from M1 direction and close location weighted by broker tick volume.

## Decision

- US30 met the 15% research return gate, but its 24.59% equity drawdown is too high for the existing portfolio and the PF is only 1.15. Keep research-only.
- US100 was slightly profitable but too weak to qualify.
- XAU failed out of sample and should not be traded.
- None of the three should be added to the main BAT at this stage.

## Files

- `Source/Hybrid CVD VWAP EA.mq5` and `.ex5`: source and compiled EA.
- `Sets/BEST - *.set`: selected settings for reproducibility, not live approval.
- `Backtest Reports/Final/*.htm`: native MT5 reports.
- `Backtest Reports/Final/*.png`: native MT5 equity/balance graphs.
- `Backtest Reports/Final/final-summary.csv` and `final-results.json`: extracted statistics.
- `Backtest Reports/Final/comparison-realized-balance.png`: comparison of closed-deal balance curves.
