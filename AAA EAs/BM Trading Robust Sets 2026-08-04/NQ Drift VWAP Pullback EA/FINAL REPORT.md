# NQ Drift VWAP Pullback — independent MT5 validation

## Decision

**REJECTED for the synchronized live portfolio.** The exact implementation had a profitable most-recent year, but it lost money in development and selection data, finished the full continuous test negative, and reached 42.26% maximum equity drawdown. The synchronized BAT installer was deliberately left unchanged.

## Test setup

| Item | Value |
|---|---|
| Broker/data | Exness `USTEC` CFD |
| Chart | M5 signals, M15 session VWAP |
| Model | MT5 Every tick, random execution delay |
| Initial balance | USD 10,000 |
| Position risk | 1.00% of current equity at the nominal 80-index-point stop |
| VWAP | Typical price weighted by broker tick volume, anchored 09:30 New York |
| History quality | 98–100% in the native reports |

This is not the same dataset as centralized NQ futures. Exness CFD tick volume is a broker activity proxy, while the video refers to NQ futures and exchange volume. Results therefore validate this MT5/Exness deployment, not the speaker's undisclosed futures backtest.

## Locked exact-rules result

| Segment | Dates | Initial | Final | Net / return | Max equity DD | PF | Win rate | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Development | 2022-01-03 to 2024-12-31 | $10,000.00 | $6,890.16 | -$3,109.84 / -31.10% | $4,395.19 / 42.26% | 0.94 | 59.93% | 2,144 |
| Selection | 2025-01-02 to 2025-08-06 | $10,000.00 | $9,165.98 | -$834.02 / -8.34% | $1,273.74 / 12.58% | 0.94 | 60.59% | 444 |
| Untouched final year | 2025-08-07 to 2026-08-06 | $10,000.00 | $14,885.86 | +$4,885.86 / +48.86% | $2,229.98 / 17.07% | 1.16 | 66.46% | 799 |
| Full continuous | 2022-01-03 to 2026-08-06 | $10,000.00 | $9,663.65 | -$336.35 / -3.36% | $4,395.19 / 42.26% | 1.00 | 61.62% | 3,395 |

Full-period gross profit was $84,466.09 and gross loss was -$84,802.44. Average win was $40.38; average loss was -$63.55. The low payoff ratio requires a stable win rate materially above break-even, and that stability was absent before August 2025.

## Predeclared development sensitivity check

| Variant | Return | Max equity DD | PF | Win rate | Trades |
|---|---:|---:|---:|---:|---:|
| Exact video parameters | -31.10% | 42.26% | 0.94 | 59.93% | 2,144 |
| Strict first qualifying pullback only | -34.98% | 48.18% | 0.93 | 59.12% | 1,595 |
| 0.075% hourly drift | -33.85% | 44.22% | 0.94 | 59.90% | 2,157 |
| 0.125% hourly drift | -31.11% | 42.36% | 0.94 | 60.13% | 2,127 |
| 40/40 point targets | -42.55% | 50.45% | 0.92 | 61.82% | 2,221 |
| 50/50 point targets | -27.18% | 38.98% | 0.95 | 57.76% | 2,024 |

All six development variants were negative. Selecting the strong recent year after seeing it would be regime cherry-picking, not robust optimization.

## Mechanical interpretation

- Session VWAP is calculated from completed M15 bars beginning at 09:30 New York.
- Trend requires price above/below VWAP, VWAP rising/falling over the last completed M15 bar, and a four-bar M15 change of at least +0.10% or -0.10%.
- The next M5 bar opens a trade after a counter-color M5 candle; subsequent qualifying pullbacks remain eligible until the four-trade/two-loss limits. A stricter one-per-drift-episode interpretation was tested separately and performed worse.
- No entries occur before 10:30 or at/after 15:30 New York; open positions are instructed to close at 15:55.
- Nominal exits are 80 index points stop, 40 points long target, and 50 points short target.

The native report shows individual losses can exceed the nominal 1% risk during gaps or when the CFD cannot execute exactly at the requested stop/flat time. The final-year largest loss was -$242.74 on the $10,000 test account.

## Evidence

- [Development native MT5 report](Reports/dev-exact.htm)
- [Selection native MT5 report](Reports/selection-exact.htm)
- [Untouched final-year native MT5 report](Reports/final-exact.htm)
- [Full continuous native MT5 report](Reports/full-exact.htm)
- [Full equity curve](Reports/full-exact.png)
- [Final-year equity curve](Reports/final-exact.png)

The disabled `.set` file is saved only for inspection/reproduction. `InpEnableTrading=false` prevents accidental deployment.
