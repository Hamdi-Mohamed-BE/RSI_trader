# Step 5 — Month-End Institutional Flow

## Goal

Test whether the documented turn-of-the-month equity-index effect can be converted into a cost-aware, rules-based MT5 strategy for USTEC and US30.

## Frozen process

- Development: 2023-09-01 to 2024-09-01.
- Pre-lock validation: 2024-09-01 to 2025-09-01.
- Untouched locked year: 2025-09-01 to 2026-09-01.
- Full context: 2023-09-01 to 2026-09-01.
- Risk: fixed 1% of current equity per trade.
- Calendar labels: known Monday-Friday calendar positions only; no future-bar inspection.
- Costs: broker spread plus an additional friction allowance in the screening model; native MT5 validation includes broker spread, commission, swap and random delay.

## Pipeline

1. Calendar window, signal timeframe and entry-session timing.
2. Candle confirmation, daily trend/regime filter and trade direction.
3. Maximum holding period.
4. Stop placement.
5. Fixed reward/risk from 0.5R to 6R.
6. No management, break-even, ATR trail and Dynamic M15 50/20.
7. Recheck calendar/timeframe/session interactions with the selected exits.
8. Freeze the configuration before opening the locked year.
9. Native MT5 locked-year and three-year validation.
10. Rolling stability and 10,000-path block-bootstrap Monte Carlo.

Promotion gate: positive locked return, PF at least 1.10, at least 24 locked trades, max equity drawdown below 15%, positive Sharpe and no material collapse versus pre-lock validation.
