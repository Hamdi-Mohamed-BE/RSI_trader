# Weekend Gap Reversal — Full Pipeline Report

Research only. No deployment changes were made.

| Pair | Train Ret/PF/WR | Validation Ret/PF/WR | Locked Ret/PF/WR | DD | Sharpe | Recovery | Trades | Stress PF | MC P5 | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| GBPUSD | +1.37%/2.33/80.00% | +1.86%/1.90/75.00% | +2.15%/3.11/83.33% | 1.01% | 1.53 | 2.13 | 6 | 2.92 | -0.17% | FAIL |

## Configurations and decisions

### GBPUSD

- Selected before locked reveal: `{"confirmation": "first-bar-reversal", "delay_hours": 0, "direction": "paper", "management": "dynamic-50-20", "max_hold_hours": 48, "rolling_weeks": 52, "rr": 0.75, "stop_mode": "atr", "stop_value": 2.0, "tail_percent": 5.0, "target_mode": "fixed", "timeframe": "H1"}`
- **FAIL** — locked trades < 10, Monte Carlo P5 <= 0
