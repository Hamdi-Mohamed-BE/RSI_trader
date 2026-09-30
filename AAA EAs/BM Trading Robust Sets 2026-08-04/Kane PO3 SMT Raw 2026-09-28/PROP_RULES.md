# Account replay assumptions and limitations — checked 28 September 2026

These are offline counterfactuals using Exness CFD entries/exits and recorded minute equity envelopes, NOT executions on FTMO or FundedNext. No account was connected or purchased. "Cash" means simulated eligible trader share at request time, not an approved payment or guaranteed receipt.

## Planned accounts

FTMO Swing 2-Step: $10,000, $50 base stop-risk (0.5%) before caps, 10% challenge and 5% verification targets, four entry days each phase, 5% daily equity limit resetting at Prague midnight, 10% static maximum loss. See [2-Step objectives](https://ftmo.com/en/trading-objectives/). Two and five business-day phase/handover delays are OUR administrative assumptions.

After funding: model 80% share, 14-day eligibility, close all positions before request. The $25 minimum gross withdrawal in this engine is OUR conservative convention: the official page currently says $20 minimum closed profit for bank wire and $50 for crypto. It is not an exact model of either withdrawal channel. Processing delay/approval is excluded. [FTMO rewards](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/). Swing allows news/overnight/weekend holding subject to its general restrictions; this EA is flat by noon. [Swing](https://ftmo.com/faq/ftmo-swing-account-type/).

FundedNext Stellar Instant: $5,000, 0.25% base risk further capped at 5% of available loss headroom; 6% balance-trailing maximum-loss floor, capped at starting capital and never lowered after withdrawals; no formal daily drawdown rule. A 70% initial share is used. [Loss limit](https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts). Eligibility: at least 1% growth after 14 days or 5% growth at end of day; model retains a 3% initial-capital buffer after payout (OURS). [Eligibility](https://help.fundednext.com/en/articles/11641693-what-is-the-eligibility-criteria-for-my-performance-reward-in-the-stellar-instant-account).

The simulator conservatively uses index leverage 15 for Swing and 5 for Instant, 0.05 minimum USTEC lot, 0.01 step and 30% equity maximum margin usage. The latter is OUR portfolio safety rule. Exact target-server contract sizes/minima and commissions were not obtained; the Instant help-page index leverage and marketing table conflicted in the preceding study. Keep 5 until the account's actual specification is checked.

## Guards (ours, not provider trading objectives)

One open position per EA, seven total entries and three realized losses maximum per day; native Kane already limits entries to two. FTMO: 1.5% aggregate stop-risk, 0.75% per symbol, 1.5% internal daily limit and 2% buffer above overall loss floor. Instant: aggregate 20% and same-symbol 10% of headroom, 0.75% internal daily guard, additional 0.2% buffer. Floors include unrealized adverse excursions. Original risk stays reserved even after BE: conservative.

Lot size is rounded DOWN. If below minimum lot or above margin/risk caps, skip; never upsize to force a trade. Narrow stops can therefore be margin-rejected. Unresolved/no payout does not mean breached; surviving without sufficient growth is not a success.

## Costs and rule uncertainty

Native spread and 150ms fills are in native results. Replay applies the larger of native commission or $0.70 per index lot, with differing entry/exit fee timing. This fee floor is a hypothetical conservative assumption, NOT measured target-broker pricing.

Stress is deliberately hypothetical: positive price P&L multiplied by 0.9, negative by 1.1, plus $2/lot extra index costs; adverse equity envelopes scaled accordingly. It is NOT the pipeline's measured-cost promotion stress. Swap floors/doubling exist in the shared engine but are immaterial to these intraday trades.

Instant positive trades opened OR closed within five minutes of a flagged news event receive a 60% deduction, losses remain full. Only 29 pre-existing event timestamps are available: this is an INCOMPLETE calendar, particularly relevant to 10:00 NY releases. Unflagged positive trades get an additional 10% haircut in the stress scenario, which does not prove complete policy compliance. [Clarity Cards](https://help.fundednext.com/en/articles/15644011-what-are-the-clarity-cards-and-how-do-they-affect-my-account).

Profitable <=30-second trades reaching 30% of positive profit trigger an absorbing compliance block at modeled withdrawal eligibility. This is a conservative interpretation, NOT a drawdown breach: the Clarity article describes deductions then escalation; a general restricted-strategy page had stricter wording in the preceding review. [Restricted strategies](https://help.fundednext.com/en/articles/8020351-what-are-the-restricted-prohibited-trading-strategies). Resolve the actual account terms before use.

Instant EA use requires the appropriate paid add-on and compliance with custom/distinct strategy restrictions. [EA policy](https://help.fundednext.com/en/articles/11641338-can-i-use-ea-in-stellar-instant). Fees for purchase, resets, subscriptions, EA add-ons and tax are excluded. Ignore inherited generic fee-recovery fields in raw simulator JSON; those thresholds are not verified current purchase prices.

## Interpretation

Weekly historical starts overlap: 48 / 44 / 35 / 27 completed windows at 30 / 60 / 120 / 180 days. Frequencies are historical replay counts, not independent estimates of future success probability. There is no claim of unseen holdout validation.

Price paths use first-tick-per-minute snapshots plus interval minima, not complete target-broker tick paths. Some minima straddle a minute boundary and preserve native costs, making the envelope conservative. Entry/exit times round upward to minutes; positions open at a horizon remain marked and are not silently liquidated. No signal replay after an account breach; native trade availability is inherited, not regenerated under a different balance. Changes in stops and earlier exits can also create new re-entry opportunities across variants.

The entire-year no-withdrawal replay is a funded-style risk diagnostic, not a two-step pass or a request for payment. Raw strategy tests remain the promotion gate. No optimized production build, parameter search or deployment is authorized by these results.

