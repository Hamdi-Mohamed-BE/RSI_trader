# Intraday FX Session Effect — Full Pipeline

Research only. Nothing in the EA catalogue, website, installers, BAT files, or
recommended portfolio is changed until the locked-year result is reviewed.

## Paper

Francis Breedon and Angelo Ranaldo, *Intraday patterns in FX returns and order
flow*, Swiss National Bank Working Paper 2011-04.

Official source:
https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04

The paper documents that a currency tends to depreciate during its own local
trading hours. Its simple EURUSD implementation shorts the euro during the
European session and buys it during the US session.

## Frozen protocol

- Current connected MT5 broker M15 bid bars and broker spread, with a retail
  spread floor and explicit commission/slippage allowance.
- Development train: 2023-09-01 to 2024-09-01.
- Development validation: 2024-09-01 to 2025-09-01.
- Untouched locked year: 2025-09-01 to 2026-09-01.
- Exactly 1% current-equity risk per engineered trade.
- Stop is resolved before target if both occur inside one bar.
- Paper rule is reported separately without pretending that it is a 1%-risk
  strategy, because the paper itself does not define a stop.

## Full search

- Markets: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD and EURJPY.
- Timeframes: M15, M30 and H1.
- Sessions: DST-aware European and New York windows around the paper hours,
  tested separately and together.
- Direction: paper direction, inverse, long-only and short-only.
- Confirmation: raw, prior-bar momentum/reversal, EMA alignment, volatility
  regime and relative-volume filters.
- Stops: ATR, recent swing and prior-day structure.
- Targets: timed session exit, 0.5R through 4R, and adaptive RR.
- Management: none, breakeven, ATR trail and Dynamic 50/20.
- Weekday filters: all days, no Monday, no Friday and Tuesday–Thursday.
- Validation: development train/validation balance, untouched locked year,
  doubled execution-cost stress and 5,000-path block Monte Carlo.

## Promotion gate

The selected configuration is chosen without seeing the locked year. It must
then have positive train, validation, locked-year and stressed returns; locked
PF at least 1.20; at least 80 locked-year trades; locked drawdown no more than
15%; and positive Monte Carlo P5 return. Passing research still requires a
native MT5 Every Tick EA confirmation before deployment.

