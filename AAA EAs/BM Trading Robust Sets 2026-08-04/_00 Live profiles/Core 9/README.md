# Core 9 (2026-11-05)

Nine EAs, three launchers. Nothing here has been installed on a terminal.

| EA | Symbol | Timeframe | Settings |
|---|---|---|---|
| Nasdaq 5M Candle Momentum | USTEC | M5 | Stop and DI asked at install |
| USDJPY London Open Momentum | USDJPY | M15 | DI asked at install, ADX20 stays on |
| 3 Way Gold | XAUUSD | M15 | Breakout module only, market entries |
| Sell Nasdaq 15min | USTEC | M15 | Full EA preset |
| EMA3 | XAUUSD | H4 | Current 14 preset |
| ORB VP Volume Confirmed | XAUUSD | M5 | Full EA preset, 2.5R |
| XAU Squeeze Momentum | XAUUSD | H1 | Current 14 preset (128 trades in the stream) |
| US100 Selective ORB V3 | USTEC | M5 | 0.5R |
| XAU RSI VWAP | XAUUSD | H1 | Current 14 preset |

## Launchers

| BAT | Guard | Asks, in order | Default risk |
|---|---|---|---|
| `Core 9 - FTMO 1-Step guard.bat` | FTMO 1-Step rules | Phase, risk type, risk, Nasdaq stop, Nasdaq DI, USDJPY DI, total cap, symbol cap | 0.5% |
| `Core 9 - FTMO 2-Step guard.bat` | Prop Ready (FTMO 2-step limits) | Phase, risk type, risk, Nasdaq stop, Nasdaq DI, USDJPY DI, total cap, symbol cap | 0.75% |
| `Core 9 - no guard.bat` | None | Risk type, risk, Nasdaq stop, Nasdaq DI, USDJPY DI | 0.5% |

Before running: MT5 open and logged in, account flat, Algo Trading off, hedging account. The installers never place orders, and the guarded ones leave Algo Trading off.

## Sell Nasdaq differs between the guarded and no-guard builds

The production EA places a sell stop. Both guards refuse pending orders, and any pending order on the account would also block the other EAs.

- **Guarded builds:** the EA holds the level itself and sells at market on the first tick with bid at or below it, using the same stop and target.
- **No-guard build:** keeps the real sell stop, the tested EX5.
- **Restart:** if MT5 restarts while the level is armed, that day's Sell Nasdaq trade is lost.
- **Parity (2026-11-09, PASS):** `parity/parity.py`, native Model 4, 2021-10-07 to 2026-11-01, no guard. The held stop traded on the same 270 days as production; net $8,567.82 vs $8,607.92 (-0.5%); entry price differs by 0 points at the median, at most 5.77. Both runs log the same 5,218 "market closed" retries of the production hard exit, which is not caused by this change.

## What has and has not been tested

- Passed: 18 wrappers compiled with 0 errors and 0 warnings, `-ValidateOnly` on all three installers, and the question flow with typed answers on the two guarded installers.
- The no-guard EX5s are the same files the earlier native runs used (Current 14 and Edge 10).
- Not tested: a real install on a terminal, and any native run of the guards, because they refuse the tester.
- The FTMO results in `Merged E10 FTMO17 2026-11-05/` are Python replays of the signal stream. They are in-sample, and the list was chosen on those same periods.
- Open issue inherited from `ftmo 1_step`: a mid-challenge rerun starts a new baseline, which can sit below FTMO's real trailing floor.

## Rebuild

```bash
uv run python "../BM Trading Robust Sets 2026-08-04/_00 Live profiles/Core 9/build.py"
```

Run it from `AAA EAs/EA store`. It recompiles the wrappers. Add `installer` to regenerate only the installers.
