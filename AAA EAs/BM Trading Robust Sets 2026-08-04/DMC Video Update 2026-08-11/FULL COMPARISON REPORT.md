# DMC video update — old versus new MT5 comparison

## Bottom line

The video-based rewrite improved both index results relative to the old EA, but it did not produce a robust deployable system. It materially damaged XAU performance, and the only promising optimized USTEC configuration lost money in the untouched final four months.

**Deployment decision:** keep the original XAU DmC EA and its active settings. Do not replace it, do not add the video EA to the synchronized BAT, and do not activate the video EA on a funded/live account. The new version is preserved as research code.

## Matched one-year baseline comparison

All six tests used Exness `Exness-MT5Trial16`, H1, USD 10,000 initial balance, 1% planned risk, 1:2000 leverage, MT5 Every Tick, random execution delay, and 2025-08-07 through 2026-08-06.

| Symbol | Version | Net | Return | Max equity DD | PF | Win rate | Trades |
|---|---|---:|---:|---:|---:|---:|---:|
| XAUUSD | Old | $2,087.40 | +20.87% | 9.82% | 1.15 | 41.20% | 233 |
| XAUUSD | Video baseline | -$874.20 | -8.74% | 24.83% | 0.92 | 32.80% | 186 |
| USTEC | Old | -$4,084.40 | -40.84% | 45.11% | 0.73 | 31.41% | 277 |
| USTEC | Video baseline | $279.12 | +2.79% | 25.02% | 1.02 | 39.06% | 192 |
| US30 | Old | -$353.67 | -3.54% | 29.02% | 0.98 | 37.99% | 279 |
| US30 | Video baseline | $449.54 | +4.50% | 23.09% | 1.04 | 37.88% | 198 |

### Improvement by market

| Symbol | Return change | DD change | Verdict |
|---|---:|---:|---|
| XAUUSD | -29.62 percentage points | +15.01 points worse | Clear regression; retain old EA |
| USTEC | +43.64 percentage points | 20.09 points lower | Large relative improvement, but PF 1.02 is not a useful edge |
| US30 | +8.03 percentage points | 5.93 points lower | Improved, but PF 1.04 is too weak |

## Parameter-screen protocol

Seven predeclared video-faithful variants were screened on 2025-08-07 through 2026-04-06 using M1 OHLC only as a faster ranking model. The choices covered immediate confirmation versus retest, first-touch-only versus quick regain, daily/weekly/monthly combinations, and minimum RR. Variants were not generated after seeing individual trades.

A candidate had to be profitable, have PF above 1, and contain at least 20 trades before out-of-sample validation. XAUUSD and US30 produced no eligible candidate. USTEC v05—daily body levels, immediate confirmation, first-touch plus quick regain and minimum 1.25R—was the only material candidate:

| Development result | Value |
|---|---:|
| Net / return | $1,635.67 / +16.36% |
| Max equity DD | 7.08% |
| PF | 1.22 |
| Win rate | 40.00% |
| Trades | 105 |

## Untouched out-of-sample validation

The selected USTEC v05 parameters were frozen and tested on 2026-04-07 through 2026-08-06 using Every Tick and random delay.

| Version | Net | Return | Max equity DD | PF | Win rate | Trades |
|---|---:|---:|---:|---:|---:|---:|
| Old USTEC DmC | -$964.25 | -9.64% | 13.22% | 0.84 | 34.41% | 93 |
| Video v05 USTEC | -$315.74 | -3.16% | 11.16% | 0.92 | 31.03% | 58 |

The new version lost less than the old version, but it still lost money and had PF below 1. It therefore failed validation.

## USTEC v05 full-year reference

The frozen v05 set over the complete year produced:

| Metric | Result |
|---|---:|
| Final balance | $11,450.80 |
| Net / return | $1,450.80 / +14.51% |
| Max equity DD | $1,441.99 / 11.59% |
| Max balance DD | $1,318.51 / 10.65% |
| PF | 1.12 |
| Win rate | 37.20% |
| Wins / losses | 61 / 103 |
| Trades | 164 |
| Gross profit / loss | $13,620.90 / -$12,170.10 |
| Largest win / loss | $819.87 / -$124.80 |
| Average win / loss | $223.29 / -$115.19 |
| Sharpe / recovery | 2.02 / 1.01 |
| History quality | 100% |

The positive full-year aggregate is not enough to override the negative out-of-sample result.

## Files

- New source and compiled EA: `AAA Final EAs/AAA Final DmC Video EA/`
- Timestamped source summary: `TIMESTAMPED VIDEO SUMMARY.md`
- Rule mapping: `IMPLEMENTATION MAPPING.md`
- Machine-readable results: `comparison-summary.csv`
- Native full-year MT5 reports and graphs: `MT5 Reports/Baseline Full Year/`
- Native validation reports and graphs: `MT5 Reports/USTEC Validation/`
- All parameter-screen evidence: `MT5 Reports/Development Screens/`

## Honest interpretation

The public video communicates a discretionary framework, not a complete algorithm. Its exact level ranking, trade selection, stop placement and early-exit judgment are not numerically specified, and the presenter explicitly says the full nuances are outside the video. The EA therefore documents every mechanical assumption instead of claiming to reproduce an advertised 80–90% win rate.

Historical backtests are not profit guarantees. The index improvements are worth researching, but the present version is not suitable for live deployment because its final untouched sample remained negative.

