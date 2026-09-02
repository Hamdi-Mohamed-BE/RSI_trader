# XAUUSD M1 High Frequency OCO EA

This is the standalone research package for the **XAUUSD M1 OCO** reconstruction. It is deliberately separate from the main BM Trading portfolio BAT and the EA website.

> **Status: demo research only.** The original high-profit audit used MT5 `Model=0` (ticks generated from M1 bars). That model is unsuitable for a strategy whose trades often last only seconds. On 2026-09-01 the old build made 891 demo trades and lost $214.95 (PF 0.48). Do not use the old result as evidence of a live edge.

## Install

1. Open and log into the target MT5. Leave only that MT5 terminal open.
2. Run `INSTALL AND RUN HIGH FREQUENCY EA.bat`.
3. The safer recommended preset is applied automatically; there is no lot-size prompt.
4. MT5 closes cleanly, installs the EA and settings, then restarts on the dedicated `HIGH FREQUENCY OCO - XAUUSD M1` profile.

The chart now shows a plain-language status such as `ACTIVE`, `WAITING`, or `BLOCKED`. If Algo Trading is briefly unavailable during startup, the EA retries every five seconds instead of waiting silently for the next M1 bar.

## Reality-check backtest

Run `RUN VERIFIED XAU BACKTEST.bat`. It forces **XAUUSD M1** and MT5 `Model=4` (**Every tick based on real ticks**) in an isolated Exness tester. A report is valid only when its History Quality explicitly says `100% real ticks`; `n/a` or mixed quality is rejected.

The installer reads the active MT5 symbol list and automatically selects a currently tradable gold symbol, including broker variants such as `XAUUSDm`, `XAUUSD.`, `mXAUUSD`, or `GOLDm`. A chart-file fallback is used only if live symbol discovery is unavailable. It then backs up an older standalone HFT profile, enables the existing Algo Trading preference when `common.ini` is available, and records the installation in `LAST INSTALL.txt`.

The generated MT5 chart uses the native M1 chart type (`period_type=0`, `period_size=1`). An H1 profile uses `period_type=1`; the installer checks this distinction after MT5 restarts.

## Lot sizing

The installer applies a fixed **0.01 lot**. Dynamic equity scaling is disabled and both the configured minimum and maximum are 0.01 lot. This is the safer setting selected for the $50 audit.

## Live Guard v1.20 rules

- XAUUSD M1.
- The completed previous M1 bar must have at least 0.5 ATR range and at least 1.0× its 20-bar average tick volume.
- Virtual buy/sell triggers sit $0.40 beyond the previous M1 high/low.
- Only one market order can be sent. The EA no longer leaves two separate broker pending orders that can race and both fill.
- Initial stop: $0.50.
- Trailing starts after $0.80 favorable movement and stays $0.45 behind price.
- Trigger levels refresh every new M1 bar while flat.
- Maximum spread: $0.25; maximum holding time: 180 minutes.
- Session filter: 13:00-21:00 server time (UTC in the audited Exness history).
- Cooldown: 60 seconds after a win and 300 seconds after a loss.
- Maximum 12 trades/day and a $3 realized daily-loss guard at the fixed 0.01 lot.
- No fixed take-profit, grid or martingale.

## Honest validation

The repaired build compiled with zero errors and zero warnings. The latest contiguous 100%-real-tick Exness test (2026-06-01 to 2026-07-31) was still negative: **-$33.89, PF 0.82, 36.20% wins, 0.43% max equity drawdown, 453 trades** from a $10,000 reporting deposit at fixed 0.01 lot. This means the safety bugs are fixed, but the strategy is not yet validated as profitable.

A Raw/Zero-spread account and a lower-latency VPS may reduce costs and races, but they cannot turn PF 0.82 into a proven edge. Keep this build on demo and use the diagnostic report in `Live Diagnosis 2026-09-01`.
