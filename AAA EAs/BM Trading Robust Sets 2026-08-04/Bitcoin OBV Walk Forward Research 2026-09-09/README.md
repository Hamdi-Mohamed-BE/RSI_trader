# Bitcoin OBV Walk-Forward — raw paper transfer

This folder reproduces the implementable, published **Best** and **Best 50**
OBV portfolio variants from Deprez & Frömmel (2024) on archived Exness BTCUSD
CFD data.  It is isolated research only: no EA, website, BAT installer, or live
portfolio file is changed.

The paper uses Bitstamp traded volume.  MT5 does not provide that field here,
so this transfer necessarily uses broker tick volume as a proxy.  The report
separates broker-spread results from the paper-fee stress case.

Run order:

1. `python acquire_data.py`
2. `python run_raw_test.py`
3. `python verify_results.py`
