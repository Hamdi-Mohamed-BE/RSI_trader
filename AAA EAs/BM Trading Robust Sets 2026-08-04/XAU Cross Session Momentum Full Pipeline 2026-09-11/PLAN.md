# XAUUSD Cross-Session Momentum — Frozen Full Pipeline

Research only. No EA, website, BAT or live-account change is permitted by this
run. XAGUSD is excluded by the user's decision.

## Rule family

The paper's raw long-only rule buys a session when the immediately preceding
UTC session had a positive return. Sessions remain fixed at Asia 00:00–08:00,
Europe 08:00–14:30 and U.S. 14:30–24:00. Weekend signals reset.

The deployable search keeps that causal signal and tests only transparent
extensions: minimum preceding-session momentum, traded-session subset, weekday
subset, completed-bar trend confirmation, ATR stop, fixed-R or session-close
exit, and breakeven or ATR trailing management.

## Frozen evidence split

- Development train: 2021-09-13 to 2024-09-11.
- Development validation: 2024-09-11 to 2025-09-11.
- Untouched locked year: 2025-09-11 to 2026-09-11.
- The locked year is read only once after one configuration is selected using
  train and validation.

## Costs and sizing

- Connected Exness Zero XAUUSD M30 data and recorded historical spreads.
- Conservative $3.50 per lot per side commission.
- Recorded long-swap points whenever a position survives the U.S. rollover,
  including the broker's triple-rollover day.
- 1% current-equity risk per trade and a 5x effective-leverage cap.
- Stress adds one further recorded round-trip spread and raises commission 50%.
- Stop is checked before target when both are touched inside the same M30 bar.

## Promotion gate

Train, validation, locked and stressed locked returns must be positive. Locked
PF must be at least 1.20 with at least 80 trades and no more than 15% drawdown.
Stressed locked PF must be at least 1.10, 10,000-path block-bootstrap P5 return
must be positive, at least 60% of local parameter neighbours must be profitable,
and at least four of five annual windows must be profitable. Passing remains a
research promotion only; native MT5 Every Tick confirmation is still required
before deployment.
