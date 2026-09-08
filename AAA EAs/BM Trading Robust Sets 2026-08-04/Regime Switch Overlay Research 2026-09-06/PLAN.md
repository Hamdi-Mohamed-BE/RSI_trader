# Step 1 — Volatility-Regime Switch

## Goal

Test whether a causal Markov regime layer improves the already frozen 1% risk
momentum configurations on XAUUSD, XAGUSD, BTCUSD and USTEC. Where a separately
validated session-VWAP mean-reversion leg exists, also test a true regime switch:
directional momentum in Bull/Bear states and VWAP snapback in Sideways states.

## Evidence protocol

- Broker data: Exness MT5 history already acquired for the source research.
- Components: native MT5 trade ledgers from the frozen Slow Trend and Session
  VWAP studies. Those studies already searched timeframe, session, direction,
  stop, RR and management settings.
- Risk: fixed 1% per accepted trade.
- Development: 2023-09-01 through 2024-08-31.
- Validation: 2024-09-01 through 2025-08-31.
- Locked test: 2025-09-01 through 2026-08-31, inspected only after selection.
- Regime inputs use completed UTC daily bars only. The newest transition is not
  used when forecasting the next state.
- Markov grid: return windows 10/20/40/60 days, thresholds 2/3/5/8%, history
  126/252/504/all transitions, signal gates 0/3/5/10%, and Sideways probability
  gates 34/40/50%.
- Robustness: 10,000 five-trade block-bootstrap Monte Carlo paths.
- XAGUSD is mandatory portability evidence, not optional.

## Production rule

This is research only. No BAT, selected SET, EA default or website portfolio is
changed unless the locked evidence supports promotion and the user approves it.

