# Telegram MT5 Copier

A focused Telegram-to-MT5 copy trader. The old RSI strategy, backtests, Docker setup, Playwright browser reader, and general dashboard were removed.

## Features

- Telegram Bot API polling with the configured bot token.
- Optional Telethon user API for channels your personal Telegram account can read.
- Source chat allowlist by numeric chat ID or `@username`.
- Signal parsing for market, limit, and stop entries; `SL`, `STOPLOSS`, and `STOPOSS` are accepted.
- One MT5 order per signal, sized to risk 5% by default.
- Broker minimum lot is used when calculated risk volume is smaller.
- Automatic broker symbol discovery, including suffixes such as `XAUUSDm`.
- Same-direction position and pending-order duplicate protection.
- Final TP on the order; SL moves to break-even once TP1 is reached.
- SQLite message/trade deduplication.
- Local settings and activity page at `http://127.0.0.1:8787`.
- Masked Gemini API key configuration for future image/LLM signal parsing.

## Start

Double-click `run.bat`. It installs dependencies through `uv`, starts the API copier, and keeps its console visible.

## Telegram Modes

### Bot API

The shared bot token is already stored in the ignored `.env`. A Telegram bot receives channel posts only when it has been added to that channel, normally as an administrator. It cannot read arbitrary channels simply because your personal account can see them.

### User API

For channels where the bot cannot be added:

1. Create an application at `https://my.telegram.org/apps`.
2. Enter the API ID, API hash, phone number, and source channels on the Settings page.
3. Select **User API (Telethon)** and save.
4. Run `login.bat` once and enter Telegram's login code.
5. Restart the copier.

The session is saved under `runtime/` and is excluded from Git.

## Safety

`LIVE_TRADING=true` sends orders to the MT5 account currently open on this computer. Confirm the MT5 account and AutoTrading state before starting. If broker minimum lot is forced, actual risk may exceed the requested percentage and is recorded in the trade state.

The bot token was shared in chat. Rotate it with BotFather if this conversation or machine is not private, then update it on the Settings page.
