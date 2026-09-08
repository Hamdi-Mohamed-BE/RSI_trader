# Weekend Gap Reversal — Full Pipeline Plan

The existing `backtest_weekend_gap_reversal.py` remains the untouched raw-paper
replication. This second study engineers a stop-defined 1%-risk version and is
research-only until reviewed.

## Markets

EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD and EURJPY only.

## Frozen periods

- Train: 2023-09-01 to 2024-09-01
- Development validation: 2024-09-01 to 2025-09-01
- Untouched locked year: 2025-09-01 to 2026-09-01

## Search

- Rolling distributions: 52, 104, 156 and 260 weeks.
- Extreme-gap tails: 2.5%, 5%, 7.5%, 10% and 15%.
- Execution timeframes: M15, M30 and H1.
- Entry delays after the broker-week open: 0, 1, 2, 4, 8 and 12 hours.
- Paper, inverse, long-only and short-only direction.
- Raw, first-bar reversal/momentum, EMA, volatility and relative-volume filters.
- ATR, gap-sized and swing stops.
- Timed, gap-fill, 0.5R–4R and adaptive targets.
- No management, breakeven, ATR trail and Dynamic 50/20.
- 24, 48, 72 and 120-hour or Friday-close maximum holds.

## Costs and gates

- 1% current-equity risk per trade.
- Retail spread floor plus 0.4 pip commission/slippage.
- Locked-year test with an extra 1 pip cost stress.
- 5,000-path block Monte Carlo.
- Weekly strategies require at least 10 locked trades per pair; all train,
  validation, locked and stressed returns must be positive; locked PF must be
  at least 1.20; DD at most 15%; and Monte Carlo P5 must be positive.

