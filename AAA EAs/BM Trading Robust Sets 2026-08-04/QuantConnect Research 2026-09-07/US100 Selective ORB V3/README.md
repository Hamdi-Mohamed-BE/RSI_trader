# US100 Selective ORB V3 — QuantConnect

This is a fidelity port of the locked Calyx **US100 Selective ORB V3** preset.
It uses the continuous CME Micro E-mini Nasdaq-100 (`MNQ`) future for signals
and the currently mapped front contract for orders.

## Locked rules

- Opening range: 09:30–10:00 New York
- Entries: M5 breakout followed by a qualifying retest
- Entry cutoff: 11:30 New York
- Direction schedule: both before 10:30, long-only from 10:30, short-only from 11:00
- Baseline: prior 20 sessions
- Opening relative volume: at least 0.60
- Range: 0.05–0.35 of median daily true range
- Breakout relative volume: at least 0.90 at the same clock time
- Breakout body: at least 75% of the M5 candle range
- Breakout buffer: 0.015 daily ATR
- Session VWAP confirmation: enabled
- Retest: within 3 bars and 0.25 opening ranges of the boundary
- Maximum pre-retest excursion: 0.60 opening ranges
- Stop: opposite range boundary plus 0.05 opening ranges
- Maximum stop: 0.80 daily ATR
- Risk: maximum 1% of current portfolio equity
- Target: 2R
- Breakeven: 1R
- One trade per day; flat at 15:55 New York

The QuantConnect version uses centralized CME traded volume. The MT5 version
used Exness USTEC broker tick volume, so results are expected to differ even
when the rules are preserved.

## Source MT5 evidence

The latest cached Calyx evidence for this EA reports 17.76% return, 1.88 profit
factor, 59.68% win rate, 3.66% maximum drawdown, 62 trades, 9.92 Sharpe ratio,
and 4.07 recovery factor over 5 September 2016–5 September 2026.

## Validation

- Local Python syntax: passed
- Direction schedule boundary checks: passed (7 cases)
- QuantConnect cloud compilation: passed (LEAN 2.5.0.0.18057)
- QuantConnect cloud project: `36247794`
- Final cloud backtest: `Adaptable Green Parrot`

## QuantConnect result

Tested on centralized CME MNQ minute data from 1 January 2020 through the
latest data available to the cloud engine on 10 June 2026. Interactive Brokers
fees were enabled. Signals used the adjusted continuous series and orders used
the mapped front contract. The roll-adjustment translation was validated so
stop distances are preserved across those two price series.

| Metric | Result |
|---|---:|
| Starting equity | $100,000.00 |
| Ending equity | $99,587.02 |
| Net return | -0.413% |
| Net P&L after fees | -$412.98 |
| Closed trades | 63 |
| Wins | 13 |
| Win rate | 20.63% |
| Gross profit factor | 0.993 |
| Net profit factor after fees | 0.969 |
| Max drawdown | 6.90% |
| Sharpe ratio | -1.925 |
| Sortino ratio | -0.565 |
| Average win / average loss | 3.77 |
| Total fees | $321.48 |
| Average net P&L per trade | -$6.56 |

Yearly net P&L: 2020 +$603.56; 2021 -$817.90; 2022 -$2,721.30;
2023 +$2,769.94; 2024 -$2,270.86; 2025 +$2,069.28; 2026 YTD -$45.70.

Conclusion: the locked MT5 V3 edge did **not** transfer to centralized CME MNQ
volume without re-optimization. Keep the existing MT5 EA unchanged; do not add
this QuantConnect port to the recommended/live portfolio in its current form.
