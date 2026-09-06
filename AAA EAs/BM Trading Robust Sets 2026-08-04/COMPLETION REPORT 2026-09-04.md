# Completion Report — 2026-09-04

## Step 1 — Installer failure

**Goal:** remove the strict-mode crash that stopped the Best Recommended BAT before MT5 started.

**Result:** fixed. The installer no longer references PowerShell's pipeline variable outside a pipeline. It now checks the selected portfolio explicitly before applying dynamic risk.

**Verification:** the dated Best Recommended BAT completed a read-only validation for all 14 active EAs. LTA was validated with 67 inputs and no terminal/profile/account files were changed.

## Step 2 — LTA hybrid volume-profile confirmation

**Goal:** preserve the current LTA strategy, add completed-profile POC/heavy-zone first-retest confirmation as a subordinate gate, optimize it, and measure the effect.

**Result:** implemented and compiled with zero errors/warnings.

The current active LTA remains unchanged because the filter reduced two-year maximum drawdown from 20.54% to 7.61% and improved PF from 1.22 to 1.45, but reduced return from +96.16% to +14.55% and trades from 488 to 48. The active BAT explicitly disables the filter. The H0.50 / D0.50 ATR / 3-bar configuration remains available as an optional selective research setting.

See the dedicated report: `Volume Profile POC Improvements Research 2026-08-31/STEP 2 - LTA HYBRID SUB-CONDITION REPORT.md`.

## Step 3 — Real MT5 evidence refresh

**Goal:** make the website's Update evidence control run MT5 rather than merely refiltering an archived curve.

**Result:** complete.

The EA detail page now:

1. accepts a date range from seven days to three years;
2. resolves the broker's real symbol, including suffix variants;
3. launches the selected EA and BAT preset in the isolated MT5 terminal;
4. shows queued/running/parsing progress;
5. replaces return, PF, win rate, drawdown and trade count with the native result;
6. redraws the equity curve;
7. replaces the trade table with native MT5 deal rows;
8. preserves a flat, valid result when the EA makes zero trades.

Only one tester run can execute at a time, duplicate clicks reuse the active job, and each run has a 30-minute timeout.

**Real verification:** BTC Top Down FVG Liquidity, BTCUSD M15, 2026-07-01 through 2026-07-10, MT5 Every Tick:

| Return | PF | Win rate | Max DD | Trades | Native deal rows |
| ---: | ---: | ---: | ---: | ---: | ---: |
| +0.97% | 1.97 | 50.00% | 2.03% | 2 | 2 |

## Step 4 — Show trade on a real price chart

**Goal:** add a per-trade graph with entry and exit markers.

**Result:** complete.

Every EA detail trade table now has a **View trade** action after a fresh MT5 run. It loads candles from the connected broker's MT5 terminal, automatically selects M1/M5/M15 detail based on trade duration, and renders:

- real broker OHLC candlesticks;
- entry price and time;
- exit price and time;
- long/short direction;
- win/loss marker;
- lot size and net P/L.

**Real verification:** the second BTC test trade loaded 83 native BTCUSD M1 candles, with entry 62,624.05 and exit 63,117.69.

## Step 5 — Quality checks

- Python compilation: passed.
- Browser JavaScript syntax: passed.
- Automated website tests: **20 passed**.
- Website health endpoint: healthy.
- Active catalogue: 14 EAs.
- LTA product page discloses that the optional POC gate is disabled in active BATs.
- Website restarted on `0.0.0.0:8080`.

