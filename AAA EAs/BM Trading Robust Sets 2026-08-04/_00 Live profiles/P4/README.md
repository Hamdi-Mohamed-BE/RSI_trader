# P4 (2026-11-10)

Four EAs, three launchers. Nothing here has been installed on a terminal.

| EA | Symbol | Timeframe | Settings | Source |
|---|---|---|---|---|
| Overnight Bias ORB | USTEC | M15 | Raw rules as tested (bias from the 09:30 open in the overnight range, 09:30-09:45 range break, ADX > 20, stop 0.3 x daily range, target 3x, flat 15:30 NY) | Research EA (Video ORB VWAP Ideas Raw 2026-11-09, InpStrategy 4) |
| Nasdaq 5M Candle Momentum | USTEC | M5 | REPLACE carry; stop and DI asked at install (tested: ATR6 stop, DI OFF) | Production EX5 (FTMO-AnyBroker / Edge 10 wrappers) |
| EMA3 | XAUUSD | H4 | Current preset | Production EX5 |
| Gold Band Wave | XAUUSD | H4 | BBTrend 20/50, signal SMA9, SMA200 trend, 2 x ATR14 stop, exit on the opposite cross | Research EA (Gold Band Wave Raw 2026-11-10) |

## Launchers

| BAT | Guard | Asks, in order | Default risk |
|---|---|---|---|
| `P4 - FTMO 1-Step guard.bat` | FTMO 1-Step rules (10% EOD-trailing max loss, 3% daily, best day <= 50%), state key P4O | Phase, risk type, risk, Nasdaq stop, Nasdaq DI, total cap, symbol cap | 0.5% |
| `P4 - FTMO 2-Step guard.bat` | Prop Ready guard (FTMO 2-step limits), state key P4T | Phase, risk type, risk, Nasdaq stop, Nasdaq DI, total cap, symbol cap | 0.75% |
| `P4 - no guard.bat` | None (`../Packages/P4`) | Risk type, risk, Nasdaq stop, Nasdaq DI | 0.5% |

The Nasdaq DI default is OFF in all three, as tested. There is no USDJPY EA; the BATs pass `-UsdJpyDIFilter OFF` so that question never appears.
Before running: MT5 open and logged in, account flat, Algo Trading off, hedging account. The installers never place orders; the guarded ones leave Algo Trading off.

## The two research EAs

Both trade with market orders only (no pending orders), so the guards accept them without changes. `build.py` includes their research sources with three asserted edits; none changes the tester path:

1. **Live clock (Overnight Bias ORB):** the research EA assumed a UTC server (Exness). Live, it now uses the broker clock minus UTC, rounded to 30 minutes, the way Nasdaq 5M does. In the tester it still uses `InpServerUtcOffsetHours`.
2. **Restart (Gold Band Wave):** the exit follows the direction of the signal that opened the trade, kept in memory. After an MT5 restart that is lost, so the open position's own direction is used. In the tester the two always agree.
3. **Preset checks:** an unused `InpAdaptivePortfolioControls` input was added so the installers' checks apply unchanged. In the no-guard build only, the lot budget is the installer's % of equity or fixed USD (RiskSupport) instead of balance x `InpRiskPercent`.

Known limits:

- **Gold Band Wave on H4 bars:** a broker whose server clock is not UTC (FTMO: UTC+2/+3) has different H4 bars, so signals will differ from the Exness tests.
- **Overnight Bias ORB keeps its "one trade a day" flag in memory.** A restart after that day's trade has closed could allow a second trade the same day.

## What has and has not been tested

- **Passed:**
  - 10 wrappers compiled with 0 errors and 0 warnings.
  - `-ValidateOnly` passes on all three BATs.
  - The source packages (FTMO-AnyBroker, ftmo 1_step, Best Prop 15, Edge 10, Current 14, Core 9, both research folders) are byte-identical before and after the build.
- **Not tested yet:**
  - Native parity of the edited research wrappers against the research EX5.
  - A native run with a guard (the guards refuse the tester).
  - Any install on a terminal.
- **Evidence:** in-sample and selection-biased; `../../Portfolio P7 2026-11-10/` (native all years: +320R, PF 1.19, 36 trades/month, 1.7/day, closed DD 42R; FTMO simulation `P4_RESULTS.md` when it finishes).

`python build.py` rebuilds everything, and `python build.py installer` regenerates only the installers. Run either from `AAA EAs/EA store` with `uv run python`.
