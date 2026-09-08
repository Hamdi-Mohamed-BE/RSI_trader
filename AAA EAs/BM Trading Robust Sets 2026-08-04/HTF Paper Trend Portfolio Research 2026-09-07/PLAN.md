# Step 1 — Paper-Based HTF Multi-Asset Trend Portfolio

Research only. Nothing in the live/recommended installer or website is changed before review.

## Goal

Test a single shared higher-timeframe trend rule across XAUUSD, XAGUSD,
BTCUSD, ETHUSD, USTEC, US30, EURUSD and GBPJPY. The design follows the
time-series-momentum literature: combine slow return horizons, size exposure
through a volatility-derived stop, diversify across markets, and cap risk.

## Fixed protocol

- Source data: archived Exness M15 broker bars and recorded spreads.
- Warm-up/history begins in 2022.
- Development selection: 2023-01-01 through 2025-08-31.
- Untouched locked test: 2025-09-01 through 2026-08-31.
- Primary context: 2023-01-01 through 2026-08-31.
- One configuration is selected for the whole basket before the locked year is read.
- Maximum planned risk is 1% of current equity per accepted trade.
- At most four concurrent trades are accepted, capping initial portfolio stop risk at 4%.
- Recorded spread plus conservative commission/financing friction is included.
- Same-bar ambiguity is resolved against the strategy: stop before target.

## Screen

- Signal timeframe: H4, D1 and W1.
- Momentum ensembles: 1/3/12 months, 1/3/6 months and 3/6/12 months.
- Trend confirmation: none, EMA100 or EMA200.
- Direction: long/short, long-only, or growth markets long-only with metals/FX long-short.
- Entry timing: all day, Asia, London, New York or overlap where applicable.
- Stop: ATR, swing or chandelier; 1.5, 2.5 and 3.5 ATR floors.
- Exit: signal reversal, 0.5R through 6R, adaptive RR, or 20/60/120-day time exit.
- Management: none, breakeven, ATR trail, chandelier trail or Dynamic 50/20.

## Acceptance

The locked basket must be positive with PF above 1.20, tolerable drawdown,
adequate trade count, positive cost stress and no dependence on one market.
Monte Carlo and six-month stability slices must also be reported. Backtests
are evidence, not proof or a forecast.
