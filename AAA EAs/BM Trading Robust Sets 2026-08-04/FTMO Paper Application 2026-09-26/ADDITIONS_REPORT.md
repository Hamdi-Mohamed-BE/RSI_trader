# FTMO $10K Swing: adding Gold RSI VWAP and Claude Nasdaq 5M DI

Offline research, 26 September 2026. No live account, EA, launcher, website or trading settings changed.

## Scope and method

Core = raw Gold Overnight Value Area + News Pulse XAU + News Pulse XAG. RSI VWAP means the separate gold EA; it is not an extra indicator bolted onto Nasdaq. Nasdaq means Claude's promoted DI-filter build (DI period 14, EMA 12, 09:30 NY M5 signal, fixed 2.5R, ATR trailing OFF). It is NOT Nasdaq Overnight or the original no-DI bot.

All four portfolios use the same $10,000 account, $71.43 nominal fixed-dollar risk per ordinary entry and $10 per news side. Broker lot rounding can increase actual risk. This study does not apply the production Recommended Adaptive 0.25x Nasdaq multiplier. Both news sides stay available, subject to shared gates.

Shared gates: $300 daily admission budget, $225 simultaneous initial risk, $150 metals/per-symbol risk, $9,200 internal equity buffer, seven entries/day and no new entries after three closed losses; 80% maximum reserved margin. Ordinary stressed floating-loss reserve 1.25R; news 2R. Full assumptions: PROTOCOL.md.

1,000 matched 180-day paths per portfolio and cost case, using joint weekly blocks from 2 March–30 August 2026; seed 20260926. Same draws and limits for every combination. Historical replay uses 4 March–30 August 2026. September is excluded to preserve comparability with the existing core study.

This is a saved native-MT5-ledger portfolio simulation, NOT a fresh FTMO tick backtest. News presets were fitted on the same history; the DI rule was selected on Sep 2025–Apr 2026, partly overlapping this sample. No independent out-of-sample forecast is claimed. Small samples, regime change, weekly-resampling limitations and selection bias dominate Monte Carlo sampling error.

FTMO modeling: 10% then 5% targets, four trading days per evaluation phase, $500 daily/$1,000 static loss limits, Prague midnight, no time limit. Administrative assumptions: two business days to Phase 2, five to funded, first reward after 14 calendar days of funded trading while flat, four business days to receipt; 80% profit share. Stops at first reward request or day 180; no lifetime survival estimate.

Reference costs retain native spread/gaps with commission floors. Stress reduces gross wins 10%, enlarges gross losses 10%, adds slippage (2 USTEC points; $0.20 ordinary gold/$1 news gold; $0.04 silver), doubles negative swaps and adds overnight carry reserve.

## Source availability

| EA | Source trades in 26 weeks |
|---|---:|
| gold-overnight-value-area/standard | 100 |
| news-pulse-xau/standard | 20 |
| news-pulse-xag/standard | 17 |
| xau-rsi-vwap/standard | 32 |
| nasdaq-5m-candle-momentum/dynamic | 90 |

## Stressed execution

| Portfolio | Funded 30d | Funded 60d | Funded 120d | Funded 180d | Paid 60d | Paid 120d | Paid 180d | Median days to funded* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Core: Raw Gold + XAU/XAG news | 0.4% | 11.3% | 55.1% | 88.2% | 2.0% | 35.7% | 78.5% | 106.1 |
| Core + Gold RSI VWAP | 0.6% | 11.7% | 51.8% | 83.8% | 2.5% | 33.0% | 72.8% | 106.4 |
| Core + Nasdaq 5M DI | 3.0% | 20.7% | 49.9% | 66.8% | 5.8% | 34.5% | 56.5% | 84.8 |
| Core + Gold RSI VWAP + Nasdaq 5M DI | 3.3% | 21.5% | 49.6% | 63.1% | 5.3% | 33.8% | 50.6% | 79.7 |

*Timing is conditional on completion by day 180; unfinished paths are censored, not failed.

### Historical shared-account replay (no withdrawals or phase resets)

| Portfolio | Admitted trades | Net USD | Win rate | PF | Closed-balance DD | Stop-reserve DD proxy | Worst modeled day | Max win/loss streak | News baskets admitted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Core: Raw Gold + XAU/XAG news | 124 | $3,037.64 | 70.97% | 2.82 | 2.25% | 3.50% | $204.16 | 11/3 | 24 |
| Core + Gold RSI VWAP | 142 | $2,808.90 | 72.54% | 2.10 | 3.21% | 4.33% | $272.58 | 13/3 | 24 |
| Core + Nasdaq 5M DI | 204 | $2,278.76 | 55.88% | 1.38 | 8.63% | 10.09% | $294.64 | 7/5 | 21 |
| Core + Gold RSI VWAP + Nasdaq 5M DI | 18 | $-772.54 | 33.33% | 0.22 | 8.43% | 8.66% | $267.48 | 1/4 | 2 |

Historical P&L is hypothetical evaluation trading profit, NOT a payout. Stop-reserve DD is not tick-measured equity DD; neither stops nor reserves bound gap losses.

### Phase timing and safety

| Portfolio | P1 median days* | P2 median days* | Paid median days* | Breaches before first reward, 180d | Paths hitting $9,200 admission gate | 95th percentile reserve DD |
|---|---:|---:|---:|---:|---:|---:|
| Core: Raw Gold + XAU/XAG news | 59.6 | 31.0 | 122.0 | 0.0% | 0/1000 | 5.28% |
| Core + Gold RSI VWAP | 59.6 | 30.3 | 122.7 | 0.0% | 6/1000 | 7.04% |
| Core + Nasdaq 5M DI | 45.6 | 21.5 | 107.0 | 0.0% | 408/1000 | 12.04% |
| Core + Gold RSI VWAP + Nasdaq 5M DI | 42.8 | 20.8 | 100.9 | 0.0% | 510/1000 | 12.59% |

Phase 2 timing starts at its account availability, excluding the prior review delay. Milestone timing cohorts differ; their medians should not be added.

### Matched-path changes versus core at 180 days

| Addition | Funding change (pp) | Payout change (pp) | Payout only with addition | Payout only with core | Payout paired MC-only 95% interval (pp) |
|---|---:|---:|---:|---:|---:|
| Core + Gold RSI VWAP | -4.4 | -5.7 | 50 | 107 | -8.1 to -3.3 |
| Core + Nasdaq 5M DI | -21.4 | -22.0 | 41 | 261 | -25.1 to -18.9 |
| Core + Gold RSI VWAP + Nasdaq 5M DI | -25.1 | -27.9 | 46 | 325 | -31.3 to -24.5 |

These intervals measure random path sampling only, not real-world forecast accuracy.

### Historical per-EA attribution in the five-EA combination

| EA | Trades | Wins | Net USD |
|---|---:|---:|---:|
| xau-rsi-vwap/standard | 4 | 1 | $-296.96 |
| nasdaq-5m-candle-momentum/dynamic | 8 | 1 | $-464.35 |
| news-pulse-xag/standard | 2 | 0 | $-113.85 |
| gold-overnight-value-area/standard | 4 | 4 | $102.62 |

## Reference execution

| Portfolio | Funded 30d | Funded 60d | Funded 120d | Funded 180d | Paid 60d | Paid 120d | Paid 180d | Median days to funded* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Core: Raw Gold + XAU/XAG news | 1.7% | 22.6% | 80.8% | 98.3% | 6.2% | 61.4% | 95.9% | 86.8 |
| Core + Gold RSI VWAP | 2.4% | 23.6% | 79.0% | 97.4% | 6.6% | 60.9% | 94.8% | 86.8 |
| Core + Nasdaq 5M DI | 5.5% | 37.5% | 80.4% | 92.9% | 11.9% | 65.6% | 88.5% | 71.6 |
| Core + Gold RSI VWAP + Nasdaq 5M DI | 6.0% | 39.4% | 78.4% | 89.0% | 13.1% | 64.8% | 82.4% | 66.6 |

*Timing is conditional on completion by day 180; unfinished paths are censored, not failed.

### Historical shared-account replay (no withdrawals or phase resets)

| Portfolio | Admitted trades | Net USD | Win rate | PF | Closed-balance DD | Stop-reserve DD proxy | Worst modeled day | Max win/loss streak | News baskets admitted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Core: Raw Gold + XAU/XAG news | 125 | $4,221.25 | 72.00% | 4.20 | 1.58% | 2.50% | $150.65 | 11/3 | 25 |
| Core + Gold RSI VWAP | 142 | $4,107.82 | 72.54% | 2.95 | 2.11% | 2.71% | $229.99 | 13/3 | 24 |
| Core + Nasdaq 5M DI | 211 | $4,573.35 | 57.35% | 1.89 | 6.82% | 8.71% | $237.83 | 7/5 | 23 |
| Core + Gold RSI VWAP + Nasdaq 5M DI | 25 | $-787.73 | 36.00% | 0.31 | 8.67% | 8.67% | $210.66 | 2/4 | 3 |

Historical P&L is hypothetical evaluation trading profit, NOT a payout. Stop-reserve DD is not tick-measured equity DD; neither stops nor reserves bound gap losses.

### Phase timing and safety

| Portfolio | P1 median days* | P2 median days* | Paid median days* | Breaches before first reward, 180d | Paths hitting $9,200 admission gate | 95th percentile reserve DD |
|---|---:|---:|---:|---:|---:|---:|
| Core: Raw Gold + XAU/XAG news | 45.6 | 26.0 | 107.7 | 0.0% | 0/1000 | 3.88% |
| Core + Gold RSI VWAP | 45.6 | 25.1 | 107.7 | 0.0% | 0/1000 | 4.48% |
| Core + Nasdaq 5M DI | 36.6 | 20.0 | 92.9 | 0.0% | 119/1000 | 9.56% |
| Core + Gold RSI VWAP + Nasdaq 5M DI | 31.8 | 19.0 | 88.6 | 0.0% | 196/1000 | 10.27% |

Phase 2 timing starts at its account availability, excluding the prior review delay. Milestone timing cohorts differ; their medians should not be added.

### Matched-path changes versus core at 180 days

| Addition | Funding change (pp) | Payout change (pp) | Payout only with addition | Payout only with core | Payout paired MC-only 95% interval (pp) |
|---|---:|---:|---:|---:|---:|
| Core + Gold RSI VWAP | -0.9 | -1.1 | 13 | 24 | -2.3 to +0.1 |
| Core + Nasdaq 5M DI | -5.4 | -7.4 | 20 | 94 | -9.4 to -5.4 |
| Core + Gold RSI VWAP + Nasdaq 5M DI | -9.3 | -13.5 | 19 | 154 | -15.9 to -11.1 |

These intervals measure random path sampling only, not real-world forecast accuracy.

### Historical per-EA attribution in the five-EA combination

| EA | Trades | Wins | Net USD |
|---|---:|---:|---:|
| xau-rsi-vwap/standard | 4 | 1 | $-256.56 |
| nasdaq-5m-candle-momentum/dynamic | 12 | 2 | $-600.98 |
| news-pulse-xag/standard | 3 | 1 | $8.75 |
| gold-overnight-value-area/standard | 6 | 5 | $61.05 |

## Important limits

- Zero breaches in these paths does not establish zero real breach probability. Intratrade FTMO bid/ask equity, abrupt gaps, outages, liquidity/rejections, changing margin and contractual disqualification are not fully modeled.
- The model stops at the first reward request; continued funded-account survival and post-withdrawal drawdown are not tested.
- Swing allows news trading generally, but this does not confirm that the exact pre-release two-sided stop strategy meets FTMO forbidden-practice conditions. Written eligibility clarification is still needed.
- Existing news production builds hard-lock a different risk level. The $10/order and shared FTMO gates are research assumptions, not a deployable claim. No launcher has been created or changed.
- More trades do not guarantee faster passing: losses, correlated exposure, margin competition and daily admission limits matter. No parameters were optimized for this comparison.

## Interpretation of the actual historical sequence

Under stressed execution the five-EA combination closed its final trade on 18 March 2026, after only 18 trades, at $9,227.46. It then could not admit another trade while reserving losses above the $9,200 internal buffer: 194 ordinary signals and 26 news baskets were rejected by that buffer. It did not breach the modeled FTMO hard limit, but it did not pass either phase or receive a payout. The reference-cost version also stalled ($9,212.27, 25 trades). These are sequence-dependent failures to progress, not successful low-drawdown outcomes.

Adding only Nasdaq DI reduced historical admitted news baskets from 24 to 21 under stress, and gold news fills from 10 to 6. Margin-rejected news baskets increased from six to nine. Adding only RSI VWAP reduced admitted raw Gold trades from 97 to 85; its own 30 trades made a net loss of $283.28 despite winning 20 trades. These effects are specific to this period and sizing.

**Sizing caveat:** $71.43 is a nominal target in this inherited simulation, not a strict cash-risk cap. It rounds UP to a 0.01-lot step; the largest admitted initial trade risk was $140.79 in the RSI addition historical case. A deployment requiring a hard $71.43 ceiling must round down (or skip the trade if the minimum lot is too large) and be retested. Do not interpret these results as testing a strict $71.43 maximum.

At the tested nominal allocation, keep the core as the stronger six-month candidate; do not add both at full ordinary risk based on this evidence. Nasdaq improved early completion rates among modeled paths, but not overall six-month success. A reduced Nasdaq allocation would be a separate test, not a proven remedy. Neither this comparison nor the core itself has established reliable real-world pass or payout probabilities.

## Verification

DI cache EX5 hash matches the promoted production DI binary; 971 native trades have uniquely reconstructed initial stops and reconciled cash P&L. All original source hashes, nine engine tests, seven adapter checks, eight historical parity fields and eleven phase tests passed. Core funding/payout percentages match the prior phase study exactly at every horizon.

[FTMO comparison](https://ftmo.com/en/comparison-table/) · [Reward rules](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/) · [Swing](https://ftmo.com/en/faq/ftmo-swing-account-type/) · [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/)
