# Calyx — EA Store

## Raw Gold Value Area and current website publication — 2026-09-19

The maintained normal MT5 roster now contains **34 EAs**, including raw Gold Overnight Value Area. The optimized Gold candidate is not deployed. Its four independent native windows end September 18; the one-year result is +22.26%, 200 trades, 74% wins. Production parity matched all 200 original one-year trades. Gold News V9 remains evidence-pending, so 33 EAs contribute tested portfolio ledgers.

News Pulse XAU continues to use the approved v2.16 event-specific settings, both pending directions, 0.75% target risk per side and adaptive exemption. Its website-native windows end September 5 exclusive: 6m +167.04% (22 trades), 1y +300.00% (40), 3y +1,029.12% (121), 5y +2,394.29% (194). Those are hindsight-fitted backtests, not forecasts. The September-19 research comparison has different dates and must not replace these website-window figures.

The portfolio now uses the **intersection** of component histories, ending August 30, rather than extending missing data to the newest EA's date. Exact start/end dates and limitations are displayed. The manifest, per-EA ledgers and portfolio totals include raw Gold. The regular production risks have **not** been replaced by the separate $71.43 FTMO research proposal.

Audited artifact paths in the root `.gitattributes` preserve exact bytes across Windows checkouts; line-ending conversion must not invalidate native source/report fingerprints. Restart the website after pulling changed catalogue/installer code. Updating or pushing files does not deploy new settings to attached MT5 charts.

## XAG / BTC / EURUSD event-specific promotion — 2026-09-19

The user explicitly selected the **full-year optimized** NFP/CPI/FOMC combinations, not the earlier-selected variants. XAG, BTC and the restored EURUSD use the dedicated v2.17 multi-asset event EA. XAU stays on its approved v2.16 source and settings. That promotion had 33 EAs; raw Gold subsequently brings the current roster to **34**, including **five adaptive-exempt news EAs** (four News Pulse charts plus Gold News V9).

All four News Pulse charts retain both pending directions and 0.75% planned equity risk per side. Four simultaneous straddles therefore plan 6% combined risk before rounding, costs and gaps; Gold News V9 adds exposure. This is not a realized loss cap or a prop-firm-safe configuration. Ordinary non-news risk controls are unchanged.

The canonical event map is `AAA Final EAs/AAA Final News Pulse Multi Asset Event EA/EVENT PARAMETERS.json`. Matching source generation, exact production/research parity checks, twelve independent website-period native runs, build/SET hashes and publication are retained in `News Pulse Multi Asset Event Parameters 2026-09-19/Deployment`. `publish_deployment.py` republishes completed reports and rebuilds current/recommended-adaptive portfolio overlays without starting MT5. Previous caches remain backed up there.

The four News Pulse website windows end on **2026-09-05 exclusive**. Original full-year optimization comparisons end on **2026-09-19** and are not interchangeable. Other products have their own documented cutoffs; the current portfolio uses their common intersection as described above. Results are hindsight-optimized, include recorded commissions/swaps, and show real/generated tick quality. Portfolio ledgers are independently sized overlays, not shared-margin or floating-equity simulations. Gold News V9 remains evidence-pending.

Updating files does not update attached MT5 charts. Reapply `RECOMMENDED ADAPTIVE.bat` (or another maintained BAT) when ready; this promotion does not itself restart or attach anything to the trading terminal.

## XAU event-specific promotion — 2026-09-19

News Pulse XAU uses a dedicated v2.16 build with separate NFP/CPI/FOMC timing, anchors, stops and exits. All maintained portfolio BATs select it; both pending sides remain enabled, 0.75% equity risk per side and adaptive exemption are unchanged. The later XAG/BTC/EURUSD promotion above does not modify XAU.

Four independent native runs replace XAU's cached results and feed the rebuilt portfolio ledgers. Website periods retain the 2026-09-05 cutoff; the September-19 research comparison uses different dates. Current source-matched reports are under `News Pulse Event Parameters Research 2026-09-19/Deployment`, and `independent_news_result` rejects old XAU evidence during future rebuilds. Card, detail and API disclosures identify hindsight optimization and real/generated tick percentages. Multi-year figures are not live execution evidence or forecasts.

To republish the retained runs without starting MT5, run `publish_deployment.py` in that research directory. The production executable was matched to the selected research run before publication; the parity and build manifests are retained there. Installing into an already running live terminal still requires rerunning a maintained BAT.

A FastAPI storefront generated from the Expert Advisors currently listed in:

`..\BM Trading Robust Sets 2026-08-04\_Auto Deploy\Install-BMTradingPortfolio.ps1`

The public catalogue is generated directly from every active entry in the recommended installer. It now contains 34 EAs; the count updates automatically when the installer changes.

The 2026-09-10 full portfolio audit keeps four evidence-selected Safe defaults (LTA Volume Profile, EMA3, XAU Weakness and XAU Squeeze Momentum Standard), promotes Sell Nasdaq 15min to its Dynamic London preset, and retains DMC Current XAU by explicit user decision. Engineered Liquidity XAU, ORB Volume Profile High Win 0.75R, XAG Session VWAP Snapback and XAU Squeeze Momentum High Win 0.75R were removed from the active catalogue and every main portfolio BAT; their research evidence remains archived.

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

Add `--safe` to generate the compatible Full Safe variants too. The Best Recommended portfolio currently defaults LTA Volume Profile, EMA3, XAU Weakness and XAU Squeeze Momentum Standard to Safe evidence, and Sell Nasdaq 15min to Dynamic London; every other active EA uses Standard. The portfolio curve selects those modes from the existing per-EA caches and chronologically overlays their separate native results. It is not a simultaneous shared-margin portfolio test, and each page states that limitation.

This is a catalogue, not a profit guarantee or financial advice.

## Live MT5 dashboard

The store connects read-only to `C:\Program Files\MetaTrader 5\terminal64.exe`. Keep that terminal open and logged into the account that should be displayed. No password is stored and the public page masks the account number.

The connector polls every five seconds and displays balance, equity, floating P/L, open positions, pending orders, EA-attributed history and per-EA results. Magic numbers are read from the active SET files. Magic `0` is labelled manual; unknown numbers are labelled external rather than assigned to the wrong EA.

Equity snapshots are stored locally in `data\live-telemetry.sqlite3`, starting when monitoring first runs. That database is ignored by Git because it contains private account telemetry. Set `EA_STORE_MT5_TERMINAL` before launch if the terminal path changes, or set `EA_STORE_DISABLE_MT5=1` to run the store without live monitoring.

## Test

```powershell
uv run pytest
```
