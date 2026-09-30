# Calyx Crypto Arbitrage - Research and Implementation Master Plan

Created: 2026-09-19  
Re-planned: 2026-09-29 - application stack fixed to **FastAPI + SQLite + Tailwind CSS (Calyx site theme) + uv**, with an
admin dashboard for API keys; cost and paper-trading tables added (§11, §12, §16, §17).  
Status: PLAN ONLY - no trading deployment or profitability validation; nothing installed, no keys created  
Owner workspace: `C:\Users\hama101\Desktop\geek\ai trader\AAA crypto arbitage`  
Sister plan: `POLYMARKET_COPY_AND_MEME_ROTATION_PLAN.md` (Models D and E). Both plans share **one** application
platform defined in §16-§17 of this file.

## 1. Purpose and decisions already agreed

Investigate whether we can build a crypto arbitrage system inspired by BJF Trading Group's fast-feed/slow-venue concept, using established open-source infrastructure rather than starting from scratch.

The intended deliverable is an evidence-based BTC-first experiment, followed only if justified by a controlled live pilot. The project must distinguish a technically working bot from an economically profitable strategy.

Current decisions:

- **Application stack (decided 2026-09-29):** Python 3.12 managed with **uv** (`pyproject.toml` + `uv.lock`), **FastAPI**
  (+ Jinja2 templates), **SQLite** as the only database for now, **Tailwind CSS** using the Calyx website's design tokens,
  and an **admin dashboard** for API keys, bot modes and risk limits. See §16-§17.
- Use **HftBacktest as the initial research/backtesting foundation** (pip/uv-installable).
- Use **ccxt** (MIT, uv-installable) as the first exchange adapter layer for REST and WebSocket access in paper/shadow mode.
  **Hummingbot** remains an optional later execution reference, but it is normally run from its own Docker/conda
  environment, so it is kept **outside** the uv project and is not a phase-1 dependency.
- Add **Cryptofeed only if needed** for recording or exchange coverage. Do not build multiple overlapping data systems unnecessarily.
- Keep **Flashbots simple-arbitrage as a separate educational reference**, not the initial implementation and not a contract to fund unchanged.
- Start with BTC on two eligible exchanges, preferably the same spot pair and quote asset on both. ETH is a later extension.
- Start with no leverage, no martingale, no doubling, and no automatic deposits or withdrawals.
- Evaluate cross-exchange arbitrage and fast-feed lead-lag as **separate strategies**. Do not substitute one for the other without labeling the change.
- Preserve the existing Calyx website, MT5 EAs, launchers, accounts and portfolio. This is a separate research project.
- Do not install packages, clone projects, purchase data/software, connect trading keys, or place orders merely because this document describes those steps. Those are future stages, not actions completed while saving this plan.

Success is not a promised daily income or target return. Success first means discovering whether an executable net edge exists at our actual fee tier, capital size and connectivity.

## 2. What was reviewed, and limits of the evidence

### 2.1 BJF material

Reviewed the supplied latency-arbitrage narration and BJF's latency and crypto product pages. The embedded YouTube player could not be played through the research tool. The assessment therefore relies on supplied transcripts, retrieved pages and technical documentation; it is not a claim of having watched every video frame.

BJF describes detecting a price move on a reference feed before a target venue updates, then entering and exiting around the expected catch-up. Its crypto product advertises both latency and hedge modules.

Vendor speed, revenue and profitability claims are not independently verified performance evidence. A delayed quote received by our computer does not prove that the matching engine will execute against that quote. No claim of universal exchange permission, geographic eligibility, or guaranteed advantage should be copied from marketing material.

### 2.2 Attached AI/DEX tutorial

Original supplied transcript:

`C:\Users\hama101\.codex\attachments\587cc999-b08b-408e-9013-0c4e6b8970df\Pasted text.txt`

The tutorial describes an off-chain searcher and an on-chain executor, then instructs the viewer to deploy a contract, deposit ETH, press Start and later withdraw. It claims a minimum of 1 ETH and presents an increased contract balance as evidence.

Unresolved warning signs:

- The transcript does not establish how the required off-chain searcher is installed and operated.
- A contract needs transaction-driven execution; it does not independently wake up and continuously scan venues.
- A wallet being the contract creator does not establish safe ownership or exclusive withdrawal rights.
- Deposits or rising balances do not prove arbitrage profit. Trace all incoming/outgoing funds and transaction costs.
- There is no universal minimum of 1 ETH for arbitrage software.
- The source repository, deployed contract address and complete transaction evidence for that specific demonstration have not been supplied or audited.

These are reasons not to fund the tutorial code, not a conclusive accusation about an unidentified contract. If we revisit it, obtain the exact source and deployed address, inspect bytecode/source correspondence and fund flows, and test locally before considering any money.

## 3. Separate the strategy hypotheses

| Model | Trading mechanism | Main uncertainty | Planned treatment |
|---|---|---|---|
| A: Prefunded cross-exchange spot arbitrage | Buy BTC on the cheaper exchange and sell existing BTC inventory on the dearer exchange as close together as possible | One leg may fail; fees, depth and rebalancing can remove the edge | First executable prototype candidate |
| B: Fast-feed lead-lag / latency | Reference venue moves; trade the target venue, then exit on catch-up or a strict risk/time limit | Apparent lag may be only data-delivery lag; the trade is directional until closed | Separate research arm, not described as risk-free |
| C: Same-chain DEX arbitrage | Off-chain searcher finds a route; on-chain executor performs multiple swaps in a transaction | Gas, MEV competition, inclusion, contract security and route state | Deferred educational/research branch |

### Model A: starting definition

1. Compare executable depth-weighted buying and selling prices for a fixed BTC quantity.
2. Require sufficient quote balance on the buying exchange and BTC balance on the selling exchange.
3. Require estimated net profit above costs plus a conservative uncertainty buffer.
4. Send both legs using supported price-bounded execution, preferably marketable limit/IOC orders where available and correctly implemented.
5. Track actual fills, quantities, fees and remaining exposure independently.
6. If only one leg executes, follow a predefined bounded reconciliation/hedging procedure and stop further opportunities until reconciled.
7. Repeat in either direction only when balances allow. Rebalance inventory outside the critical execution path, with all costs attributed.

Do not buy BTC, transfer it across the blockchain and then sell as if that were a simultaneous trade. The transfer delay and price exposure make that a different strategy.

### Model B: starting definition

1. Detect reference-price changes and target executable prices using timestamped, healthy books.
2. Estimate normal cross-venue basis from past data only. Do not treat every persistent venue premium as temporary mispricing.
3. Enter only if the price available after modeled order latency still provides enough expected edge to cover entry and exit fees, slippage and a buffer.
4. Exit on basis-adjusted convergence, adverse-price limit, or a maximum holding time.
5. Freeze initial rules before measuring held-out results. Determine provisional thresholds from observed data quality and costs, not by searching thousands of profitable historical settings.

The fast venue is not assumed in advance. Measure which venue leads, by how much, at what times, and whether this is stable. Spot short trades require inventory or borrowing; do not simulate unrestricted shorting in an unleveraged spot account.

### Model C: if revisited later

Use an audited design with an off-chain searcher, route simulation, explicit minimum-output/profit checks, a constrained executor, and protected submission where appropriate. Atomic route failure can revert swaps but still incur transaction costs. Private submission is not a profit guarantee. Searcher competition and validator/builder payments must be included.

Do not combine cross-chain settlement with an assumption of same-chain atomic execution. Do not implement market-manipulation or broker-restriction evasion features.

## 4. Recommended repositories and reuse boundaries

### HftBacktest - first research dependency

Repository: https://github.com/nkaz001/hftbacktest  
Documentation: https://hftbacktest.readthedocs.io/en/latest/  
License shown during review: MIT

Relevant capabilities include full order-book/trade replay, feed and order latency, queue-position models, multi-asset and multi-exchange testing, and Python/Numba plus Rust components. The project documents Rust live-trading support for Binance Futures and Bybit; do not assume this automatically covers our chosen two-exchange spot deployment.

Reuse:

- Event/replay framework and order-book structures.
- Latency and queue-model interfaces.
- Collector/data examples where suitable.
- Backtesting statistics as inputs to our independent reporting checks.

We still implement our own synchronized multi-venue strategy, inventory accounting, fee calibration and scenario definitions.

Limitations to address explicitly:

- Historical replay cannot alter historical liquidity in response to our trades; market impact is not faithfully modeled.
- The default no-partial-fill model can be optimistic for liquidity-taking orders.
- Partial-fill models also have limitations; small order sizes and conservative depth assumptions remain necessary.
- Queue estimates and latency inputs are assumptions unless independently measured.
- Historical results must be reconciled against actual tiny live fills before claiming executability.

### Hummingbot - preferred trading-prototype foundation

Repository: https://github.com/hummingbot/hummingbot  
Releases: https://github.com/hummingbot/hummingbot/releases  
License shown during review: Apache-2.0

Reuse exchange connectors, balance/order tracking, strategy lifecycle and monitoring interfaces. The repository and release history provide evidence of substantial engineering activity, not audited profitability for our strategy.

Specific source reviewed:

https://github.com/hummingbot/hummingbot/blob/master/hummingbot/strategy_v2/executors/arbitrage_executor/arbitrage_executor.py

At review time, the executor constructor defaulted to `update_interval=1.0` and its order functions requested `OrderType.MARKET`. It is therefore not a drop-in implementation for 50-200 ms opportunities.

Before live reuse:

- Audit the selected release's fee calculation, quote normalization, order retries, early-stop behavior and P&L reporting.
- Benchmark callback-to-send and send-to-fill performance.
- Verify price protection and partial-fill handling for each actual connector.
- Add stale-book gates, idempotent order identifiers, unmatched-leg handling and shutdown behavior.
- For strict latency trading, consider a custom event-driven execution component using supported APIs if measurements show the standard controller/executor path is inadequate. Lowering a timer alone is not proof of suitability.

### Cryptofeed - optional recording component

Repository: https://github.com/bmoscon/cryptofeed

Use its WebSocket order-book/trade normalization and recording backends if they solve a concrete coverage or recording gap. Preserve raw exchange messages as well as normalized events so transformations remain auditable. Verify current connector behavior and license at the chosen revision.

### Flashbots simple-arbitrage - deferred reference

Repository: https://github.com/flashbots/simple-arbitrage

The project's own README warns that its example is very unlikely to be profitable because the opportunities are well known and competitive. Treat it as an architecture example, not a recommended funded bot. Verify current API compatibility, dependencies and license before reuse.

### Dependency policy

On implementation approval, pin release tags/commit SHAs and record them in a dependency manifest. Do not invent or assume revision IDs now. Review licenses and notices before redistribution or Calyx commercial integration. Never run random installation scripts with wallet secrets present. Repository popularity is not a security audit.

No repositories were cloned or installed as part of saving this plan.

## 5. Venue selection and unresolved decisions

Do not choose exchanges solely because a library supports them. Before any account connection establish:

- User's actual country of residence and the relevant exchange entity's onboarding/product permissions. A computer timezone is not residency evidence.
- Which accounts the user already has and whether spot API trading is enabled.
- Applicable maker/taker fees, discounts, commissions charged in another asset, and minimum order/notional increments.
- Supported identical BTC pair and quote currency on both venues.
- Order-book feed cadence, completeness, sequence numbers and exchange timestamp meaning.
- Order submission APIs, rate limits, client order IDs, IOC/limit semantics and private fill streams.
- Minimum deposits/withdrawals, available networks, operational status, funding restrictions and custody concentration.
- Whether the proposed activity complies with exchange terms. No geographic bypass or concealment features.

Binance, Bybit, OKX and Kraken are examples to investigate, not an approved account shortlist. Actual eligibility, fees and API behavior decide selection.

Prefer the same quote asset. If using different stablecoins, model conversion costs and depeg exposure instead of assuming dollar parity. Never treat wrapped and native assets as costlessly interchangeable.

## 6. Architecture and data requirements

Logical components:

1. **Exchange adapters:** raw feeds, snapshot/delta recovery, public and private connection health.
2. **Recorder:** append-only raw events, normalized events, timestamps and quality markers.
3. **Opportunity engine:** executable-size pricing, fee-aware comparisons, lead-lag calculations.
4. **Risk and inventory manager:** balances, exposure, outstanding orders, daily shutdown and reconciliation.
5. **Replay/simulator:** separate exchange-state and local-observed-state timing, modeled execution.
6. **Execution adapter:** initially disabled; later authenticated routing and fill tracking.
7. **Accounting/reporting:** cashflows, marked inventory, costs, trade logs and Calyx research views.

Keep the trading-critical path separate from dashboards, databases that can block, and AI responses. AI may assist offline development, investigation and reporting; it must not authorize each millisecond-sensitive trade.

Mapping onto the 2026-09-29 stack: components 1-6 run as **uv-managed worker processes**, and component 7 plus all
control and configuration lives in the **FastAPI dashboard** (§16-§17). Workers read their configuration and decrypted
keys at start-up and write fills and ledger rows to SQLite through a non-blocking queue. The dashboard never sits
between a signal and an order. High-frequency order-book recordings stay in compressed files and are **not** stored in
SQLite (see §16.3).

### Required recorded fields

- Venue, market type, symbol, base/quote asset and contract specification where applicable.
- Exchange event time and its defined semantics.
- Local UTC receipt time and local monotonic receipt time.
- Snapshot/update IDs, bids/asks and quantities, trade events where available.
- Disconnects, dropped sequences, resynchronization and stale intervals.
- Clock-offset estimates, process version, server region and configuration hash.
- Later pilot: decision, send, acknowledgment, partial/full fill and cancel times; order IDs; actual fee asset and amount.

Do not infer one-way network latency simply by subtracting unrelated unsynchronized timestamps. Record clock uncertainty. Replay must not expose an exchange event to the strategy before its simulated local arrival.

Use immutable compressed files with schema version and checksums. Partition by venue, pair and UTC date. Build derived datasets reproducibly. Treat the first day's measured storage growth as the basis for retention budgets.

### Historical coverage

Our existing MT5 candles/ticks are not synchronized two-exchange depth and cannot validate this project. Historical L2/L3 data from suitable providers may help, but historical local latency for our own server is unavailable unless it was recorded.

First check lawful data availability, resolution, completeness and licensing. Do not purchase datasets without approval. If adequate history is unavailable, collect fresh data for 30 days. Missing depth or timestamps must be reported, not fabricated.

## 7. Cost and accounting model

For matched base quantity q and the same quote asset:

`estimated edge = q * (executable sell price - executable buy price) - buy fees - sell fees - additional execution allowance - allocated rebalancing costs`

Executable prices should consume available depth for q. Avoid counting that depth-related slippage twice. A separate allowance can represent latency, uncertainty and adverse fills. In a detailed replay, derive execution prices from the delayed order-arrival state rather than merely subtracting a fixed spread.

Include when applicable:

- Actual fees on every fill, with fee-currency conversion.
- One-leg hedging/unwind costs and canceled/rejected-operation outcomes.
- Rebalancing commissions, transfers, network fees and conversion spread.
- Derivative funding and borrowing only if a separately approved derivative/margin model is used.
- Hosting/data expenses in business-level net results, separate from trading P&L.
- Daily mark-to-market of BTC and stablecoin inventory, not just favorable matched trades.

Holding BTC for spot selling creates inventory exposure. Neutrality relative to initial inventory is not the same as a cash-neutral account. Report total account equity and incremental arbitrage P&L separately. Compare against holding the same initial inventory without trading and against cash where meaningful.

Illustrative fee hurdle, not a forecast: with $1,000 notional on each leg, a 0.15% price difference earns $1.50 gross. Assuming 0.10% fees on both legs costs about $2 total, leaving about -$0.50 before other costs. Verify actual account fees instead of hard-coding this example.

## 8. First experiment and validation protocol

### Raw baseline

- BTC only; two venues; same spot pair if available.
- Models A and B independently reported.
- No leverage, no martingale, no hidden risk scaling.
- Compare at fixed order sizes supported by both venues, initially considering $25, $50 and $100 equivalent for feasibility. These are sensitivity scenarios, not guaranteed executable sizes.
- Base fees from the actual account tier, not an unattained VIP tier.
- No proprietary paid feed or software license initially.
- Freeze baseline logic and experiment manifest before evaluating a held-out window.

### Timing and execution stress

Test measured latency distributions when available and clearly labeled hypothetical order delays of 20, 50, 100, 200 and 500 ms. Treat feed and order latency separately. Correlate adverse latency with volatile periods where measurements support it; do not sample every delay independently without justification.

Stress book age, reduced available depth, higher fees, partial fills, one-leg rejection, disconnects, exchange throttling, rebalancing costs and stablecoin conversion. For marketable orders, ensure limits and exchange minimums still permit the simulated fill.

### Chronological validation

A provisional 30-day split is 14 days development, 7 days validation and 9 days untouched final evaluation. This is an initial feasibility screen, not enough to establish long-term profitability. Include quiet periods, active periods, weekends and high-volatility sessions. Extend collection if opportunities are rare or conditions are unrepresentative.

Record every tested variant and rejected idea. Do not choose parameters on the entire dataset and then label the same results out-of-sample. After viewing the final window, any new settings require a new untouched period.

### Required report

- Exact UTC dates, venues, products, fee tiers, data coverage and gaps.
- Gross opportunities, fee-positive opportunities, eligible operations and rejected opportunities by reason.
- Matched completed cycles, individual legs, partial fills, unmatched exposure and failures. A two-leg cycle is not two independent strategy wins.
- Net trading P&L, operating costs, total marked equity, incremental strategy P&L and inventory benchmark.
- Trade/cycle count, net win rate, average win/loss, expectancy, profit factor and maximum equity drawdown.
- Monthly/daily results and longest loss sequence where the sample supports these summaries.
- Total fees, realized slippage and rebalancing/hedging cost breakdown.
- Exposure duration, peak unmatched notional and worst single failure scenario.
- Latency percentiles and break-even fee/latency estimates.
- Capital utilization, results by venue direction and profit concentration by day.
- Raw baseline versus stressed variants versus held-out results.

Report confidence limitations. Opportunities clustered in one market move are not independent samples. If uncertainty intervals are calculated, use an appropriate block/day treatment rather than pretending every tick is independent. Never manufacture a probability of profit or pass/fail confidence from insufficient data.

## 9. Risk controls for an eventual approved live pilot

The following are proposed pilot limits, not live settings and not guarantees:

- $500-$1,000 total experimental capital across two venues, only if the user chooses to risk it and balances/minimums support the strategy.
- Initially $25-$100 equivalent per leg, bounded by actual liquidity and balances.
- One outstanding arbitrage operation at a time.
- No leverage, borrowing, martingale or averaging down.
- Proposed $10 daily trading-loss shutdown, including fees and failed-leg costs. Unfilled exits, outages and gaps can cause a larger loss.
- Separate total-equity/inventory drawdown monitoring; do not hide spot inventory losses behind profitable cycles.
- No withdrawals on trading API keys; IP allowlisting where available; a dedicated subaccount if supported.
- Keys remain in secure local/server secret storage, never Markdown, Git, logs, chat or public dashboards.
- Stop initiating trades on stale books, missing sequences, clock anomalies, exchange status problems, balance mismatches or unreconciled orders.
- Bound the time and notional allowed for unmatched exposure. Calibrate limits from measurements; do not promise a fixed millisecond hedge guarantee across venues.
- A manual kill switch plus automatic shutdown. Shutdown must reconcile outstanding orders; simply stopping the process can leave exposure.
- Never automatically retry an uncertain order until checking its client ID/status to avoid duplicate fills.
- Notify the operator on actionable failures. Future notification setup requires its own explicit implementation step.

Demo/testnet and paper fills are useful for plumbing, not evidence of production liquidity or profitability. Only an explicitly approved tiny live pilot can validate our real fills.

## 10. Phases, deliverables and go/no-go gates

| Phase | Indicative effort/time | Deliverable | Exit condition |
|---|---|---|---|
| 0. Venue and dependency review | 2-3 days | Eligibility/fee/API matrix, pinned dependency plan | Two suitable venues and no unresolved permission/security issue |
| 1. Recorder and quality checks | About 1 week build; 2-4 weeks collection | Auditable synchronized data and quality report | Replay-compatible books, known gaps and usable timing |
| 2. Raw replay and shadow operation | 1-2 weeks, overlapping collection | Model A/B reports with all costs and stress scenarios | Plausible net edge not dependent on optimistic fills |
| 3. Held-out review | Dataset-dependent | Untouched-window results and failure analysis | Edge survives realistic measured delays and costs across multiple days |
| 4. Tiny live pilot | 2-4 weeks after explicit approval | Expected-versus-realized fill/cost comparison | Actual net outcomes support the hypothesis; failures remain controlled |
| 5. Scale or stop | Evidence-dependent | Written decision and revised limits | Repeatable net economics justify added capital/complexity |

These durations are planning estimates, not a delivery or income promise. Integration or data gaps may extend them.

Stop or redesign if fees remove the edge; order arrival occurs after opportunities disappear; losses on failed legs dominate; results depend on one day, one assumed clock offset or implausible fill rules; or legal/account restrictions prevent execution.

Do not proceed to live merely because a simulation displays a high win rate. Some profitable-looking cycles may not cover inventory, rebalancing or infrastructure costs.

## 11. Budget, API-key costs, paper trading and purchasing policy

Re-checked 2026-09-29. Prices change; re-verify before paying anything. Figures exclude labour, taxes and trading losses.

### 11.1 Cost per API key / service (Models A and B)

| Service | Key needed? | Cost of the key/subscription | Per-trade cost | Paper trading available? |
|---|---|---|---|---|
| Binance spot API | Yes (trading); no key for public books | $0 | 0.10% maker/taker (0.075% paying fees in BNB) at the regular tier | **Yes**: Spot Testnet with virtual balances. Plumbing only; its liquidity is not the real market. |
| Bybit spot API | Yes (trading) | $0 | 0.10% / 0.10% at the regular tier | **Yes**: separate testnet, plus a demo account on mainnet with pre-funded virtual balances |
| OKX spot API | Yes (trading) | $0 | 0.08% maker / 0.10% taker at the regular tier | **Yes**: demo-trading API keys and a simulated-trading header |
| Kraken spot API | Yes (trading) | $0 | Higher at low volume; check the account's tier | Spot: no official sandbox found, so use shadow mode |
| Public WebSocket order books and trades (all venues) | No | $0 | - | Used for **shadow/paper mode on real books**, which is the only paper mode that measures real economics |
| ccxt, HftBacktest, Cryptofeed (open source) | No | $0 | - | - |
| Historical L2 data vendor (e.g. Tardis-style) | Yes | **Not budgeted.** Get a quote only if 30 days of self-recording is not enough. | - | - |
| Telegram Bot API (alerts, `/pause`, `/kill`) | Bot token | $0 | - | - |
| Claude API (optional weekly research summaries, never in the trade path) | Yes | Usage-based; weekly summaries on a small model should cost a few dollars a month. Check anthropic.com/pricing. | - | - |
| Server: local Windows PC (phases 0-3) | - | $0 (latency not representative) | - | - |
| Server: DigitalOcean (measured regions) | - | 4 GB basic **$24/month**; 4 GB CPU-optimised **$42/month** (reviewed 2026-09-29) | - | - |
| Backups/monitoring | - | $0-$10/month | - | - |

Round-trip hurdle for Model A at regular-tier taker fees on both venues: about **0.20% of notional**, before slippage
and rebalancing. A gap smaller than that is not an opportunity.

### 11.2 Expected initial cost

| Stage | One-off | Monthly | Notes |
|---|---:|---:|---|
| Phases 0-3: recorder, shadow/paper mode, dashboard on the local PC | $0 | **$0** | All keys are free; public data only; testnet keys for plumbing tests |
| Same, on a cloud server for realistic latency | $0 | **$24-$52** | $24-$42 server + $0-$10 backups |
| Phase 4: tiny live pilot (only after explicit approval) | **$500-$1,000 capital** split across two venues | $24-$52 | Capital is at risk. Fees are paid per fill from the capital. |

**Paper first? Yes, for both Model A and Model B.** Use shadow mode on real public books, with simulated fills at
executable depth and modelled latency. Use exchange testnets and demos only to prove order and plumbing code; never
count their P/L as evidence.

DigitalOcean pricing (re-checked 2026-09-29): a 4 GB basic Droplet is $24/month and a 4 GB CPU-optimised Droplet is $42/month, now billed per second with a monthly cap. Ordinary cloud hosting does not establish exchange colocation or a speed advantage. Choose regions by measurement, including tail latency and connection stability, not solely marketing or ping.

BJF's crypto product page reviewed on that date lists a $1,790 one-time license. This plan does not recommend purchasing it before feasibility is demonstrated. Hosting and trading capital would be additional.

Own development time and existing AI/tool subscriptions are not free economically and are excluded from the cash table. Obtain a separate scoped quote if outsourcing. DEX RPC services, audits and gas are also excluded because that path is deferred.

No credible expected monthly income is available yet. Do not extrapolate vendor screenshots or a short optimized sample into an income forecast.

## 12. Suggested future project organization

**Implemented from 2026-09-29 in `crypto-lab/`** (Model D first; see `crypto-lab/README.md` and `crypto-lab/progress.md`).
The code lives in that subfolder so it can be extracted and open-sourced as its own repository. There is **one uv project** for all five models
(A-E), with one dashboard and separate workers:

```text
AAA crypto arbitage/
  CRYPTO_ARBITRAGE_MASTER_PLAN.md
  POLYMARKET_COPY_AND_MEME_ROTATION_PLAN.md
  pyproject.toml  uv.lock  .python-version      # uv-managed, Python 3.12
  .env.example                                  # names only, never values
  app/
    main.py                  # FastAPI app factory, routers, Jinja2
    settings.py              # pydantic-settings; DB path, bind host, master-key source
    db.py  models.py         # SQLModel/SQLAlchemy 2 on SQLite (WAL mode)
    migrations/              # Alembic
    security/  auth.py  vault.py  csrf.py       # admin login, encrypted key vault
    routers/   admin_keys.py  admin_bots.py  admin_risk.py  audit.py
               cex.py  polymarket.py  solana.py  research.py
    templates/ base.html  admin/*.html  cex/*.html  polymarket/*.html  solana/*.html
    static/    calyx.css (tokens copied from the site)  app.css (Tailwind build output)
  workers/
    cex_recorder.py  cex_arb_shadow.py           # Models A/B
    poly_collector.py  poly_scanner.py  poly_copy_paper.py   # Model D
    sol_scanner.py  sol_rugfilter.py  sol_rotation_paper.py  # Model E
    telegram_bot.py
  tests/                     # unit, replay, accounting, vault and auth tests
  data/                      # git-ignored
    crypto_lab.sqlite        # app state, ledgers, paper fills, audit log
    raw/  normalized/        # compressed order-book/trade recordings (Parquet/zstd)
  experiments/  reports/     # manifests, standard results tables, graphs
```

Keep this environment separate: do not install into or alter the active MT5/Calyx runtime or the public website. Do not commit API keys, the SQLite file or market-data archives. Preserve upstream licenses and notices.

The dashboard reuses the Calyx website's **look** (§16.4). It is a separate app on its own port and is **not** mounted on the public site. A public research page on the Calyx website remains a later, separately approved change. Trading logic runs independently of website availability.

## 13. Tests required before enabling execution

- Order-book snapshot/delta reconstruction, dropped-sequence recovery and stale-feed gating.
- Timestamp ordering, clock-offset uncertainty and no-lookahead replay.
- Fee calculations for both sides, fee-in-base cases, rounding and minimum notional.
- Depth-sensitive execution, IOC partial fills, unmatched-leg scenarios and canceled orders.
- Client-ID idempotency and recovery after timeout or process restart.
- Daily loss/equity calculations, inventory mark-to-market and cashflow reconciliation.
- Rebalance-cost attribution without double counting.
- No trading when balances, books or order states are uncertain.
- Shutdown with open orders and residual inventory.
- Independent reconciliation of sample fills against exchange statements during any live pilot.

Passing these tests proves specified behaviors under tested conditions, not absence of all bugs or market risk.

## 14. Resume checklist for the next work session

1. Read this plan and applicable workspace instructions; confirm the user wants implementation rather than further discussion.
2. Ask which crypto exchange accounts are available and confirm residence/product eligibility without requesting secrets in chat.
3. Confirm starting capital, allowed operating budget and spot-only scope. Do not assume historic FTMO/Exness authorization applies.
4. Recheck official repository health, releases, licenses, exchange docs and fee schedules because they change.
5. Create the uv project and dashboard skeleton (§16-§17) only after approval. Pin HftBacktest and ccxt first; assess Hummingbot connectors separately (outside the uv project) without enabling live trading.
6. Check historical depth availability and provenance. If unsuitable, prepare the read-only recorder and explain the collection period.
7. Freeze a BTC-only experiment specification, data schema and accounting convention.
8. Run data-quality and no-lookahead tests before any performance report.
9. Present raw Model A and Model B results separately, with costs, failure cases and evidence limitations.
10. Obtain explicit approval before authenticated trading, purchases, deposits, withdrawals or changes to the active Calyx system.

## 15. Source register

Sources reviewed for this plan on 2026-09-19. Repository default branches and prices can change; pin/recheck them before implementation.

1. BJF latency-arbitrage explanation: https://bjftradinggroup.com/latency-arbitrage/
2. BJF crypto product and license price: https://bjftradinggroup.com/sharptrader-crypto/
3. Hummingbot repository: https://github.com/hummingbot/hummingbot
4. Hummingbot release history: https://github.com/hummingbot/hummingbot/releases
5. Hummingbot arbitrage executor source: https://github.com/hummingbot/hummingbot/blob/master/hummingbot/strategy_v2/executors/arbitrage_executor/arbitrage_executor.py
6. Hummingbot executor documentation: https://hummingbot.org/strategies/v2-strategies/executors/
7. HftBacktest repository: https://github.com/nkaz001/hftbacktest
8. HftBacktest execution/replay limitations: https://hftbacktest.readthedocs.io/en/latest/order_fill.html
9. Cryptofeed repository: https://github.com/bmoscon/cryptofeed
10. Flashbots educational arbitrage example: https://github.com/flashbots/simple-arbitrage
11. Binance official WebSocket/order-book documentation: https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md
12. Ethereum smart-contract introduction: https://ethereum.org/developers/docs/smart-contracts/
13. Ethereum MEV/arbitrage explanation: https://ethereum.org/developers/docs/mev
14. Ethereum smart-contract security: https://ethereum.org/developers/docs/smart-contracts/security
15. Bybit fee reference; verify actual account rate: https://www.bybit.com/en-GB/help-center/article/Bybit-Spot-Fees-Explained?category=fab47a9a78e803e784
16. DigitalOcean instance prices: https://www.digitalocean.com/pricing/droplets

Added 2026-09-29 (cost re-plan):

17. Binance / Bybit / OKX spot fees and testnet/demo environments (comparison, verify on each venue): https://edge-ledger.io/blog/binance-vs-bybit-vs-okx-2026 and https://developers.binance.com/docs/binance-spot-api-docs/faqs/testnet and https://www.bybit.com/en/help-center/article/FAQ-Demo-Trading
18. DigitalOcean per-second billing and Droplet prices (re-checked): https://www.digitalocean.com/pricing/droplets
19. uv package manager: https://docs.astral.sh/uv/
20. Tailwind CSS standalone CLI (no Node.js needed): https://tailwindcss.com/blog/standalone-cli

## 16. Shared application platform (decided 2026-09-29; applies to Models A-E)

### 16.1 Stack

| Layer | Choice | Notes |
|---|---|---|
| Package/env manager | **uv** | `uv init`, `uv add`, `uv lock`, `uv run`. Python pinned in `.python-version` (3.12). `uv.lock` is committed; `.venv` is not. No pip/conda in this project. |
| Web/API | **FastAPI** + Jinja2 + Uvicorn | Server-rendered pages like the Calyx site; small vanilla JS or HTMX for live panels; WebSocket or SSE for live feeds. |
| Database | **SQLite** (for now) via SQLModel/SQLAlchemy 2 + Alembic migrations | WAL mode, `busy_timeout`, one writer queue per process. Can be swapped for Postgres later without rewriting models. |
| CSS | **Tailwind CSS** with the Calyx theme tokens | Built with the Tailwind standalone CLI (e.g. the `pytailwindcss` dev dependency via uv), so no Node.js toolchain is needed. The Calyx site uses the Tailwind CDN script; the lab builds a static CSS file instead. |
| Charts | TradingView Lightweight Charts (Apache-2.0) or inline SVG | Equity/balance curves, spreads, order-book depth. |
| Workers | Separate `uv run python -m workers.<name>` processes | One process per bot/recorder; supervised by a small launcher or Windows Task Scheduler / systemd on a server. |
| Alerts/control | Telegram bot | `/status`, `/pause`, `/kill`. Never accepts or displays key material. |
| Tests/lint | pytest, ruff (uv dev dependencies) | |

Indicative first dependency set (added only after implementation approval; pin versions when adding):
`uv add fastapi "uvicorn[standard]" jinja2 python-multipart sqlmodel alembic pydantic-settings httpx websockets cryptography keyring argon2-cffi pyotp itsdangerous ccxt polars pyarrow`
and `uv add --dev pytest ruff pytailwindcss`. Model-specific extras: `hftbacktest` (A/B); the official Polymarket CLOB
client, checked for CLOB V2 compatibility at build time (D); `solders`/`solana` (E).

Local run (after approval): `uv run uvicorn app.main:app --host 127.0.0.1 --port 8090`. Port 8090 avoids the EA store's
existing 8080 and other local tools; confirm the port is free first.

### 16.2 Process model

```text
 FastAPI dashboard (127.0.0.1:8090)  <--- admin browser (login, 2FA)
   | reads/writes config, keys (encrypted), modes, limits; reads ledgers
 SQLite  data/crypto_lab.sqlite  (WAL)
   ^ fills, paper ledger, heartbeats, alerts          ^ config + decrypted keys at start-up only
 workers: cex_recorder | cex_arb_shadow | poly_collector | poly_scanner | poly_copy_paper | sol_scanner | sol_rotation_paper | telegram_bot
```

- Workers poll a `bot_control` table (mode, pause, kill) every second. A kill sets mode OFF, cancels open orders and
  reconciles positions before the worker exits.
- A worker heartbeat older than N seconds shows red in the dashboard and triggers a Telegram alert.

### 16.3 What goes in SQLite vs files

| SQLite tables (app state) | Compressed files (high-frequency data) |
|---|---|
| `admin_user`, `session`, `api_credential` (encrypted), `wallet` (public address; secret only if burner, encrypted), `bot`, `bot_control`, `risk_limit`, `paper_order`, `paper_fill`, `live_order`, `live_fill`, `position`, `ledger_entry`, `opportunity` (Model A/D scanner hits), `wallet_profile` (Model D), `token_screen` (Model E), `alert`, `audit_log`, `cost_entry` (subscriptions + fees), `experiment`, `result_row` | Raw WebSocket messages and normalised order books/trades, partitioned by venue/pair/UTC date (Parquet + zstd, with checksums). SQLite stores only their manifest rows. |

### 16.4 Calyx theme for the dashboard

The theme is taken from the Calyx website source (`AAA EAs/EA store/templates/base.html` and `static/site.css`, which
render e.g. `https://calyx.duckdns.org/eas/xau-slow-trend?period=3y`). The **tokens and component classes are copied** into
the lab's own `static/`, so it never links the public site's CSS.

| Token | Value |
|---|---|
| `ink` (page background) | `#07100f` |
| `panel` | `#0b1715` |
| `mint` (primary accent) | `#7ef7c7` |
| `lime` (gradient start) | `#c4ff63` |
| `muted` text | `#8fa6a1` |
| `line` borders | `rgba(255,255,255,.10)` |
| Positive / warning / negative badges | `#9ff9d4` / `#f7d98e` / `#fca5a5` on 7% tints |
| Fonts | **Manrope** 400-800 (UI), **DM Mono** 400/500 (numbers, eyebrows, badges) |

Reused components: sticky blurred header with the Calyx logo mark; `eyebrow` labels (DM Mono, uppercase, 0.16em
tracking); `button-primary` (lime→mint gradient) and `button-secondary`; `terminal-card` / `product-card` panels (20-24px
radius, dark green gradient); `stats-strip` and `mini-stat` metric tiles; `chart-panel` for equity curves;
`evidence-controls` for period selectors (1y / 3y / 5y style); `badge-good|warn|bad|neutral`; the subtle noise overlay
and 56px grid hero. The layout mirrors the EA detail page: title + badges, a metric strip, the equity/balance chart with
period controls, then trade tables.

Every results view uses the standard Calyx research table: return %, PF, win rate, consistency score, average
win/loss streak, Sharpe, max balance DD, max equity DD, **trades, trades/month, trades/day**. It is labelled clearly as
PAPER, SHADOW or LIVE.

## 17. Admin dashboard (API keys, bots, risk)

### 17.1 Access and hosting
- Single admin account (more users later). Password hashed with **argon2id**; optional TOTP 2FA (`pyotp`).
  HttpOnly + SameSite=Strict session cookie; CSRF token on every form; login rate limiting and lockout.
- Bound to **127.0.0.1** by default. For remote use, go through a private network (e.g. Tailscale) or a reverse proxy
  with HTTPS and IP allow-listing. **Never** exposed on the public `calyx.duckdns.org` site.
- Every change is written to `audit_log` (who, when, what field; **never the secret value**).

### 17.2 API key vault
| Feature | Behaviour |
|---|---|
| Add / edit / rotate / disable / delete key | Per provider: Binance, Bybit, OKX, Kraken, Polymarket CLOB (L2 API creds), Kalshi (key id + RSA private key), Helius, Jupiter, Birdeye, Etherscan, Telegram bot token, Anthropic. Fields: label, environment (**testnet / demo / paper-data / live**), created, last rotated, expiry reminder. |
| Storage | Encrypted at rest (AES-GCM via `cryptography`). The master key comes from the Windows Credential Manager / OS keyring (`keyring`) or a server secret, never from the repo, the SQLite file or `.env` in Git. |
| Display | Write-only: after saving, only the provider, label and last 4 characters are shown. There is no "reveal" or export endpoint. |
| Test connection | A read-only call (balance or permission endpoint) that reports OK or FAIL without printing the secret. Where the venue exposes key permissions (e.g. Binance API restrictions), it **blocks live mode if withdrawals are enabled** and shows whether an IP whitelist is set. |
| Wallet keys (Polymarket signer, Solana burner) | Public address stored in plain text. The private key is only for **dedicated burner wallets** and uses a *separate* passphrase entered at worker start (held in memory, not persisted in plain text). The UI never shows it again. The main wallet is never entered. |
| Logs | Secrets are redacted by a logging filter; tests check that no key string appears in logs, HTML or API responses. |

### 17.3 Bot and risk control pages
- **Bots:** one card per worker (Model A/B/D/E), with mode **OFF → SHADOW → PAPER → LIVE**, heartbeat, last error, and
  pause / kill buttons. LIVE stays locked until the model's paper gate is marked passed, and then needs a typed
  confirmation plus the 2FA code.
- **Risk limits** (per bot, stored in SQLite, read by workers): max per trade, max open positions, daily loss stop,
  max trades per hour, max slippage, max price deviation for copy trades, kill switch.
- **Ledgers:** paper and live orders, fills, fees, positions and equity curve, in the Calyx theme, with CSV export
  (no secrets).
- **Costs:** subscriptions (Helius, Jupiter, server, etc.) plus fees paid, compared with P/L, so the net business
  result is visible.
- **Research:** the standard results table per experiment, with dev / validation / holdout labels and trades/month/day.

### 17.4 Build order (after approval)
1. uv project skeleton, settings, SQLite + Alembic, admin login + 2FA, audit log, Calyx-themed base template.
2. Key vault + "test connection" for public/testnet keys only.
3. Bot control table + one worker (the Model D read-only collector or the Model A recorder) + heartbeat page.
4. Paper ledgers and results pages; Telegram alerts.
5. Live mode stays disabled in code until a model passes its gate **and** the user approves amount and venue.

**Final principle:** reuse established infrastructure, measure the execution edge, protect keys and capital, and be willing to stop if the real economics do not work.
