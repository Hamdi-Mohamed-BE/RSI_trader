# Sniper Entry Python Bot

This automates the shared KhanSaab Sniper script logic on MT5 using the 4h timeframe.

Default mode is `live`, so valid fresh signals can place real MT5 orders. Use `--dry-run` when you want to scan without placing orders.

## Symbols

Configured logical symbols:

- `BTCUSD`
- `ETHUSD`
- `XAUUSD`
- `XAGUSD`
- `US30` -> broker alias usually `DJ30.`
- `US100` -> broker alias usually `NAS100.`
- `EURUSD` -> prefers `EURUSD-VIP` if available

## Strategy

- Signal: EMA 9 / EMA 21 cross on the closed 4h candle.
- Entry: market price at scan time.
- SL: `ATR(14) * 1.5`.
- Broker TP: TP5 / final target.
- TP1-TP4 are virtual management levels.
- Management does not trail at TP1. Once TP2 is hit, it can move SL to TP1 for bot-owned trades.

## Run

From this folder:

```powershell
& "C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe" .\sniper_entry_bot.py --once
```

Keep it running:

```powershell
& "C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe" .\sniper_entry_bot.py --loop
```

Dry-run mode:

```powershell
& "C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe" .\sniper_entry_bot.py --once --dry-run
```

The first run bootstraps state and does not trade old signals. To change that, set `bootstrap_no_trade` to `false` in `config.json`.
