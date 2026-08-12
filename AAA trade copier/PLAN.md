# MT5 Multi-Account Trade Copier — Project Plan

Status: implementation in progress. The fresh control plane, automatic MT5 discovery and agent attachment, durable copier core, continuous Windows MT5 reconciliation, complete lifecycle ticket mapping, and guarded MQL5 integration agents are implemented. Demo hedging-account execution is available; live execution remains gated until the Phase 7 qualification criteria pass.

## 1. Objective

Create a Windows-based system that copies trades from one selected MT5 master
account to multiple follower accounts with low local latency, account-specific
risk sizing, reliable recovery, and a modern web dashboard.

The first release should support approximately ten accounts on one Windows PC
or VPS, while leaving a clean path to more accounts or multiple machines later.

## 2. Recommended architecture

Use one dedicated portable MT5 terminal installation for every account. Each
terminal remains logged into exactly one account and runs one small copier EA.

Recommended execution path:

**Master MT5 → Master Publisher EA → local named pipe → Copier Core → follower
named pipes → Follower Executor EAs → follower brokers**

Separate control and reporting path:

**MT5 agents and Copier Core → event database → FastAPI → WebSocket → web UI**

The FastAPI application is the control and reporting plane. It must not be in
the time-critical trade route. A slow browser, report query, or dashboard
restart must never delay trade copying.

### Why this is the best fit

- A dedicated MT5 terminal per account isolates logins, broker connections,
  symbols, positions, and failures.
- The master EA can capture manual trades and EA trades immediately through
  MT5 trade-transaction events instead of polling positions periodically.
- Persistent Windows named pipes provide fast local communication without an
  external DLL and without making an HTTP request for every trade.
- Each follower EA calculates its own volume from that account's equity and
  broker contract specifications before sending the order.
- The Copier Core provides sequencing, deduplication, routing, reconciliation,
  latency measurement, and a complete audit trail.

### Approaches not recommended for the primary execution path

| Approach | Benefit | Problem | Decision |
|---|---|---|---|
| One Python loop polling every MT5 account | Easiest prototype | Polling delay, missed intermediate changes, weak isolation | Use only for diagnostics or reconciliation |
| EA sends HTTP requests to FastAPI | Simple API | Synchronous web overhead and the web server becomes part of execution | Do not use for the hot path |
| Shared JSON/CSV files | No special communication service | File contention, polling, duplicates, and poor latency | Avoid |
| Direct master-to-every-follower connections | One fewer service hop | Harder recovery, logging, sequencing, and account management | Not preferred |
| Persistent local named pipes through Copier Core | Fast, local-only, no DLL, centrally auditable | Requires a small EA on each terminal | Recommended |

If the system later spans multiple PCs, replace named pipes between machines
with authenticated TLS sockets. The account and risk model should remain the
same.

## 3. Main components

### A. Terminal Manager

- Creates and manages one portable MT5 directory per account.
- Starts, stops, and restarts terminals independently.
- Confirms the expected login, broker server, account currency, trade mode,
  hedging/netting mode, and Algo Trading permission.
- Installs the correct Publisher or Executor EA and opens its control chart.
- Maintains a heartbeat and reports disconnected or frozen terminals.
- Never silently changes the selected master account.

### B. Master Publisher EA

- Runs only on the selected master terminal.
- Observes trade events as they occur, including manual and EA-generated trades.
- Publishes normalized events for:
  - market entry;
  - pending-order creation;
  - pending-order modification or cancellation;
  - stop-loss and take-profit modification;
  - partial close;
  - full close;
  - position reversal where supported.
- Adds a unique event ID, source order/position identifiers, sequence number,
  strategy magic number, symbol, direction, volume, prices, and timestamps.
- Performs minimal work inside the MT5 event handler so MT5's transaction queue
  cannot be blocked.

### C. Copier Core service

- Maintains persistent connections to the Publisher and all Executors.
- Validates and sequences master events.
- Produces one idempotent copy job per eligible follower account.
- Applies routing rules, account status, symbol mapping, and safety gates.
- Dispatches jobs before performing nonessential database/report work.
- Records four separate timestamps:
  - master event detected;
  - Copier Core received;
  - follower command received;
  - broker acknowledgement/fill received.
- Reconciles master and follower state after reconnects or restarts.
- Uses an append-only event journal so an interrupted service can resume without
  duplicating orders.

### D. Follower Executor EA

- Runs on every follower terminal.
- Receives only commands addressed to its account.
- Resolves the broker's actual symbol and contract specifications.
- Calculates follower-specific risk and normalized volume.
- Checks spread, market status, margin, volume limits, slippage limits, and risk
  caps immediately before execution.
- Executes, modifies, partially closes, or closes the mapped follower trade.
- Returns acknowledgement, broker result code, requested price, filled price,
  volume, and error information to the Copier Core.
- Maintains the source-to-follower ticket mapping locally as well as centrally.

### E. FastAPI control and reporting application

- Provides account setup, master selection, routing, risk configuration,
  monitoring, reports, and emergency controls.
- Streams live state to the browser through WebSockets.
- Uses `uv` for Python/project/dependency management.
- Runs as a separate process from Copier Core, even if both are in one project.
- Initially binds to `127.0.0.1` only. Remote access requires authentication,
  HTTPS, and an explicit security review.

### F. Web interface

Recommended simple stack:

- FastAPI;
- server-rendered templates;
- HTMX for actions and partial page updates;
- Alpine.js only where small client-side state is useful;
- Tailwind CSS for a modern responsive interface;
- WebSockets for live account, trade, equity, and latency updates.

This avoids the complexity of a separate React application while still
providing a modern live dashboard.

## 4. Account onboarding and credential security

The web form will accept:

- account display name;
- MT5 login;
- password;
- broker server;
- terminal/broker profile;
- account role: master candidate or follower;
- enabled/paused status;
- risk profile;
- symbol-map profile.

Security requirements:

- Never store passwords in plaintext, SQLite fields, logs, reports, browser
  storage, command-line arguments, or generated documentation.
- Encrypt credentials with Windows DPAPI or Windows Credential Manager under
  the dedicated service identity.
- Prefer a one-time login workflow: use the password to authorize MT5, allow
  MT5 to retain its own encrypted session, then remove the password from the
  application vault when practical.
- Mask login details in normal UI views and record every credential change in
  the audit log without recording the secret.
- Protect the web application with an administrator login even when bound only
  to localhost.
- Require explicit confirmation before changing the master account, closing
  trades, or applying a risk profile to multiple accounts.

## 5. Master selection and routing

- Exactly one account is the active master in version 1.
- Changing the master requires all copy queues to be idle and an explicit
  confirmation screen.
- Each follower can be enabled, paused, or placed in monitor-only mode.
- Routing can include all master trades or filter by:
  - manual trades;
  - EA magic number;
  - symbol;
  - strategy tag/comment;
  - market versus pending orders.
- Recommended default: copy both manual and EA trades, but allow an inclusion
  list of magic numbers so unrelated trades are not copied accidentally.

## 6. Correct risk adjustment per account

The system should copy the trade idea, not blindly copy the master's lot size.

Recommended default mode: **stop-loss risk percentage**.

For every follower:

1. Read current follower equity, free margin, account currency, and broker
   contract data.
2. Map the master symbol to the follower's actual symbol.
3. Preserve the trade direction and intended stop distance.
4. Calculate the follower's allowed cash risk from its configured percentage.
5. Calculate expected one-lot loss at the follower's entry and stop using the
   follower broker's tick value and contract size.
6. Floor the volume to the broker's volume step.
7. Reject the trade if minimum volume would exceed the allowed risk. Never
   round upward silently.
8. Check margin, maximum account exposure, daily-loss limits, and correlated
   exposure before sending.

Example policy: a $100,000 master and a $10,000 follower can take the same idea,
but a follower configured for 1% risk should risk approximately $100 at its own
broker prices—not copy the master's lots.

### Supported sizing modes

| Mode | Use | Recommendation |
|---|---|---|
| Stop-loss risk percentage | Accurate risk when an SL exists | Default |
| Fixed cash risk | Account-specific fixed amount | Supported |
| Equity proportional to master lots | Compatibility mode | Optional, not default |
| Fixed lots | Testing or special cases | Restricted and clearly warned |

Trades without a stop loss should be rejected by default. An optional per-
account fallback may use a configured emergency stop or fixed-lot rule, but it
must never be silently assumed.

### Portfolio-level safety limits

- maximum risk per trade;
- maximum total open risk;
- maximum risk per symbol or asset group;
- maximum daily realized loss;
- maximum daily equity drawdown;
- maximum spread and slippage;
- maximum simultaneously open copied positions;
- optional news/session blocks;
- pause-new-trades switch that still allows closes and protective changes.

## 7. Cross-broker compatibility

Maintain an explicit symbol-mapping table, for example:

- master `USTEC` → follower `NAS100`, `US100`, or broker-suffixed equivalent;
- master `XAUUSD` → follower `GOLD` or `XAUUSDm`;
- master `US30` → follower `DJ30` or `WS30`.

Each mapping records contract size, tick size, supported order types, minimum
stop distance, trading sessions, and whether prices require a mapping offset.

The copier should carry both absolute prices and relative distances. For cross-
broker execution, the recommended default is to preserve SL/TP distance from
the follower's fill rather than blindly copying an absolute master price.

Hedging and netting accounts require different ticket mapping. Version 1 should
fully support hedging accounts. Netting support should be enabled only after
tests cover merged positions, partial reductions, and reversals.

## 8. Reliability and reconciliation

- Every source event and follower job has a unique, deterministic idempotency
  key. Replaying an event must not create a duplicate trade.
- Sequence numbers preserve modification and close order.
- Trade-transaction arrival order cannot be assumed; the system rebuilds the
  current state from terminal orders, positions, and history when necessary.
- Each agent sends a heartbeat at least once per second.
- After a reconnect, the system compares master and follower state before
  accepting new entries.
- Protective closes and SL modifications have priority over new entries.
- If the master closes while a follower is disconnected, the close remains in
  a durable queue and is executed immediately after reconnection, subject to a
  visible warning.
- A watchdog restarts individual terminals or services without restarting the
  entire system.
- An emergency global pause stops new copies; closing all accounts is a
  separate, strongly confirmed action.

## 9. Latency strategy and measurements

The goal is low and measurable latency, not an impossible guarantee of equal
broker fills.

Design targets on one healthy Windows VPS:

- master event to Copier Core receipt: p95 below 25 ms;
- Copier Core receipt to follower command delivery: p95 below 25 ms;
- combined local dispatch: p95 below 50 ms;
- zero duplicate orders during normal operation and restart tests;
- broker acknowledgement and fill latency measured separately because it is
  controlled by terminal-to-broker network conditions.

Methods:

- event-driven capture instead of Python position polling;
- persistent named-pipe connections;
- compact versioned messages;
- dispatch before dashboard/database fan-out;
- bounded in-memory queues with an append-only durable journal;
- high-resolution EA timers only for receiving/reconciliation work;
- no report generation or browser requests on execution threads;
- Windows VPS located near the brokers' trade servers when live latency matters.

## 10. Web application pages

### Dashboard

- master account and system state;
- total balance, equity, realized P&L, floating P&L, and open risk;
- active trades across all accounts;
- follower health and last heartbeat;
- copy success/failure counts;
- current p50/p95/p99 copy and broker latency;
- warnings and emergency pause.

### Accounts

- add/edit/remove account;
- verify login and server;
- master selection;
- start/stop/restart terminal;
- balance/equity/margin and hedging/netting mode;
- risk profile and symbol-map assignment;
- monitor-only, paused, and active state.

### Active trades

- master trade with all linked follower trades;
- requested versus filled prices and slippage;
- requested versus actual follower risk;
- SL/TP and modification state;
- missing, rejected, delayed, or manually changed followers.

### History and reports

- per account and combined views;
- daily, weekly, monthly, and custom periods;
- deposits/withdrawals separated from trading P&L;
- realized P&L, floating P&L, return, drawdown, win rate, PF, and trade count;
- copy success rate, rejection reasons, slippage, and latency;
- master-versus-follower divergence;
- CSV export.

### Configuration and audit

- routing rules;
- risk profiles;
- symbol mappings;
- account safety limits;
- user actions, configuration changes, copier decisions, and broker errors.

## 11. Data storage

Start with SQLite in WAL mode because version 1 is a single-host application.
Keep database writes off the trade-dispatch path. Move to PostgreSQL only when
multi-host deployment, multiple dashboard users, or substantially higher event
volume justifies it.

Planned data groups:

- accounts and encrypted-secret references;
- terminal instances and heartbeats;
- master selection and routing rules;
- risk profiles and symbol mappings;
- source trade events;
- follower copy jobs and acknowledgements;
- order, deal, and position mappings;
- equity snapshots and daily statistics;
- latency samples;
- alerts and audit events.

Retention defaults should preserve complete trade/audit history while allowing
old high-frequency heartbeat and equity samples to be summarized.

## 12. Delivery phases

### Phase 0 — Final specification

- Confirm same-PC/VPS deployment and target account count.
- List brokers, servers, symbols, hedging/netting modes, and prop-firm rules.
- Confirm whether manual trades, all EAs, or selected magic numbers are copied.
- Lock the risk and no-stop-loss policies.
- Define the exact pass/fail acceptance criteria below.

### Phase 1 — Read-only foundation

- Project structure managed by `uv`.
- FastAPI application and modern Tailwind dashboard shell.
- SQLite schema, audit log, authentication, and secret vault design.
- Terminal Manager discovers accounts and reports balances/health.
- No order execution.

### Phase 2 — Account and terminal management

- Add-account workflow.
- One isolated portable terminal per account.
- Login verification, master selection, watchdog, and heartbeats.
- Read-only open-trade and history dashboard.

### Phase 3 — Copier MVP on demo accounts

- Master Publisher and Follower Executor agents.
- Persistent local named-pipe protocol.
- Copy market entries and full closes only.
- Stop-risk sizing, symbol mapping, deduplication, and acknowledgements.
- Start with one master and one follower.

### Phase 4 — Complete trade lifecycle

- Pending orders, cancellations, SL/TP changes, partial closes, and reversals.
- Hedging-account mapping and restart reconciliation.
- Spread, slippage, margin, exposure, and daily-loss gates.
- Expand testing to ten demo accounts.

### Phase 5 — Reports and operational UI

- Live trade tree and account dashboard.
- Per-account and combined reports.
- Latency, slippage, divergence, rejection reasons, and alerts.
- CSV exports and searchable audit history.

### Phase 6 — Hardening

- DPAPI/Credential Manager integration.
- Failure injection: broker disconnects, terminal restarts, Copier Core restart,
  duplicate/out-of-order messages, slow follower, and database lock.
- Recovery validation with open positions and pending orders.
- Windows service packaging, backups, log rotation, and upgrade/rollback plan.

### Phase 7 — Demo qualification

- Run two accounts for at least one week.
- Run the target ten-account topology for at least thirty calendar days.
- Compare every master event with every eligible follower result.
- Review all risk differences, missed trades, duplicates, slippage, and latency.
- Do not proceed while unexplained divergence remains.

### Phase 8 — Controlled live rollout

- Verify every broker/prop firm permits EAs and trade copying.
- Start with one low-risk follower.
- Add followers gradually after reconciliation and risk reports remain clean.
- Keep a manual emergency stop and documented rollback procedure.

## 13. Acceptance criteria before live use

- Zero duplicate entries across restart and reconnect tests.
- Every eligible master action produces a follower acknowledgement or an
  explicit visible rejection—never a silent miss.
- Follower risk is within one broker volume step of the configured target.
- A follower never exceeds its per-trade, total exposure, or daily-loss limit.
- Full and partial closes reconcile correctly on all supported account modes.
- Symbol mapping is verified with live broker contract data.
- Local dispatch p95 is below 50 ms on the intended host under ten-account load.
- Broker latency is displayed separately and never misreported as copier delay.
- Service/terminal restart recovers mappings without creating new exposure.
- Passwords are absent from databases, logs, reports, process arguments, and
  browser storage.
- Thirty-day ten-account demo test completes with no unexplained divergence.

## 14. Important limitations

- No copier can guarantee identical fills across different brokers or servers.
- Fast copying does not remove spread, slippage, market gaps, rejected orders,
  minimum-volume limits, or differing contract specifications.
- A 1% configured stop risk can be exceeded by gaps or slippage.
- Prop firms may restrict EAs, copy trading, identical trading across accounts,
  account groups, or maximum allocation. Compliance must be verified per firm
  before an account is enabled.
- The system should never promise profits or payouts; it only copies and manages
  execution according to configured rules.

## 15. Recommended version-1 defaults

- One Windows VPS or PC; maximum ten accounts.
- One portable MT5 terminal per account.
- One master, multiple followers.
- Local named-pipe execution transport.
- FastAPI/HTMX/Tailwind dashboard bound to localhost.
- `uv` project and dependency management.
- SQLite WAL database.
- Hedging accounts first; netting accounts gated until specifically tested.
- Stop-loss percentage sizing, default 1% per account.
- Trades without an SL rejected.
- Minimum lots never rounded upward.
- Copy market orders, pending orders, modifications, partial closes, and closes.
- New entries pause automatically when an account or agent is unhealthy.
- Protective changes and closes continue while new entries are paused.

## 16. Research basis

- MT5 exposes trade changes through `OnTradeTransaction`, including manual
  trades, EA trades, pending-order activation, and server-side operations:
  https://www.mql5.com/en/docs/event_handlers/ontradetransaction
- MQL5 can communicate through local Windows named pipes without a DLL:
  https://www.mql5.com/en/docs/files/fileopen
- MT5 supports sub-second EA timers, normally limited to approximately 10–16 ms
  by hardware in real time:
  https://www.mql5.com/en/docs/eventfunctions/eventsetmillisecondtimer
- The official Python integration connects to a specified terminal executable
  and supports portable mode, which supports the dedicated-terminal design:
  https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
- MQL5 also supports TCP/TLS sockets if a future multi-machine version is
  required:
  https://www.mql5.com/en/docs/network
- `uv` officially supports FastAPI projects and locked project environments:
  https://docs.astral.sh/uv/guides/integration/fastapi/
