# Step 3 — Slow Multi-Asset Trend Basket

Research only. No production installer, website manifest, or live MT5 profile is changed by this package.

## Fixed protocol

- Markets: XAUUSD, XAGUSD, BTCUSD, ETHUSD, USTEC, US30, EURUSD, GBPJPY.
- Development: 2023-09-01 through 2025-08-31.
- Locked validation: 2025-09-01 through 2026-08-31.
- Full three-year context: 2023-09-01 through 2026-08-31. This includes the development sample and is not an out-of-sample claim.
- Risk: 1% of current equity per new trade. Combined portfolio risk is capped at 4% when portfolio results are constructed.
- Signal inputs are frozen before the locked year is read for model selection.
- Costs: recorded broker spread in the broad screen plus a conservative execution/financing allowance; native MT5 validation uses the broker model, swap, spread, and random execution delay.

## Test matrix

- Signal timeframe: H4, D1, W1.
- Momentum: combinations of approximately 1, 3, 6 and 12 months.
- Trend filter: none, EMA100, EMA200, and rising-EMA confirmation.
- Direction: long/short and long-only (especially for US indices and crypto).
- Entry timing: first available/all-day, Asia, London, New York, and London–New York overlap.
- Stop: ATR, recent swing, or chandelier boundary.
- Exit: signal reversal, 0.5R through 6R, time exit, or adaptive RR.
- Management: none, breakeven, ATR trail, chandelier trail, and the M15 50%-to-20% dynamic stop.

## Acceptance gate

A market is not recommended from development performance alone. The locked year should have positive net return, PF above 1.10, tolerable drawdown, enough trades for its slow frequency, and no obvious dependence on one exceptional trade. The combined basket is also evaluated with block-bootstrap Monte Carlo and cost stress.
