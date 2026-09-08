# Weekend Gap Reversal — Full Pipeline Report

Research only. No deployment changes were made.

| Pair | Train Ret/PF/WR | Validation Ret/PF/WR | Locked Ret/PF/WR | DD | Sharpe | Recovery | Trades | Stress PF | MC P5 | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| EURUSD | +72.58%/6.32/25.00% | +87.47%/3.62/11.54% | -17.97%/0.00/0.00% | 17.97% | -5.93 | -1.00 | 18 | 0.00 | -18.16% | FAIL |
| GBPUSD | +3.62%/4.38/88.89% | +3.92%/4.64/80.00% | +5.58%/3.67/75.00% | 1.02% | 1.99 | 5.49 | 12 | 3.34 | +3.48% | PASS |
| USDJPY | +22.76%/10.34/20.00% | +41.11%/14.88/9.09% | +10.01%/5.46/16.67% | 2.11% | 0.90 | 4.74 | 6 | 4.16 | -4.10% | FAIL |
| USDCHF | +3.47%/4.24/80.00% | +10.15%/3.37/60.00% | +6.28%/1.93/53.33% | 2.06% | 0.93 | 3.05 | 15 | 1.69 | -2.18% | FAIL |
| AUDUSD | +1.51%/14.28/83.33% | +3.42%/13.41/90.00% | +0.96%/99.00/100.00% | 0.00% | 1.96 | 0.00 | 2 | 99.00 | +0.96% | FAIL |
| EURJPY | +13.61%/7.26/60.00% | +12.45%/13.28/80.00% | +0.55%/99.00/100.00% | 0.00% | 6.58 | 0.00 | 3 | 99.00 | +0.55% | FAIL |

## Configurations and decisions

### EURUSD

- Selected before locked reveal: `{"confirmation": "none", "delay_hours": 0, "direction": "paper", "management": "none", "max_hold_hours": 0, "rolling_weeks": 260, "rr": 0.0, "stop_mode": "atr", "stop_value": 0.75, "tail_percent": 15.0, "target_mode": "timed", "timeframe": "M15"}`
- **FAIL** — locked return <= 0, locked_cost_stress return <= 0, locked PF < 1.20, locked DD > 15%, Monte Carlo P5 <= 0

### GBPUSD

- Selected before locked reveal: `{"confirmation": "first-bar-reversal", "delay_hours": 0, "direction": "paper", "management": "breakeven", "max_hold_hours": 48, "rolling_weeks": 52, "rr": 0.0, "stop_mode": "gap", "stop_value": 2.0, "tail_percent": 15.0, "target_mode": "adaptive", "timeframe": "M15"}`
- **PASS** — all research gates passed; native Every Tick confirmation remains required

### USDJPY

- Selected before locked reveal: `{"confirmation": "first-bar-reversal", "delay_hours": 0, "direction": "paper", "management": "breakeven", "max_hold_hours": 0, "rolling_weeks": 52, "rr": 0.0, "stop_mode": "atr", "stop_value": 1.0, "tail_percent": 15.0, "target_mode": "timed", "timeframe": "M15"}`
- **FAIL** — locked trades < 10, Monte Carlo P5 <= 0

### USDCHF

- Selected before locked reveal: `{"confirmation": "first-bar-reversal", "delay_hours": 12, "direction": "paper", "management": "atr-trail", "max_hold_hours": 48, "rolling_weeks": 260, "rr": 4.0, "stop_mode": "atr", "stop_value": 1.25, "tail_percent": 15.0, "target_mode": "fixed", "timeframe": "H1"}`
- **FAIL** — Monte Carlo P5 <= 0

### AUDUSD

- Selected before locked reveal: `{"confirmation": "first-bar-momentum", "delay_hours": 2, "direction": "paper", "management": "none", "max_hold_hours": 24, "rolling_weeks": 52, "rr": 0.5, "stop_mode": "atr", "stop_value": 3.0, "tail_percent": 7.5, "target_mode": "fixed", "timeframe": "M30"}`
- **FAIL** — locked trades < 10

### EURJPY

- Selected before locked reveal: `{"confirmation": "none", "delay_hours": 0, "direction": "short-only", "management": "dynamic-50-20", "max_hold_hours": 0, "rolling_weeks": 52, "rr": 0.0, "stop_mode": "atr", "stop_value": 1.25, "tail_percent": 7.5, "target_mode": "timed", "timeframe": "H1"}`
- **FAIL** — locked trades < 10
