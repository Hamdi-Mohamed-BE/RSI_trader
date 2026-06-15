# Parabolic SAR MT5 Bot

This bot trades Parabolic SAR direction flips on the 5-minute timeframe.

Default mode is `live`, so fresh PSAR flips can place real MT5 market orders. Use `--dry-run` whenever you want to test without trading.

## Symbols And Lots

Configured in `config.json`:

- `BTCUSD`: 0.10 lot
- `ETHUSD`: 5.00 lots
- `XAUUSD`: 0.10 lot
- `XAGUSD`: 0.10 lot
- `EURUSD`: 0.50 lot

To change symbols, aliases, or lots, edit only the `symbols` section in `config.json`.

## How It Trades

- Timeframe: `M5`
- Loop interval: 30 seconds
- Buy: PSAR flips from above price to below price.
- Sell: PSAR flips from below price to above price.
- On an opposite flip, the bot closes bot-owned opposite positions and opens the new direction.
- The stop loss is the current PSAR value.
- By default it manages only positions it opened itself, using the configured magic number/comment.
- The first run bootstraps state and does not trade an old flip. Set `bootstrap_no_trade` to `false` only if you intentionally want it to act on the latest historical flip.

## Run Once

```powershell
& "C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe" .\parabolic_sar_bot.py --once
```

## Keep Running

```powershell
& "C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe" .\parabolic_sar_bot.py --loop
```

Stop it with `Ctrl+C` in the terminal window.

## Dry Run

```powershell
& "C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe" .\parabolic_sar_bot.py --once --dry-run
```
