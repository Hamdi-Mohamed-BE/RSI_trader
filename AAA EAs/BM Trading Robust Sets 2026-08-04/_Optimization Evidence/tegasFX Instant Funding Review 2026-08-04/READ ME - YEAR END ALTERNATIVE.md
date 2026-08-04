# Year-End Alternative — tegasFX Instant Funding

Prepared: 2026-08-04  
Deadline: cash processing targeted by 2026-12-31  
Portfolio: existing four-EA $100,000 configuration

## Decision

tegasFX Instant Funding has a much higher modeled probability of reaching a payout-request threshold by year-end than an E8 Pro challenge because there is no evaluation target. It is **not** a payout guarantee and the $100,000 product is not recommended without first completing a small-account withdrawal test.

The decisive concern is cost and counterparty exposure. The current page lists a $9,999 security deposit for the $100,000 account. Its refund formula is 90% of the applicable security deposit minus realized account losses, following review. Even with no losses, the difference between $9,999 paid and a 90% refund is $999.90. Therefore, the first $1,000 cash payout would approximately recover only that built-in deposit haircut before any other costs.

## Official rule match

- MT5 and EAs allowed.
- Copy trading, grid and martingale are listed as allowed.
- Overall loss floor is based on the original starting capital rather than accumulated profits.
- First payout request after at least 10 trading days, when the account is flat and profitable.
- Starting Bronze profit split: 50%.
- Payout processing stated as up to 48 hours after successful review.
- Indonesia is not on the published restricted-country list.
- Overall and daily drawdown tiers are selectable; the simulation conservatively uses 10%.

The daily rule is calculated from the day's closed-equity high-water mark. This is a daily loss rule, not an overall trailing floor, but floating equity is still enforced in reality.

## Simulation through year-end

The simulation starts on 2026-08-05. Requests must become eligible by 2026-12-28 to leave time for the firm's stated 48-hour processing window before December 31. There are 50,000 five-day-block paths per scenario.

| Scenario | Survive through Dec 31 | Eligible for any positive request | Eligible for at least $1,000 cash | Median date of $1,000 request | Median request when threshold first reached |
|---|---:|---:|---:|---|---:|
| Exact tested execution | 99.970% | 97.794% | 87.900% | 2026-09-09 | $1,150.89 |
| Moderate execution stress | 99.728% | **93.570%** | **72.918%** | 2026-09-14 | $1,139.83 |
| Severe execution stress | 98.200% | 84.898% | 52.540% | 2026-09-14 | $1,133.33 |

The 50% starting split means the account needs $2,000 of gross profit to request $1,000 cash.

## Ten identical $100,000 accounts

The current listed security deposit is $9,999 per $100,000 account:

| Item | One account | Ten accounts |
|---|---:|---:|
| Security deposits paid | $9,999 | **$99,990** |
| Maximum 90% refund before losses and review | $8,999.10 | $89,991 |
| Built-in 10% deposit haircut before losses | $999.90 | **$9,999** |
| Moderate-stress median first $1,000+ request | $1,139.83 | $11,398.30 if all ten are approved |

Ten identical accounts do not create ten independent chances. They follow the same market path, so they will usually profit or fail together. The moderate-stress probability remains approximately 72.918% for the synchronized group to reach the $1,000-per-account request threshold; it does not become ten times larger. Execution and slippage can still make individual accounts diverge.

The official pages say copy trading can be used with Instant Funding and display no numerical account limit. They do not explicitly confirm that one customer may mirror the same EA across ten Instant Funding accounts. Written approval for this exact arrangement is required before purchasing more than one account.

## What the percentages do not mean

- They measure numerical eligibility under the published trading rules, not payout approval.
- They do not prove the firm will remain solvent, return the security deposit, or approve the EAs.
- Floating equity is absent from the MT5 reports, so real breach probability is higher.
- Future execution, symbol names, contract sizes, spreads, commissions, swaps and news gaps are unknown.
- The historical source covers only 2025-01-02 through 2026-07-31.

## Trust assessment

Trustpilot currently displays 4.6/5 from 218 reviews. That is a positive signal but a much smaller evidence base than the largest established challenge firms. The company states it is licensed by MISA under BFX2024226. This is an offshore framework and should not be treated as equivalent to a top-tier investor compensation or deposit-protection regime. Independent current license verification should be completed before sending a security deposit.

## Practical recommendation

Do not begin with the $100,000 account or ten copied accounts. If this route is pursued, the defensible sequence is:

1. Obtain written confirmation that these exact BM Trading third-party EAs and all four symbols are permitted.
2. Confirm the precise 10% tier price, refund calculation, payout method available in Indonesia, and whether realized losing trades reduce the refundable deposit even when the account is net profitable.
3. Run the firm's demo/free environment and compare symbol contract sizes and spreads.
4. Start with one $10,000 pilot only, with every EA risk scaled to 10% of the $100,000 settings.
5. Request and receive a small payout, then close the account and successfully recover the deposit before considering larger exposure.

This pilot is a counterparty and execution test. It does not create a guarantee.

## Sources checked

- Official Instant Funding rules and pricing: https://www.tegasfx.com/instant-funding
- Independent review profile: https://www.trustpilot.com/review/tegasfx.com
- Client agreement: https://www.tegasfx.com/Client-Service-Agreement-tegasFX.pdf

## Saved evidence

- `READ ME - YEAR END ALTERNATIVE.md` — this decision.
- `tegasfx-year-end-summary.csv` — compact results.
- `tegasfx-year-end-simulation.json` — full results and limitations.
- `simulate_tegasfx.py` — reproducible model.

Bottom line: this is the first candidate with a strong numerical chance of a year-end request, but its deposit structure prevents calling it a safe or guaranteed payout. A small pilot is the maximum reasonable first exposure.
