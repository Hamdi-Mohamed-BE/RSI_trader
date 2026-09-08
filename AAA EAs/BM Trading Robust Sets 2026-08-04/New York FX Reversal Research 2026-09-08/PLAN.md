# Foreign Exchange Reversals in New York Time — Full Pipeline

Research only. No portfolio, BAT, EA catalogue or website changes are allowed
before review.

## Paper

Blake LeBaron and Yan Zhao, *Foreign Exchange Reversals in New York Time*,
Brandeis University, September 2008.

Official author copy: https://people.brandeis.edu/~blebaron/wps/fxnyc.pdf

The paper samples prices hourly, calculates a moving average of the latest 4–12
hourly prices, sells when price is above the average and buys when price is
below it. The position reverses when price crosses the average. Its key result
was concentrated in 10:00–15:00 New York time.

## Frozen protocol

- EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD and EURJPY only.
- Train: 2023-09-01 to 2024-09-01.
- Development validation: 2024-09-01 to 2025-09-01.
- Untouched locked year: 2025-09-01 to 2026-09-01.
- 1% current-equity risk per engineered trade.
- M15, M30 and H1 signal/execution bars.
- DST-aware New York windows around the paper window plus fixed-EST replication.
- MA lengths 4–12, 16 and 24; deviation, volatility and relative-volume gates.
- Reversal, inverse/trend, long-only and short-only directions.
- ATR and swing stops; signal-cross, session-close, 0.5R–4R and adaptive targets.
- Breakeven, ATR trail, Dynamic 50/20 and maximum-hold comparisons.
- Retail spread floor, commission/slippage, extra-cost stress, parameter-neighbour
  audit and 5,000-path block Monte Carlo.

## Promotion gate

Selection uses train and validation only. The final candidate must then have
positive train, validation, locked and extra-cost returns; locked PF at least
1.20; at least 80 locked trades; DD at most 15%; positive Monte Carlo P5; and
the majority of nearby parameter configurations must remain profitable.

