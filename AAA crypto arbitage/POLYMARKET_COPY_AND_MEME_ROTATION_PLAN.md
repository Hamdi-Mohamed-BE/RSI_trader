# Polymarket Wallet-Copy Bot & Meme-Coin Rotation Bot — Recreation Plan

Created: 2026-09-29 · Re-planned 2026-09-29: **FastAPI + SQLite + Tailwind (Calyx theme) + uv**, with an admin
dashboard for API keys; cost and paper-trading table in §6.
Status: **Model D in development** in `crypto-lab/` (scanner + wallet tracker working in shadow/paper; see `crypto-lab/progress.md`). Model E: plan only.
Original status: **PLAN ONLY** — nothing installed, no accounts, keys, wallets, deposits or orders.
Workspace: `C:\Users\hama101\Desktop\geek\ai trader\AAA crypto arbitage`
Related: `CRYPTO_ARBITRAGE_MASTER_PLAN.md` (BTC cross-exchange / latency arbitrage, Models A–C).
These two projects are added as **Model D** and **Model E** alongside the master plan's Models A–C. All five models
share **one** uv project, one SQLite database and one Calyx-themed admin dashboard, specified in the master plan
**§16 (platform) and §17 (admin dashboard / key vault)**. This file covers only what is specific to D and E.

---

## 0. Sources and what they actually prove

| Post | Claim | What is verifiable |
|---|---|---|
| X @Amelia_With_Ai, 2026-09-28 (status 2104384699716296801) | Claude built a Polymarket "monitoring terminal" that scans undervalued markets, profiles 500–1,000+ wallets, finds arbitrage wallets and copies 7 of them via a Telegram copy-trading bot; "$2K → $11K overnight", "70% hit rate" | Nothing. No wallet address, no trade list, no code. The post asks readers to comment/like/RT/follow to "get it" (engagement funnel); a reply calls it spam/manipulation. |
| X @laoyingkhq, 2026-09-28 (status 2104446373211127963, Chinese) | Grok given $50, 12 meme coins, "6 agents"; rotated on GMGN; "$50 → $3,532 in 4 min 14 s", 99 fills, 82% win rate, $104 fees | Nothing. Contains a GMGN **referral link**; a reply notes "no wallet, no tx hashes, no explorer link — that's a dashboard, not a trade history". |

Treat both as **marketing that describes a real idea**, not as performance evidence. Never use their links, code
offers or referral codes. Success for us = measured net edge after fees, latency and slippage, not screenshots.

---

## 1. Model D — Polymarket wallet intelligence, arbitrage scanner & copy-trading

### 1.1 What we would actually build
1. **Market data collector** (read-only): Polymarket public APIs — Gamma (market/event metadata), CLOB (order books,
   prices, trades), Data API (positions/activity per wallet) — plus Polygon on-chain data (block explorer API or a
   subgraph) for independent verification of fills. Market/wallet metadata, trades and scanner hits go to **SQLite**;
   high-frequency order-book snapshots go to compressed files indexed from SQLite (master plan §16.3).
2. **Arbitrage scanner** (alerts only first):
   - D1 *Complement*: YES best ask + NO best ask < $1.00 − fees/slippage buffer (buy both, hold to resolution).
   - D2 *Multi-outcome*: sum of YES asks across mutually exclusive outcomes < $1.00 (or sum of bids > $1.00).
   - D3 *Logical constraints*: related markets that must be consistent (A ⊂ B ⇒ P(A) ≤ P(B)); flag violations.
   - D4 *Cross-venue*: the same event on Polymarket vs **Kalshi** (reuse the `AAA BTC JEV` Kalshi BTC repo's API and
     paper-mode knowledge); needs identical resolution rules, both fees, and capital on both venues.
   - Every opportunity is priced at **executable depth** for a fixed size, not the top-of-book quote.
   - Fees matter a lot here. The Polymarket taker fee is `shares × rate × p × (1−p)`, with rate 0.07 for crypto, 0.05 for
     sports/economics/culture, 0.04 for politics/finance/tech and 0 for geopolitics; makers pay 0. Buying both YES and NO
     at about 50¢ as a taker in a crypto market costs about **3.5¢ per $1 pair**, so D1 needs YES + NO < about $0.965
     there (≤ $1.00 minus slippage in fee-free categories).
3. **Wallet profiler / leaderboard**: for every active wallet — realised P/L, win rate with confidence interval,
   consistency by week, market categories, typical size, holding time, entry timing vs price moves, and whether its
   positions are hedged pairs (a real arbitrageur) or directional bets. Flag wash-trading and sybil clusters.
4. **Copy engine (paper first)**: watch selected wallets, mirror new positions with configurable delay, max price
   deviation from the source fill, liquidity filter, per-trade and per-market caps, and skip rules. Paper ledger with
   simulated fills from the recorded order book.
5. **Telegram bot**: alerts (new arbitrage, copied trade, fill, P/L), `/status`, `/pause`, `/kill` — control only,
   no key material over Telegram. Check first whether the repo's existing Telegram-copy work (branch
   `new-telegram-copy`) can be reused rather than rebuilt.
6. **Dashboard** (FastAPI + Jinja2 + Tailwind in the Calyx website theme, master plan §16.4): pages for the wallet
   leaderboard (sortable, with confidence intervals), scanner feed (D1–D4 with fee-adjusted edge), copied wallets, paper
   positions and equity curve (standard results table with trades/month/day), and the market browser. Admin pages
   (master plan §17) hold the Polymarket CLOB credentials, the signer wallet address, Kalshi key, Etherscan/RPC keys and
   the Telegram token, plus copy-engine risk limits and the OFF/SHADOW/PAPER/LIVE switch.
7. **LLM layer (optional, off the execution path)**: Claude summarises wallet behaviour and writes weekly research
   notes; it never signs, sizes or sends orders.

### 1.2 The core problem to test honestly
Copying **arbitrage** wallets is structurally late: true arbitrage closes in seconds, so a copy that arrives after the
source's fill usually pays the corrected price. Copying **directional** "smart money" is a different bet with
survivorship bias (yesterday's top wallets are selected *because* they were lucky). The plan tests both separately.

### 1.3 Validation protocol
- Wallet selection **walk-forward**: rank wallets on days t−60…t−1, copy them on days t…t+30, roll forward; never
  rank and evaluate on the same period.
- Copy delays of 2 s, 10 s, 60 s, 5 min against recorded books; fees and slippage from real depth.
- Arbitrage scanner: count opportunities that were still executable at our modelled latency and size.
- Report per strategy: trades, trades/month/day, return, win rate, PF, consistency, streaks, Sharpe, max DD,
  capital locked until resolution, and time-to-resolution.
- Gate before any money: positive after costs in ≥ 2 of 3 walk-forward folds, enough trades (≥ 100), and a
  delay-stress that stays positive at the realistic latency.

### 1.4 Compliance and account questions (must be answered first)
- Polymarket's terms restrict some jurisdictions (historically including the US on its main international venue);
  confirm the user's country and the current terms before creating any account. Kalshi likewise has its own
  eligibility rules.
- KYC, USDC funding route, tax treatment of prediction-market P/L.
- Copy-trading another wallet is legal to observe on-chain data, but automated trading must respect each venue's API
  terms and rate limits.

---

## 2. Model E — multi-agent meme-coin rotation bot (Solana)

### 2.1 What we would actually build
Six "agents" as ordinary services (deterministic code; an LLM is optional and never in the trade path):
1. **Scanner** — new/active meme tokens from DEX data APIs (e.g. DEX Screener, Birdeye, Jupiter quotes; Solana RPC
   provider such as Helius/QuickNode) with liquidity, volume, age and holder data.
2. **Risk / rug filter** — mint and freeze authority revoked, LP burned/locked, top-holder concentration, honeypot
   sell-simulation via a quote for the reverse swap, dev-wallet activity, blacklists.
3. **Signal** — short-term relative-strength rotation within a small basket (e.g. 12 tokens): rotate into the strongest
   momentum with volume confirmation, out on reversal or time stop.
4. **Execution** — Jupiter swap routes with strict slippage caps, priority-fee model, MEV-protected submission
   (e.g. Jito bundles) — **paper mode first** using live quotes as fills.
5. **Portfolio / risk manager** — max position per token, daily loss limit, kill switch, max trades/hour.
6. **Journal** — every decision, quote, fill, fee and reason logged to SQLite for replay and review.

Model E dashboard pages (same Calyx theme): token screener with the rug-filter checklist per token, rotation basket,
paper positions and equity curve, cost breakdown (swap fees + priority fees + Jito tips vs gross P/L) and the rug/honeypot
event log. Admin: Helius/Jupiter/Birdeye keys, the burner wallet **address**, and limits (max per token, daily loss,
max trades/hour, max slippage bps).

### 2.2 The core problem to test honestly
DEX swap fees (~0.25–1% per swap), priority fees, slippage and MEV make very fast rotation expensive: the post's
"99 fills in ~4 minutes" would pay roughly 50–200% of capital in costs at small size unless the edge per trade is
enormous. Meme tokens also carry rug-pull, honeypot and liquidity-disappearance risk that no win rate captures.

### 2.3 Validation protocol
- Record live quotes and on-chain swaps for a basket for several weeks (read-only), then **replay** the rotation rules
  with fees, slippage from quote depth and a latency model.
- Live **paper** trading for ≥ 4 weeks using real Jupiter quotes as fills.
- Report the standard table (trades, per month/day, return, PF, win rate, consistency, streaks, Sharpe, max DD) plus
  cost share of gross P/L and every rug/honeypot event encountered.
- Gate: positive after all costs over the paper period with costs < 50% of gross profit; zero unhandled rug events.

### 2.4 Security rules (non-negotiable)
- A **separate burner wallet** only, funded with a small, explicitly approved amount; never the main wallet.
- Private keys never in the repository, logs, Telegram or chat; stored in the OS key store / environment only.
- No third-party "free bot", referral site or copy-paste contract from social media; no signing of unknown transactions.
- Withdrawal and allowance limits reviewed before any live pilot.

---

## 3. Shared phases and go/no-go gates

| Phase | Deliverable | Gate to continue |
|---|---|---|
| 0 | Compliance/eligibility check (Polymarket, Kalshi, Solana DEX use in the user's country); budget decision | User approval |
| 1 | Read-only collectors + local DB (Polymarket/Kalshi data; Solana quotes/swaps) | Clean, gap-free data for ≥ 2 weeks |
| 2 | D: arbitrage scanner alerts + wallet leaderboard. E: rug filter + signal replay | Opportunities survive realistic latency/costs |
| 3 | Paper trading (copy engine / rotation bot) with Telegram alerts and dashboard | Gates in §1.3 / §2.3 |
| 4 | Tiny live pilot, hard caps, kill switch, burner wallet / small venue balance | **Explicit user approval of amount and venue** |
| 5 | Scale or stop, based on live vs paper reconciliation | Live results within the paper range |

## 4. Reuse from existing work
- `AAA BTC JEV` (Kalshi BTC bot): paper-mode design and Kalshi API access for D4. It already uses uv
  (`pyproject.toml` + `uv.lock`), so its dependency conventions can be copied. The new dashboard uses the Calyx website
  theme, not the Kalshi UI styling.
- `AAA EAs/EA store` (the Calyx website source): design tokens and component classes (`static/site.css`, `templates/base.html`),
  copied into the lab, not linked.
- Calyx research habits: rules fixed before testing, controls, walk-forward, standard results table, no deployment
  without approval (`AAA EAs/BM Trading Robust Sets 2026-08-04/PIPELINE.md`).
- Existing Telegram-copy work on the `new-telegram-copy` branch — inspect before building a new Telegram layer.

## 5. Open decisions for the user
1. Which first: Model D (Polymarket) or Model E (meme rotation)? Recommended: **D first, read-only**, because its
   arbitrage checks are measurable and it builds on the Kalshi work; E carries the highest loss/scam risk.
2. Country/eligibility for Polymarket and Kalshi.
3. Research budget for data/RPC providers (free tiers first; see §6).
4. Whether any LLM (Claude) involvement is wanted beyond research summaries.
5. Where the dashboard runs: local PC only (default, 127.0.0.1) or a private server (Tailscale/VPN), never the public
   Calyx site.
6. Whether to start the shared uv/FastAPI skeleton + admin key vault (master plan §17.4, steps 1–3) as the first
   implementation task.

## 6. Expected initial cost per API key, and paper trading (checked 2026-09-29)

Prices change; re-verify before paying. The platform/dashboard itself (FastAPI, SQLite, Tailwind, uv) costs **$0**.
It runs on the local PC at first, or shares one server with Models A/B (master plan §11: $24–$42/month).

### 6.1 Model D — Polymarket (+ optional Kalshi for D4)

| Service | Key? | Key / subscription cost | Per-trade cost | Paper trading? |
|---|---|---|---|---|
| Polymarket Gamma, CLOB (books/prices) and Data API (wallet positions/activity) — public reads | No | $0 | — | Recorded real books are the input for paper fills |
| Polymarket CLOB trading credentials (L1 wallet signature → L2 API creds) | Yes; derived from a wallet | $0 to create. Needs a wallet funded with USDC. There are no Polymarket deposit/withdrawal fees; intermediaries may charge. | Taker: `shares × rate × p × (1−p)`, rate 0–0.07 by category (100 crypto shares at 50¢ = **$1.75**; politics **$1.00**; geopolitics **$0**). **Makers pay 0.** | **Yes, but simulated only.** No official testnet/sandbox was found, so paper = simulated fills against recorded live order books (same as the copy-delay tests in §1.3). |
| Polymarket builder/relayer tier | Optional | $0 (unverified tier: 100 relayer tx/day; verified 10,000/day) | — | — |
| Kalshi API (D4 cross-venue) | Yes (key id + RSA key) | $0 | Taker ≈ `0.07 × C × P × (1−P)` rounded up to the cent (about 1.75¢ per contract at 50¢ on standard series); makers 0 on most series | **Yes**: free **demo environment with mock funds** (`demo.kalshi.co`). Demo prices may not match real markets, so economics still come from recorded real books. |
| Etherscan API V2 (Polygon fill verification) | Yes | **$0** free tier: 5 calls/s, 100k/day, Polygon included | — | — |
| Polygon RPC (Alchemy/Infura/public) | Yes (free tier) | $0 at research volume | — | — |
| Telegram bot | Token | $0 | — | — |
| Claude API (optional wallet summaries) | Yes | Usage-based, a few dollars a month for weekly notes | — | — |

**Model D initial cost:** **$0/month** for phases 1–3 (collector, scanner, wallet profiler, paper copy engine). A
live pilot (phase 4, only with explicit approval) adds the capital you choose, e.g. **$100–$300 USDC**, plus the same
amount on Kalshi if D4 is used. Jurisdiction eligibility must be confirmed first (§1.4).

### 6.2 Model E — Solana meme rotation

| Service | Key? | Key / subscription cost | Per-trade cost | Paper trading? |
|---|---|---|---|---|
| DEX Screener API | No | $0 (rate-limited) | — | — |
| Helius RPC / webhooks | Yes | **Free**: 1M credits/month, 10 RPS → **Developer $49/month**: 10M credits, 50 RPS (Business $499) | — | — |
| Jupiter swap/quote API | Yes (developer platform) | **Free $0**: 1 req/s → **Developer $25/month**: 25M credits, 10 req/s (Launch $100, Pro $500) | Route/DEX pool fees, usually about 0.25–1% per swap on meme pools | **Yes**: live Jupiter quotes used as paper fills. Devnet has no real meme liquidity, so it is only for code tests. |
| Birdeye Data API | Yes | Standard free; Starter about $99, Premium about $199, Business about $699/month (from Birdeye's pricing page via search; the page blocked direct fetch). **Optional**: avoid until free sources prove insufficient. | — | — |
| Solana network + priority fees + Jito tips | No key | — | Base 5,000 lamports per signature (a fraction of a cent) + priority fee + optional Jito tip, on **every** swap | Modelled in paper mode |
| Burner wallet | Keypair | $0 | — | Paper mode needs no funded wallet |

**Model E initial cost:** **$0/month** on free tiers for scanner + rug filter + paper rotation. The realistic step-up
when the free rate limits bind is Helius Developer $49 + Jupiter Developer $25 = **$74/month**. A live pilot (only
after the §2.3 gate **and** explicit approval) uses a burner wallet with e.g. **$50–$100**, all at risk.

### 6.3 Summary — what it costs to start

| Project | Paper trading first? | Initial monthly cost (paper phase) | Step-up if limits bind / server | Live pilot capital (approval required) |
|---|---|---:|---:|---:|
| A/B CEX arbitrage (master plan) | **Yes** — shadow on real books; Binance/Bybit/OKX testnets for plumbing | $0 local | $24–$52/month server | $500–$1,000 |
| D Polymarket copy + arbitrage | **Yes (simulated)** — no Polymarket sandbox; Kalshi has a mock-funds demo | $0 | +$6–$24/month if moved to a server | $100–$300 USDC (+ Kalshi if D4) |
| E Solana meme rotation | **Yes** — live Jupiter quotes as fills | $0 | $74/month (Helius Dev + Jupiter Dev) | $50–$100 burner wallet |

One shared server can host all workers and the dashboard. None of these amounts is a return forecast.

Sources (checked 2026-09-29): [Polymarket fees](https://docs.polymarket.com/polymarket-learn/trading/fees) ·
[Polymarket builder tiers](https://docs.polymarket.com/builders/tiers) ·
[Kalshi demo environment](https://docs.kalshi.com/getting_started/demo_env) ·
[Kalshi fee schedule](https://kalshi.com/docs/kalshi-fee-schedule.pdf) ·
[Etherscan API limits](https://docs.etherscan.io/etherscan-v2/rate-limits) ·
[Helius pricing](https://www.helius.dev/pricing) · [Jupiter pricing](https://developers.jup.ag/pricing) ·
[Birdeye Data pricing](https://birdeye.so/data-api/pricing)

## 7. Not financial advice
This is a software and research plan. Nothing here is a recommendation to trade or a forecast of returns; social-media
return claims in §0 are unverified.
