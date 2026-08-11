# US100 Asia-London Continuation — final research report

Research completed 2026-08-10. Initial test balance: USD 10,000. Risk: 1% of current equity per trade.

## Verdict

The exact 20-index-point rule has a small positive edge in the available tests, including the untouched 2025–2026 Exness period and an unchanged-settings MEXAtlantic replay. It is **not strong enough to call production-ready** because there are only 86 Exness trades across roughly seven years, only 34 cross-broker trades, and the native MT5 full-period PF is 1.15. The strategy is low-frequency and far below a 20% annual return at 1% risk.

The EA is compiled and its source default is disabled. It has not been added to the portfolio installer.

## Unit decision

Both tested broker symbols use:

- price digits: 2
- broker point: 0.01
- minimum trade tick: 0.01

Therefore:

- 2,000 broker ticks = `2,000 × 0.01 = 20.00` index points
- 200 pips equals 20.00 index points only when one pip is defined as 0.10 index point

The EA input is deliberately named `InpExtremeProximityPoints` and set to 20.00. It does not use the ambiguous word “pip.”

## Locked signal

- All sessions are evaluated in `America/New_York` time with daylight-saving conversion.
- Asia: previous New York calendar day 18:00 to 03:00.
- London: 03:00 to 09:30.
- Asia and London must each close in the same direction relative to their respective opens.
- Bullish: absolute difference between the first New York M15 high and Asia high must be no more than 20.00 index points.
- Bearish: absolute difference between the first New York M15 low and Asia low must be no more than 20.00 index points.
- Both long and short directions remain enabled. Their ranking reversed between brokers, so removing one would be hindsight fitting.

## Selected execution

| Parameter | Selected value |
|---|---:|
| Entry | Break of first New York 15-minute range |
| Entry window | 09:45–10:30 New York |
| Stop | max(1.25 × opening-range width, 20.00 index points) |
| Take profit | 2.0R |
| Break-even | Off |
| M15 trailing | Off |
| Hard exit | 16:00 New York |
| Maximum first M15 range | 400 index points |
| Risk | 1% of current equity |
| Frequency | One attempted setup per New York day |

The execution search covered 288 combinations: market versus opening-range breakout, 10:30/11:30 cutoffs, 1.0/1.25 range stops, 20/40-point minimum stops, 1.5/2/3/4R targets, no trailing/break-even at 1R/M15 trailing after 1.5R, and 14:00/16:00 exits. Selection used 2019–2023 training plus 2024 validation. The 2025–2026 holdout was not used for selection.

No trailing stop was selected. Break-even reduced training PF from 1.195 to 1.144 and did not improve the 2024 validation PF, which was 1.484 for both. The M15 trailing candidate ranked lower overall.

## Native MT5 result — primary evidence

Compiled-EA replay on Exness `USTEC`, M1-generated ticks, USD 10,000, 1% equity risk.

| Statistic | Full 2019-07-16–2026-08-09 | Untouched 2025-01-01–2026-08-09 |
|---|---:|---:|
| History quality | 98% | 100% |
| Trades | 86 | 9 |
| Net profit | $652.39 | $226.58 |
| Return | +6.52% | +2.27% |
| Final balance | $10,652.39 | $10,226.58 |
| Profit factor | 1.15 | 1.50 |
| Win rate | 43.02% | 44.44% |
| Gross profit | $5,094.92 | $678.32 |
| Gross loss | -$4,442.53 | -$451.74 |
| Maximum balance DD | 10.19% | 4.42% |
| Maximum equity DD | 10.89% | 5.64% |
| Largest win | $207.26 | $199.19 |
| Largest loss | -$106.19 | -$101.34 |
| Average win | $137.70 | $169.58 |
| Average loss | -$88.31 | -$89.15 |
| Long trades | 55; 47.27% won | 3; 66.67% won |
| Short trades | 31; 35.48% won | 6; 33.33% won |

The native result is lower than the research simulator because MT5 uses actual pending-order and generated-tick execution. The native result is the primary number.

## Research simulator and cross-broker check

The research engine used broker-recorded M1 spreads and conservative stop-first resolution when a stop and target were both touched inside one minute.

| Data set | Trades | Return | PF | Win rate | Max closed-balance DD |
|---|---:|---:|---:|---:|---:|
| Exness USTEC 2019–2026 approximation | 86 | +10.77% | 1.26 | 45.35% | 7.96% |
| Exness untouched 2025–2026 approximation | 9 | +2.31% | 1.53 | 44.44% | 4.41% |
| MEXAtlantic UT100 2022–2026, unchanged settings | 34 | +15.24% | 1.93 | 52.94% | 5.38% |

The MEX yearly result was positive in 2022, 2023, 2024, and 2026, but negative in 2025. That is important evidence against assuming smooth monthly or yearly profits.

## Extra slippage stress

Additional adverse slippage was applied at both entry and exit, on top of each broker's recorded spread.

| Broker replay | Extra slippage each side | Return | PF | Max DD |
|---|---:|---:|---:|---:|
| Exness approximation | 0.5 index point | +8.71% | 1.21 | 8.80% |
| Exness approximation | 1.0 index point | +6.68% | 1.16 | 9.64% |
| Exness approximation | 2.0 index points | +2.74% | 1.07 | 11.30% |
| MEXAtlantic replay | 0.5 index point | +14.58% | 1.88 | 5.51% |
| MEXAtlantic replay | 1.0 index point | +13.92% | 1.83 | 5.64% |
| MEXAtlantic replay | 2.0 index points | +12.61% | 1.73 | 5.90% |

## Files

- `AAA Final US100 Asia London Continuation EA.mq5`: source
- `AAA Final US100 Asia London Continuation EA.ex5`: compiled EA
- `BEST TEST - Exness USTEC M1 - exact 20 points - 1pct.set`: Exness test preset
- `CROSS BROKER TEST - MEXAtlantic UT100 M1 - unchanged settings - 1pct.set`: MEX tester clock preset
- `Research/final-review/MT5 Exness full 2019-2026 report.htm`: native full MT5 report
- `Research/final-review/MT5 Exness holdout 2025-2026 report.htm`: native holdout MT5 report
- `Research/final-review/MT5 Exness full 2019-2026 equity.png`: native MT5 balance curve
- `Research/final-review/cross-broker-equity.png`: research-simulator cross-broker curve
- `Research/final-review/results.json`: stress and direction statistics

## Honest deployment decision

Use this only as a small, isolated forward-test EA. Do not increase risk to compensate for the low return. The evidence supports continued observation, not guaranteed profitability or inclusion in the main portfolio.
