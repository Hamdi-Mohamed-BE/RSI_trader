# Handoff to Codex — Claude session work, 2026-09-29 → 2026-09-30

This session's work, what it produced, where it stands, and what to do next. Everything below was verified at
the time of writing. Read `CLAUDE.md` first (project rules). The dated entries there for 2026-09-29/30 summarise the
same items. Treat this file as a snapshot: re-check files and hashes before relying on numbers.

**Nothing in this session was pushed, published or deployed to the VPS, and no live MT5 chart, SET or AutoTrading setting was changed.**

**Git warning:** another session committed to the repo root on 2026-09-30 (for example
`c52b49868 "Publish current applications, EA deployment and documentation (batch 1 of 9)"` and "Archive … batch 1–9"). Those commits
include some of the files listed here. Check `git log` and `git status` before committing or pushing anything.

---

## 1. Current live state (important)

| Thing | State |
|---|---|
| Public site `https://calyx.duckdns.org` | Runs on the **VPS 51.91.121.15**. Healthy, still the **old 34-EA version**. Nothing of this session is deployed there. |
| Local site `http://127.0.0.1:8080` (this PC only) | Running **detached** (cmd → uv → uvicorn), **store ENABLED** (`CALYX_STORE_ENABLED=1`, `CALYX_COOKIE_SECURE=0`). Log: `AAA EAs\EA store\ea-store-local-8080.log`. It is NOT managed by a Claude preview. Stop it by the PID listening on 8080. |
| Store configuration | `data/store.sqlite3` exists. **0 admin users, 0 settings (no deposit addresses), 0 orders.** The owner must run `tools/create_admin.py` themself (it prompts for the password; never create real passwords for them). |
| Isolated MT5 tester `_Backtests\MT5-DMC-20260811` | **Auto-updated its MT5 build on 2026-09-30** during a run ("tester forced to close", then it restarted itself with `/skipupdate`). All final 3 Way Gold evidence and parity was re-run on the new build. Research runs from earlier in the day ran on the old build. |
| Normal live MT5 (`C:\Program Files\MetaTrader 5`) | Untouched. |

---

## 2. Work items, in order

### 2.1 Site-wide Sharpe metric (done, local only)
- `app/risk_metrics.py`: daily closed-trade returns, every calendar day counted, ×√365, no risk-free rate. Used on cards, detail pages, catalogue sort, portfolio and the prop simulator. The MT5 report Sharpe appears only as a labelled note.

### 2.2 Prop Challenge Simulator (done, local only)
- Route `/prop-simulator`. Code in `app/prop_sim/`; rules in `data/prop-rules/` (14 programmes, 8 firms); logos in `static/prop-firms/`; suggestions come from `tools/precompute_prop_suggestions.py`.
- Default preset `ftmo13-controls`: fixed $50 per trade, −2% daily equity stop, +4% profit close. These controls were tested but **not installed**.
- Plan / status: `AAA EAs\EA store\PROP_CHALLENGE_SIMULATOR_PLAN.md` §15.
- The FTMO preset now pulls **14** EAs from the FTMO manifest (3 Way Gold was added, see 2.6).
- Fixed: a zero-risk bug in `static/prop-simulator.js`, where the row risk was lost when the table was re-rendered.

### 2.3 Rolling-Sharpe and win/loss streak charts (done, local only)
- Cards use `app/risk_visuals.py`, which draws inline SVG sparklines and streak bars. Detail pages use `static/ea-metrics.js`, backed by the API route `/api/evidence/{slug}/risk-series`.
- Chart colours `#0ea371` / `#f0443c` were validated for colour-blind readability on `#0b1715`. Tests: `tests/test_risk_visuals.py`.

### 2.4 QuantLab-style gold trio — RAW (done, research)
- Folder: `AAA EAs\BM Trading Robust Sets 2026-08-04\QuantLab Gold Trio Raw 2026-09-30\`, with `REPORT.md` and `RULES.md`.
- Rules were reconstructed from QuantLab's public report image plus gold-ETF turn-of-month research. The video version's exact rules are unpublished.
- Modules: A momentum H4; B Donchian + volatility M30 (tested all year and Q4-only); C turn of month; D EMA10 (website reference).
- Raw 3y gate: **B passed; A and C failed.**

### 2.5 Full optimisation pipeline (done, research)
- Folder: `…\QuantLab Gold Trio Pipeline 2026-09-30\`. Start with `REPORT.md`; `PROTOCOL.md` was frozen before the search.
- 1,770 native passes. Exact raw parity was checked first.
- Split: development 2021-09→2024-03 (Model 1), validation 2024-03→2025-09, recent year, untouched older holdout 2019-09→2021-09 (Model 4).
- Results:
  - **BEST trio**: 5y +114.4%, PF 1.44, equity DD 7.9%.
  - **PROP trio**: 5y +96.1%, PF 1.30, DD 11.5%.
  - **Both lost on the untouched 2019–2021 holdout** (−20.3% / −24.2%), and the deflated Sharpe was 63% / 38% (pipeline requires ≥95%). Verdict: **WATCH_ONLY**.
  - Only C-prop qualified, and it is thin (~1 trade/month).
- Extra diagnostic `ftmo_market_variant.py` → `FTMO MARKET VARIANT.json`: market entries instead of limit entries. It was defined post hoc and counted in `TRIAL ACCOUNTING.json`.

### 2.6 "3 Way Gold" added to the system (done; user-approved despite research-only evidence)
Deployment record: `…\3 Way Gold Deployment 2026-09-30\README.md`, with `PARITY.json`, `deploy.py` and `make_ftmo_entry.py`.
- **Production EA:** `…\3 Way Gold EA\3 Way Gold EA.mq5/.ex5`. EX5 SHA-256 `63d2dd2744a9e91713ad17273d638ab3aa1c150e24f2b21e99ab176e4527c66d`.
  - The BEST settings are locked inside the EA.
  - Magic numbers 930930100/101/102, one per module.
  - Standard installer inputs: `InpRiskPercent` / `InpRiskMode` / `InpFixedRiskMoney` / `InpAdaptivePortfolioControls` (shared governor). Risk applies **per module**.
  - Sessions run on a UTC clock (automatic server offset when live). Trail updates rejected by a closed market are retried. Requires a hedging account.
  - `InpMarketEntries` (default false) is for the FTMO build.
  - Parity: exact for both modes (439/439 positions, +$11,435.14; market 562/562, +$10,870.84).
- **Normal BATs:** a new item in `_Auto Deploy\Install-BMTradingPortfolio.ps1`, plus SET `Selected Portfolio Settings 2026-09-01\25 3 Way Gold - BEST OPTIMISED - 1PCT PER MODULE.set`.
  - All eight normal BATs go through `Start-Dynamic-Portfolio.ps1`, so they all pick it up. `AVA EAS.bat` was intentionally excluded (user decision).
  - `-ValidateOnly` passes for every mode.
- **FTMO:** the guard admits market entries only, so the user chose the market-entry variant.
  - `FTMO Thirteen EA Deployment 2026-09-27\build_package.py` appends entry 14 from `3 Way Gold Deployment…\FTMO_ENTRY.json`. Manifest version `FTMO14-20260930-3WAYGOLD-MARKET`.
  - The guard and the original 13 entries/files are byte-identical; 4 files were added.
  - `Install-FTMO13.ps1` now expects 14 entries. The script name and the BAT file name (`FTMO 10K SWING - 13 EAS - NEWS OFF.bat`) were **kept** for compatibility; the title says 14. Renaming was offered and not yet done.
- **Website:** product `3-way-gold` in `app/catalog.py`, labelled status "Watch only - failed older holdout".
  - Evidence cache 6m/1y/3y/5y ends 2026-09-05. 5y: +120.06%, PF 1.46, DD 7.92%. Trade counts and win rate are MT5-deal based, so partial closes count separately.
  - The portfolio caches were rebuilt with `--portfolio-only` so they use the common window. Rebuilding them with an end date instead breaks `test_gold_value_area`.
- Test count expectations updated: 34→35 installer items, 47→49 normal+FTMO, 13→14 FTMO entries, portfolio 34/33→35/34.

### 2.7 Crypto store, licenses, admin, install BAT, video (built by a sub-agent; local only)
Code lives in `AAA EAs\EA store\app\store\`. The agent's log is `AAA EAs\EA store\STORE_CHECKOUT_PROGRESS.md`; owner setup steps are at the top of the EA store `README.md`.

**Pricing and payments**
- Every bot is 40% cheaper. "Buy 3, get 1 free": the cheapest of every 4 in the cart is free. The full package is $1,194.
- Payment is USDT, TRC20 or BEP20, sent to the owner's Binance deposit addresses; these are set in admin, never in code.
- Each order has a unique amount (+0.01–0.99 USDT) and expires after 60 min, with a 30-min late window.
- The watcher reads TronGrid and BSC `eth_getLogs`. Confirmations: 20 for TRC20, 15 for BEP20. Admins can mark an order paid manually, with a required note.

**Licenses**
- One key per bot, 1 live + 1 demo account, bound to the product slug and the product's magic number.
- `POST /api/license/check` returns a signed answer. The EA checks at start and every 24h, with 72h offline grace; when denied it calls `ExpertRemove()`. The Strategy Tester bypasses the check.
- The EA-side include is `app/store/mql/CalyxLicense.mqh`. Store builds are wrappers around the unmodified strategy code, built by `tools/build_store_eas.py` into the gitignored `data/store-builds/`: 26 binaries covering 35 products, 0 errors / 0 warnings.

**Admin and downloads**
- `/admin`: scrypt passwords, optional TOTP, CSRF, lockout after 5 failures.
- Downloads are signed links valid 2h. Each ZIP holds the EX5, a SET with the key pre-filled, `INSTALL <bot>.bat` + `Install-CalyxBot.ps1` (PowerShell only), README and LICENSE.
- The installer refuses Ava/tester folders, never enables Algo Trading, and edits the WebRequest allow-list only while MT5 is closed.

**Video**
- `static/video/calyx-how-it-works.mp4`: 3:24, 1920×1080, with VTT captions and a poster. It is on `/how-it-works`.
- Voice: Edge-TTS `en-US-AndrewNeural`. Assembled with ffmpeg; tools in `tools/video/` (copied from the clipper project, which was not modified). The MT5 scenes are mock-ups with a fake account.

**Launch switch (added by Claude after the agent finished)**
- `CALYX_STORE_ENABLED` (in `app/store/config.py`), **default OFF**. Off = the pre-store site: list prices, WhatsApp buy buttons, and no store routes, DB or watcher.
- Template hunks are wrapped `{% if store_enabled %}…{% else %}<pre-store original>{% endif %}`. The pre-store pricing page is `templates/pricing.html`; the store version is `templates/pricing_store.html`. Route fallbacks are in `app/main.py` (`_legacy_pricing_context`).
- `tests/conftest.py` sets the switch ON for the suite. `tests/test_store_disabled.py` checks the OFF mode in a subprocess.

**Tests (whole EA store suite):** 241 passed, 1 skipped (the qrcode package is absent), **7 failed: the long-standing `tests/test_store.py` failures** (stale catalogue text/count expectations from before this session). Don't mask them by editing expectations without understanding them.

---

## 3. What is left (prioritised)

### A. Make payments work end to end (owner + Codex)
1. The owner creates an admin: `cd "AAA EAs\EA store" && uv run python tools/create_admin.py`. Then sign in at `/admin/login`, enable 2FA, and paste the Binance **USDT** TRC20/BEP20 deposit addresses in Settings.
2. **Real payment test.** Place a small order and send the exact amount on the matching network. Confirm the watcher auto-confirms it; check the log and admin → Chain transfers.
   - Not yet verified: whether Binance deposit transfers appear as plain on-chain transfers to the watcher.
   - Exchange withdrawals that net the fee out of the amount will not auto-match; they appear for manual review.
3. **Deploy the store to the VPS** (the public site): set `CALYX_STORE_ENABLED=1`, a real `CALYX_STORE_SECRET` and `CALYX_LICENSE_SECRET`, and working HTTPS.
   - The license secret must be **identical** on the build machine and the VPS: copy `data/store-secrets.json` or set the environment variable. Otherwise locally built EAs are refused.
   - Rebuild with `uv run python tools/build_store_eas.py` wherever builds are made.
   - The activation URL `https://calyx.duckdns.org/api/license/check` is compiled into the builds.
4. **Live license test:** install a purchased store build on a **demo** chart (Algo Trading on, WebRequest allowed) and confirm it activates and trades. **Never done**, because the sub-agent was not allowed to start a terminal.
5. Nice to have: email delivery of the order link (buyers currently only get a secret link on screen); refunds/support flow.

### B. Known store limitations to consider
- The offline grace period can be stretched by changing the PC clock.
- Shared-EX5 products are distinguished only by magic number. A cheap ORB license could run a pricier variant's parameters.
- `/api/eas` still reports catalogue list prices.
- Gold News V9 is now for sale but depends on the local Gold News API, and its evidence is pending. Consider excluding it.
- The 32 MB video is not gitignored.

### C. 3 Way Gold follow-ups
- Offered, not yet decided: rename the FTMO BAT to "14 EAS".
- The evidence is research-grade (failed the older holdout). Keep the "Watch only" label; demo-forward before live money.
- The guarded FTMO build cannot be backtested (the guard blocks the tester by design). The guard's $150 per-symbol XAU cap will refuse some entries.

### D. Older open items (not started)
- ORB V2 proposals from the ORB trade-count audit.
- The next steps list for the crypto-lab project (`AAA crypto arbitage\crypto-lab`).
- The 7 pre-existing `test_store.py` failures.
- Publishing the website to the VPS: the owner's decision.

---

## 4. Rules that must continue to hold
- Isolated tester only (`_Backtests\MT5-DMC-20260811`), one tester process at a time. Never use the live terminal or Ava for tests.
- No trades, no attaching EAs to live charts, no replacing live SETs, no AutoTrading changes, no MT5 restarts without a fresh explicit task.
- No push, publish or deploy unless the user asks. Git push does not update MT5 or the VPS.
- Never enter or store the owner's real passwords, API keys or wallet secrets. Deposit addresses are entered by the owner in admin.
- Don't expose secrets: the local tester agent command line contains a password, and `data/store-secrets.json` holds live store secrets.
- Report floating equity DD separately from balance DD, and never fabricate results.
