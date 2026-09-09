# News Pulse Ten-Year Research Plan

Saved: 2026-08-10

Status: Planned and paused. No ten-year market-data download has been completed.

## Objective

Create a reproducible ten-year research dataset for the long-only News Pulse EA and use it for a scientifically defensible event-study backtest on XAUUSD.

Fixed study window:

- Start: 2016-08-09 00:00:00 UTC
- End: 2026-08-09 00:00:00 UTC (exclusive)
- Instrument: XAUUSD
- Events: U.S. NFP, CPI, and scheduled FOMC policy statements
- Primary resolution: real bid/ask ticks with millisecond timestamps
- EA direction: long-only
- Risk setting for the first locked test: 1% per event

## Important Correction to the Existing Test

The existing one-year MT5 report used `Model=0`, which is MT5 "Every tick" generation from minute history. It was not `Model=4`, "Every tick based on real ticks."

That result remains useful as a preliminary experiment, but it is not sufficient evidence for a 30-to-60-second news strategy. The ten-year paper test must use real bid/ask tick data around every event.

## Data Sources

### Primary XAUUSD data

- Dukascopy Historical Data Export / JForex Historical Data Manager
- Required fields: UTC timestamp, bid, ask, bid volume, ask volume when available
- Preserve the untouched downloaded files before conversion

Official source:

- https://www.dukascopy.com/swiss/english/marketwatch/historical/

### NFP and CPI timestamps

- U.S. Bureau of Labor Statistics archived releases
- Use the actual publication date and time, not a modern recurring-calendar assumption
- Record exceptional rescheduling caused by government shutdowns or other disruptions

Official sources:

- https://www.bls.gov/bls/news-release/
- https://www.bls.gov/bls/news-release/cpi.htm

### FOMC timestamps

- Federal Reserve meeting calendars and historical materials
- Include scheduled policy statements in the primary study
- Store unscheduled/emergency announcements separately and do not mix them into the primary sample without a declared robustness test

Official sources:

- https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- https://www.federalreserve.gov/monetarypolicy/fomc_historical_year.htm

### Optional independent validation

- CME Gold futures Time & Sales from CME DataMine
- Paid dataset; use as a robustness check rather than pretending it is the same instrument as a broker's XAUUSD CFD

Official source:

- https://www.cmegroup.com/market-data.html

## Current Environment Findings

- Free space on drive C at the storage check: approximately 72.31 GB
- Node.js and Python are available
- Windows curl is available
- 7-Zip and xz were not found on PATH
- Direct requests to `datafeed.dukascopy.com` were redirected by the current network provider to `internetbaik.telkomsel.com`
- The direct HTTPS request also reported a certificate problem
- Do not bypass certificate validation for the scientific dataset
- Resume through Dukascopy's official Historical Data Export/JForex service or from a different trusted network

## Acquisition Strategy

Use two stages so storage and data quality are known before committing to a full decade of continuous ticks.

### Stage A — event-window dataset

1. Build and manually audit the complete official event calendar.
2. Download real XAUUSD bid/ask ticks from T-15 minutes through T+15 minutes for every event.
3. This is sufficient for the current EA, which places an order 30 seconds before the event and exits no later than 60 seconds afterward.
4. Preserve a wider window than the EA needs so spread baselines, data gaps, and pre-event conditions can be measured.
5. Run integrity checks and estimate the full-decade storage requirement from the actual compressed and expanded sizes.

### Stage B — continuous dataset

1. Download full continuous XAUUSD tick history in monthly chunks only if the measured size fits a conservative 55 GB working limit.
2. Keep at least 15 GB free for MT5 caches, conversions, reports, and temporary files.
3. If the continuous tick dataset would exceed the limit, retain the event-window tick data and add continuous M1 background bars instead.

## Required Files

The resumed work should produce this structure:

```text
Research/
  README.md
  provenance/
    sources.csv
    download-manifest.csv
    checksums-sha256.txt
  events/
    events-2016-2026.csv
    event-audit.md
  raw/
    dukascopy/
  normalized/
    xauusd-event-ticks-2016-2026.parquet
    xauusd-event-ticks-2016-2026.csv.gz
  mt5-import/
    XAUUSD_NEWS_RESEARCH_ticks.csv
    XAUUSD_NEWS_RESEARCH_symbol.json
  reports/
    data-quality-report.md
```

## Event Calendar Schema

```text
event_id,event_type,release_time_utc,release_time_new_york,scheduled_or_unscheduled,source_url,source_sha256,notes
```

Every row must have an official source URL. Daylight-saving conversion must use the `America/New_York` timezone database, not fixed UTC offsets.

## Tick Quality Checks

For every event window:

- Confirm timestamps are ordered and unique where expected
- Detect missing seconds and missing minutes
- Verify ask is not below bid
- Calculate median, 95th percentile, 99th percentile, and maximum spread
- Flag zero or negative prices
- Flag large price jumps for manual inspection
- Record first and last tick around each event
- Record tick count and quote frequency
- Keep raw and normalized SHA-256 checksums

An event with insufficient data must be excluded with a recorded reason; it must not silently disappear.

## MT5 Integration

1. Create a dedicated custom symbol named `XAUUSD_NEWS_RESEARCH`.
2. Copy the relevant XAUUSD contract properties deliberately before importing history.
3. Import normalized real bid/ask ticks in MT5's supported tick format.
4. Add a historical tester mode to the EA that reads the audited `events-2016-2026.csv` schedule.
5. Keep live mode anchored to the MT5 broker calendar and broker quotes.
6. Never let the tester use today's live calendar to reconstruct old events.

MT5 documentation:

- https://www.metatrader5.com/en/terminal/help/trading_advanced/custom_instruments
- https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation

## Locked Experimental Design

Do not optimize on the final period.

- Development: 2016-08-09 through 2022-12-31
- Validation: 2023-01-01 through 2024-12-31
- Final untouched test: 2025-01-01 through 2026-08-09

Primary locked configuration:

- Long-only buy stop
- Entry offset: $6
- Stop loss: $6
- Risk: 1% of current equity
- Placement: T-30 seconds
- Trailing activation: 1.5R
- Trailing distance: $15
- Forced exit: T+60 seconds

Robustness tests should vary execution delay, spread inflation, slippage, missing ticks, entry offset, stop distance, and exit time. Report all tested variants, not only the winner.

## Restart Checklist

1. Confirm at least 72 GB remains free or select a larger data drive.
2. Access Dukascopy Historical Data Export/JForex from a trusted connection without certificate bypasses.
3. Download a single active-event day as a pilot.
4. Verify timestamp timezone, bid/ask ordering, price precision, and file licensing.
5. Measure pilot storage and choose Stage A plus Stage B, or Stage A plus continuous M1 bars.
6. Generate and audit the official NFP/CPI/FOMC event calendar.
7. Download event windows in resumable monthly batches.
8. Generate manifests and checksums immediately after every batch.
9. Only then modify the EA's historical tester mode and begin the ten-year test.

## Completion Standard

The data phase is complete only when:

- Every included event has an official timestamp source
- Every event has a validated real-tick window
- Missing events and exclusions are documented
- Raw files are immutable and checksummed
- Normalized data can be regenerated from scripts
- MT5 can replay the research symbol without timestamp or spread errors
- The final 2025–2026 sample has not been used for parameter selection

