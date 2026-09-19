# Raw Gold + XAU/XAG News — $10K FTMO Swing feasibility

Window: **19 July–18 September 2026**, with 19 September excluded. One account, one attempt, no replacement purchases. Research only; no live settings, BATs, website, terminal or account were changed.

## Conclusion

**The observed sequence did not reach funded status or payout within these two months.** At the larger margin-compatible news allocation, Phase 1 passed on 4 September; Verification remained below its 5% target at the end. This is an unfinished evaluation, not an observed account blow-up.

There is **no defensible real-world funding or payout probability from this study alone**. The resampling frequencies below are conditional model outputs from nine weeks, including six news releases, with news parameters fitted on the same year. They are not validated FTMO probabilities and should not justify buying or trading a paid challenge without further checks.

## Risk and margin

- Raw Gold Overnight Value Area: unchanged entry/exit rules; $100 target stop risk, i.e. 1% of initial $10K. Sizing uses the pre-fill requested entry and original stop. Broker lot-step rounding up can increase actual risk; it is not a $100 hard cap.
- Main news scenario: $10 target risk per order, **0.10% per side on each metal**. Both directions retained. This gives $20 planned per asset/event and $40 across both metals before costs, gaps and other positions.
- Corresponding news lots: XAU 0.05 each side with a $2 price stop; XAG 0.10 each side with a $0.02 price stop. Tight stops are why even small cash risk can require substantial margin.
- Maximum reserved gross margin in this replay: **$7,468.22**. Research ceiling: 80% of conservative modeled equity; no hedge-margin relief. New-entry daily closed-loss gate and planned open-risk ceiling: $200 each. These gates were not installed anywhere.
- Current/default news setting, $75 per order (0.75%), cannot be assumed executable on $10K Swing. On 12 August, reserving both sides requires about **$22,380 gold + $33,172 silver**. Even one side exceeds $10K on each metal. All 12 asset/event baskets were rejected by the unchanged-sizing scenario's margin check.
- Global Swing gold and silver leverage used: **1:15**, not the headline FX maximum 1:30. Silver increased from 1:9 effective 11 May 2026. The official notice excludes Australian and US clients; the actual purchased entity/specifications still need verification. [Gold update](https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/), [silver update](https://ftmo.com/en/blog/trading-updates/trading-update-7-may-2026/).

## Historical challenge path — $10/order news scenario

| Metric | Saved execution reference | Additional execution/cost stress |
|---|---:|---:|
| Closed trades actually admitted during evaluation | 50 | 50 |
| Phase 1 completion | 4 September 2026 | 4 September 2026 |
| Phase 1 closing balance | $11,743.65 | $11,616.72 |
| Verification ending balance | $10,287.94 | $10,191.98 |
| Verification return | +2.88% | +1.92% |
| Required Verification balance | $10,500 | $10,500 |
| Funded within window | No | No |
| Payout within window | $0 | $0 |
| Detected equity-proxy limit breach | None | None |
| Maximum equity-proxy drawdown | 4.60% | 5.09% |
| Worst daily loss from midnight balance, equity proxy | $116.44 | $116.76 |

Phase 1's excess profit does not carry into Verification. One raw trade was missed during the modeled phase transition, hence 50 admitted trades versus 51 in an uninterrupted account. Maximum peak-to-trough drawdown is not FTMO's daily-loss measure.

The model applies 10%/5% profit targets, four separate opening-trade days per evaluation, a $500 daily equity loss allowance relative to Prague midnight balance and a static $9,000 equity floor. No 1-Step Best Day rule is imposed. [FTMO objectives](https://ftmo.com/en/trading-objectives/).

Administrative timing is an assumption: two business days between evaluations, five business days to activate the funded account, and four business days from reward request to receipt. First reward request requires at least 14 days after the first funded trade, flat positions/orders and positive profit; 80% initial reward share is modeled. Passing the trading targets does not assure account approval or actual payment. [FTMO reward rules](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/).

## Per-EA contribution if the account runs continuously, without phase resets

These figures explain the strategy contribution, **not withdrawable challenge income**. Shared $10K, $100 raw risk / $10 news-order risk; all 51 trades admitted in the continuous replay.

| EA | Trades | Reference win rate | Reference net USD | Stressed net USD |
|---|---:|---:|---:|---:|
| Raw Gold Overnight Value Area | 35 | 65.71% | +$10.26 | -$12.89 |
| News Pulse XAU, event-specific | 8 | 75.00% | +$635.63 | +$590.52 |
| News Pulse XAG, event-specific | 8 | 50.00% | +$1,365.00 | +$1,209.50 |
| Combined | 51 | 64.71% | **+$2,010.89** | **+$1,787.14** |

Continuous final balances: **$12,010.89 / $11,787.14**, or +20.11% / +17.87%. Source tests originally compounded independently; here lots are resized to the stated fixed-reference budgets. Therefore raw USD totals legitimately differ from a simple slice of the original compounded raw ledger. Stressed combined win rate is 62.75%.

The six releases are 29 July FOMC, 7 August NFP, 12 August CPI, 4 September NFP, 11 September CPI and 16 September FOMC. A release can produce more than one trade per asset. Nearly all profit came from a very small news sample; the raw strategy itself was approximately flat.

## 1,000 joint weekly-block resamples — NOT forecast probabilities

Same initial account, no retries. All three EAs and opposite/same-event legs stay together within each sampled week. Seed 20260919; nine sampled weeks per path. Repeating weeks also repeats their news opportunities, so these paths do not represent a known future economic calendar. They are not 1,000 independent observed challenges.

| Outcome for $10/order news scenario | Reference paths | Stressed paths |
|---|---:|---:|
| Funded within 30 calendar days | 1.1% (11/1,000) | 1.0% (10/1,000) |
| Funded before the two-month endpoint | 51.9% (519/1,000) | 46.2% (462/1,000) |
| Eligible to request a first payout by endpoint | 22.8% (228/1,000) | 19.9% (199/1,000) |
| Payout receipt by endpoint, under assumed processing lag | 13.8% (138/1,000) | 11.4% (114/1,000) |
| Detected equity-proxy breach by endpoint | 0.0% (0/1,000) | 0.7% (7/1,000) |
| Median first reward among paths with modeled receipt | $387.71 | $348.92 |

Zero observed breaches in one resampling scenario does **not** mean zero risk. The actual chronological sequence did not fund at all; the resampling moves favorable news weeks earlier on some paths. The remaining non-passing paths often simply remain in evaluation rather than fail the loss limits.

### Lower-risk and unchanged-sizing checks

| Sizing | Historical endpoint | Funded by endpoint, reference / stress | Payout receipt by endpoint, reference / stress |
|---|---|---:|---:|
| Raw $100 + news $5/order (XAU rounds to $6 planned) | Phase 2; $9,847.14 / $9,817.52 | 15.6% / 13.3% | 0.6% / 0.4% |
| Raw $100 + current news $75/order | News margin checks reject all baskets; Phase 1 | 0% / 0% | 0% / 0% |
| Raw $100 without news | Phase 1; $10,010.26 / $9,987.11 | 0% / 0% | 0% / 0% |

## Why these are not reliable real-world probabilities

1. The source fills are **Exness native MT5**, not FTMO. This study is an offline shared-account replay, not a new native FTMO backtest. Margin, quote paths, stop acceptance and execution may differ materially at FTMO.
2. The news presets were selected on 2025-09-19 through 2026-09-19; this whole test window is part of that fit. Event-specific training leaks into a predictive interpretation, although the replay itself uses chronological entry/exit events.
3. Source spreads and recorded commissions/swaps are included. Stress uses the separate 250ms news run, additional adverse price costs on entry/exit (gold news $0.50 each, silver $0.02 each, raw gold $0.10 each), and commission floors. This is not historical FTMO fee calibration or a simulation of live liquidity/order rejection. Recorded swap is zero; a different rollover/holiday exit could introduce swap at FTMO.
4. Intratrade equity is a mixed minute/second adverse-mark proxy, not synchronized native FTMO ticks. Boundary seconds, variable spread and asynchronous marks prevent certifying the exact daily/max-loss path. One raw trade crosses Prague midnight following a source-broker holiday close delay.
5. Fixed-dollar sizing and the documented margin/risk guards are hypothetical settings, not a claim about current installed EA behavior. News stays eligible in both directions; margin acceptance is separate from strategy entry eligibility.
6. FTMO Swing permits news trading but separately prohibits news-gap exploitation and non-replicable execution practices. The exact pre-news two-sided stop strategy requires clarification from FTMO. Account approval, country/entity eligibility, identity/contract review and reward approval are not included in these percentages. [Swing rules](https://ftmo.com/en/faq/ftmo-swing-account-type/), [forbidden practices](https://ftmo.com/en/forbidden-trading-practices/).

**Decision:** not a dependable one-month funding plan. First obtain written confirmation about the exact news-straddle design, then validate the unchanged strategies with FTMO instrument specifications and execution data, using forward/untouched periods. No deployment is recommended solely from these fitted-history resamples.

## Reproducibility

- `PROTOCOL.md`: assumptions, risk/margin rules, execution stress and official sources.
- `study.py`: offline shared-account replay and joint weekly resampling; no MT5 connection or trading code.
- `results.json`: full scenario output, individual admitted trades, source hashes and source-path audit.
- `test_study.py`: eight passing tests covering cash/cost conservation, rounding, daily reset, floating breach, distinct minimum days, phase resets, payout timing, default-news margin rejection and identity-order replay.
