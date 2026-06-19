# Sniper Entry Python Bot

This automates the shared KhanSaab Sniper script logic on MT5 using the 4h timeframe.

Default mode is `live`, so valid fresh signals can place real MT5 orders. Use `--dry-run` when you want to scan without placing orders.

## Symbols

Configured logical symbols:

- `BTCUSD`

## Strategy

- Signal: EMA 9 / EMA 21 cross on the closed 4h candle.
- Entry: market price at scan time.
- SL: `ATR(14) * 1.5`.
- Broker TP: TP3 / final target.
- Lot sizing: risks `5%` of current account balance per trade by default, controlled by `risk.balance_risk_pct` in `config.json`.
- TP1 and TP2 are virtual management levels.
- At TP1 the bot closes 50% and moves SL to entry. At TP2 it trails SL to TP1.
- Guardrails block weekends, trades outside the configured New York session, duplicate exposure, more than one trade per day, daily loss beyond 5%, drawdown beyond 15%, and two consecutive losses inside the configured lookback.

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
