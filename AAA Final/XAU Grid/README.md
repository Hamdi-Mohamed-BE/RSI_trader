# XAU Safe Grid

This is a risk-capped XAUUSD grid for MetaTrader 5. It automatically discovers the
broker's gold alias and uses the account already connected in the open MT5 terminal.

## Selected flow

- H4 and H1 trends must agree.
- A completed M15 candle must break a 12-candle price extreme with momentum.
- Three equal-sized stop entries scale into continuation at `0.10`, `0.35`, and
  `0.60` M15 ATR beyond the signal anchor.
- All legs share one stop at `1.00` ATR behind the anchor.
- The basket objective is `2.00` ATR beyond the deepest grid level.
- The full basket is sized to lose no more than `0.50%` of current balance at its
  initial stop. If the broker's minimum lot is too large, the setup is skipped.
- There is no martingale, lot multiplier, recovery grid, or adding after a loss.

## Safety controls

- 0.50% maximum planned basket risk
- 1.00% UTC daily loss circuit breaker
- 6.00% live equity drawdown circuit breaker
- 500% minimum margin-level filter
- $0.80 maximum XAU spread
- 60-minute pending-order expiry and six-hour maximum holding time
- Only orders with magic number `4080401` are managed

## Backtest method

MT5 M5 bid bars were used with the broker's historical spread. Signals use only
completed M15/H1/H4 bars. Buy fills use estimated ask prices, sell exits use ask,
and an ambiguous bar is resolved against the strategy (stop before target). Swap,
commission, latency, and gap slippage are not available in bar data and are not
included.

The 550-day research period was split chronologically into training, validation,
and a final 90-day holdout. The selected configuration passed the holdout gate,
but its PF of 1.12 is a modest edge rather than proof of future profitability.

## Run

- `run_optimize.bat` — rerun chronological optimization.
- `run_backtest.bat` — backtest the values currently in `.env`.
- `run_live.bat` — start the live monitor/executor. This file is never launched
  automatically.

Keep the first live use on demo or minimum size and collect at least 30 forward
trades before increasing risk.
