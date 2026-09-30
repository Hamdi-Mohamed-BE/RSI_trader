# Prop Challenge Simulator — Plan

Created: 2026-09-29 · Updated: 2026-09-29 (owner decisions, SET audit, prop-firm registry) · Status: **IMPLEMENTED on the local dev site (2026-09-29), not published** — see "Implementation status" at the end.
Target: new section of the Calyx website (`AAA EAs/EA store`, FastAPI + Jinja2 + Tailwind), e.g. `/prop-simulator`.

## 0. Owner decisions (2026-09-29)

| # | Question | Decision |
|---|---|---|
| 1 | Which prop firms? | **As many as possible that allow EAs on MT5.** Rules are stored as data, with a firm registry (§11) and generic rule components (§12). |
| 2 | Public or gated? | **Public page for all visitors**, so the §6 limits (validation, caps, rate limit, caching) are mandatory. |
| 3 | EA universe | **The user picks any list of EAs and their risk per trade.** The suggestion engine searches all compatible site EAs (currently 37). |
| 4 | Suggestion objective | **All three**, side by side: best expected value, highest pass-both rate and fastest median pass. |
| 5 | News EAs | **Included** wherever the firm or programme allows news trading. Blocked or rule-adjusted where it doesn't (§12). |
| 6 | Native FTMO-SET MT5 tests | **Authorised** (isolated tester only). The Phase 0 audit (§13) shows they are needed only as an optional guard/sizing check, not for strategy logic. |

## 1. Goal

A visitor picks one EA or a combination of EAs, chooses a prop-firm programme and a risk policy, and gets:

- simulated **likelihood of passing Phase 1**, **Phase 2 (given Phase 1)**, and **both**;
- how accounts fail (daily-loss breach vs max-loss breach vs not finished in the horizon);
- **days to pass** (median and range);
- **expected payouts** in the funded stage (after the profit split, minus the challenge fee);
- the standard statistics of the selected combination: trades, **trades/month, trades/day**, return %, **PF**, **win
  rate**, **Sharpe**, consistency, **average and maximum win/loss streaks**, max balance DD, max equity DD, worst day,
  and correlation between the chosen EAs.

By default the page opens on a **suggested combination and risk policy**. The user can then change EAs, risk per
trade and guards, and re-run.

## 2. What already exists (reuse, don't rebuild)

| Asset | Where | Use |
|---|---|---|
| Native MT5 trade lists for **all 37 site EAs**, incl. all **13 FTMO-package EAs**, for 6m / 1y / 3y / 5y (open/close time, net P/L incl. costs, volume, `estimated_r`) | `data/evidence-cache/v1/products/<slug>/<mode>/<period>.trades.json` | Input ledger for every simulation |
| Site trade metrics (streaks, R estimates) | `app/trade_metrics.py` | Stats for the selected combo |
| Portfolio Monte Carlo (single fixed combination) | `_portfolio_monte_carlo()` in `app/main.py`, portfolio cache | Pattern for cached, precomputed results |
| Research prop engines with FTMO / FundedNext rule logic, minute equity, payout milestones, block bootstrap | `BM Trading Robust Sets 2026-08-04/Bruni Statistical Models Raw 2026-09-28/prop_engine.py`, `Conte Research Basket Raw 2026-09-28/prop_sim.py`, `PROP_PROTOCOL.md` | Rule reference and **golden cross-check** for the new engine |
| FTMO 13-EA package (EAs, SETs, $50 planned risk, News OFF) | `FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json` | "Saved FTMO package" preset |
| FTMO symbol specs (contract size, commission, leverage) | `Daily Equity Controls Audit 2026-09-29/FTMO_SPECS.json` | Lot rounding, min lot, costs |
| −2% daily equity stop / +4% daily profit close comparison | `Daily Equity Controls Audit 2026-09-29/` | Validation target for the daily-guard option (**tested, not installed**) |

Important data gap: the site caches are at the **site's settings** (mode `standard`, `safe`, `dynamic`, about 1% risk),
not the FTMO SETs (0.5% / fixed $50, News OFF). Rescaling each trade by its R handles a different risk size, but not
different logic inputs. Phase 0 therefore audits, EA by EA, that the FTMO SET differs from the cached mode **only** in
risk. Any EA that differs in logic needs native tests of its FTMO SET before its numbers are shown under the FTMO
preset.

## 3. User flow and inputs

1. **Programme preset**, with rules stored as data (source URL and verified date shown on the page):
   - FTMO 2-Step **Standard** and **Swing** (first); later FundedNext, The5ers and 1-step variants.
   - Fields: account size, fee, Phase 1 / Phase 2 targets, daily-loss % and its reference (day-start balance or
     equity, reset time zone), max loss (static or trailing), minimum trading days, time limit, weekend/news
     restrictions, profit split, payout cadence, first-payout fee refund.
   - The "custom" preset makes every field editable.
2. **EAs:** a multi-select of site EAs. Presets: *Suggested*, *Saved FTMO 13 package*, *single EA*, *custom*.
   Each EA shows market, timeframe, version and compatibility badges:
   - "holds over the weekend" (Swing only);
   - "trades news";
   - "no hard stop".
3. **Risk policy:**
   - risk per trade: % of balance or fixed $ (default for the FTMO preset: $50 on $10k);
   - optional weight per EA;
   - lot rounding: **down** (the FTMO launcher's rule), or up (the normal portfolio rule, which is shown as oversizing);
   - maximum simultaneous open risk;
   - maximum entries per day;
   - daily guard: stop new entries after −X% on the day;
   - optional **−2% daily equity stop / +4% daily profit close**;
   - option to halve risk after a Phase 1 pass or after N losses.
4. **Evidence and sampling:**
   - window: 1y / 3y / 5y (default 3y);
   - sampling method: calendar-block bootstrap (default) or historical rolling start dates;
   - number of paths (default 2,000; maximum 10,000);
   - seed;
   - horizon (60 / 120 / 180 / 365 days).

## 4. Simulation method

### 4.1 Build the combined ledger
- Load each chosen EA's cached native trades for the window, and convert each trade to **R** (net P/L ÷ planned risk
  at entry, using the cache's `estimated_risk_cash`).
- Re-size to the user's risk: P/L = R × risk $ (balance-based or fixed).
- Derive the stop distance (planned risk ÷ volume × contract value), then apply symbol **minimum lot and lot step**
  from the FTMO specs. A trade whose rounded lot is 0, or exceeds the risk cap when rounding up, is **skipped and
  counted**, never forced.
- Keep open/close timestamps, so overlapping positions across EAs are real overlaps from history.

### 4.2 Sample paths while keeping cross-EA correlation
- **Calendar-block bootstrap on the combined ledger:**
  - resample whole 28-day (or 7-day) calendar blocks, so all EAs move together and correlation is preserved;
  - keep zero-trade days and the order of trades within each block;
  - a block cannot start while a trade from the previous block is still open.
- **Historical rolling starts:** every weekly start date in the window, played forward. This is shown next to the
  bootstrap as a sanity check.

### 4.3 Apply the programme rules to each path (event loop by day and trade)
- **Balance** updates on trade close.
- **Equity for the daily and max-loss checks:** the site caches have no intratrade equity path. The fast Level 1 engine
  therefore uses a conservative envelope: every position open during the day is assumed to reach its full stop
  (−1R) at the worst moment of that day. A breach is recorded if `day-start reference − worst equity ≥ daily limit`,
  or if `worst equity ≤ max-loss floor`. This overstates breaches for trades that never went near their stop, and it
  is labelled *conservative*. Trades without a hard stop use their emergency stop, or they are flagged and excluded
  from the FTMO preset.
- **Phase logic:**
  - target reached on closed balance with at least the minimum trading days, then the next phase starts;
  - model a handover delay (default 2 business days after Phase 1, 5 after Phase 2);
  - funded stage: payouts on the firm's cadence, with the split, first-payout fee refund and minimum amount;
  - a breach ends the account.
- **User guards** (daily stop, profit close, open-risk cap, entries per day) are applied *before* each entry. They are
  entry filters, not intratrade liquidation, which matches how the EAs and the FTMO guard work.
- **Level 2 (optional, later):** reuse the research minute-equity engine for curated combinations (the suggested
  combo and the FTMO 13 package), and show its result as "minute-equity check" next to Level 1.

### 4.4 Outputs per run
- Pass Phase 1 %, pass Phase 2 % (given Phase 1), pass both %; breach % by cause; unresolved %.
- Days-to-pass distribution for each phase.
- **Funded:** probability of at least 1 payout within 3 / 6 / 12 months, expected number of payouts, expected payout $
  after the split, and **expected value = E[payouts] − fee + E[refund]**, with a 5th–95th percentile range.
- **Combo statistics** from the plain historical merged ledger at the chosen risk (not the bootstrap): trades,
  trades/month, trades/day, return %, PF, win rate, Sharpe, consistency, average and maximum win/loss streaks, max
  balance DD, max equity DD (**n/a** at Level 1; missing ≠ zero), worst day, monthly returns and the EA correlation
  matrix.
- **Charts:**
  - equity fan chart (median and 5th–95th percentile);
  - histogram of pass days;
  - pie of breach causes.
- A table of skipped trades and why (minimum lot, guard, open-risk cap), so the user can see what the risk policy
  changed.

## 5. Suggested combination and risk (the default)

- **Search space:** the EAs compatible with the programme × risk per trade (0.25–1.0% in 0.125% steps, or $25–$100) ×
  a few guard presets (none / daily −2% stop / −2% stop plus +4% close).
- **Objectives:** show **three suggestions side by side** (owner decision), each with its own EAs, risk and guards:
  **best expected value**, **highest pass-both rate** and **fastest median pass**. Each is subject to:
  - breach probability ≤ 35%;
  - at least 20 trades a month;
  - no single EA above 30% of total risk.
- **Search method:**
  1. screen all subsets with a fast proxy (Level 1 at 300 paths, greedy forward selection plus swap moves);
  2. re-run the top 20 candidates at 5,000 paths;
  3. re-check the winner at Level 2.
- **Overfitting guard (mandatory):** choose the combo on the **development window** (for example years 1–4 of the 5y
  data), then report its numbers on the **untouched final year** next to the in-sample numbers. Monte Carlo on the
  chosen version is required, per `PIPELINE.md`. The page shows both, labelled "selected on" and "tested on".
- The search is computed **offline** (a nightly or on-demand precompute script), not on each page load. The page
  shows the cached suggestion with its timestamp and an "Apply" button that loads it into the form.

## 6. Architecture (website)

```text
app/prop_sim/
  rules.py        # ProgrammeRules dataclass + presets (JSON in data/prop-rules/*.json with source URL + verified date)
  ledger.py       # load cached trades -> R ledger; risk re-sizing; lot rounding from symbol specs; skip reasons
  sampling.py     # calendar-block bootstrap (combined ledger), rolling historical starts; seeded RNG
  engine.py       # vectorised numpy phase/breach/payout simulation (Level 1); returns raw path outcomes
  metrics.py      # pass/breach/payout aggregation + standard combo stats (reuses trade_metrics)
  optimizer.py    # offline suggested-combo search with dev/holdout split
  service.py      # cache by config hash, run limits, job queue (reuse evidence_jobs pattern)
templates/prop_simulator.html   # form + results in the Calyx theme
static/js/prop-simulator.js     # form state, submit, render charts (no inline scripts)
tools/precompute_prop_suggestions.py
tests/test_prop_*.py
```

- **API:**
  - `GET /prop-simulator` (page);
  - `POST /api/prop-sim/run` (validated JSON config → result, or a job id);
  - `GET /api/prop-sim/jobs/{id}`;
  - `GET /api/prop-sim/suggested?programme=…`.
- **Public-site safety:**
  - inputs validated against whitelists (EA slugs, presets, ranges);
  - path count and horizon capped;
  - per-IP rate limit and a time-out;
  - results cached by config hash;
  - no user data stored.
- **Performance target:** 13 EAs × 3y × 2,000 paths in under about 3 s on the server (numpy, daily loop); heavier runs
  go to the job queue.

## 7. Validation before launch

1. Unit tests for the rules:
   - breach exactly at the thresholds;
   - daily reset time zone;
   - minimum trading days;
   - phase transitions and handover delay;
   - payout cadence, split and refund;
   - lot rounding and skip counting.
2. **Golden test:** run the FTMO 13 package config through the new Level 1 engine and compare it with the research
   `prop_engine.py` output on the same window. Level 1 must be *at least as conservative*: equal or lower pass rate,
   equal or higher breach rate. Document the gap.
3. Reproduce the site's existing single-portfolio stats (PF, win rate, trades) from the merged ledger, and check they
   match the cached portfolio summary.
4. Reproduce the −2% / +4% daily-control comparison from the Daily Equity Controls Audit.

## 8. Honesty, compliance and wording (public page)

- Wording: "**simulated frequency**" or "historical-scenario pass rate", never "your chance to pass" and never a
  guarantee. Show the evidence type, the window and that it is an **arithmetic overlay of separate native MT5 tests**,
  not a simultaneous shared-margin run.
- Show that the Level 1 equity check is conservative and that intratrade drawdown is modelled, not recorded.
- Rules have a "verified on" date and link to the source; the firm's current terms override.
- **FTMO wording:** use "FTMO-style 2-Step rules" and state "not affiliated with or endorsed by FTMO". Put the same
  disclaimer on every firm preset.
- **Compatibility warnings:** weekend/overnight holders (Nasdaq Overnight, Nasdaq 5M) need a Swing-type account; news
  EAs are off by default under FTMO presets; the pre-news straddle is not certified under any firm's rules.
- The pipeline rules apply: backtest return is not forecast return, and the suggested combo is research output, not
  a deployment instruction.

## 9. Phases

| Phase | Work | Estimate |
|---|---|---|
| 0 | Re-verify current FTMO 2-Step Standard/Swing rules (official pages); write rule JSON. Audit FTMO SET vs cached mode for the 13 EAs; list EAs needing native FTMO-SET tests | 1–2 days |
| 1 | `ledger`, `sampling`, `engine`, `metrics` + unit tests + golden cross-check | 3–4 days |
| 2 | API, validation, caching, job queue, rate limit | 1–2 days |
| 3 | Page and charts in the Calyx theme; presets; skipped-trade table; disclaimers | 2–3 days |
| 4 | Offline optimizer with dev/holdout split + Monte Carlo; "Suggested" preset | 2–3 days |
| 5 (optional) | Level 2 minute-equity check for curated combos via the research engine | 3–5 days |
| 6 | Review, then the owner publishes the website update (no automatic publish) | — |

## 10. Remaining open points

The earlier questions are answered in §0. Still open:
1. **Fee data:** fees and promotions change often. Default to each firm's list price at verification time, and let
   the user edit the fee (expected value depends on it).
2. **Account currency:** start with USD accounts only.
3. **Refresh cadence** for the firm registry: proposed monthly, plus a "rules may have changed" banner after 45 days.

## 11. Prop-firm registry (seed list; each programme is verified on its official page in Phase 0)

Our EAs are **MT5 CFD** EAs, so a firm qualifies only if it offers **MT5 with EAs allowed** and lists our symbols
(XAUUSD, US100/USTEC, USDJPY, XAG, BTC/ETH, EURUSD).

| Firm | EA policy (from 2026 comparison sources; to be re-verified) | Programmes to model | Notes |
|---|---|---|---|
| **FTMO** | Allowed unless a forbidden practice (HFT, e.g. >2,000 server requests/day; latency arbitrage; tick scalping) | 2-Step Standard, 2-Step Swing, 1-Step | Official page checked 2026-09-29: 2-Step 10%/5%, 5% daily from 00:00 CE(S)T, 10% static, 4 trading days. 1-Step: 10% target, 3% daily, 10% EOD-trailing max loss, best-day ≤ 50% of positive-day profit |
| **FundedNext** | Allowed within prohibited strategies (HFT, latency, tick scalping, grid); Quick-Strike 30 s rule; news-window profit split rules | Stellar 2-Step, Stellar 1-Step, Stellar Lite, Stellar Instant | The Stellar Instant rules are already modelled in the research `PROP_PROTOCOL.md` |
| **The5ers** | Allowed; own source code; no HFT, rollover-night scalping, third-party or copy EAs | High Stakes (2-step), Hyper Growth, Bootcamp | High Stakes: 5% daily, 10% max, unlimited time (per comparison source) |
| **E8 Markets** | Allowed, incl. martingale; one strategy per user; ≤ 50% of trades under 1 min; 2,000 requests/day; lot caps | E8 One, E8 Classic/Track | Straddling banned, which blocks the News Pulse pre-news straddle |
| **FXIFY** | EAs need **written pre-approval**; instant accounts ban EAs | 1/2/3-phase | Flag "pre-approval required" |
| **Goat Funded Trader** | Allowed if compliant; no third-party or pass-assessment EAs; funded trades < 2 min count as zero profit | 1/2-step | Hold-time rule matters for scalpers |
| **Audacity Capital** | Allowed; no third-party signals; MT5 | Funded / challenge programmes | Static drawdown model |
| **FundingPips** | **Restricted:** own EAs need proof of source code; third-party EAs only as trade managers | 1/2-step | Flag "restricted"; our EAs are our own code |
| **Blueberry Funded** | Allowed; HFT and tick scalping banned; no cross-account hedging | 1/2-step | 4% daily / 8% max (per comparison source) |
| Candidates to research | Alpha Capital, BrightFunded, Blue Guardian, Funded Trading Plus, Maven, Hola Prime, Aqua Funded, City Traders Imperium, Crypto Fund Trader, FTUK, Lark Funding | — | Add only if MT5 + EAs + our symbols are confirmed |
| Excluded for now | FundYourFX (MatchTrader only), Topstep and other futures-only firms (no MT5 CFD) | — | Our EAs cannot run there as-is |

For every programme, Phase 0 records: the official URL, the date checked, every rule field in §12, symbol list,
commission/spread profile, leverage per asset class, fee per account size, split and payout cadence. Aggregator
articles are leads only, never the source of a published rule.

Comparison sources used for the seed list (not authoritative):
[FundedTrading EA list, updated 2026-06-27](https://fundedtrading.com/prop-firms-for-expert-advisors-ea-trading/) ·
[NYC Servers EA firms, 2026-07-21](https://newyorkcityservers.com/blog/best-prop-firms-ea-trading) ·
[Audacity Capital EA guide](https://audacity.capital/trading-guides/best-prop-firms-allow-ea/) ·
official [FTMO trading objectives](https://ftmo.com/en/trading-objectives/).

## 12. Generic rules engine (to support many firms without special-casing)

Each programme is a JSON file (`data/prop-rules/<firm>/<programme>.json`, with `source_url` and `verified_at`)
composed from reusable rule components. The engine evaluates them on every simulated trade and day (Composite +
Strategy patterns):

| Component | Variants needed across firms |
|---|---|
| `ProfitTarget` | Per phase, % of initial; on closed balance or on equity |
| `DailyLoss` | % of initial, or % of day-start balance / equity / the higher of the two; reset time zone (CE(S)T, broker time, UTC); some firms have none |
| `MaxLoss` | Static; end-of-day trailing; intraday trailing; trailing that locks at the initial balance; resets after payout |
| `MinTradingDays` / `TimeLimit` | Per phase; unlimited |
| `Consistency` | Best day ≤ X% of total (or positive-day) profit; this blocks the pass, it is not a breach |
| `HoldTime` | Trades under N seconds or minutes flagged, voided or zero-profit |
| `NewsWindow` | ±N minutes around high-impact news: blocked, profit voided or split-reduced. Uses the site's news calendar; the News Pulse EAs are affected directly |
| `WeekendOvernight` | Not allowed / allowed (Swing-type). Nasdaq Overnight and Nasdaq 5M need "allowed" |
| `LotAndRequestLimits` | Maximum lots per symbol, maximum open orders, requests per day (estimated from trade counts) |
| `Leverage` / `Costs` | Per asset class; commission per lot; used for lot rounding, margin cap and cost adjustment |
| `PayoutPolicy` | Split (and scaling), first payout after N days, cadence, minimum amount, fee refund |
| `Phases` | 0 (instant), 1, 2 or 3 phases, with handover delays |

**EA compatibility check per programme** runs before simulating. Each EA gets a badge: *compatible*, *compatible
with rule adjustments* (e.g. news profit split), *needs approval* (FXIFY) or *incompatible* (e.g. weekend holder on a
no-weekend programme, or straddle on E8). Incompatible EAs cannot be selected for that programme, and the reason
is shown.

**Firm-specific costs:** the site's cached trades carry the source broker's commissions and swaps. The ledger
removes the native commission and applies the programme's commission profile, recording both, so a firm with higher
costs gives worse results. Spreads are not re-modelled (they are not recorded per trade); this is disclosed.

## 13. Phase 0 audit result: FTMO SET vs cached website evidence (done 2026-09-29, read-only)

Each FTMO13 `PACKAGE.json` input set was compared with the inputs embedded in the site's cached native MT5 5-year
reports (`data/evidence-cache/v1/source-runs/<slug>/<mode>/5y.htm`), ignoring sizing, identity and guard fields.

| EA | Cached mode that matches the FTMO SET | Result |
|---|---|---|
| XAU RSI VWAP | standard | **match** (risk only: 1.0% cached vs 0.5% FTMO) |
| Gold Overnight Value Area | pipeline native runs (`Gold Overnight Value Area Pipeline 2026-09-19`, parity-verified; exact R) | **match**; confirm raw-version inputs in Phase 0 |
| XAU Squeeze Momentum | **standard** (the safe mode differs: Markov filter on) | **match** |
| DMC Fresh Reaction US100 | standard | **match** |
| EMA3 | **standard** (the safe mode differs: Markov filter on) | **match** |
| XAU Trend Progression | standard | **match** |
| XAU ORB London–NY M30 | standard | **match** |
| Nasdaq Overnight | standard | **match** |
| US100 H1 ORB 13UTC | standard | **match** |
| USDJPY London Open Momentum | standard | **match** |
| US100 Month End Flow | standard | **match** |
| DMC Current XAU | standard | **match** |
| Nasdaq 5M Candle Momentum | **dynamic** (DI14 + 0.60% stop + ATR6 trail; standard/safe are older versions with 8–9 logic differences) | **match** |

**Conclusion:** all 13 FTMO strategies can use existing cached evidence, rescaled from 1% to the chosen risk by R.
The "Saved FTMO 13 package" preset must map to exactly these modes. Native FTMO-SET runs (authorised) are
**optional**: they would validate the FTMO guard and the $50 round-down sizing, not the strategy logic. Run them in
Phase 1 only if the golden cross-check shows a sizing gap.

## 14. Revised phases (larger firm scope)

| Phase | Work | Estimate |
|---|---|---|
| 0 | Official-page verification and rule JSON for about 9 firms / 20+ programmes; symbol, cost and leverage profiles; EA compatibility matrix (37 EAs × programmes) | 4–6 days |
| 1 | Ledger, sampling and generic rules engine (§12) with unit tests per component; golden cross-check against the research engine (FTMO 2-Step, FundedNext Instant) | 5–7 days |
| 2 | API, validation, caching, job queue, rate limit (public page) | 2 days |
| 3 | Page: firm/programme/size picker, compatibility badges, EA and risk selection, results, charts, disclaimers | 3–4 days |
| 4 | Offline suggestions for each programme at a reference size, for **all three objectives**, with dev/holdout split and Monte Carlo; cached with timestamp | 3–4 days |
| 5 | Optional Level 2 minute-equity check for the suggested combos and the FTMO 13 package; optional native FTMO-SET guard runs | 3–5 days |
| 6 | Owner review, then the owner publishes the website update | — |

Pass rates for percentage-based rules do not depend on account size, except for lot rounding and fees. Suggestions
are therefore computed once per programme at a reference size, and expected value is rescaled with the size's fee.

## 15. Implementation status (2026-09-29)

Built on the local dev site (port 8081 preview; the owner's running 8080 instance and the public site are unchanged).

| Plan item | Status |
|---|---|
| Rules registry (§11–12) | **Done** — 14 programmes / 8 firms in `data/prop-rules/`; FTMO + The5ers verified on official pages, others `secondary` with sources; generic components: phases (target, min trading / profitable days, time limit), daily loss, static / EOD-trailing / trailing-locked-at-initial max loss, best-day consistency, hold-time voiding, news / weekend / straddle / EA-policy compatibility, payout cadence / split / refund, handover delays |
| Ledger (§4.1) | **Done** — R re-sizing, 0.01-lot round-down with skip counts, guards (daily loss, profit lock, open-risk cap, entries/day) on the historical timeline, daily features |
| Sampling (§4.2) | **Done** — calendar-block bootstrap (all EAs together) and weekly rolling starts, seeded |
| Engine (§4.3) | **Done (Level 1)** — vectorised; both equity views: conservative (open risk at stop) and optimistic (closed trades) |
| Outputs (§4.4) | **Done** — pass per phase / all, breaches by cause, days to funded, payout probabilities, expected payouts and value, combo statistics, fan chart, correlation, monthly returns, skipped trades |
| Suggestions (§5) | **Done** — three objectives, dev 80 % / combination-selection holdout 20 % of the 5y window, `tools/precompute_prop_suggestions.py` |
| API + public page (§6) | **Done** — validation, 20 runs/min/IP, result cache, text-only DOM rendering, mobile layout checked |
| Validation (§7) | Unit/integration tests `tests/test_prop_sim.py` (20) pass. **Open:** golden cross-check vs the research `prop_engine.py`; firm-specific commission profiles; news-window simulation (news EAs are currently blocked where restricted); Level 2 minute equity |
| Publish | **Not done** — owner publishes the website update |

Observed first results (in-sample, FTMO 13 package at 0.5 % on FTMO Swing $10k, 3y window, 2,000 paths): pass all 99.8–99.9 %, median 81 days to funded. These rates reflect EAs whose settings were developed on this history; treat them as an upper bound, not a forecast.
