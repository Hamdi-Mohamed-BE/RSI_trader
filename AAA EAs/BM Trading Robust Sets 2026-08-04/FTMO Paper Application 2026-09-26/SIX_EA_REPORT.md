# FTMO $10K Swing — all three additions together

Research report: 27 September 2026. Simulation only. No live account, EA, BAT, website or production risk policy changed.

## Outcome

With strict round-down sizing and stressed execution, the modeled six-month funding rate is 89.0% versus 82.0% for the core; first-reward receipt is 80.4% versus 69.4%. These are fitted-history scenario frequencies, NOT calibrated real-world probabilities.

Historical continuous-account P&L increases by $357.62, from $2,757.98 to $3,115.60. Admitted trades increase from 112 to 210; win rate falls from 74.11% to 69.52% and reserve-based drawdown rises from 2.32% to 3.87%.

## Six-EA basket

| EA | Role | Planned stop-risk sizing |
|---|---|---|
| Gold Overnight Value Area (raw) | Existing core | $71.43 per entry |
| News Pulse XAU | Existing core | $10 per pending side |
| News Pulse XAG | Existing core | $10 per pending side |
| Nasdaq Overnight | Added in this simulation | $71.43 per entry |
| EMA3 Full Safe | Added in this simulation | $71.43 per entry |
| ORB Volume Profile 0.75R | Added in this simulation | $71.43 per entry |

The new Nasdaq addition is **Nasdaq Overnight**, not Nasdaq 5M DI. Neither RSI VWAP nor Gold News V9 is included. ORB uses the saved 0.75R / Dynamic 50-20 configuration; it has not been restored to the launcher.

Strict sizing rounds DOWN to 0.01 lots. Skip a signal if its minimum lot exceeds the planned stop-risk budget. This caps initial price-to-stop risk, NOT realized loss including gaps, commission and slippage. The reference calculation uses the exact $500/7 amount before rounding.

Both news sides remain enabled, but all pending/open positions share account risk and margin. Limits are unchanged: $300 daily admission budget, $225 aggregate simultaneous initial risk, $150 combined metals/per-symbol initial risk, $9,200 internal projected-equity buffer, seven entries/day, no new entries after three closed losses, maximum 80% reserved margin.

## Method and evidence

- 1,000 paired paths per portfolio/sizing/cost case; eight cases, 8,000 paths total. Seed 20260926. The same 26 weekly draws are used across every combination.
- Source pool: 2 March–30 August 2026. Synthetic evaluation purchase: 28 September 2026. Historical replay: 4 March–30 August 2026. September trades are not included, preserving the prior comparison window.
- Existing native broker trade ledgers, resampled jointly by week; no fresh FTMO tick backtest. Within-week relationships are preserved, not multi-week dependence; spanning trades and holiday schedules can be distorted by resampling.
- ORB recovered directly from its native MT5 Orders/Deals tables: all 304 five-year trades match the cached timing, side, lot, prices and net P&L; commission/swap/gross P&L and initial stops reconstructed. Total native net reconciles to $1,204.05. Only the matching study-period trades are used.
- News parameters were fitted to overlapping history; added EAs were shortlisted after seeing historical results. The source has only 20 XAU and 17 XAG news trades. Repeated sampling cannot create independent evidence.
- Reference retains native fills and spread with commission floors. Stress reduces gross wins 10%, enlarges gross losses 10%, adds adverse slippage ($0.20 ordinary gold/$1 news gold, $0.04 silver, two Nasdaq points), doubles negative swaps and reserves additional carry.
- Floating equity is approximated by full-stop reserves (ordinary 1R/reference or 1.25R/stress; news 1.25R/reference or 2R/stress). This is NOT tick-measured equity and is NOT a guaranteed bound on gap losses.

FTMO assumptions: $10,000 2-Step Swing; +$1,000 then +$500, four trading days per phase, $500 daily and $1,000 static total-loss limits, Prague midnight reset; no evaluation time limit or 2-Step Best Day Rule. See [FTMO comparison](https://ftmo.com/en/comparison-table/).

Administrative assumptions: two business days between evaluations, five until funded activation, first request after at least 14 calendar days from first funded trade and while flat, four business days for receipt; 80% reward share. Minimum modeled closed profit for request is $25. Actual administration can differ. See [reward rules](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/). Simulation stops at first request or day 180; it does not model later funded-account survival.

## Strict planned-risk cap — stressed execution

| Calendar days | Core funded | Six-EA funded | Core first payout received | Six-EA first payout received |
|---|---:|---:|---:|---:|
| 30 | 0.3% | 0.6% | 0.0% | 0.0% |
| 60 | 8.3% | 13.8% | 1.3% | 2.6% |
| 90 | 24.5% | 35.6% | 9.3% | 16.5% |
| 120 | 45.8% | 58.8% | 27.6% | 39.2% |
| 180 | 82.0% | 89.0% | 69.4% | 80.4% |

### Six-EA phase progression

| Days | Phase 1 passed | Both phases passed | Funded/activated | First payout received | Hard breaches before first reward | Still evaluating |
|---|---:|---:|---:|---:|---:|---:|
| 30 | 17.8% | 2.0% | 0.6% | 0.0% | 0.0% | 98.0% |
| 60 | 53.3% | 17.3% | 13.8% | 2.6% | 0.0% | 82.7% |
| 90 | 77.7% | 40.6% | 35.6% | 16.5% | 0.0% | 59.4% |
| 120 | 89.2% | 64.3% | 58.8% | 39.2% | 0.0% | 35.7% |
| 180 | 98.3% | 90.5% | 89.0% | 80.4% | 0.0% | 9.5% |

### Timing, conditional on completion by day 180

| Milestone | Core median days | Six-EA median days | Six-EA 10th–90th percentile | Six-EA completed paths |
|---|---:|---:|---:|---:|
| Phase 1 from purchase | 66.6 | 58.8 | 18.6–114.8 | 983 |
| Phase 2 from availability | 32.9 | 29.2 | 9.2–70.1 | 905 |
| Funded including review waits | 113.6 | 101.6 | 56.4–156.8 | 890 |
| First reward received | 129.0 | 121.0 | 77.6–165.4 | 804 |

These are different conditional cohorts; do not add separate medians. Unfinished accounts are censored, not assigned zero days or called breached.

### Paired-path comparison at day 180

- Funded: +7.0 percentage points; 80 paths succeed only with six EAs, 10 only with the core. Paired 95% Monte Carlo-only interval: +5.2 to +8.8 pp.
- Paid: +11.0 percentage points; 135 paths succeed only with six EAs, 25 only with the core. Paired 95% Monte Carlo-only interval: +8.6 to +13.4 pp.

Monte Carlo intervals exclude selection bias, small-history uncertainty, model error and changing execution. They are not real-world confidence bounds.

## Historical continuous account — strict sizing and stressed costs

No withdrawals or phase resets in this comparison. P&L is hypothetical account trading profit, not payout income.

| Metric | Three-EA core | Six EAs together |
|---|---:|---:|
| Trades | 112 | 210 |
| Net P&L | $2,757.98 | $3,115.60 |
| Win rate | 74.11% | 69.52% |
| Profit factor | 3.44 | 2.20 |
| Closed-balance DD | 1.67% | 2.38% |
| Stop-reserve equity DD proxy | 2.32% | 3.87% |
| Worst modeled daily loss | $139.53 | $261.39 |
| Longest winning/losing streak | 11/2 | 10/3 |
| Average trades per seven calendar days | 4.36 | 8.17 |
| News baskets admitted | 24 | 24 |
| Minimum-lot signals skipped | 14 | 26 |

### Per-EA contribution in the six-EA account

| EA | Trades | Wins | Win rate | Net P&L | Largest planned initial risk |
|---|---:|---:|---:|---:|---:|
| Gold Overnight Value Area (raw) | 85 | 67 | 78.82% | $541.01 | $71.39 |
| News Pulse XAU | 10 | 9 | 90.00% | $839.37 | $10.00 |
| News Pulse XAG | 17 | 7 | 41.18% | $1,377.60 | $10.00 |
| Nasdaq Overnight | 56 | 35 | 62.50% | $187.62 | $71.37 |
| EMA3 Full Safe | 6 | 3 | 50.00% | $-58.46 | $68.62 |
| ORB Volume Profile 0.75R | 36 | 25 | 69.44% | $228.46 | $71.05 |

EMA3 is not hidden by the combined result: at this risk cap it admitted only six historical trades and lost money. Nasdaq Overnight and 0.75R ORB contributed positively. Strict sizing allowed the core trades and news baskets to remain unchanged in this historical sequence; the legacy round-up basket crowded some out.

### Monthly closed-trade P&L (continuous account, not payouts)

| Month | Trades | Core P&L | Six-EA P&L |
|---|---:|---:|---:|
| 2026-03 | 33 | $101.46 | $151.01 |
| 2026-04 | 27 | $97.99 | $143.98 |
| 2026-05 | 34 | $32.55 | $265.68 |
| 2026-06 | 37 | $645.13 | $738.98 |
| 2026-07 | 46 | $1,624.30 | $1,529.39 |
| 2026-08 | 33 | $256.55 | $286.56 |

March starts on March 4; August ends on August 30. P&L uses UTC exit months.

## One historical challenge path — strict sizing and stressed costs

| Milestone | Core | Six EAs |
|---|---|---|
| Phase 1 passed | 2026-07-02T12:31:01+00:00 | 2026-06-17T18:02:01+00:00 |
| Phase 2 passed | 2026-07-15T18:29:55+00:00 | 2026-07-02T13:29:00+00:00 |
| Funded activation | 2026-07-22T18:29:55+00:00 | 2026-07-09T13:29:00+00:00 |
| First reward received | 2026-08-14T14:31:04+00:00 | 2026-07-29T14:08:41+00:00 |
| First profit reward | $506.06 | $135.28 |

One path only, not an expected payout. Earlier funding changes which trades fall in the funded phase, so earlier first reward can be smaller. Amounts exclude fee refund, tax, FX, VPS and other expenses.

## Sensitivity to costs and inherited sizing

| Sizing | Costs | Portfolio | Funded 180d | Paid 180d | Historical net P&L | Reserve DD |
|---|---|---|---:|---:|---:|---:|
| Legacy UP | Reference | Three-EA core | 98.3% | 95.9% | $4,221.25 | 2.50% |
| Legacy UP | Stress | Three-EA core | 88.2% | 78.5% | $3,037.64 | 3.50% |
| Legacy UP | Reference | Six EAs together | 98.6% | 97.2% | $4,909.79 | 4.56% |
| Legacy UP | Stress | Six EAs together | 88.1% | 79.1% | $3,215.58 | 6.80% |
| Strict DOWN | Reference | Three-EA core | 94.8% | 88.7% | $3,720.17 | 1.60% |
| Strict DOWN | Stress | Three-EA core | 82.0% | 69.4% | $2,757.98 | 2.32% |
| Strict DOWN | Reference | Six EAs together | 98.8% | 97.4% | $4,580.59 | 2.79% |
| Strict DOWN | Stress | Six EAs together | 89.0% | 80.4% | $3,115.60 | 3.87% |

Legacy UP is retained only to reproduce the preceding reports: it can exceed the nominal risk target. It is not a hard-$71.43-risk recommendation. Compare portfolios within the same sizing and cost row family, not across changed assumptions.

## Breaches, internal buffer, and decision

| Case | Hard breaches before first reward/180d | Paths touching $9,200 admission buffer | 95th percentile reserve DD |
|---|---:|---:|---:|
| legacy_round_up / Three-EA core | 0.0% | 0/1000 | 5.28% |
| legacy_round_up / Six EAs together | 0.0% | 72/1000 | 8.76% |
| strict_round_down / Three-EA core | 0.0% | 0/1000 | 3.89% |
| strict_round_down / Six EAs together | 0.0% | 0/1000 | 5.98% |

Zero simulated breaches is conditional on the admission rules and equity approximation. It does not establish zero live breach risk. Peak-to-trough DD differs from FTMO's static initial-balance limit. The $300 gate reserves modeled risk; it is not a guaranteed realized-loss stop, as the legacy daily loss exceeding $300 demonstrates.

This six-EA basket is a stronger modeled medium-term candidate with strict sizing, but it does NOT provide a high modeled probability of funding in one month or a payout in two months. It also does not improve historical win rate or longest winning streak. No claim that all three additions are necessary is established: an ablation comparison excluding EMA3 has not been run in this request.

Deployment remains separate. Exact News Pulse pre-event two-sided behavior must satisfy FTMO contract/practice rules; Swing news permission alone is not specific approval. Existing production news builds have a different hard-locked risk policy. [FTMO forbidden practices](https://ftmo.com/en/forbidden-trading-practices/).

## Verification

Native ORB stop/cost reconstruction verified; all source hashes unchanged. Nine original engine tests, seven adapter checks, eight historical parity fields, eleven phase tests and fourteen strict-sizing checks passed. Verified 40 deadline state counts, 8,000 path records, and all eight historical cash ledgers. The legacy core reproduces the prior funded/payout rates at every horizon.

Machine-readable evidence: SIX_EA_FROZEN.json, SIX_EA_RESULTS.json, SIX_EA_CHECKS.json. No MT5 trading API was initialized.
