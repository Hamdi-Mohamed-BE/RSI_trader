# XAU port of US100 Weakness

This research profile reuses the restored US100 Weakness engine without
changing the US100 strategy. It automatically resolves the connected broker's
XAUUSD alias and applies the same New York/London S2A rules to gold.

## Exact S2A rule

- Evaluate the second New York M15 candle at 10:00 New York.
- If it closes green and the bullish-continuation filter is absent, fade it.
- Use an OCO sell limit at the 09:15 reference high and sell stop at its low.
- Stop above the London high and target 1.7R.

## Validation result

On connected-MT5 XAUUSD M1 history from 2025-08-04 through 2026-08-04, the
exact S2A port failed: 84 ideas, 32.14% win rate, PF 0.68, -6.29R net, and
6.50% maximum realized drawdown at 1% risk. The train-selected alternative
also failed both validation and untouched holdout. For that reason this
profile is deliberately research-only and is not included in the master live
launcher.

The executable evidence is saved in `reports/XAUUSD.._baseline_summary.json`
and `reports/XAUUSD.._baseline_trades.csv`.
