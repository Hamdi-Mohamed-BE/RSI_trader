# RSI Divergence MT5 Bot

This project turns the optimized RSI divergence strategy into a local MT5 bot and a small FastAPI dashboard.

It supports four strategy modes:

- `signal_no_tp_protection` — split into one MT5 order per TP leg, no SL moves
- `signal_with_tp_protection` — split legs; when TP1/TP2 hit, move remaining legs' SL to that TP
- `signal_full_no_tp_protection` — one full-size MT5 order (total lot), final TP only, no SL moves
- `signal_full_with_tp_protection` — one full-size MT5 order; when TP1/TP2 hit, move SL to that TP

It also supports three decision profiles:

- `safe`: live trading uses spread, TP distance, risk cap, duplicate, open-position, and max-setup filters.
- `balanced`: live trading and backtests use spread, TP distance, and risk caps, including per-symbol risk caps when configured. Open-position and max-setup filters are ignored so the live runner behaves closer to the backtest.
- `backtest`: live auto-run takes the same valid strategy signals that the raw backtest takes. Spread, risk-cap, open-position, and max-setup filters are ignored; only duplicate same-signal protection remains so the same closed candle is not ordered repeatedly.

Each profile is only a preset. You can override the active filters directly in `risk:`:

```yaml
risk:
  use_spread_filter: true
  use_tp1_spread_filter: true
  use_risk_filter: true
  use_existing_position_filter: false
  use_max_setups_filter: false
  min_tp1_spread_multiple: 1.5
  max_daily_loss_pct: 15.0
```

## Setup

```powershell
cd "C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot"
uv sync
```

On a fresh Windows VPS, you can also double-click:

```text
install.bat
```

Copy the example config if you want a private live config:

```powershell
Copy-Item config.example.yaml config.yaml
```

The example config starts with:

```yaml
bot:
  dry_run: true
```

Keep `dry_run: true` for testing. Set it to `false` only when you want the bot to place real MT5 orders.

## Run The Web Page

```powershell
uv run rsi-bot web --config config.example.yaml
```

Or double-click:

```text
run.bat
```

Then open:

```text
http://127.0.0.1:8787
```

## Run With Docker On Linux VPS

The Docker setup runs two services: the bot web dashboard and a Wine-based MT5 container with browser access.

Before first start, edit `config.yaml` for Docker:

```yaml
mt5:
  mode: linux_bridge
  login: 1109378
  password: "your-password"
  server: VTMarkets-Demo
  host: mt5
  port: 8001
  transport: tcp
bot:
  dry_run: false
web:
  host: 0.0.0.0
  port: 8787
```

You can use `config.docker.example.yaml` as the Docker template.

Start:

```bash
docker compose up -d --build
```

Open:

```text
Bot dashboard: http://SERVER_IP:8787
MT5 web view:  http://SERVER_IP:6081
```

Logs:

```bash
docker compose logs -f bot
docker compose logs -f mt5
```

The MT5 web view login is controlled by `CUSTOM_USER` and `PASSWORD` in `docker-compose.yml`.

## Run One Scan

```powershell
uv run rsi-bot once --config config.example.yaml
```

## Run The Bot Continuously

From the web dashboard, click **Start auto run** to scan all symbols on a loop until you click **Stop auto run**.

Or from the CLI:

```powershell
uv run rsi-bot run --config config.example.yaml
```

Set `dry_run: false` in your config when you are ready for live MT5 orders.

## Backtest From CLI

```powershell
uv run rsi-bot backtest --config config.example.yaml --start 2026-05-13T00:00:00+00:00 --end 2026-05-21T00:00:00+00:00 --strategy signal_with_tp_protection
```

## Notes

- MT5 must be open, logged in, and connected.
- The bot uses confirmed closed candles only.
- The web page and console show the same bot logs.
- Docker mode uses `mt5.mode: linux_bridge` and talks to the Wine MT5 container over the internal bridge port.
- The dashboard includes a Manual live trade panel. It sends real market orders when confirmed, even if the text came from a pasted external signal.
- Backtests, scan reporting, and live trading use the same shared RSI-divergence strategy rules after a raw signal appears.
- Live trading can run the shared decision function in `safe`, `balanced`, or `backtest` profile via `bot.trade_decision_profile`.
- Set `max_setup_risk_usd` on a symbol to override the global `risk.max_setup_risk_usd` cap for that market.
- Backtests use broker tick values from MT5 and follow the configured decision profile so scan, live, and backtest behavior stay aligned.
- Full backtest and chart preview use the same symbol backtest engine. Chart preview defaults to the symbol's configured candle size; changing the preview candle size intentionally tests a different timeframe.
- Live trading records a UTC day-start balance/equity guard. If equity drawdown reaches `risk.max_daily_loss_pct`, the bot blocks new trades until the next UTC day while still running position protection checks.
- Intrabar handling is conservative: if SL and TP are inside the same candle, the stop is counted first.
- Broker suffixes are grouped automatically for duplicate and position checks. For example, `XAUUSD-VIP`, `XAUUSD-STD`, and `XAUUSD.crp` share the market key `XAUUSD`, while orders still use the exact configured broker symbol.
