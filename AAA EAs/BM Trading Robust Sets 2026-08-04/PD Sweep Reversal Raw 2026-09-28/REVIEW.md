# Completed raw review — 28 September 2026

64 main native tests and four engineering smoke tests completed. M5 and M15
were tested without optimization. No trading strategy was installed live.

Last-year return / PF / equity-DD leaders: M5 on US30 and BTC, M15 on US100
and XAU. Only US100 M15 was profitable over the last year: +21.76%, net PF
1.12, win rate 39.03%, 269 trades, equity DD 22.48%.

Every raw asset/timeframe combination lost money over BOTH three and five
years. All eight fail the frozen review gate. None is selected for system or
FTMO use. This rejects these disclosed raw assumptions, not every possible
implementation of previous-day sweeps. No future success probability inferred.

## Independent verification

- 18 helper tests passed; 68 native runs and 40,020 closed positions reconciled.
- 42,866 recorded signals checked against native historical candles and prior
  completed daily levels; all independently rebuilt eligible signals match.
- Source/binary/rules/configuration hashes unchanged; zero unexplained omissions.
- Reconstructed risk sizing, one-tick candle stops, 2R targets, chronology,
  direction control, one-position constraint, fees and native report totals.
- Final audit resolved BTC 9 July 2024: the nominal 18:50 M5 candle starts with
  the 18:52 M1 record. There is no 18:50/18:51 minute. The frozen freshness guard
  correctly skips the 18:45 rejection, leaving the 22:50 rejection eligible.
  Independent M1 availability is now checked on every asset/timeframe/run.
  Only the auditor changed; neither the EA nor the performance evidence did.
- Static balance chart visually reviewed; it is not a floating-equity chart.

## Limits that matter

Research uses Exness CFD history and assumptions, not the connected FTMO account.
Older tick paths are generated; retained real ticks begin January 2026. Windows
overlap and are not out-of-sample validation. Historical broker costs/specification
changes and real execution are not guaranteed to be reproduced.

The 1% risk input is a target, not a loss cap. Upward lot rounding/minimum lots
caused gold M15 planned stop exposure to reach 2.09% on one last-year trade,
before costs/gaps. Some market-closure gaps also carried positions overnight.

See REPORT.md for all four windows, controls, trade frequency, streaks, costs,
drawdown and assumptions. Research inputs with account references remain local.
