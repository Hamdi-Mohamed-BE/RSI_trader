# Daily equity controls — research results, 29 September 2026

## Bottom line

For the current 13-EA FTMO basket, **A: 2% daily equity-loss cut + 4% equity-profit goal** had the highest return in the fixed-$50 reference replay, but the improvement was small and did not survive a five-minute closing-delay sensitivity. Its main benefit was lower worst daily loss, not a material improvement in overall drawdown. **B: 2.5% open-risk cap alone is not a daily loss limit.** It slightly reduced return here and is not a substitute for an equity-loss stop.

**No production settings, running EAs, open trades, MT5 account or crypto-paper bots were changed. This is a source-trade/M1 replay, not a native shared-account or real-tick equity-stop backtest.**

## Coverage — what is and is not complete

- Current FTMO13 News-OFF strategy package: 972 source trades; **27 September 2025–24 September 2026**, 363 days. Exact existing package/source receipts rechecked unchanged. Nasdaq is DI14/EMA12, 0.60% price stop, ATR6 trail from +1R, no TP. The requested risk policies replace existing BAT/adaptive guards for comparison.
- Broad installer catalogue: 34 products, but **only 33 have comparable cached ledgers**; Gold News V9 is missing. The common cached year is **31 August 2025–30 August 2026**, not the trailing year through today.
- **31 broad-basket binary hashes differ from current builds**, and XAU Regime Switch has a SET mismatch. Those results are historical diagnostics, not an audit proving current-build performance. The current local connection confirms Exness demo, but not every running chart/VPS EA.
- News Pulse cached parameters were selected on overlapping history. Unfilled pending-side reservations are missing from the broad replay. Treat its unusually high returns as unfit for a deployment decision. Non-news results are separated below.

## Rules and account assumptions

One shared $10,000 account; primary comparison uses **fixed $50 planned initial-stop risk**, 0.5% of starting capital. Lots round DOWN; unaffordable or minimum-lot-over-budget entries are rejected. Commission, spread, gaps and slippage can cause losses beyond planned stop risk. Nasdaq is not quarter-sized in this requested comparison.

A closes the portfolio after net equity (including floating P&L and modeled costs) minus Prague-midnight balance reaches -$200/-$250 or +$400/+$500. It blocks entries until the next Prague day. B instead caps summed original open-stop risk at $250, with NO internal daily loss stop, retaining the same profit close/day lock. Trailing-stop risk relief is not assumed. Profit targets include already closed daily P&L; they are not open-position profit alone.

The daily thresholds stay fixed to initial capital, including in the equity-sizing sensitivity. They are not 4–5% of a growing balance. FTMO imposes separate $500 daily equity loss and $9,000 static total-equity floor checks, reset at 00:00 CE(S)T. Normal capital has no FTMO disqualification. Both accounts use an 80% equity margin-admission assumption.

Forced exits are scheduled one minute after observation at the first available minute open; native exits may occur first. Thresholds are triggers, not guaranteed fill prices. No future bar closes are used before bar completion, but the source-total swap timing is approximated across its observed duration. Intraminute paths and signal changes after forced exits are not reproduced.

Official rules checked: [FTMO trading objectives](https://ftmo.com/en/trading-objectives/), [Swing account](https://ftmo.com/en/faq/ftmo-swing-account-type/), [public instrument specifications](https://ftmo.com/wp-json/ftmo/symbols). Swing leverage and target commission assumptions differ from Exness; actual FTMO historical quotes, minimum lots and swaps are not verified.

## Current FTMO13: continuous $10,000 account, fixed $50 risk

Returns below are account-equity changes, NOT payouts or withdrawable FTMO rewards. DD is peak-to-trough sampled equity drawdown divided by the running equity peak. Daily loss is relative to the initial $10K. No sampled FTMO breach occurred in any fixed-$50 reference or stress row; this is not proof of tick-level compliance.

| Policy | Normal return | FTMO return | DD normal / FTMO | Worst FTMO day loss | Goal triggers | Loss-stop triggers |
|---|---|---|---|---|---|---|
| Baseline | +70.28% | +68.07% | 5.34% / 5.42% | 2.77% | 0 | 0 |
| A loss2 goal4 | +71.19% | +69.10% | 5.38% / 5.46% | 2.09% | 5 | 3 |
| A loss2 goal5 | +70.91% | +68.81% | 5.34% / 5.42% | 2.09% | 0 | 3 |
| A loss2.5 goal4 | +70.84% | +68.64% | 5.38% / 5.46% | 2.54% | 5 | 1 |
| A loss2.5 goal5 | +70.56% | +68.35% | 5.34% / 5.42% | 2.54% | 0 | 1 |
| B risk2.5 goal4 | +69.68% | +67.48% | 5.43% / 5.51% | 2.77% | 4 | 0 |
| B risk2.5 goal5 | +68.50% | +66.29% | 5.43% / 5.51% | 2.77% | 0 | 0 |

A 2%/4% ends at **$17,119.36 normal / $16,910.20 FTMO**. Compared with baseline its FTMO gain improves by $103.00, while worst daily loss falls from 2.77% to 2.09%. Its overall peak drawdown is slightly higher, not lower.

Only five 4% goal triggers occurred in 363 calendar days; the 5% target triggered zero times in this basket at fixed $50 sizing. The 2%/4% policy forced 17 positions out and skipped 5 later signals on locked days. The largest loss-close underfill was $7.05 beyond its trigger; the largest profit-close shortfall was $24.94. Thus even the sampled model does not deliver exact 2% caps or 4% banked wins.

### Costs and execution sensitivity

| Policy | Normal stressed return | FTMO stressed return | FTMO stress DD | FTMO 5-min close return |
|---|---|---|---|---|
| Baseline | +61.40% | +59.20% | 5.95% | +68.07% |
| A loss2 goal4 | +62.49% | +60.29% | 5.99% | +67.53% |
| A loss2 goal5 | +62.17% | +59.96% | 5.95% | +68.79% |
| A loss2.5 goal4 | +61.97% | +59.76% | 5.99% | +66.96% |
| A loss2.5 goal5 | +61.65% | +59.44% | 5.95% | +68.21% |
| B risk2.5 goal4 | +60.82% | +58.62% | 6.05% | +67.21% |
| B risk2.5 goal5 | +59.64% | +57.44% | 6.05% | +66.29% |

Stress is a hypothetical additional adverse fill plus doubled negative swaps, NOT a measured execution distribution or worst-case loss. The 5-minute column uses reference costs. A 2%/4% loses its slight profit advantage when liquidation is delayed. There is no robust statistical winner between 4% and 5% profit targets.

### If 0.5% means current equity instead of fixed $50

Trade risk increases as equity grows; daily targets/loss budgets remain $400/$500 and $200/$250. This is a separate sizing policy, not an interchangeable interpretation of the table above. A stopped FTMO return is truncated at its first sampled breach.

| Policy | Normal return | FTMO return to end/breach | FTMO DD | Worst daily loss | First FTMO breach |
|---|---|---|---|---|---|
| Baseline | +112.65% | +101.73% | 6.53% | 5.02% | 2026-09-01 18:17 UTC |
| A loss2 goal4 | +91.20% | +86.34% | 7.02% | 2.52% | None observed |
| A loss2 goal5 | +97.46% | +93.62% | 6.93% | 2.38% | None observed |
| A loss2.5 goal4 | +100.33% | +96.33% | 6.44% | 2.79% | None observed |
| A loss2.5 goal5 | +103.46% | +102.34% | 6.43% | 2.66% | None observed |
| B risk2.5 goal4 | +86.92% | +84.21% | 8.12% | 4.51% | None observed |
| B risk2.5 goal5 | +94.23% | +87.16% | 8.10% | 4.57% | None observed |

The compounding baseline breaches the $500 FTMO daily-loss floor on 1 September 2026 despite substantial prior profits. B keeps open commitments below $250 but still experiences roughly 4.5% daily losses as risk capacity is reused after exits. A also overshoots its chosen internal cap due to observation/fill delay; it is not insurance against gaps.

### Single historical two-phase path

All seven fixed-$50 policies reached the same modeled milestones on this one start: Challenge flat above +10% on **27 October 2025**, Verification flat above +5% on **21 November 2025**, with at least four opening days per phase. The model resets balance and restarts on the next weekday, ignoring actual review delays. This does not establish a pass probability, payout eligibility, payment or a promise that a new challenge would pass.

## Broad historical basket: NOT current-build validated

Do not rank these figures against the newer FTMO13 table as if dates and evidence quality were equal. The news-inclusive basket is shown only for completeness and is not suitable for estimating future profit.

### 29 non-news catalogue EAs

| Policy | Normal return | FTMO-overlay return | DD normal / FTMO | FTMO goal triggers | FTMO worst daily loss |
|---|---|---|---|---|---|
| Baseline | +221.60% | +207.79% | 5.15% / 5.18% | 0 | 2.80% |
| A loss2 goal4 | +159.39% | +148.91% | 4.44% / 4.49% | 26 | 2.39% |
| A loss2 goal5 | +171.81% | +162.21% | 4.40% / 4.45% | 19 | 2.18% |
| A loss2.5 goal4 | +159.02% | +148.42% | 4.44% / 4.49% | 26 | 2.55% |
| A loss2.5 goal5 | +171.48% | +161.50% | 4.40% / 4.45% | 19 | 2.55% |
| B risk2.5 goal4 | +157.39% | +146.06% | 4.00% / 4.01% | 25 | 2.75% |
| B risk2.5 goal5 | +170.35% | +160.64% | 3.95% / 3.97% | 16 | 2.75% |

### 33 cached catalogue EAs, news included; Gold News V9 excluded

| Policy | Normal return | FTMO-overlay return | DD normal / FTMO | FTMO goal triggers | FTMO worst daily loss |
|---|---|---|---|---|---|
| Baseline | +757.88% | +389.56% | 3.16% / 4.37% | 0 | 4.05% |
| A loss2 goal4 | +515.15% | +292.75% | 3.02% / 4.30% | 38 | 2.39% |
| A loss2 goal5 | +525.36% | +306.12% | 2.97% / 4.21% | 31 | 2.39% |
| A loss2.5 goal4 | +514.29% | +290.78% | 3.02% / 4.30% | 38 | 2.55% |
| A loss2.5 goal5 | +524.50% | +307.78% | 2.97% / 4.21% | 31 | 2.55% |
| B risk2.5 goal4 | +425.86% | +284.59% | 3.86% / 3.56% | 36 | 2.75% |
| B risk2.5 goal5 | +452.51% | +299.15% | 3.30% / 3.52% | 27 | 2.75% |

The older basket’s daily profit caps cut off profitable trend/news excursions and reduce its reported return. The large news contribution is dominated by fitted historical outcomes and incomplete pending-order modeling. It must not be used to justify purchasing an FTMO account or deploying the entire catalogue. Every cost case, including unattractive outcomes, is retained in RESULTS.json.

## Monthly and EA detail — current FTMO13, A 2%/4%

| Exit month UTC | Closed positions | Net USD |
|---|---|---|
| 2025-09 | 1 | $-45.24 |
| 2025-10 | 83 | $1,360.51 |
| 2025-11 | 58 | $525.04 |
| 2025-12 | 60 | $551.42 |
| 2026-01 | 69 | $693.12 |
| 2026-02 | 54 | $406.88 |
| 2026-03 | 67 | $674.37 |
| 2026-04 | 67 | $1,548.97 |
| 2026-05 | 67 | $276.13 |
| 2026-06 | 67 | $173.56 |
| 2026-07 | 79 | $416.85 |
| 2026-08 | 74 | $146.30 |
| 2026-09 | 64 | $182.29 |

September endpoints are partial months. Attribution is closed-position net P&L, not a payout schedule.

| EA | Closed positions | Net USD |
|---|---|---|
| nasdaq-5m-candle-momentum | 177 | $2,591.84 |
| us100-h1-orb-13utc | 73 | $1,082.22 |
| dmc-current-xau | 116 | $858.21 |
| us100-month-end-flow | 33 | $504.00 |
| usdjpy-london-open-momentum | 134 | $479.90 |
| xau-trend-progression | 12 | $433.06 |
| gold-overnight-value-area | 130 | $322.95 |
| nasdaq-overnight | 71 | $261.93 |
| xau-rsi-vwap | 22 | $226.96 |
| xau-orb-london-ny-overlap-m30 | 25 | $214.41 |
| xau-squeeze-momentum-standard | 3 | $31.01 |
| dmc-fresh-reaction-us100 | 11 | $26.80 |
| ema3 | 3 | $-123.08 |

## Checks and next decision

- 112 continuous-account cases plus 35 sensitivity/stage cases generated. 16 targeted accounting, floating-equity, midnight/DST, margin, sizing and liquidation tests passed. Saved-case accounting and risk checks passed for all 112 primary cases.
- All 972 current FTMO13 source entry/exit quotes were compared with matching M1 envelopes: none exceeded the envelope by more than 0.25 initial R; maximum deviation was about 0.107R. This is a reconciliation check, not tick-path validation.
- Original source entry schedules remain fixed; after a forced close an EA might reenter, and after a skipped trade it might generate different later signals. That requires a native multi-EA rerun to validate.
- Current FTMO13 retains prior strategy-selection bias. One historical year and small policy differences are not evidence of a durable edge.
- For a forward demo test, the **daily marked-equity loss cut is the useful safety feature**. Do not replace it with open-risk admission alone. Treat the 4–5% goal as an occasional lock-in trigger, not expected daily earnings. Do not promote a new live policy from this audit.
- To finish a true full-current-EA audit: freeze the actual running EA/SET roster, archive/replay Gold News V9 predictions, regenerate current-build ledgers through the same end date, reserve all pending orders, and run coordinated tick-level forced-close/reentry tests with verified target-broker specifications.

Reproduction: inventory.py, collect.py (read-only price/spec access), prepare.py and prepare.py --recent, simulate.py, sensitivity.py, verify.py, and test_simulate.py. See PROTOCOL.md and AMENDMENTS.md for complete assumptions. No changes were made outside this new research directory.
