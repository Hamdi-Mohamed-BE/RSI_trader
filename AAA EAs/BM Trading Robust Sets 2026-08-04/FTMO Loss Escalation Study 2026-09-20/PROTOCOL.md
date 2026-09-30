# FTMO Swing loss-escalation comparison

Research-only follow-up correcting the previous Gold standalone sizing test. Scope: the prior $10,000 FTMO 2-Step Swing challenge, verification, funded stage and first reward model. No live EA, website, BAT or connected-account change. No trading commands and no source data rebuild.

## Frozen comparisons

1. Raw Gold Overnight Value Area alone.
2. The prior preferred combination: raw Gold Overnight Value Area + News Pulse XAU + News Pulse XAG.

Use the prior requested ordinary base risk: $500 / 7 = $71.428571; news uses the prior margin-compatible $10 per side. The user's $50 was an example of the multiplier, not a replacement of the previous FTMO base risk. This is explicitly stated in the response.

For each combination compare flat risk with 1.5 raised to the number of consecutive net losing closes. Maintain ONE portfolio-wide loss counter: any net win resets it, a net loss increments it, a zero-net close leaves it unchanged. A news loss can therefore increase the next ordinary risk and vice versa. This portfolio-level interpretation is an assumption, not an independently confirmed user choice. Each new challenge phase starts a new account and resets the counter. No reset at midnight, after a skipped signal or when the requested risk is unaffordable.

Both sides of a news basket use the multiplier known at placement. Its pending order sizes remain frozen after a later close changes the multiplier. Keep the opposite side: no hindsight cancellation or resizing. Existing positions are not resized. Same-time events retain the original engine's deterministic placement/open/close ordering; only closes already processed can affect future orders.

## Unchanged account controls

Preserve the previous engine: FTMO 10%/5% phase targets, four Prague entry days per phase, $500 daily allowance against Prague-midnight balance and a static $9,000 equity floor. Same 2/5-business-day review assumptions, 14-day reward wait, $25 minimum modeled gross profit, flat/no pending before requesting, 80% split and four-business-day receipt assumption. Stop at first request. Fees/refunds/tax and subsequent withdrawals are excluded.

Also preserve the prior INTERNAL controls (not FTMO-imposed numerical limits): seven entries/day including pending slots, stop after three daily losing closes, $225 total open/pending risk, $150 metals exposure, $300 daily admission budget, $9,200 total-loss buffer and 80% gross margin allocation. These controls can reject the increased risk; do not silently clip it or remove protections. Thirty evaluation days without an entry are reported as an inactivity-model outcome, not a verified account-rule breach.

Gold and silver margin modeled at 1:15, lot step/minimum 0.01 with round-up; no assumed hedged-margin relief. Unfilled news sides reserve gross margin. This preserves the previous comparison, not an assertion that a connected demo has identical Swing specifications.

## Evidence and scenarios

Read immutable prepared.json from FTMO Combination Study 2026-09-19. All actual windows end 2026-08-31 exclusive: 2m from June 30, 4m from April 30, 6m from February 28. The resampling pool remains 26 shared full weeks, March 2 to August 30. No claim that these are windows ending today. No new FTMO tick test or account data is claimed.

Reference preserves recorded native spread/gap fills and source costs, with the existing fee floors. The previous stress scenario reduces positive gross profit by 10%, enlarges gross losses by 10%, adds asset-specific execution charges ($0.20/oz ordinary Gold, $1/oz Gold news, $0.04/oz Silver news), and applies adverse carry reserves. All assumptions remain identical across sizing rules. Larger orders are assumed to get the recorded fills; size-dependent liquidity is not simulated.

Open equity uses the previous simultaneous initial-stop exposure envelope, NOT synchronized intratrade FTMO equity. Distinguish modeled breaches, inactivity and unfinished attempts. Funded status is not the same as a received payout. Fitted news settings overlap the evaluated source period; bootstrap percentages are model frequencies, not independently validated future probabilities. Swing permits news holding/trading, but exact pre-release straddles and increased trade-idea risk remain subject to FTMO's forbidden-practices rules.

## Experiment and checks

- 1,000 paired joint-week bootstrap attempts per combination, 2/4/6-month horizon and reference/stress scenario, using seed 20260920. The flat and escalating rule see identical sampled market weeks.
- 1,000 paired two-week-block sensitivity attempts per 2/4/6-month horizon under stress for Gold + news, seed 20260921.
- Keep every outcome, historical ledger and rejection reason. Report pass/funding, receipt, model breach, inactivity, unfinished, trade counts, reward conditional on receipt, and maximum requested/admitted risk.
- Verify flat engine parity against the frozen original on every historical case and selected bootstrap samples. Test net-cost resets, no lookahead, frozen news orders, persistent blocked escalation and phase reset.
- No optimization, candidate selection or invented 70% goal result.

Official rules rechecked 20 September 2026:
- https://ftmo.com/en/trading-objectives/
- https://ftmo.com/en/faq/ftmo-swing-account-type/
- https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/
- https://ftmo.com/en/forbidden-trading-practices/

The 2-Step rules are used; the 1-Step 3% daily allowance, trailing loss floor and Best Day rule are NOT substituted.
