# Relative-Volume ORB: 60-Day Research Report

Period: 2026-05-08 to 2026-07-07
Starting balance: $300.00
Chronological train/validation screen: **PASSED**

## Walk-Forward Selection

- Symbols: ETHUSD,BTCUSD
- Opening range: 5 minutes
- Stop: 15% of prior 14-session ATR
- Minimum relative volume: 0.75
- Daily rank limit: 3
- Training: 2.43% over 44 trades
- Validation: 15.21% over 17 trades
- Full period: $353.41 (17.80%), 61 trades, 11.77% max drawdown
- Win rate: 37.70%; profit factor: 1.43
- Minimum-lot fallbacks: 13; maximum observed trade risk was 1.33%

The later segment is used to rank the optimization grid. It is chronological out-of-sample data for each individual configuration, but it is not an untouched final test after model selection.

## Best Per-Symbol Profiles

| Symbol | Configuration | Return | Trades | Max DD | Train / validation |
| --- | --- | ---: | ---: | ---: | --- |
| US100 | 60m, 15% ATR, RVOL 0.75 | +17.03% | 25 | 5.32% | +15.43% / +0.79% |
| ETHUSD | 15m, 20% ATR, RVOL 1.00 | +11.53% | 21 | 3.83% | +1.30% / +10.01% |
| BTCUSD | 5m, 15% ATR, RVOL 0.75 | +10.15% | 30 | 6.53% | +0.24% / +9.91% |
| GBPUSD | 5m, 20% ATR, RVOL 1.25 | +4.23% | 6 | 0.95% | +3.50% / +0.73% |
| AUDUSD | 30m, 20% ATR, RVOL 0.75 | +0.44% | 25 | 5.15% | +0.35% / +0.09% |

US30, XAUUSD, XAGUSD, EURUSD, USDJPY, USDCHF, USDCAD, and NZDUSD did not produce a stable positive profile. USDJPY's full-period result was large but collapsed in the later segment and is rejected.

## Full-Period Winner (In-Sample)

- Symbols: USDJPY
- Configuration: 15m range, 20% ATR stop, RVOL >= 0.75, top 1
- Full return: 251.86% over 23 trades
- Validation: -95.35% over 5 trades

This winner is reported for transparency, not promoted to a live default, because it did not pass the chronological validation gate.

## Data Limitation

The paper uses consolidated U.S. share volume. This broker supplies MT5 tick volume for its stock CFDs, so relative volume is only an activity proxy and the one-million-share eligibility filter cannot be reproduced faithfully.
