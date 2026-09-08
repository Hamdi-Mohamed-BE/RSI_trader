# Step 5 — Conditional FX Momentum

Research only. No EA, SET, BAT, website, cache, or recommended-portfolio file
may change before the locked-year result is reviewed and native MT5 confirmation
is completed.

## Goal

Test causal intraday momentum on EURUSD and GBPJPY, entering only when a
completed-bar breakout, a directional EMA, and an optional walk-forward market
regime agree.

## Frozen research protocol

- Exness M15 broker bars with recorded spread; M30, H1 and H4 are resampled.
- Development train: 2023-09-01 to 2024-09-01.
- Development validation: 2024-09-01 to 2025-09-01.
- Untouched locked year: 2025-09-01 to 2026-09-01.
- Three-year context: 2023-09-01 to 2026-09-01.
- Exactly 1% current-equity risk per trade.
- Stops are evaluated before targets when both are touched in one bar.
- Recorded spread plus a 0.02R commission/slippage allowance is included.

## Search

- Timeframes: M15, M30, H1 and H4.
- Sessions: all day, Asia, London, New York and London/New York overlap.
- Breakout lookbacks: 10, 20 and 40 completed bars.
- EMA filters: 50, 100 and 200.
- Direction: both, long only and short only.
- Regime: none, causal Bull/Bear state, walk-forward Markov confirmation,
  Markov buffers, normal-volatility gating, and the documented 20-bar/5%
  reference state.
- Stops: 0.75–2 ATR, 5/10/20-bar swing and opposite structure.
- Targets: 0.5R, 0.75R, 1R, 1.5R, 2R, 2.5R, 3R, 4R, 6R and adaptive RR.
- Management: none, breakeven, 1.5 ATR trail and Dynamic 50/20.
- Maximum holding time: 24, 72, 120 hours or no timed exit.

## Promotion gate

Each market must be profitable in development train, development validation,
the locked year, extra-cost stress and Monte Carlo P5; locked PF must be at
least 1.20 with at least 30 trades and no more than 15% drawdown. The
conditional version must materially improve the otherwise identical ungated
version. Passing research still requires native MT5 Every Tick confirmation.
