# Session VWAP Liquidity Snapback — Step 4

Start with `REPORT.md`. The final decision is to reject all five tested variants for production. No active installer, website catalogue, or live MT5 profile was changed.

## Reproducible order

1. `acquire_data.py` reads M5 history from the isolated Exness demo terminal.
2. `research.py` screens 8,630 configurations using only the two pre-lock years, freezes one configuration per asset, then opens the locked year.
3. `native.py` compiles the tester-only EA and runs five locked-year Every Tick tests plus five three-year 1-minute-OHLC context tests.
4. `build_report.py` creates the saved comparisons, temporal slices, Monte Carlo results and charts.
5. `verify_research.py` reconciles the artefacts and native trade ledgers.

The source data, exact SET files, native MT5 reports, trade ledgers, screen rows and generated charts are included. Backtests are historical diagnostics and not forecasts.
