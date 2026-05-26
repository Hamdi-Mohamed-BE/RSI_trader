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

Set any `use_*_filter` key to `null` to fall back to the profile default. Set it to `true` or `false` to force that filter on or off regardless of profile.

## Risk settings reference

These keys live under `risk:` in `config.yaml`. They control **RSI auto-run / manual live trade** filtering unless noted otherwise. Telegram signal copy uses some of the same rules (daily loss guard, open-symbol guard) but has its own settings under `telegram_signals:`.

| Setting | What it does | When it blocks a trade |
| --- | --- | --- |
| `max_setup_risk_usd` | Maximum estimated loss in USD if the stop loss is hit for one setup. Uses broker tick value × lot × SL distance. Split strategies count all legs; full/single strategies count one position at `lot_per_leg`. | Only when `use_risk_filter: true`. A symbol-level `max_setup_risk_usd` overrides this global cap for that market. |
| `use_daily_loss_guard` | Master switch for the daily loss system. | When `false`, daily loss checks are disabled entirely. |
| `max_daily_loss_pct` | Daily loss limit as a % of the UTC day-start balance. Used in two ways: (1) **halt** — if current equity is down by this % from day start, no new RSI trades until the next UTC day; (2) **pre-trade cap** — reject a new setup if its estimated SL risk exceeds `day_start_balance × max_daily_loss_pct / 100`. | Active when `use_daily_loss_guard: true` and `max_daily_loss_pct > 0`. Telegram copies also respect the halt (unless hard copy bypasses it). |
| `max_extension_atr` | Signal **generation** filter, not a live order filter. Skips creating a signal when entry is too far from the 20 EMA: `abs(entry - ema20) > ATR × max_extension_atr`. | During RSI scan/backtest signal detection only. No effect after a signal already exists. |
| `max_spread_atr` | Compares current spread to volatility: `spread / ATR_proxy` must stay at or below this cap. ATR proxy comes from the signal’s SL distance and `sl_atr_mult`. | When `use_spread_filter: true` (or profile default enables spread filter). Blocks wide-spread entries. |
| `max_live_entry_drift_risk` | Live execution guard. Compares signal entry to current bid/ask. Adverse drift must stay within `SL distance × this fraction`. Example: `0.35` allows price to move up to 35% of the SL distance against you before the order is rejected. | When placing RSI bot orders with a reference entry price. Telegram copy passes `entry_price: null`, so this drift check is skipped for Telegram. Set to `null` to disable everywhere. |
| `min_tp1_spread_multiple` | Minimum distance from entry to TP1, measured as a multiple of the current spread: `TP1 distance ≥ spread × this value`. | When `use_tp1_spread_filter: true` (or profile default enables it). Avoids trades where TP1 is too close to pay the spread. |
| `use_spread_filter` | Force the spread/ATR filter on or off. `null` = use `bot.trade_decision_profile` default. | See `max_spread_atr`. |
| `use_tp1_spread_filter` | Force the TP1-vs-spread filter on or off. `null` = profile default. | See `min_tp1_spread_multiple`. |
| `use_risk_filter` | Force the per-setup USD risk cap on or off. `null` = profile default. | See `max_setup_risk_usd`. |
| `use_existing_position_filter` | Force the open-position filter on or off. Blocks a new setup when any open position exists on the same **market key** (e.g. `XAUUSD` groups `XAUUSD-VIP`, `XAUUSD-STD`, etc.). | RSI auto-run / manual trade when enabled. Separate from `telegram_signals.ignore_open_symbol_trades`. |
| `use_max_setups_filter` | Force the concurrent-setup cap on or off. Blocks new entries when tracked active setups ≥ `bot.max_concurrent_setups`. | RSI auto-run when enabled. Skipped signals are retried on the next poll (not marked seen). |
| `skip_if_symbol_has_position` | Default input for the **safe** profile’s open-position filter. If you set `use_existing_position_filter` explicitly, this value is ignored. | Only affects profile defaults when `use_existing_position_filter: null`. |

### How your current `balanced` profile interacts

With `bot.trade_decision_profile: balanced`, the defaults are: spread **on**, TP1 spread **on**, risk cap **on**, open-position **off**, max-setups **off**.

Your overrides:

```yaml
use_spread_filter: false        # spread/ATR filter OFF
use_tp1_spread_filter: true     # TP1 must be ≥ 1.5× spread
use_risk_filter: false          # max_setup_risk_usd cap OFF
use_existing_position_filter: false
use_max_setups_filter: false
skip_if_symbol_has_position: false
```

So today the bot mainly enforces **TP1 distance vs spread**, **daily loss guard (15%)**, and **signal extension vs EMA** at scan time. It does **not** enforce spread/ATR, per-setup USD risk cap, open-position, or max-setup limits unless you turn those filters back on.

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
- See **Risk settings reference** above for what each `risk:` key does.
- Backtests use broker tick values from MT5 and follow the configured decision profile so scan, live, and backtest behavior stay aligned.
- Full backtest and chart preview use the same symbol backtest engine. Chart preview defaults to the symbol's configured candle size; changing the preview candle size intentionally tests a different timeframe.
- Live trading records a UTC day-start balance/equity guard. If equity drawdown reaches `risk.max_daily_loss_pct`, the bot blocks new trades until the next UTC day while still running position protection checks.
- Intrabar handling is conservative: if SL and TP are inside the same candle, the stop is counted first.
- Broker suffixes are grouped automatically for duplicate and position checks. For example, `XAUUSD-VIP`, `XAUUSD-STD`, and `XAUUSD.crp` share the market key `XAUUSD`, while orders still use the exact configured broker symbol.
