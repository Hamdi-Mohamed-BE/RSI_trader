# Step 2 — Relative-Strength Momentum Rotation

Research only until the locked test and portfolio-fit gate pass. Nothing is
added to the EA catalogue, BAT installers, recommended portfolio or website
merely because it performs well in development.

## Goal

Rank XAUUSD, XAGUSD, BTCUSD, ETHUSD, USTEC, US30, EURUSD and GBPJPY by
completed higher-timeframe momentum. Hold only the strongest eligible assets
instead of forcing exposure to every positive trend.

## Frozen protocol

- Source: archived Exness M15 bars and recorded spreads.
- Development selection: 2023-01-01 through 2025-08-31.
- Untouched locked test: 2025-09-01 through 2026-08-31.
- All ranking inputs use completed daily data; positions begin no earlier than
  the following executable M15 bar.
- Primary risk is 1% of current equity per trade.
- A maximum of four simultaneous positions caps initial stop risk at 4%.
- Stops are checked before targets when both are touched in one M15 bar.
- Recorded spread plus commission and holding-friction allowances are included.

## Search

- Weekly and monthly rebalancing.
- 12-month and 1/3/6, 1/3/12 and 3/6/12-month momentum ensembles.
- Top one through top four positions.
- Raw and volatility-adjusted ranking.
- Positive absolute-momentum gate on/off.
- Long-only and long/short ranking.
- No trend filter, EMA100 and EMA200 confirmation.
- All day, Asia, London, New York and London/New York overlap entry timing.
- ATR, swing and chandelier stop placement.
- 0.5R through 6R, adaptive RR, rank-change and timed exits.
- No management, breakeven, ATR trail, chandelier trail and Dynamic 50/20.

## Promotion gate

The locked year must be positive with PF at least 1.20, at least 40 trades,
closed drawdown no greater than 15%, positive additional-cost stress, positive
contribution from at least four assets, positive Monte Carlo P5 and materially
better evidence than the rejected shared-rule trend portfolio. Only a strategy
passing those gates is eligible for a correlation/incremental portfolio test.
