# US100 Overnight Value Area Breakout — validation report

Research date: 2026-08-26

## Verdict

The literal viral rule is rejected for deployment. Its high win rate hides negative expectancy in the older training and validation periods. The developed retest version is positive in every native segment, but the edge is too small for the active BAT: latest-year PF is only 1.09 and return is about 2% at 1% risk per trade.

## Native MT5 results

| Version | Segment / model | Return | PF | Win rate | Equity DD | Trades | Quality |
|---|---|---:|---:|---:|---:|---:|---:|
| Developed | Training / 1-minute OHLC | +1.19% | 1.01 | 52.08% | 8.19% | 432 | 98% |
| Developed | Validation / 1-minute OHLC | +5.15% | 1.17 | 50.33% | 6.70% | 151 | 98% |
| Developed | Locked / real ticks | +2.50% | 1.10 | 53.91% | 4.83% | 128 | 56% real ticks |
| Developed | One year / real ticks | +2.14% | 1.09 | 53.57% | 4.82% | 112 | 64% real ticks |
| Developed | One year / Every Tick | +2.04% | 1.09 | 52.68% | 4.91% | 112 | 100% |
| Developed | Full / 1-minute OHLC | +8.39% | 1.05 | 51.83% | 11.12% | 712 | 98% |
| Literal | Training / 1-minute OHLC | -32.17% | 0.79 | 62.65% | 33.23% | 514 | 98% |
| Literal | Validation / 1-minute OHLC | -13.14% | 0.80 | 62.50% | 16.62% | 192 | 98% |
| Literal | One year / real ticks | +2.12% | 1.04 | 68.39% | 7.06% | 155 | 64% real ticks |
| Literal | One year / Every Tick | +4.65% | 1.09 | 68.83% | 5.90% | 154 | 100% |

## Versions

- Literal: overnight VA from 16:30 to 09:30 New York; the first 09:30 M15 candle must close outside VAH/VAL; direct market entry; signal-candle stop; 0.5R target.
- Developed: wait up to four M15 bars after 09:30 for a directional close outside VAH/VAL; require a directional candle; enter only after a VAH/VAL retest; stop one median prior-RTH range away; 1.5R target; close at 15:55 New York.
- Both use 70% value area, one trade per day, automatic New York DST conversion and 1% equity risk.

## Data limitation

The Exness USTEC CFD has broker tick activity, not centralized Nasdaq futures exchange volume or true bid/ask CVD. The recent real-tick reports contain only 56–64% real-tick history quality. The corresponding 100% MT5 Every Tick checks are therefore the primary one-year comparison.

## Decision

Do not add either version to the active BAT. Keep the developed EA as research/watch-only until it produces a stronger PF and return in an additional untouched period or is tested against paid CME futures volume.

The active installer, active SET files and website portfolio were not changed.
