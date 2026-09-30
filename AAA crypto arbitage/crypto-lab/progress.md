# Progress log

A running log of each development step: what was built, how it was verified, and what is still open.
Newest entries go at the bottom of each day. Dates are UTC.

---

## 2026-09-29

### Step 0: Scope and decisions
- Scope: one uv project for all planned models (A/B CEX arbitrage, D Polymarket, E Solana). **Model D is first**
  (Polymarket scanner + wallet tracker, paper mode), per the user's choice.
- Stack (from the re-planned `../CRYPTO_ARBITRAGE_MASTER_PLAN.md` §16–17): FastAPI + Jinja2, SQLite (SQLAlchemy 2
  async + Alembic), Tailwind in the Calyx website theme, uv.
- Guidance applied from the requested `jeffallan/claude-skills` skills (read from GitHub, not installed): fastapi-expert,
  python-pro, secure-code-guardian, architecture-designer (ADRs), test-master.
- ADRs written: [0001 stack](docs/adr/0001-stack.md), [0002 layering](docs/adr/0002-hexagonal-layering.md),
  [0003 vault](docs/adr/0003-credential-vault.md), [0004 paper honesty](docs/adr/0004-latency-checked-paper-fills.md).

### Step 1: Project skeleton (uv)
- `uv init --package crypto-lab` (Python 3.12), runtime and dev dependencies added with `uv add` and locked in `uv.lock`.
- Tooling configured in `pyproject.toml`: pytest (asyncio auto), coverage (greenlet-aware), ruff (broad rule set),
  mypy `--strict`.

### Step 2: Platform core
- `domain/`: bot modes and the LIVE guard chain, credential provider registry (13 providers), errors, standard
  performance table.
- `security/`: Argon2id passwords, AES-256-GCM vault cipher with record-bound associated data, master-key provider
  chain (env → OS keyring → dev file), TOTP, tokens, sliding-window rate limiter.
- `infrastructure/db/`: async engine (WAL, foreign keys, busy timeout), UTC-aware datetime type, exact `DecimalText`
  type (SQLite has no decimal), models, repositories, Unit of Work, Alembic env (programmatic + CLI).
- `services/`: auth (lockout, server-side sessions, 2FA), vault (write-only views), bots (policy-checked mode
  changes, kill switch, heartbeat), audit.

### Step 3: Dashboard (admin)
- App factory with lifespan (migrate + seed bots), strict security headers/CSP, CSRF on every form, login-required
  redirects, typed `Annotated` dependencies.
- Pages: login, overview, API keys (add/rotate/enable/disable/delete), bots (modes + kill switch), audit log, 2FA
  enrolment (QR via segno).
- Theme: Calyx tokens and components ported from `AAA EAs/EA store/static/site.css` into
  `web/static/src/input.css` (Tailwind v4). Built with the standalone CLI (v4.3.3) to `web/static/css/app.css`.

### Step 4: Model D domain and adapters
- Checked the real public API shapes live (read-only): Gamma `/events` (markets embed `clobTokenIds` / `outcomes`
  as JSON strings, and a per-market `feeSchedule {rate, exponent, takerOnly}`), CLOB `POST /books` (bids ascending,
  asks descending), Data API `/v1/leaderboard` (50 per page), `/trades`, `/closed-positions`.
- Domain: `OrderBook` (normalised sorting, depth walking), `FeeSchedule` (per-level exact fee, 5-dp rounding),
  three arbitrage detectors, wallet stats (Wilson lower bound, style labels), ports.
- Infrastructure: `JsonHttpClient` (token bucket, retries with jitter on 429/5xx), Gamma/CLOB/Data adapters,
  mappers as an anti-corruption layer.

### Step 5: Model D services, workers and pages
- `ScannerService`: grouped fetch → freshness → detect → upsert the feed (dedup by fingerprint) → PAPER
  re-pricing after latency (fill or *missed*) → scan-run health row.
- `WalletTrackerService`: leaderboard + watchlist refresh, trade dedup, stats JSON; watchlist toggle.
- `BotWorker` loop (Template Method) reads mode and kill from SQLite every cycle; workers `poly-scanner` and
  `poly-wallets`; CLI `crypto-lab worker <slug> [--once --mode]`.
- Pages: scanner feed + scan health, paper ledger (standard table + SVG balance chart), wallets, wallet detail.

### Step 6: Verification
- **Tests:** 110 passed (unit + integration, no network) covering crypto, auth, CSRF, lockout, open-redirect, vault
  secrecy (secret never in HTML, audit or ciphertext), LIVE guard chain, detectors, fees, mappers, scanner
  (dedup/close/paper fill/missed/stale/capital), adapters (mock transport), wallet tracker, worker loop, 2FA.
- **Coverage:** 91% overall (the untested lines are mainly the live network wiring in `workers/polymarket.py`).
- **Lint/types:** `ruff check` clean, `ruff format` applied, `mypy --strict` clean (70 files).
- **Live smoke runs (read-only, public APIs):**
  - Scanner, SHADOW, first run: 150 events / 2,486 markets / 4,972 books, 0 opportunities, 17.6 s. **Bug found:**
    3,886 books were flagged stale.
    - Fix 1: fetch and check per event group. Still 2,908 stale, which showed that the CLOB `timestamp` is the
      book's last *change*, not the serve time.
    - Fix 2: added `received_ms` (local receive time) and based freshness on it. Result: **0 stale**.
  - Scanner, PAPER: 150 events / 2,475 markets / 4,950 books, **0 stale, 0 opportunities**, 17.2 s. Near-miss
    metrics were added in migration `29ea239512cf`. Lowest YES+NO ask sum 1.001; highest bid sum 0.999. So there was
    no gross complement arbitrage even before fees at that moment. This is expected for liquid markets.
  - Wallet tracker: 50 leaderboard wallets refreshed, 41,389 trades stored, 0 errors.
- **Browser check** (local dev admin; credentials in the git-ignored `data/dev-admin.txt`): overview, scanner,
  wallets, paper and 2FA pages render in the Calyx theme with live data; no console errors under the strict CSP.

### Open items / next steps
1. **Paper copy engine** (Model D, next): mirror watch-listed wallets from the Data API trade stream with a delay,
   a max price deviation, liquidity and size caps; walk-forward wallet selection (rank on days t−60…t−1, copy on
   t…t+30).
2. Run `poly-scanner` in PAPER continuously for 2–4 weeks and review the missed/filled ratio and near-miss
   distribution before judging D1/D2/D3.
3. Settlement job for open neg-risk basket paper trades (poll resolution).
4. Investigate the closed-positions sample size (only 7–10 rows for some top wallets); consider deriving P/L from
   trades plus resolutions instead.
5. D4 Polymarket↔Kalshi (Kalshi demo environment for plumbing).
6. Choose an open-source license (user decision) before publishing.
7. Later modules: A/B CEX arbitrage (ccxt adapters), E Solana rotation (Jupiter/Helius adapters).
# 2026-09-29 — shared 100 USDC local paper lab

- User requested all five bots running with the dashboard, login skipped for now, **100 USDC shared total**,
  and **10 USDC maximum commitment per trade** (including modeled entry costs; unleveraged exposure, not stop-risk sizing).
- Backed up the original SQLite database with its live WAL through SQLite backup to
  `data/crypto_lab.before-paper-20260929-152347.sqlite`. Preserved existing users, encrypted vault, wallet data,
  scanner history and saved bot modes. Migration `7bc431d7a001` adds account, positions, state, activity and leases.
- Added managed startup/shutdown, per-process worker ownership, 2-second control/heartbeat checks, cancellation
  on mode changes, persistence of errors until a successful cycle, and restart of enabled workers.
- Added CEX BTC/USDC inventory rotation, forward-only Polymarket wallet copy and Jupiter-quoted Solana momentum
  paper workers. Models and costs are explicit in README and the Paper page; these are experimental, not validated.
- Existing Polymarket scanner now obeys shared capital and entry caps. Added explicit-resolution settlement for
  held baskets. Atomic SQLite spending, unique signal keys and position caps prevent overspending/repeated fills.
- Loopback-only login bypass leaves normal authentication available when disabled; Host/client/Origin boundaries,
  CSRF and live-trading lock remain active. Vault/account-security pages are blocked during bypass.
- Added **/paper** (combined holdings/results) and **/activity** (cycles/fills/skips/errors), 10-second refresh,
  current worker health and shared account totals. Existing /polymarket/paper opens the combined page.
- Verification: **128 tests passed**, Ruff clean, strict mypy clean (71 source files), Tailwind rebuilt.
  Added real worker-flow simulations, budget concurrency, fee caps, duplicate/close accounting, stale marks,
  worker leases, resolution, local-only access, CSRF and live lock tests.
- Public-data smoke: all five workers completed cycles without errors. Scanner covered ~5,000 order books with
  zero qualifying arbitrage; tracker refreshed 50 wallets and recorded 3,308 new source trades. CEX seeded one
  8.39491495 USDC paper BTC inventory lot; copy subsequently opened a 1.73309 USDC paper position. No real orders.
  These are initial test observations, not performance claims. Counts/balances will change as the workers run.
- Browser verification confirmed no login, live account totals and running status for all five; fixed clipped
  navigation in the narrow in-app browser. Process remains running at 127.0.0.1:8090. No Windows boot service added.
- Remaining research: actual strategy validation/walk-forward selection, CEX lead-lag and real venue cash
  allocation/transfer costs, execution failure/partial-fill realism, Polymarket/Kalshi comparison. No live readiness.
