# AAA Loophole — Nasdaq-100 Research System

This project searches a deliberately bounded set of daily Nasdaq-100 futures patterns, locks one rule using pre-2021 development data, and evaluates it on untouched 2021-present data.

It reports profit factor, win rate, maximum drawdown, trades, risk-normalized return, a QQQ cross-check, and bootstrap uncertainty. It is a research prototype—not a live-trading recommendation.

## Run

```powershell
python nasdaq_loophole_backtest.py
```

Outputs are written to `results/`; downloaded snapshots are written to `data/`.

## Current scope

- Reference instrument: Yahoo continuous E-mini Nasdaq-100 futures (`NQ=F`)
- Cross-check: QQQ
- Bars: daily
- Execution: next open after a close signal
- Development: 2000–2020 in three robustness folds
- Locked test: 2021–present
- Risk normalization: 0.5% of equity per initial stop

Do not connect this version to live execution. Broker-specific US100 data, tick-level costs, rollover handling, and forward testing are required first.

## Higher-frequency intraday prototype

The separate hourly engine searches 1,404 intraday rules, selects using development and validation data through 2025, and opens 2026 only for the final test:

```powershell
python nasdaq_intraday_backtest.py
```

Its outputs are written to `results_intraday/`. It permits at most one trade per New York session and never intentionally holds overnight.
