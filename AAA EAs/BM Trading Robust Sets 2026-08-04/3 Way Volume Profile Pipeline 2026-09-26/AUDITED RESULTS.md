# 3 Way Volume Profile — audited qualification

Research only. Optimization status at report build: {"utc": "2026-09-26T15:15:04.722654+00:00", "state": "complete_rejected", "search_passes": 415, "unique_configurations": 385, "result": "Raw gold retained; all optimized finalists rejected on validation; holdout preserved; nothing deployed"}. No production changes.

## Tick-mode confirmations

Model 4 native MT5, M15, $10,000, target 1% equity risk, 2R, configured 150ms delay. Real-tick coverage can be partial; older ticks are generated. This is not FTMO execution evidence.

| Asset / setup | Window | Return | PF | Trades | /month | /trading day | Win rate | Max equity DD | Max balance DD | Avg W/L streak | Longest W/L streak | Profitable months* |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| BTCUSD REV | 3y | +34.31% | 1.09 | 592 | 16.44 | 0.540 | 35.98% | 29.28% | 28.22% | 1.55/2.77 | 5/12 | 20/37 |
| BTCUSD REV | 5y | +25.95% | 1.04 | 911 | 15.19 | 0.499 | 35.46% | 38.35% | 37.39% | 1.51/2.76 | 6/12 | 30/61 |
| USDJPY ALL | 3y | +84.44% | 1.18 | 554 | 15.39 | 0.707 | 39.17% | 21.79% | 21.61% | 1.67/2.59 | 8/12 | 23/37 |
| USDJPY ALL | 5y | +99.12% | 1.13 | 913 | 15.22 | 0.700 | 37.68% | 27.73% | 27.37% | 1.64/2.72 | 8/13 | 34/61 |
| USDJPY BRK | 3y | +56.12% | 1.24 | 272 | 7.55 | 0.347 | 39.71% | 15.39% | 13.40% | 1.69/2.6 | 4/8 | 21/37 |
| USDJPY BRK | 5y | +34.70% | 1.11 | 451 | 7.52 | 0.346 | 36.59% | 25.44% | 23.51% | 1.56/2.72 | 4/10 | 33/61 |
| XAUUSD BRK | 1y | +19.82% | 1.30 | 78 | 6.50 | 0.299 | 41.03% | 13.43% | 12.88% | 1.68/2.56 | 7/7 | 7/13 |
| XAUUSD BRK | 3y | +93.10% | 1.37 | 270 | 7.50 | 0.344 | 42.59% | 13.79% | 12.71% | 1.8/2.42 | 7/8 | 23/37 |
| XAUUSD BRK | 5y | +80.22% | 1.22 | 446 | 7.43 | 0.342 | 39.24% | 15.26% | 14.43% | 1.64/2.53 | 7/8 | 33/61 |

*Calendar months include the partial first and last September. BTC /day uses calendar days; gold and FX use weekdays. Equity/balance DD use MT5's maximum RELATIVE percentage, not the percentage at the largest dollar drawdown.

## Decisions

- BTCUSD REV: **FAIL**.
  - 3y: absolute gate False; median random control None; beats control False.
  - 5y: absolute gate False; median random control None; beats control False.
- XAUUSD BRK: **QUALIFIED**.
  - 3y: absolute gate True; median random control {'return_pct': -23.93, 'profit_factor': 0.87}; beats control True.
  - 5y: absolute gate True; median random control {'return_pct': -31.41, 'profit_factor': 0.89}; beats control True.
- USDJPY ALL: **FAIL**.
  - 3y: absolute gate True; median random control None; beats control False.
  - 5y: absolute gate False; median random control None; beats control False.
- USDJPY BRK: **FAIL**.
  - 3y: absolute gate True; median random control None; beats control False.
  - 5y: absolute gate False; median random control None; beats control False.

## Integrity and limitations

- Trades and net P/L reconcile to the report in 23/23 runs.
- Original gold one-year parity: all 78 trade records and every summary metric matched. Only the parser's report-label field differed.
- Broker lot rounding is upward: especially at the minimum lot, actual initial risk can exceed the nominal 1%.
- Account leverage and contract conditions are from the saved Exness research binding, not a simulated FTMO Swing account.
- No-signal controls use 2 ATR stops instead of profile structure stops. They are a sanity reference, not a perfectly matched causal experiment.
- Absolute PF is rounded to two decimals in the native report; exact trade-ledger PF is retained in AUDIT.json.
- No website, BAT, active EA, live account or Git publication was changed.

## Tick coverage and order exceptions

### qual-BTCUSD-REV-3y-m4-raw

Report history quality: 24% real ticks. First entry: 2023-09-27T14:45:00; last exit: 2026-09-25T23:59:58.

- BTCUSD : real ticks begin from 2026.01.01 00:00:00
- BTCUSD: history data begins from 2014.01.15 00:00
- BTCUSD: history synchronized from 2020.01.01 to 2026.09.25
- BTCUSD: history ticks synchronized from 2026.01.01 to 2026.09.25

### qual-BTCUSD-REV-5y-m4-raw

Report history quality: 14% real ticks. First entry: 2021-09-26T09:45:00; last exit: 2026-09-25T23:59:58.

- BTCUSD : real ticks begin from 2026.01.01 00:00:00
- BTCUSD: history data begins from 2014.01.15 00:00
- BTCUSD: history synchronized from 2020.01.01 to 2026.09.25
- BTCUSD: history ticks synchronized from 2026.01.01 to 2026.09.25

### qual-USDJPY-ALL-3y-m4-raw

Report history quality: 24% real ticks. First entry: 2023-09-26T08:00:00; last exit: 2026-09-25T13:20:50.

- USDJPY : real ticks begin from 2026.01.01 00:00:00
- USDJPY: history data begins from 2018.01.02 00:00
- USDJPY: history synchronized from 2020.01.02 to 2026.09.25
- USDJPY: history ticks synchronized from 2026.01.01 to 2026.09.25

### qual-USDJPY-ALL-5y-m4-raw

Report history quality: 14% real ticks. First entry: 2021-09-27T08:30:00; last exit: 2026-09-25T13:20:50.

- USDJPY : real ticks begin from 2026.01.01 00:00:00
- USDJPY: history data begins from 2018.01.02 00:00
- USDJPY: history synchronized from 2020.01.02 to 2026.09.25
- USDJPY: history ticks synchronized from 2026.01.01 to 2026.09.25

### qual-USDJPY-BRK-3y-m4-raw

Report history quality: 24% real ticks. First entry: 2023-09-27T09:45:00; last exit: 2026-09-25T13:20:50.

- USDJPY : real ticks begin from 2026.01.01 00:00:00
- USDJPY: history data begins from 2018.01.02 00:00
- USDJPY: history synchronized from 2020.01.02 to 2026.09.25
- USDJPY: history ticks synchronized from 2026.01.01 to 2026.09.25

### qual-USDJPY-BRK-5y-m4-raw

Report history quality: 14% real ticks. First entry: 2021-09-27T08:30:00; last exit: 2026-09-25T13:20:50.

- USDJPY : real ticks begin from 2026.01.01 00:00:00
- USDJPY: history data begins from 2018.01.02 00:00
- USDJPY: history synchronized from 2020.01.02 to 2026.09.25
- USDJPY: history ticks synchronized from 2026.01.01 to 2026.09.25
- 2022.01.21 21:15:00   failed market sell 0.28 USDJPY sl: 114.035 tp: 112.787 [Market closed]

### qual-XAUUSD-BRK-1y-m4-raw

Report history quality: 73% real ticks. First entry: 2025-09-26T14:15:00; last exit: 2026-09-25T20:57:59.

- XAUUSD : real ticks begin from 2026.01.01 00:00:00
- XAUUSD: history data begins from 2014.01.14 00:00
- XAUUSD: history synchronized from 2018.01.02 to 2026.09.25
- XAUUSD: history ticks synchronized from 2026.01.01 to 2026.09.25
- 2025.12.17 21:30:00   failed market buy 0.05 XAUUSD sl: 4319.812 tp: 4393.291 [Market closed]

### qual-XAUUSD-BRK-3y-m4-raw

Report history quality: 24% real ticks. First entry: 2023-09-29T03:15:00; last exit: 2026-09-25T20:57:59.

- XAUUSD : real ticks begin from 2026.01.01 00:00:00
- XAUUSD: history data begins from 2014.01.14 00:00
- XAUUSD: history synchronized from 2018.01.02 to 2026.09.25
- XAUUSD: history ticks synchronized from 2026.01.01 to 2026.09.25
- 2025.12.17 21:30:00   failed market buy 0.08 XAUUSD sl: 4319.812 tp: 4393.291 [Market closed]

### qual-XAUUSD-BRK-5y-m4-raw

Report history quality: 14% real ticks. First entry: 2021-09-29T17:00:00; last exit: 2026-09-25T20:57:59.

- XAUUSD : real ticks begin from 2026.01.01 00:00:00
- XAUUSD: history synchronized from 2018.01.02 to 2026.09.25
- XAUUSD: history ticks synchronized from 2026.01.01 to 2026.09.25
- 2025.12.17 21:30:00   failed market buy 0.07 XAUUSD sl: 4319.812 tp: 4393.291 [Market closed]
