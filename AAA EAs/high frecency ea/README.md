# XAUUSD M1 High Frequency OCO EA

This is the standalone package for the winning **current-price OCO** reconstruction. It is deliberately separate from the main BM Trading portfolio BAT and the EA website.

## Install

1. Open and log into the target MT5. Leave only that MT5 terminal open.
2. Run `INSTALL AND RUN HIGH FREQUENCY EA.bat`.
3. The safer recommended preset is applied automatically; there is no lot-size prompt.
4. MT5 closes cleanly, installs the EA and settings, then restarts on the dedicated `HIGH FREQUENCY OCO - XAUUSD M1` profile.

The chart now shows a plain-language status such as `ACTIVE`, `WAITING`, or `BLOCKED`. If Algo Trading is briefly unavailable during startup, the EA retries every five seconds instead of waiting silently for the next M1 bar.

## Verified backtest

Run `RUN VERIFIED XAU BACKTEST.bat`. It forces **XAUUSD M1** and a valid August 2026 date range in an isolated Exness tester, so an unrelated symbol left selected in MT5 cannot produce a misleading zero-result run.

The installer reads the active MT5 symbol list and automatically selects a currently tradable gold symbol, including broker variants such as `XAUUSDm`, `XAUUSD.`, `mXAUUSD`, or `GOLDm`. A chart-file fallback is used only if live symbol discovery is unavailable. It then backs up an older standalone HFT profile, enables the existing Algo Trading preference when `common.ini` is available, and records the installation in `LAST INSTALL.txt`.

The generated MT5 chart uses the native M1 chart type (`period_type=0`, `period_size=1`). An H1 profile uses `period_type=1`; the installer checks this distinction after MT5 restarts.

## Lot sizing

The installer applies a fixed **0.01 lot**. Dynamic equity scaling is disabled and both the configured minimum and maximum are 0.01 lot. This is the safer setting selected for the $50 audit.

## Winning rules

- XAUUSD M1.
- Buy Stop at ask + $0.40 and Sell Stop at bid − $0.40.
- The sibling order is cancelled when one side triggers.
- Initial stop: $0.50.
- Trailing starts after $0.80 favorable movement and stays $0.45 behind price.
- Orders refresh every new M1 bar while flat.
- Maximum spread: $0.50; maximum holding time: 180 minutes.
- Session filter: 13:00-21:00 server time (UTC in the audited Exness history).
- No fixed take-profit, grid or martingale.

## Warning

The July–August MT5 test executed 43,226 trades and paid approximately $121,233 in commission under compounded sizing. Live VPS latency, broker throttling, slippage and simultaneous OCO fills can materially worsen the result. Use a demo account first and monitor the Experts and Journal tabs.

The complete backtest statistics and graph are stored in the `Audit` folder.
