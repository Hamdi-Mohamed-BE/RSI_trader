# Prop-firm simulation for the BM Trading $100K portfolio

Prepared 2026-08-04. Proposed payout deadline: 2026-09-30 (42 business days including the start date).

## Decision

**Do not buy a challenge if a payout by September 30 is required.** The exact portfolio never reached a first payout inside that deadline in any of 371 rolling historical windows. Its best actual 42-business-day profit was $7,334.91, below the $10,000 target required by the one-step products before review, account activation, and a funded payout cycle.

If the deadline is removed, the best technical fit is **FundedNext Stellar 1-Step, $100K, MT5 with the paid EA add-on**. Its overall maximum-loss floor is **static/fixed at $94,000**, not trailing. This recommendation does **not** apply to FundedNext Stellar Instant, whose maximum-loss rule trails the account. FTMO has the longer reputation, but [FTMO's current eligibility page](https://ftmo.com/en/faq/who-can-join-ftmo/) lists the Republic of Indonesia as restricted. If the trader is an Indonesian citizen or resident, FTMO cannot be purchased. FTMO 1-Step also does not offer Swing and therefore introduces news/weekend restrictions that are unsafe for an unattended four-EA portfolio.

## Static-drawdown confirmation

- **Buy only:** FundedNext **Stellar 1-Step Challenge**, $100K, MT5 + EA add-on.
- **Static overall floor:** the 6% maximum loss is calculated from the $100,000 initial balance, so the breach floor is $94,000. Profits do not pull this floor upward.
- **After passing:** the new $100,000 FundedNext Account gets its own $94,000 floor; the limit is reset from the funded account's initial balance.
- **Separate daily rule:** the 3% daily-loss allowance resets daily, but floating P/L, commissions and swaps count. This daily reset does not make the overall $94,000 floor trailing.
- **Do not buy Stellar Instant:** its 6% maximum-loss level trails gains until it reaches the initial balance, and withdrawals can reduce the remaining buffer.

Official references: [Stellar 1-Step maximum-loss rule](https://help.fundednext.com/en/articles/8019915-what-is-the-maximum-loss-limit), [Stellar 1-Step rules](https://help.fundednext.com/en/articles/8021061-what-are-the-rules-for-the-stellar-1-step-challenge-at-fundednext), and [Stellar Instant trailing rule](https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts).

## Simulation results

| Program | Main rules modeled | Historical payout by Sep 30 | Bootstrap payout by Sep 30 | Bootstrap payout within 260 business days |
|---|---|---:|---:|---:|
| FundedNext Stellar 1-Step | 10% target, 3% daily, 6% total, 2 trading days, 5-business-day reward cycle | 0 / 371 = **0.00%** | **0.054%** (27 / 50,000) | **64.96%** |
| FTMO 1-Step Standard | 10% target, 3% daily, 10% EOD trailing, 50% best-day rule, 14-day reward wait | 0 / 371 = **0.00%** | **0.010%** (5 / 50,000) | **63.67%** |
| FTMO 2-Step Swing | 10% + 5% targets, 5% daily, 10% static, 4 days per phase, 14-day reward wait | 0 / 371 = **0.00%** | **0.000%** (0 / 50,000) | **29.70%** |

For FundedNext, the estimated probability of merely passing the challenge inside the deadline was **0.106%**; the probability fell to **0.054%** after including activation and a profitable reward cycle. Among the very rare deadline successes, the estimated net first payout averaged about **$729** after an 80% split and a modeled maximum 3.5% payment-processor charge.

The portfolio's tested average of $939.21 per month implies about **10.6 average months just to accumulate a 10% challenge target**, before any funded trading. Trying to force the target inside approximately one month would require roughly six times the present risk and would invalidate the 4% drawdown design.

## Why FundedNext is the closest fit

- [Stellar 1-Step rules](https://help.fundednext.com/en/articles/8021061-what-are-the-rules-for-the-stellar-1-step-challenge-at-fundednext): 10% target, 3% daily loss and 6% maximum loss.
- [EA policy](https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext): third-party MT5 EAs are allowed with the EA add-on, but their settings must be customized and the strategy must be unique. The delivered portfolio settings are customized. Written confirmation should still be obtained before purchase.
- [Overnight/weekend policy](https://help.fundednext.com/en/articles/11982358-does-fundednext-allow-holding-trades-over-the-night-weekend): both are allowed, with swaps counting toward losses.
- [Reward schedule](https://help.fundednext.com/en/articles/10701585-how-often-will-i-receive-my-performance-reward): Stellar 1-Step rewards can be requested every five business days after funding.
- [News rule](https://help.fundednext.com/en/articles/10701447-is-news-trading-allowed-at-fundednext): on the funded account, only 40% of profits from executions within five minutes before/after listed high-impact news count, while losses remain fully counted. This was not deducted in the simulation and can reduce real payouts.
- [Country eligibility](https://help.fundednext.com/en/articles/8020080-are-any-countries-restricted-on-fundednext-cfds): Indonesia is not on FundedNext's current restricted list. Eligibility must still be confirmed during KYC.
- [Tradable symbols](https://help.fundednext.com/en/articles/8224087-fundednext-tradable-assets-what-can-i-trade-on-fundednext-cfd-accounts): USDJPY, XAUUSD, US30 and NDX100 are offered. Turnaround Tuesday would have to use **NDX100 instead of the tested broker's UT100 symbol**.

The registration fee and EA add-on are purchase costs, not trading deposits. Confirm the live checkout amount because prices and promotions change. For accounts purchased under the current structure, the one-step registration fee is not returned until the third Performance Reward.

## FTMO trust comparison (not available to Indonesian residents/citizens)

- [FTMO 2-Step objectives](https://ftmo.com/en/2-step-challenge/): 10% + 5% targets, 5% daily loss, 10% maximum loss, unlimited time and four trading days per phase.
- [FTMO Swing account](https://ftmo.com/faq/ftmo-swing-account-type/): only available with 2-Step and removes news, overnight and weekend restrictions.
- [FTMO EA/strategy policy](https://ftmo.com/au/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/): algorithmic trading and EAs are generally allowed, subject to legitimate real-market behavior and allocation limits.
- [FTMO reward timing](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/): reward claims become available on or after day 14 of the funded account.

FTMO publicly states that it has operated since 2015, served more than 4.5 million customers and paid more than $650 million in rewards. Those are company-reported figures, not a regulatory guarantee. Its current restricted-country policy includes Indonesia, so it is only an alternative if the trader has an eligible citizenship and legal residence. Prop-firm accounts are simulated accounts and prop firms are not equivalent to regulated deposit-taking banks or brokers.

## The5ers was rejected

[The5ers' current EA policy](https://the5ers.com/faqs/can-i-use-an-ea-expert-advisor-can-i-set-a-stealth-mode-stop-loss/) says that the trader must own the EA source code. These downloaded commercial EAs are `.ex5` files and no owned source code was supplied, so buying its challenge for this portfolio risks cancellation or reward denial.

## Simulation method and limitations

- Source: exact deal history from the four final MT5 reports, 2025-01-02 through 2026-07-31, starting balance $100,000.
- All 371 possible rolling 42-business-day historical windows were replayed.
- 50,000 five-day-block bootstrap paths were simulated for the deadline and for a 260-business-day horizon.
- Positive and negative realized P/L were kept at their tested values. Intraday closed-loss paths were shocked by 1.25x when checking risk-limit breaches.
- The maximum stressed intraday closed loss was $2,379.27, below a $3,000 daily limit.
- Prop firms measure **floating equity**, whereas the available combined data contains closed deals. Actual breach probability is therefore higher than this model suggests.
- The MT5 reports use MEXAtlantic price feeds and contract specifications, not FundedNext's feed. NDX100 also replaces UT100. A FundedNext MT5 free-trial backtest/forward test is required before purchase.
- The bootstrap reuses only 19 months of history. Its confidence interval reflects Monte Carlo sampling error, not strategy, market-regime, execution, rule-change or firm-payment uncertainty.

## Recommended action

1. Do not purchase based on the September payout goal.
2. Run the exact portfolio on an FTMO free trial or a FundedNext demo/free-trial environment first, including news and weekend behavior.
3. Ask FundedNext support in writing to approve the four named third-party EAs, the customized settings, MT5, and all four instruments before paying for an EA-enabled challenge.
4. If buying despite the timing result, choose **FundedNext Stellar 1-Step $100K + MT5 EA add-on** for rule compatibility, and budget **6–12 months**, not one month, for a first payout attempt.
5. Do not buy FTMO if your citizenship or residence is Indonesia; its current policy explicitly restricts Indonesia.

The JSON file contains every modeled probability and status count. The CSV is the compact comparison table. This analysis is not a guarantee of passing, payout, or firm solvency.
