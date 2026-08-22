# HAMA Algo Systems — EA Store

A FastAPI storefront generated from the Expert Advisors currently listed in:

`..\BM Trading Robust Sets 2026-08-04\_Auto Deploy\Install-BMTradingPortfolio.ps1`

The installer currently contains 27 entries. The public store offers 13 EAs; 14 Auction Market research presets are marked as development builds and excluded from the catalogue, ranking, API, pricing and purchase package.

## Run locally

The easiest option is to double-click `RUN EA STORE.bat`.

Or run it manually from this folder:

```powershell
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Then open <http://127.0.0.1:8080>.

## Pages

- `/` — store landing page
- `/eas` — searchable catalogue of the 13 available EAs
- `/eas/{slug}` — logic, risk notes, historical statistics and equity graph
- `/portfolio` — available EA portfolio and the combined core audit
- `/live` — read-only active MT5 account, equity curve, positions, orders and complete reconstructed trade history
- `/pricing` — individual and bundle prices
- `/risk` — disclosure and responsible-use page
- `/api/eas` — JSON catalogue
- `/api/live/portfolio` — uncached live MT5 snapshot used by the dashboard
- `/api/health` — sync status

## Catalogue and pricing

The installer PowerShell file is the source of truth for the catalogue. Restart the web server after changing the installer.

Descriptions and prices are in `app\catalog.py`. Public names remove the internal `AAA Final` prefix. Purchase buttons open WhatsApp for `+216 93 830 957` with the EA and price already included in the message. The available-EA package is USD 1,990. This version does not process payments or automatically issue licenses.

## Evidence

Available historical results and graph files are read from the existing research folders. The home page ranks all 13 available EAs by the latest complete one-year window, 11 August 2025 through 10 August 2026. The portfolio page leads with that profitable one-year cash-flow overlay and keeps the failed five-year reconstruction in a compact longer-history disclosure. Each page identifies the period and test scope. Individual results must not be added together as if they were a safe simultaneous portfolio.

This is a catalogue, not a profit guarantee or financial advice.

## Live MT5 dashboard

The store connects read-only to `C:\Program Files\MetaTrader 5\terminal64.exe`. Keep that terminal open and logged into the account that should be displayed. No password is stored and the public page masks the account number.

The connector polls every five seconds and displays balance, equity, floating P/L, open positions, pending orders, EA-attributed history and per-EA results. Magic numbers are read from the active SET files. Magic `0` is labelled manual; unknown numbers are labelled external rather than assigned to the wrong EA.

Equity snapshots are stored locally in `data\live-telemetry.sqlite3`, starting when monitoring first runs. That database is ignored by Git because it contains private account telemetry. Set `EA_STORE_MT5_TERMINAL` before launch if the terminal path changes, or set `EA_STORE_DISABLE_MT5=1` to run the store without live monitoring.

## Test

```powershell
uv run pytest
```
