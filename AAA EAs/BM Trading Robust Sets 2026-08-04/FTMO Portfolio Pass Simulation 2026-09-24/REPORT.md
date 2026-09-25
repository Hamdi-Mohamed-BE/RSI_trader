# FTMO 2-Step portfolio pass simulation — 24 September 2026

Research only. No EA, SET, BAT, website or account was changed. Probabilities below are historical resampling
frequencies under stated assumptions, **not** guaranteed future pass rates.

## Question and method

User request: find the best EA combination for an FTMO 2-Step account and simulate it with the framework of a
pasted post: pass Phase 1, pass both phases, a zero-edge control, one funded year of survival, a risk-per-trade
sweep and expected payout.

- **Portfolio selection (no hindsight):** the frozen rule of `FTMO Combination Study 2026-09-19/prepare.py` on data
  before 2024-09-19 only (≥ 50 trades, positive stressed R, PF > 1.05). Exactly five EAs qualify:
  XAU Squeeze Momentum Standard, USDJPY London Open Momentum, XAU Trend Progression, US100 ORB New York M30,
  XAU Elliott Wave 1-2-3. "Top 3" = the first three by that study's training score.
- **Trades:** the audited native MT5 ledgers from that study (`prepared.json`: original stops, commission, swap),
  1,171 trades 2021-09 → 2026-08 for the Top 5 (4.5 per week). Each trade's result in R uses that study's
  **stressed FTMO-style costs** (winners −10%, losers +10%, slippage, doubled negative swap).
- **Account:** $100,000; risk per trade = fixed % of initial capital; Phase 1 +10%, Phase 2 +5% (flat, ≥ 4 trading
  days); breach if equity < $90,000 or < (00:00 Prague balance − $5,000); each phase capped at 365 days
  ("unfinished" counts as not passed; FTMO itself sets no time limit, so eventual pass rates can be higher).
  Funded: 365 days, same limits, 80% of profit paid every 30 days. Expected payout = average over all attempts.
- **Equity brackets:** *conservative* counts every open trade at its full stop; *optimistic* counts closed trades
  only. Real floating equity is between.
- **Timeline:** weekly block bootstrap (keeps the EAs' same-week correlation), 5,000 paths per cell, seed 20260924.
  Pools: full 5 years; pre-2024-09 (selection period); post-2024-09 (never used for selection).
- **Zero-edge control:** each EA's average R is subtracted from its trades (same timing and volatility, no edge).

Files: `simulate.py`, `RESULTS.json` (all 240 cells), `run.log`.

## Top 5 — full 5 years (conservative / optimistic equity)

| Risk per trade | Pass Phase 1 | Pass both | Both within 30 days | within 90 days | within 180 days | Median days to fund | Funded-year survival | Expected payout per attempt |
|---:|---|---|---|---|---|---|---|---|
| 0.25% | 28% / 28% | 19% / 19% | 0% | 0% | 0% | ~440 | 99% / 100% | $1.1k / $1.0k |
| **0.5%** | 70% / 69% | **60% / 61%** | 0% | 1% | 10% | ~287 | **82% / 87%** | $6.6k / $6.7k |
| **0.75%** | 74% / 78% | **62% / 68%** | 0.1% | 7% | 28% | ~190–205 | 47% / 62% | **$9.0k / $10.7k** |
| 1% | 62% / 76% | 44% / 62% | 1% | 14–15% | 34–41% | ~120–140 | 12% / 39% | $5.7k / $11.4k |
| 1.5% | 34% / 69% | 17% / 51% | 3–4% | 14–31% | 17–48% | ~55–77 | 0% / 11% | $0.9k / $10.1k |
| 2% | 14% / 61% | 4% / 41% | 2–8% | 3–35% | 4–41% | ~31–52 | 0% / 2% | $0.0k / $7.7k |

### Same EAs with the edge removed (zero-edge control, full 5y)

| Risk | Pass both (cons. / opt.) | Funded-year survival | Expected payout |
|---:|---|---|---|
| 0.5% | 15% / 15% | 44% / 52% | $0.7k / $0.8k |
| 0.75% | 22% / 27% | 14% / 24% | $1.2k / $1.8k |
| 1% | 18% / 27% | 3% / 10% | $1.0k / $2.1k |

### Out-of-sample check — Top 5, post-2024-09 only (never used for selection)

| Risk | Pass both | Funded-year survival | Expected payout |
|---:|---|---|---|
| 0.5% | 62% / 63% | 85% / 91% | $6.8k / $7.0k |
| 0.75% | 66% / 72% | 51% / 68% | $9.4k / $11.3k |
| 1% | 48% / 69% | 15% / 43% | $6.1k / $12.7k |

Average trade: +0.108R before 2024-09, +0.103R after — the edge held on unseen data.

### Top 3 for comparison (full 5y, conservative / optimistic)

Pass both at 0.75%: 49% / 53%; at 1%: 48% / 54%. **Post-2024-09 the Top 3 average trade fell to +0.02R**
(USDJPY and XAU Squeeze weakened) and pass-both at 0.75% dropped to 27–28%. Diversifying across five EAs mattered.

## Findings

1. **Best combination: the Top 5 at 0.5–0.75% risk per trade.** About 60–68% pass both phases and it was stable
   out of sample. 0.5% maximises funded-account survival (82–91%); 0.75% maximises expected payout (~$9–11k per
   attempt on $100k, before the fee).
2. **A one-month pass is not realistic with this edge.** At 0.5–0.75% the median time to be funded is ~6–10 months;
   the share funded within 30 days is ≤ 0.2%. Risk high enough to be fast (1.5–2%) mostly breaches.
3. **Risk per trade is the dominant control**, as the post argued: going from 0.75% to 2% cuts the conservative
   pass rate from 62% to 4% and funded survival from 47% to 0%.
4. **The edge is real but modest:** the zero-edge control passes 15–27%, the real portfolio 60–68%.
5. The conservative/optimistic gap widens with risk; at ≥ 1% the real result depends heavily on intratrade
   drawdowns, so higher risks are also the least certain.

## Limitations

- Native Exness demo tester trades (generated ticks before 2026), not FTMO executions; FTMO symbol specs, costs,
  margin and slippage must be verified. Three of five EAs trade gold; simultaneous gold positions are modelled
  but margin is not.
- Weekly bootstrap does not preserve multi-month regimes; the 5-year history includes one strong gold trend.
- 365-day phase cap, no inter-phase admin days, payouts every 30 days; FTMO scaling and fee refund not modelled.
- Rules checked 2026-09-24 at https://ftmo.com/en/trading-objectives/ (10%/5% targets, 5% daily and 10% total loss
  on equity, 4 trading days). Recheck before buying a challenge.

## Addendum 2026-09-24 — Nasdaq 5M Candle Momentum alone, 1% with the Recommended Adaptive governor

Script `simulate_n5_adaptive.py` → `RESULTS_N5_ADAPTIVE.json`, `run_n5_adaptive.log` (5,000 paths per cell,
seed 20260925). Native 5y ledger `nasdaq-5m-candle-momentum/standard` (1,267 trades, includes the EA's real
Friday/holiday late exits). Sizing = current balance × risk × multiplier. Governor copied from
`_Shared/CalyxAdaptivePortfolio.mqh` (daily closed-loss stop −5%; closed-balance DD ≥ 4% ×0.5, ≥ 7% ×0.25;
loss streak ≥ 3 ×0.5, ≥ 5 ×0.25). Scenario B adds the installer's 0.25× base factor for this EA in Recommended
Adaptive. Same FTMO rules as above; values shown as conservative equity model (optimistic is within ~2 points).

Average trade: reference (native recorded) costs +0.065R over 5y, +0.160R since 2024-09;
stressed FTMO-style costs −0.094R over 5y, +0.004R since 2024-09.

| Scenario | Costs / pool | Pass Phase 1 | Pass Phase 2 (if P1 passed) | Pass both | Phase 1 days (25%/median/75%) | Phase 2 days | Total days | Funded ≤ 90 days | Funded-year survival |
|---|---|---:|---:|---:|---|---|---|---:|---:|
| A. 1% + governor | reference, 5y | 50% | 69% | **35%** | 30 / 66 / 149 | 10 / 26 / 85 | 62 / **129** / 235 | 13% | 83% |
| A. 1% + governor | reference, since 2024-09 | 82% | 91% | **74%** | 30 / 66 / 143 | 11 / 25 / 73 | 64 / **127** / 228 | 27% | 86% |
| A. 1% + governor | stressed, 5y | 14% | 32% | **4%** | 23 / 38 / 74 | 9 / 18 / 38 | 41 / 69 / 111 | 3% | 35% |
| A. 1% + governor | stressed, since 2024-09 | 34% | 53% | **18%** | 29 / 57 / 121 | 10 / 24 / 59 | 55 / 103 / 204 | 8% | 70% |
| B. as installed (0.25× base) | reference, 5y | 15% | 52% | 8% | 207 / 268 / 319 | 101 / 171 / 248 | 356 / 430 / 513 | 0% | 100% |
| B. as installed (0.25× base) | reference, since 2024-09 | 49% | 85% | 42% | 191 / 246 / 304 | 87 / 141 / 218 | 321 / 396 / 470 | 0% | 99% |
| C. flat 1% | reference, 5y | 63% | 74% | 47% | 32 / 58 / 102 | 11 / 24 / 50 | 60 / 93 / 142 | 23% | 7% |
| C. flat 1% | reference, since 2024-09 | 82% | 86% | 71% | 29 / 52 / 87 | 10 / 23 / 44 | 54 / 85 / 129 | 38% | 11% |
| D. 0.5% + governor | reference, 5y | 40% | 67% | 27% | 98 / 159 / 241 | 39 / 78 / 148 | 186 / 272 / 359 | 1% | 96% |

Findings: (1) the result depends mainly on execution cost — with the native recorded costs 1% + governor passes both
phases in ~35% (5y) to ~74% (recent 2 years) of paths, median ~4 months; with stressed costs only 4–18%.
(2) The governor lowers pass rates vs flat 1% (average multiplier ~0.44) but raises funded-year survival from
~7–11% to ~83–86%. (3) The installed 0.25× base factor makes an FTMO pass take >1 year on median.
Verify real FTMO US100 spread/commission/slippage before relying on either cost bracket.

## Addendum 2026-09-24 — Nasdaq 5M with loss-doubling (martingale) sizing

User idea: double the risk after every loss until a win, then reset. Script `simulate_n5_martingale.py` →
`RESULTS_N5_MARTINGALE.json`, `run_n5_martingale.log` (5,000 paths, seed 20260926, conservative equity model).
Risk = current balance × base × 2^(consecutive losses); streak resets at each new FTMO account. Same ledger and rules.

Reference (native recorded) costs, full 5y:

| Sizing | Pass Phase 1 | Breach in Phase 1 | Pass both | Median days to funded | Funded ≤ 30 days | Funded-year survival | Expected payout / attempt |
|---|---:|---:|---:|---:|---:|---:|---:|
| Martingale from 1% | 28% | 72% | 13% | 14 | 13% | 0% | $72 |
| Martingale from 0.5% | 33% | 67% | 17% | 27 | 12% | 0% | $619 |
| Martingale from 0.25% | 36% | 64% | 20% | 48 | 1% | 0% | $929 |
| Martingale from 0.5%, capped at 4% | 46% | 54% | 27% | 30 | 13% | 0% | $1,916 |
| 1% + adaptive governor | 51% | 11% | 36% | 129 | 2% | 84% | $2,120 |
| Flat 1% | 65% | 35% | 47% | 92 | 3% | 8% | $5,006 |

Since 2024-09 (reference costs) the martingale versions pass both phases 16–35%, the governor 75%, flat 1% 72%.
With stressed costs martingale passes 8–23%.

Finding: doubling after losses makes the passes that do happen faster (median 2–7 weeks) but most attempts breach
in Phase 1, no funded account survives a year, and expected payout is the lowest of all sizings. The EA's ~40% win
rate and 11–12-loss streaks make 4–5 consecutive losses routine; at 1% base the 4th loss already exceeds the 10%
maximum loss. **Not recommended.**

## Addendum 2026-09-24 — best combination by pre-registered greedy selection

Script `select_portfolio.py` → `SELECTION_RESULTS.json`, `run_selection.log`. Candidates: all non-news EA/modes with
audited native 5y ledgers (one mode per EA). Objective frozen before running: FTMO pass-both frequency at 0.5% risk,
stressed costs, conservative equity, pre-2024-09-19 pool only (1,500 paths per evaluation). Forward selection stopped
when the best addition improved < 1 point (the 9th candidate, XAU RSI VWAP, lowered it: 69.5% → 67.9%).

**Chosen (in order):** USDJPY London Open Momentum, XAU Trend Progression, XAU Squeeze Momentum Standard,
US100 Selective ORB V3, ORB Volume Profile (Safe), ETH Top Down FVG Liquidity (Safe), XAU Elliott Wave 1-2-3,
US100 ORB New York M30. 1,311 trades in 5y (~22 per month).

Combined native-ledger overlay at 0.5% of $100k per trade (closed balance, not compounded):
reference costs 5y +169.9%, PF 1.71, win 48.1%, closed DD 5.7%, streaks 8 W / 10 L; since 2024-09 +64.3%, PF 1.64.
Stressed costs 5y +72.3%, PF 1.26, closed DD 10.7%; since 2024-09 +24.8%, PF 1.21.

FTMO (5,000 paths, conservative equity), pass both phases / median days / funded-year survival / expected payout:

| Risk | Stressed, full 5y | Stressed, post-2024-09 (unseen) | Reference, full 5y | Reference, post-2024-09 |
|---:|---|---|---|---|
| 0.25% | 28% / 433 d / 100% / $1.7k | 20% / 465 d / 100% / $1.1k | 90% / 321 d / 100% / $11.8k | 92% / 332 d / 100% / $11.5k |
| 0.5% | 67% / 278 d / 84% / $8.4k | 64% / 292 d / 84% / $7.0k | 99% / 172 d / 99% / $25.7k | 99% / 176 d / 99% / $25.0k |
| 0.75% | 68% / 170 d / 48% / $11.1k | 66% / 190 d / 51% / $9.7k | 96% / 118 d / 87% / $36.0k | 97% / 118 d / 87% / $34.9k |
| 1% | 46% / 104 d / 12% / $6.0k | 42% / 109 d / 7% / $4.5k | 76% / 81 d / 37% / $25.6k | 75% / 80 d / 30% / $22.0k |

Findings: the combination held out of sample (stressed pass-both 64–66% unseen vs 67–70% in selection). The
cost assumption dominates: with the costs recorded in the native tests pass-both is 96–99% at 0.5–0.75%; with
FTMO-style stressed costs 64–68%. Several small components (Selective ORB V3, ORB VP Safe, ETH Safe, Squeeze) are
near break-even under stress since 2024-09 and add mainly trade count/diversification. USDJPY London is negative
under stress since 2024-09 (PF 0.85) — watch it. Real FTMO spreads/commission must be measured before deciding.

## Addendum 2026-09-24 — can the 8-EA combination be funded within 2–4 months?

Script `simulate_fast_schemes.py` → `RESULTS_FAST_SCHEMES.json`, `run_fast_schemes.log` (5,000 paths, seed 20260928,
conservative equity; funded account always at flat 0.5% with a −2.5% daily brake). A payout-reset bug in the first run
of this script (daily anchor not lowered after a withdrawal, faking daily-loss breaches in the funded year) was fixed
before these figures; challenge-phase results were unaffected.

Full 5y pool, stressed / reference costs:

| Scheme | Pass both | Funded ≤ 60 d | ≤ 90 d | ≤ 120 d | ≤ 180 d | Median days | Funded-year survival |
|---|---|---|---|---|---|---|---|
| flat 0.75% | 67% / 96% | 3% / 11% | 9% / 30% | 19% / 51% | 35% / 78% | 176 / 116 | 83% / 99% |
| flat 1.0% | 46% / 76% | 7% / 21% | 18% / 41% | 27% / 57% | 37% / 71% | 108 / 84 | 83% / 99% |
| floor-scaled 1.0% + brake | 59% / 90% | 6% / 20% | 15% / 41% | 23% / 57% | 35% / 75% | 151 / 97 | 83% / 99% |
| floor-scaled 1.25% + brake | 36% / 63% | 8% / 23% | 15% / 37% | 20% / 47% | 27% / 56% | 106 / 76 | 83% / 99% |
| floor-scaled 1.5% + brake | 24% / 46% | 9% / 23% | 14% / 33% | 17% / 38% | 20% / 43% | 71 / 61 | 82% / 99% |
| phase split 1.25%→0.5% + brake | 47% / 73% | 3% / 11% | 9% / 28% | 16% / 43% | 28% / 62% | 154 / 106 | 83% / 99% |

Unseen post-2024-09 pool gives the same picture (±3 points). Finding: no scheme reaches a high probability of funding
within 4 months — the best is ~20–27% (stressed costs) or ~57% (recorded tester costs), and pushing risk higher
only moves failures earlier. Floor-scaled 1% + daily brake is the best compromise (pass-both 59% / 90%, ~23% / 57%
funded within 120 days). Switching to 0.5% once funded keeps funded-year survival at 83–99%.
