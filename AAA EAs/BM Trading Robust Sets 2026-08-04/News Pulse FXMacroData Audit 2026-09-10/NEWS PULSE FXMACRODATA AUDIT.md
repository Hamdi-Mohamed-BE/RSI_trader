# News Pulse — FXMacroData MCP timing audit

## Decision

FXMacroData found 1 release missing from the tester calendar. A research-only corrected MT5 replay is required before any production decision.

No live EA, BAT installer, website evidence, or risk setting was changed by this audit.

## Verified overlap

FXMacroData anonymous coverage used here: **2026-06-17T18:00:00+00:00 through 2026-09-04T12:30:00+00:00**. The provider returned official timestamps, but the anonymous tier does not cover the full historical backtests.

The tester list contains **6** of the **7** available NFP/CPI/FOMC releases. It is missing **1**: NFP 2026-09-04T12:30:00+00:00

| EA | Matched events | Timestamp mismatches | Overlap trades | Overlap net | Overlap PF | Overlap WR | Result change |
|---|---:|---:|---:|---:|---:|---:|---:|
| News Pulse XAU — fresh MT5 Standard run | 4 | 0 | 4 | $13,400.00 | 671.00 | 75.00% | $0.00 |
| News Pulse XAG — fresh MT5 Standard run | 4 | 0 | 6 | $14,950.00 | 23.15 | 66.67% | $0.00 |
| News Pulse EURUSD — fresh MT5 Standard run | 6 | 0 | 8 | $2,624.38 | 11.71 | 75.00% | $0.00 |

## What the current EA does

- **Live:** MT5's built-in USD economic calendar supplies the broker-server release timestamp. The EA refreshes an eight-day cache every five minutes and recognizes NFP, CPI and FOMC by event name.
- **Placement clock:** a fresh broker-stamped tick is required. The VPS clock and VPS timezone are ignored. Orders are accepted only inside the configured pre-release lead window.
- **Tester:** MT5 does not expose its economic calendar in Strategy Tester, so the EA uses hard-coded official dates, assumes NFP/CPI at 08:30 New York and FOMC at 14:00 New York, converts New York time to tester server time with DST handling, then uses the release epoch as the event ID.

## What FXMacroData changed

Every event that was already present in the tester used the same timestamp as FXMacroData. However, the tester omitted the event listed above, so a corrected replay is required to measure its P&L effect.

FXMacroData still improves the process by replacing manually maintained future tester dates with a reproducible official-source calendar and source receipts. It does **not** prove the full-period result until historical access covers every event.

## Important constraint

The actual CPI/NFP/rate value is published at the release. News Pulse places its pending orders before the release, so filtering those orders using the actual value would introduce look-ahead bias. A legitimate actual-versus-consensus reaction rule would need a separate post-release strategy, paid consensus data, latency assumptions and a new MT5 backtest.
