# MT5 refresh preset fix — 4 September 2026

## Problem

The website's fresh MT5 refresh showed only 4 LTA Volume Profile trades and a +4.77% return for 1 September 2025 through 25 August 2026. This contradicted the locked optimized result, which has roughly 247 trades over the full locked year.

## Root cause

The temporary MT5 `.set` file was written with malformed Windows line endings (`CR-CR-LF`). MT5 silently ignored that file and ran the EA's compiled default inputs instead of the selected BAT preset.

## Fix

- Preserve the source `.set` values and optimization metadata exactly.
- Write the temporary `.set` as bytes with valid line endings.
- Parse the Inputs section of every completed MT5 report.
- Compare MT5's actual inputs against the selected BAT settings.
- Reject the refresh instead of publishing misleading evidence when MT5 does not load the requested settings.

## Live verification

The website API was restarted and the same LTA period was rerun through the public refresh endpoint.

| Metric | Correct fresh MT5 result |
| --- | ---: |
| Period | 2025-09-01 to 2026-08-25 |
| Initial balance | $10,000.00 |
| Final balance | $20,838.97 |
| Return | +108.39% |
| Profit factor | 1.44 |
| Win rate | 33.47% |
| Max drawdown | 14.60% |
| Trades | 245 |
| Sharpe ratio | 5.19 |
| Recovery factor | 4.97 |
| History quality | 99% |

The two-trade difference versus the 247-trade locked headline is expected because this refresh ends on 25 August 2026 while the locked headline runs through 31 August 2026.

The native trade chart endpoint was also verified on the refreshed result: it resolved XAUUSD and returned 66 broker candle bars for trade 1.

## Automated verification

All 22 website tests pass, including new regression coverage for LTA preset preservation and MT5 setting comparisons.
