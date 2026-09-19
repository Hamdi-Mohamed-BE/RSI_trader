# FTMO Swing 2-Step challenge simulation

Generated 13 September 2026 from the website's complete five-year cached trade ledgers.

## Decision result

The planning estimate is a **61.90% probability of completing both FTMO phases within 730 days** under the execution-stress model. The 95% binomial confidence interval is **58.85% to 64.86%**. This implies **1.62 challenge starts per successful two-phase completion** within the reporting horizon.

This is not a guarantee. Of the 1,000 independent validation paths:

- 619 completed both phases;
- 225 breached an FTMO loss rule;
- 156 remained unresolved after 730 days.

FTMO's official trading period is unlimited, so an unresolved path is not counted as a rule failure. Its eventual outcome cannot be inferred honestly from this finite simulation.

The more conservative floating-risk envelope passed 594 of 1,000 paths (59.40%), breached 292 and left 114 unresolved. This is the safer lower planning case because exact historical intratrade floating equity is unavailable.

## FTMO rules modelled

- Phase 1 profit target: 10%.
- Phase 2 profit target: 5%.
- Maximum daily loss: 5% of the initial $200,000 balance, including closed and floating P/L, commissions and swaps, reset at midnight CE(S)T.
- Maximum total loss: a static 10% of initial balance in the 2-Step product.
- At least four trading days in each phase.
- Unlimited official trading period; 730 days is only the simulation reporting horizon.
- Swing leverage constraints: forex 1:30, indices 1:15, metals 1:9 and crypto 1:1, with a further 20% free-margin reserve in the simulation.

Official references: [FTMO Trading Objectives](https://ftmo.com/en/trading-objectives/), [FTMO 2-Step](https://ftmo.com/en/2-step-challenge/), [news trading rules](https://ftmo.com/faq/can-i-trade-news/), [Swing account rules](https://ftmo.com/faq/ftmo-swing-account-type/) and [account specifications](https://ftmo.com/en/faq/what-are-the-account-specifications/).

## Recommended controls selected

The settings were selected on a separate 300-path parameter screen, then graded on a fresh set of 1,000 paths:

- Non-news risk: **0.50% per trade**.
- Internal non-news closed-loss stop: **1.00% per CE(S)T day**.
- Non-news maximum simultaneous planned risk: **3.00%**.
- Drawdown taper: half size from 4% drawdown; quarter size from 7%.
- Loss-streak taper: half size after three losses; quarter size after five.
- FTMO hard limits remain 5% daily and 10% total.
- News Pulse risk remains hard-coded at **0.75% per entry**, and news trades bypass the adaptive gates, matching the requested live system behavior.

This is the best tested combination under the constraint that news trades must remain exempt. It is not necessarily the safest possible portfolio if that constraint is removed.

## EAs used

The three statistically verified News Pulse EAs were combined with five non-news EAs selected for five-year evidence, profit factor, return, drawdown, recency and diversification.

| EA | Symbol | 5Y return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|---:|
| News Pulse XAU | XAUUSD | +53.07% | 2.77 | 56.39% | 3.62% | 133 |
| News Pulse XAG | XAGUSD | +149.14% | 3.43 | 53.95% | 4.67% | 152 |
| News Pulse BTC | BTCUSD | +2,439.59% | 9.31 | 72.73% | 4.45% | 198 |
| ORB Volume Profile Volume Confirmed | XAUUSD | +34.62% | 1.69 | 43.33% | 5.67% | 120 |
| XAU Trend Progression | XAUUSD | +83.90% | 2.27 | 58.70% | 5.54% | 138 |
| USDJPY London Open Momentum | USDJPY | +178.41% | 1.46 | 53.97% | 12.12% | 693 |
| US100 ORB New York M30 | USTEC | +40.09% | 1.78 | 48.96% | 8.02% | 96 |
| US100 H1 ORB 13UTC | USTEC | +92.93% | 1.57 | 48.79% | 17.82% | 289 |

Gold News V9 Direction was excluded because it has no verified five-year backtest. Inventing returns for it would invalidate the simulation.

## Main 1,000-run outcomes

| Scenario | Passed | Rule breach | Unresolved at 730d | Pass probability | Expected starts/pass | Median time if passed | Median time to breach |
|---|---:|---:|---:|---:|---:|---:|---:|
| Historical closed P/L, Swing margin | 999 | 1 | 0 | 99.90% | 1.00 | 136 days | 114 days |
| **Stressed closed P/L, Swing margin** | **619** | **225** | **156** | **61.90%** | **1.62** | **300 days** | **375 days** |
| Conservative stop/floating envelope | 594 | 292 | 114 | 59.40% | 1.68 | 293.5 days | 354 days |
| Naive historical replay ignoring Swing margin | 965 | 35 | 0 | 96.50% | 1.04 | 60 days | 24 days |

The historical result is intentionally not the recommendation. It assumes the recorded backtest outcomes repeat and cannot capture unseen intratrade drawdown. The naive no-margin run is also not deployable: it allows BTC sizing that an FTMO Swing account cannot fund.

## Stressed phase breakdown

- Phase 1: 731 passes, 143 loss-rule breaches and 126 unresolved paths.
- Phase 2 among the 731 entrants: 619 passes, 82 loss-rule breaches and 30 unresolved paths.
- Conditional Phase 2 pass rate: 84.68% of Phase 2 entrants.
- All 225 close-only failures reached the static 10% maximum-loss boundary; no daily closed-P/L breach occurred in that model.
- The conservative envelope produced 248 simultaneous-stop maximum-loss breaches, 12 possible daily floating-loss breaches and 32 closed-P/L maximum-loss breaches.
- Ninety percent of successful stressed paths finished within 667 days. Ninety percent of stressed rule breaches occurred within 702.6 days.

In prop-firm language, the 225 or 292 rule breaches are the account "blow-ups." The account is terminated at the first rule violation, so the model does not continue those paths to a literal zero balance.

## Swing margin finding

At the selected settings, the stressed model rejected an average of 56.91 entries per challenge start for insufficient Swing margin:

- News Pulse BTC: 45.92 rejected and **0 accepted** on average.
- News Pulse XAG: 7.82 rejected and 27.47 accepted on average.
- News Pulse XAU: 3.16 rejected and 27.42 accepted on average.

The BTC News Pulse backtest cannot be deployed at its locked 0.75% risk on FTMO Swing's 1:1 crypto leverage. Its very large historical return therefore contributes nothing to the realistic Swing simulation. It should be disabled on Swing or redesigned with an explicit margin-aware risk ceiling before use.

The connected $200,000 FTMO terminal reported **1:100 leverage**, which identifies it as a Standard-style account rather than Swing's capped 1:30 account. The simulation nevertheless used Swing rules and margin because that is the requested target. A Standard account cannot be assumed to retain unrestricted news trading after funding; use an actual Swing account for that requirement.

## Method and limitations

- Common source window: 5 September 2021 through 31 August 2026.
- Complete weeks were block-bootstrapped so trades from different EAs on the same historical week remained correlated.
- Each phase started from a fresh $200,000 account and used a separately sampled path.
- P/L used the net MT5 deal result, including recorded commission and swap.
- Each source trade was normalized from its reconstructed balance at entry before applying the new account balance and risk. This avoids double-counting the source backtest's compounding.
- Stress reduced news winners by 35%, enlarged news losses by 25% and charged another 0.15R adverse execution cost. Non-news winners were reduced by 10%, losses enlarged by 10% and another 0.02R was charged.
- The source ledgers are the website's broker-native tests, not five years of FTMO tick data. The five-year News Pulse tests report only 13% real-tick coverage; older missing ticks were generated by MT5.
- Closed deals cannot reconstruct every floating-equity path, which is why both close-only and deliberately conservative stop-envelope results are shown.
- Margin is calculated for filled historical positions. Any broker margin reserved for the unfilled sibling pending order of a two-sided News Pulse setup is not present in the deal ledger and could cause additional live rejections.
- A bootstrap estimates outcomes if the sampled historical weekly distribution remains relevant. It cannot guarantee a future pass rate or predict a new market regime.

## Recommendation

For a $200,000 FTMO Swing attempt, use the five selected non-news EAs at 0.50% risk with the 1% internal daily stop, 3% open-risk cap and existing adaptive tapers. Keep News Pulse XAU and XAG at their locked 0.75% only if the deliberate news exemption is retained. Disable News Pulse BTC on Swing until its lot sizing is margin-aware. Treat **59% to 62% within 730 days** as the honest planning range, not the 99.9% raw replay.
