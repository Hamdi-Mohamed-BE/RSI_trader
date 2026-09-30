# ORB trade-count funnel (5 years, 2021-09-05 → 2026-09-05, Model 1)

Each weekday is classified once by the audit EA (identical trading logic to production + logging).

## ORB Volume Profile (XAU, M5)

| Step | Days | % of weekdays |
|---|---:|---:|
| Weekdays evaluated | 1299 | 100% |
| Opening range accepted | 630 | 48.5% |
| Price closed beyond the range in the trade window | 617 | 47.5% |
| **Traded** | **304** | **23.4%** |

Median opening-range size = 1.20 × ATR (filter band see SET).

Why the range was rejected:

- opening range too WIDE vs ATR (InpMaxRangeATR): **605** days (46.6%)
- opening volume below its 20-day median threshold: **55** days (4.2%)
- session never reached the end of the range (no ticks): **9** days (0.7%)

Why a real breakout day was not traded (last rule that blocked it):

- breakout candle body < InpBreakoutBodyMinimum: **183** days (14.1%)
- breakout candle volume below InpMinBreakoutRelativeVolume: **100** days (7.7%)
- stop distance > InpMaximumStopATR x ATR (entry too far from the range): **15** days (1.2%)
- close beyond range but within the ATR buffer or wrong candle colour: **15** days (1.2%)

## ORB Volume Profile Volume Confirmed (XAU, M5)

| Step | Days | % of weekdays |
|---|---:|---:|
| Weekdays evaluated | 1299 | 100% |
| Opening range accepted | 498 | 38.3% |
| Price closed beyond the range in the trade window | 487 | 37.5% |
| **Traded** | **120** | **9.2%** |

Median opening-range size = 1.20 × ATR (filter band see SET).

Why the range was rejected:

- opening range too WIDE vs ATR (InpMaxRangeATR): **608** days (46.8%)
- opening volume below its 20-day median threshold: **184** days (14.2%)
- session never reached the end of the range (no ticks): **9** days (0.7%)

Why a real breakout day was not traded (last rule that blocked it):

- breakout candle body < InpBreakoutBodyMinimum: **210** days (16.2%)
- breakout candle volume below InpMinBreakoutRelativeVolume: **145** days (11.2%)
- stop distance > InpMaximumStopATR x ATR (entry too far from the range): **8** days (0.6%)
- close beyond range but within the ATR buffer or wrong candle colour: **4** days (0.3%)

## XAU ORB New York M30

| Step | Days | % of weekdays |
|---|---:|---:|
| Weekdays evaluated | 1299 | 100% |
| Opening range accepted | 808 | 62.2% |
| Price closed beyond the range in the trade window | 713 | 54.9% |
| **Traded** | **78** | **6.0%** |

Median opening-range size = 1.76 × ATR (filter band see SET).

Why the range was rejected:

- opening range too WIDE vs ATR (InpMaxRangeATR): **440** days (33.9%)
- opening volume below its 20-day median threshold: **42** days (3.2%)
- session never reached the end of the range (no ticks): **9** days (0.7%)

Why a real breakout day was not traded (last rule that blocked it):

- breakout candle body < InpBreakoutBodyMinimum: **409** days (31.5%)
- stop distance > InpMaximumStopATR x ATR (entry too far from the range): **124** days (9.5%)
- close beyond range but within the ATR buffer or wrong candle colour: **75** days (5.8%)
- breakout candle volume below InpMinBreakoutRelativeVolume: **27** days (2.1%)

## XAU ORB London NY Overlap M30

| Step | Days | % of weekdays |
|---|---:|---:|
| Weekdays evaluated | 1299 | 100% |
| Opening range accepted | 1201 | 92.5% |
| Price closed beyond the range in the trade window | 1194 | 91.9% |
| **Traded** | **116** | **8.9%** |

Median opening-range size = 0.92 × ATR (filter band see SET).

Why the range was rejected:

- opening volume below its 20-day median threshold: **87** days (6.7%)
- session never reached the end of the range (no ticks): **9** days (0.7%)
- opening range too WIDE vs ATR (InpMaxRangeATR): **1** days (0.1%)
- no/too few M1 bars in the range window (holiday, closed market): **1** days (0.1%)

Why a real breakout day was not traded (last rule that blocked it):

- breakout candle body < InpBreakoutBodyMinimum: **693** days (53.3%)
- research session filter (InpResearchSession) blocked the entry hour: **228** days (17.6%)
- close beyond range but within the ATR buffer or wrong candle colour: **130** days (10.0%)
- stop distance > InpMaximumStopATR x ATR (entry too far from the range): **16** days (1.2%)
- breakout candle volume below InpMinBreakoutRelativeVolume: **10** days (0.8%)
- spread > InpMaxSpreadRangePercent of range: **1** days (0.1%)

## US100 ORB New York M30

| Step | Days | % of weekdays |
|---|---:|---:|
| Weekdays evaluated | 1301 | 100% |
| Opening range accepted | 1159 | 89.1% |
| Price closed beyond the range in the trade window | 1127 | 86.6% |
| **Traded** | **48** | **3.7%** |

Median opening-range size = 1.68 × ATR (filter band see SET).

Why the range was rejected:

- opening volume below its 20-day median threshold: **68** days (5.2%)
- opening range too WIDE vs ATR (InpMaxRangeATR): **62** days (4.8%)
- session never reached the end of the range (no ticks): **12** days (0.9%)

Why a real breakout day was not traded (last rule that blocked it):

- breakout candle body < InpBreakoutBodyMinimum: **640** days (49.2%)
- stop distance > InpMaximumStopATR x ATR (entry too far from the range): **279** days (21.4%)
- close beyond range but within the ATR buffer or wrong candle colour: **151** days (11.6%)
- spread > InpMaxSpreadRangePercent of range: **9** days (0.7%)

## US100 H1 ORB 13UTC

| Step | Days | % of weekdays |
|---|---:|---:|
| Weekdays evaluated | 1301 | 100% |
| Opening range accepted | 1159 | 89.1% |
| Price closed beyond the range in the trade window | 796 | 61.2% |
| **Traded** | **289** | **22.2%** |

Median opening-range size = 2.21 × ATR (filter band see SET).

Why the range was rejected:

- opening range too WIDE vs ATR (InpMaxRangeATR): **69** days (5.3%)
- opening volume below its 20-day median threshold: **61** days (4.7%)
- session never reached the end of the range (no ticks): **11** days (0.8%)
- no/too few M1 bars in the range window (holiday, closed market): **1** days (0.1%)

Why a real breakout day was not traded (last rule that blocked it):

- breakout candle body < InpBreakoutBodyMinimum: **290** days (22.3%)
- stop distance > InpMaximumStopATR x ATR (entry too far from the range): **175** days (13.5%)
- close beyond range but within the ATR buffer or wrong candle colour: **32** days (2.5%)
- spread > InpMaxSpreadRangePercent of range: **10** days (0.8%)

