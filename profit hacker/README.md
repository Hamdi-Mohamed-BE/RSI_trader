# Profit Hacker Telegram to MT5 Bot

This bot reads fresh Telegram channel messages, parses trading signals, places MT5 orders, and watches open trades so the stop loss can move to break-even once the first TP price is reached.

It starts in dry-run mode. Keep it that way on a demo account until the logs match exactly what you expect.

## What it does

- Reads the Telegram channel id from your Telegram Web URL: `-1001303328644`.
- Ignores forwarded messages.
- Ignores stale messages older than `MAX_SIGNAL_AGE_SECONDS`, default `180`.
- Ignores messages that do not contain a valid symbol, direction, stop loss, and TP.
- Supports market signals like:

```text
NAS100 BUY NOW
STOPLOSS @ 29,235

TP @ 29,650
TP @ 29,810
TP @ 30,020
```

- Supports pending signals like:

```text
XAUUSD BUY LIMIT @ 3330
SL @ 3310
TP @ 3350
TP @ 3375
```

- Uses `RISK_PERCENT=5` by default.
- If the calculated volume is below the broker minimum lot, it uses the broker minimum lot.
- Auto-discovers broker symbols when `SYMBOL_MAP` does not define one, so `NAS100` can resolve to names like `NAS100.cash`, `NAS100m`, `US100`, or `USTECm`.
- `ORDER_MODE=single` places one trade with the last TP and moves SL to break-even when TP1 is touched.
- `ORDER_MODE=split` splits the total volume across all TP levels when broker minimum lot rules allow it.
- Cancels still-pending orders after `PENDING_ORDER_TTL_SECONDS`, default `180`.

## Setup

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
```

Edit `.env` and fill:

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_PHONE`
- `MT5_PATH`
- `SYMBOL_MAP` if your broker uses suffixes such as `NAS100.cash` or `XAUUSDm`

You get Telegram API credentials from `https://my.telegram.org`.

## First run

```powershell
.\.venv\Scripts\profit-hacker-bot.exe
```

Telegram may ask for a login code the first time. After that it stores a local `.session` file.

Leave `DRY_RUN=true` first. The bot will read and parse signals without sending live orders.

When the dry-run output looks right, use a demo MT5 account and set:

```env
DRY_RUN=false
```

## Important config

```env
RISK_PERCENT=5
MAX_SIGNAL_AGE_SECONDS=180
PENDING_ORDER_TTL_SECONDS=180
ORDER_MODE=single
SYMBOL_MAP=NAS100=NAS100.cash,GBPUSD=GBPUSD
AUTO_DISCOVER_SYMBOLS=true
```

For MT5 live trading, your terminal must be installed, logged in, and allowed to trade. Use a demo account first.
