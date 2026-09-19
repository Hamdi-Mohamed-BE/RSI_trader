# Four months: Raw Gold + XAU/XAG News on a $10K Swing model

## Bottom line

Both reference and stressed historical paths reached a **first simulated payout within four months**. This is a conditional offline replay of saved Exness executions under modeled FTMO constraints, not native FTMO execution or proof of contractual approval.

The observed four-month window is **19 May–18 September 2026**, 123 calendar days. Same settings as the preceding comparison: raw Gold Overnight Value Area $100 target initial stop risk, XAU News $10 per order, XAG News $10 per order, both news directions retained. Target combined news risk is $40 per event before costs/gaps. Lot rounding can exceed requested risk. No optimization, live EA/BAT/website changes, MT5 account switching or order submission.

## Observed historical sequence

| Milestone | Reference execution | Stressed execution/costs |
|---|---:|---:|
| Phase 1 passed | 18 June | 26 June |
| Phase 1 closing balance | $11,016.39 | $11,017.59 |
| Verification passed | 2 July | 7 July |
| Verification closing balance | $11,194.11 | $11,024.58 |
| Modeled funded activation | 9 July | 14 July |
| First reward request | 23 July | 29 July |
| Modeled first reward receipt | **29 July** | **4 August** |
| First reward after 80% split | **$439.23** | **$65.45** |
| Trades before first reward request | 41 | 41 |
| Detected equity-proxy limit breach before first request | None | None |
| Maximum equity-proxy DD before first request | 2.03% | 2.04% |
| Largest daily equity-proxy loss before first request | $116.00 | $116.64 |
| Maximum reserved gross margin before first request | $7,871.81 | $7,871.81 |

The stressed path activated later and missed the profitable 14 July news release on its funded account. This timing effect explains why its first payout is substantially smaller; it is not simply a percentage haircut to the same funded trades.

The evaluation path **stops at the first payout request**, with receipt projected using the processing assumption. The figures above do not describe continued funded-account survival or repeated payouts through September. The reward excludes challenge fee/refund, taxes and payment fees. These are hypothetical amounts, not income received.

## Extra time alone: same source weeks as the original two-month estimate

This is the cleaner comparison for "what if I allow four months?": keep the same nine observed July–September weeks, change only the simulation horizon from 62 to 123 days, preserve all EAs and same-event legs together and retain New York session clocks through synthetic autumn DST. Each cell comes from 1,000 deterministic joint weekly-block resamples. These are **model frequencies, not validated future probabilities**.

| Outcome | 2 months reference | 2 months stressed | 4 months reference | 4 months stressed |
|---|---:|---:|---:|---:|
| Funded by endpoint | 51.9% | 46.2% | **93.6%** | **87.8%** |
| First payout request eligible by endpoint | 22.8% | 19.9% | 85.1% | 78.2% |
| First payout receipt by endpoint, under assumed lag | 13.8% | 11.4% | **81.1%** | **73.6%** |
| Detected equity-proxy breach before first payout request or endpoint | 0.0% | 0.7% | 0.3% | 1.8% |
| Median first reward, conditional on modeled receipt | $387.71 | $348.92 | $412.25 | $389.30 |

The four-month horizon-only paths are synthetic patterns placed from 19 July to 19 November (exclusive). No market data after 18 September were observed or forecast. Bootstrap repeats can create a different news frequency/calendar from a real future period. More time helps within the model; it does not validate its execution, strategy-selection or distribution assumptions.

## Wider four-month sample: a separate, more optimistic estimate

Source period 19 May–18 September contains **69 raw Gold trades, 13 XAU News trades and 13 XAG News trades**, on eleven distinct news release dates. Historical replay uses the full window. Resampling uses the 17 complete Monday–Friday weeks, 25 May–18 September, excluding the initial partial week from the source pool. Boundary clipping preserves the exact 123-day destination window.

| Outcome, 1,000 paths | Reference | Stressed |
|---|---:|---:|
| Funded within 30 days | 10.3% | 9.2% |
| Funded within four months | 99.7% | 98.3% |
| First reward request eligible within four months | 96.9% | 95.5% |
| First reward receipt within four months, under assumed lag | 96.1% | 93.8% |
| Detected equity-proxy breach before request or endpoint | 0.0% | 0.0% |
| Median first reward, conditional on modeled receipt | $439.85 | $419.29 |

Do **not** interpret this table as a credible 94–96% real-world payout chance. It changes the source sample as well as the horizon, bringing in stronger May–June patterns. News settings were fitted on the same year, including these dates. Eleven release dates are not enough independent evidence for such a strong predictive claim. Zero modeled breaches is not zero risk.

## Uninterrupted-account contribution over all four months

For attribution only: one shared $10K account, no challenge resets, no payout withdrawals, same fixed-reference risk and margin guards. These totals are not withdrawable evaluation income.

| EA | Trades | Reference net USD | Stressed net USD |
|---|---:|---:|---:|
| Raw Gold Overnight Value Area | 69 | +$572.07 | +$525.55 |
| News Pulse XAU | 13 | +$1,308.70 | +$1,249.20 |
| News Pulse XAG | 13 | +$2,896.75 | +$2,673.75 |
| Combined | **95** | **+$4,777.52** | **+$4,448.50** |

Uninterrupted ending balances are $14,777.52 / $14,448.50. Do not apply the 80% split to those totals and call it the challenge payout: the actual modeled challenge account resets its balance between stages and misses trades during administrative pauses.

## Assumptions and limitations retained

- One attempt, no replacement accounts. Phase 1 +10%, Verification +5%, four distinct Prague opening days in each phase, flat before transitions, $500 midnight-balance-relative daily equity loss allowance and static $9,000 equity floor. No 1-Step Best Day rule. [FTMO objectives](https://ftmo.com/en/trading-objectives/).
- Global Swing metals leverage 1:15; full gross margin reserved for both news sides with no hedge relief; 80% margin budget. $200 daily closed-loss new-entry gate and $200 planned-open-risk cap. These are research assumptions, not changes to installed bots. [Gold leverage](https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/), [silver leverage](https://ftmo.com/en/blog/trading-updates/trading-update-7-may-2026/).
- Administrative delays assumed: two business days to Verification, five to funded activation, four from request to receipt. First reward request requires at least 14 calendar days from the first funded trade, flat positions/orders and sufficient positive profit; 80% first reward share. Actual review, eligibility and payment timing are not guaranteed. [Reward rules](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/).
- Recorded Exness spread, commission and swap remain in the reference. Stress uses the separate 250ms native news run, additional entry/exit adverse-price costs and commission floors from the prior protocol. These are not verified historical FTMO tariffs, depth or executions.
- Equity is checked with minute/second adverse-price proxies, not synchronized native FTMO ticks. Gaps, boundary seconds, spread changes, holiday schedules and execution rejection can change results materially.
- News parameters were selected on the same year being replayed. No pristine out-of-sample or prospective validation supports the high resampling percentages.
- The exact two-sided pre-news straddle design needs FTMO confirmation. Swing news permission does not override the separate prohibition of news-gap exploitation or non-replicable execution. Numerical success alone does not prove account/reward approval. [Swing](https://ftmo.com/en/faq/ftmo-swing-account-type/), [forbidden practices](https://ftmo.com/en/forbidden-trading-practices/).

## Verification and artifacts

Nine unit tests pass, including explicit New York DST resampling. All eight previous two-month scenarios reproduce their historical and uninterrupted outputs exactly after the date-range extension. The four-month historical path equals replaying its weekly blocks in original order. No source trade or pending basket crosses a weekly-block boundary. Reference and stress use identical random week indexes within each comparison.

`results.json` stores source audits, parameter/protocol fingerprints, detailed admitted trades and all summary values. `paths-reference.json` and `paths-stress.json` retain individual simulation outcomes. `PROTOCOL.md` specifies the full methodology. The engine is shared with the two-month study; previous saved two-month results are preserved.

**Conclusion:** four months is materially more achievable in this model, and both observed cost scenarios reached a first simulated reward. This still does not establish a dependable real-world probability or authorize deployment on a paid FTMO account.
