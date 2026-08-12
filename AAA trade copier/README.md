# AAA Trade Copier

A safe-by-default Windows control plane and copier-core MVP for copying MT5 trades from one selected master account to multiple follower accounts.

## Current implementation

- FastAPI dashboard with signed-session authentication and CSRF protection.
- SQLite WAL persistence for accounts, risk profiles, symbol mappings, source events, follower jobs, acknowledgements, and audit events.
- One active master with explicit confirmation and automatic pause after a master change.
- Account-specific stop-loss risk sizing that floors to broker volume steps and rejects unsafe minimum lots.
- Cross-broker symbol mappings with relative SL/TP preservation.
- Durable idempotency keys and explicit follower decisions; duplicate source events do not create duplicate jobs.
- Continuous master-terminal reconciliation captures positions and pending orders opened from MT5 desktop, mobile, web, scripts, and EAsâ€”not only orders submitted by the dashboard.
- Persistent master-to-follower ticket links drive pending-order changes/cancellations, SL/TP changes, proportional partial closes, and full closes against the exact copied follower trade.
- Fresh trading workspace with no sample accounts, risk profiles, mappings, or trades.
- Automatic discovery of already-running, logged-in MT5 terminals on Windows.
- Windows DPAPI credential vault; SQLite stores only opaque credential references.
- Persistent Windows named-pipe listeners, newline-framed versioned messages, verified account/job acknowledgements, and timeouts.
- MQL5 Publisher and Executor integration agents with disabled-by-default inputs.
- Portable MT5 launcher that validates `terminal.exe`/`terminal64.exe` and never exposes a password in process arguments.
- Modern Tailwind/HTMX/Alpine interface.
- Normal Windows launcher, Makefile, and Docker web control plane.

Continuous execution supports verified **demo and live hedging accounts**. Demo copying requires the dashboard confirmation `ENABLE`. Live copying requires both environment safety gates plus the stronger dashboard confirmation `ENABLE LIVE`. The optional MQL named-pipe agents remain a separate integration path; the default Windows runtime performs continuous reconciliation directly through each isolated MT5 terminal.

## Quick start

```bat
run.bat
```

`run.bat` performs first-time setup when necessary, ensures the default administrator exists, starts the Copier Core and dashboard, and opens `http://127.0.0.1:8100` automatically. It never resets the password of an existing administrator.

Before starting the services, `run.bat` also bootstraps MT5 integration on Windows. It detects the logged-in active master, copies the versioned agents into that terminal's actual `TERMINAL_DATA_PATH`, writes a secret-free Publisher preset containing the account UUID and local pipe name, and uses MT5's supported `/config:` startup mechanism to attach `AAA_Master_Publisher` to an M1 control chart. The exact master terminal is restarted only when the attachment is missing or stale. Follower agent files are installed for compatibility, but no follower chart EA is required by the default isolated-Python executor.

`run.bat` binds the dashboard to `0.0.0.0`, so on a VPS it is also reachable at `http://YOUR-VPS-IP:8100`. Windows Firewall and the VPS provider firewall must allow inbound TCP port 8100. Change the default password and place the dashboard behind an HTTPS reverse proxy before treating it as an internet-facing service.

The setup command creates an ignored `.env` if needed, installs Python and frontend dependencies, builds CSS, and initializes an empty SQLite trading database. This workspace contains only the requested local dashboard administrator:

```text
Email:    admin@aaa.local
Password: AAA-Copier-Local-2026!
```

Change that password before exposing the dashboard beyond localhost. To create a different administrator interactively:

```bat
dev.bat create-admin
```

## Safety model

Two environment gates must both be changed before any live execution can be considered:

```dotenv
SAFE_MODE=false
LIVE_EXECUTION_ENABLED=true
```

After changing these flags, restart with `run.bat`, verify every account, symbol route, stop-loss, and 1% risk profile, then type `ENABLE LIVE` on the dashboard. Existing unlinked master positions are baselined during recovery and are not opened retroactively on followers; only new positions created after live activation are copied. Linked positions continue to receive modifications and closes.

Demo copying does not require weakening these environment gates. Keep their defaults, verify that every account is shown as `demo` and `hedging`, then type `ENABLE` on the dashboard. Pausing blocks new exposure while linked modifications, cancellations, and closes continue to be obeyed.

Automatic agent setup is enabled by default:

```dotenv
AUTO_INSTALL_MT5_AGENTS=true
```

The active master must already be logged into MT5 when `run.bat` starts. The generated startup configuration does not contain the MT5 password; MT5 reuses its own saved account authorization. If no logged-in terminal is detected, the bootstrap reports that it was skipped and the Python reconciliation path remains available.

## Adding and managing MT5 accounts

Open **Accounts** from the left navigation. The page provides two onboarding paths:

1. Start MT5 and log into the intended main account, then press **Detect connected MT5**. When the trading database has no master, the first running connected terminal becomes the master automatically. Copying remains paused until reviewed.
2. Use **Add another account** for each follower. Enter its login, broker server, and password. The app encrypts the password with Windows DPAPI, builds a unique portable terminal under `storage/mt5_instances/<account-id>`, installs the copier agents, launches that instance, and logs in through the native MT5 API.

Every account card includes **Edit and manage** controls for its name, terminal path, role, enabled state, trade mode, position mode, risk profile, and deletion. Its **Build and connect MT5** action can create or repair the dedicated instance and safely replace its automatic-login password. Additional detected accounts are imported as paused followers. Detection never requests or stores an MT5 password; it reads the active saved terminal session.

Passwords are never written to SQLite, audit details, generated instance files, or process command lines. They remain encrypted in the local DPAPI vault and are decrypted only in memory for the MT5 login call. Set `MT5_TEMPLATE_PATH` in `.env` when the correct broker terminal should be used as the default template; otherwise the app selects an installed MT5 automatically.

No sample accounts, mappings, trades, or performance records are created. One system-managed **Automatic 1% per trade** risk profile is created and assigned only to followers that do not already have a custom profile. It risks at most 1% of each follower's own equity using the trade stop distance; daily loss and daily profit caps are disabled. Early development demo records are removed automatically by an exact one-time compatibility cleanup, without touching user-created accounts.

## Cross-account copy test

Open **Copy test** from the navigation or dashboard. Enter one master trade and type `TEST`. Tests support Buy or Sell with Market, Limit, and Stop entries, plus stop-loss and optional take-profit prices. The app reads the active main MT5 account's live Ask for Buy validation and live Bid for Sell validation; users do not enter a reference market price. The runner checks the active master and every configured follower and records:

- active master state, terminal health, broker symbol, and live quote;
- follower state and terminal health;
- assigned risk profile;
- master-to-follower symbol mapping;
- automatic broker-symbol discovery by exact name, prefix/suffix, common alias, and base/profit currencies;
- follower contract specification and volume step;
- spread limit;
- calculated follower volume and cash risk;
- mapped entry, stop-loss, and take-profit prices;
- broker order, deal, and return code when demo execution is selected;
- the exact error for every failed follower.

Before running the checks, the diagnostic connects to the active main MT5 and managed follower instances, then refreshes their requested broker symbol specifications. If a broker renames a symbol, such as `XAUUSDm`, the resolved `XAUUSD → XAUUSDm` route is saved automatically and reused by future tests and copier events. The first incoming trade for a new symbol runs the same discovery before routing.

When continuous copying is enabled, **Place on master and all ready followers** sends only the master request; the background copier routes the followers and records their durable jobs. This prevents the same test from being copied twice. When continuous copying is paused, Copy Test retains its direct diagnostic execution behavior. Market positions and pending orders remain active until they are closed or cancelled in the master MT5, and followers then obey that lifecycle automatically.

## MT5 demo integration

The integration sources live in [mt5/README.md](mt5/README.md). Every follower account page shows the exact pipe name and account UUID required by its Executor EA. The master uses `aaa_trade_copier_master` and the active master account UUID.

Compile both agents with the locally installed MetaEditor:

```bat
dev.bat compile-mt5
```

The default Windows process layout is:

```text
Master MT5 (all open orders and positions) -> Copier Core reconciliation
Copier Core -> persistent ticket mapping -> each isolated follower MT5
FastAPI dashboard <-> shared SQLite event journal
```

`dev.bat start` opens the Windows Copier Core and web dashboard. By default the core checks the master every 350 ms, detects opens and lifecycle changes, deduplicates them, applies symbol/risk routing, executes the correct follower action, and records the broker acknowledgement. `CONTINUOUS_COPY_POLL_MS` can be tuned in `.env`; keep it at or above 100 ms.

The watcher sees the trading account itself, so a trade may originate from MT5 desktop, the broker's mobile/web interface, a script, or another EA. A stop loss is required before the default 1% risk profile can open a follower trade. If the master entry initially has no stop, the rejection is recorded and the copier retries after a valid stop is added.

## Docker scope

```bat
dev.bat docker-up
```

Docker runs the dashboard, empty SQLite journal, and reports on `http://127.0.0.1:8100`. Login defaults to `admin@aaa.local` / `AAA-Copier-Docker-2026!` unless overridden through environment variables. MT5 discovery is Windows-host-only and is disabled in the Linux container.

MT5 and local Windows named pipes cannot run inside the Linux container. Run `dev.bat core` on the Windows host for terminal integration; Docker is for the control-plane demo and later web deployment only.

## Verification

```bat
dev.bat check
```

This runs formatting/lint rules, strict type checks, protocol/risk/security tests, duplicate-event tests, and full dashboard tests with warnings promoted to errors.

## Deployment note: CSS and static assets

The compiled stylesheet at `src/trade_copier/static/css/app.css` is committed to the repository so a normal VPS pull does not require Node.js. After pulling an update, restart the application with `run.bat` and hard-refresh the browser with `Ctrl+F5`.

If the stylesheet is missing, `run.bat` attempts to rebuild it automatically. You can also rebuild it manually with:

```bat
dev.bat css
```
