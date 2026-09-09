# FX Fixing Reversal — raw paper transfer

Raw, unoptimized CFD transfer of Krohn, Mueller and Whelan, “Foreign Exchange
Fixings and Returns around the Clock,” *Journal of Finance* 79(1), 2024.

The scripts use an isolated Exness demo M5 archive from 2021-09-01 through
2026-08-31 for EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCHF and USDCAD.
They do not connect to a live terminal, place trades, or change any EA, website,
BAT, set file, or portfolio.

1. `python acquire_data.py`
2. `python run_raw_test.py`
3. `python verify_results.py`

Final status: raw result rejected; no production action.
