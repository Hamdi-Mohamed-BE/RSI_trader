# FTMO $10K Swing combination study — 19 September 2026

**No credible, independently validated 70% future payout probability has been established.** The strongest tested news combinations cross 70% only at six months under this model. Their event presets were fitted to overlapping history, and actual FTMO news-straddle eligibility remains unresolved.

## What was actually run

Offline chronological shared-cash replay of saved native MT5 trade outcomes, then 1,000 joint-week bootstrap paths per portfolio, horizon and cost scenario. Eleven frozen combinations; 66,000 primary paths plus 9,000 two-week stress sensitivity paths. This is not a fresh synchronized FTMO tick backtest. No connected-account orders, chart deployment or risk changes were made.

All comparisons end **2026-08-31 exclusive**. Two months: June 30–August 30; four months: April 30–August 30; six months: February 28–August 30. These are not windows ending today. The common bootstrap pool is 26 full weeks, March 2–August 30. Each horizon draws from that same pool; it is not a walk-forward forecast at its historical start date.

Audited 44 usable EA/mode variants; 5 excluded for missing original-stop or cost evidence. Gold News V9 has no comparable five-year ledger and was not assigned fabricated performance. Non-news candidate screening uses pre-2024-09-19 history; the underlying strategies themselves were researched retrospectively.

## Risk and account assumptions

- Requested ordinary-entry risk: 5% / 7 = **0.7142857% = $71.43**, fixed to initial $10,000, not compounded. Lots round UP to 0.01, so actual planned loss can exceed this target. Gold raw in the regular production BAT still defaults to 1%; the FTMO research profile has not been installed.
- Literal news comparison also requests $71.43 per side. Tight stops require too much gross margin when both sides are reserved, so this version admits no news baskets in the tested windows. Reduced-news alternatives explicitly use **$10 per side**, not $71.43. No opposite-side cancellation.
- Maximum 7 daily entries, reserving slots for pending sides; stop new entries after 3 closed losses. Portfolio planned open/pending risk capped at $225, metals combined at $150.
- Admission reserves a $300 daily loss budget (including costs and stressed stop allowances) and an internal $9,200 equity buffer. FTMO hard checks remain $500 daily and $9,000 total-equity floor. These admission checks can skip signals and are not the production news-exemption logic.
- Margin: gold, silver and US100 1:15; FX 1:30; crypto conservatively 1:1. At most 80% of modeled equity allocated to gross reserved margin, without assumed hedging relief. Actual regional FTMO instrument specs must be verified.
- 10% and 5% phase targets, 4 entry days per phase, Prague DST-aware midnight resets; assumed 2 and 5 business days phase administration. First funded trade starts a 14-day wait; request only flat, no pending orders, at least $25 gross profit. Initial payout split 80%, assumed 4 business days receipt. No evaluation profit withdrawal, fees/refunds/tax or subsequent payouts included.
- A 30-day no-entry period during evaluation is classified separately as inactive, not as a loss breach. Calendar/admin assumptions are not promises from FTMO.

## Cost and equity limitations

Reference keeps native spread/gap fills, commission and swap, with explicit conservative fee floors. Stress reduces profitable gross outcomes by 10%, enlarges losses by 10%, adds asset-specific execution costs, and doubles negative swap or reserves additional carry. These are assumed stress costs, **not measured FTMO slippage**. The news sources are the fitted native reports, not evidence that the same returns are achievable at FTMO.

Open equity is approximated by reserving every active position’s initial stop simultaneously: 1R ordinary / 1.25R news in reference, 1.25R / 2R under stress. This can reject viable trades and still miss larger gaps. Model drawdown is not observed intraday FTMO equity drawdown. Zero modeled breaches does not mean zero failure risk.

## All combinations — modeled first payout receipt frequency

Each cell is reference / execution-stress. This measures completion of both phases AND receipt of the first reward within the horizon, not merely hitting phase 1.

| Portfolio | 2 months | 4 months | 6 months |
|---|---|---|---|
| Raw Gold | 0.0% / 0.0% | 0.0% / 0.0% | 7.3% / 0.9% |
| Raw + XAU/XAG news, literal risk | 0.0% / 0.0% | 0.0% / 0.0% | 7.3% / 0.9% |
| Raw + XAU/XAG news, $10/order | 5.0% / 1.9% | 63.3% / 41.1% | 95.5% / 78.8% |
| High-win comparison | 0.0% / 0.0% | 2.0% / 0.2% | 40.5% / 5.0% |
| High-win + news | 8.6% / 4.2% | 73.1% / 45.9% | 97.4% / 79.1% |
| Training top 3 | 0.0% / 0.0% | 1.2% / 0.1% | 5.8% / 0.6% |
| Training top 5 | 0.9% / 0.3% | 10.7% / 2.8% | 27.5% / 7.4% |
| Training top 3 + raw | 0.1% / 0.0% | 8.1% / 1.4% | 33.3% / 6.4% |
| Training top 3 + raw + news | 4.8% / 1.4% | 60.6% / 23.7% | 89.3% / 52.6% |
| Raw + USDJPY + news | 6.0% / 1.8% | 69.6% / 33.0% | 96.0% / 69.5% |
| Raw + all four news, literal risk | 0.0% / 0.0% | 0.0% / 0.0% | 7.3% / 0.9% |

## Preferred next validation candidate

**Raw Gold Overnight Value Area + News Pulse XAU + News Pulse XAG**, with ordinary risk $71.43 and news risk $10/order, is the simpler research candidate. Adding RSI VWAP and Nasdaq Overnight raises the six-month one-week stressed payout frequency only from 78.8% to 79.1%, less than ordinary Monte Carlo sampling uncertainty; it is not evidence of superiority. Neither combination is approved here for a paid challenge.

The five-EA high-win comparison consists of Raw Gold, XAU RSI VWAP Standard, Nasdaq Overnight Standard, News Pulse XAU and News Pulse XAG. The training-top-three are XAU Squeeze Momentum Standard, USDJPY London Open Momentum Standard and XAU Trend Progression Standard; top-five adds US100 ORB New York M30 and XAU Elliott Wave 1-2-3.

## Shortlist — historical path, including challenge resets

These are single observed paths, not probabilities. Statistics stop at the first reward request or failure; reward is shown only if its modeled receipt falls within the horizon.

| Portfolio | Months | Costs | Trades | WR | Best wins / losses | Model DD | Funded | Reward receipt | Reward USD | Breach |
|---|---|---|---|---|---|---|---|---|---|---|
| Raw + XAU/XAG news, $10/order | 2 | reference | 22 | 90.9% | 12 / 1 | 1.30% | 2026-07-21 | 2026-08-10 | $392.91 | False |
| Raw + XAU/XAG news, $10/order | 2 | stress | 39 | 79.5% | 11 / 2 | 3.40% | 2026-08-14 | No | $0.00 | False |
| Raw + XAU/XAG news, $10/order | 4 | reference | 52 | 73.1% | 8 / 2 | 2.12% | 2026-07-09 | 2026-07-29 | $427.19 | False |
| Raw + XAU/XAG news, $10/order | 4 | stress | 59 | 79.7% | 12 / 2 | 2.65% | 2026-07-21 | 2026-08-10 | $329.73 | False |
| Raw + XAU/XAG news, $10/order | 6 | reference | 92 | 70.7% | 7 / 4 | 2.10% | 2026-06-29 | 2026-07-22 | $1,355.08 | False |
| Raw + XAU/XAG news, $10/order | 6 | stress | 92 | 70.7% | 9 / 2 | 2.75% | 2026-07-09 | 2026-07-29 | $317.07 | False |
| High-win + news | 2 | reference | 35 | 82.9% | 7 / 1 | 2.01% | 2026-07-21 | 2026-08-10 | $469.83 | False |
| High-win + news | 2 | stress | 43 | 74.4% | 7 / 1 | 2.93% | 2026-07-23 | 2026-08-13 | $674.25 | False |
| High-win + news | 4 | reference | 85 | 70.6% | 13 / 4 | 3.81% | 2026-07-09 | 2026-07-29 | $295.00 | False |
| High-win + news | 4 | stress | 86 | 70.9% | 9 / 2 | 3.19% | 2026-07-09 | 2026-07-29 | $266.20 | False |
| High-win + news | 6 | reference | 126 | 73.0% | 15 / 2 | 3.52% | 2026-06-24 | 2026-07-14 | $1,146.01 | False |
| High-win + news | 6 | stress | 139 | 69.1% | 8 / 2 | 5.54% | 2026-07-09 | 2026-07-29 | $266.20 | False |

A stressed path can sometimes pay earlier or more than the reference path: changed admission and phase-transition dates select different subsequent trades. This is not a claim that worse execution improves the strategy.

## Stress bootstrap detail

| Portfolio | Months | Funded | Payout received | Model breach | Inactive | Unfinished | Median trades | Median reward if paid | 95th percentile model DD |
|---|---|---|---|---|---|---|---|---|---|
| Raw + XAU/XAG news, $10/order | 2 | 12.1% | 1.9% | 0.0% | 0.0% | 98.1% | 41.0 | $198.71 | 4.47% |
| Raw + XAU/XAG news, $10/order | 4 | 59.0% | 41.1% | 0.0% | 0.0% | 58.9% | 75.0 | $174.89 | 5.02% |
| Raw + XAU/XAG news, $10/order | 6 | 88.7% | 78.8% | 0.0% | 0.0% | 21.2% | 86.0 | $156.69 | 5.32% |
| High-win + news | 2 | 16.4% | 4.2% | 0.0% | 0.0% | 95.8% | 64.0 | $129.31 | 6.16% |
| High-win + news | 4 | 63.6% | 45.9% | 0.0% | 0.0% | 54.1% | 117.0 | $167.32 | 6.87% |
| High-win + news | 6 | 89.0% | 79.1% | 0.0% | 0.1% | 20.8% | 128.0 | $172.49 | 7.05% |

## Two-week dependence sensitivity

| Portfolio | Months | Stressed payout frequency |
|---|---|---|
| Raw + XAU/XAG news, $10/order | 2 | 2.7% |
| Raw + XAU/XAG news, $10/order | 4 | 43.1% |
| Raw + XAU/XAG news, $10/order | 6 | 81.0% |
| High-win + news | 2 | 4.5% |
| High-win + news | 4 | 53.3% |
| High-win + news | 6 | 86.0% |
| Raw + USDJPY + news | 2 | 2.1% |
| Raw + USDJPY + news | 4 | 36.8% |
| Raw + USDJPY + news | 6 | 72.8% |

Longer blocks preserve more consecutive wins/losses and regimes. These results still resample the same six-month history. A 1,000-path frequency near 79% has roughly ±2.5 percentage points of binomial Monte Carlo uncertainty; that does **not** include selection bias, data quality, broker behavior or changing markets.

## Compliance gate and next steps

1. Obtain written FTMO clarification for the exact pre-release two-sided straddle, tight stops and simultaneous XAU/XAG exposure. Swing permits ordinary news trading, but FTMO separately prohibits news-gap exploitation and excessive correlated trade-idea risk. No approval is assumed.
2. Validate original signals and both pending directions on FTMO tick data, including actual contract sizes, fee schedule, margin, spread widening, gaps and rejected orders.
3. Forward-test untouched settings and a shared-account risk controller. Treat the $71.43 and $10 alternatives as research until reviewed.
4. Do not raise risk just to force a 70% headline. Two- and four-month stressed frequencies do not meet that target.

Official rules: [Objectives](https://ftmo.com/en/trading-objectives/), [Swing](https://ftmo.com/en/faq/ftmo-swing-account-type/), [Rewards](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/), [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/). See PROTOCOL.md for margin/update references.

## Audit files

- `audit.json`: every screened mode, prior-period statistics and exclusions.
- `prepared.json`: normalized source trades, original-stop provenance and placements.
- `results.json`: all 33 horizon/portfolio combinations, both cost scenarios, historical and continuous-account ledgers, per-EA contribution, fees, rejections and bootstrap summaries.
- `sensitivity.json`: nine two-week stress experiments.
- `test_simulate.py`: deterministic accounting/risk/date regression checks.
- `SOURCE MANIFEST.json`: hashes tying this report to inputs and engine.
