# Calyx — EA Store

A FastAPI storefront generated from the Expert Advisors currently listed in:

`..\BM Trading Robust Sets 2026-08-04\_Auto Deploy\Install-BMTradingPortfolio.ps1`

The public catalogue is generated directly from every active entry in the recommended installer. At the time of this audit it contains 24 EAs, and the count updates automatically when the installer changes.

## Run locally

The easiest option is to double-click `RUN EA STORE.bat`.

Or run it manually from this folder:

```powershell
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Then open <http://127.0.0.1:8080>.

## One-click Windows VPS DNS and HTTPS

After claiming a DuckDNS hostname and pointing it to the VPS IPv4 address, run
`configDns.bat` as Administrator on the Windows VPS. Its default hostname is
`calyx.duckdns.org`; a different hostname can be supplied as the
first argument.

The installer does not store a DuckDNS token. It verifies DNS, prepares the
Python environment, downloads the latest official Windows AMD64 Caddy archive
and verifies its published SHA-512 checksum, opens Windows firewall ports 80
and 443, installs automatic startup tasks, binds the EA Store privately to
`127.0.0.1:8080`, and prints the final HTTPS link. Caddy and website logs are
stored under `C:\Calyx-Caddy`.

## Pages

- `/` — store landing page
- `/eas` — searchable catalogue of all recommended EAs
- `/eas/{slug}` — logic, risk notes, historical statistics and equity graph
- `/portfolio` — available EA portfolio and the combined core audit
- `/live` — read-only active MT5 account, equity curve, positions, orders and complete reconstructed trade history
- `/pricing` — individual and bundle prices
- `/risk` — disclosure and responsible-use page
- `/api/eas` — JSON catalogue
- `/api/live/portfolio` — uncached live MT5 snapshot used by the dashboard
- `/api/portfolio/equity-series?period=3y` — cached recommended-portfolio evidence (website default)
- `/api/evidence/{slug}/series?period=3y` — cached per-EA evidence (website default)
- `/api/health` — sync status

## Catalogue and pricing

The installer PowerShell file is the source of truth for the catalogue. Restart the web server after changing the installer.

Descriptions and prices are in `app\catalog.py`. Public names remove the internal `AAA Final` prefix. Purchase buttons open WhatsApp for `+216 93 830 957` with the EA and price already included in the message. The available-EA package is USD 1,990. This version does not process payments or automatically issue licenses.

## Evidence

The website exposes four fixed periods: 6 months, 1 year, 3 years and 5 years. The 3-year period is the website default. Each period is generated as an independent native MT5 Every Tick run using the exact active compiled EA and recommended SET. Statistics, sampled balance curves and complete parsed trade ledgers are stored under `data\evidence-cache\v1`; public endpoints read those files instead of starting MT5 on demand.

Portfolio caches also include drawdown, monthly P/L, asset contribution, trade allocation, directional and per-EA breakdowns. Cached trades include reconstructed favorable price movement using 1 pip = 10 broker points (while index and crypto moves remain displayed as points), plus an estimated realized R based on the configured equity-risk budget at entry. The R value is explicitly an estimate because closed MT5 deals do not preserve every original stop after break-even or trailing-stop changes.

Rebuild the resumable cache after changing an EA or SET:

```powershell
uv run python tools\precompute_evidence_cache.py --period all
```

Add `--safe` to generate the compatible Full Safe variants too. The portfolio curve is a chronological realized-cash-flow overlay of the separate per-EA native tests. It is not a simultaneous shared-margin portfolio test, and each page states that limitation.

This is a catalogue, not a profit guarantee or financial advice.

## Live MT5 dashboard

The store connects read-only to `C:\Program Files\MetaTrader 5\terminal64.exe`. Keep that terminal open and logged into the account that should be displayed. No password is stored and the public page masks the account number.

The connector polls every five seconds and displays balance, equity, floating P/L, open positions, pending orders, EA-attributed history and per-EA results. Magic numbers are read from the active SET files. Magic `0` is labelled manual; unknown numbers are labelled external rather than assigned to the wrong EA.

Equity snapshots are stored locally in `data\live-telemetry.sqlite3`, starting when monitoring first runs. That database is ignored by Git because it contains private account telemetry. Set `EA_STORE_MT5_TERMINAL` before launch if the terminal path changes, or set `EA_STORE_DISABLE_MT5=1` to run the store without live monitoring.

## Test

```powershell
uv run pytest
```
