# XAU 365-Day Configuration Selection

## Selected default

- Entry mode: `stop_only`
- New York observation window: `70` minutes from 13:30 UTC
- Target: `2.25R`
- Entry buffer: `1.0` historical spread
- Stop buffer: `24%` of the Asia range
- Protective lock: move the stop to `+0.04R` after price reaches `+0.20R`
- Risk: `3%` of current balance
- Maximum planned exposure: `3%`
- Pending-order cutoff: 16:00 UTC
- Force exit: 21:00 UTC

## One-year result

Period: 2025-07-30 00:00 UTC through 2026-07-30 00:00 UTC.

| Metric | Optimized result |
|---|---:|
| Trades | 21 |
| Wins / losses | 18 / 3 |
| Win rate | 85.71% |
| Profit factor | 2.86 |
| Net result | +3.89R |
| Return from $1,000 | +11.73% |
| Ending balance | $1,117.30 |
| Realized balance max DD | 5.68% |
| Estimated intratrade equity DD | 7.16% |
| Maximum concurrent trades | 1 |

The intratrade estimate uses each trade's recorded maximum adverse excursion
against the compounded balance. It is not a tick-by-tick portfolio-equity
reconstruction.

## Exit composition

| Exit | Trades | Net R |
|---|---:|---:|
| Protected `+0.04R` stop | 15 | +0.60R |
| Full `2.25R` target | 2 | +4.50R |
| Initial stop | 2 | -2.00R |
| 21:00 UTC force exit | 2 | +0.79R |

The high win rate is mainly created by the early protective lock. Only two
trades reached the full target, so the 85.71% figure should not be interpreted
as 18 large winners.

## Comparison with prior defaults

| Configuration | Trades | Win rate | PF | Realized DD | Return |
|---|---:|---:|---:|---:|---:|
| Old dual limit + stop | 54 | 42.59% | 0.60 | 49.44% | -25.70% |
| Baseline stop-only | 26 | 50.00% | 1.22 | 22.97% | +7.36% |
| Selected optimized stop-only | 21 | 85.71% | 2.86 | 5.68% | +11.73% |

## Robustness warning

The one-year sample contains only 21 trades. The first 275 days were slightly
negative (about -2.54%, PF 0.60), while the latest 90 days produced all of the
net growth (about +14.64%, seven wins and no losses). Nearby configurations
showed similar behavior, so the parameter cluster is not an isolated point,
but it is still regime-dependent and requires forward testing before real
capital is enabled.
