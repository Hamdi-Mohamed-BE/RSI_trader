# AAA Trade Copier

A safe-by-default Windows control plane and copier-core MVP for copying MT5 trades from one selected master account to multiple follower accounts.

## Current implementation

- FastAPI dashboard with signed-session authentication and CSRF protection.
- SQLite WAL persistence for accounts, risk profiles, symbol mappings, source events, follower jobs, acknowledgements, and audit events.
- One active master with explicit confirmation and automatic pause after a master change.
- Account-specific stop-loss risk sizing that floors to broker volume steps and rejects unsafe minimum lots.
- Cross-broker symbol mappings with relative SL/TP preservation.
- Durable idempotency keys and explicit follower decisions; duplicate source events do not create duplicate jobs.
- Safe demo simulator with live dashboard updates over WebSockets.
- Windows DPAPI credential vault; SQLite stores only opaque credential references.
- Persistent Windows named-pipe listeners, newline-framed versioned messages, verified account/job acknowledgements, and timeouts.
- MQL5 Publisher and Executor integration agents with disabled-by-default inputs.
- Portable MT5 launcher that validates `terminal.exe`/`terminal64.exe` and never exposes a password in process arguments.
- Modern Tailwind/HTMX/Alpine interface.
- Normal Windows launcher, Makefile, and Docker demo control plane.

Live order placement is intentionally disabled. The Publisher can feed normalized master events into the core, but the first Executor agent rejects broker placement until demo-terminal qualification, restart/reconciliation testing, and the acceptance criteria in [PLAN.md](PLAN.md) pass.

## Quick start

```bat
run.bat
```

`run.bat` performs first-time setup when necessary, ensures the default administrator exists, starts the Copier Core and dashboard, and opens `http://127.0.0.1:8100` automatically. It never resets the password of an existing administrator.

`run.bat` binds the dashboard to `0.0.0.0`, so on a VPS it is also reachable at `http://YOUR-VPS-IP:8100`. Windows Firewall and the VPS provider firewall must allow inbound TCP port 8100. Change the default password and place the dashboard behind an HTTPS reverse proxy before treating it as an internet-facing service.

The setup command creates an ignored `.env` if needed, installs Python and frontend dependencies, builds CSS, initializes SQLite, and creates safe demo data. This workspace already contains a local bootstrap administrator:

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

Changing these flags is not enough to qualify the system for live use. The named-pipe transport remains guarded until the MT5 demo integration and acceptance tests are completed. Use demo accounts only during development.

## MT5 demo integration

The integration sources live in [mt5/README.md](mt5/README.md). Every follower account page shows the exact pipe name and account UUID required by its Executor EA. The master uses `aaa_trade_copier_master` and the active master account UUID.

Compile both agents with the locally installed MetaEditor:

```bat
dev.bat compile-mt5
```

The intended Windows process layout is:

```text
Master MT5 Publisher -> master named pipe -> Copier Core
Copier Core -> one follower named pipe per account -> Follower MT5 Executor
FastAPI dashboard <-> shared SQLite event journal
```

`dev.bat start` opens the Windows Copier Core and web dashboard. The core accepts master events, deduplicates them, applies routing and risk decisions, and records follower acknowledgements. Its real execution gate is derived from both environment safety flags.

## Docker scope

```bat
dev.bat docker-up
```

Docker runs the safe dashboard, SQLite journal, simulator, and reports on `http://127.0.0.1:8100`. Login defaults to `admin@aaa.local` / `AAA-Copier-Docker-2026!` unless overridden through environment variables.

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
