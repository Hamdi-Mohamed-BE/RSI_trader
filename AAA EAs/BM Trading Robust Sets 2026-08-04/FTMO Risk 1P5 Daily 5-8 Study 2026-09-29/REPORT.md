# FTMO 2-Step Swing: 1.5% risk with -5%/+8% daily controls

## Decision

**Do not promote the requested settings for a durable FTMO account.** They accelerated phase completion among successful starts, but every complete six-month historical scenario eventually breached an FTMO limit. A 4% internal loss buffer reduced daily-limit failures but did not fix total-loss failures. The tested 1% alternative also increased failures. Retain the 0.5%/-2%/+4% research benchmark for forward validation; it is not proven safe or profitable in future trading.

Research as of 29 September 2026. Current saved 13-EA package, News OFF, initial $10,000; 972 source signals; 27 September 2025–25 September 2026 (363 days). This identifies the saved package, not every EA actually attached to the active terminal. No live account, order, EA, SET file or deployment was changed.

## Six-month lifecycle comparison — reference costs

26 weekly starts have a full 180 days of observation (29 September 2025–23 March 2026). These windows overlap heavily. They are historical scenarios, not 26 independent experiments or estimates of future pass/payout probabilities. Times are calendar days from starting phase 1, conditional on completing the milestone. Payout means eligibility/request in this model, not approved or received cash.

| Risk / daily stop / daily profit close | Passed both phases | Median days to pass both | First payout request | Median days to first request | Any breach by day 180 | Payout and still valid at day 180 |
|---|---:|---:|---:|---:|---:|---:|
| 0.5% / -2% / +4% | 26/26 (100.0%) | 73 | 26/26 (100.0%) | 95 | 0/26 (0.0%) | 26/26 (100.0%) |
| 1.5% / -5% / +8% | 22/26 (84.6%) | 25 | 14/26 (53.8%) | 51 | 26/26 (100.0%) | 0/26 (0.0%) |
| 1.5% / -4% / +8% | 22/26 (84.6%) | 25 | 14/26 (53.8%) | 51 | 24/26 (92.3%) | 2/26 (7.7%) |
| 1.0% / -3% / +8% | 25/26 (96.2%) | 32 | 25/26 (96.2%) | 58 | 10/26 (38.5%) | 16/26 (61.5%) |
| 1.5% current equity / -5% / +8% | 21/26 (80.8%) | 25 | 13/26 (50.0%) | 51 | 26/26 (100.0%) | 0/26 (0.0%) |

The requested fixed-$150 policy passed both phases in a median 25 days among the 22 successful starts, versus 73 days for the benchmark. First requests were earlier (51 versus 95 days among paths reaching them). However, 12/26 requested-policy starts failed before any reward; all 14 that requested a reward also failed later within their 180-day window.

The 1%/-3%/+8% diagnostic had 10/26 failures at reference costs, all involving the overall loss floor, despite the tighter daily close. It is faster but not an equivalently safe substitute.

## Dollar reward tradeoff — all 26 starts, including zeros

Mean cumulative modeled trader share over 180 days. Assumes 80% share and full withdrawals; excludes challenge purchases, retries, refunds, taxes and payment/approval risk. Larger early rewards can coexist with subsequent account failure. These are not recurring monthly-income estimates.

| Policy | Reference | Higher costs | Higher costs + 10% weaker outcomes | 5-minute liquidation |
|---|---:|---:|---:|---:|
| 0.5% / -2% / +4% | $1,367 | $1,127 | $136 | $1,331 |
| 1.5% / -5% / +8% | $1,605 | $1,075 | $299 | $1,440 |
| 1.5% / -4% / +8% | $1,761 | $1,377 | $241 | $1,605 |
| 1.0% / -3% / +8% | $3,343 | $2,297 | $438 | $3,201 |
| 1.5% current equity / -5% / +8% | $1,253 | $1,239 | $222 | $1,340 |

The requested settings produced a higher reference-case mean share ($1,605 versus $1,367), but that advantage disappeared under higher costs ($1,075 versus $1,127), and all requested-policy accounts failed in both cases. Replacing failed accounts is not modeled. The larger number alone does not establish a better sustainable FTMO policy.

## Stress tests — same complete six-month cohort

| Policy | Cost/execution case | Both phases passed | Any payout request | Any breach | Payout and still valid |
|---|---|---:|---:|---:|---:|
| 0.5% / -2% / +4% | Reference | 26/26 | 26/26 | 0/26 | 26/26 |
| 0.5% / -2% / +4% | Higher costs | 26/26 | 26/26 | 0/26 | 26/26 |
| 0.5% / -2% / +4% | Costs + weaker edge | 21/26 | 14/26 | 0/26 | 14/26 |
| 0.5% / -2% / +4% | 5-minute liquidation | 26/26 | 26/26 | 0/26 | 26/26 |
| 1.5% / -5% / +8% | Reference | 22/26 | 14/26 | 26/26 | 0/26 |
| 1.5% / -5% / +8% | Higher costs | 20/26 | 11/26 | 26/26 | 0/26 |
| 1.5% / -5% / +8% | Costs + weaker edge | 15/26 | 6/26 | 26/26 | 0/26 |
| 1.5% / -5% / +8% | 5-minute liquidation | 22/26 | 14/26 | 26/26 | 0/26 |
| 1.5% / -4% / +8% | Reference | 22/26 | 14/26 | 24/26 | 2/26 |
| 1.5% / -4% / +8% | Higher costs | 22/26 | 14/26 | 24/26 | 2/26 |
| 1.5% / -4% / +8% | Costs + weaker edge | 19/26 | 8/26 | 26/26 | 0/26 |
| 1.5% / -4% / +8% | 5-minute liquidation | 22/26 | 14/26 | 24/26 | 2/26 |
| 1.0% / -3% / +8% | Reference | 25/26 | 25/26 | 10/26 | 16/26 |
| 1.0% / -3% / +8% | Higher costs | 24/26 | 21/26 | 14/26 | 12/26 |
| 1.0% / -3% / +8% | Costs + weaker edge | 17/26 | 8/26 | 22/26 | 4/26 |
| 1.0% / -3% / +8% | 5-minute liquidation | 25/26 | 25/26 | 13/26 | 13/26 |
| 1.5% current equity / -5% / +8% | Reference | 21/26 | 13/26 | 26/26 | 0/26 |
| 1.5% current equity / -5% / +8% | Higher costs | 21/26 | 14/26 | 26/26 | 0/26 |
| 1.5% current equity / -5% / +8% | Costs + weaker edge | 14/26 | 6/26 | 26/26 | 0/26 |
| 1.5% current equity / -5% / +8% | 5-minute liquidation | 21/26 | 13/26 | 26/26 | 0/26 |

The 0.5% benchmark was also fragile in terms of earnings: only 14/26 starts requested a reward under the higher-cost/weaker-edge case, although no minute-observed FTMO breaches occurred. A historical no-breach result is not a future guarantee.

## Continuous account from 27 September 2025 — no evaluation resets or withdrawals

A different experiment from the lifecycle above. Stop the account immediately at a sampled FTMO breach. Do not interpret pre-failure profit as a surviving full-year return. Different failure dates mean the trade statistics below are not equal-duration comparisons. The continuous account retains profits as a buffer against the static overall loss floor; the funded-cycle model withdraws them and returns to $10,000. Phase timing also changes which trades are admitted. Thus a continuous full-year survivor can still fail in some phase/payout-start scenarios.

| Policy | Account outcome | Marked equity peak-to-trough DD | Worst daily equity loss | Highest concurrent initial-stop risk | Most simultaneous trades |
|---|---|---:|---:|---:|---:|
| 0.5% / -2% / +4% | Completed; +69.10% marked equity | 5.46% | 2.09% | 2.80% | 6 |
| 1.5% / -5% / +8% | Failed 2025-12-10 19:37 UTC | 12.14% | 5.28% | 9.50% | 7 |
| 1.5% / -4% / +8% | Failed 2026-01-16 15:20 UTC | 12.60% | 5.06% | 10.15% | 7 |
| 1.0% / -3% / +8% | Completed; +151.33% marked equity | 9.56% | 3.43% | 6.61% | 7 |
| 1.5% current equity / -5% / +8% | Failed 2025-11-04 15:56 UTC | 7.21% | 5.25% | 10.05% | 7 |

At requested fixed sizing, the first continuous-account failure was 10 December 2025 at 19:37 UTC, with a 5.28% daily equity loss. The 5% internal stop never safely liquidated first: observed equity had already crossed the FTMO boundary. Sizing each trade at 1.5% of current equity failed earlier, 4 November 2025.

At fixed $150, initial committed stop exposure reached about $950 across seven concurrent trades before that first continuous failure. A daily loss-close does not prevent opening too much correlated exposure. The primary experiment intentionally did not add an unrequested aggregate-risk cap.

A risk increase also changes which signals are tradable: wider-stop trades previously below minimum lot size can enter, while larger margin needs reject other trades. This is not a simple tripling of the old equity curve.

## Why a 5% internal stop is unsuitable here

FTMO 2-Step measures a 5% initial-capital daily loss allowance against the balance recorded at midnight CE(S)T, using equity including open P/L, swaps and commissions. The overall limit is 10% of initial capital. Therefore a $500 internal loss trigger on $10,000 sits on the daily failure boundary, not below it. A quote jump or closing delay can breach first. [Official FTMO trading objectives](https://ftmo.com/en/trading-objectives/).

Four $150 initial-stop losses total $600 before costs. Several EAs can expose the portfolio to the same market movement. The +8% setting is only an occasional take-profit trigger, not expected daily growth, and does not compensate for a loss-limit breach.

## Failure concentration — reference lifecycle

Counts below are complete 180-day starts, not independent market events. A few bad dates recur in many overlapping starts.

| Policy | Failure-date counts (UTC) | Boundary crossed at failure |
|---|---|---|
| 0.5% / -2% / +4% | None | None |
| 1.5% / -5% / +8% | 2025-12-10: 3, 2026-02-20: 18, 2026-07-17: 5 | daily: 22, total: 4 |
| 1.5% / -4% / +8% | 2025-12-10: 3, 2026-02-23: 7, 2026-02-24: 11, 2026-09-01: 3 | total: 21, daily: 3 |
| 1.0% / -3% / +8% | 2025-12-10: 1, 2026-06-12: 8, 2026-09-02: 1 | total: 10 |
| 1.5% current equity / -5% / +8% | 2025-12-10: 6, 2026-02-20: 15, 2026-07-17: 5 | daily: 17, total: 9 |

## Assumptions and limits

- Most headline comparisons use fixed $50/$100/$150, i.e. percent of initial capital, not compounding. The explicitly labeled equity-sized sensitivity uses 1.5% of current equity. Daily and FTMO loss amounts stay anchored to initial capital.
- Controls replace the original package governors rather than stacking with them. Native EA entry/exit schedules are reused; entries are not regenerated after skipped trades or forced exits. Actual EA re-entry behavior can differ.
- Prices are archived source-broker minute data, translated using the prior public FTMO Swing contract, commission, minimum-size and leverage assumptions. This is not a native FTMO real-tick portfolio backtest. Original total-trade swaps are apportioned approximately for early closes.
- Minute observations cannot certify tick-level compliance. Separate adverse-bar flags are retained in raw results and may reflect nonsimultaneous per-symbol extremes. Real execution could fail earlier.
- Full source ledgers and strategy choices contain selection bias; this is not an untouched out-of-sample year. More capital risk does not validate the underlying edge.
- Phase targets are +10% and +5%, flat, with four opening-trade days per phase. Assume two weekdays between phases and five before funding; holidays, KYC and actual service delays are not modeled.
- Rewards require at least 14 calendar days from first funded entry, flat positions and at least $50 profit in this simulation. Withdraw all profit at 80% share, restart at $10,000 after an assumed two-weekday gap. Eligibility/request is not cash receipt. [Official FTMO reward FAQ](https://ftmo.com/faq/how-do-i-withdraw-my-profits/).
- The constant-risk approach may admit few wide-stop trades at $50, so the basket composition changes at larger sizes. Source signal order, lot rounding and margin checks are preserved across policies.

## Verification

- 20 continuous cases, 960 weekly-start lifecycle paths, 3971 stage simulations and 1688 modeled reward requests checked.
- 39 synthetic test executions passed: original controls plus seven targeted risk/boundary cases (inherited original tests are repeated; these are not 39 unique scenarios).
- Copied-engine defaults exactly matched every returned original-engine metric, trade log, daily record and equity-curve element for the benchmark. The saved baseline and all four prior baseline lifecycle cases reproduced exactly.
- Flat-stage cash reconciliation maximum error: 2.72e-11 USD; fixed risk budgets, stage sequencing, minimum days and reward timing asserted.
- Archived inputs and earlier audit files stayed unchanged, verified by SHA-256. No market orders, MT5 changes or external account writes.

Reproduction: study.py, test_risk.py, report.py. Inputs/hashes: SOURCE_AUDIT.json. Raw cases: RESULTS.json. Checks: CHECKS.json. Frozen scope: PROTOCOL.md.
