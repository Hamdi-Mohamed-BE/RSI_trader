# FTMO $10K Swing: flat risk versus 1.5x after losses

20 September 2026. This replaces the prior standalone Gold sizing answer for the user's intended FTMO question. It does not replace that research's data or alter live settings.

## Result

**With the previous FTMO portfolio controls unchanged, geometric loss escalation made passing and getting a payout less frequent.** For raw Gold + XAU/XAG news, six-month stressed first-payout receipt frequency fell from **78.8% to 41.1%**. The principal failure mode was blocked entries and stalled evaluation, not more modeled loss-limit breaches.

These are conditional model frequencies from resampled historical weeks, **not credible independently validated probabilities of a future paid challenge**. The news presets were fitted on overlapping history, and the source outcomes are not a fresh FTMO tick backtest.

## Account, risk and comparison

The modeled account is $10,000 FTMO 2-Step Swing: $1,000 Challenge target, $500 Verification target, four trading days per phase, $500 daily allowance and static $9,000 equity floor. Daily reset follows Prague daylight saving. These are the [2-Step objectives](https://ftmo.com/en/trading-objectives/), not 1-Step's different rules.

Two frozen combinations:

1. Raw Gold Overnight Value Area only.
2. The prior preferred three-EA combination: raw Gold Overnight Value Area + News Pulse XAU + News Pulse XAG.

Base risk stays as previously tested: **$71.43 ordinary Gold risk** (5% daily allowance / 7) and **$10 per news order**, reserving both news sides. The user's $50 was treated as an illustrative multiplier example, not a requested replacement base.

One account-wide counter is used: each net losing close increases the next requested risk to 1.5 times the preceding level; any net winning close resets it. Net breakeven does not reset. Gold sequence: $71.43, $107.14, $160.71, $241.07, $361.61. News per-side sequence: $10, $15, $22.50, $33.75, $50.625. A win on any included EA resets the shared counter; this is not an independent counter per EA. New account phases reset it too.

Pending news orders keep the size fixed at placement. A loss on the first side does not resize the already placed opposite side. The opposite order is retained. Existing positions are not resized.

## Main results: Gold + XAU/XAG news

Each row uses **1,000 identical sampled market paths per rule**, with all EAs sharing one account and the original timing/margin constraints. Funded means both phases completed and the modeled funded account ready. Paid means first reward receipt within the horizon, not just eligibility to request it.

### With execution/cost stress

| Horizon | Flat funded | 1.5x funded | Flat paid | 1.5x paid | Flat stalled | 1.5x stalled | Model loss breaches, flat / 1.5x |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 months | 12.1% | 10.1% | 1.9% (19/1,000) | 1.9% (19/1,000) | 0.0% | 12.2% | 0 / 0 |
| 4 months | 59.0% | 38.7% | 41.1% (411/1,000) | 25.9% (259/1,000) | 0.0% | 35.2% | 0 / 0 |
| 6 months | 88.7% | 47.0% | 78.8% (788/1,000) | 41.1% (411/1,000) | 0.0% | 47.3% | 0 / 0 |

The remaining six-month outcomes were 21.2% unfinished for flat and 11.6% unfinished for escalation. Stalled means the inherited model stopped an evaluation after 30 days without an entry. It is recorded separately from an equity breach and is not a newly verified FTMO contractual termination outcome. Zero model breaches does not establish zero actual loss-limit or liquidation risk.

| Horizon | Median trades, flat / 1.5x | Median first reward **if paid**, flat / 1.5x | 95th-percentile model DD, flat / 1.5x |
|---|---:|---:|---:|
| 2 months | 41 / 30 | $198.71 / $210.65 | 4.47% / 3.71% |
| 4 months | 75 / 45.5 | $174.89 / $158.21 | 5.02% / 4.12% |
| 6 months | 86 / 45 | $156.69 / $163.78 | 5.32% / 4.20% |

Conditional reward medians exclude unpaid attempts. Lower modeled drawdown on escalation largely reflects taking fewer trades; it is not evidence of a better passing plan. At six months the paired payout-frequency difference is -37.7 percentage points; the Monte Carlo-only approximate 95% interval is -40.84 to -34.56 points. This interval excludes selection bias, feed differences, execution uncertainty and model error.

### Reference costs, without additional stress

| Horizon | Flat funded | 1.5x funded | Flat paid | 1.5x paid |
|---|---:|---:|---:|---:|
| 2 months | 23.7% | 16.2% | 5.0% | 3.7% |
| 4 months | 80.9% | 52.7% | 63.3% | 40.0% |
| 6 months | 98.7% | 56.2% | 95.5% | 51.9% |

## Why increasing risk causes stalls

The previous internal controls remain unchanged: $150 combined metals exposure, $225 total open/pending stop risk, a $300 daily admission budget, $9,200 internal equity buffer, seven daily entries and no new entries after three daily losing closes. These are **our model's internal protections**, not additional numerical FTMO rules.

After two consecutive losses, Gold requests $160.71, already over the $150 metals cap. A skipped trade is neither a win nor a reset, so subsequent Gold trades remain blocked. With Gold alone, there is no other trade to reset the counter. With news included, an affordable winning news side can reset it, but news size also increases and can exceed reserved margin. After more losses, the entire combination can stall.

Lot rounding can block entries earlier. Historical example: on 18 March, requested Gold risk $107.14 rounded to $158.75 and was rejected. On 7 April, requested $160.71 rounded to $198.685 and was rejected. These are sizing rejections, not actual trading losses.

Across the paired simulations, requested Gold risk reached $361.61 in the combined strategy, but the largest **admitted single initial-stop risk** was $147.13. Flat risk also occasionally admitted more than its target because of minimum/step rounding (up to $140.30). The model rejects the $280.63 minimum-lot risk seen in the standalone study. Requested risk is not a guaranteed cash-loss cap; gaps and costs remain separate.

The experiment did not remove safeguards, clip escalation at the cap, reset it after a rejection or reset it every morning. Each of those would be a different risk rule.

## Gold alone

| Horizon | Flat paid, reference / stress | 1.5x paid, reference / stress | 1.5x stalled under stress |
|---|---:|---:|---:|
| 2 months | 0.0% / 0.0% | 0.0% / 0.0% | 59.5% |
| 4 months | 0.0% / 0.0% | 0.0% / 0.0% | 94.6% |
| 6 months | 7.3% / 0.9% | 0.6% / 0.3% | 99.0% |

Gold-only six-month stressed funding frequency was 2.9% flat versus 0.4% escalating. The six-month stressed median trade count fell from 97 to 13. This is mostly the hard-cap conflict, not a universal conclusion about every possible capped progression.

## Actual historical sequence: Gold + news, stressed

These single paths are distinct from the resampling frequencies above. Independent accounts start at each window's beginning.

| Window | Rule | Closed trades | Win rate | Funded | First reward received | End/model-stop state | Model DD |
|---|---|---:|---:|---|---:|---|---:|
| 2 months | Flat | 39 | 79.49% | 14 Aug 2026 | $0 | Funded; no receipt by cutoff | 3.40% |
| 2 months | 1.5x | 31 | 64.52% | No | $0 | Verification, balance $10,182.25 | 2.65% |
| 4 months | Flat | 59 | 79.66% | 21 Jul 2026 | $329.73 on 10 Aug | First payout received | 2.65% |
| 4 months | 1.5x | 7 | 42.86% | No | $0 | Challenge stalled, balance $9,896.83 | 1.76% |
| 6 months | Flat | 92 | 70.65% | 9 Jul 2026 | $317.07 on 29 Jul | First payout received | 2.75% |
| 6 months | 1.5x | 41 | 60.98% | No | $0 | Challenge stalled, balance $10,042.44 | 3.54% |

No historical path above crossed a modeled loss floor. Unlike the earlier standalone replay, win rate and trade count can change here because risk/margin admission and phase transitions select different subsequent trades.

## Sensitivity: preserve two-week blocks

Another 1,000 paired attempts per horizon preserve longer streaks and dependence, using the same six-month evidence pool under execution stress.

| Horizon | Flat payout receipt | 1.5x payout receipt |
|---|---:|---:|
| 2 months | 2.7% | 2.3% |
| 4 months | 43.1% | 20.0% |
| 6 months | 81.0% | 37.3% |

The direction of the longer-window result is unchanged. This is not out-of-sample evidence.

## Data, costs and rule limitations

- Exact historical windows end **31 August 2026 exclusive**, through 30 August: 2m starts 30 June, 4m starts 30 April, 6m starts 28 February. They do not end today. Bootstrap draws from 26 shared weeks, 2 March–30 August; it is not a forward forecast made at each historical start date.
- Existing native source fills are replayed under FTMO-style margin, costs and rules. This is **not a fresh native MT5 test on FTMO ticks**, nor a test on the currently connected account. Position-size-dependent execution and synchronized floating equity are unavailable.
- Same fee floors as before: Gold $7 and Silver $47.50 per round-trip lot, or worse recorded source commission; recorded swap retained. These are simulation assumptions, not newly measured account charges. Stress haircuts favorable gross outcomes by 10%, enlarges gross losses by 10%, adds $0.20/oz ordinary Gold, $1/oz Gold news and $0.04/oz Silver execution cost, with adverse carry reserves.
- Open equity uses simultaneous initial-stop loss reserves (ordinary 1R, news 1.25R reference; 1.25R and 2R stress), not actual tick-by-tick floating P/L. It can reject a viable trade and still miss a larger gap. Model peak drawdown is not the same quantity as FTMO's static maximum-loss allowance.
- Gold/Silver 1:15 leverage is the frozen current-style scenario applied across all windows. [Gold's February update](https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/) and [Silver's May update](https://ftmo.com/en/blog/trading-updates/trading-update-7-may-2026/) support the published Swing rates; Silver was 1:9 before 11 May. This is not a reconstruction of every historical margin schedule or regional exception.
- Review delays remain assumed 2 business days after Challenge and 5 after Verification. First funded trade starts a conservative 14-day wait; request only flat with no pending orders and $25 gross profit, with four business days to receipt. FTMO describes requests on/after the 14th day, an initial 80% share for 2-Step and payment review/processing timing in its [reward FAQ](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/). The $25 modeled threshold is conservative relative to its stated $20 bank-transfer minimum; crypto withdrawal requirements differ. Challenge fees/refunds, taxes and subsequent rewards are excluded.
- Swing's ordinary news-trading permission does not certify a pre-news straddle or variable-risk sequence. FTMO separately warns about substantially enlarged positions and repeated higher trade-idea exposure in its [risk-management rules](https://ftmo.com/en/forbidden-trading-practices/). No exact numerical multiplier approval or future reward eligibility is assumed.

## Verification and saved evidence

30,000 modeled attempts: 24,000 one-week primary cases plus 6,000 two-week stress sensitivities. Eight new risk-rule tests and nine original FTMO-account tests passed. All 12 primary flat baseline aggregates exactly match the previous saved study; historical and selected paired paths also pass engine parity checks. Every outcome group reconciles. Input and engine hashes are saved in SOURCE MANIFEST.json.

`results.json` contains full historical ledgers, skipped-entry reasons, per-EA totals and bootstrap summaries. Fifteen `*-paths.json` files retain each paired path's outcome, trade count, payout, drawdown and requested/admitted risk. `PROTOCOL.md`, `engine.py`, `run_study.py` and `test_engine.py` make the assumptions and comparison reproducible. Python on Windows needs a valid IANA timezone database; the run used the bundled tzdata via PYTHONTZPATH.

**Recommendation for this tested FTMO configuration: retain flat risk.** A bounded progression that cannot lock itself out would need a separate, explicitly defined test. Do not treat lower modeled drawdown caused by inactivity as improved account-passing performance. No live settings, BATs, website data or original research inputs were changed; nothing was pushed.
