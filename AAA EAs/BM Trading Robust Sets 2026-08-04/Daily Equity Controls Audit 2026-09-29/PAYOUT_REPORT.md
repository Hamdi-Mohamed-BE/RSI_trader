# FTMO $10,000 2-Step Swing: which setup, how long, and how much?

Research date: 29 September 2026. Offline scenarios only; no active trading settings changed.

## Decision

The preferred **forward-test candidate** is the current 13-EA, news-off basket with **Approach A: fixed maximum $50 initial-stop risk per entry, a $200 daily net-equity loss close, and a $400 daily net-equity profit close**. After either daily threshold, close positions and stop entries until the next Prague trading day. Costs and gaps can take the realized result past a threshold.

This is a risk-control preference, not proof of superior future returns. The 2.5% loss setting made slightly more in some reference scenarios, and the 5% goal did better on some higher-cost horizons. There is no consistent, statistically established return winner. The 2% stop leaves more room before the official daily limit; an open-risk cap alone does not stop cumulative daily losses. A combination of both guards is not modeled in these results.

The 4% profit close is an occasional lock-in threshold, **not a realistic promise of 4% daily earnings**. It triggered only five days in the earlier full-period reference replay. Do not increase risk to force the daily target.

These results use the 13-EA signal basket with the requested alternative governors. They are **not the unchanged installer/BAT configuration**, whose original aggregate, per-symbol and daily-entry guards were replaced for this comparison. The older broad 33-EA cache is excluded from this recommendation because it does not establish current-build performance.

## Official rules versus modeling assumptions

FTMO's current 2-Step targets are 10% then 5%, with four distinct opening-trade days per phase. On $10,000, the daily equity floor is Prague midnight balance minus $500 and the static total floor is $9,000. These apply to floating P&L and costs, not just closed losses. [FTMO trading objectives](https://ftmo.com/en/trading-objectives/).

Swing permits holding overnight/weekends and trading around news, subject to the agreement and forbidden-practice rules. It must be selected when ordering the 2-Step product. [FTMO Swing FAQ](https://ftmo.com/en/faq/ftmo-swing-account-type/).

The model allows two weekdays between phases and five weekdays before the funded account, at the same local time. These are assumptions, including a modest onboarding allowance, not guaranteed service times. FTMO currently describes typical reviews of 1–2 business days after Challenge and 1–4 after Verification, followed by identity/agreement steps. [Passing review FAQ](https://ftmo.com/en/faq/i-have-successfully-passed-what-to-do-now/).

The initial 2-Step reward split is **80% to the trader**; 90% requires qualifying for Scaling or Premium conditions. A reward can be requested from day 14 after the first trade on the specific funded account, with positions and pending orders closed. Published review time is 1–2 business days, then reward dispatch is typically 1–2 business days after invoice approval. Actual receipt can take longer. [FTMO reward FAQ](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/).

Our withdrawal policy requests the first available flat reward after 14 full days and at least $50 closed profit, withdraws all profit, and pauses two weekdays before the next $10,000 cycle. The $50 threshold is chosen to cover the published cryptocurrency minimum (bank wire is $20). Purchase fees, refunds, taxes, conversion and transfer costs are excluded. Simulated request amounts assume approval; they are not received cash.

## Timeline for the preferred candidate

All figures are **calendar days from the historical Challenge start**, except the explicitly labeled Verification duration. Timing uses the 26 starts with a full 180-day observation window, not a mix of short and long follow-ups.

| Milestone | Reference median | Reference middle 80% of scenarios | Higher-cost median |
|---|---:|---:|---:|
| Pass phase 1 (+$1,000) | 41 days | 26–59 days | 41 days |
| Verification trading duration after its account is ready | 25 days | 9–46 days | 27 days |
| Both phases passed, total elapsed | 73 days | 46–92 days | 79 days |
| Funded account ready, modeled | 80 days | 53–99 days | 86 days |
| First reward request, total elapsed | 95 days | 72–113 days | 100 days |

Reference means were 42 days for phase 1, 70 days for both phases, and 93 days to first reward request. Means and medians are historical descriptions, not expected future completion times. Separate milestone medians do not necessarily add up because they summarize different dates across paths.

Planning interpretation: the reference replay suggests roughly **2½ months to pass both phases and 3–4 months to request a first reward**, plus payment processing. A deteriorating edge can mean more than six months, or no pass/reward at all. Do not budget essential expenses against this replay.

## How often did historical starts reach the milestones?

Preferred A / 2% loss / 4% goal policy:

| Time since Challenge start | Starts with full follow-up | Both phases: reference | First reward: reference | Both phases: higher costs + weaker edge | First reward: higher costs + weaker edge |
|---|---:|---:|---:|---:|---:|
| 30 days | 48 | 0 / 48 (0%) | 0 / 48 (0%) | 0 / 48 (0%) | 0 / 48 (0%) |
| 60 days | 44 | 11 / 44 (25.0%) | 2 / 44 (4.5%) | 0 / 44 (0%) | 0 / 44 (0%) |
| 90 days | 39 | 25 / 39 (64.1%) | 15 / 39 (38.5%) | 3 / 39 (7.7%) | 1 / 39 (2.6%) |
| 120 days | 35 | 31 / 35 (88.6%) | 29 / 35 (82.9%) | 9 / 35 (25.7%) | 3 / 35 (8.6%) |
| 180 days | 26 | 26 / 26 (100%) | 26 / 26 (100%) | 21 / 26 (80.8%) | 14 / 26 (53.8%) |

The weaker-edge sensitivity applies the previous audit's extra execution/carry costs, reduces positive gross P&L by 10%, and increases negative gross P&L by 10%. It is a hypothetical stress, not an estimated distribution of future conditions. Higher costs alone yielded first rewards in 23/35 starts by 120 days and 26/26 by 180 days.

**100% here is not a 100% chance of passing.** These overlapping weekly windows reuse one selected historical sample. The 180-day cohort starts between 29 September 2025 and 23 March 2026; later starts lack six months of observed history. Each horizon therefore has a different cohort. No statistical confidence interval treating these starts as independent is appropriate.

No sampled official-limit breaches or adverse-envelope flags occurred in these 1,344 lifecycle scenarios. That is not evidence of zero future breach risk, and minute sampling cannot establish tick-by-tick compliance. In the weaker-edge case, 12 of the 26 six-month paths were still without a first reward, not necessarily failed accounts.

## Reward amounts on $10,000

Amounts below are **the trader's 80% share**, not account gross profit, and exclude fees/refunds/taxes. First-reward amounts are conditional on reaching one within 180 days. Six-month totals include all 26 starts, including zero-reward paths.

| Measure | Reference | Higher costs | Higher costs + weaker edge |
|---|---:|---:|---:|
| First reward request reached by day 180 | 26 / 26 | 26 / 26 | 14 / 26 |
| Median first reward | $369 | $272 | $88 |
| Mean first reward, among recipients | $344 | $332 | $210 |
| Middle 80% of first rewards | $58–$501 | $125–$502 | $55–$464 |
| Mean total rewards requested in first 180 days, including evaluation time and zero-reward starts | $1,367 | $1,127 | $136 |
| Median total rewards in first 180 days | $1,372 | $1,155 | $55 |
| Median number of requests in first 180 days | 5 | 5 | 1 |

These are not monthly salaries. The six-month clock includes the unpaid Challenge and Verification periods. The earliest-eligible withdrawal policy produces different amounts than a monthly policy or retaining a buffer; neither alternative was optimized here.

## Comparison of all seven tested policies

Same current 13 EAs and fixed $50 sizing. Medians are from the 26 fully observed six-month reference scenarios; the last column includes zero-reward paths in the weaker-edge stress.

| Policy | Median days to both phases | Median days to first request | Mean six-month reference rewards | Mean six-month weaker-edge rewards |
|---|---:|---:|---:|---:|
| Baseline, no requested daily controls | 73 | 95 | $1,346 | $81 |
| A: −2% / +4% | 73 | 95 | $1,367 | $136 |
| A: −2% / +5% | 73 | 95 | $1,340 | $111 |
| A: −2.5% / +4% | 73 | 95 | $1,372 | $97 |
| A: −2.5% / +5% | 73 | 95 | $1,346 | $81 |
| B: 2.5% open-risk cap / +4%, no internal daily loss stop | 78 | 99 | $1,299 | $125 |
| B: 2.5% open-risk cap / +5%, no internal daily loss stop | 78 | 99 | $1,281 | $100 |

Five-minute forced-exit latency moved A −2% / +4% to 78 days for both phases, 99 days for the first request, and $1,331 mean six-month requested rewards. Its slight reference advantage is not robust enough to promise an income improvement. The more defensible benefit of A is explicit daily equity-loss control.

## Evidence quality and next step

The source contains 972 native trades from the current 13-EA research basket over 27 September 2025–24 September 2026, with completed-minute price marks through the ending boundary. It is not a verified live track record or an untouched out-of-sample test. Signals are reused rather than regenerated after skipped or early-closed positions. Positions present before each start are excluded.

Exness price history is translated with public FTMO Swing contract, fee and leverage assumptions. Actual FTMO fills, lot minima/steps, financing, simultaneous price extremes, latency and spread can differ. Carry timing uses native trade totals spread over the observed holding period. The portfolio was selected using known historical evidence, creating selection/overfitting risk. This replay tests financial objectives, not every contractual conduct rule or reward-approval decision.

The decision is therefore **demo/Free Trial forward validation before paying for or deploying on a Challenge**, with fixed risk and the equity stop, not an assertion that a future pass is assured. Do not silently add other guards and assume these same results still apply.

Verification: 24 unique synthetic tests passed (40 test executions including inherited cases); 1,344 paths, 6,093 stages and 3,012 reward calculations passed consistency checks. Source-data hash stayed unchanged. Optional lifecycle endpoints reproduced the previous baseline and A −2% / +4% continuous results exactly with defaults disabled. These checks validate accounting logic, not the trading edge.

Reproducible artifacts in this folder: `PAYOUT_PROTOCOL.md`, `payout_followup.py`, `PAYOUT_RESULTS.json`, `test_payout.py`, `verify_payout.py`, and `PAYOUT_CHECKS.json`. The previous continuous annual audit remains in `REPORT.md`.
