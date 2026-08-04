# Six-month prop-firm simulation: ten copied $100K accounts

Prepared 2026-08-04. Simulated trading period: 2026-08-05 through 2027-02-04 (132 weekdays).

## Decision

**Do not buy ten $100K challenges for this EA portfolio.** There is no reviewed, payout-credible firm on which ten identical $100K accounts are both rule-compliant and supported by this evidence.

Ten copied accounts are not ten independent chances. They take essentially the same trades, so they pass, fail, and draw down together. The simulation therefore multiplies payout dollars by the account count but does **not** multiply the probability of success.

The least-bad single-account candidate remains **FundedNext Stellar 1-Step $100K on MT5 with the paid EA permission/add-on**, but only after FundedNext approves the exact four commercial `.ex5` files, settings, instruments, and unattended trading in writing. FundedNext's July 2026 EA policy permits third-party EAs on MT4/MT5 for an extra fee, but requires customized settings, prohibits identical EA trades across FundedNext accounts, and caps each EA/bot strategy at $300,000. That makes ten cloned FundedNext accounts non-compliant.

BrightFunded technically permits MT5 EAs and copying between accounts owned by the same trader, but funded allocation is capped at $400,000, or four $100K accounts. It also fails this report's trust screen: Trustpilot currently makes its rating unavailable because of a guidelines breach, says fake reviews were removed, and shows 17% one-star reviews. It is **not** recommended for purchase.

## Data and method

- Portfolio source: the exact final combined MT5 closed-deal history from 2025-01-02 through 2026-07-31.
- Tested starting balance: $100,000.
- Tested net profit: $17,844.91 over 19 months.
- Monte Carlo: 50,000 five-day-block bootstrap paths per firm and stress scenario.
- Prop limits were checked against the reconstructed intraday **closed-deal** path. Prop firms also count floating equity, which is unavailable; true breach and no-payout risk are therefore higher.
- Account copies were modeled as fully correlated.

Three execution cases were simulated:

1. **Tested execution:** exact net deal results from the MT5 reports.
2. **Moderate stress:** every winning deal is 5% smaller and every losing deal is 5% larger. The original 19-month profit drops from $17,844.91 to $7,087.03.
3. **Severe stress:** every winning deal is 10% smaller and every losing deal is 10% larger. The original 19-month sample becomes a $3,670.86 loss.

The stress tests matter because the strategy generated $116,501.30 of gross winning deals and lost $98,656.39 on losing deals. A relatively small execution/news haircut consumes much of the net edge.

## Honest result: one compliant FundedNext account

Modeled rules: 10% target, 3% daily loss, 6% static maximum loss, two trading days, two-business-day activation allowance, then a five-business-day reward cycle. Payout uses the initial 80% share and a conservative maximum 3.5% processor-fee deduction.

| Scenario | Pass challenge in six months | Receive first payout by Feb 4 | Most likely outcome | Median cash payout if successful | Median receipt date if successful |
|---|---:|---:|---:|---:|---:|
| Tested execution | 26.274% | **19.280%** | No payout: 80.720% | $477.00 | 2026-12-29 |
| Moderate stress | 9.164% | **5.960%** | No payout: 94.040% | $424.90 | 2027-01-01 |
| Severe stress | 2.104% | **1.136%** | No payout: 98.864% | $380.36 | 2027-01-04 |

In the moderate-stress successes, the middle 80% of receipt dates ran approximately from 2026-11-18 through 2027-01-29. This is conditional on being in the 5.96% of paths that produced a payout. It does **not** mean January is a likely unconditional payout date; the most likely six-month result is no payout.

The unconditional expected first payout in the six-month window is only $120.45 per account under tested execution, $34.22 under moderate stress, and $6.29 under severe stress. Those values include zero for no-payout paths and are not expected monthly income.

The historical cross-check agrees that timing is weak: across all 281 actual rolling 132-business-day windows, FundedNext produced 57 first payouts under exact execution (20.28%) and 8 under moderate stress (2.85%).

## Ten-account calculation — hypothetical and prohibited

If ten $100K accounts were allowed to take the identical portfolio, the probability would remain the same as one account because all ten are correlated:

| Scenario | Chance all ten reach a first payout by Feb 4 | Chance of no payout on any | Median combined payout if successful | Mean combined payout if successful | Unconditional expected combined first payout |
|---|---:|---:|---:|---:|---:|
| Tested execution | 19.280% | 80.720% | $4,769.96 | $6,247.59 | $1,204.54 |
| Moderate stress | 5.960% | 94.040% | $4,249.01 | $5,741.34 | $342.18 |
| Severe stress | 1.136% | 98.864% | $3,803.60 | $5,537.35 | $62.90 |

These are mathematical illustrations only. Ten identical FundedNext accounts violate the current EA uniqueness rule. Public FundedNext pricing material lists a standard $100K Stellar 1-Step around $569.99 before the additional EA fee and changing promotions, so ten base fees alone would be about $5,699.90. Under moderate stress, that is far above the $342.18 unconditional expected first payout inside six months. The registration fee is not trading capital, and under the current one-step schedule its refundable fee is not requestable until the third reward.

Do **not** use `1 - (1 - p)^10` for this setup. That formula assumes independent accounts and would materially exaggerate the chance of a payout.

## BrightFunded four-account rules-fit calculation — not recommended

BrightFunded's 2-Step Bright uses an 8% Phase 1 target, 5% Phase 2 target, 4% daily loss, and 8% static maximum loss. It allows MT5 EAs, copying between accounts owned by the same trader, and up to four copied $100K funded accounts ($400K total). Its first standard payout can be requested 30 calendar days after the first funded trade with an 80% split.

| Scenario | First-payout probability by Feb 4 | Median combined payout across four if successful | Unconditional expected combined first payout |
|---|---:|---:|---:|
| Tested execution | 2.880% | $4,331.60 | $164.08 |
| Moderate stress | 0.548% | $3,523.61 | $26.29 |
| Severe stress | 0.072% | $3,289.40 | $3.10 |

The current public promotion showed €333.90 per $100K challenge, or €1,335.60 for four before add-ons. None of the 281 actual rolling six-month windows produced a BrightFunded first payout, even under exact tested execution. Combined with the Trustpilot warning, buying this four-account plan is rejected.

## EA, static-drawdown, platform, and country checks

### FundedNext Stellar 1-Step

- **Static drawdown:** the $100K floor is fixed at $94,000; it does not trail profits.
- **EA/algo:** third-party MT4/MT5 EAs are allowed for an additional fee, with customization, distinct-strategy and allocation rules.
- **Portfolio instruments:** USDJPY, XAUUSD, US30 and NDX100 are offered. The tested UT100 chart must be mapped to NDX100 and revalidated.
- **Country:** Indonesia is absent from FundedNext's April 2026 restricted-country list, subject to successful KYC.
- **News:** on funded accounts, only 40% of profits from executions in the five minutes before/after listed high-impact news count; all losses count. This can reduce real payouts more than the generic 5% stress if the EAs cluster around news.
- **Payout review:** every reward request undergoes compliance review; published timing is not an automatic guarantee.

### BrightFunded 2-Step Bright

- **Static drawdown:** 8% maximum loss, fixed from the original balance; 4% daily loss.
- **EA/algo:** EAs are permitted on MT5; automation is not supported on DXtrade.
- **Copying:** permitted only among accounts owned by the same person; maximum funded allocation is $400,000.
- **Country:** Indonesia is absent from the current restricted list, subject to KYC.
- **Payout/reputation concern:** rating unavailable on Trustpilot due a guidelines breach; 17% of displayed reviews are one-star.

## Payout-reputation conclusion

No private CFD prop firm can be certified as an “honest payout” guarantee. These are simulated-account contracts, not protected broker deposits. Review sites do not provide a controlled denominator of every eligible payout request, so they cannot be converted into a reliable payout-approval percentage.

FundedNext has the stronger available public reputation signal: Trustpilot showed 4.5/5 from 75,092 reviews, with 7% one-star, on 2026-08-04. That is evidence of a large operating history, not proof that a future compliant request will be paid. BrightFunded's current Trustpilot warning is strong enough to reject it for this plan.

## What to do

1. **Do not buy ten accounts.** Do not auto-deploy the EAs to multiple prop accounts yet.
2. Send FundedNext support the four EA names, `.ex5` status, exact settings, MT5 platform, symbols and risk limits. Obtain written approval that the EAs are not banned and that this exact configuration is eligible for rewards.
3. Run the portfolio on FundedNext's MT5 free trial/price feed for at least 30–60 days. Confirm NDX100 mapping, lot value, swaps, news behavior and floating equity.
4. If the forward test and written approval both pass, the maximum defensible first purchase is **one** $100K FundedNext Stellar 1-Step with EA permission—not Stellar Instant, and not ten accounts.
5. Plan for **no payout during the next six months**. If a moderate-stress success occurs, the conditional midpoint is around 2027-01-01 and about $425 received on one account. The actual chance of cash receipt is no higher than the modeled 5.96% trading-eligibility probability and may be lower because firm/payment risk is unquantified.

## Official and reputation sources

- FundedNext: [Stellar 1-Step rules](https://help.fundednext.com/en/articles/8021061-what-are-the-rules-for-the-stellar-1-step-challenge-at-fundednext), [static maximum loss](https://help.fundednext.com/en/articles/8019915-what-is-the-maximum-loss-limit), [EA policy](https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext), [reward schedule/review](https://help.fundednext.com/en/articles/10701585-how-often-will-i-receive-my-performance-reward), [news rule](https://help.fundednext.com/en/articles/10701447-is-news-trading-allowed-at-fundednext), [instruments](https://help.fundednext.com/en/articles/8224087-fundednext-tradable-assets-what-can-i-trade-on-fundednext-cfd-accounts), [country restrictions](https://help.fundednext.com/en/articles/8020080-are-any-countries-restricted-on-fundednext-cfds), and [Trustpilot](https://www.trustpilot.com/review/fundednext.com).
- BrightFunded: [2-Step Bright rules](https://help.brightfunded.com/en/articles/14284817-brightfunded-2-step-bright), [EA policy](https://help.brightfunded.com/en/articles/9241699-can-i-use-ea), [copy-trading policy](https://help.brightfunded.com/en/articles/9241709-is-copy-trading-allowed), [allocation cap](https://help.brightfunded.com/en/articles/9241621-what-capital-will-i-trade-at-brightfunded), [reward schedule](https://help.brightfunded.com/en/articles/9268736-how-does-my-reward-split-work-on-my-funded-account), [country restrictions](https://help.brightfunded.com/en/articles/9286630-what-countries-are-restricted-at-brightfunded), [current pricing](https://brightfunded.com/2-step-bright), and [Trustpilot warning](https://www.trustpilot.com/review/brightfunded.com).

This simulation estimates strategy/rule outcomes, not a guaranteed financial return, payout approval, or firm solvency.
