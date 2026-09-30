# Okala 80/20 — build, native tests and prop-account replay

Research date: 28 September 2026. Instrument: Exness USTEC CFD. Decision: **do not add this mechanical version to the funded portfolio.**

## Executive conclusion

The research EA is built and compiles with zero errors and warnings. It is explicitly locked to Strategy Tester, not live trading. The frozen mechanical adaptation does not reproduce the transcript's claimed 70% win rate. The combined version loses money over the year and the fully real-tick six-month sample, fails the predeclared long-history PF gate, and is worse than the shifted-level control. That rejects this implementation for deployment; it does not prove that the discretionary futures trader lacks an edge.

Compared accounts: **FTMO $10K 2-Step Swing** and **FundedNext $5K Stellar Instant**, as in the previous account plan. This is standalone testing, not an addition to the existing multi-EA basket, not FundedNext FNL futures, and not a target-broker backtest. No live EA, BAT, website or funded account was changed. No Git push or purchase was made.

## What was built

The EA combines prices ending in 20/80 with tick-built 200-second execution bars and M10 context. It includes a strict fork reversal, a cross-section pullback, an H-context continuation proxy and untouched repair targets. Main exit: initial 10-index-point stop, half off at +15, remaining stop to entry, a quarter at +30 and the final quarter at a 30–60-point repair target or +60. Separate sensitivity: all out at +15. Execution delay can change the actual fill-to-stop distance.

The transcript does not supply complete numerical rules for reaction speed, fork/H geometry, level tolerance, the exact time window, or discretionary exits. Those were frozen as research assumptions in RULES.md before the tests. The source uses Nasdaq futures; a CFD can quote a different price, so the same last-two-digit level need not be the same market level. Wickless candles do not establish that unfilled orders remain there.

Sessions 09:30–11:30 and 13:30–15:30 New York; spread cap 2 points; one idea at a time; max 7/day; 20-minute maximum hold; no pyramiding or risk escalation. Source tick size 0.01; 10 price points means 10.00, not ten broker ticks. These are choices for this adaptation, not claimed exact trader rules.

## Native results — last year

27 September 2025 through 26 September 2026, end exclusive 27 September. $10K starting balance, fixed $100 planned stop-risk per whole idea, no compounding. Native spread, commission and 150ms execution delay included. These raw returns are **not** the smaller-risk prop-account returns below. Win rate counts complete ideas, grouping their partial exits.

| Variant | Ideas | Return | Win rate | PF | Max equity DD | Ideas/weekday | Max W/L streak |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Strict fork | 0 | 0.00% | — | — | 0.00% | 0.00 | 0/0 |
| Cross-section | 224 | -21.51% | 40.62% | 0.85 | 30.32% | 0.86 | 5/6 |
| H-context cross | 64 | -5.28% | 40.62% | 0.87 | 14.70% | 0.25 | 3/5 |
| 80/20 combined, staged | 224 | -21.51% | 40.62% | 0.85 | 30.32% | 0.86 | 5/6 |
| Shifted 30/70 control | 230 | 4.20% | 44.35% | 1.03 | 18.65% | 0.88 | 7/7 |
| 80/20 combined, full TP15 | 224 | -17.32% | 39.73% | 0.88 | 30.62% | 0.86 | 5/8 |

The strict fork produced **zero yearly entries**: its retest-and-break requirement plus a 10-point stop is too restrictive on these observations. This is an uninformative test of our interpretation, not a negative backtest of his discretionary fork. Combined equals cross-section on the year because the H entries are a subset and no fork qualifies. Do not count the two identical results as independent confirmation.

Combined activity: 224 ideas, 18.68/month, 4.30/week and 0.86/weekday; median hold 88.36 seconds. Native MT5 lists 354 closing deals because of partial exits; using that denominator would misstate the idea win rate. Illustrative binomial 95% interval around the grouped win rate: 34.4–47.2%; serial dependence and selection make this an incomplete uncertainty measure, not proof of future accuracy.

## Real-tick check and older-history limitations

Only the six-month check is 100% real ticks. The year mixes real ticks with synthesized older ticks. Genuine source ticks start 1 January 2026. Intrabar wick/200-second strategies are especially sensitive to that distinction.

| Window | Variant | Ideas | Return | Win rate | PF | Equity DD | Tick quality |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6m | 80/20 combined, staged | 133 | -23.43% | 38.35% | 0.74 | 30.89% | 100% real ticks |
| 6m | Shifted 30/70 control | 141 | -10.18% | 41.13% | 0.89 | 21.06% | 100% real ticks |
| 1y | 80/20 combined, staged | 224 | -21.51% | 40.62% | 0.85 | 30.32% | 73% real ticks |
| 1y | Shifted 30/70 control | 230 | 4.20% | 44.35% | 1.03 | 18.65% | 73% real ticks |
| 3y | 80/20 combined, staged | 343 | 6.45% | 43.73% | 1.03 | 26.27% | 24% real ticks |
| 3y | Shifted 30/70 control | 366 | 26.85% | 44.81% | 1.12 | 15.80% | 24% real ticks |
| 5y | 80/20 combined, staged | 344 | 5.36% | 43.60% | 1.03 | 26.48% | 14% real ticks |
| 5y | Shifted 30/70 control | 367 | 25.76% | 44.69% | 1.12 | 15.92% | 14% real ticks |

Older Model1 screens and every native test are retained in RAW_RESULTS.json. Model1 synthetic ticks cannot validate true historical 200-second structure. These tests are not an untouched forward-validation sample. No parameter search was performed after seeing the losses.

## Account assumptions and rule compatibility

FTMO 2-Step: 10% then 5% targets, at least four opening days per phase, 5% Prague-midnight daily loss and 10% static total loss. The replay assumes 2/5 business days of administration after phases one/two, then the first funded reward window after 14 days. Swing does not impose the usual news/overnight/weekend restrictions, but all other forbidden-practice rules still apply. [Official objectives](https://ftmo.com/en/trading-objectives/), [Swing rules](https://ftmo.com/faq/ftmo-swing-account-type/), [rewards](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/).

Stellar Instant: no evaluation phases; 6% balance-trailing loss floor capped at initial balance, no firm daily loss limit; reward after 14 days with at least 1% growth, or 5% growth checked at EOD. The model retains 3% of initial capital above the floor when withdrawing. Initial split modeled at 70%, FTMO at 80%. [Loss rules](https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts), [reward eligibility](https://help.fundednext.com/en/articles/11641693-what-is-the-eligibility-criteria-for-my-performance-reward-in-the-stellar-instant-account).

Stellar Instant permits EAs with an additional EA fee and other conditions. Its Quick Strike rule counts profitable positions closed within 30 seconds; a cycle share at or above 30% is a violation. The official funded-account process includes warning/forfeiture and possible termination. Here the conservative proxy counts >=30% short-duration partial-profit share at a flat cycle boundary as compatibility failure and credits no payout, not as a drawdown breach. Partial-exit classification and exact cycle-end treatment require written confirmation. This is not a definitive compliance adjudication. [EA rules](https://help.fundednext.com/en/articles/11641338-can-i-use-ea-in-stellar-instant), [Quick Strike](https://help.fundednext.com/en/articles/14702484-understanding-the-quick-strike-parameter-on-fundednext).

The research-analysis skill separated these current official requirements from replay assumptions and from the interview's promotional claims. It led to a separate Quick Strike compatibility audit rather than equating a profitable backtest with an approved payout.

### Sizing and costs

Index leverage modeled at 1:15 FTMO Swing / 1:5 Instant, one USD per index point per lot. Target-account lot sizes and exact execution remain unverified. Conservatively require >=0.05 lot per quarter, total >=0.20 and multiples of 0.04. Size down for margin first, never round up above risk. Same lot grid for TP15 to isolate exit differences. These contract assumptions must be checked on the purchased platform before any future implementation. [FTMO published index leverage](https://ftmo.com/en/blog/a-few-answers-to-your-questions/), [Instant leverage](https://help.fundednext.com/en/articles/11641369-what-is-the-leverage-provided-in-the-stellar-instant-accounts).

Risk caps are 0.25%/0.50% FTMO and 0.15%/0.25% Instant, generally with a 30% margin ceiling. A separate FTMO 80%-margin reference approximates the higher existing exposure allowance; it is not a recommendation. Initial risk covers the entire idea, not each partial. Loss/headroom guards may stop new trading; an unresolved safe account is not a passed challenge.

Reference replay retains native fills/spread/latency with a $0.70/lot commission floor. Stress adds 2 index points/lot, reduces positive realized gross partials by 10%, worsens negative ones by 10%, and shocks floating marks similarly. Instant deducts 60% of positive news-window profit for 29 known releases; the release calendar is incomplete. Stress also removes 10% of other positive Instant partials. This is hypothetical sensitivity, not measured target-broker slippage.

Native partial cash and recorded approximately one-second adverse equity enter the replay. Interval lows and newly ratcheted floors are combined conservatively. No invented emergency closing price or live execution. Timings mean first request eligibility, not money arriving in a bank; fees, add-ons, tax and VPS costs are excluded.

## Whole-year account replay

Start 27 September 2025. If a guard or compatibility failure stops trading, the row stops too; it does not represent continued trading through a breach. Both cost cases are shown.

| Exit | Account / configured cap | Costs | Median actual risk $ | Ideas | End/stop balance $ | Phase 1 | First request | Quick proxy failure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 80/20 combined, staged | FTMO 10K 0.25% cap / 30% margin | reference | 16.80 | 224 | 9,652.63 | not reached | not reached | not reached |
| 80/20 combined, staged | FTMO 10K 0.25% cap / 30% margin | stress | 17.20 | 129 | 9,207.71 | not reached | not reached | not reached |
| 80/20 combined, staged | FTMO 10K 0.50% cap / 30% margin | reference | 16.80 | 224 | 9,652.63 | not reached | not reached | not reached |
| 80/20 combined, staged | FTMO 10K 0.50% cap / 30% margin | stress | 17.20 | 129 | 9,207.71 | not reached | not reached | not reached |
| 80/20 combined, staged | FTMO 10K 0.50% cap / 80% margin | reference | 45.65 | 190 | 9,294.48 | not reached | not reached | not reached |
| 80/20 combined, staged | FTMO 10K 0.50% cap / 80% margin | stress | 45.11 | 37 | 9,193.57 | not reached | not reached | not reached |
| 80/20 combined, staged | Instant 5K 0.15% cap / 30% margin | reference | 2.69 | 224 | 4,942.30 | not reached | not reached | not reached |
| 80/20 combined, staged | Instant 5K 0.15% cap / 30% margin | stress | 2.68 | 208 | 4,746.00 | not reached | not reached | not reached |
| 80/20 combined, staged | Instant 5K 0.25% cap / 30% margin | reference | 2.69 | 224 | 4,942.30 | not reached | not reached | not reached |
| 80/20 combined, staged | Instant 5K 0.25% cap / 30% margin | stress | 2.68 | 208 | 4,746.00 | not reached | not reached | not reached |
| 80/20 combined, full TP15 | FTMO 10K 0.25% cap / 30% margin | reference | 16.80 | 224 | 9,715.54 | not reached | not reached | not reached |
| 80/20 combined, full TP15 | FTMO 10K 0.25% cap / 30% margin | stress | 17.20 | 128 | 9,214.87 | not reached | not reached | not reached |
| 80/20 combined, full TP15 | FTMO 10K 0.50% cap / 30% margin | reference | 16.80 | 224 | 9,715.54 | not reached | not reached | not reached |
| 80/20 combined, full TP15 | FTMO 10K 0.50% cap / 30% margin | stress | 17.20 | 128 | 9,214.87 | not reached | not reached | not reached |
| 80/20 combined, full TP15 | FTMO 10K 0.50% cap / 80% margin | reference | 45.90 | 173 | 9,228.06 | not reached | not reached | not reached |
| 80/20 combined, full TP15 | FTMO 10K 0.50% cap / 80% margin | stress | 45.11 | 43 | 9,198.60 | not reached | not reached | not reached |
| 80/20 combined, full TP15 | Instant 5K 0.15% cap / 30% margin | reference | 2.80 | 17 | 4,990.91 | not reached | not reached | 2025-11-26 |
| 80/20 combined, full TP15 | Instant 5K 0.15% cap / 30% margin | stress | 2.80 | 17 | 4,973.94 | not reached | not reached | 2025-11-26 |
| 80/20 combined, full TP15 | Instant 5K 0.25% cap / 30% margin | reference | 2.80 | 17 | 4,990.91 | not reached | not reached | 2025-11-26 |
| 80/20 combined, full TP15 | Instant 5K 0.25% cap / 30% margin | stress | 2.80 | 17 | 4,973.94 | not reached | not reached | 2025-11-26 |

## 180-day resampling — not future probabilities

500 paired 28-day block-bootstrap paths from the same year, seed 9288020; blocks preserve intraday clustering, price paths, exits and source news labels. They do not predict future news, spread, regime or slippage. Only about one year of source observations supports the resampling. 0/500 is a sample result, not zero real-world risk. Rows are alternative scenarios, not independent extra evidence. Instant starts in the funded stage by construction; calling that a 100% challenge pass rate would be misleading.

| Exit | Account | Costs | Phase 1 | Both phases | First request | Days if reached | Loss-limit breach | Quick proxy failure | Mean total reward $ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 80/20 combined, staged | FTMO 10K 0.25% cap / 30% margin | reference | 0/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, staged | FTMO 10K 0.25% cap / 30% margin | stress | 0/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, staged | FTMO 10K 0.50% cap / 30% margin | reference | 0/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, staged | FTMO 10K 0.50% cap / 30% margin | stress | 0/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, staged | FTMO 10K 0.50% cap / 80% margin | reference | 2/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, staged | FTMO 10K 0.50% cap / 80% margin | stress | 0/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, staged | Instant 5K 0.15% cap / 30% margin | reference | N/A | N/A | 8/500 | 142.2 | 0/500 | 171/500 | 0.57 |
| 80/20 combined, staged | Instant 5K 0.15% cap / 30% margin | stress | N/A | N/A | 0/500 | — | 0/500 | 169/500 | 0.00 |
| 80/20 combined, staged | Instant 5K 0.25% cap / 30% margin | reference | N/A | N/A | 8/500 | 142.2 | 0/500 | 171/500 | 0.57 |
| 80/20 combined, staged | Instant 5K 0.25% cap / 30% margin | stress | N/A | N/A | 0/500 | — | 0/500 | 169/500 | 0.00 |
| 80/20 combined, full TP15 | FTMO 10K 0.25% cap / 30% margin | reference | 0/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, full TP15 | FTMO 10K 0.25% cap / 30% margin | stress | 0/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, full TP15 | FTMO 10K 0.50% cap / 30% margin | reference | 0/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, full TP15 | FTMO 10K 0.50% cap / 30% margin | stress | 0/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, full TP15 | FTMO 10K 0.50% cap / 80% margin | reference | 14/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, full TP15 | FTMO 10K 0.50% cap / 80% margin | stress | 0/500 | 0/500 | 0/500 | — | 0/500 | 0/500 | 0.00 |
| 80/20 combined, full TP15 | Instant 5K 0.15% cap / 30% margin | reference | N/A | N/A | 12/500 | 118.7 | 0/500 | 311/500 | 0.87 |
| 80/20 combined, full TP15 | Instant 5K 0.15% cap / 30% margin | stress | N/A | N/A | 0/500 | — | 0/500 | 307/500 | 0.00 |
| 80/20 combined, full TP15 | Instant 5K 0.25% cap / 30% margin | reference | N/A | N/A | 12/500 | 118.7 | 0/500 | 311/500 | 0.87 |
| 80/20 combined, full TP15 | Instant 5K 0.25% cap / 30% margin | stress | N/A | N/A | 0/500 | — | 0/500 | 307/500 | 0.00 |

## Main staged version — 30/60/120/180-day windows

Percentages below are unconditional across all starts, including unresolved and failed paths. Conditional days exist only when at least one path reaches the milestone. Overlapping historical starts are not independent experiments. The JSON includes counts, no-trade paths, rejection reasons, breach timings and rewards for both exit variants.

| Method | Days | Account | Costs | Starts | Phase 1 | First request | Quick proxy failure | No request/no failure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rolling | 30 | FTMO 10K 0.25% cap / 30% margin | reference | 48 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 30 | FTMO 10K 0.25% cap / 30% margin | reference | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 60 | FTMO 10K 0.25% cap / 30% margin | reference | 44 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 60 | FTMO 10K 0.25% cap / 30% margin | reference | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 120 | FTMO 10K 0.25% cap / 30% margin | reference | 35 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 120 | FTMO 10K 0.25% cap / 30% margin | reference | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 180 | FTMO 10K 0.25% cap / 30% margin | reference | 27 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 180 | FTMO 10K 0.25% cap / 30% margin | reference | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 30 | FTMO 10K 0.25% cap / 30% margin | stress | 48 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 30 | FTMO 10K 0.25% cap / 30% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 60 | FTMO 10K 0.25% cap / 30% margin | stress | 44 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 60 | FTMO 10K 0.25% cap / 30% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 120 | FTMO 10K 0.25% cap / 30% margin | stress | 35 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 120 | FTMO 10K 0.25% cap / 30% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 180 | FTMO 10K 0.25% cap / 30% margin | stress | 27 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 180 | FTMO 10K 0.25% cap / 30% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 30 | FTMO 10K 0.50% cap / 30% margin | reference | 48 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 30 | FTMO 10K 0.50% cap / 30% margin | reference | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 60 | FTMO 10K 0.50% cap / 30% margin | reference | 44 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 60 | FTMO 10K 0.50% cap / 30% margin | reference | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 120 | FTMO 10K 0.50% cap / 30% margin | reference | 35 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 120 | FTMO 10K 0.50% cap / 30% margin | reference | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 180 | FTMO 10K 0.50% cap / 30% margin | reference | 27 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 180 | FTMO 10K 0.50% cap / 30% margin | reference | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 30 | FTMO 10K 0.50% cap / 30% margin | stress | 48 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 30 | FTMO 10K 0.50% cap / 30% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 60 | FTMO 10K 0.50% cap / 30% margin | stress | 44 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 60 | FTMO 10K 0.50% cap / 30% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 120 | FTMO 10K 0.50% cap / 30% margin | stress | 35 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 120 | FTMO 10K 0.50% cap / 30% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 180 | FTMO 10K 0.50% cap / 30% margin | stress | 27 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 180 | FTMO 10K 0.50% cap / 30% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 30 | FTMO 10K 0.50% cap / 80% margin | reference | 48 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 30 | FTMO 10K 0.50% cap / 80% margin | reference | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 60 | FTMO 10K 0.50% cap / 80% margin | reference | 44 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 60 | FTMO 10K 0.50% cap / 80% margin | reference | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 120 | FTMO 10K 0.50% cap / 80% margin | reference | 35 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 120 | FTMO 10K 0.50% cap / 80% margin | reference | 500 | 0.4% | 0.0% | 0.0% | 100.0% |
| rolling | 180 | FTMO 10K 0.50% cap / 80% margin | reference | 27 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 180 | FTMO 10K 0.50% cap / 80% margin | reference | 500 | 0.4% | 0.0% | 0.0% | 100.0% |
| rolling | 30 | FTMO 10K 0.50% cap / 80% margin | stress | 48 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 30 | FTMO 10K 0.50% cap / 80% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 60 | FTMO 10K 0.50% cap / 80% margin | stress | 44 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 60 | FTMO 10K 0.50% cap / 80% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 120 | FTMO 10K 0.50% cap / 80% margin | stress | 35 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 120 | FTMO 10K 0.50% cap / 80% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 180 | FTMO 10K 0.50% cap / 80% margin | stress | 27 | 0.0% | 0.0% | 0.0% | 100.0% |
| bootstrap | 180 | FTMO 10K 0.50% cap / 80% margin | stress | 500 | 0.0% | 0.0% | 0.0% | 100.0% |
| rolling | 30 | Instant 5K 0.15% cap / 30% margin | reference | 48 | N/A | 0.0% | 25.0% | 75.0% |
| bootstrap | 30 | Instant 5K 0.15% cap / 30% margin | reference | 500 | N/A | 0.0% | 26.4% | 73.6% |
| rolling | 60 | Instant 5K 0.15% cap / 30% margin | reference | 44 | N/A | 0.0% | 34.1% | 65.9% |
| bootstrap | 60 | Instant 5K 0.15% cap / 30% margin | reference | 500 | N/A | 0.0% | 32.2% | 67.8% |
| rolling | 120 | Instant 5K 0.15% cap / 30% margin | reference | 35 | N/A | 0.0% | 17.1% | 82.9% |
| bootstrap | 120 | Instant 5K 0.15% cap / 30% margin | reference | 500 | N/A | 0.6% | 33.8% | 65.8% |
| rolling | 180 | Instant 5K 0.15% cap / 30% margin | reference | 27 | N/A | 0.0% | 7.4% | 92.6% |
| bootstrap | 180 | Instant 5K 0.15% cap / 30% margin | reference | 500 | N/A | 1.6% | 34.2% | 64.6% |
| rolling | 30 | Instant 5K 0.15% cap / 30% margin | stress | 48 | N/A | 0.0% | 25.0% | 75.0% |
| bootstrap | 30 | Instant 5K 0.15% cap / 30% margin | stress | 500 | N/A | 0.0% | 26.4% | 73.6% |
| rolling | 60 | Instant 5K 0.15% cap / 30% margin | stress | 44 | N/A | 0.0% | 34.1% | 65.9% |
| bootstrap | 60 | Instant 5K 0.15% cap / 30% margin | stress | 500 | N/A | 0.0% | 32.2% | 67.8% |
| rolling | 120 | Instant 5K 0.15% cap / 30% margin | stress | 35 | N/A | 0.0% | 17.1% | 82.9% |
| bootstrap | 120 | Instant 5K 0.15% cap / 30% margin | stress | 500 | N/A | 0.0% | 33.6% | 66.4% |
| rolling | 180 | Instant 5K 0.15% cap / 30% margin | stress | 27 | N/A | 0.0% | 7.4% | 92.6% |
| bootstrap | 180 | Instant 5K 0.15% cap / 30% margin | stress | 500 | N/A | 0.0% | 33.8% | 66.2% |
| rolling | 30 | Instant 5K 0.25% cap / 30% margin | reference | 48 | N/A | 0.0% | 25.0% | 75.0% |
| bootstrap | 30 | Instant 5K 0.25% cap / 30% margin | reference | 500 | N/A | 0.0% | 26.4% | 73.6% |
| rolling | 60 | Instant 5K 0.25% cap / 30% margin | reference | 44 | N/A | 0.0% | 34.1% | 65.9% |
| bootstrap | 60 | Instant 5K 0.25% cap / 30% margin | reference | 500 | N/A | 0.0% | 32.2% | 67.8% |
| rolling | 120 | Instant 5K 0.25% cap / 30% margin | reference | 35 | N/A | 0.0% | 17.1% | 82.9% |
| bootstrap | 120 | Instant 5K 0.25% cap / 30% margin | reference | 500 | N/A | 0.6% | 33.8% | 65.8% |
| rolling | 180 | Instant 5K 0.25% cap / 30% margin | reference | 27 | N/A | 0.0% | 7.4% | 92.6% |
| bootstrap | 180 | Instant 5K 0.25% cap / 30% margin | reference | 500 | N/A | 1.6% | 34.2% | 64.6% |
| rolling | 30 | Instant 5K 0.25% cap / 30% margin | stress | 48 | N/A | 0.0% | 25.0% | 75.0% |
| bootstrap | 30 | Instant 5K 0.25% cap / 30% margin | stress | 500 | N/A | 0.0% | 26.4% | 73.6% |
| rolling | 60 | Instant 5K 0.25% cap / 30% margin | stress | 44 | N/A | 0.0% | 34.1% | 65.9% |
| bootstrap | 60 | Instant 5K 0.25% cap / 30% margin | stress | 500 | N/A | 0.0% | 32.2% | 67.8% |
| rolling | 120 | Instant 5K 0.25% cap / 30% margin | stress | 35 | N/A | 0.0% | 17.1% | 82.9% |
| bootstrap | 120 | Instant 5K 0.25% cap / 30% margin | stress | 500 | N/A | 0.0% | 33.6% | 66.4% |
| rolling | 180 | Instant 5K 0.25% cap / 30% margin | stress | 27 | N/A | 0.0% | 7.4% | 92.6% |
| bootstrap | 180 | Instant 5K 0.25% cap / 30% margin | stress | 500 | N/A | 0.0% | 33.8% | 66.2% |

## Why this is not a funded-system candidate

1. Raw loss and control failure: the main year has PF 0.85; the six-month fully real-tick check has PF 0.74. No observed advantage for the advertised 20/80 grid over the matched shifted grid.
2. Unresolved fidelity: the strict fork gives no yearly entries; the H is only a numerical proxy. The actual trader's timing, discretion and futures feed have not been replicated.
3. Tight stops plus modest index leverage consume margin before reaching the configured risk cap. Raising risk does not create an edge and often changes no trade size at all.
4. Short holds create a separate Instant compliance concern. The staged year's positive-partial <=30-second share is 16.80% versus 4.34% using complete ideas; neither full-year number guarantees a particular payout cycle is under 30%.
5. Guards reduce breach incidence by stopping entries. They do not convert this into a profitable or fast-passing system.

Decision: retain the EA and evidence as research, reject production promotion and do not buy either account for this strategy alone. Keep the existing portfolio unchanged. A new study would first need annotated chart examples to resolve fork/cross discretion and original NQ tick data (or explicitly accept CFD transfer risk), followed by genuinely untouched forward data and target-platform fill checks. Such a study would be a separately registered revision, not an optimization of these losing thresholds.

## Audit and reproducibility

RULES.md, run-config.json and BUILD.json freeze each native revision. Initial build/output remains in audit-initial-build. Revision 1.01 fixes current-candle repair-target invalidation without retuning thresholds. Both builds and all results are retained; no favorable run is hidden. Native reports, inputs, orders, journals, deal CSVs and floating traces are compressed under native/. Native cash reconciles with grouped idea cash. A 150ms quote/deal timestamp mismatch is aligned forward in the analyzer using the native ledger, not altered prices or profit.

PROP_PROTOCOL.md documents predeclared replay assumptions; PROP_MANIFEST.json hashes the simulator and its source data. PROP_RESULTS.json contains all windows and both exit methods; PROP_YEAR.json includes every accepted account-replay idea. Unit checks cover floating losses, partial-profit ratchets, cash, phase sequencing, trading days, withdrawal accounting, margin and minimum lots, Quick Strike, truncated horizons and daylight-saving-preserving bootstrap blocks. CHECKS.json records the final audit.

Reproduce locally with the saved research runner only; do not attach the EA to a live account. Its tester-only guard intentionally refuses live initialization.

