# H4 Box Bot

Python MT5 bot for XAUUSD, XAGUSD, BTCUSD, EURUSD, USDJPY, US30, US100, and ETHUSD.

Default mode is `dry_run`, so it scans and prints trade plans without placing real orders. Use `--live` only after the dry-run output matches what you expect.

## Strategy

- Box: previous closed `H4` candle high/low.
- Execution: closed `M5` candles.
- Range mode:
  - Sell rejection near the H4 high, targeting the H4 low.
  - Buy rejection near the H4 low, targeting the H4 high.
  - Final target requires about `1:3` reward/risk.
- Breakout mode:
  - If an M5 candle closes outside the H4 box by an ATR buffer, the bot stops fading that edge.
  - It waits for a retest of the broken box edge and trades continuation with TP1/TP2/TP3 at 1R/2R/3R.
- Entries split into 3 legs:
  - TP1 = 1R
  - TP2 = 2R
  - TP3 = opposite box edge in range mode, or 3R in breakout mode
- When TP1 is hit, remaining open legs move stop loss to breakeven.

## Lots

Configured in `config.json`:

- `XAUUSD`: `0.05` lot per leg
- `XAGUSD`: `0.05` lot per leg
- `BTCUSD`: `0.08` lot per leg
- `EURUSD`: `0.01` lot per leg
- `USDJPY`: `0.01` lot per leg
- `US30`: `0.01` lot per leg
- `US100`: `0.01` lot per leg
- `ETHUSD`: `0.10` lot per leg (broker minimum)

## Run

Install dependency if needed:

```powershell
.\install.bat
```

Dry run once:

```powershell
.\run_dry_once.bat
```

Loop using the mode from `config.json`:

```powershell
.\run_loop.bat
```

Force live mode:

```powershell
python .\box_bot.py --loop --live
```

Stop the loop with `Ctrl+C`.

## Backtest

Run a one-year backtest with a `$300` starting balance:

```powershell
python .\backtest_box_bot.py --start 2025-06-17 --end 2026-06-17 --start-balance 300 --summary-only
```

The backtester saves full JSON and CSV trade reports in `reports/`.
