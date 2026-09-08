# Intraday FX Session Effect — Full Pipeline Report

Research only. No EA/BAT/website/portfolio deployment was performed.

## Source and test design

The source is the Swiss National Bank paper by Breedon and Ranaldo. The paper reports local-currency depreciation during local trading hours and found its simple EURUSD session rules profitable after interdealer costs. Calyx retests that hypothesis on recent retail MT5 data with a frozen train/validation/locked-year protocol.

## Selected results

| Pair | Locked WR | Locked PF | Locked return | Locked DD | Sharpe | Recovery | Trades | Avg win R | Stress PF | MC P5 | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| EURUSD | 57.02% | 1.07 | +2.70% | 9.23% | 0.30 | 0.29 | 121 | 0.60R | 0.96 | -11.50% | FAIL |
| GBPUSD | 43.28% | 0.82 | -4.70% | 7.68% | -0.54 | -0.61 | 67 | 0.77R | 0.73 | -15.03% | FAIL |
| USDJPY | 40.68% | 1.35 | +12.15% | 8.55% | 0.76 | 1.42 | 59 | 1.89R | 1.19 | -7.03% | FAIL |
| USDCHF | 41.44% | 0.84 | -9.00% | 19.60% | -0.61 | -0.46 | 111 | 1.08R | 0.72 | -27.10% | FAIL |
| AUDUSD | 1.30% | 0.06 | -55.60% | 55.67% | -5.54 | -1.00 | 77 | 7.86R | 0.03 | -59.60% | FAIL |
| EURJPY | 44.85% | 0.88 | -9.67% | 16.76% | -0.54 | -0.58 | 165 | 0.98R | 0.80 | -26.38% | FAIL |

## Paper-rule comparison

| Pair | Raw locked WR | Raw locked PF | Raw locked return | Optimized locked PF |
|---|---:|---:|---:|---:|
| EURUSD | 49.03% | 0.92 | -3.88% | 1.07 |
| GBPUSD | 49.61% | 1.02 | +1.14% | 0.82 |
| USDJPY | 49.23% | 0.91 | -4.56% | 1.35 |
| USDCHF | 49.61% | 0.88 | -6.87% | 0.84 |
| AUDUSD | 50.58% | 0.99 | -0.66% | 0.06 |
| EURJPY | 51.35% | 0.92 | -3.48% | 0.88 |

## Configurations and decisions

### EURUSD

- Selected without looking at locked year: `{"confirmation": "ema50", "direction": "paper", "management": "atr-trail", "rr": 0.0, "session": "ny-07-13", "stop_mode": "prior-day", "stop_value": 0.0, "target_mode": "adaptive", "timeframe": "M30", "weekdays": "all"}`
- Decision: **FAIL**
- Reasons: locked_double_cost return <= 0, locked PF < 1.20, Monte Carlo P5 <= 0

### GBPUSD

- Selected without looking at locked year: `{"confirmation": "low-vol", "direction": "paper", "management": "atr-trail", "rr": 0.0, "session": "ny-07-13", "stop_mode": "prior-day", "stop_value": 0.0, "target_mode": "timed", "timeframe": "M30", "weekdays": "all"}`
- Decision: **FAIL**
- Reasons: locked return <= 0, locked_double_cost return <= 0, locked PF < 1.20, locked trades < 80, Monte Carlo P5 <= 0

### USDJPY

- Selected without looking at locked year: `{"confirmation": "ema50", "direction": "inverse", "management": "atr-trail", "rr": 0.0, "session": "ny-09-15", "stop_mode": "swing", "stop_value": 8.0, "target_mode": "timed", "timeframe": "M15", "weekdays": "tue-thu"}`
- Decision: **FAIL**
- Reasons: locked trades < 80, Monte Carlo P5 <= 0

### USDCHF

- Selected without looking at locked year: `{"confirmation": "momentum", "direction": "inverse", "management": "none", "rr": 0.0, "session": "eu-07-15-paper", "stop_mode": "atr", "stop_value": 1.5, "target_mode": "timed", "timeframe": "H1", "weekdays": "no-monday"}`
- Decision: **FAIL**
- Reasons: locked return <= 0, locked_double_cost return <= 0, locked PF < 1.20, locked DD > 15%, Monte Carlo P5 <= 0

### AUDUSD

- Selected without looking at locked year: `{"confirmation": "rel-volume", "direction": "inverse", "management": "none", "rr": 0.0, "session": "ny-08-16-paper", "stop_mode": "atr", "stop_value": 0.5, "target_mode": "timed", "timeframe": "M15", "weekdays": "no-monday"}`
- Decision: **FAIL**
- Reasons: locked return <= 0, locked_double_cost return <= 0, locked PF < 1.20, locked trades < 80, locked DD > 15%, Monte Carlo P5 <= 0

### EURJPY

- Selected without looking at locked year: `{"confirmation": "ema50", "direction": "paper", "management": "atr-trail", "rr": 0.0, "session": "ny-07-13", "stop_mode": "atr", "stop_value": 1.25, "target_mode": "timed", "timeframe": "H1", "weekdays": "all"}`
- Decision: **FAIL**
- Reasons: locked return <= 0, locked_double_cost return <= 0, locked PF < 1.20, locked DD > 15%, Monte Carlo P5 <= 0

## Final decision

Only rows marked PASS are candidates for a native MT5 Every Tick EA confirmation. This report does not authorize live deployment or portfolio inclusion.
