# Weekend Gap Reversal Research

This folder reproduces the raw weekend-overreaction paper rule on the connected
MT5 broker's weekly bars. It is deliberately separate from the active portfolio.

Run `py backtest_weekend_gap_reversal.py` with MT5 open and connected. The script
writes `results.json` and `FULL REPORT.md`. It never sends orders, edits the BAT,
or installs an EA.
