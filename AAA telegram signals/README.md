# Telegram to MetaTrader 5 Signal Copier

A local Windows/VPS automation service that polls a Telegram channel or chat every 10 seconds (using a Bot account), parses trading signals using a regex-based deterministic parser with Gemini AI validation, resolves symbol name variances across brokers, calculates lot sizes under customized risk configurations, and places orders directly on MetaTrader 5.

## Features

- **Double-Layer Parsing**: Combines a regex deterministic parser for standard layouts with a Gemini AI parser (`gemini-2.5-flash`) for advanced validation.
- **Database Caching**: Caches Gemini responses in a local SQLite database to prevent redundant API calls.
- **Auto Symbol Resolution**: Dynamically maps common forex and commodity codes (e.g. `USDCAD`, `GOLD`, `BTC`) to broker-specific symbols (e.g. `USDCADm`, `XAUUSD-STD`).
- **Flexible Risk Models**: Places orders using Fixed Lot, Balance/Equity Risk Percentage, or hard USD Risk Caps.
- **Per-Symbol Fixed Lots**: Uses a conservative default lot with UI overrides such as `XAUUSD=0.10`; aliases and broker suffixes are discovered automatically.
- **Break-Even Trade Manager**: Automatically moves open trade stop-losses to entry price once the first take-profit (TP1) is crossed.
- **Sleek Web Interface**: Features a premium dark-mode glassmorphic dashboard built with FastAPI and Jinja2 templates.

## Installation & Setup

1. **Open MetaTrader 5**: Ensure your MT5 terminal is running on the same Windows system, logged into your broker account, and has **Algo Trading** enabled.
2. **Execute Launcher**: Double click `run.bat`. It will create a virtual environment (`.venv`), install all packages listed in `pyproject.toml`, initialize the SQLite database, and launch the web server.
3. **Open Browser**: Open [http://51.91.121.15:8787](http://51.91.121.15:8787) to access the dashboard.
4. **Save Configuration**: Go to the **Settings** page, check that your credentials are set, and configure your risk preferences.
5. **Start Copying**: Toggle the Copier Switch on the dashboard header to start processing!

### Telegram Channel Access

- Paste a numeric chat ID, username, `t.me/c/...` link, or `web.telegram.org/a/#-100...` URL into Settings.
- Bot mode requires the Telegram bot to be an administrator/member of the target channel.
- User mode reads channels joined by your Telegram account. The first start shows a QR image at `storage/sessions/telegram_login_qr.png`; scan it from Telegram mobile via **Settings > Devices > Link Desktop Device**. If QR login expires, the app falls back to phone-code login in the visible console window.
- `Telegram Read Mode` can be switched between `API session` and `Browser scraper`. Browser mode opens Telegram Web through Selenium, keeps the Chrome profile/cookies in `storage/browser_profile`, and reads visible chat messages from the automated browser before sending them through the same copier pipeline. Keep browser headless off for the first login.

### Fixed Lots

Choose **Fixed Lot** in Settings. `Default Fixed Lot` applies to all unlisted symbols. Add overrides one per line:

```text
XAUUSD=0.10
BTCUSD=1.00
```

The signal and broker symbols are canonicalized before lookup. For example, `GOLD`, `XAUUSD`, and `XAUUSDm` share the `XAUUSD` override, while an unlisted pair such as `EURUSDm` uses the default lot. Every lot is normalized to the connected broker's volume constraints before order validation.

## Running Tests

To run the automated test suite:
- Double click `test.bat` (executes `pytest` on tests for parsing, symbol resolving, risk calculations, and trade requests builders).
