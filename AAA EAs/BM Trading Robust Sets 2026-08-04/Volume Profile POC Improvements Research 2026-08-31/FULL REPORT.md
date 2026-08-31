# Volume Profile POC improvement audit

## Decision

Do not replace the active LTA or ORB presets with the transcript-derived rules.

The first-retest/high-volume-zone logic reduced recent drawdown, but it was not profitable in the earlier development year and removed most of the active LTA system's return. The active BAT and website were intentionally left unchanged.

## Mechanical rules reconstructed from the transcript

- Build the profile only from completed history; no current-session look-ahead.
- Use the prior completed daily profile's POC and its contiguous high-volume zone.
- Require price to depart at least 1 ATR from the zone before considering a retest.
- Trade only the first retest.
- Enter at the near edge of the high-volume zone rather than its center POC.
- Put the stop beyond the complete high-volume barrier.
- Test fixed 2R/3R targets and the nearest known profile barrier, with a minimum 1R.
- Do not add martingale, averaging, or discretionary chart interpretation.

## Development selection — 2024-08-29 to 2025-08-28

| Variant | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|
| Active baseline | -3.11% | 0.98 | 25.62% | 20.13% | 242 |
| Heavy-zone edge, 3R | -2.98% | 0.89 | 23.68% | 11.00% | 38 |
| Heavy-zone edge, 2R | -7.23% | 0.72 | 26.32% | 11.15% | 38 |
| POC center, 2R | -13.34% | 0.54 | 21.95% | 15.88% | 41 |
| Edge with profile-barrier target | -4.22% | 0.85 | 23.68% | 10.70% | 38 |

No transcript variant passed the development period. The edge/3R version was carried forward only as the least-bad transcript reconstruction, not as a profitable selection.

## Locked comparison — 2025-08-29 to 2026-08-28

| Variant | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|
| Active baseline, same build/window | +107.82% | 1.44 | 33.33% | 15.24% | 249 |
| Transcript edge/3R | +8.10% | 1.30 | 30.00% | 5.69% | 40 |
| Difference | -99.72 points | -0.14 | -3.33 points | -9.55 points | -209 |

The transcript mode behaves like a severe frequency and drawdown filter. It is not a robust improvement because its prior-year PF was 0.89.

## ORB volume-profile check

The existing ORB research already compared its control against value-area, POC-bias and LVN filters. On the XAU selection sample, the control produced +13.33%, PF 2.16 and 32 trades; POC bias produced +3.04%, PF 1.57 and 17 trades. The profile filter again reduced activity and return, so the ORB code and active preset were not changed.

## Test integrity

- Exness MT5 Every Tick modelling from synchronized broker M1 history.
- USD 10,000 initial balance and 1% equity risk.
- Broker spread, random execution delay, commission and swaps where charged.
- 99% history quality.
- Candidate rules were compared on the earlier year before the locked recent-year run.
- The active source, BAT presets and website data were not overwritten.

## Artifacts

- `EA/LTA POC First Retest EA.mq5` — research source.
- `EA/LTA POC First Retest EA.ex5` — compiled research EA.
- `Sets/` — every exact tester preset.
- `Backtest Reports/` — native MT5 reports and graphs.
- `POC IMPROVEMENT EQUITY CURVES.png` — visual comparison.
- `RESULTS.csv` and `RESULTS.json` — machine-readable metrics.
